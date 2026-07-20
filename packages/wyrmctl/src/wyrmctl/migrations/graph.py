"""Explicit adjacent migration graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from wyrmctl.errors import MigrationError

MigrationFunction = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class MigrationStep:
    kind: str
    from_version: int
    to_version: int
    migrate: MigrationFunction
    reverse: MigrationFunction | None = None

    @property
    def reversible(self) -> bool:
        return self.reverse is not None


class MigrationGraph:
    def __init__(self) -> None:
        self._steps: dict[tuple[str, int, int], MigrationStep] = {}

    def register(self, step: MigrationStep) -> None:
        if step.from_version < 0 or step.to_version < 1 or abs(step.to_version - step.from_version) != 1:
            raise ValueError("migration steps must connect adjacent non-negative versions")
        key = (step.kind, step.from_version, step.to_version)
        if key in self._steps:
            raise ValueError(f"migration step already registered: {key}")
        self._steps[key] = step

    def path(self, kind: str, from_version: int, to_version: int) -> tuple[MigrationStep, ...]:
        if from_version == to_version:
            return ()
        direction = 1 if to_version > from_version else -1
        out: list[MigrationStep] = []
        current = from_version
        while current != to_version:
            next_version = current + direction
            direct = self._steps.get((kind, current, next_version))
            if direct is None and direction < 0:
                forward = self._steps.get((kind, next_version, current))
                if forward is not None and forward.reverse is not None:
                    direct = MigrationStep(kind, current, next_version, forward.reverse, forward.migrate)
            if direct is None:
                raise MigrationError(f"no migration path for {kind} {current} -> {next_version}")
            out.append(direct)
            current = next_version
        return tuple(out)

    def migrate(self, kind: str, document: dict[str, Any], *, to_version: int) -> dict[str, Any]:
        before = document.get("schemaVersion")
        if before is None:
            before = 0
        if isinstance(before, bool) or not isinstance(before, int):
            raise MigrationError("schemaVersion must be an integer")
        current = dict(document)
        for step in self.path(kind, before, to_version):
            current = step.migrate(dict(current))
            if current.get("schemaVersion") != step.to_version:
                raise MigrationError(f"migration {step.from_version}->{step.to_version} returned wrong schemaVersion")
        return current

    def steps(self) -> tuple[MigrationStep, ...]:
        return tuple(self._steps[key] for key in sorted(self._steps))
