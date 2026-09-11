from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from aipf.models import Kind, TaskStatus
from aipf.runtime import active_task_ids
from aipf.store import ProjectStore


FLOW_FILENAME = "PROJECT_FLOW.md"
FLOW_START = "<!-- AIPF:FLOW START -->"
FLOW_END = "<!-- AIPF:FLOW END -->"


def _line(value: Any) -> str:
    return str(value).replace("\n", " ").strip()


def _mermaid_text(value: Any) -> str:
    """Return text safe for a quoted Mermaid label."""
    value = _line(value).replace("\\", "\\\\")
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _mermaid_label(*parts: Any) -> str:
    return "<br/>".join(_mermaid_text(part) for part in parts if _line(part))


def _flow_node(identifier: str, *label_parts: Any) -> str:
    return f'    {identifier}["{_mermaid_label(*label_parts)}"]'


def _flow_plan_identifier(plan_id: str) -> str:
    return f"plan_{plan_id}"


def _flow_checkpoint_identifier(checkpoint_id: str) -> str:
    return f"checkpoint_{checkpoint_id.replace('-', '_')}"


def _flow_audit_identifier(audit_id: str) -> str:
    return f"audit_{audit_id}"


def render_flow_graph(store: ProjectStore, runtime: dict[str, Any]) -> str:
    """Render the compact, deterministic Plan-flow Mermaid graph.

    Plans and their checkpoint index are the source of checkpoint nodes. Tasks
    and Evidence are intentionally only used to resolve an Audit's owning Plan;
    neither appears as a node or an edge label.
    """
    plans = list(store.objects(Kind.PLAN))
    plan_ids = {str(plan.get("id")) for plan in plans}
    plan_nodes = {plan_id: _flow_plan_identifier(plan_id) for plan_id in plan_ids}

    checkpoint_nodes: dict[str, str] = {}
    checkpoints_by_plan: dict[str, list[str]] = {}
    for plan in plans:
        plan_id = str(plan.get("id", ""))
        checkpoint_ids: list[str] = []
        for checkpoint in plan.get("checkpoints", []):
            if not isinstance(checkpoint, dict):
                continue
            checkpoint_id = str(checkpoint.get("id", ""))
            if not checkpoint_id or checkpoint_id in checkpoint_nodes:
                continue
            checkpoint_nodes[checkpoint_id] = _flow_checkpoint_identifier(checkpoint_id)
            checkpoint_ids.append(checkpoint_id)
        checkpoints_by_plan[plan_id] = checkpoint_ids

    tasks_by_id: dict[str, dict[str, Any]] = {}
    for task in store.objects(Kind.TASK):
        task_id = str(task.get("id", ""))
        if task_id:
            tasks_by_id[task_id] = task

    audits = list(store.objects(Kind.AUDIT))
    current_node = "current_runtime"
    current_plan_id = runtime.get("active_plan_id")
    runtime_task_ids = active_task_ids(runtime)
    if not current_plan_id:
        for task_id in runtime_task_ids:
            if task_id in tasks_by_id:
                current_plan_id = tasks_by_id[task_id].get("plan_id")
                if current_plan_id:
                    break

    nodes: list[str] = [
        _flow_node(
            current_node,
            "현재 상태",
            runtime.get("state", "unknown"),
            f"Plan: {current_plan_id or '없음'}",
        )
    ]
    for plan in plans:
        plan_id = str(plan.get("id", ""))
        if not plan_id:
            continue
        nodes.append(
            _flow_node(
                plan_nodes[plan_id],
                plan_id,
                plan.get("goal", ""),
                f"status: {plan.get('status', 'unknown')}",
            )
        )
        for checkpoint_id in checkpoints_by_plan.get(plan_id, []):
            nodes.append(_flow_node(checkpoint_nodes[checkpoint_id], checkpoint_id, f"Plan: {plan_id}"))
    for audit in audits:
        audit_id = str(audit.get("id", ""))
        if audit_id:
            nodes.append(
                _flow_node(
                    _flow_audit_identifier(audit_id),
                    audit_id,
                    audit.get("event", ""),
                    audit.get("summary", ""),
                )
            )

    edges: list[str] = []
    seen_edges: set[str] = set()

    def add_edge(source: str, target: str) -> None:
        edge = f"    {source} --> {target}"
        if edge not in seen_edges:
            seen_edges.add(edge)
            edges.append(edge)

    for plan in plans:
        plan_id = str(plan.get("id", ""))
        if plan_id not in plan_nodes:
            continue
        prior_plan_id = plan.get("prior_plan_id")
        if prior_plan_id in plan_nodes:
            add_edge(plan_nodes[prior_plan_id], plan_nodes[plan_id])
        for checkpoint_id in checkpoints_by_plan.get(plan_id, []):
            add_edge(plan_nodes[plan_id], checkpoint_nodes[checkpoint_id])

    for audit in audits:
        audit_id = str(audit.get("id", ""))
        if not audit_id:
            continue
        audit_node = _flow_audit_identifier(audit_id)
        target = str(audit.get("target", ""))
        target_node: str | None = None
        if target in checkpoint_nodes:
            target_node = checkpoint_nodes[target]
        elif target in plan_nodes:
            target_node = plan_nodes[target]
        elif target in tasks_by_id:
            target_plan_id = tasks_by_id[target].get("plan_id")
            if target_plan_id in plan_nodes:
                target_node = plan_nodes[target_plan_id]
        elif target == "project" or target.startswith("P_"):
            # Unknown Plan targets remain project-wide rather than producing a
            # dangling node. A malformed checkpoint target can still resolve to
            # its owning Plan when that Plan is present.
            target_plan_id = target.split("-", 1)[0]
            if target_plan_id in plan_nodes:
                target_node = plan_nodes[target_plan_id]
        if target_node is None:
            target_node = current_node
        if audit.get("event") == "checkpoint_restored" and target in checkpoint_nodes:
            add_edge(checkpoint_nodes[target], audit_node)
        else:
            add_edge(audit_node, target_node)

    if current_plan_id in plan_nodes:
        add_edge(plan_nodes[current_plan_id], current_node)

    return "\n".join(["flowchart LR", *nodes, *edges])


