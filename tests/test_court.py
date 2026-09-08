import tempfile
import unittest
import unittest.mock
from pathlib import Path

from aipf.cli import main, read_runtime
from aipf.court import CourtPolicy, effective_risk, next_court_action, requires_court, run_court_review
from aipf.models import HandoffKind, Risk, Status, Verdict
from aipf.store import HandoffStore


def task_body(risk="high"):
    return {
        "goal": "review work", "scope": {"includes": [], "excludes": []}, "inputs": [], "outputs": [],
        "constraints": [], "acceptance_criteria": ["safe"],
        "verification": {"commands": [], "evidence": ["tests pass"]}, "dependencies": [],
        "read_set": [], "write_set": ["src/app.py"], "resources": [], "risk": risk,
        "budget": {"timeout_seconds": 10, "max_input_tokens": 1000, "max_output_tokens": 200, "max_cost_usd": 1},
        "attempt": 1, "max_retries": 1,
        "progress": {"summary": "done", "completed": ["work"], "remaining": [], "next_action": "review"},
        "result": {"outcome": "success", "artifacts": [], "evidence": ["tests pass"]}, "blocker": None,
    }


class CourtTests(unittest.TestCase):
    def test_rejected_case_gets_improvement_before_limit(self):
        self.assertEqual(next_court_action(Verdict.REJECTED, 1, CourtPolicy()), "create_improvement_task")

    def test_rejected_case_asks_user_at_limit(self):
        self.assertEqual(next_court_action(Verdict.REJECTED, 3, CourtPolicy()), "ask_user")

    def test_fixed_composition(self):
        with self.assertRaises(ValueError):
            CourtPolicy(critics=1)

    def _project_with_task(self, directory, risk="high"):
        self.assertEqual(main(["--directory", directory, "init", "--goal", "court test"]), 0)
        root = Path(directory)
        store = HandoffStore(root)
        path = store.create(
            "worker", HandoffKind.TASK, task_body(risk),
            project_id=read_runtime(root)["project_id"], status=Status.REVIEW,
        )
        return root, store, path

    def test_risk_policy_can_raise_but_not_lower_risk(self):
        low_code = task_body("low")
        critical = task_body("critical")
        self.assertEqual(effective_risk(low_code), Risk.MEDIUM)
        self.assertEqual(effective_risk(critical), Risk.CRITICAL)
        self.assertTrue(requires_court(Risk.HIGH))
        self.assertFalse(requires_court(Risk.MEDIUM))
        self.assertTrue(requires_court(Risk.MEDIUM, medium_uses_court=True))

    def test_court_uses_five_distinct_sessions_and_approved_completes(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store, path = self._project_with_task(directory)
            calls = []

            def evaluator(role, session_id, payload):
                calls.append((role, session_id, payload))
                if role == "critic":
                    self.assertNotIn("critic_claims", payload)
                    return {"claims": []}
                if role == "defender":
                    self.assertIn("critic_claims", payload)
                    self.assertNotIn("defenses", payload)
                    return {"responses": []}
                self.assertIn("critic_claims", payload)
                self.assertIn("defenses", payload)
                return {"verdict": "approved", "reason": "all criteria satisfied"}

            result = run_court_review(store, "T_0000", evaluator)
            self.assertEqual(result.action, "complete")
            self.assertEqual([item[0] for item in calls], ["critic", "critic", "defender", "defender", "judge"])
            self.assertEqual(len({item[1] for item in calls}), 5)
            self.assertEqual(store.read(path)["status"], Status.COMPLETED.value)
            self.assertEqual(read_runtime(root)["state"], "awaiting_task_confirmation")
            self.assertTrue((store.control / "court" / result.case_id / "manifest.yaml").exists())

    def test_rejection_creates_improvement_before_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            _, store, path = self._project_with_task(directory)

            def evaluator(role, session_id, payload):
                if role == "critic":
                    return {"claims": [{"claim_id": session_id, "description": "fix defect", "severity": "high", "evidence": "checksum"}]}
                if role == "defender":
                    return {"responses": []}
                return {"verdict": "rejected", "reason": "defect remains"}

            result = run_court_review(store, "T_0000", evaluator, round_number=1)
            self.assertEqual(result.action, "create_improvement_task")
            self.assertEqual(result.improvement_task_id, "T_0001")
            self.assertEqual(store.read(path)["status"], Status.BLOCKED.value)
            improvement = store.read(store.find("T_0001", HandoffKind.TASK))
            self.assertEqual(improvement["status"], Status.READY.value)
            self.assertEqual(improvement["parent_ids"], ["T_0000"])

    def test_rejection_at_limit_requires_user_without_improvement(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store, path = self._project_with_task(directory)

            def evaluator(role, session_id, payload):
                if role == "critic":
                    return {"claims": []}
                if role == "defender":
                    return {"responses": []}
                return {"verdict": "rejected", "reason": "limit reached"}

            result = run_court_review(store, "T_0000", evaluator, round_number=3)
            self.assertEqual(result.action, "ask_user")
            self.assertIsNone(result.improvement_task_id)
            self.assertEqual(store.read(path)["status"], Status.BLOCKED.value)
            self.assertEqual(read_runtime(root)["state"], "blocked")

    def test_manual_approval_cannot_bypass_required_court(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, _ = self._project_with_task(directory)
            result = main(["--directory", directory, "_review-task", "--task", "T_0000", "--verdict", "approved"])
            self.assertEqual(result, 2)

    def test_plan_completion_stops_for_user_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(main(["--directory", directory, "init", "--goal", "plan checkpoint"]), 0)
            with unittest.mock.patch("aipf.notifications.send_telegram"):
                self.assertEqual(main(["--directory", directory, "_complete-plan", "--plan", "P_0000"]), 0)
            self.assertEqual(read_runtime(Path(directory))["state"], "awaiting_plan_confirmation")
