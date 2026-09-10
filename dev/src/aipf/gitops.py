from __future__ import annotations

import re
import subprocess
from pathlib import Path, PurePosixPath

from aipf.models import Kind
from aipf.projector import write_project, write_project_flow
from aipf.store import ProjectStore
from aipf.validation import validate_plan


def _git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ("git", *arguments),
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(message or f"git {' '.join(arguments)} failed")
    return result


def _repository_root(root: Path) -> None:
    result = _git(root, "rev-parse", "--show-toplevel")
    actual = Path(result.stdout.decode().strip()).resolve()
    if actual != root.resolve():
        raise RuntimeError("the AIPF project root must also be the Git repository root")
    if _git(root, "rev-parse", "--verify", "HEAD", check=False).returncode:
        raise RuntimeError("Git requires an initial commit before creating a checkpoint")


def _names(result: subprocess.CompletedProcess[bytes]) -> set[str]:
    return {value.decode("utf-8") for value in result.stdout.split(b"\0") if value}


def _dirty_paths(root: Path) -> set[str]:
    unstaged = _names(_git(root, "diff", "--name-only", "-z"))
    untracked = _names(_git(root, "ls-files", "--others", "--exclude-standard", "-z"))
    return unstaged | untracked


def _normalize_path(root: Path, value: str) -> str:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        relative = resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"checkpoint path is outside the project: {value}") from exc
    normalized = relative.as_posix()
    if normalized in {".", ".git"} or normalized.startswith(".git/"):
        raise ValueError(f"checkpoint path is too broad or reserved: {value}")
    return normalized


def _covered(path: str, allowed: set[str]) -> bool:
    candidate = PurePosixPath(path)
    return any(candidate == PurePosixPath(value) or PurePosixPath(value) in candidate.parents for value in allowed)


def create_checkpoint(
    store: ProjectStore,
    plan_id: str,
    task_ids: list[str],
    paths: list[str],
) -> str:
    root = store.root
    _repository_root(root)
    if _git(root, "diff", "--cached", "--quiet", check=False).returncode:
        raise RuntimeError("checkpoint creation requires an empty Git staging area")
    plan = store.read_object(Kind.PLAN, plan_id)
    if plan["status"] not in {"approved", "completed"}:
        raise RuntimeError("checkpoint plan must be approved or completed")
    if not task_ids or len(task_ids) != len(set(task_ids)):
        raise ValueError("checkpoint requires one or more unique Task ids")
    if any(task_id not in plan["task_ids"] for task_id in task_ids):
        raise ValueError("checkpoint Tasks must belong to the Plan")

    explicit = {_normalize_path(root, value) for value in paths}
    managed = {
        f".aipf/plans/{plan_id}.yaml",
        ".aipf/audits",
        ".aipf/runtime.yaml",
        "PROJECT.md",
        ".aipf/PROJECT_FLOW.md",
    }
    for task_id in task_ids:
        task = store.read_object(Kind.TASK, task_id)
        managed.add(f".aipf/tasks/{task_id}.yaml")
        managed.update(f".aipf/evidence/{evidence_id}.yaml" for evidence_id in task["evidence_ids"])
        explicit.update(_normalize_path(root, output) for output in task["outputs"])
    allowed = explicit | managed
    unaccounted = sorted(path for path in _dirty_paths(root) if not _covered(path, allowed))
    if unaccounted:
        raise RuntimeError("unaccounted working-tree changes: " + ", ".join(unaccounted))

    recorded_numbers = [int(item["id"].rsplit("_", 1)[1]) for item in plan["checkpoints"]]
    checkpoint_number = max(recorded_numbers + _checkpoint_numbers(root, plan_id), default=0) + 1
    checkpoint_id = f"{plan_id}-C_{checkpoint_number:03d}"
    original_plan = plan.copy()
    original_plan["checkpoints"] = [item.copy() for item in plan["checkpoints"]]
    plan["checkpoints"].append({"id": checkpoint_id, "task_ids": task_ids})
    validate_plan(plan)
    runtime = store.read(store.runtime_path)
    stage_paths = sorted(_dirty_paths(root))
    try:
        store.write(store.path(Kind.PLAN, plan_id), plan)
        write_project(store, runtime)
        write_project_flow(store, runtime)
        stage_paths = sorted(_dirty_paths(root))
        _git(root, "add", "-A", "--", *stage_paths)
        if _git(root, "diff", "--cached", "--quiet", check=False).returncode:
            task_label = ",".join(task_ids)
            _git(root, "commit", "-m", f"aipf({checkpoint_id}): checkpoint {task_label}")
        else:
            raise RuntimeError("checkpoint has no changes to commit")
    except Exception:
        _git(root, "restore", "--staged", "--", *stage_paths, check=False)
        store.write(store.path(Kind.PLAN, plan_id), original_plan)
        write_project(store, runtime)
        try:
            write_project_flow(store, runtime)
        except ValueError:
            # Preserve a malformed user file so the marker error is visible.
            pass
        raise
    return checkpoint_id


