from __future__ import annotations

import os
import re
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import yaml

from aipf.models import HandoffKind, ResourceClaim, Risk, Status, TaskView
from aipf.security import resolve_inside


ID_PATTERN = re.compile(r"^(?P<prefix>[PTDAK])_(?P<number>\d{4,})\.yaml$")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class HandoffStore:
    def __init__(self, project_root: Path):
        self.root = project_root.resolve()
        self.control = self.root / ".aipf"
        self.handoff_root = self.control / "handoff"

    def initialize(self) -> None:
        for directory in (
            self.handoff_root / "orchestrator" / "plan",
            self.handoff_root / "orchestrator" / "task",
            self.handoff_root / "orchestrator" / "decision",
            self.handoff_root / "orchestrator" / "audit",
            self.handoff_root / "orchestrator" / "knowledge",
            self.control / "court",
            self.control / "sessions",
            self.control / "bin",
            self.control / "locks",
            self.control / "logs",
            self.control / "archive",
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def agent_dir(self, agent_id: str, kind: HandoffKind) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", agent_id):
            raise ValueError(f"invalid agent id: {agent_id}")
        return resolve_inside(self.handoff_root, Path(agent_id) / kind.value)

    def allocate_id(self, agent_id: str, kind: HandoffKind) -> str:
        directory = self.agent_dir(agent_id, kind)
        directory.mkdir(parents=True, exist_ok=True)
        numbers = []
        for path in directory.glob(f"{kind.prefix}_*.yaml"):
            match = ID_PATTERN.match(path.name)
            if match and match.group("prefix") == kind.prefix:
                numbers.append(int(match.group("number")))
        return f"{kind.prefix}_{max(numbers, default=-1) + 1:04d}"

    def create(
        self,
        agent_id: str,
        kind: HandoffKind,
        body: dict[str, Any],
        *,
        project_id: str,
        status: Status = Status.PENDING,
    ) -> Path:
        handoff_id = self.allocate_id(agent_id, kind)
        timestamp = utc_now()
        document = {
            "schema_version": "1.0",
            "id": handoff_id,
            "uid": str(uuid.uuid4()),
            "kind": kind.value,
            "agent_id": agent_id,
            "project_id": project_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            "revision": 1,
            "status": status.value,
            "parent_ids": [],
            "tags": [],
            **body,
        }
        from aipf.validation import require_valid

        require_valid(document, "handoff")
        path = self.agent_dir(agent_id, kind) / f"{handoff_id}.yaml"
        self.atomic_write(path, document)
        return path

    def atomic_write(self, path: Path, document: dict[str, Any]) -> None:
        path = resolve_inside(self.root, path)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                yaml.safe_dump(document, stream, sort_keys=False, allow_unicode=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, path)
        except BaseException:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise

    @staticmethod
    def read(path: Path) -> dict[str, Any]:
        with path.open(encoding="utf-8") as stream:
            value = yaml.safe_load(stream)
        if not isinstance(value, dict):
            raise ValueError(f"handoff root must be a mapping: {path}")
        return value

    def iter_handoffs(self, kind: HandoffKind | None = None) -> Iterable[Path]:
        if not self.handoff_root.exists():
            return ()
        if kind:
            return sorted(self.handoff_root.glob(f"*/{kind.value}/{kind.prefix}_*.yaml"))
        return sorted(self.handoff_root.glob("*/*/[PTDAK]_*.yaml"))

    def tasks(self) -> list[TaskView]:
        result: list[TaskView] = []
        for path in self.iter_handoffs(HandoffKind.TASK):
            raw = self.read(path)
            result.append(
                TaskView(
                    id=str(raw["id"]),
                    agent_id=str(raw["agent_id"]),
                    goal=str(raw.get("goal", "")),
                    status=Status(raw["status"]),
                    dependencies=tuple(raw.get("dependencies", [])),
                    claim=ResourceClaim(
                        tuple(raw.get("read_set", [])),
                        tuple(raw.get("write_set", [])),
                        tuple(raw.get("resources", [])),
                    ),
                    risk=Risk(raw.get("risk", "low")),
                    raw=raw,
                    path=path,
                )
            )
        return result

    def find(self, handoff_id: str, kind: HandoffKind | None = None) -> Path:
        matches = [path for path in self.iter_handoffs(kind) if path.stem == handoff_id]
        if not matches:
            raise ValueError(f"handoff not found: {handoff_id}")
        if len(matches) > 1:
            raise ValueError(f"handoff id is ambiguous: {handoff_id}")
        return matches[0]

    def update(self, path: Path, document: dict[str, Any]) -> None:
        document["revision"] = int(document.get("revision", 0)) + 1
        document["updated_at"] = utc_now()
        from aipf.validation import require_valid

        require_valid(document, "handoff")
        self.atomic_write(path, document)
