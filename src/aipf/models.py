from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class HandoffKind(StrEnum):
    PLAN = "plan"
    TASK = "task"
    DECISION = "decision"
    AUDIT = "audit"
    KNOWLEDGE = "knowledge"

    @property
    def prefix(self) -> str:
        return {
            self.PLAN: "P",
            self.TASK: "T",
            self.DECISION: "D",
            self.AUDIT: "A",
            self.KNOWLEDGE: "K",
        }[self]


class Status(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Risk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Verdict(StrEnum):
    APPROVED = "approved"
    CHANGES_REQUIRED = "changes_required"
    REJECTED = "rejected"
    USER_DECISION_REQUIRED = "user_decision_required"


@dataclass(frozen=True, slots=True)
class ResourceClaim:
    read_set: tuple[str, ...] = ()
    write_set: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Budget:
    timeout_seconds: int = 900
    max_input_tokens: int = 50_000
    max_output_tokens: int = 10_000
    max_cost_usd: float = 2.0


@dataclass(slots=True)
class TaskView:
    id: str
    agent_id: str
    goal: str
    status: Status
    dependencies: tuple[str, ...] = ()
    claim: ResourceClaim = field(default_factory=ResourceClaim)
    risk: Risk = Risk.LOW
    raw: dict[str, Any] = field(default_factory=dict)
    path: Path | None = None
