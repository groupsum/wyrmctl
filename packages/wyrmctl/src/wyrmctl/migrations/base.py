"""Migration datatypes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class MigrationResult:
    """Result of migrating one document."""

    path: Path
    changed: bool
    before_version: int | None
    after_version: int
    document: dict[str, Any]
