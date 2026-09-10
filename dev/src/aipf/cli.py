from __future__ import annotations

import argparse
import sys
from importlib.resources import files
from pathlib import Path

from aipf.config import write_default_config
from aipf.gitops import create_checkpoint, restore_checkpoint
from aipf.models import Kind, ProjectState, TaskStatus
from aipf.notifications import notify
from aipf.projector import write_project, write_project_flow
from aipf.store import ProjectStore, utc_now
from aipf.validation import validate_plan, validate_project_spec, validate_store, validate_task
from aipf.writer import apply_plan, create_evidence, load_plan_spec, parse_plan_spec


def project_root(value: str) -> Path:
    return Path(value).resolve()


def read_runtime(store: ProjectStore) -> dict:
    if not store.runtime_path.exists():
        raise RuntimeError(f"not an aipf project: {store.root}; run `aipf init` first")
    return store.read(store.runtime_path)


def refresh(store: ProjectStore, runtime: dict) -> None:
    write_project(store, runtime)
    write_project_flow(store, runtime)


def _report_list(values: list[str], *, empty: str = "없음") -> None:
    if values:
        for value in values:
            print(f"- {value}")
    else:
        print(f"- {empty}")


def print_plan_review_report(plan: dict, tasks: list[dict]) -> None:
    """Print the persisted proposal in the form the user approves."""
    print(f"Plan {plan['id']} 승인 전 보고")
    print()
    print(f"Roadmap 단계: {plan['roadmap_stage']}")
    print(f"이전 Plan: {plan['prior_plan_id'] or '없음 (첫 Plan)'}")
    print(f"목표: {plan['goal']}")
    print("수행 방법:")
    _report_list(plan["approach"])
    print()
    print("범위:")
    print("- 포함:")
    _report_list(plan["scope"]["includes"])
    print("- 제외:")
    _report_list(plan["scope"]["excludes"])
    print()
    print("Task 순서:")
    for index, task in enumerate(tasks, start=1):
        print(f"{index}. {task['id']} {task['goal']}")
        print("   - 참조 자료: " + (", ".join(task["references"]) or "없음"))
        print("   - 산출물: " + (", ".join(task["outputs"]) or "없음"))
        verification = task["verification"]
        expected = verification["commands"] + verification["evidence"]
        print("   - 검증: " + (", ".join(expected) or "없음"))
    print()
    print("위험 및 주의점:")
    _report_list(plan["risks"])
    print()
    print("완료 조건:")
    _report_list(plan["acceptance_criteria"])
    print()
    print("다음 행동:")
    print(f"aipf review approve --target {plan['id']}")


def print_task_review_report(
    task: dict,
    omitted_outputs: list[str],
    evidence: dict,
) -> None:
    """Print the persisted Evidence and Task state before review."""
    print(f"Task {task['id']} 완료 보고")
    print()
    print(f"목표: {task['goal']}")
    print(f"Evidence: {evidence['id']}")
    print(f"결과 요약: {evidence['summary']}")
    print()
    print("실제 수행:")
    _report_list(evidence["changes"])
    print()
    print("산출물:")
    _report_list(evidence["outputs"])
    print()
    print("검증 결과:")
    _report_list(evidence["verification"])
    print()
    print("미완료 및 알려진 문제:")
    _report_list(task["remaining"])
    print()
    print("사용자 결정 필요:")
    _report_list(task["decisions"])
    print()
    print("선언했지만 제출하지 않은 산출물:")
    _report_list(omitted_outputs)
    print()
    print("다음 행동:")
    print("approve / revise / retry / cancel")


def write_guidance_files(root: Path) -> None:
    templates = files("aipf.templates")
    for name in ("AGENTS.md", "SKILLS.md", "MEMORY_MAP.md", "README.md"):
        target = root / name
        if not target.exists():
            target.write_text(templates.joinpath(name).read_text(encoding="utf-8"), encoding="utf-8")
    specification = root / "inputs" / "PROJECT_SPEC.md"
    if not specification.exists():
        specification.write_text(templates.joinpath("PROJECT_SPEC.md").read_text(encoding="utf-8"), encoding="utf-8")


