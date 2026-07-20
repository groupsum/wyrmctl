"""Logging helpers."""

from __future__ import annotations

import re

_SECRET_RE = re.compile(r"(?i)(token|secret|password)=([^\s]+)")


def redact(value: str) -> str:
    """Redact obvious secrets from diagnostic text."""

    return _SECRET_RE.sub(lambda match: f"{match.group(1)}=***", value)
