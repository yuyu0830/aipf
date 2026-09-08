import copy
import tempfile
import unittest
from pathlib import Path

from aipf.cli import main, read_runtime
from aipf.config import DEFAULT_CONFIG
from aipf.policy import PolicyDeniedError, PolicyEngine, recorded_approvals
from aipf.security import redact, resolve_inside
from aipf.store import HandoffStore


class SecurityTests(unittest.TestCase):
    def test_redacts_common_secrets(self):
        value = redact("api_key=abc token: xyz sk-abcdefghijklmnop 123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ authorization: Bearer secret-value")
        self.assertNotIn("abc", value)
        self.assertNotIn("xyz", value)
        self.assertNotIn("sk-", value)
        self.assertNotIn("ABCDEFGHIJKLMNOPQRSTUVWXYZ", value)
        self.assertNotIn("secret-value", value)

    def test_rejects_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PermissionError):
                resolve_inside(Path(directory), "../outside")

    def test_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (root / "escape").symlink_to(Path(outside), target_is_directory=True)
            with self.assertRaises(PermissionError):
                resolve_inside(root, "escape/secret.txt")

    def test_command_allowlist_requires_exact_prefix(self):
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["security"]["allowed_commands"] = ["python -m aipf.worker"]
        policy = PolicyEngine(config)
        self.assertEqual(policy.authorize_command(["python", "-m", "aipf.worker", "--task", "T_0000"])[0], "python")
        with self.assertRaises(PolicyDeniedError):
            policy.authorize_command(["python", "-c", "dangerous"])

    def test_sensitive_actions_require_explicit_approval(self):
        config = copy.deepcopy(DEFAULT_CONFIG)
        policy = PolicyEngine(config)
        with self.assertRaises(PolicyDeniedError):
            policy.authorize_network()
        with self.assertRaises(PolicyDeniedError):
            policy.authorize_external_transfer()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PolicyDeniedError):
                policy.authorize_delete(Path(directory), "file.txt")
        approved = PolicyEngine(config, frozenset({"network", "external_transfer", "delete"}))
        approved.authorize_network()
        approved.authorize_external_transfer()

    def test_cli_user_approval_is_available_to_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(main(["--directory", directory, "init", "--goal", "approval test"]), 0)
            self.assertEqual(main(["--directory", directory, "approve", "network", "--target", "T_0000"]), 0)
            approvals = recorded_approvals(HandoffStore(Path(directory)), "T_0000")
            self.assertIn("network", approvals)
