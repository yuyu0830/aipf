from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from aipf.config import load_config
from aipf.security import redact
from aipf.store import ProjectStore


SUPPORTED_EVENTS = {"task_completed", "plan_completed", "blocked"}


@dataclass(frozen=True, slots=True)
class NotificationResult:
    status: str
    error: str | None = None


def notification_events(store: ProjectStore) -> set[str]:
    project_path = store.root / "PROJECT.md"
    if project_path.exists():
        pattern = r"(?ms)^## Telegram 알림 설정\s*$.*?^- 전송 조건:\s*([^\n]*)"
        match = re.search(pattern, project_path.read_text(encoding="utf-8"))
        if match:
            configured = {item.strip() for item in match.group(1).split(",") if item.strip()}
            return set() if "never" in configured else configured & SUPPORTED_EVENTS
    configured = set(load_config(store.config_path)["notifications"]["events"])
    return set() if "never" in configured else configured & SUPPORTED_EVENTS


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
    try:
        with (opener or urlopen)(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict) or not payload.get("ok"):
            return NotificationResult("failed", "Telegram API rejected request")
        return NotificationResult("sent")
    except HTTPError as exc:
        return NotificationResult("failed", f"Telegram HTTP {exc.code}")
    except (TimeoutError, URLError, UnicodeDecodeError, json.JSONDecodeError):
        return NotificationResult("failed", "Telegram network or response error")


def notify(store: ProjectStore, event: str, subject: str, summary: str) -> NotificationResult:
    if event not in SUPPORTED_EVENTS:
        raise ValueError(f"unknown notification event: {event}")
    if event not in notification_events(store):
        return NotificationResult("skipped")
    config = load_config(store.config_path)
    runtime = store.read(store.runtime_path)
    message = "\n".join(
        [
            str(runtime["goal"]),
            f"Event: {event}",
            f"Target: {subject}",
            f"Summary: {summary}",
            "Next: check PROJECT.md",
        ]
    )
    timeout = int(config["notifications"]["timeout_seconds"])
    return send_telegram(redact(message), timeout=timeout)