def command_init(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    store = ProjectStore(root)
    if store.control.exists() and not args.force:
        raise RuntimeError(f"already initialized: {store.control}")
    goal = (args.goal or "").strip()
    if not goal:
        raise RuntimeError("--goal is required")
    store.initialize()
    write_guidance_files(root)
    write_default_config(store.config_path)
    runtime = {
        "schema_version": "1.0",
        "goal": goal,
        "state": ProjectState.AWAITING_PLAN.value,
        "active_plan_id": None,
        "active_task_id": None,
        "updated_at": utc_now(),
    }
    store.write(store.runtime_path, runtime)
    refresh(store, runtime)
    print(f"initialized: {root}")
    return 0


def command_plan_apply(args: argparse.Namespace) -> int:
    store = ProjectStore(project_root(args.directory))
    runtime = read_runtime(store)
    validate_project_spec(store.root / "inputs" / "PROJECT_SPEC.md")
    spec = parse_plan_spec(sys.stdin.read()) if args.file == "-" else load_plan_spec(Path(args.file).resolve())
    plan_id, task_ids = apply_plan(store, runtime, spec)
    refresh(store, runtime)
    plan = store.read_object(Kind.PLAN, plan_id)
    tasks = [store.read_object(Kind.TASK, task_id) for task_id in task_ids]
    print_plan_review_report(plan, tasks)
    return 0


def command_run(args: argparse.Namespace) -> int:
    store = ProjectStore(project_root(args.directory))
    runtime = read_runtime(store)
    if runtime["state"] in {ProjectState.AWAITING_PLAN, ProjectState.AWAITING_PLAN_CONFIRMATION}:
        print("waiting for plan approval")
        return 3
    if runtime["state"] == ProjectState.AWAITING_TASK_CONFIRMATION:
        print("waiting for task review")
        return 3
    plan = store.read_object(Kind.PLAN, runtime["active_plan_id"])
    tasks = [store.read_object(Kind.TASK, task_id) for task_id in plan["task_ids"]]
    task = next((item for item in tasks if item["status"] in {TaskStatus.PENDING, TaskStatus.READY}), None)
    if task is None:
        print("no task ready")
        return 0
    missing_references = [value for value in task["references"] if not (store.root / value).exists()]
    if missing_references:
        task["status"] = TaskStatus.BLOCKED.value
        blocked_summary = "Missing references: " + ", ".join(missing_references)
        task["remaining"] = [blocked_summary]
        task["decisions"] = []
        runtime.update({"state": ProjectState.BLOCKED.value, "active_task_id": task["id"], "updated_at": utc_now()})
        store.write(store.path(Kind.TASK, task["id"]), task)
        store.write(store.runtime_path, runtime)
        refresh(store, runtime)
        notify(store, "blocked", task["id"], blocked_summary)
        print(blocked_summary)
        return 2
    task["status"] = TaskStatus.RUNNING.value
    task["updated_at"] = utc_now()
    validate_task(task)
    store.write(store.path(Kind.TASK, task["id"]), task)
    runtime.update({"state": ProjectState.RUNNING.value, "active_task_id": task["id"], "updated_at": utc_now()})
    store.write(store.runtime_path, runtime)
    refresh(store, runtime)
    print(f"active task: {task['id']}")
    print(f"goal: {task['goal']}")
    print("references: " + (", ".join(task["references"]) or "none"))
    print("outputs: " + (", ".join(task["outputs"]) or "none"))
    print("verification commands: " + (", ".join(task["verification"]["commands"]) or "none"))
    print("expected evidence: " + (", ".join(task["verification"]["evidence"]) or "none"))
    return 0


def command_task_submit(args: argparse.Namespace) -> int:
    store = ProjectStore(project_root(args.directory))
    runtime = read_runtime(store)
    task = store.read_object(Kind.TASK, args.target)
    if task["status"] != TaskStatus.RUNNING:
        raise RuntimeError(f"task is not running: {args.target}")
    if not args.change:
        raise ValueError("at least one --change is required")
    outputs = args.output or []
    if not set(outputs) <= set(task["outputs"]):
        raise ValueError("submitted outputs must be declared by the task")
    missing = [value for value in outputs if not (store.root / value).exists()]
    if missing:
        raise ValueError("submitted outputs do not exist: " + ", ".join(missing))
    if (task["verification"]["commands"] or task["verification"]["evidence"]) and not args.evidence:
        raise ValueError("verification evidence is required")
    omitted = [value for value in task["outputs"] if value not in outputs]
    if omitted:
        print("warning: declared outputs not submitted: " + ", ".join(omitted))
    task["remaining"] = args.remaining or []
    task["decisions"] = args.decision_needed or []
    evidence_id = create_evidence(
        store,
        task,
        summary=args.summary,
        changes=args.change,
        outputs=outputs,
        verification=args.evidence or [],
        remaining=task["remaining"],
        decisions=task["decisions"],
    )
    task["evidence_ids"].append(evidence_id)
    task["status"] = TaskStatus.AWAITING_REVIEW.value
    task["updated_at"] = utc_now()
    validate_task(task)
    store.write(store.path(Kind.TASK, task["id"]), task)
    runtime.update({"state": ProjectState.AWAITING_TASK_CONFIRMATION.value, "active_task_id": task["id"], "updated_at": utc_now()})
    store.write(store.runtime_path, runtime)
    refresh(store, runtime)
    print_task_review_report(task, omitted, store.read_object(Kind.EVIDENCE, evidence_id))
    return 0


def _review_plan(store: ProjectStore, runtime: dict, target: str, decision: str) -> None:
    plan = store.read_object(Kind.PLAN, target)
    if runtime.get("active_plan_id") != target or plan["status"] != "proposed":
        raise RuntimeError("only the active proposed plan can be reviewed")
    if decision == "approve":
        plan["status"] = "approved"
        runtime["state"] = ProjectState.READY.value
    elif decision in {"revise", "retry"}:
        runtime["state"] = ProjectState.AWAITING_PLAN.value
    else:
        plan["status"] = "cancelled"
        runtime["state"] = ProjectState.CANCELLED.value
    plan["updated_at"] = utc_now()
    validate_plan(plan)
    store.write(store.path(Kind.PLAN, target), plan)


def _review_task(store: ProjectStore, runtime: dict, target: str, decision: str, feedback: str | None) -> list[str]:
    task = store.read_object(Kind.TASK, target)
    if runtime.get("active_task_id") != target or task["status"] != TaskStatus.AWAITING_REVIEW:
        raise RuntimeError("only the active submitted task can be reviewed")
    events: list[str] = []
    if decision == "approve":
        task["status"] = TaskStatus.COMPLETED.value
        runtime["active_task_id"] = None
        plan = store.read_object(Kind.PLAN, runtime["active_plan_id"])
        remaining = [
            store.read_object(Kind.TASK, task_id)
            for task_id in plan["task_ids"]
            if task_id != target and store.read_object(Kind.TASK, task_id)["status"] not in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}
        ]
        if remaining:
            runtime["state"] = ProjectState.READY.value
            events.append("task_completed")
        else:
            plan["status"] = "completed"
            plan["updated_at"] = utc_now()
            store.write(store.path(Kind.PLAN, plan["id"]), plan)
            runtime["state"] = ProjectState.AWAITING_PLAN.value
            events.extend(["task_completed", "plan_completed"])
    elif decision in {"revise", "retry"}:
        task["status"] = TaskStatus.READY.value
        task["feedback"] = feedback if decision == "revise" else None
        runtime["state"] = ProjectState.READY.value
    else:
        task["status"] = TaskStatus.CANCELLED.value
        runtime["state"] = ProjectState.CANCELLED.value
    task["updated_at"] = utc_now()
    validate_task(task)
    store.write(store.path(Kind.TASK, target), task)
    return events


