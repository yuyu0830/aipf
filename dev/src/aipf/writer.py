from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aipf.models import Kind, ProjectState, TaskStatus
from aipf.store import ProjectStore, utc_now
from aipf.validation import validate_evidence, validate_plan, validate_task


def parse_plan_spec(content: str) -> dict[str, Any]:
    value = yaml.safe_load(content)
    if not isinstance(value, dict):
        raise ValueError("plan input root must be a mapping")
    return value


def load_plan_spec(path: Path) -> dict[str, Any]:
    return parse_plan_spec(path.read_text(encoding="utf-8"))


def apply_plan(store: ProjectStore, runtime: dict[str, Any], spec: dict[str, Any]) -> tuple[str, list[str]]:
    if runtime["state"] not in {ProjectState.AWAITING_PLAN, ProjectState.AWAITING_PLAN_CONFIRMATION}:
        raise RuntimeError("an approved plan cannot be replaced")
    plan_input = spec.get("plan")
    task_inputs = spec.get("tasks")
    if not isinstance(plan_input, dict) or not isinstance(task_inputs, list) or not task_inputs:
        raise ValueError("input requires a plan mapping and at least one task")

    active_id = runtime.get("active_plan_id")
    active_path = store.path(Kind.PLAN, active_id) if active_id else None
    active_plan = store.read(active_path) if active_path and active_path.exists() else None
    existing_id = active_id if active_plan and active_plan["status"] == "proposed" else None
    requested_id = plan_input.get("id")
    plan_id = str(requested_id or existing_id or store.next_id(Kind.PLAN))
    plan_path = store.path(Kind.PLAN, plan_id)
    if plan_path.exists() and plan_id != existing_id:
        raise RuntimeError("only the active proposed plan can be revised")
    previous = store.read(plan_path) if plan_path.exists() else None

    task_documents: list[dict[str, Any]] = []
    reserved = {path.stem for path in store.paths(Kind.TASK)}
    next_number = max((int(value.split("_")[1]) for value in reserved), default=-1) + 1
    for item in task_inputs:
        if not isinstance(item, dict):
            raise ValueError("each task must be a mapping")
        task_id = str(item.get("id") or f"T_{next_number:03d}")
        next_number += 1
        task = {
            "id": task_id,
            "kind": Kind.TASK.value,
            "plan_id": plan_id,
            "goal": item.get("goal"),
            "references": item.get("references", []),
            "outputs": item.get("outputs", []),
            "constraints": item.get("constraints", []),
            "acceptance_criteria": item.get("acceptance_criteria", []),
            "verification": item.get("verification", {"commands": [], "evidence": []}),
            "status": TaskStatus.PENDING.value,
            "feedback": None,
            "remaining": [],
            "decisions": [],
            "evidence_ids": [],
            "updated_at": utc_now(),
        }
        validate_task(task)
        task_documents.append(task)

    task_ids = [task["id"] for task in task_documents]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("task ids must be unique")
    plan = {
        "id": plan_id,
        "kind": Kind.PLAN.value,
        "goal": plan_input.get("goal"),
        "roadmap_stage": plan_input.get("roadmap_stage"),
        "prior_plan_id": (
            active_plan.get("prior_plan_id") if existing_id and active_plan else active_id
        ),
        "approach": plan_input.get("approach"),
        "risks": plan_input.get("risks"),
        "scope": plan_input.get("scope", {"includes": [], "excludes": []}),
        "acceptance_criteria": plan_input.get("acceptance_criteria", []),
        "task_ids": task_ids,
        "checkpoints": previous.get("checkpoints", []) if existing_id and previous else [],
        "status": "proposed",
        "updated_at": utc_now(),
    }
    validate_plan(plan)

    for task in task_documents:
        store.write(store.path(Kind.TASK, task["id"]), task)
    store.write(plan_path, plan)
    runtime.update({
        "goal": plan["goal"],
        "state": ProjectState.AWAITING_PLAN_CONFIRMATION.value,
        "active_plan_id": plan_id,
        "active_task_id": None,
        "updated_at": utc_now(),
    })
    store.write(store.runtime_path, runtime)
    return plan_id, task_ids


def create_evidence(
    store: ProjectStore,
    task: dict[str, Any],
    *,
    summary: str,
    changes: list[str],
    outputs: list[str],
    verification: list[str],
    remaining: list[str],
    decisions: list[str],
) -> str:
    """Create and append an immutable Evidence snapshot for a submitted Task."""
    evidence_id = store.next_id(Kind.EVIDENCE)
    document = {
        "id": evidence_id,
        "kind": Kind.EVIDENCE.value,
        "plan_id": task["plan_id"],
        "task_id": task["id"],
        "attempt": len(task.get("evidence_ids", [])) + 1,
        "timestamp": utc_now(),
        "summary": summary,
        "changes": changes,
        "outputs": outputs,
        "verification": verification,
        "remaining": remaining,
        "decisions": decisions,
    }
    validate_evidence(document)
    return store.append_evidence(document)
