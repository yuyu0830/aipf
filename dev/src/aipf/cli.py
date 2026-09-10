from __future__ import annotations

import argparse
import sys
from importlib.resources import files
from pathlib import Path

from aipf.config import load_config, write_default_config
from aipf.gitops import create_checkpoint, restore_checkpoint
from aipf.models import Kind, ProjectState, TaskStatus
from aipf.notifications import (
    notify,
    notification_events,
    send_review_request,
    telegram_credentials,
    telegram_review_key,
    wait_for_review,
)
from aipf.projector import write_project, write_project_flow
from aipf.runtime import active_task_ids, set_active_task_ids
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
    for name in ("PROJECT_SPEC.md", "CODE_CONVENTIONS.md"):
        target = root / "guidance" / name
        if not target.exists():
            target.write_text(templates.joinpath(name).read_text(encoding="utf-8"), encoding="utf-8")


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
        "updated_at": utc_now(),
    }
    set_active_task_ids(runtime, [])
    store.write(store.runtime_path, runtime)
    refresh(store, runtime)
    print(f"initialized: {root}")
    return 0


def command_plan_apply(args: argparse.Namespace) -> int:
    store = ProjectStore(project_root(args.directory))
    runtime = read_runtime(store)
    validate_project_spec(store.root / "guidance" / "PROJECT_SPEC.md")
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
    if runtime["state"] in {
        ProjectState.AWAITING_PLAN,
        ProjectState.AWAITING_PLAN_CONFIRMATION,
        ProjectState.AWAITING_PLAN_COMPLETION_CONFIRMATION,
    }:
        if runtime["state"] == ProjectState.AWAITING_PLAN_COMPLETION_CONFIRMATION:
            print("waiting for Plan completion confirmation")
        else:
            print("waiting for plan approval")
        return 3
    if runtime["state"] == ProjectState.AWAITING_PLAN_TASK_REVIEW:
        print("waiting for Plan-agent task review")
        return 3
    if runtime["state"] == ProjectState.AWAITING_TASK_CONFIRMATION:
        print("waiting for task review")
        return 3
    plan = store.read_object(Kind.PLAN, runtime["active_plan_id"])
    tasks = [store.read_object(Kind.TASK, task_id) for task_id in plan["task_ids"]]
    by_id = {task["id"]: task for task in tasks}
    active_ids = active_task_ids(runtime)
    requested_ids = list(dict.fromkeys(getattr(args, "task", None) or []))
    if requested_ids:
        unknown = [task_id for task_id in requested_ids if task_id not in by_id]
        if unknown:
            raise ValueError("task is not in the active plan: " + ", ".join(unknown))
        not_ready = [
            task_id for task_id in requested_ids
            if by_id[task_id]["status"] not in {TaskStatus.PENDING, TaskStatus.READY}
        ]
        if not_ready:
            raise RuntimeError("task is not ready: " + ", ".join(not_ready))
    else:
        requested_ids = [
            task["id"] for task in tasks
            if task["status"] in {TaskStatus.PENDING, TaskStatus.READY}
            and task["id"] not in active_ids
        ][:1]
    if not requested_ids:
        print("no task ready")
        return 0

    missing_by_task = {
        task_id: [value for value in by_id[task_id]["references"] if not (store.root / value).exists()]
        for task_id in requested_ids
    }
    missing_by_task = {task_id: missing for task_id, missing in missing_by_task.items() if missing}
    if missing_by_task:
        for task_id, missing_references in missing_by_task.items():
            task = by_id[task_id]
            task["status"] = TaskStatus.BLOCKED.value
            blocked_summary = "Missing references: " + ", ".join(missing_references)
            task["remaining"] = [blocked_summary]
            task["decisions"] = []
            task["updated_at"] = utc_now()
            validate_task(task)
            store.write(store.path(Kind.TASK, task_id), task)
        set_active_task_ids(runtime, [*active_ids, *missing_by_task])
        runtime.update({"state": ProjectState.BLOCKED.value, "updated_at": utc_now()})
        store.write(store.runtime_path, runtime)
        refresh(store, runtime)
        for task_id, missing_references in missing_by_task.items():
            blocked_summary = "Missing references: " + ", ".join(missing_references)
            notify(store, "blocked", task_id, blocked_summary)
            print(f"{task_id}: {blocked_summary}")
        return 2

    for task_id in requested_ids:
        task = by_id[task_id]
        task["status"] = TaskStatus.RUNNING.value
        task["updated_at"] = utc_now()
        validate_task(task)
        store.write(store.path(Kind.TASK, task_id), task)
    set_active_task_ids(runtime, [*active_ids, *requested_ids])
    runtime.update({"state": ProjectState.RUNNING.value, "updated_at": utc_now()})
    store.write(store.runtime_path, runtime)
    refresh(store, runtime)
    for task_id in requested_ids:
        task = by_id[task_id]
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
    if args.target not in active_task_ids(runtime):
        raise RuntimeError(f"task is not active: {args.target}")
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
    task["review_stage"] = "plan" if getattr(args, "plan_review", False) else "user"
    task["updated_at"] = utc_now()
    validate_task(task)
    store.write(store.path(Kind.TASK, task["id"]), task)
    current_active_ids = active_task_ids(runtime)
    running_ids = [
        task_id for task_id in current_active_ids
        if task_id != task["id"]
        and store.path(Kind.TASK, task_id).exists()
        and store.read_object(Kind.TASK, task_id)["status"] == TaskStatus.RUNNING
    ]
    review_state = ProjectState.AWAITING_PLAN_TASK_REVIEW if task["review_stage"] == "plan" else ProjectState.AWAITING_TASK_CONFIRMATION
    runtime.update({
        "state": ProjectState.RUNNING.value if running_ids else review_state.value,
        "updated_at": utc_now(),
    })
    set_active_task_ids(runtime, current_active_ids)
    store.write(store.runtime_path, runtime)
    refresh(store, runtime)
    print_task_review_report(task, omitted, store.read_object(Kind.EVIDENCE, evidence_id))
    return 0


