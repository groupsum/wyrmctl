"""Non-destructive artifact retention evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RetentionCandidate:
    path: Path
    age_days: int


def disposal_candidates(
    paths: list[Path], *, retain_days: int, now: datetime | None = None
) -> tuple[RetentionCandidate, ...]:
    if retain_days < 1:
        raise ValueError("retain_days must be positive")
    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(days=retain_days)
    out: list[RetentionCandidate] = []
    for path in paths:
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if modified < cutoff:
            out.append(RetentionCandidate(path, (current - modified).days))
    return tuple(sorted(out, key=lambda item: item.path.as_posix()))
