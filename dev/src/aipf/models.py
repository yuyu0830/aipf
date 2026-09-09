from __future__ import annotations

from enum import StrEnum


class Kind(StrEnum):
    PLAN = "plan"
    TASK = "task"
    AUDIT = "audit"

    @property
    def prefix(self) -> str:
        return {self.PLAN: "P", self.TASK: "T", self.AUDIT: "A"}[self]


class TaskStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class ProjectState(StrEnum):
    AWAITING_PLAN = "awaiting_plan"
    AWAITING_PLAN_CONFIRMATION = "awaiting_plan_confirmation"
    READY = "ready"
    RUNNING = "running"
    AWAITING_TASK_CONFIRMATION = "awaiting_task_confirmation"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