def command_task_accept(args: argparse.Namespace) -> int:
    """Record the Plan agent's review before exposing a Task to the user."""
    store = ProjectStore(project_root(args.directory))
    runtime = read_runtime(store)
    task = store.read_object(Kind.TASK, args.target)
    if args.target not in active_task_ids(runtime) or task["status"] != TaskStatus.AWAITING_REVIEW:
        raise RuntimeError(f"task is not awaiting Plan review: {args.target}")
    if task.get("review_stage", "user") != "plan":
        raise RuntimeError(f"task does not require Plan review: {args.target}")

    task["plan_review"] = {"status": "accepted", "timestamp": utc_now()}
    if args.user_review:
        task["review_stage"] = "user"
        task["updated_at"] = utc_now()
        validate_task(task)
        store.write(store.path(Kind.TASK, args.target), task)
        runtime["state"] = _state_for_active_tasks(store, runtime).value
        runtime["updated_at"] = utc_now()
        store.write(store.runtime_path, runtime)
        refresh(store, runtime)
        print(f"Plan review recorded; user review required: {args.target}")
        return 0

    task["review_stage"] = "user"
    task["updated_at"] = utc_now()
    validate_task(task)
    store.write(store.path(Kind.TASK, args.target), task)
    events = _review_task(store, runtime, args.target, "approve", None)
    runtime["updated_at"] = utc_now()
    store.write(store.runtime_path, runtime)
    refresh(store, runtime)
    for event in events:
        notify(store, event, args.target, "Plan agent accepted the Task result")
    print(f"Plan review accepted: {args.target}")
    return 0


