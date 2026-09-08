import tempfile
import unittest
import uuid
from pathlib import Path

from aipf.cli import main
from aipf.models import HandoffKind, Status
from aipf.store import HandoffStore
from aipf.validation import validate_store


class StoreAndCliTests(unittest.TestCase):
    def test_init_creates_valid_project(self):
        with tempfile.TemporaryDirectory() as directory:
            result = main(["--directory", directory, "init", "--goal", "테스트 목표"])
            self.assertEqual(result, 0)
            root = Path(directory)
            self.assertTrue((root / "PROJECT.md").exists())
            self.assertTrue((root / ".aipf" / "config.yaml").exists())
            self.assertEqual(validate_store(HandoffStore(root)), [])

    def test_task_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = HandoffStore(root)
            store.initialize()
            path = store.create(
                "worker-01",
                HandoffKind.TASK,
                {
                    "goal": "write file",
                    "scope": {"includes": ["x"], "excludes": []},
                    "inputs": [],
                    "outputs": ["x"],
                    "constraints": [],
                    "acceptance_criteria": ["x exists"],
                    "verification": {"commands": [], "evidence": []},
                    "dependencies": [],
                    "read_set": [],
                    "write_set": ["x"],
                    "resources": [],
                    "risk": "low",
                    "budget": {"timeout_seconds": 1, "max_input_tokens": 1, "max_output_tokens": 1, "max_cost_usd": 0},
                    "attempt": 0,
                    "max_retries": 1,
                    "progress": {"summary": "", "completed": [], "remaining": [], "next_action": "write x"},
                    "result": {"outcome": None, "artifacts": [], "evidence": []},
                    "blocker": None,
                },
                project_id=str(uuid.uuid4()),
                status=Status.READY,
            )
            self.assertEqual(path.name, "T_0000.yaml")
            self.assertEqual(store.tasks()[0].goal, "write file")
