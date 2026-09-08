import tempfile
import unittest
import uuid
import copy
from pathlib import Path

from aipf.models import HandoffKind, Status
from aipf.config import DEFAULT_CONFIG
from aipf.providers import ProviderError, ProviderErrorCode, default_registry
from aipf.routing import (
    ModelCandidate,
    NoEligibleModelError,
    RoutingRequirements,
    build_agent_request,
    candidates_from_config,
    select_model,
)
from aipf.session import issue_session
from aipf.store import HandoffStore


WEIGHTS = {"quality": 0.25, "cost": 0.35, "security": 0.20, "context": 0.10, "tools": 0.10}


def task_body() -> dict:
    return {
        "goal": "route work", "scope": {"includes": [], "excludes": []}, "inputs": [], "outputs": [],
        "constraints": [], "acceptance_criteria": ["routed"],
        "verification": {"commands": [], "evidence": []}, "dependencies": [], "read_set": [],
        "write_set": [], "resources": [], "risk": "low",
        "budget": {"timeout_seconds": 60, "max_input_tokens": 1000, "max_output_tokens": 200, "max_cost_usd": 1},
        "attempt": 0, "max_retries": 1,
        "progress": {"summary": "", "completed": [], "remaining": ["route"], "next_action": "route"},
        "result": {"outcome": None, "artifacts": [], "evidence": []}, "blocker": None,
    }


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.remote = ModelCandidate("openai_compatible", "remote", 1.0, 0.8, 0.7, 1.0, 1.0, context_tokens=100000)
        self.local = ModelCandidate("ollama", "local", 0.7, 1.0, 1.0, 0.6, 0.5, local=True, context_tokens=32000)

    def test_selection_is_deterministic(self):
        first = select_model([self.remote, self.local], WEIGHTS)
        second = select_model([self.local, self.remote], WEIGHTS)
        self.assertEqual(first, second)

    def test_sensitive_task_selects_only_local_model(self):
        decision = select_model([self.remote, self.local], WEIGHTS, RoutingRequirements(sensitive=True))
        self.assertEqual(decision.provider, "ollama")
        self.assertTrue(decision.local)

    def test_external_transfer_ban_rejects_remote_only_catalog(self):
        with self.assertRaises(NoEligibleModelError):
            select_model([self.remote], WEIGHTS, RoutingRequirements(external_allowed=False))

    def test_build_request_uses_task_budget_and_records_metadata(self):
        task = {"id": "T_0000", "kind": "task", **task_body()}
        decision = select_model([self.local], WEIGHTS)
        request = build_agent_request(task, decision, system_prompt="system", prompt_version="v1")
        self.assertEqual(request.max_output_tokens, 200)
        self.assertEqual(request.metadata["provider"], "ollama")
        self.assertEqual(request.metadata["prompt_version"], "v1")

    def test_session_records_route_budget_and_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HandoffStore(Path(directory))
            store.initialize()
            project_id = str(uuid.uuid4())
            store.create("worker", HandoffKind.TASK, task_body(), project_id=project_id, status=Status.READY)
            decision = select_model([self.local], WEIGHTS)
            session_id, _ = issue_session(store, "T_0000", "worker", decision=decision, prompt_version="v1")
            session = store.read(store.control / "sessions" / f"{session_id}.yaml")
            self.assertEqual(session["model"], "local")
            self.assertEqual(session["budget"]["max_output_tokens"], 200)
            audits = list(store.iter_handoffs(HandoffKind.AUDIT))
            self.assertEqual(len(audits), 1)
            self.assertIn("model=local", store.read(audits[0])["evidence"])

    def test_registry_has_builtin_providers_and_common_error(self):
        registry = default_registry()
        self.assertEqual(registry.names, ("mock", "ollama", "openai_compatible"))
        self.assertIsNotNone(registry.create("mock"))
        with self.assertRaises(ProviderError) as context:
            registry.create("unknown")
        self.assertEqual(context.exception.code, ProviderErrorCode.CONFIGURATION)

    def test_candidates_load_from_validated_config(self):
        candidates = candidates_from_config(copy.deepcopy(DEFAULT_CONFIG))
        decision = select_model(candidates, WEIGHTS)
        self.assertEqual((decision.provider, decision.model), ("mock", "mock-default"))
