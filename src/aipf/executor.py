from __future__ import annotations

import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aipf.completion import report_task_failure, submit_task
from aipf.config import load_config
from aipf.models import HandoffKind, Status, TaskView
from aipf.policy import PolicyEngine, recorded_approvals
from aipf.providers import default_registry
from aipf.routing import (
    RoutingDecision,
    RoutingRequirements,
    build_agent_request,
    candidates_from_config,
    select_model,
)
from aipf.scheduler import ready_batches
from aipf.security import redact
from aipf.session import heartbeat_expired, issue_session, rollover_session, touch_heartbeat
from aipf.state import validate_transition
from aipf.store import HandoffStore


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    task_id: str
    returncode: int
    session_id: str
    stdout: str
    stderr: str


class BudgetExceededError(RuntimeError):
    pass


def _requirements(task: TaskView) -> RoutingRequirements:
    constraints = {str(value).lower() for value in task.raw.get("constraints", [])}
    tags = {str(value).lower() for value in task.raw.get("tags", [])}
    return RoutingRequirements(
        sensitive="sensitive" in tags,
        external_allowed="external_transfer_forbidden" not in constraints,
        minimum_context_tokens=int(task.raw.get("minimum_context_tokens", 0)),
        tools_required=bool(task.raw.get("tools_required", False)),
    )


def _prepare_task(store: HandoffStore, task: TaskView, config: dict[str, Any]) -> tuple[str, str]:
    decision = select_model(candidates_from_config(config), config["routing"]["weights"], _requirements(task))
    policy = PolicyEngine(config, recorded_approvals(store, task.id))
    if decision.provider != "mock":
        policy.authorize_network()
    if not decision.local:
        policy.authorize_external_transfer()
    document = store.read(task.path)  # type: ignore[arg-type]
    validate_transition(document["status"], Status.RUNNING)
    document["status"] = Status.RUNNING.value
    store.update(task.path, document)  # type: ignore[arg-type]
    return issue_session(store, task.id, task.agent_id, decision=decision, prompt_version="worker-v1")


