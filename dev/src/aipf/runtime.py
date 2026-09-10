"""Helpers for the persisted execution runtime.

``active_task_id`` was the original single-task runtime field.  Newer
runtimes keep the complete execution set in ``active_task_ids`` while
retaining the singular field as a compatibility alias for older callers and
generated documents.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def active_task_ids(runtime: dict[str, Any]) -> list[str]:
    """Return active task IDs from either the new or legacy runtime shape."""
    values = runtime.get("active_task_ids")
    if values is None:
        value = runtime.get("active_task_id")
        return [value] if isinstance(value, str) and value else []
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str) and value]


def set_active_task_ids(runtime: dict[str, Any], task_ids: Iterable[str]) -> None:
    """Persist a deduplicated active set and its legacy first-item alias."""
    values = list(dict.fromkeys(task_ids))
    runtime["active_task_ids"] = values
    runtime["active_task_id"] = values[0] if values else None
