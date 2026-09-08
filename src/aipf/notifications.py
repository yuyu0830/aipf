from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from aipf.models import HandoffKind, Status
from aipf.security import redact
from aipf.store import HandoffStore


TELEGRAM_EVENTS = frozenset({"task_completed", "plan_completed", "blocked"})
DEFAULT_TELEGRAM_EVENTS = TELEGRAM_EVENTS


@dataclass(frozen=True, slots=True)
class NotificationResult:
    status: str
    error: str | None = None


def notification_events(project_file: Path) -> frozenset[str]:
    if not project_file.exists():
        return DEFAULT_TELEGRAM_EVENTS
    content = project_file.read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^## Telegram 알림 설정\s*$.*?^- 전송 조건:\s*([^\n]*)",
        content,
    )
    if not match:
        return DEFAULT_TELEGRAM_EVENTS
    configured = {item.strip() for item in match.group(1).split(",") if item.strip()}
    if "never" in configured:
        return frozenset()
    return frozenset(configured & TELEGRAM_EVENTS)


def should_notify(store: HandoffStore, event: str) -> bool:
    if event not in TELEGRAM_EVENTS:
        raise ValueError(f"unknown Telegram event: {event}")
    return event in notification_events(store.root / "PROJECT.md")


def send_telegram(
    text: str,
    *,
    environ: Mapping[str, str] | None = None,
    timeout: int = 10,
    opener=None,
) -> NotificationResult:
    values = os.environ if environ is None else environ
    token = values.get("AIPF_TELEGRAM_BOT_TOKEN", "")
    chat_id = values.get("AIPF_TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return NotificationResult("skipped")
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=urlencode({"chat_id": chat_id, "text": text}).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    open_request = opener or urlopen
    try:
        with open_request(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict) or not payload.get("ok"):
            return NotificationResult("failed", "Telegram API rejected request")
        return NotificationResult("sent")
    except HTTPError as exc:
        return NotificationResult("failed", f"Telegram HTTP {exc.code}")
    except (TimeoutError, URLError):
        return NotificationResult("failed", "Telegram network error")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return NotificationResult("failed", "Telegram returned invalid JSON")


def completion_message(store: HandoffStore, task: dict[str, Any]) -> str:
    runtime = store.read(store.control / "runtime.yaml")
    candidates = [
        item for item in store.tasks()
        if item.id != task["id"] and item.status in {Status.READY, Status.PENDING}
    ]
    next_task = candidates[0] if candidates else None
    attempts = task.get("execution", {}).get("attempts", [])
    summary = str(
        (attempts[-1].get("summary") if attempts else None)
        or task.get("progress", {}).get("summary")
        or task.get("result", {}).get("outcome")
        or "completed"
    )
    review = str(task.get("review", {}).get("verdict", "approved"))
    lines = [
        str(runtime["goal"]),
        f"Task: {task['id']} 완료",
        f"요약: {summary}",
        f"검토: {review}",
        "다음 체크포인트: 사용자 task 완료 확인",
    ]
    if next_task:
        lines.extend(
            [
                f"다음 Task: {next_task.id} {next_task.goal}",
                f"다음 수행: {next_task.raw.get('progress', {}).get('next_action') or next_task.goal}",
            ]
        )
    else:
        lines.append("다음 수행: 다음 plan 확인 또는 프로젝트 완료 승인")
    lines.append(f"사용자 행동: aipf approve continue --target {task['id']}")
    return "\n".join(lines)


def notify_task_completed(store: HandoffStore, task_id: str) -> NotificationResult:
    task = store.read(store.find(task_id, HandoffKind.TASK))
    if task["status"] != Status.COMPLETED.value:
        raise ValueError("completion notification requires completed task")
    if not should_notify(store, "task_completed"):
        return NotificationResult("skipped")
    return send_telegram(redact(completion_message(store, task)))


def notify_project_event(store: HandoffStore, event: str, *, subject_id: str, detail: str) -> NotificationResult:
    if not should_notify(store, event):
        return NotificationResult("skipped")
    runtime = store.read(store.control / "runtime.yaml")
    labels = {"plan_completed": "Plan 완료", "blocked": "프로젝트 차단"}
    text = "\n".join(
        [
            str(runtime["goal"]),
            f"이벤트: {labels[event]}",
            f"대상: {subject_id}",
            f"내용: {detail}",
            "다음 수행: PROJECT.md의 다음 체크포인트 확인",
        ]
    )
    return send_telegram(redact(text))
