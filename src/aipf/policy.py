from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from aipf.models import HandoffKind, Status
from aipf.security import resolve_inside
from aipf.store import HandoffStore


class PolicyDeniedError(PermissionError):
    pass


def recorded_approvals(store: HandoffStore, target_id: str) -> frozenset[str]:
    approvals = set()
    for path in store.iter_handoffs(HandoffKind.DECISION):
        decision = store.read(path)
        if (
            decision.get("status") == Status.COMPLETED.value
            and decision.get("decided_by") == "user"
            and decision.get("impact") in {target_id, "project"}
        ):
            approvals.add(str(decision.get("selection")))
    return frozenset(approvals)


@dataclass(frozen=True, slots=True)
class PolicyEngine:
    config: dict[str, Any]
    approvals: frozenset[str] = frozenset()

    @property
    def security(self) -> dict[str, Any]:
        return self.config["security"]

    def workspace_path(self, root: Path, requested: str | Path) -> Path:
        if not self.security["workspace_only"]:
            return Path(requested).resolve()
        return resolve_inside(root, requested)

    def authorize_command(self, argv: Iterable[str]) -> tuple[str, ...]:
        command = tuple(str(item) for item in argv)
        if not command or any(not item or "\x00" in item for item in command):
            raise PolicyDeniedError("invalid command arguments")
        allowed = [tuple(shlex.split(item)) for item in self.security["allowed_commands"]]
        if not any(command[: len(prefix)] == prefix for prefix in allowed if prefix):
            raise PolicyDeniedError(f"command is not allowed: {command[0]}")
        return command

    def authorize_network(self) -> None:
        if self.security["require_network_approval"] and "network" not in self.approvals:
            raise PolicyDeniedError("network requires user approval")

    def authorize_delete(self, root: Path, requested: str | Path) -> Path:
        path = self.workspace_path(root, requested)
        if self.security["require_delete_approval"] and "delete" not in self.approvals:
            raise PolicyDeniedError("delete requires user approval")
        return path

    def authorize_external_transfer(self) -> None:
        if self.security["require_external_transfer_approval"] and "external_transfer" not in self.approvals:
            raise PolicyDeniedError("external transfer requires user approval")
