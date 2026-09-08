import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from aipf.cli import main, read_runtime
from aipf.completion import submit_task
from aipf.executor import BudgetExceededError, ExecutionResult, execute_assigned_task, recover_stale_tasks, run_ready_tasks
from aipf.models import HandoffKind, Status
from aipf.providers import AgentResponse
from aipf.routing import ModelCandidate, select_model
from aipf.session import issue_session, rollover_session, touch_heartbeat
from aipf.store import HandoffStore


def task_body(goal: str, *, read_set=None, write_set=None) -> dict:
    return {
        "goal": goal, "scope": {"includes": [], "excludes": []}, "inputs": [], "outputs": [],
        "constraints": [], "acceptance_criteria": ["worker completed"],
        "verification": {"commands": [], "evidence": []}, "dependencies": [],
        "read_set": read_set or [], "write_set": write_set or [], "resources": [], "risk": "low",
        "budget": {"timeout_seconds": 10, "max_input_tokens": 1000, "max_output_tokens": 200, "max_cost_usd": 1},
        "attempt": 0, "max_retries": 1,
        "progress": {"summary": "ready", "completed": [], "remaining": [], "next_action": "execute"},
        "result": {"outcome": None, "artifacts": [], "evidence": []}, "blocker": None,
    }


class ExecutorTests(unittest.TestCase):
    def _project(self, directory: str) -> tuple[Path, HandoffStore, str]:
        root = Path(directory)
        self.assertEqual(main(["--directory", directory, "init", "--goal", "executor test"]), 0)
        return root, HandoffStore(root), read_runtime(root)["project_id"]

    def test_cli_run_executes_mock_worker_subprocess(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store, project_id = self._project(directory)
            path = store.create("worker", HandoffKind.TASK, task_body("execute"), project_id=project_id, status=Status.READY)
            self.assertEqual(main(["--directory", directory, "run"]), 0)
            self.assertEqual(store.read(path)["status"], Status.REVIEW.value)
            events = [store.read(item)["event"] for item in store.iter_handoffs(HandoffKind.AUDIT)]
            self.assertIn("session_issued", events)
            self.assertIn("worker_process_finished", events)
            self.assertEqual(read_runtime(root)["state"], "ready")

    def test_independent_tasks_run_in_parallel_and_conflicts_run_serially(self):
        for conflicting, expected_maximum in ((False, 2), (True, 1)):
            with self.subTest(conflicting=conflicting), tempfile.TemporaryDirectory() as directory:
                root, store, project_id = self._project(directory)
                store.create("worker", HandoffKind.TASK, task_body("one", write_set=["src"]), project_id=project_id, status=Status.READY)
                second_reads = ["src/file.py"] if conflicting else ["docs"]
                store.create("worker", HandoffKind.TASK, task_body("two", read_set=second_reads), project_id=project_id, status=Status.READY)
                lock = threading.Lock()
                active = 0
                maximum = 0

                def fake_run(run_root, task, session_id, token):
                    nonlocal active, maximum
                    with lock:
                        active += 1
                        maximum = max(maximum, active)
                    time.sleep(0.05)
                    submit_task(
                        HandoffStore(run_root), task_id=task.id, session_id=session_id, token=token,
                        summary="done", evidence=["fake worker"], artifacts=[],
                    )
                    with lock:
                        active -= 1
                    return ExecutionResult(task.id, 0, session_id, "done", "")

                with patch("aipf.executor._run_process", side_effect=fake_run):
                    results = run_ready_tasks(root)
                self.assertEqual(len(results), 2)
                self.assertEqual(maximum, expected_maximum)

    def test_token_for_one_task_cannot_submit_another(self):
        with tempfile.TemporaryDirectory() as directory:
            _, store, project_id = self._project(directory)
            store.create("worker", HandoffKind.TASK, task_body("one"), project_id=project_id, status=Status.RUNNING)
            store.create("worker", HandoffKind.TASK, task_body("two"), project_id=project_id, status=Status.RUNNING)
            session_id, token = issue_session(store, "T_0000", "worker")
            with self.assertRaises(PermissionError):
                submit_task(
                    store, task_id="T_0001", session_id=session_id, token=token,
                    summary="wrong", evidence=["none"], artifacts=[],
                )

    def test_failure_retries_once_then_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store, project_id = self._project(directory)
            path = store.create("worker", HandoffKind.TASK, task_body("retry"), project_id=project_id, status=Status.READY)
            calls = 0

            def fail_then_succeed(run_root, task, session_id, token):
                nonlocal calls
                calls += 1
                if calls == 1:
                    return ExecutionResult(task.id, 2, session_id, "", "first failure")
                submit_task(
                    HandoffStore(run_root), task_id=task.id, session_id=session_id, token=token,
                    summary="retry succeeded", evidence=["second attempt"], artifacts=[],
                )
                return ExecutionResult(task.id, 0, session_id, "done", "")

            with patch("aipf.executor._run_process", side_effect=fail_then_succeed):
                results = run_ready_tasks(root)
            document = store.read(path)
            self.assertEqual(len(results), 2)
            self.assertEqual(document["status"], Status.REVIEW.value)
            self.assertEqual(document["attempt"], 2)

    def test_second_failure_blocks_task(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store, project_id = self._project(directory)
            path = store.create("worker", HandoffKind.TASK, task_body("fail"), project_id=project_id, status=Status.READY)

            def always_fail(run_root, task, session_id, token):
                return ExecutionResult(task.id, 2, session_id, "", "failure")

            with patch("aipf.executor._run_process", side_effect=always_fail):
                results = run_ready_tasks(root)
            document = store.read(path)
            self.assertEqual(len(results), 2)
            self.assertEqual(document["status"], Status.BLOCKED.value)
            self.assertEqual(document["attempt"], 2)

    def test_resume_recovers_stale_session_then_blocks_at_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store, project_id = self._project(directory)
            path = store.create("worker", HandoffKind.TASK, task_body("recover"), project_id=project_id, status=Status.RUNNING)
            first_session, _ = issue_session(store, "T_0000", "worker")
            first_path = store.control / "sessions" / f"{first_session}.yaml"
            first = store.read(first_path)
            first["heartbeat_at"] = "2000-01-01T00:00:00Z"
            store.atomic_write(first_path, first)
            self.assertEqual(recover_stale_tasks(root), ["T_0000"])
            self.assertEqual(store.read(path)["status"], Status.READY.value)

            document = store.read(path)
            document["status"] = Status.RUNNING.value
            store.update(path, document)
            second_session, _ = issue_session(store, "T_0000", "worker")
            second_path = store.control / "sessions" / f"{second_session}.yaml"
            second = store.read(second_path)
            second["heartbeat_at"] = "2000-01-01T00:00:00Z"
            store.atomic_write(second_path, second)
            self.assertEqual(recover_stale_tasks(root), ["T_0000"])
            self.assertEqual(store.read(path)["status"], Status.BLOCKED.value)

    def test_rollover_creates_child_session_and_resumes_from_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store, project_id = self._project(directory)
            path = store.create("worker", HandoffKind.TASK, task_body("rollover"), project_id=project_id, status=Status.RUNNING)
            candidate = ModelCandidate("mock", "mock-default", 0.5, 1, 1, 0.5, 0, local=True, context_tokens=50000)
            decision = select_model([candidate], {"quality": 0.25, "cost": 0.35, "security": 0.2, "context": 0.1, "tools": 0.1})
            session_id, token = issue_session(store, "T_0000", "worker", decision=decision, prompt_version="worker-v1")
            touch_heartbeat(store, session_id, progress=0.6, checkpoint="saved", context_usage=0.70)
            rolled = rollover_session(store, session_id, "T_0000", token, threshold=0.70)
            self.assertIsNotNone(rolled)
            child_id, child_token = rolled  # type: ignore[misc]
            child = store.read(store.control / "sessions" / f"{child_id}.yaml")
            self.assertEqual(child["parent_session_id"], session_id)
            execute_assigned_task(root, "T_0000", child_id, child_token)
            self.assertEqual(store.read(path)["status"], Status.REVIEW.value)

    def test_provider_usage_over_budget_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store, project_id = self._project(directory)
            store.create("worker", HandoffKind.TASK, task_body("budget"), project_id=project_id, status=Status.RUNNING)
            candidate = ModelCandidate("mock", "mock-default", 0.5, 1, 1, 0.5, 0, local=True, context_tokens=50000)
            decision = select_model([candidate], {"quality": 0.25, "cost": 0.35, "security": 0.2, "context": 0.1, "tools": 0.1})
            session_id, token = issue_session(store, "T_0000", "worker", decision=decision, prompt_version="worker-v1")

            class OverBudgetProvider:
                def run(self, request):
                    return AgentResponse(output="too large", output_tokens=201)

            class Registry:
                def create(self, name, config):
                    return OverBudgetProvider()

            with patch("aipf.executor.default_registry", return_value=Registry()):
                with self.assertRaises(BudgetExceededError):
                    execute_assigned_task(root, "T_0000", session_id, token)

    def test_context_usage_at_threshold_rolls_over_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store, project_id = self._project(directory)
            path = store.create("worker", HandoffKind.TASK, task_body("automatic rollover"), project_id=project_id, status=Status.RUNNING)
            config_path = root / ".aipf" / "config.yaml"
            config = store.read(config_path)
            config["routing"]["models"][0]["context_tokens"] = 100
            store.atomic_write(config_path, config)
            candidate = ModelCandidate("mock", "mock-default", 0.5, 1, 1, 0.5, 0, local=True, context_tokens=100)
            decision = select_model([candidate], {"quality": 0.25, "cost": 0.35, "security": 0.2, "context": 0.1, "tools": 0.1})
            session_id, token = issue_session(store, "T_0000", "worker", decision=decision, prompt_version="worker-v1")
            calls = 0

            class ThresholdProvider:
                def run(self, request):
                    nonlocal calls
                    calls += 1
                    return AgentResponse(output="done", input_tokens=70, output_tokens=1)

            class Registry:
                def create(self, name, config):
                    return ThresholdProvider()

            with patch("aipf.executor.default_registry", return_value=Registry()):
                execute_assigned_task(root, "T_0000", session_id, token)
            self.assertEqual(calls, 2)
            self.assertEqual(store.read(path)["status"], Status.REVIEW.value)
            sessions = [store.read(item) for item in (store.control / "sessions").glob("S_*.yaml")]
            self.assertEqual(len(sessions), 2)
            self.assertEqual(sum(item["parent_session_id"] is not None for item in sessions), 1)
