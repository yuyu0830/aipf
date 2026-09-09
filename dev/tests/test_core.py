import tempfile
import unittest
from contextlib import redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import yaml

from aipf.cli import main
from aipf.models import Kind
from aipf.notifications import NotificationResult, send_telegram
from aipf.store import ProjectStore


def plan_spec() -> dict:
    return {
        "plan": {
            "goal": "Create a report",
            "scope": {"includes": ["report"], "excludes": []},
            "acceptance_criteria": ["The report exists"],
        },
        "tasks": [{
            "goal": "Write the report",
            "references": ["docs/requirements.md"],
            "outputs": ["src/report.md"],
            "constraints": ["Use the requirements"],
            "acceptance_criteria": ["src/report.md exists"],
            "verification": {"commands": [], "evidence": ["src/report.md"]},
        }],
    }


def prepare_submitted_task(directory: str) -> ProjectStore:
    root = Path(directory)
    main(["--directory", directory, "init", "--goal", "Review project"])
    (root / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
    spec_path = root / "plan.yaml"
    spec_path.write_text(yaml.safe_dump(plan_spec(), sort_keys=False), encoding="utf-8")
    main(["--directory", directory, "plan", "apply", "--file", str(spec_path)])
    main(["--directory", directory, "review", "approve", "--target", "P_000"])
    main(["--directory", directory, "run"])
    (root / "src" / "report.md").write_text("# Report\n", encoding="utf-8")
    main([
        "--directory", directory, "task", "submit", "--target", "T_000",
        "--summary", "Report written", "--evidence", "reviewed", "--output", "src/report.md",
    ])
    return ProjectStore(root)


class CoreLifecycleTests(unittest.TestCase):
    def test_init_creates_visible_structure(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(main(["--directory", directory, "init", "--goal", "Test project"]), 0)
            root = Path(directory)
            for path in ("AGENTS.md", "SKILLS.md", "MEMORY_MAP.md", "README.md", "PROJECT.md", "docs", "ref", "src", ".aipf/plans", ".aipf/tasks", ".aipf/audits"):
                self.assertTrue((root / path).exists(), path)
            self.assertEqual(main(["--directory", directory, "validate"]), 0)

    def test_plan_task_review_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(main(["--directory", directory, "init", "--goal", "Draft"]), 0)
            (root / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
            spec_path = root / "plan.yaml"
            spec_path.write_text(yaml.safe_dump(plan_spec(), sort_keys=False), encoding="utf-8")
            self.assertEqual(main(["--directory", directory, "plan", "apply", "--file", str(spec_path)]), 0)
            self.assertEqual(main(["--directory", directory, "run"]), 3)
            self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "P_000"]), 0)
            self.assertEqual(main(["--directory", directory, "run"]), 0)
            (root / "src" / "report.md").write_text("# Report\n", encoding="utf-8")
            self.assertEqual(main([
                "--directory", directory, "task", "submit", "--target", "T_000",
                "--summary", "Report written", "--evidence", "reviewed", "--output", "src/report.md",
            ]), 0)
            with patch("aipf.cli.notify", return_value=NotificationResult("failed", "network")):
                self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "T_000"]), 0)
            store = ProjectStore(root)
            self.assertEqual(store.read(store.runtime_path)["state"], "completed")
            self.assertEqual(store.read_object(Kind.TASK, "T_000")["status"], "completed")
            self.assertEqual(len(store.paths(Kind.AUDIT)), 2)

    def test_user_can_revise_retry_or_cancel(self):
        expected = {"revise": "ready", "retry": "ready", "cancel": "cancelled"}
        for decision, state in expected.items():
            with self.subTest(decision=decision), tempfile.TemporaryDirectory() as directory:
                store = prepare_submitted_task(directory)
                arguments = ["--directory", directory, "review", decision, "--target", "T_000"]
                if decision == "revise":
                    arguments.extend(["--feedback", "Add more detail"])
                self.assertEqual(main(arguments), 0)
                task = store.read_object(Kind.TASK, "T_000")
                self.assertEqual(task["status"], state)
                self.assertEqual(list(store.objects(Kind.AUDIT))[-1]["decision"], decision)
                if decision == "revise":
                    self.assertEqual(task["feedback"], "Add more detail")

    def test_telegram_transport_is_optional_and_failure_safe(self):
        self.assertEqual(send_telegram("test", environ={}).status, "skipped")

        class Response(BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

        success = send_telegram(
            "test",
            environ={"AIPF_TELEGRAM_BOT_TOKEN": "token", "AIPF_TELEGRAM_CHAT_ID": "1"},
            opener=lambda request, timeout: Response(b'{"ok": true}'),
        )
        self.assertEqual(success.status, "sent")

        failed = send_telegram(
            "test",
            environ={"AIPF_TELEGRAM_BOT_TOKEN": "token", "AIPF_TELEGRAM_CHAT_ID": "1"},
            opener=lambda request, timeout: (_ for _ in ()).throw(URLError("offline")),
        )
        self.assertEqual(failed.status, "failed")

    def test_run_uses_only_active_plan_task_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(main(["--directory", directory, "init", "--goal", "Order test"]), 0)
            (root / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")

            first = plan_spec()
            first_path = root / "first.yaml"
            first_path.write_text(yaml.safe_dump(first, sort_keys=False), encoding="utf-8")
            self.assertEqual(main(["--directory", directory, "plan", "apply", "--file", str(first_path)]), 0)
            self.assertEqual(main([
                "--directory", directory, "review", "revise", "--target", "P_000", "--feedback", "Replace tasks",
            ]), 0)

            replacement = plan_spec()
            replacement["tasks"] = [
                plan_spec()["tasks"][0] | {"id": "T_005", "goal": "First declared task"},
                plan_spec()["tasks"][0] | {"id": "T_001", "goal": "Second declared task"},
            ]
            replacement_path = root / "replacement.yaml"
            replacement_path.write_text(yaml.safe_dump(replacement, sort_keys=False), encoding="utf-8")
            self.assertEqual(main(["--directory", directory, "plan", "apply", "--file", str(replacement_path)]), 0)
            self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "P_000"]), 0)
            self.assertEqual(main(["--directory", directory, "run"]), 0)

            store = ProjectStore(root)
            runtime = store.read(store.runtime_path)
            self.assertEqual(runtime["active_task_id"], "T_005")
            self.assertEqual(store.read_object(Kind.TASK, "T_000")["status"], "pending")

    def test_submit_requires_evidence_and_warns_for_omitted_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            store = prepare_submitted_task(directory)
            task = store.read_object(Kind.TASK, "T_000")
            task["status"] = "running"
            store.write(store.path(Kind.TASK, "T_000"), task)

            without_evidence = [
                "--directory", directory, "task", "submit", "--target", "T_000", "--summary", "Draft result",
            ]
            self.assertEqual(main(without_evidence), 2)

            output = StringIO()
            with redirect_stdout(output):
                result = main(without_evidence + ["--evidence", "Manual verification completed"])
            self.assertEqual(result, 0)
            self.assertIn("warning: declared outputs not submitted", output.getvalue())