def _checkpoint_commit(root: Path, checkpoint_id: str) -> str:
    if not re.fullmatch(r"P_[0-9]{3}-C_[0-9]{3}", checkpoint_id):
        raise ValueError("invalid checkpoint id")
    result = _git(root, "log", "--format=%H%x00%s%x00")
    fields = [item.decode("utf-8", errors="replace").strip() for item in result.stdout.split(b"\0") if item.strip()]
    expected = f"aipf({checkpoint_id}): checkpoint"
    matches = [fields[index] for index in range(0, len(fields) - 1, 2) if fields[index + 1].startswith(expected)]
    if len(matches) != 1:
        raise RuntimeError(f"checkpoint commit must exist exactly once: {checkpoint_id}")
    return matches[0]


def _checkpoint_numbers(root: Path, plan_id: str) -> list[int]:
    result = _git(root, "log", "--format=%s")
    pattern = re.compile(rf"^aipf\({re.escape(plan_id)}-C_([0-9]{{3}})\): checkpoint")
    return [int(match.group(1)) for line in result.stdout.decode().splitlines() if (match := pattern.match(line))]


def restore_checkpoint(store: ProjectStore, checkpoint_id: str, reason: str) -> str:
    root = store.root
    _repository_root(root)
    reason = reason.strip()
    if not reason:
        raise ValueError("checkpoint restore reason must not be empty")
    if _git(root, "status", "--porcelain", "-z").stdout:
        raise RuntimeError("checkpoint restore requires a clean working tree")
    commit = _checkpoint_commit(root, checkpoint_id)
    if _git(root, "merge-base", "--is-ancestor", commit, "HEAD", check=False).returncode:
        raise RuntimeError("checkpoint is not an ancestor of HEAD")

    current_plan = store.read_object(Kind.PLAN, checkpoint_id[:5])
    if checkpoint_id not in {item["id"] for item in current_plan["checkpoints"]}:
        raise RuntimeError("checkpoint is not indexed by its Plan")
    checkpoint_history = [item.copy() for item in current_plan["checkpoints"]]
    evidence_history = list(store.objects(Kind.EVIDENCE))
    audit_history = list(store.objects(Kind.AUDIT))
    flow_path = root / ".aipf/PROJECT_FLOW.md"
    current_flow = flow_path.read_text(encoding="utf-8") if flow_path.exists() else None

    _git(root, "restore", "--source", commit, "--staged", "--worktree", "--", ".")
    restored_store = ProjectStore(root)
    restored_plan = restored_store.read_object(Kind.PLAN, checkpoint_id[:5])
    if checkpoint_id not in {item["id"] for item in restored_plan["checkpoints"]}:
        raise RuntimeError("checkpoint is not indexed by its restored Plan")
    restored_plan["checkpoints"] = checkpoint_history
    validate_plan(restored_plan)
    restored_store.write(restored_store.path(Kind.PLAN, restored_plan["id"]), restored_plan)
    for document in evidence_history:
        path = restored_store.path(Kind.EVIDENCE, document["id"])
        if not path.exists():
            restored_store.append_evidence(document)
    for document in audit_history:
        path = restored_store.path(Kind.AUDIT, document["id"])
        if not path.exists():
            restored_store.write(path, document)
    restored_store.append_audit(
        "checkpoint_restored",
        checkpoint_id,
        reason,
    )
    if current_flow is not None:
        flow_path.write_text(current_flow, encoding="utf-8")
    runtime = restored_store.read(restored_store.runtime_path)
    write_project(restored_store, runtime)
    write_project_flow(restored_store, runtime)
    _git(root, "add", "-A", "--", ".")
    _git(root, "commit", "-m", f"aipf({checkpoint_id}): restore checkpoint")
    return checkpoint_id
