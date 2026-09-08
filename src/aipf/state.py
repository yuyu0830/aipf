from __future__ import annotations

from aipf.models import Status


class InvalidTransition(ValueError):
    pass


ALLOWED_TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.PENDING: frozenset({Status.READY, Status.CANCELLED}),
    Status.READY: frozenset({Status.RUNNING, Status.CANCELLED}),
    Status.RUNNING: frozenset(
        {Status.BLOCKED, Status.REVIEW, Status.FAILED, Status.CANCELLED}
    ),
    Status.BLOCKED: frozenset({Status.READY, Status.CANCELLED}),
    Status.REVIEW: frozenset(
        {Status.RUNNING, Status.COMPLETED, Status.BLOCKED, Status.CANCELLED}
    ),
    Status.COMPLETED: frozenset(),
    Status.FAILED: frozenset(),
    Status.CANCELLED: frozenset(),
}


def validate_transition(current: Status | str, target: Status | str) -> None:
    current_status = Status(current)
    target_status = Status(target)
    if target_status not in ALLOWED_TRANSITIONS[current_status]:
        raise InvalidTransition(f"invalid transition: {current_status} -> {target_status}")