def _review_plan(
    store: ProjectStore,
    runtime: dict,
    target: str,
    decision: str,
    feedback: str | None = None,
) -> list[str]:
    plan = store.read_object(Kind.PLAN, target)
    if runtime.get("active_plan_id") != target:
        raise RuntimeError("only the active plan can be reviewed")
    completion_review = runtime.get("state") == ProjectState.AWAITING_PLAN_COMPLETION_CONFIRMATION.value
    expected_status = "approved" if completion_review else "proposed"
    if plan["status"] != expected_status:
        raise RuntimeError(f"only the active {expected_status} plan can be reviewed")
    if decision == "defer":
        return []

    events: list[str] = []
    if completion_review:
        if decision == "approve":
            plan["status"] = "completed"
            runtime["state"] = ProjectState.AWAITING_PLAN.value
            events.append("plan_completed")
        elif decision == "revise":
            # A revised Plan is superseded by the next Plan session. Keep the
            # executed Plan in history as cancelled so project completion can
            # distinguish it from a Plan awaiting final confirmation.
            plan["status"] = "cancelled"
            plan["feedback"] = feedback
            runtime["state"] = ProjectState.AWAITING_PLAN.value
        elif decision == "retry":
            plan["feedback"] = None
            for task_id in plan["task_ids"]:
                task = store.read_object(Kind.TASK, task_id)
                if task["status"] == TaskStatus.COMPLETED.value:
                    task["status"] = TaskStatus.READY.value
                    task["updated_at"] = utc_now()
                    validate_task(task)
                    store.write(store.path(Kind.TASK, task_id), task)
            set_active_task_ids(runtime, [])
            runtime["state"] = ProjectState.READY.value
        elif decision == "cancel":
            plan["status"] = "cancelled"
            runtime["state"] = ProjectState.CANCELLED.value
        else:
            raise ValueError(f"unsupported Plan completion decision: {decision}")
    elif decision == "approve":
        plan["status"] = "approved"
        runtime["state"] = ProjectState.READY.value
    elif decision in {"revise", "retry"}:
        plan["feedback"] = feedback if decision == "revise" else None
        runtime["state"] = ProjectState.AWAITING_PLAN.value
    elif decision == "cancel":
        plan["status"] = "cancelled"
        runtime["state"] = ProjectState.CANCELLED.value
    else:
        raise ValueError(f"unsupported Plan decision: {decision}")
    plan["updated_at"] = utc_now()
    validate_plan(plan)
    store.write(store.path(Kind.PLAN, target), plan)
    return events


def _state_for_active_tasks(store: ProjectStore, runtime: dict) -> ProjectState:
    """Choose the next persisted state from all active parallel Tasks."""
    statuses: list[tuple[str, str]] = []
    for task_id in active_task_ids(runtime):
        path = store.path(Kind.TASK, task_id)
        if not path.exists():
            continue
        task = store.read_object(Kind.TASK, task_id)
        statuses.append((task["status"], task.get("review_stage", "user")))
    if any(status == TaskStatus.RUNNING.value for status, _ in statuses):
        return ProjectState.RUNNING
    if any(status == TaskStatus.AWAITING_REVIEW.value and stage == "plan" for status, stage in statuses):
        return ProjectState.AWAITING_PLAN_TASK_REVIEW
    if any(status == TaskStatus.AWAITING_REVIEW.value for status, _ in statuses):
        return ProjectState.AWAITING_TASK_CONFIRMATION
    return ProjectState.READY


def _review_task(store: ProjectStore, runtime: dict, target: str, decision: str, feedback: str | None) -> list[str]:
    task = store.read_object(Kind.TASK, target)
    if target not in active_task_ids(runtime) or task["status"] != TaskStatus.AWAITING_REVIEW:
        raise RuntimeError("only the active submitted task can be reviewed")
    if task.get("review_stage", "user") == "plan":
        raise RuntimeError("Task requires Plan-agent review before user review")
    events: list[str] = []
    current_active_ids = active_task_ids(runtime)
    if decision == "approve":
        task["status"] = TaskStatus.COMPLETED.value
        remaining_active_ids = [task_id for task_id in current_active_ids if task_id != target]
        set_active_task_ids(runtime, remaining_active_ids)
        plan = store.read_object(Kind.PLAN, runtime["active_plan_id"])
        remaining = [
            store.read_object(Kind.TASK, task_id)
            for task_id in plan["task_ids"]
            if task_id != target and store.read_object(Kind.TASK, task_id)["status"] not in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}
        ]
        if remaining:
            runtime["state"] = _state_for_active_tasks(store, runtime).value
            events.append("task_completed")
        else:
            # Completing the final Task only makes the Plan eligible for
            # completion. The Plan itself requires an explicit confirmation.
            # Refresh the Plan marker so buttons from the initial Plan
            # proposal cannot be replayed as completion decisions.
            plan["updated_at"] = utc_now()
            validate_plan(plan)
            store.write(store.path(Kind.PLAN, plan["id"]), plan)
            runtime["state"] = ProjectState.AWAITING_PLAN_COMPLETION_CONFIRMATION.value
            events.append("task_completed")
    elif decision in {"revise", "retry"}:
        task["status"] = TaskStatus.READY.value
        task["feedback"] = feedback if decision == "revise" else None
        set_active_task_ids(runtime, [task_id for task_id in current_active_ids if task_id != target])
        runtime["state"] = _state_for_active_tasks(store, runtime).value
    elif decision == "cancel":
        task["status"] = TaskStatus.CANCELLED.value
        set_active_task_ids(runtime, [task_id for task_id in current_active_ids if task_id != target])
        runtime["state"] = ProjectState.CANCELLED.value
    elif decision == "defer":
        return []
    else:
        raise ValueError(f"unsupported Task decision: {decision}")
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
        events = _review_plan(store, runtime, args.target, args.decision, args.feedback)
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