def command_review(args: argparse.Namespace) -> int:
    store = ProjectStore(project_root(args.directory))
    runtime = read_runtime(store)
    if args.decision == "revise" and not args.feedback:
        raise ValueError("--feedback is required for revise")
    if args.target.startswith("P_"):
        _review_plan(store, runtime, args.target, args.decision)
        events = []
    elif args.target.startswith("T_"):
        events = _review_task(store, runtime, args.target, args.decision, args.feedback)
    else:
        raise ValueError("review target must be a plan or task id")
    runtime["updated_at"] = utc_now()
    store.write(store.runtime_path, runtime)
    summary = args.feedback or f"User selected {args.decision}"
    if args.audit_summary:
        store.append_audit("user_review", args.target, args.audit_summary, decision=args.decision)
    refresh(store, runtime)
    for event in events:
        notify(store, event, args.target, summary)
    print(f"review recorded: {args.decision} {args.target}")
    return 0


def command_status(args: argparse.Namespace) -> int:
    store = ProjectStore(project_root(args.directory))
    runtime = read_runtime(store)
    refresh(store, runtime)
    print(f"state: {runtime['state']}")
    print(f"plan: {runtime['active_plan_id'] or 'none'}")
    print(f"task: {runtime['active_task_id'] or 'none'}")
    return 0


