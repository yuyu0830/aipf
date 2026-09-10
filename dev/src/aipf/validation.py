from __future__ import annotations

import re
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

from aipf.models import Kind, ProjectState, TaskStatus


def _require(document: dict[str, Any], fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in document]
    if missing:
        raise ValueError(f"{label} missing fields: {', '.join(missing)}")


def _strings(value: Any, field: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and (item or not nonempty) for item in value):
        raise ValueError(f"{field} must be a list of strings")
    return value


def _safe_paths(values: Any, field: str, roots: set[str]) -> None:
    for value in _strings(values, field):
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] not in roots:
            raise ValueError(f"unsafe {field} path: {value}")


def validate_project_spec(path: Path) -> None:
    if not path.is_file():
        raise ValueError("project specification not found: inputs/PROJECT_SPEC.md")
    lines = path.read_text(encoding="utf-8").splitlines()
    heading = re.compile(r"^##\s+(?:\d+\.\s*)?진행 계획\s*$")
    start = next((index + 1 for index, line in enumerate(lines) if heading.match(line.strip())), None)
    if start is None:
        raise ValueError("project specification requires a 진행 계획 section")
    section: list[str] = []
    for line in lines[start:]:
        if re.match(r"^#{1,2}\s+", line.strip()):
            break
        section.append(line)
    item = re.compile(r"^\s*(?:\d+[.)]|[-*+])\s+(.+?)\s*$")
    for line in section:
        match = item.match(line)
        if not match:
            continue
        content = re.sub(r"\[[^]]*]", "", match.group(1)).strip()
        if content:
            return
    raise ValueError("project specification roadmap requires at least one stage")


def validate_plan(document: dict[str, Any]) -> None:
    _require(
        document,
        (
            "id", "kind", "goal", "roadmap_stage", "prior_plan_id", "approach", "risks",
            "scope", "acceptance_criteria", "task_ids", "checkpoints", "status",
        ),
        "plan",
    )
    plan_id = document["id"]
    if document["kind"] != Kind.PLAN.value or not re.fullmatch(r"P_[0-9]{3}", str(plan_id)):
        raise ValueError("invalid plan identity")
    if not isinstance(document["goal"], str) or not document["goal"].strip():
        raise ValueError("plan goal must not be empty")
    if not isinstance(document["roadmap_stage"], str) or not document["roadmap_stage"].strip():
        raise ValueError("plan roadmap_stage must not be empty")
    prior_plan_id = document["prior_plan_id"]
    if prior_plan_id is not None and (not isinstance(prior_plan_id, str) or not prior_plan_id.startswith("P_")):
        raise ValueError("plan prior_plan_id must be a plan id or null")
    _strings(document["approach"], "approach", nonempty=True)
    if not document["approach"]:
        raise ValueError("plan approach must not be empty")
    _strings(document["risks"], "risks", nonempty=True)
    if not isinstance(document["scope"], dict):
        raise ValueError("plan scope must be a mapping")
    _strings(document["scope"].get("includes"), "scope.includes")
    _strings(document["scope"].get("excludes"), "scope.excludes")
    _strings(document["acceptance_criteria"], "acceptance_criteria", nonempty=True)
    task_ids = _strings(document["task_ids"], "task_ids")
    if any(not re.fullmatch(r"T_[0-9]{3}", task_id) for task_id in task_ids):
        raise ValueError("task_ids must contain only task ids")
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("plan task_ids must be unique")
    checkpoints = document["checkpoints"]
    if not isinstance(checkpoints, list):
        raise ValueError("checkpoints must be a list")
    expected_checkpoint = 1
    for checkpoint in checkpoints:
        if not isinstance(checkpoint, dict):
            raise ValueError("each checkpoint must be a mapping")
        _require(checkpoint, ("id", "task_ids"), "checkpoint")
        checkpoint_id = checkpoint["id"]
        expected_id = f"{plan_id}-C_{expected_checkpoint:03d}"
        if checkpoint_id != expected_id:
            raise ValueError("checkpoint ids must match the plan and remain sequential")
        checkpoint_task_ids = _strings(checkpoint["task_ids"], "checkpoint.task_ids", nonempty=True)
        if len(checkpoint_task_ids) != len(set(checkpoint_task_ids)):
            raise ValueError("checkpoint task_ids must be unique")
        if any(task_id not in task_ids for task_id in checkpoint_task_ids):
            raise ValueError("checkpoint task_ids must refer to tasks in the plan")
        expected_checkpoint += 1
    if document["status"] not in {"proposed", "approved", "completed", "cancelled"}:
        raise ValueError("invalid plan status")