def _telegram_review_target(store: ProjectStore, runtime: dict) -> tuple[str, str, str]:
    """Return the currently reviewable target and a concise Telegram prompt."""
    state = runtime.get("state")
    if state in {
        ProjectState.AWAITING_PLAN_CONFIRMATION.value,
        ProjectState.AWAITING_PLAN_COMPLETION_CONFIRMATION.value,
    }:
        target = runtime.get("active_plan_id")
        if not isinstance(target, str):
            raise RuntimeError("Telegram review requires an active plan")
        plan = store.read_object(Kind.PLAN, target)
        completion_review = state == ProjectState.AWAITING_PLAN_COMPLETION_CONFIRMATION.value
        expected_status = "approved" if completion_review else "proposed"
        if plan.get("status") != expected_status:
            raise RuntimeError(f"Telegram review requires an {expected_status} active plan")
        tasks = [store.read_object(Kind.TASK, task_id) for task_id in plan["task_ids"]]
        task_lines = "\n".join(f"{task['id']}: {task['goal']}" for task in tasks)
        title = "Plan 완료 확인 필요" if completion_review else "Plan 승인 필요"
        # The final Task acceptance refreshes updated_at, invalidating buttons
        # from the initial Plan proposal while keeping the original key shape.
        return target, telegram_review_key(target, str(plan["updated_at"])), "\n".join([
            f"Plan {target} {title}",
            f"목표: {plan['goal']}",
            f"Roadmap: {plan['roadmap_stage']}",
            "Tasks:",
            task_lines or "없음",
        ])
    if state in {ProjectState.RUNNING.value, ProjectState.AWAITING_TASK_CONFIRMATION.value}:
        review_targets = [
            task_id for task_id in active_task_ids(runtime)
            if store.path(Kind.TASK, task_id).exists()
            and store.read_object(Kind.TASK, task_id).get("status") == TaskStatus.AWAITING_REVIEW
            and store.read_object(Kind.TASK, task_id).get("review_stage", "user") == "user"
        ]
        target = review_targets[0] if review_targets else runtime.get("active_task_id")
        if not isinstance(target, str):
            raise RuntimeError("Telegram review requires an active task")
        task = store.read_object(Kind.TASK, target)
        if task.get("plan_id") != runtime.get("active_plan_id"):
            raise RuntimeError("Telegram review task is not in the active plan")
        if task.get("status") != TaskStatus.AWAITING_REVIEW:
            raise RuntimeError("Telegram review requires a submitted active task")
        if task.get("review_stage", "user") != "user":
            raise RuntimeError("Telegram review requires Plan-agent acceptance first")
        evidence_ids = task.get("evidence_ids") or []
        evidence = store.read_object(Kind.EVIDENCE, evidence_ids[-1]) if evidence_ids else None
        summary = evidence.get("summary", "") if evidence else ""
        return target, telegram_review_key(target, str(evidence_ids[-1])), "\n".join([
            f"Task {target} 승인 필요",
            f"목표: {task['goal']}",
            f"결과: {summary}",
        ])
    raise RuntimeError("Telegram wait is allowed only during plan or task approval")


def _persist_review_decision(
    store: ProjectStore,
    runtime: dict,
    target: str,
    decision: str,
    feedback: str | None,
) -> None:
    if target.startswith("P_"):
        events = _review_plan(store, runtime, target, decision, feedback)
    elif target.startswith("T_"):
        events = _review_task(store, runtime, target, decision, feedback)
    else:
        raise ValueError("review target must be a plan or task id")
    runtime["updated_at"] = utc_now()
    store.write(store.runtime_path, runtime)
    refresh(store, runtime)
    summary = feedback or f"User selected {decision}"
    for event in events:
        notify(store, event, target, summary)


