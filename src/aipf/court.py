from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from aipf.models import HandoffKind, Risk, Status, Verdict
from aipf.security import resolve_inside
from aipf.state import validate_transition
from aipf.store import HandoffStore, utc_now


RISK_ORDER = {Risk.LOW: 0, Risk.MEDIUM: 1, Risk.HIGH: 2, Risk.CRITICAL: 3}


@dataclass(frozen=True, slots=True)
class CourtPolicy:
    critics: int = 2
    defenders: int = 2
    judges: int = 1
    max_rounds: int = 3

    def __post_init__(self) -> None:
        if (self.critics, self.defenders, self.judges) != (2, 2, 1):
            raise ValueError("court requires 2 critics, 2 defenders, and 1 judge")
        if self.max_rounds < 1:
            raise ValueError("max_rounds must be positive")


@dataclass(frozen=True, slots=True)
class CourtResult:
    case_id: str
    verdict: Verdict
    action: str
    improvement_task_id: str | None = None


class CourtEvaluator(Protocol):
    def __call__(self, role: str, session_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...


def effective_risk(task: dict[str, Any]) -> Risk:
    declared = Risk(task.get("risk", Risk.LOW))
    markers = " ".join(
        [*(str(item).lower() for item in task.get("tags", [])),
         *(str(item).lower() for item in task.get("constraints", [])),
         *(str(item).lower() for item in task.get("resources", []))]
    )
    writes_code = any(str(path) == "src" or str(path).startswith(("src/", "src\\")) for path in task.get("write_set", []))
    public_interface = "public_interface" in markers or "public interface" in markers
    security_related = "security" in markers or "secret" in markers or "credential" in markers
    inferred = Risk.MEDIUM if writes_code or public_interface or security_related else Risk.LOW
    return declared if RISK_ORDER[declared] >= RISK_ORDER[inferred] else inferred


def requires_court(risk: Risk | str, *, medium_uses_court: bool = False) -> bool:
    value = Risk(risk)
    return value in {Risk.HIGH, Risk.CRITICAL} or (value == Risk.MEDIUM and medium_uses_court)


def next_court_action(verdict: Verdict | str, round_number: int, policy: CourtPolicy) -> str:
    decision = Verdict(verdict)
    if decision == Verdict.APPROVED:
        return "complete"
    if decision == Verdict.USER_DECISION_REQUIRED:
        return "ask_user"
    if round_number >= policy.max_rounds:
        return "ask_user"
    return "create_improvement_task"


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(store: HandoffStore, task_path: Path, task: dict[str, Any]) -> dict[str, Any]:
    artifacts = []
    for item in task.get("result", {}).get("artifacts", []):
        path = resolve_inside(store.root, item)
        if path.is_file():
            artifacts.append({"path": str(path.relative_to(store.root)), "sha256": _checksum(path)})
    return {
        "task_path": str(task_path.relative_to(store.root)),
        "task_sha256": _checksum(task_path),
        "artifacts": artifacts,
        "acceptance_criteria": task["acceptance_criteria"],
        "constraints": task["constraints"],
        "verification_evidence": task["result"]["evidence"],
    }


def _evaluate(
    evaluator: CourtEvaluator,
    case_dir: Path,
    role: str,
    ordinal: int,
    payload: dict[str, Any],
    store: HandoffStore,
) -> dict[str, Any]:
    session_id = f"CSESSION_{uuid.uuid4().hex[:12]}"
    response = evaluator(role, session_id, payload)
    if not isinstance(response, dict):
        raise ValueError(f"{role} response must be an object")
    if role == "critic" and not isinstance(response.get("claims"), list):
        raise ValueError("critic response requires claims")
    if role == "defender" and not isinstance(response.get("responses"), list):
        raise ValueError("defender response requires responses")
    record = {"role": role, "ordinal": ordinal, "session_id": session_id, "response": response}
    store.atomic_write(case_dir / f"{role}-{ordinal}.yaml", record)
    return record


def _improvement_body(task: dict[str, Any], verdict: Verdict, claims: list[dict[str, Any]]) -> dict[str, Any]:
    descriptions = [str(claim.get("description", "")) for claim in claims if claim.get("description")]
    return {
        "parent_ids": [task["id"]],
        "tags": [*task.get("tags", []), "court-improvement"],
        "goal": f"Improve {task['id']} after court verdict {verdict.value}",
        "scope": task["scope"],
        "inputs": [*task["inputs"], *descriptions],
        "outputs": task["outputs"],
        "constraints": task["constraints"],
        "acceptance_criteria": task["acceptance_criteria"],
        "verification": task["verification"],
        "dependencies": [],
        "read_set": task["read_set"],
        "write_set": task["write_set"],
        "resources": task["resources"],
        "risk": task["risk"],
        "budget": task["budget"],
        "attempt": 0,
        "max_retries": task["max_retries"],
        "progress": {"summary": "court improvement required", "completed": [], "remaining": descriptions or ["address verdict"], "next_action": "address court claims"},
        "result": {"outcome": None, "artifacts": [], "evidence": []},
        "blocker": None,
    }


def _set_runtime_state(store: HandoffStore, state: str) -> None:
    path = store.control / "runtime.yaml"
    if not path.exists():
        return
    runtime = store.read(path)
    runtime["state"] = state
    runtime["updated_at"] = utc_now()
    store.atomic_write(path, runtime)


def run_court_review(
    store: HandoffStore,
    task_id: str,
    evaluator: CourtEvaluator,
    *,
    round_number: int = 1,
    policy: CourtPolicy = CourtPolicy(),
) -> CourtResult:
    task_path = store.find(task_id, HandoffKind.TASK)
    task = store.read(task_path)
    if task["status"] != Status.REVIEW.value:
        raise ValueError("court review requires task in review")
    case_id = f"CASE_{uuid.uuid4().hex[:12]}"
    case_dir = store.control / "court" / case_id
    evidence = _snapshot(store, task_path, task)
    manifest = {
        "case_id": case_id, "task_id": task_id, "round": round_number,
        "risk": effective_risk(task).value, "created_at": utc_now(), "evidence": evidence,
        "composition": {"critics": 2, "defenders": 2, "judges": 1},
    }
    store.atomic_write(case_dir / "manifest.yaml", manifest)
    base_payload = {
        "task": {key: task[key] for key in ("id", "goal", "scope", "constraints", "acceptance_criteria", "result")},
        "evidence": evidence,
    }
    critics = [_evaluate(evaluator, case_dir, "critic", index, base_payload, store) for index in (1, 2)]
    public_claims = [record["response"] for record in critics]
    defense_payload = {**base_payload, "critic_claims": public_claims}
    defenders = [_evaluate(evaluator, case_dir, "defender", index, defense_payload, store) for index in (1, 2)]
    judge_payload = {
        **base_payload,
        "critic_claims": public_claims,
        "defenses": [record["response"] for record in defenders],
        "allowed_verdicts": [item.value for item in Verdict],
    }
    judge = _evaluate(evaluator, case_dir, "judge", 1, judge_payload, store)
    verdict = Verdict(judge["response"].get("verdict"))
    reason = str(judge["response"].get("reason", "court judgment"))
    action = next_court_action(verdict, round_number, policy)
    improvement_task_id = None

    store.create(
        "orchestrator", HandoffKind.DECISION,
        {
            "question": f"Court verdict for {task_id}", "options": [item.value for item in Verdict],
            "selection": verdict.value, "rationale": reason, "impact": task_id,
            "decided_by": judge["session_id"], "decided_at": utc_now(),
        },
        project_id=task["project_id"], status=Status.COMPLETED,
    )
    task.setdefault("review", {}).update({"case_id": case_id, "round": round_number, "verdict": verdict.value, "reason": reason})
    if action == "complete":
        validate_transition(task["status"], Status.COMPLETED)
        task["status"] = Status.COMPLETED.value
        runtime_state = "awaiting_task_confirmation"
    elif action == "create_improvement_task":
        claims = [claim for response in public_claims for claim in response.get("claims", [])]
        improvement_path = store.create(
            task["agent_id"], HandoffKind.TASK, _improvement_body(task, verdict, claims),
            project_id=task["project_id"], status=Status.READY,
        )
        improvement_task_id = improvement_path.stem
        validate_transition(task["status"], Status.BLOCKED)
        task["status"] = Status.BLOCKED.value
        task["blocker"] = f"court improvement task {improvement_task_id}"
        runtime_state = "ready"
    else:
        validate_transition(task["status"], Status.BLOCKED)
        task["status"] = Status.BLOCKED.value
        task["blocker"] = "court requires user decision"
        runtime_state = "blocked"
    store.update(task_path, task)
    _set_runtime_state(store, runtime_state)
    store.atomic_write(
        case_dir / "verdict.yaml",
        {"verdict": verdict.value, "reason": reason, "action": action, "improvement_task_id": improvement_task_id},
    )
    store.create(
        "orchestrator", HandoffKind.AUDIT,
        {"event": "court_decided", "actor": judge["session_id"], "target_id": task_id,
         "evidence": [f"case_id={case_id}", f"verdict={verdict.value}", f"action={action}"], "masked": True},
        project_id=task["project_id"], status=Status.COMPLETED,
    )
    return CourtResult(case_id, verdict, action, improvement_task_id)
