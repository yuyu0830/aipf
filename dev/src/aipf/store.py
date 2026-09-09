from __future__ import annotations

import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import yaml

from aipf.models import Kind
from aipf.security import resolve_inside


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class ProjectStore:
    DIRECTORIES = {Kind.PLAN: "plans", Kind.TASK: "tasks", Kind.AUDIT: "audits"}

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.control = self.root / ".aipf"

    def initialize(self) -> None:
        for name in (*self.DIRECTORIES.values(),):
            (self.control / name).mkdir(parents=True, exist_ok=True)
        for name in ("docs", "ref", "src"):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def directory(self, kind: Kind) -> Path:
        return self.control / self.DIRECTORIES[kind]

    def paths(self, kind: Kind) -> list[Path]:
        return sorted(self.directory(kind).glob(f"{kind.prefix}_[0-9][0-9][0-9].yaml"))

    def next_id(self, kind: Kind) -> str:
        numbers = [int(path.stem.split("_")[1]) for path in self.paths(kind)]
        return f"{kind.prefix}_{max(numbers, default=-1) + 1:03d}"

    def path(self, kind: Kind, object_id: str) -> Path:
        if not re.fullmatch(fr"{kind.prefix}_[0-9]{{3}}", object_id):
            raise ValueError(f"invalid {kind.value} id: {object_id}")
        return self.directory(kind) / f"{object_id}.yaml"

    def read(self, path: Path) -> dict[str, Any]:
        resolved = resolve_inside(self.root, path)
        with resolved.open(encoding="utf-8") as stream:
            value = yaml.safe_load(stream)
        if not isinstance(value, dict):
            raise ValueError(f"document root must be a mapping: {resolved}")
        return value

    def read_object(self, kind: Kind, object_id: str) -> dict[str, Any]:
        path = self.path(kind, object_id)
        if not path.exists():
            raise ValueError(f"{kind.value} not found: {object_id}")
        return self.read(path)

    def objects(self, kind: Kind) -> Iterable[dict[str, Any]]:
        return (self.read(path) for path in self.paths(kind))

    def write(self, path: Path, document: dict[str, Any]) -> None:
        resolved = resolve_inside(self.root, path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{resolved.name}.", dir=resolved.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                yaml.safe_dump(document, stream, sort_keys=False, allow_unicode=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, resolved)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    def append_audit(self, event: str, target: str, summary: str, *, decision: str | None = None) -> str:
        audit_id = self.next_id(Kind.AUDIT)
        document = {
            "id": audit_id,
            "kind": Kind.AUDIT.value,
            "timestamp": utc_now(),
            "event": event,
            "target": target,
            "summary": summary,
            "decision": decision,
        }
        from aipf.validation import validate_audit

        validate_audit(document)
        self.write(self.path(Kind.AUDIT, audit_id), document)
        return audit_id

    @property
    def runtime_path(self) -> Path:
        return self.control / "runtime.yaml"

    @property
    def config_path(self) -> Path:
        return self.control / "config.yaml"
