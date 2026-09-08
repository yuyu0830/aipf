from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": "1.0",
    "context": {"rollover_threshold": 0.70},
    "execution": {
        "max_concurrency": 4,
        "max_retries": 1,
        "heartbeat_interval_seconds": 15,
        "heartbeat_timeout_seconds": 60,
    },
    "review": {
        "medium_uses_court": False,
        "court": {"critics": 2, "defenders": 2, "judges": 1, "max_rounds": 3},
    },
    "routing": {
        "weights": {
            "quality": 0.25,
            "cost": 0.35,
            "security": 0.20,
            "context": 0.10,
            "tools": 0.10,
        },
        "models": [
            {
                "provider": "mock",
                "model": "mock-default",
                "quality": 0.50,
                "cost": 1.00,
                "security": 1.00,
                "context": 0.50,
                "tools": 0.00,
                "local": True,
                "context_tokens": 50000,
                "enabled": True,
            }
        ],
    },
    "security": {
        "workspace_only": True,
        "require_network_approval": True,
        "require_delete_approval": True,
        "require_external_transfer_approval": True,
        "allowed_commands": [],
    },
}


def write_default_config(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(deepcopy(DEFAULT_CONFIG), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise ValueError("config root must be a mapping")
    from aipf.validation import require_valid

    require_valid(value, "config")
    return value
