from __future__ import annotations

import re
from pathlib import Path


SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password)(\s*[:=]\s*)([^\s,]+)"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgh[opusr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\b[0-9]{6,}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,]+"),
)


def redact(text: str) -> str:
    result = text
    result = SECRET_PATTERNS[0].sub(r"\1\2[REDACTED]", result)
    for pattern in SECRET_PATTERNS[1:4]:
        result = pattern.sub("[REDACTED]", result)
    result = SECRET_PATTERNS[4].sub(r"\1[REDACTED]", result)
    return result


def resolve_inside(root: Path, requested: str | Path) -> Path:
    root = root.resolve()
    candidate = (root / requested).resolve()
    if candidate != root and root not in candidate.parents:
        raise PermissionError(f"path escapes project root: {requested}")
    return candidate
