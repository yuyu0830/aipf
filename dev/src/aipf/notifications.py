from __future__ import annotations

import json
import os
import re
from hashlib import sha256
from dataclasses import dataclass
from time import monotonic, sleep
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from aipf.config import load_config
from aipf.security import redact
from aipf.store import ProjectStore


SUPPORTED_EVENTS = {
    "plan_review_required",
    "task_review_required",
    "task_completed",
    "plan_completed",
    "blocked",
}


@dataclass(frozen=True, slots=True)
class NotificationResult:
    status: str
    error: str | None = None


@dataclass(frozen=True, slots=True)
class TelegramWaitResult:
    status: str
    decision: str | None = None
    target: str | None = None
    feedback: str | None = None
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
    reply_markup: dict | None = None,
) -> NotificationResult:
    values = os.environ if environ is None else environ
    token = values.get("AIPF_TELEGRAM_BOT_TOKEN", "")
    chat_id = values.get("AIPF_TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return NotificationResult("skipped")
    values_to_send = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        values_to_send["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=urlencode(values_to_send).encode("utf-8"),
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


def telegram_user_id(environ: Mapping[str, str] | None = None) -> str:
    """Return the one Telegram user allowed to control the project."""
    values = os.environ if environ is None else environ
    return values.get("AIPF_TELEGRAM_USER_ID", "")


def telegram_credentials(environ: Mapping[str, str] | None = None) -> tuple[str, str, str]:
    values = os.environ if environ is None else environ
    token = values.get("AIPF_TELEGRAM_BOT_TOKEN", "")
    chat_id = values.get("AIPF_TELEGRAM_CHAT_ID", "")
    user_id = telegram_user_id(values)
    if not token or not chat_id or not user_id:
        raise ValueError(
            "Telegram interaction requires AIPF_TELEGRAM_BOT_TOKEN, "
            "AIPF_TELEGRAM_CHAT_ID, and AIPF_TELEGRAM_USER_ID"
        )
    return token, chat_id, user_id


def telegram_review_key(target: str, marker: str) -> str:
    """Bind a Telegram button to one specific Plan or Task review attempt."""
    return sha256(f"{target}:{marker}".encode("utf-8")).hexdigest()[:12]


def review_keyboard(target: str, review_key: str) -> dict:
    """Build the small, auditable decision keyboard used by review messages."""
    return {
        "inline_keyboard": [[
            {"text": "승인", "callback_data": f"aipf|approve|{target}|{review_key}"},
            {"text": "수정", "callback_data": f"aipf|revise|{target}|{review_key}"},
            {"text": "재시도", "callback_data": f"aipf|retry|{target}|{review_key}"},
            {"text": "취소", "callback_data": f"aipf|cancel|{target}|{review_key}"},
        ], [
            {"text": "보류", "callback_data": f"aipf|defer|{target}|{review_key}"},
        ]]
    }


def send_review_request(
    text: str,
    target: str,
    review_key: str,
    *,
    environ: Mapping[str, str] | None = None,
    timeout: int = 10,
    opener=None,
) -> NotificationResult:
    """Send a review request with callback buttons; local state is untouched."""
    return send_telegram(
        text,
        environ=environ,
        timeout=timeout,
        opener=opener,
        reply_markup=review_keyboard(target, review_key),
    )


def _telegram_call(
    method: str,
    parameters: Mapping[str, str],
    *,
    token: str,
    timeout: float,
    opener=None,
) -> dict:
    request = Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=urlencode(parameters).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with (opener or urlopen)(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Telegram HTTP {exc.code}") from exc
    except (TimeoutError, URLError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Telegram network or response error") from exc
    if not isinstance(payload, dict) or not payload.get("ok"):
        raise RuntimeError("Telegram API rejected request")
    return payload


def _read_updates(
    token: str,
    *,
    offset: int | None,
    timeout: int,
    opener=None,
) -> list[dict]:
    parameters: dict[str, str] = {
        "timeout": str(timeout),
        "allowed_updates": json.dumps(["callback_query", "message"]),
    }
    if offset is not None:
        parameters["offset"] = str(offset)
    payload = _telegram_call("getUpdates", parameters, token=token, timeout=max(timeout + 5, 10), opener=opener)
    result = payload.get("result", [])
    if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
        raise RuntimeError("Telegram getUpdates returned invalid data")
    return result


def _answer_callback(token: str, callback_id: str, *, opener=None) -> None:
    # Telegram treats this as an acknowledgement only; review state is persisted
    # separately after all local revalidation succeeds.
    _telegram_call("answerCallbackQuery", {"callback_query_id": callback_id}, token=token, timeout=10, opener=opener)


def _request_feedback(token: str, chat_id: str, *, opener=None) -> None:
    _telegram_call(
        "sendMessage",
        {"chat_id": chat_id, "text": "수정할 내용을 텍스트로 보내주세요."},
        token=token,
        timeout=10,
        opener=opener,
    )


def _update_identity(update: dict) -> tuple[str, str, str, str | None] | None:
    """Return (kind, user_id, chat_id, payload) for supported update shapes."""
    if not isinstance(update.get("update_id"), int):
        return None
    callback = update.get("callback_query")
    if isinstance(callback, dict):
        sender = callback.get("from")
        message = callback.get("message")
        if not isinstance(sender, dict) or not isinstance(message, dict):
            return None
        chat = message.get("chat")
        if not isinstance(chat, dict) or chat.get("type") != "private" or "id" not in sender or "id" not in chat:
            return None
        data = callback.get("data")
        return "callback", str(sender["id"]), str(chat["id"]), data if isinstance(data, str) else None
    message = update.get("message")
    if isinstance(message, dict):
        sender = message.get("from")
        chat = message.get("chat")
        if (
            not isinstance(sender, dict)
            or not isinstance(chat, dict)
            or chat.get("type") != "private"
            or "id" not in sender
            or "id" not in chat
        ):
            return None
        text = message.get("text")
        return "message", str(sender["id"]), str(chat["id"]), text if isinstance(text, str) else None
    return None


def wait_for_review(
    *,
    target: str,
    token: str,
    chat_id: str,
    user_id: str,
    review_key: str | None = None,
    timeout: int = 600,
    opener=None,
    clock=monotonic,
    sleep_fn=sleep,
) -> TelegramWaitResult:
    """Poll Telegram once for a decision, returning timeout without side effects."""
    if timeout < 1:
        raise ValueError("Telegram wait timeout must be a positive integer")
    deadline = clock() + timeout
    offset: int | None = None
    pending_feedback = False
    while True:
        remaining = deadline - clock()
        if remaining <= 0:
            return TelegramWaitResult("timeout")
        poll_timeout = max(1, min(30, int(remaining)))
        updates = _read_updates(token, offset=offset, timeout=poll_timeout, opener=opener)
        for update in updates:
            offset = max(offset or 0, int(update["update_id"]) + 1)
            identity = _update_identity(update)
            if identity is None:
                continue
            kind, update_user_id, update_chat_id, payload = identity
            if update_user_id != str(user_id) or update_chat_id != str(chat_id):
                continue
            if kind == "callback":
                callback = update.get("callback_query", {})
                callback_id = callback.get("id")
                if not isinstance(payload, str):
                    continue
                parts = payload.split("|")
                expected_size = 4 if review_key is not None else 3
                if len(parts) != expected_size or parts[0] != "aipf" or parts[2] != target:
                    continue
                if review_key is not None and parts[3] != review_key:
                    continue
                decision = parts[1]
                if decision not in {"approve", "revise", "retry", "cancel", "defer"}:
                    continue
                if isinstance(callback_id, str):
                    try:
                        _answer_callback(token, callback_id, opener=opener)
                    except RuntimeError:
                        pass
                if decision == "revise":
                    pending_feedback = True
                    _request_feedback(token, chat_id, opener=opener)
                    continue
                if decision == "defer":
                    return TelegramWaitResult("deferred", decision=decision, target=target)
                return TelegramWaitResult("decision", decision=decision, target=target)
            if kind == "message" and pending_feedback and payload and payload.strip():
                return TelegramWaitResult("decision", decision="revise", target=target, feedback=payload.strip())
        if not updates:
            sleep_fn(min(1, max(0.0, deadline - clock())))


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