def validate_task(document: dict[str, Any]) -> None:
    _require(
        document,
        (
            "id", "kind", "plan_id", "goal", "references", "outputs", "constraints",
            "acceptance_criteria", "verification", "status", "remaining", "decisions",
            "evidence_ids",
        ),
        "task",
    )
    if "result" in document:
        raise ValueError("task result must be stored as Evidence")
    if document["kind"] != Kind.TASK.value or not str(document["id"]).startswith("T_"):
        raise ValueError("invalid task identity")
    if not isinstance(document["goal"], str) or not document["goal"].strip():
        raise ValueError("task goal must not be empty")
    _safe_paths(document["references"], "references", {"inputs", "ref", "src"})
    _safe_paths(document["outputs"], "outputs", {"src"})
    _strings(document["constraints"], "constraints")
    _strings(document["acceptance_criteria"], "acceptance_criteria", nonempty=True)
    verification = document["verification"]
    if not isinstance(verification, dict):
        raise ValueError("verification must be a mapping")
    _strings(verification.get("commands"), "verification.commands")
    _strings(verification.get("evidence"), "verification.evidence")
    if document["status"] not in set(TaskStatus):
        raise ValueError("invalid task status")
    _strings(document["remaining"], "remaining", nonempty=True)
    _strings(document["decisions"], "decisions", nonempty=True)
    evidence_ids = _strings(document["evidence_ids"], "evidence_ids")
    if any(not re.fullmatch(r"E_[0-9]{3}", value) for value in evidence_ids):
        raise ValueError("evidence_ids must contain only evidence ids")
    if document["status"] in {TaskStatus.AWAITING_REVIEW, TaskStatus.COMPLETED} and not evidence_ids:
        raise ValueError("submitted task requires at least one Evidence id")


def validate_evidence(document: dict[str, Any]) -> None:
    _require(
        document,
        (
            "id", "kind", "plan_id", "task_id", "attempt", "timestamp",
            "summary", "changes", "outputs", "verification", "remaining", "decisions",
        ),
        "evidence",
    )
    if document["kind"] != Kind.EVIDENCE.value or not re.fullmatch(r"E_[0-9]{3}", str(document["id"])):
        raise ValueError("invalid evidence identity")
    if not isinstance(document["plan_id"], str) or not re.fullmatch(r"P_[0-9]{3}", document["plan_id"]):
        raise ValueError("evidence plan_id must be a plan id")
    if not isinstance(document["task_id"], str) or not re.fullmatch(r"T_[0-9]{3}", document["task_id"]):
        raise ValueError("evidence task_id must be a task id")
    for field in ("attempt",):
        if not isinstance(document[field], int) or isinstance(document[field], bool) or document[field] < 1:
            raise ValueError(f"evidence {field} must be a positive integer")
    for field in ("timestamp", "summary"):
        if not isinstance(document[field], str) or not document[field].strip():
            raise ValueError(f"evidence {field} must be a non-empty string")
    _strings(document["changes"], "evidence.changes", nonempty=True)
    _strings(document["outputs"], "evidence.outputs", nonempty=True)
    _strings(document["verification"], "evidence.verification", nonempty=True)
    _strings(document["remaining"], "evidence.remaining", nonempty=True)
    _strings(document["decisions"], "evidence.decisions", nonempty=True)


def validate_audit(document: dict[str, Any]) -> None:
    _require(document, ("id", "kind", "timestamp", "event", "target", "summary", "decision"), "audit")
    if document["kind"] != Kind.AUDIT.value or not str(document["id"]).startswith("A_"):
        raise ValueError("invalid audit identity")
    if not all(isinstance(document[field], str) and document[field] for field in ("timestamp", "event", "target", "summary")):
        raise ValueError("audit text fields must not be empty")
    if document["decision"] is not None and document["decision"] not in {"approve", "revise", "retry", "cancel"}:
        raise ValueError("invalid audit decision")


def validate_runtime(document: dict[str, Any]) -> None:
    _require(document, ("schema_version", "goal", "state", "active_plan_id", "active_task_id", "updated_at"), "runtime")
    if document["state"] not in set(ProjectState):
        raise ValueError("invalid project state")


def validate_config(document: dict[str, Any]) -> None:
    _require(document, ("schema_version", "notifications"), "config")
    notifications = document["notifications"]
    if not isinstance(notifications, dict):
        raise ValueError("notifications must be a mapping")
    events = _strings(notifications.get("events"), "notifications.events")
    supported = {"task_completed", "plan_completed", "blocked", "never"}
    if not set(events) <= supported or ("never" in events and len(events) != 1):
        raise ValueError("invalid notification events")
    timeout = notifications.get("timeout_seconds")
    if not isinstance(timeout, int) or timeout < 1:
        raise ValueError("notification timeout must be a positive integer")


def validate_store(store) -> list[tuple[str, str]]:
    validators = {
        Kind.PLAN: validate_plan,
        Kind.TASK: validate_task,
        Kind.EVIDENCE: validate_evidence,
        Kind.AUDIT: validate_audit,
    }
    errors: list[tuple[str, str]] = []
    for kind, validator in validators.items():
        for path in store.paths(kind):
            try:
                validator(store.read(path))
            except Exception as exc:
                errors.append((str(path), str(exc)))
    for path, validator in ((store.runtime_path, validate_runtime), (store.config_path, validate_config)):
        try:
            validator(store.read(path))
        except Exception as exc:
            errors.append((str(path), str(exc)))
    return errors
