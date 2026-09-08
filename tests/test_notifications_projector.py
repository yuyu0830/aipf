import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from aipf.cli import main, read_runtime
from aipf.models import HandoffKind, Status
from aipf.notifications import NotificationResult, completion_message, notification_events, notify_task_completed, send_telegram
from aipf.projector import render_project
from aipf.store import HandoffStore, utc_now


def task_body(status="review"):
    return {
        "goal": "notify completion", "scope": {"includes": [], "excludes": []}, "inputs": [], "outputs": ["report.txt"],
        "constraints": [], "acceptance_criteria": ["safe"],
        "verification": {"commands": [], "evidence": ["tests pass"]}, "dependencies": [],
        "read_set": [], "write_set": ["report.txt"], "resources": [], "risk": "low",
        "budget": {"timeout_seconds": 10, "max_input_tokens": 1000, "max_output_tokens": 200, "max_cost_usd": 1},
        "attempt": 1, "max_retries": 1,
        "progress": {"summary": "report produced", "completed": ["report"], "remaining": [], "next_action": "review"},
        "result": {"outcome": "success", "artifacts": ["report.txt"], "evidence": ["tests pass"]},
        "blocker": None, "review": {"verdict": "approved", "reason": "criteria satisfied"},
    }


class FakeResponse:
    def __init__(self, payload=b'{"ok": true}'):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class NotificationAndProjectorTests(unittest.TestCase):
    def test_send_success_and_missing_configuration(self):
        self.assertEqual(send_telegram("x", environ={}).status, "skipped")
        result = send_telegram(
            "x", environ={"AIPF_TELEGRAM_BOT_TOKEN": "token", "AIPF_TELEGRAM_CHAT_ID": "1"},
            opener=lambda request, timeout: FakeResponse(),
        )
        self.assertEqual(result.status, "sent")

    def test_timeout_and_http_errors_do_not_raise(self):
        values = {"AIPF_TELEGRAM_BOT_TOKEN": "token", "AIPF_TELEGRAM_CHAT_ID": "1"}

        def timeout(request, timeout):
            raise URLError(TimeoutError())

        def http_error(request, timeout):
            raise HTTPError(request.full_url, 500, "error", {}, io.BytesIO())

        self.assertEqual(send_telegram("x", environ=values, opener=timeout).status, "failed")
        self.assertEqual(send_telegram("x", environ=values, opener=http_error).error, "Telegram HTTP 500")

    def test_completion_hook_failure_does_not_change_completed_state(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(main(["--directory", directory, "init", "--goal", "notification test"]), 0)
            root = Path(directory)
            store = HandoffStore(root)
            path = store.create(
                "worker", HandoffKind.TASK, task_body(),
                project_id=read_runtime(root)["project_id"], status=Status.REVIEW,
            )
            with patch("aipf.notifications.notify_task_completed", return_value=NotificationResult("failed", "timeout")):
                result = main(["--directory", directory, "_review-task", "--task", "T_0000", "--verdict", "approved"])
            self.assertEqual(result, 0)
            self.assertEqual(store.read(path)["status"], Status.COMPLETED.value)
            self.assertEqual(read_runtime(root)["state"], "awaiting_task_confirmation")

    def test_completion_message_includes_next_task_and_user_action(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(main(["--directory", directory, "init", "--goal", "message test"]), 0)
            root = Path(directory)
            store = HandoffStore(root)
            project_id = read_runtime(root)["project_id"]
            completed = store.create("worker", HandoffKind.TASK, task_body(), project_id=project_id, status=Status.COMPLETED)
            next_body = task_body()
            next_body["goal"] = "next work"
            next_body["progress"]["next_action"] = "run next verification"
            store.create("worker", HandoffKind.TASK, next_body, project_id=project_id, status=Status.READY)
            message = completion_message(store, store.read(completed))
            self.assertIn("다음 Task: T_0001 next work", message)
            self.assertIn("다음 수행: run next verification", message)
            self.assertIn("aipf approve continue", message)

    def test_projector_includes_decisions_reviews_artifacts_and_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(main(["--directory", directory, "init", "--goal", "projector test"]), 0)
            root = Path(directory)
            store = HandoffStore(root)
            runtime = read_runtime(root)
            store.create("worker", HandoffKind.TASK, task_body(), project_id=runtime["project_id"], status=Status.COMPLETED)
            store.create(
                "orchestrator", HandoffKind.DECISION,
                {"question": "continue?", "options": ["yes"], "selection": "yes", "rationale": "verified", "impact": "project", "decided_by": "user", "decided_at": utc_now()},
                project_id=runtime["project_id"], status=Status.COMPLETED,
            )
            runtime["state"] = "awaiting_task_confirmation"
            content = render_project(store, runtime["goal"], runtime)
            self.assertIn("yes: verified", content)
            self.assertIn("approved: criteria satisfied", content)
            self.assertIn("report.txt", content)
            self.assertIn("aipf approve continue", content)

    def test_projector_preserves_user_notification_conditions(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(main(["--directory", directory, "init", "--goal", "setting test"]), 0)
            root = Path(directory)
            project_file = root / "PROJECT.md"
            content = project_file.read_text(encoding="utf-8")
            project_file.write_text(content.replace("blocked, plan_completed, task_completed", "never"), encoding="utf-8")
            store = HandoffStore(root)
            rendered = render_project(store, "setting test", read_runtime(root))
            self.assertIn("- 전송 조건: never", rendered)
            self.assertEqual(notification_events(project_file), frozenset())

    def test_never_condition_skips_completion_send(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(main(["--directory", directory, "init", "--goal", "disabled notification"]), 0)
            root = Path(directory)
            project_file = root / "PROJECT.md"
            project_file.write_text(
                project_file.read_text(encoding="utf-8").replace("blocked, plan_completed, task_completed", "never"),
                encoding="utf-8",
            )
            store = HandoffStore(root)
            path = store.create(
                "worker", HandoffKind.TASK, task_body(),
                project_id=read_runtime(root)["project_id"], status=Status.COMPLETED,
            )
            with patch("aipf.notifications.send_telegram") as sender:
                result = notify_task_completed(store, path.stem)
            self.assertEqual(result.status, "skipped")
            sender.assert_not_called()