def _new_flow_document(graph: str) -> str:
    return f"# PROJECT FLOW\n\n{FLOW_START}\n```mermaid\n{graph}\n```\n{FLOW_END}\n"


def _replace_flow_region(content: str, graph: str) -> str:
    start_count = content.count(FLOW_START)
    end_count = content.count(FLOW_END)
    if start_count != 1 or end_count != 1:
        raise ValueError(
            f"{FLOW_FILENAME} requires exactly one {FLOW_START} and {FLOW_END} marker"
        )
    start = content.index(FLOW_START) + len(FLOW_START)
    end = content.index(FLOW_END)
    if end < start:
        raise ValueError(f"{FLOW_FILENAME} has invalid flow marker order")
    generated = f"\n```mermaid\n{graph}\n```\n"
    return content[:start] + generated + content[end:]


def _latest_evidence(store: ProjectStore, task: dict[str, Any]) -> dict[str, Any]:
    evidence_ids = task["evidence_ids"]
    if not evidence_ids:
        return {}
    return store.read_object(Kind.EVIDENCE, evidence_ids[-1])


def render_project(store: ProjectStore, runtime: dict[str, Any]) -> str:
    tasks = list(store.objects(Kind.TASK))
    completed = [task for task in tasks if task["status"] == TaskStatus.COMPLETED]
    active = [task for task in tasks if task["status"] in {TaskStatus.READY, TaskStatus.RUNNING, TaskStatus.AWAITING_REVIEW}]
    blocked = [task for task in tasks if task["status"] == TaskStatus.BLOCKED]
    progress = round(100 * len(completed) / len(tasks)) if tasks else 0

    def rows(items: list[dict[str, Any]]) -> str:
        return "\n".join(f"- `{item['id']}` [{item['status']}] {_line(item['goal'])}" for item in items) or "- 없음"

    audits = list(store.objects(Kind.AUDIT))
    audit_rows = "\n".join(
        f"- `{item['id']}` {_line(item['event'])}: {_line(item['summary'])}" for item in audits[-5:]
    ) or "- 없음"
    state = runtime["state"]
    runtime_task_ids = active_task_ids(runtime)
    review_context = "- 없음"
    if state == "awaiting_plan_confirmation":
        plan = store.read_object(Kind.PLAN, runtime["active_plan_id"])
        prior_plan = plan.get("prior_plan_id") or "없음"
        review_context = "\n".join([
            f"- Roadmap 단계: {_line(plan.get('roadmap_stage', '미기록'))}",
            f"- Plan 목표: {_line(plan['goal'])}",
            f"- 직전 Plan: {prior_plan}",
        ])
        next_action = f"Plan `{runtime['active_plan_id']}` 보고 검토 후 승인 또는 수정"
    elif state == "awaiting_plan_completion_confirmation":
        plan = store.read_object(Kind.PLAN, runtime["active_plan_id"])
        review_context = "\n".join([
            f"- Plan: `{runtime['active_plan_id']}`",
            f"- Plan 목표: {_line(plan['goal'])}",
            "- 모든 Task가 Plan 검토를 통과함",
        ])
        next_action = (
            f"Plan `{runtime['active_plan_id']}` 완료 보고 검토 후 "
            "approve, revise, retry, cancel, defer 중 선택"
        )
    elif state in {"awaiting_task_confirmation", "running", "awaiting_plan_task_review"}:
        review_tasks = [
            store.read_object(Kind.TASK, task_id)
            for task_id in runtime_task_ids
            if store.path(Kind.TASK, task_id).exists()
            and store.read_object(Kind.TASK, task_id).get("status") == TaskStatus.AWAITING_REVIEW
        ]
        contexts: list[str] = []
        for task in review_tasks:
            evidence = _latest_evidence(store, task)
            evidence_id = task["evidence_ids"][-1] if task["evidence_ids"] else "없음"
            result_outputs = ", ".join(evidence.get("outputs", [])) or "없음"
            remaining = "; ".join(task["remaining"]) or "없음"
            decisions = "; ".join(task["decisions"]) or "없음"
            contexts.append("\n".join([
                f"- Task: `{task['id']}`",
                f"- Evidence: `{evidence_id}`",
                f"- Task 결과: {_line(evidence.get('summary', ''))}",
                f"- 제출 산출물: {result_outputs}",
                f"- 미완료 사항: {remaining}",
                f"- 사용자 결정 필요: {decisions}",
            ]))
        review_context = "\n\n".join(contexts) or "- 없음"
        plan_review_ids = [
            task["id"] for task in review_tasks if task.get("review_stage", "user") == "plan"
        ]
        user_review_ids = [
            task["id"] for task in review_tasks if task.get("review_stage", "user") == "user"
        ]
        if plan_review_ids:
            next_action = f"Plan 에이전트가 Task 검토: {', '.join(plan_review_ids)}; 검토 후 task accept 실행"
        elif user_review_ids:
            next_action = f"Task 사용자 검토 대기: {', '.join(user_review_ids)}; approve, revise, retry, cancel 중 선택"
        else:
            next_action = "활성 Task 실행 및 결과 제출"
    elif state == "ready":
        next_action = "`aipf run`으로 다음 task 시작"
    elif state == "completed":
        next_action = "프로젝트 완료 결과 확인"
    elif state == "blocked":
        next_action = "차단 원인 확인 후 사용자 결정"
    elif state == "awaiting_plan" and runtime.get("active_plan_id"):
        next_action = (
            f"새 세션에서 `inputs/PROJECT_SPEC.md`와 완료된 Plan `{runtime['active_plan_id']}`을 읽고 "
            "다음 Plan을 합의하거나 프로젝트 완료를 확정"
        )
    else:
        next_action = "초기 설계 세션에서 프로젝트 명세와 전체 진행 계획 합의"

    return f"""# PROJECT

## 목표

{_line(runtime['goal'])}

## 현재 상태

- 실행 상태: {state}
- 진행률: {progress}%
- 전체 task: {len(tasks)}
- 완료 task: {len(completed)}

## 활성 task

{rows(active)}

## 차단 사항

{rows(blocked)}

## 최근 기록

{audit_rows}

## 검토 대기 정보

{review_context}

## 다음 행동

{next_action}

## Telegram 알림 설정

- 전송 조건: {notification_setting(store.root / 'PROJECT.md')}
"""


