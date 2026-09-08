import tempfile
import unittest
import uuid
from pathlib import Path

from aipf.completion import report_task_failure, submit_task
from aipf.models import HandoffKind, Status
from aipf.session import issue_session
from aipf.store import HandoffStore


def task_body() -> dict:
    return {
        "goal": "finish work",
        "scope": {"includes": [], "excludes": []},
        "inputs": [],
        "outputs": [],
        "constraints": [],
        "acceptance_criteria": ["verified"],
        "verification": {"commands": [], "evidence": []},
        "dependencies": [],
        "read_set": [],
        "write_set": [],
        "resources": [],
        "risk": "low",
        "budget": {"timeout_seconds": 900, "max_input_tokens": 50000, "max_output_tokens": 10000, "max_cost_usd": 2.0},
        "attempt": 0,
        "max_retries": 1,
        "progress": {"summary": "done", "completed": ["work"], "remaining": [], "next_action": "submit"},
        "result": {"outcome": None, "artifacts": [], "evidence": []},
        "blocker": None,
    }


class CompletionTests(unittest.TestCase):
    def test_submit_moves_running_task_to_review_and_consumes_token(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HandoffStore(Path(directory))
            store.initialize()
            path = store.create("worker", HandoffKind.TASK, task_body(), project_id=str(uuid.uuid4()), status=Status.RUNNING)
            session_id, token = issue_session(store, "T_0000", "worker")
            submit_task(store, task_id="T_0000", session_id=session_id, token=token, summary="done", evidence=["tests pass"], artifacts=[])
            document = store.read(path)
            self.assertEqual(document["status"], "review")
            self.assertEqual(document["execution"]["attempts"][0]["outcome"], "submitted_for_review")
            with self.assertRaises(PermissionError):
                submit_task(store, task_id="T_0000", session_id=session_id, token=token, summary="again", evidence=["x"], artifacts=[])

    def test_failure_requires_cause_analysis_and_records_it(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HandoffStore(Path(directory))
            store.initialize()
            path = store.create("worker", HandoffKind.TASK, task_body(), project_id=str(uuid.uuid4()), status=Status.RUNNING)
            session_id, token = issue_session(store, "T_0000", "worker")
            report_task_failure(store, task_id="T_0000", session_id=session_id, token=token, status=Status.FAILED, summary="failed", cause_analysis="dependency missing")
            document = store.read(path)
            self.assertEqual(document["status"], "failed")
            self.assertEqual(document["execution"]["attempts"][0]["failure_analysis"], "dependency missing")
