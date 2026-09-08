from __future__ import annotations

from pathlib import PurePosixPath
from typing import Iterable

from aipf.models import ResourceClaim, Status, TaskView


def _normal(path: str) -> PurePosixPath:
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe resource path: {path}")
    return candidate


def _overlap(left: str, right: str) -> bool:
    a, b = _normal(left), _normal(right)
    return a == b or a in b.parents or b in a.parents


def claims_conflict(left: ResourceClaim, right: ResourceClaim) -> bool:
    if set(left.resources) & set(right.resources):
        return True
    for written in left.write_set:
        if any(_overlap(written, item) for item in (*right.read_set, *right.write_set)):
            return True
    for written in right.write_set:
        if any(_overlap(written, item) for item in left.read_set):
            return True
    return False


def ready_batches(tasks: Iterable[TaskView]) -> list[list[TaskView]]:
    """Create conflict-free batches in stable input order."""
    candidates = [task for task in tasks if task.status == Status.READY]
    batches: list[list[TaskView]] = []
    while candidates:
        batch: list[TaskView] = []
        deferred: list[TaskView] = []
        for task in candidates:
            if any(claims_conflict(task.claim, active.claim) for active in batch):
                deferred.append(task)
            else:
                batch.append(task)
        batches.append(batch)
        candidates = deferred
    return batches
