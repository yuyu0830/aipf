from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from aipf.models import Kind, TaskStatus
from aipf.store import ProjectStore


def _line(value: Any) -> str:
    return str(value).replace("\n", " ").strip()


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
    if state == "awaiting_plan_confirmation":
        next_action = f"Plan `{runtime['active_plan_id']}` 검토 후 승인 또는 수정"
    elif state == "awaiting_task_confirmation":
        next_action = f"Task `{runtime['active_task_id']}` 결과 검토 후 approve, revise, retry, cancel 중 선택"
    elif state == "ready":
        next_action = "`aipf run`으로 다음 task 시작"
    elif state == "completed":
        next_action = "프로젝트 완료 결과 확인"
    elif state == "blocked":
        next_action = "차단 원인 확인 후 사용자 결정"
    else:
        next_action = "사용자와 plan 합의"

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
    return "task_completed, plan_completed, blocked"


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
