from __future__ import annotations

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


def validate_plan(document: dict[str, Any]) -> None:
    _require(document, ("id", "kind", "goal", "scope", "acceptance_criteria", "task_ids", "status", "revision"), "plan")
    if document["kind"] != Kind.PLAN.value or not str(document["id"]).startswith("P_"):
        raise ValueError("invalid plan identity")
    if not isinstance(document["goal"], str) or not document["goal"].strip():
        raise ValueError("plan goal must not be empty")
    if not isinstance(document["scope"], dict):
        raise ValueError("plan scope must be a mapping")
    _strings(document["scope"].get("includes"), "scope.includes")
    _strings(document["scope"].get("excludes"), "scope.excludes")
    _strings(document["acceptance_criteria"], "acceptance_criteria", nonempty=True)
    _strings(document["task_ids"], "task_ids")
    if document["status"] not in {"proposed", "approved", "completed", "cancelled"}:
        raise ValueError("invalid plan status")


def validate_task(document: dict[str, Any]) -> None:
    _require(document, ("id", "kind", "plan_id", "goal", "references", "outputs", "constraints", "acceptance_criteria", "verification", "status", "result", "revision"), "task")
    if document["kind"] != Kind.TASK.value or not str(document["id"]).startswith("T_"):
        raise ValueError("invalid task identity")
    if not isinstance(document["goal"], str) or not document["goal"].strip():
        raise ValueError("task goal must not be empty")
    _safe_paths(document["references"], "references", {"docs", "ref", "src"})
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
    result = document["result"]
    if not isinstance(result, dict):
        raise ValueError("result must be a mapping")
    _strings(result.get("evidence"), "result.evidence")
    _strings(result.get("outputs"), "result.outputs")


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
    validators = {Kind.PLAN: validate_plan, Kind.TASK: validate_task, Kind.AUDIT: validate_audit}
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