def _run_process(root: Path, task: TaskView, session_id: str, token: str) -> ExecutionResult:
    env = os.environ.copy()
    env["AIPF_CAPABILITY_TOKEN"] = token
    env["AIPF_PROJECT_ROOT"] = str(root)
    timeout = int(task.raw["budget"]["timeout_seconds"])
    command = [
        sys.executable, "-m", "aipf.cli", "--directory", str(root),
        "_execute-task", "--task", task.id, "--session", session_id,
    ]
    try:
        completed = subprocess.run(
            command,
            env=env,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=False,
        )
        return ExecutionResult(task.id, completed.returncode, session_id, redact(completed.stdout), redact(completed.stderr))
    except subprocess.TimeoutExpired as exc:
        stdout = redact(exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = redact(exc.stderr or "") if isinstance(exc.stderr, str) else ""
        return ExecutionResult(task.id, 124, session_id, stdout, stderr or f"timeout after {timeout}s")


def _record_process_audit(store: HandoffStore, task: TaskView, result: ExecutionResult) -> None:
    task_document = store.read(task.path)  # type: ignore[arg-type]
    store.create(
        "orchestrator",
        HandoffKind.AUDIT,
        {
            "event": "worker_process_finished",
            "actor": "orchestrator",
            "target_id": task.id,
            "evidence": [
                f"session_id={result.session_id}", f"returncode={result.returncode}",
                f"stdout={result.stdout[:1000]}", f"stderr={result.stderr[:1000]}",
            ],
            "masked": True,
        },
        project_id=task_document["project_id"],
        status=Status.COMPLETED,
    )


def _retry_or_block(store: HandoffStore, task: TaskView, result: ExecutionResult, token: str) -> bool:
    cause = result.stderr.strip() or f"worker exited with code {result.returncode}"
    report_task_failure(
        store, task_id=task.id, session_id=result.session_id, token=token,
        status=Status.BLOCKED, summary="worker execution failed", cause_analysis=cause[:1000],
    )
    path = store.find(task.id, HandoffKind.TASK)
    document = store.read(path)
    if int(document["attempt"]) <= int(document["max_retries"]):
        validate_transition(document["status"], Status.READY)
        document["status"] = Status.READY.value
        document["blocker"] = None
        document["progress"]["next_action"] = "retry worker execution"
        store.update(path, document)
        return True
    return False


def run_ready_tasks(root: Path) -> list[ExecutionResult]:
    store = HandoffStore(root)
    config = load_config(root / ".aipf" / "config.yaml")
    max_concurrency = int(config["execution"]["max_concurrency"])
    results: list[ExecutionResult] = []
    while True:
        batches = ready_batches(store.tasks())
        if not batches:
            break
        for batch in batches:
            for start in range(0, len(batch), max_concurrency):
                group = batch[start : start + max_concurrency]
                prepared = [(task, *_prepare_task(store, task, config)) for task in group]
                with ThreadPoolExecutor(max_workers=len(prepared)) as pool:
                    futures = {
                        pool.submit(_run_process, root, task, session_id, token): (task, token)
                        for task, session_id, token in prepared
                    }
                    for future in as_completed(futures):
                        task, token = futures[future]
                        result = future.result()
                        if result.returncode != 0:
                            _retry_or_block(store, task, result, token)
                        _record_process_audit(store, task, result)
                        results.append(result)
    return sorted(results, key=lambda item: item.task_id)


def recover_stale_tasks(root: Path) -> list[str]:
    store = HandoffStore(root)
    config = load_config(root / ".aipf" / "config.yaml")
    timeout = int(config["execution"]["heartbeat_timeout_seconds"])
    recovered: list[str] = []
    for task in store.tasks():
        if task.status != Status.RUNNING:
            continue
        sessions = []
        for path in sorted((store.control / "sessions").glob("S_*.yaml")):
            session = store.read(path)
            if session.get("task_id") == task.id and session.get("status") == "active":
                sessions.append((path, session))
        if sessions and not heartbeat_expired(sessions[-1][1], timeout):
            continue
        if sessions:
            session_path, session = sessions[-1]
            session["status"] = "expired"
            session["used_at"] = None
            store.atomic_write(session_path, session)
        path = store.find(task.id, HandoffKind.TASK)
        document = store.read(path)
        attempt = int(document.get("attempt", 0)) + 1
        document.setdefault("execution", {}).setdefault("attempts", []).append(
            {
                "attempt": attempt, "session_id": sessions[-1][1]["session_id"] if sessions else None,
                "outcome": "heartbeat_timeout", "summary": "stale worker recovered",
                "evidence": [], "failure_analysis": "heartbeat timeout",
            }
        )
        document["attempt"] = attempt
        validate_transition(document["status"], Status.BLOCKED)
        document["status"] = Status.BLOCKED.value
        document["blocker"] = "heartbeat timeout"
        store.update(path, document)
        if attempt <= int(document["max_retries"]):
            validate_transition(document["status"], Status.READY)
            document["status"] = Status.READY.value
            document["blocker"] = None
            document["progress"]["next_action"] = "retry after heartbeat timeout"
            store.update(path, document)
        else:
            document["blocker"] = "heartbeat timeout after retry limit"
            store.update(path, document)
        recovered.append(task.id)
    return recovered


def execute_assigned_task(root: Path, task_id: str, session_id: str, token: str) -> None:
    store = HandoffStore(root)
    session = store.read(store.control / "sessions" / f"{session_id}.yaml")
    if session.get("task_id") != task_id:
        raise PermissionError("session does not own task")
    task_path = store.find(task_id, HandoffKind.TASK)
    task = store.read(task_path)
    if task["status"] != Status.RUNNING.value:
        raise ValueError("task must be running")
    decision = RoutingDecision(
        provider=str(session["provider"]), model=str(session["model"]),
        score=float(session["routing_score"]), local=bool(session.get("local", False)),
    )
    config = load_config(root / ".aipf" / "config.yaml")
    provider_config = config.get("providers", {}).get(decision.provider, {})
    provider = default_registry().create(decision.provider, provider_config)
    request = build_agent_request(
        task, decision,
        system_prompt="Complete exactly one AIPF task. Return a concise completion summary.",
        prompt_version=str(session["prompt_version"]),
    )
    interval = int(config["execution"]["heartbeat_interval_seconds"])
    stop = threading.Event()

    def heartbeat_loop() -> None:
        while not stop.wait(interval):
            touch_heartbeat(store, session_id, progress=0.5, checkpoint="provider running")

    touch_heartbeat(store, session_id, progress=0.1, checkpoint="provider starting")
    thread = threading.Thread(target=heartbeat_loop, daemon=True)
    thread.start()
    try:
        response = provider.run(request)
    finally:
        stop.set()
        thread.join(timeout=interval + 1)
    budget = task["budget"]
    if response.input_tokens > int(budget["max_input_tokens"]):
        raise BudgetExceededError("input token budget exceeded")
    if response.output_tokens > int(budget["max_output_tokens"]):
        raise BudgetExceededError("output token budget exceeded")
    if response.cost_usd > float(budget["max_cost_usd"]):
        raise BudgetExceededError("cost budget exceeded")
    model_config = next(
        (
            item for item in config["routing"]["models"]
            if item["provider"] == decision.provider and item["model"] == decision.model
        ),
        None,
    )
    context_capacity = int(model_config["context_tokens"]) if model_config else 0
    context_usage = (response.input_tokens + response.output_tokens) / context_capacity if context_capacity else 0.0
    threshold = float(config["context"]["rollover_threshold"])
    if context_usage >= threshold and not session.get("parent_session_id"):
        touch_heartbeat(
            store, session_id, progress=0.8, checkpoint="context rollover",
            context_usage=min(context_usage, 1.0),
        )
        rolled = rollover_session(store, session_id, task_id, token, threshold=threshold)
        if rolled:
            child_session_id, child_token = rolled
            execute_assigned_task(root, task_id, child_session_id, child_token)
            return
    touch_heartbeat(store, session_id, progress=0.9, checkpoint="provider completed")
    summary = redact(response.output.strip())[:1000] or "provider completed task"
    submit_task(
        store, task_id=task_id, session_id=session_id, token=token,
        summary=summary, evidence=[f"provider={decision.provider}", "worker_exit=success"], artifacts=[],
    )
