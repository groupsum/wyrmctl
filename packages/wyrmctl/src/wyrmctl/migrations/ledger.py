"""Append-only tamper-evident migration ledger."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wyrmctl.contracts import semantic_digest
from wyrmctl.errors import MigrationError


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    sequence: int
    previous_digest: str | None
    digest: str
    payload: dict[str, Any]


class MigrationLedger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def entries(self) -> tuple[LedgerEntry, ...]:
        if not self.path.exists():
            return ()
        rows: list[LedgerEntry] = []
        for index, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            try:
                raw = json.loads(line)
                entry = LedgerEntry(raw["sequence"], raw.get("previousDigest"), raw["digest"], raw["payload"])
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise MigrationError(f"invalid migration ledger entry {index}") from exc
            expected = semantic_digest(
                {"sequence": entry.sequence, "previousDigest": entry.previous_digest, "payload": entry.payload}
            )
            if (
                entry.digest != expected
                or entry.sequence != index
                or entry.previous_digest != (rows[-1].digest if rows else None)
            ):
                raise MigrationError(f"migration ledger integrity failure at entry {index}")
            rows.append(entry)
        return tuple(rows)

    def append(self, payload: dict[str, Any]) -> LedgerEntry:
        current = self.entries()
        sequence = len(current) + 1
        previous = current[-1].digest if current else None
        digest = semantic_digest({"sequence": sequence, "previousDigest": previous, "payload": payload})
        entry = LedgerEntry(sequence, previous, digest, dict(payload))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(
                json.dumps(
                    {"sequence": sequence, "previousDigest": previous, "digest": digest, "payload": payload},
                    sort_keys=True,
                )
                + "\n"
            )
            stream.flush()
            os_fsync(stream)
        return entry


def os_fsync(stream: Any) -> None:
    import os

    os.fsync(stream.fileno())
