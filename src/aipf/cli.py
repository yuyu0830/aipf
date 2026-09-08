from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

import yaml

from aipf.config import load_config, write_default_config
from aipf.completion import report_task_failure, submit_task
from aipf.court import CourtPolicy, effective_risk, requires_court, run_court_review
from aipf.models import HandoffKind, Status
from aipf.projector import render_project, write_project
from aipf.scheduler import ready_batches
from aipf.security import redact
from aipf.session import issue_session
from aipf.state import validate_transition
from aipf.store import HandoffStore, utc_now
from aipf.validation import require_valid, validate_store


def project_root(value: str) -> Path:
    return Path(value).resolve()


def runtime_path(root: Path) -> Path:
    return root / ".aipf" / "runtime.yaml"


def read_runtime(root: Path) -> dict:
    path = runtime_path(root)
    if not path.exists():
        raise RuntimeError(f"not an aipf project: {root}; run `aipf init` first")
    with path.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise RuntimeError("invalid runtime.yaml")
    require_valid(value, "runtime")
    return value


def refresh_project(root: Path, store: HandoffStore, runtime: dict) -> None:
    write_project(root / "PROJECT.md", render_project(store, str(runtime["goal"]), runtime))


def command_init(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    root.mkdir(parents=True, exist_ok=True)
    control = root / ".aipf"
    if control.exists() and not args.force:
        raise RuntimeError(f"already initialized: {control}")
    goal = args.goal
    if not goal:
        if not sys.stdin.isatty():
            raise RuntimeError("--goal is required when stdin is not interactive")
        goal = input("프로젝트 목표: ").strip()
    if not goal:
        raise RuntimeError("project goal must not be empty")

    store = HandoffStore(root)
    store.initialize()
    write_default_config(control / "config.yaml")
    runtime = {
        "schema_version": "1.0",
        "project_id": str(uuid.uuid4()),
        "goal": goal,
        "state": "awaiting_plan",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "active_plan_id": None,
        "active_session_id": None,
    }
    store.atomic_write(runtime_path(root), runtime)
    write_agent_scripts(store)
    store.create(
        "orchestrator",
        HandoffKind.PLAN,
        {
            "goal": goal,
            "scope": {"includes": [], "excludes": []},
            "task_ids": [],
            "acceptance_criteria": ["사용자가 plan을 승인한다"],
            "constraints": [],
            "checkpoint": "initial_plan",
        },
        project_id=runtime["project_id"],
    )
    refresh_project(root, store, runtime)
    print(f"initialized: {root}")
    print(f"user interface: {root / 'PROJECT.md'}")
    return 0


def write_agent_scripts(store: HandoffStore) -> None:
    scripts = {
        "complete-task": "_complete-task",
        "report-task": "_report-task",
    }
    for filename, command in scripts.items():
        path = store.control / "bin" / filename
        path.write_text(
            "#!/bin/sh\n"
            'exec python -m aipf.cli --directory "$AIPF_PROJECT_ROOT" '
            f"{command} \"$@\"\n",
            encoding="utf-8",
        )
        path.chmod(0o750)


def command_status(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    runtime = read_runtime(root)
    store = HandoffStore(root)
    refresh_project(root, store, runtime)
    tasks = store.tasks()
    counts: dict[str, int] = {}
    for task in tasks:
        counts[task.status.value] = counts.get(task.status.value, 0) + 1
    print(f"state: {runtime['state']}")
    print(f"goal: {runtime['goal']}")
    print(f"tasks: {len(tasks)} {json.dumps(counts, sort_keys=True)}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    read_runtime(root)
    load_config(root / ".aipf" / "config.yaml")
    errors = validate_store(HandoffStore(root))
    if errors:
        for path, error in errors:
            print(f"{path}: {error}", file=sys.stderr)
        return 1
    print("valid")
    return 0


def find_handoff(store: HandoffStore, handoff_id: str) -> Path:
    matches = [path for path in store.iter_handoffs() if path.stem == handoff_id]
    if not matches:
        raise RuntimeError(f"handoff not found: {handoff_id}")
    if len(matches) > 1:
        raise RuntimeError(f"handoff id is ambiguous; use --agent: {handoff_id}")
    return matches[0]


def command_inspect(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    read_runtime(root)
    store = HandoffStore(root)
    path = find_handoff(store, args.handoff_id)
    print(path.read_text(encoding="utf-8"), end="")
    return 0


def record_user_decision(args: argparse.Namespace, action: str) -> int:
    root = project_root(args.directory)
    runtime = read_runtime(root)
    store = HandoffStore(root)
    body = {
        "question": redact(args.question or action),
        "options": [],
        "selection": redact(args.value),
        "rationale": redact(args.reason or "user CLI input"),
        "impact": redact(args.target or "project"),
        "decided_by": "user",
        "decided_at": utc_now(),
    }
    path = store.create(
        "orchestrator",
        HandoffKind.DECISION,
        body,
        project_id=runtime["project_id"],
        status=Status.COMPLETED,
    )
    store.create(
        "orchestrator",
        HandoffKind.AUDIT,
        {
            "event": f"user_{action}",
            "actor": "user",
            "target_id": body["impact"],
            "evidence": [f"decision_id={path.stem}", f"selection={body['selection']}"],
            "masked": True,
        },
        project_id=runtime["project_id"],
        status=Status.COMPLETED,
    )
    if action == "approve" and args.value == "continue":
        runtime["state"] = "completed" if runtime.get("state") == "awaiting_plan_confirmation" else "ready"
        runtime["updated_at"] = utc_now()
        store.atomic_write(runtime_path(root), runtime)
        refresh_project(root, store, runtime)
    print(f"recorded: {path}")
    return 0


def command_run(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    runtime = read_runtime(root)
    store = HandoffStore(root)
    if runtime.get("state") == "awaiting_task_confirmation":
        print("waiting for user: run `aipf approve continue --target <task-id>`")
        return 3
    batches = ready_batches(store.tasks())
    if not batches:
        if any(task.status in {Status.BLOCKED, Status.FAILED} for task in store.tasks()):
            runtime["state"] = "blocked"
            runtime["updated_at"] = utc_now()
            store.atomic_write(runtime_path(root), runtime)
            refresh_project(root, store, runtime)
            from aipf.notifications import notify_project_event

            blocked_ids = ", ".join(task.id for task in store.tasks() if task.status in {Status.BLOCKED, Status.FAILED})
            notify_project_event(store, "blocked", subject_id=blocked_ids or "project", detail="task blocker requires user decision")
            print("project blocked; inspect task blockers")
            return 1
        print("no ready tasks; create or approve plan tasks")
        return 0
    for index, batch in enumerate(batches, 1):
        print(f"batch {index}: " + ", ".join(task.id for task in batch))
    runtime["state"] = "running"
    runtime["updated_at"] = utc_now()
    store.atomic_write(runtime_path(root), runtime)
    refresh_project(root, store, runtime)
    from aipf.executor import run_ready_tasks

    results = run_ready_tasks(root)
    failed = [task for task in store.tasks() if task.status in {Status.BLOCKED, Status.FAILED}]
    runtime = read_runtime(root)
    runtime["state"] = "blocked" if failed else "ready"
    runtime["updated_at"] = utc_now()
    store.atomic_write(runtime_path(root), runtime)
    refresh_project(root, store, runtime)
    if failed:
        from aipf.notifications import notify_project_event

        notify_project_event(
            store, "blocked", subject_id=", ".join(task.id for task in failed),
            detail="worker retry limit reached",
        )
    for result in results:
        print(f"task {result.task_id}: exit={result.returncode}")
    if failed:
        return 1
    return 0


def command_resume(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    read_runtime(root)
    from aipf.executor import recover_stale_tasks

    recovered = recover_stale_tasks(root)
    if recovered:
        print("recovered: " + ", ".join(recovered))
    return command_run(args)


def command_execute_task(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    read_runtime(root)
    from aipf.executor import execute_assigned_task

    execute_assigned_task(root, args.task, args.session, capability_token())
    print(f"worker completed: {args.task}")
    return 0


def capability_token() -> str:
    token = os.environ.get("AIPF_CAPABILITY_TOKEN", "")
    if not token:
        raise PermissionError("AIPF_CAPABILITY_TOKEN is required")
    return token


def command_issue_session(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    read_runtime(root)
    session_id, token = issue_session(HandoffStore(root), args.task, args.agent)
    print(f"session_id={session_id}")
    print(f"capability_token={token}")
    return 0


def command_complete_task(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    read_runtime(root)
    submit_task(
        HandoffStore(root),
        task_id=args.task,
        session_id=args.session,
        token=capability_token(),
        summary=args.summary,
        evidence=args.evidence,
        artifacts=args.artifact,
    )
    print(f"submitted for review: {args.task}")
    return 0


def command_report_task(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    read_runtime(root)
    report_task_failure(
        HandoffStore(root),
        task_id=args.task,
        session_id=args.session,
        token=capability_token(),
        status=Status(args.status),
        summary=args.summary,
        cause_analysis=args.cause_analysis,
    )
    print(f"reported {args.status}: {args.task}")
    return 0


def command_review_task(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    runtime = read_runtime(root)
    store = HandoffStore(root)
    path = store.find(args.task, HandoffKind.TASK)
    document = store.read(path)
    if args.verdict == "approved":
        config = load_config(root / ".aipf" / "config.yaml")
        if requires_court(effective_risk(document), medium_uses_court=bool(config["review"]["medium_uses_court"])):
            raise RuntimeError(f"court review required for risk {effective_risk(document).value}")
        validate_transition(document["status"], Status.COMPLETED)
        document["status"] = Status.COMPLETED.value
        document.setdefault("review", {})["verdict"] = "approved"
        store.update(path, document)
        runtime["state"] = "awaiting_task_confirmation"
        runtime["updated_at"] = utc_now()
        store.atomic_write(runtime_path(root), runtime)
        refresh_project(root, store, runtime)
        from aipf.notifications import notify_task_completed

        notification = notify_task_completed(store, args.task)
        print(f"telegram: {notification.status}")
        print(f"completed: {args.task}; waiting for user confirmation")
        return 0
    validate_transition(document["status"], Status.RUNNING)
    document["status"] = Status.RUNNING.value
    document.setdefault("review", {})["verdict"] = "changes_required"
    store.update(path, document)
    print(f"changes required: {args.task}")
    return 0


def command_court_review(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    runtime = read_runtime(root)
    store = HandoffStore(root)
    config = load_config(root / ".aipf" / "config.yaml")

    def evaluator(role: str, session_id: str, payload: dict) -> dict:
        if role == "critic":
            return {"claims": [] if args.verdict == "approved" else [{"claim_id": f"CL-{session_id}", "description": args.reason, "severity": "high", "evidence": payload["evidence"]["task_sha256"]}]}
        if role == "defender":
            return {"responses": [{"claim_id": claim.get("claim_id"), "position": "acknowledged"} for group in payload["critic_claims"] for claim in group.get("claims", [])]}
        return {"verdict": args.verdict, "reason": args.reason}

    policy_data = config["review"]["court"]
    policy = CourtPolicy(**policy_data)
    result = run_court_review(store, args.task, evaluator, round_number=args.round, policy=policy)
    runtime = read_runtime(root)
    refresh_project(root, store, runtime)
    if result.action == "complete":
        from aipf.notifications import notify_task_completed

        notification = notify_task_completed(store, args.task)
        print(f"telegram: {notification.status}")
    print(f"court {result.case_id}: {result.verdict.value}; action={result.action}")
    if result.improvement_task_id:
        print(f"improvement task: {result.improvement_task_id}")
    return 0


def command_complete_plan(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    runtime = read_runtime(root)
    store = HandoffStore(root)
    path = store.find(args.plan, HandoffKind.PLAN)
    plan = store.read(path)
    task_states = {task.id: task.status for task in store.tasks()}
    incomplete = [task_id for task_id in plan["task_ids"] if task_states.get(task_id) != Status.COMPLETED]
    if incomplete:
        raise RuntimeError("plan has incomplete tasks: " + ", ".join(incomplete))
    plan["status"] = Status.COMPLETED.value
    store.update(path, plan)
    runtime["state"] = "awaiting_plan_confirmation"
    runtime["updated_at"] = utc_now()
    store.atomic_write(runtime_path(root), runtime)
    refresh_project(root, store, runtime)
    from aipf.notifications import notify_project_event

    notify_project_event(store, "plan_completed", subject_id=args.plan, detail="all plan tasks completed; user confirmation required")
    print(f"plan completed: {args.plan}; waiting for user confirmation")
    return 0


def command_cancel(args: argparse.Namespace) -> int:
    root = project_root(args.directory)
    runtime = read_runtime(root)
    runtime["state"] = "cancelled"
    runtime["updated_at"] = utc_now()
    store = HandoffStore(root)
    store.atomic_write(runtime_path(root), runtime)
    refresh_project(root, store, runtime)
    print("project cancelled")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aipf")
    parser.add_argument("--directory", default=".", help="project root")
    commands = parser.add_subparsers(dest="command", required=True)

    init_parser = commands.add_parser("init")
    init_parser.add_argument("--goal")
    init_parser.add_argument("--force", action="store_true")
    init_parser.set_defaults(handler=command_init)

    commands.add_parser("run").set_defaults(handler=command_run)
    commands.add_parser("resume").set_defaults(handler=command_resume)
    commands.add_parser("status").set_defaults(handler=command_status)
    commands.add_parser("validate").set_defaults(handler=command_validate)
    commands.add_parser("cancel").set_defaults(handler=command_cancel)

    inspect_parser = commands.add_parser("inspect")
    inspect_parser.add_argument("handoff_id")
    inspect_parser.set_defaults(handler=command_inspect)

    for name in ("answer", "approve"):
        child = commands.add_parser(name)
        child.add_argument("value")
        child.add_argument("--question")
        child.add_argument("--reason")
        child.add_argument("--target")
        child.set_defaults(handler=lambda args, action=name: record_user_decision(args, action))

    issue = commands.add_parser("_issue-session", help=argparse.SUPPRESS)
    issue.add_argument("--task", required=True)
    issue.add_argument("--agent", required=True)
    issue.set_defaults(handler=command_issue_session)

    complete = commands.add_parser("_complete-task", help=argparse.SUPPRESS)
    complete.add_argument("--task", required=True)
    complete.add_argument("--session", required=True)
    complete.add_argument("--summary", required=True)
    complete.add_argument("--evidence", action="append", default=[], required=True)
    complete.add_argument("--artifact", action="append", default=[])
    complete.set_defaults(handler=command_complete_task)

    report = commands.add_parser("_report-task", help=argparse.SUPPRESS)
    report.add_argument("--task", required=True)
    report.add_argument("--session", required=True)
    report.add_argument("--status", choices=("blocked", "failed"), required=True)
    report.add_argument("--summary", required=True)
    report.add_argument("--cause-analysis", required=True)
    report.set_defaults(handler=command_report_task)

    review = commands.add_parser("_review-task", help=argparse.SUPPRESS)
    review.add_argument("--task", required=True)
    review.add_argument("--verdict", choices=("approved", "changes_required"), required=True)
    review.set_defaults(handler=command_review_task)

    court_review = commands.add_parser("_court-review", help=argparse.SUPPRESS)
    court_review.add_argument("--task", required=True)
    court_review.add_argument("--verdict", choices=("approved", "changes_required", "rejected", "user_decision_required"), required=True)
    court_review.add_argument("--reason", required=True)
    court_review.add_argument("--round", type=int, default=1)
    court_review.set_defaults(handler=command_court_review)

    complete_plan = commands.add_parser("_complete-plan", help=argparse.SUPPRESS)
    complete_plan.add_argument("--plan", required=True)
    complete_plan.set_defaults(handler=command_complete_plan)

    execute = commands.add_parser("_execute-task", help=argparse.SUPPRESS)
    execute.add_argument("--task", required=True)
    execute.add_argument("--session", required=True)
    execute.set_defaults(handler=command_execute_task)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, RuntimeError, ValueError, PermissionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