def command_project_complete(args: argparse.Namespace) -> int:
    store = ProjectStore(project_root(args.directory))
    runtime = read_runtime(store)
    if runtime["state"] != ProjectState.AWAITING_PLAN:
        raise RuntimeError("project can be completed only while awaiting the next plan")
    plans = list(store.objects(Kind.PLAN))
    if not plans or any(plan["status"] not in {"completed", "cancelled"} for plan in plans):
        raise RuntimeError("all plans must be completed or cancelled")
    tasks = list(store.objects(Kind.TASK))
    if any(task["status"] not in {TaskStatus.COMPLETED, TaskStatus.CANCELLED} for task in tasks):
        raise RuntimeError("all tasks must be completed or cancelled")
    runtime.update({
        "state": ProjectState.COMPLETED.value,
        "active_plan_id": None,
        "active_task_id": None,
        "updated_at": utc_now(),
    })
    store.write(store.runtime_path, runtime)
    store.append_audit("project_completed", "project", "User confirmed project completion", decision="approve")
    refresh(store, runtime)
    print("project completed")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    store = ProjectStore(project_root(args.directory))
    errors = validate_store(store)
    for path, error in errors:
        print(f"{path}: {error}", file=sys.stderr)
    if errors:
        return 1
    print("valid")
    return 0


def command_checkpoint_create(args: argparse.Namespace) -> int:
    store = ProjectStore(project_root(args.directory))
    read_runtime(store)
    checkpoint_id = create_checkpoint(store, args.plan, args.task, args.path)
    print(f"checkpoint created: {checkpoint_id}")
    return 0


def command_checkpoint_restore(args: argparse.Namespace) -> int:
    store = ProjectStore(project_root(args.directory))
    read_runtime(store)
    checkpoint_id = restore_checkpoint(store, args.target, args.reason.strip())
    print(f"checkpoint restored: {checkpoint_id}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aipf")
    parser.add_argument("--directory", default=".")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init")
    init.add_argument("--goal", required=True)
    init.add_argument("--force", action="store_true")
    init.set_defaults(handler=command_init)

    plan = commands.add_parser("plan")
    plan_commands = plan.add_subparsers(dest="plan_command", required=True)
    apply_command = plan_commands.add_parser("apply")
    apply_command.add_argument("--file", required=True)
    apply_command.set_defaults(handler=command_plan_apply)

    commands.add_parser("run").set_defaults(handler=command_run)
    commands.add_parser("status").set_defaults(handler=command_status)
    commands.add_parser("validate").set_defaults(handler=command_validate)

    checkpoint = commands.add_parser("checkpoint")
    checkpoint_commands = checkpoint.add_subparsers(dest="checkpoint_command", required=True)
    checkpoint_create = checkpoint_commands.add_parser("create")
    checkpoint_create.add_argument("--plan", required=True)
    checkpoint_create.add_argument("--task", action="append", required=True)
    checkpoint_create.add_argument("--path", action="append", default=[])
    checkpoint_create.set_defaults(handler=command_checkpoint_create)
    checkpoint_restore = checkpoint_commands.add_parser("restore")
    checkpoint_restore.add_argument("--target", required=True)
    checkpoint_restore.add_argument("--reason", required=True)
    checkpoint_restore.set_defaults(handler=command_checkpoint_restore)

    project = commands.add_parser("project")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    project_commands.add_parser("complete").set_defaults(handler=command_project_complete)

    task = commands.add_parser("task")
    task_commands = task.add_subparsers(dest="task_command", required=True)
    submit = task_commands.add_parser("submit")
    submit.add_argument("--target", required=True)
    submit.add_argument("--summary", required=True)
    submit.add_argument("--change", action="append", default=[])
    submit.add_argument("--evidence", action="append", default=[])
    submit.add_argument("--output", action="append", default=[])
    submit.add_argument("--remaining", action="append", default=[])
    submit.add_argument("--decision-needed", dest="decision_needed", action="append", default=[])
    submit.set_defaults(handler=command_task_submit)

    review = commands.add_parser("review")
    review.add_argument("decision", choices=("approve", "revise", "retry", "cancel"))
    review.add_argument("--target", required=True)
    review.add_argument("--feedback")
    review.add_argument("--audit-summary")
    review.set_defaults(handler=command_review)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, RuntimeError, ValueError, PermissionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
