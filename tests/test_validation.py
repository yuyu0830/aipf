import copy
import tempfile
import unittest
import uuid
from pathlib import Path

from aipf.config import DEFAULT_CONFIG
from aipf.models import HandoffKind
from aipf.store import HandoffStore
from aipf.store import utc_now
from aipf.validation import validate_config, validate_document, validate_runtime


PROJECT_ID = str(uuid.uuid4())


def common(kind: str, prefix: str) -> dict:
    now = utc_now()
    return {
        "schema_version": "1.0",
        "id": f"{prefix}_0000",
        "uid": str(uuid.uuid4()),
        "kind": kind,
        "agent_id": "test-agent",
        "project_id": PROJECT_ID,
        "created_at": now,
        "updated_at": now,
        "revision": 1,
        "status": "pending",
        "parent_ids": [],
        "tags": [],
    }


def valid_handoffs() -> list[dict]:
    plan = common("plan", "P") | {
        "goal": "plan work", "scope": {"includes": [], "excludes": []}, "task_ids": [],
        "acceptance_criteria": ["approved"], "constraints": [], "checkpoint": "approval",
    }
    task = common("task", "T") | {
        "goal": "do work", "scope": {"includes": [], "excludes": []}, "inputs": [], "outputs": [],
        "constraints": [], "acceptance_criteria": ["verified"],
        "verification": {"commands": [], "evidence": []}, "dependencies": [], "read_set": [],
        "write_set": [], "resources": [], "risk": "low",
        "budget": {"timeout_seconds": 1, "max_input_tokens": 1, "max_output_tokens": 1, "max_cost_usd": 0},
        "attempt": 0, "max_retries": 1,
        "progress": {"summary": "", "completed": [], "remaining": [], "next_action": "run"},
        "result": {"outcome": None, "artifacts": [], "evidence": []}, "blocker": None,
    }
    decision = common("decision", "D") | {
        "question": "continue?", "options": ["yes", "no"], "selection": "yes", "rationale": "approved",
        "impact": "project", "decided_by": "user", "decided_at": utc_now(),
    }
    audit = common("audit", "A") | {
        "event": "created", "actor": "orchestrator", "target_id": "T_0000", "evidence": [], "masked": True,
    }
    knowledge = common("knowledge", "K") | {
        "claim": "validated", "sources": ["test"], "confidence": 1.0, "scope": "tests",
        "valid_until": None, "last_verified_at": utc_now(),
    }
    return [plan, task, decision, audit, knowledge]


class ValidationTests(unittest.TestCase):
    def test_all_handoff_kinds_are_valid(self):
        for document in valid_handoffs():
            with self.subTest(kind=document["kind"]):
                self.assertEqual(validate_document(document), [])

    def test_each_handoff_kind_rejects_missing_required_field(self):
        required = {"plan": "checkpoint", "task": "budget", "decision": "decided_by", "audit": "masked", "knowledge": "last_verified_at"}
        for document in valid_handoffs():
            invalid = copy.deepcopy(document)
            del invalid[required[document["kind"]]]
            with self.subTest(kind=document["kind"]):
                self.assertTrue(validate_document(invalid))

    def test_id_prefix_must_match_kind(self):
        document = valid_handoffs()[0]
        document["id"] = "T_0000"
        self.assertTrue(validate_document(document))

    def test_runtime_schema(self):
        now = utc_now()
        runtime = {
            "schema_version": "1.0", "project_id": PROJECT_ID, "goal": "test", "state": "awaiting_plan",
            "created_at": now, "updated_at": now, "active_plan_id": None, "active_session_id": None,
        }
        self.assertEqual(validate_runtime(runtime), [])
        runtime["state"] = "unknown"
        self.assertTrue(validate_runtime(runtime))

    def test_config_schema_and_weight_policy(self):
        config = copy.deepcopy(DEFAULT_CONFIG)
        self.assertEqual(validate_config(config), [])
        config["routing"]["weights"]["cost"] = 0.1
        self.assertTrue(validate_config(config))

    def test_invalid_handoff_is_not_written(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HandoffStore(Path(directory))
            store.initialize()
            invalid_body = valid_handoffs()[1]
            for field in ("schema_version", "id", "uid", "kind", "agent_id", "project_id", "created_at", "updated_at", "revision", "status", "parent_ids", "tags", "budget"):
                invalid_body.pop(field, None)
            with self.assertRaises(ValueError):
                store.create("worker", HandoffKind.TASK, invalid_body, project_id=PROJECT_ID)
            self.assertEqual(list(store.iter_handoffs()), [])
