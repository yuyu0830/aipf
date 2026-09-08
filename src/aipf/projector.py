from __future__ import annotations

import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from aipf.models import HandoffKind, Status
from aipf.notifications import notification_events
from aipf.store import HandoffStore


def _line(value: Any) -> str:
    return str(value).replace("\n", " ").strip()


def render_project(store: HandoffStore, goal: str, runtime: dict[str, Any] | None = None) -> str:
    tasks = store.tasks()
    counts = Counter(task.status for task in tasks)
    completed = counts[Status.COMPLETED]
    progress = round(100 * completed / len(tasks)) if tasks else 0
    active = [task for task in tasks if task.status in {Status.READY, Status.RUNNING, Status.REVIEW}]
    blocked = [task for task in tasks if task.status == Status.BLOCKED]

    def task_rows(values: list) -> str:
        if not values:
            return "- 없음"
        return "\n".join(f"- `{item.id}` [{item.status.value}] {_line(item.goal)}" for item in values)

    decisions = []
    for path in list(store.iter_handoffs(HandoffKind.DECISION))[-3:]:
        item = store.read(path)
        decisions.append(f"- `{item['id']}` {_line(item['selection'])}: {_line(item['rationale'])}")
    reviews = []
    artifacts = []
    for task in tasks:
        review = task.raw.get("review", {})
        if review.get("verdict"):
            reviews.append(f"- `{task.id}` {review['verdict']}: {_line(review.get('reason', ''))}".rstrip())
        for artifact in task.raw.get("result", {}).get("artifacts", []):
            artifacts.append(f"- `{task.id}`: `{_line(artifact)}`")

    state = str((runtime or {}).get("state", "unknown"))
    telegram_events = notification_events(store.root / "PROJECT.md")
    telegram_setting = ", ".join(sorted(telegram_events)) if telegram_events else "never"
    if state == "awaiting_task_confirmation":
        checkpoint = "완료 task 확인 후 `aipf approve continue --target <task-id>` 실행"
    elif state == "awaiting_plan_confirmation":
        checkpoint = "완료 plan 사용자 확인"
    elif blocked:
        checkpoint = "차단 원인 확인 후 `aipf answer`로 결정 기록"
    elif active:
        checkpoint = "활성 task 실행 또는 검토 완료"
    else:
        checkpoint = "새 plan 생성 또는 프로젝트 완료 승인"

    return f"""# PROJECT

## 목표

{goal}

## 현재 상태

- 실행 상태: {state}
- 진행률: {progress}%
- 전체 task: {len(tasks)}
- 완료: {completed}
- 차단: {len(blocked)}

## 활성 task

{task_rows(active)}

## 차단 사항

{task_rows(blocked)}

## 최근 결정

{chr(10).join(decisions) if decisions else "- 없음"}

## 검토 결과

{chr(10).join(reviews[-5:]) if reviews else "- 없음"}

## 산출물

{chr(10).join(artifacts) if artifacts else "- 없음"}

## 다음 체크포인트

{checkpoint}

## Telegram 알림 설정

- 전송 조건: {telegram_setting}
"""


def write_project(path: Path, content: str) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".PROJECT.md.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
