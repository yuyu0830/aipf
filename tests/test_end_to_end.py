import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aipf.cli import main, read_runtime
from aipf.models import HandoffKind, Status
from aipf.notifications import NotificationResult
from aipf.store import HandoffStore


def task_body():
    return {
        "goal": "complete end-to-end fixture", "scope": {"includes": ["report.txt"], "excludes": []},
        "inputs": [], "outputs": ["report.txt"], "constraints": [],
        "acceptance_criteria": ["mock worker submits result"],
        "verification": {"commands": [], "evidence": []}, "dependencies": [],
        "read_set": [], "write_set": ["report.txt"], "resources": [], "risk": "low",
        "budget": {"timeout_seconds": 10, "max_input_tokens": 1000, "max_output_tokens": 500, "max_cost_usd": 1},
        "attempt": 0, "max_retries": 1,
        "progress": {"summary": "ready", "completed": [], "remaining": [], "next_action": "run mock worker"},
        "result": {"outcome": None, "artifacts": [], "evidence": []}, "blocker": None,
    }


class EndToEndTests(unittest.TestCase):
    def test_full_cli_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(main(["--directory", directory, "init", "--goal", "end-to-end project"]), 0)
            store = HandoffStore(root)
            runtime = read_runtime(root)
            task_path = store.create(
                "worker", HandoffKind.TASK, task_body(),
                project_id=runtime["project_id"], status=Status.READY,
            )
            plan_path = store.find("P_0000", HandoffKind.PLAN)
            plan = store.read(plan_path)
            plan["task_ids"] = ["T_0000"]
            plan["acceptance_criteria"] = ["T_0000 completed"]
            store.update(plan_path, plan)

            self.assertEqual(main(["--directory", directory, "approve", "continue", "--target", "P_0000"]), 0)
            self.assertEqual(main(["--directory", directory, "run"]), 0)
            self.assertEqual(store.read(task_path)["status"], Status.REVIEW.value)
            with patch("aipf.notifications.notify_task_completed", return_value=NotificationResult("sent")):
                self.assertEqual(main(["--directory", directory, "_review-task", "--task", "T_0000", "--verdict", "approved"]), 0)
            self.assertEqual(read_runtime(root)["state"], "awaiting_task_confirmation")
            self.assertEqual(main(["--directory", directory, "approve", "continue", "--target", "T_0000"]), 0)
            with patch("aipf.notifications.send_telegram", return_value=NotificationResult("sent")):
                self.assertEqual(main(["--directory", directory, "_complete-plan", "--plan", "P_0000"]), 0)
            self.assertEqual(read_runtime(root)["state"], "awaiting_plan_confirmation")
            self.assertEqual(main(["--directory", directory, "approve", "continue", "--target", "P_0000"]), 0)
            self.assertEqual(read_runtime(root)["state"], "completed")
            self.assertEqual(main(["--directory", directory, "validate"]), 0)
            project = (root / "PROJECT.md").read_text(encoding="utf-8")
            self.assertIn("실행 상태: completed", project)
            self.assertIn("진행률: 100%", project)
            sessions = [store.read(path) for path in (store.control / "sessions").glob("S_*.yaml")]
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0]["status"], "used")
