from __future__ import annotations

from typing import Any

from aipf.models import HandoffKind, Status
from aipf.session import consume_capability, verify_capability
from aipf.state import validate_transition
from aipf.store import HandoffStore


def submit_task(
    store: HandoffStore,
    *,
    task_id: str,
    session_id: str,
    token: str,
    summary: str,
    evidence: list[str],
    artifacts: list[str],
) -> None:
    session = verify_capability(store, session_id, task_id, token)
    path = store.find(task_id, HandoffKind.TASK)
    document = store.read(path)
    validate_transition(document["status"], Status.REVIEW)
    if not summary.strip():
        raise ValueError("completion summary must not be empty")
    if not evidence:
        raise ValueError("at least one verification evidence item is required")
    progress = document.setdefault("progress", {})
    if progress.get("remaining"):
        raise ValueError("task still has remaining work")
    attempts: list[dict[str, Any]] = document.setdefault("execution", {}).setdefault("attempts", [])
    attempts.append(
        {
            "attempt": int(document.get("attempt", 0)) + 1,
            "session_id": session_id,
            "outcome": "submitted_for_review",
            "summary": summary,
            "evidence": evidence,
            "failure_analysis": None,
        }
    )
    document["attempt"] = attempts[-1]["attempt"]
    document["result"] = {"outcome": "success", "artifacts": artifacts, "evidence": evidence}
    document["status"] = Status.REVIEW.value
    store.update(path, document)
    consume_capability(store, session)


def report_task_failure(
    store: HandoffStore,
    *,
    task_id: str,
    session_id: str,
    token: str,
    status: Status,
    summary: str,
    cause_analysis: str,
) -> None:
    if status not in {Status.BLOCKED, Status.FAILED}:
        raise ValueError("report status must be blocked or failed")
    session = verify_capability(store, session_id, task_id, token)
    path = store.find(task_id, HandoffKind.TASK)
    document = store.read(path)
    validate_transition(document["status"], status)
    if not cause_analysis.strip():
        raise ValueError("failure cause analysis must not be empty")
    attempts = document.setdefault("execution", {}).setdefault("attempts", [])
    attempts.append(
        {
            "attempt": int(document.get("attempt", 0)) + 1,
            "session_id": session_id,
            "outcome": status.value,
            "summary": summary,
            "evidence": [],
            "failure_analysis": cause_analysis,
        }
    )
    document["attempt"] = attempts[-1]["attempt"]
    document["status"] = status.value
    document["blocker"] = cause_analysis
    store.update(path, document)
    consume_capability(store, session)
