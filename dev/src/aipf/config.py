from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aipf.validation import validate_config


DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": "1.0",
    "notifications": {
        "events": [
            "plan_review_required",
            "task_review_required",
            "task_completed",
            "plan_completed",
            "blocked",
        ],
        "timeout_seconds": 10,
    },
}


def write_default_config(path: Path) -> None:
    path.write_text(yaml.safe_dump(DEFAULT_CONFIG, sort_keys=False), encoding="utf-8")


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise ValueError("config root must be a mapping")
    validate_config(value)
    return value