def _validate_telegram_target(store: ProjectStore, runtime: dict, target: str) -> None:
    """Re-read and validate every local field before applying a remote decision."""
    current_target, _, _ = _telegram_review_target(store, runtime)
    if current_target != target:
        raise RuntimeError("Telegram review target is stale")
    if target.startswith("P_"):
        plan = store.read_object(Kind.PLAN, target)
        expected_status = (
            "approved"
            if runtime.get("state") == ProjectState.AWAITING_PLAN_COMPLETION_CONFIRMATION.value
            else "proposed"
        )
        if plan.get("status") != expected_status:
            raise RuntimeError(f"Telegram plan review target is no longer {expected_status}")
    else:
        task = store.read_object(Kind.TASK, target)
        if task.get("plan_id") != runtime.get("active_plan_id"):
            raise RuntimeError("Telegram task review target is not in the active plan")
        if task.get("status") != TaskStatus.AWAITING_REVIEW:
            raise RuntimeError("Telegram task review target is no longer awaiting review")


def command_telegram_wait(args: argparse.Namespace) -> int:
    if args.timeout < 1:
        raise ValueError("Telegram wait timeout must be a positive integer")
    store = ProjectStore(project_root(args.directory))
    runtime = read_runtime(store)
    target, review_key, prompt = _telegram_review_target(store, runtime)
    review_event = "plan_review_required" if target.startswith("P_") else "task_review_required"
    if review_event not in notification_events(store):
        raise RuntimeError(f"Telegram transmission condition is disabled: {review_event}")
    token, chat_id, user_id = telegram_credentials()
    config = load_config(store.config_path)
    send_result = send_review_request(
        prompt,
        target,
        review_key,
        timeout=int(config["notifications"]["timeout_seconds"]),
    )
    if send_result.status != "sent":
        raise RuntimeError(send_result.error or "Telegram review request was not sent")
    result = wait_for_review(
        target=target,
        token=token,
        chat_id=chat_id,
        user_id=user_id,
        review_key=review_key,
        timeout=args.timeout,
    )
    if result.status == "timeout":
        print(f"Telegram wait timed out after {args.timeout} seconds")
        return 3
    if result.status == "deferred":
        print(f"Telegram review deferred: {target}")
        return 0
    if result.status != "decision" or result.decision is None:
        raise RuntimeError("Telegram did not return a review decision")
    runtime = read_runtime(store)
    _validate_telegram_target(store, runtime, target)
    if result.decision == "revise" and not result.feedback:
        raise RuntimeError("Telegram revise decision requires feedback")
    _persist_review_decision(store, runtime, target, result.decision, result.feedback)
    print(f"review recorded: {result.decision} {target}")
    return 0


def command_status(args: argparse.Namespace) -> int:
    store = ProjectStore(project_root(args.directory))
    runtime = read_runtime(store)
    refresh(store, runtime)
    print(f"state: {runtime['state']}")
    print(f"plan: {runtime['active_plan_id'] or 'none'}")
    task_ids = active_task_ids(runtime)
    print(f"task: {runtime.get('active_task_id') or 'none'}")
    print(f"tasks: {', '.join(task_ids) or 'none'}")
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
        "updated_at": utc_now(),
    })
    set_active_task_ids(runtime, [])
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

    run = commands.add_parser("run")
    run.add_argument("--task", action="append", help="start one or more ready tasks together")
    run.set_defaults(handler=command_run)
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
    submit.add_argument(
        "--plan-review",
        action="store_true",
        help="hold the submitted result for Plan-agent review before user review",
    )
    submit.set_defaults(handler=command_task_submit)
    accept = task_commands.add_parser("accept")
    accept.add_argument("--target", required=True)
    accept.add_argument(
        "--user-review",
        action="store_true",
        help="expose the Plan-accepted result for optional user review",
    )
    accept.set_defaults(handler=command_task_accept)

    review = commands.add_parser("review")
    review.add_argument("decision", choices=("approve", "revise", "retry", "cancel", "defer"))
    review.add_argument("--target", required=True)
    review.add_argument("--feedback")
    review.add_argument("--audit-summary")
    review.set_defaults(handler=command_review)

    telegram = commands.add_parser("telegram")
    telegram_commands = telegram.add_subparsers(dest="telegram_command", required=True)
    wait = telegram_commands.add_parser("wait")
    wait.add_argument("--timeout", type=int, default=600)
    wait.set_defaults(handler=command_telegram_wait)
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
