from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from aipf.models import HandoffKind
from aipf.store import HandoffStore, utc_now

if TYPE_CHECKING:
    from aipf.routing import RoutingDecision


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_session(
    store: HandoffStore,
    task_id: str,
    agent_id: str,
    *,
    decision: RoutingDecision | None = None,
    prompt_version: str = "unversioned",
    parent_session_id: str | None = None,
) -> tuple[str, str]:
    task_path = store.find(task_id, HandoffKind.TASK)
    task = store.read(task_path)
    if task["agent_id"] != agent_id:
        raise PermissionError("agent does not own task")
    session_id = f"S_{uuid.uuid4().hex[:12]}"
    token = secrets.token_urlsafe(32)
    path = store.control / "sessions" / f"{session_id}.yaml"
    store.atomic_write(
        path,
        {
            "schema_version": "1.0",
            "session_id": session_id,
            "task_id": task_id,
            "agent_id": agent_id,
            "provider": decision.provider if decision else None,
            "model": decision.model if decision else None,
            "routing_score": decision.score if decision else None,
            "local": decision.local if decision else None,
            "prompt_version": prompt_version,
            "budget": task["budget"],
            "parent_session_id": parent_session_id,
            "attempt": int(task.get("attempt", 0)) + 1,
            "capability_sha256": _digest(token),
            "status": "active",
            "created_at": utc_now(),
            "heartbeat_at": utc_now(),
            "heartbeat_progress": 0.0,
            "checkpoint": task.get("progress", {}).get("summary", ""),
            "context_usage": 0.0,
            "used_at": None,
        },
    )
    evidence = [f"session_id={session_id}", f"prompt_version={prompt_version}"]
    if decision:
        evidence.extend(
            [f"provider={decision.provider}", f"model={decision.model}", f"routing_score={decision.score}"]
        )
    store.create(
        "orchestrator",
        HandoffKind.AUDIT,
        {
            "event": "session_issued",
            "actor": "orchestrator",
            "target_id": task_id,
            "evidence": evidence,
            "masked": True,
            "budget": task["budget"],
        },
        project_id=task["project_id"],
    )
    return session_id, token


def touch_heartbeat(
    store: HandoffStore,
    session_id: str,
    *,
    progress: float,
    checkpoint: str,
    context_usage: float = 0.0,
) -> None:
    if not 0 <= progress <= 1 or not 0 <= context_usage <= 1:
        raise ValueError("heartbeat progress and context usage must be between 0 and 1")
    path = store.control / "sessions" / f"{session_id}.yaml"
    session = store.read(path)
    if session.get("status") != "active":
        raise ValueError("cannot heartbeat inactive session")
    session["heartbeat_at"] = utc_now()
    session["heartbeat_progress"] = progress
    session["checkpoint"] = checkpoint
    session["context_usage"] = context_usage
    store.atomic_write(path, session)


def heartbeat_expired(session: dict, timeout_seconds: int, *, now: datetime | None = None) -> bool:
    if session.get("status") != "active":
        return False
    timestamp = str(session.get("heartbeat_at") or session.get("created_at"))
    heartbeat = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    current = now or datetime.now(UTC)
    return (current - heartbeat).total_seconds() > timeout_seconds


def rollover_session(
    store: HandoffStore,
    session_id: str,
    task_id: str,
    token: str,
    *,
    threshold: float,
) -> tuple[str, str] | None:
    session = verify_capability(store, session_id, task_id, token)
    usage = float(session.get("context_usage", 0.0))
    if usage < threshold:
        return None
    task = store.read(store.find(task_id, HandoffKind.TASK))
    progress = task.get("progress", {})
    required = ("completed", "remaining", "next_action")
    if any(key not in progress for key in required) or not str(progress.get("next_action", "")).strip():
        raise ValueError("task progress is incomplete for rollover")
    from aipf.routing import RoutingDecision

    decision = RoutingDecision(
        provider=str(session["provider"]), model=str(session["model"]),
        score=float(session["routing_score"]), local=bool(session.get("local", False)),
    )
    consume_capability(store, session)
    return issue_session(
        store, task_id, str(session["agent_id"]), decision=decision,
        prompt_version=str(session["prompt_version"]), parent_session_id=session_id,
    )


def verify_capability(
    store: HandoffStore, session_id: str, task_id: str, token: str
) -> dict:
    path = store.control / "sessions" / f"{session_id}.yaml"
    if not path.exists():
        raise PermissionError("unknown session")
    with path.open(encoding="utf-8") as stream:
        session = yaml.safe_load(stream)
    if session.get("status") != "active":
        raise PermissionError("session capability is not active")
    if session.get("task_id") != task_id:
        raise PermissionError("session does not own task")
    if not secrets.compare_digest(str(session.get("capability_sha256")), _digest(token)):
        raise PermissionError("invalid capability token")
    return session


def consume_capability(store: HandoffStore, session: dict) -> None:
    session["status"] = "used"
    session["used_at"] = utc_now()
    path = store.control / "sessions" / f"{session['session_id']}.yaml"
    store.atomic_write(path, session)
