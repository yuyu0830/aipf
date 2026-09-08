from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from aipf.store import HandoffStore


SCHEMA_NAMES = {"handoff", "runtime", "config"}


@lru_cache(maxsize=len(SCHEMA_NAMES))
def load_schema(name: str) -> dict[str, Any]:
    if name not in SCHEMA_NAMES:
        raise ValueError(f"unknown schema: {name}")
    resource = files("aipf.schemas").joinpath(f"{name}.schema.json")
    schema = json.loads(resource.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def _schema_errors(document: dict[str, Any], schema_name: str) -> list[str]:
    validator = Draft202012Validator(load_schema(schema_name), format_checker=FormatChecker())
    errors: list[str] = []
    for error in sorted(validator.iter_errors(document), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"{location}: {error.message}")
    return errors


def validate_document(document: dict[str, Any]) -> list[str]:
    return _schema_errors(document, "handoff")


def validate_runtime(document: dict[str, Any]) -> list[str]:
    return _schema_errors(document, "runtime")


def validate_config(document: dict[str, Any]) -> list[str]:
    errors = _schema_errors(document, "config")
    weights = document.get("routing", {}).get("weights", {})
    if isinstance(weights, dict) and all(isinstance(value, (int, float)) for value in weights.values()):
        if abs(sum(weights.values()) - 1.0) > 1e-9:
            errors.append("routing.weights: values must sum to 1.0")
        cost = weights.get("cost")
        if isinstance(cost, (int, float)) and any(cost < value for key, value in weights.items() if key != "cost"):
            errors.append("routing.weights.cost: must be at least as large as every other weight")
    execution = document.get("execution", {})
    if isinstance(execution, dict):
        interval = execution.get("heartbeat_interval_seconds")
        timeout = execution.get("heartbeat_timeout_seconds")
        if isinstance(interval, int) and isinstance(timeout, int) and timeout <= interval:
            errors.append("execution.heartbeat_timeout_seconds: must exceed heartbeat interval")
    return errors


def require_valid(document: dict[str, Any], schema_name: str) -> None:
    validators = {
        "handoff": validate_document,
        "runtime": validate_runtime,
        "config": validate_config,
    }
    try:
        errors = validators[schema_name](document)
    except KeyError as exc:
        raise ValueError(f"unknown schema: {schema_name}") from exc
    if errors:
        raise ValueError("; ".join(errors))


def validate_store(store: HandoffStore) -> list[tuple[Path, str]]:
    errors: list[tuple[Path, str]] = []
    for path in store.iter_handoffs():
        try:
            document = store.read(path)
            errors.extend((path, error) for error in validate_document(document))
        except Exception as exc:
            errors.append((path, str(exc)))
    return errors