def notification_setting(path: Path) -> str:
    if path.exists():
        import re
        match = re.search(r"(?m)^- 전송 조건:\s*(.+)$", path.read_text(encoding="utf-8"))
        if match:
            return match.group(1).strip()
    return "plan_review_required, task_review_required, task_completed, plan_completed, blocked"


def write_project(store: ProjectStore, runtime: dict[str, Any]) -> None:
    content = render_project(store, runtime)
    descriptor, temporary = tempfile.mkstemp(prefix=".PROJECT.md.", dir=store.root)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, store.root / "PROJECT.md")
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def render_project_flow(store: ProjectStore, runtime: dict[str, Any]) -> str:
    """Render a new PROJECT_FLOW.md document with the generated flow region."""
    return _new_flow_document(render_flow_graph(store, runtime))


def write_project_flow(store: ProjectStore, runtime: dict[str, Any]) -> None:
    """Refresh only the generated PROJECT_FLOW.md region.

    A user-authored file is preserved outside the exact flow markers. A file
    with missing, duplicate, or reversed markers is rejected before any write.
    """
    path = store.root / FLOW_FILENAME
    graph = render_flow_graph(store, runtime)
    if path.exists():
        content = _replace_flow_region(path.read_text(encoding="utf-8"), graph)
    else:
        content = _new_flow_document(graph)

    descriptor, temporary = tempfile.mkstemp(prefix=f".{FLOW_FILENAME}.", dir=store.root)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
