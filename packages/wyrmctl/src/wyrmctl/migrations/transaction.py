"""Atomic multi-file migration transaction."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from wyrmctl.errors import MigrationError


@dataclass(frozen=True, slots=True)
class FileChange:
    target: Path
    content: bytes


@dataclass(frozen=True, slots=True)
class TransactionResult:
    changed: tuple[Path, ...]
    backups: tuple[Path, ...]


def apply_file_transaction(
    changes: tuple[FileChange, ...],
    *,
    backup_dir: Path,
    validate: Callable[[Path], None] | None = None,
) -> TransactionResult:
    targets = [change.target.resolve() for change in changes]
    if len(targets) != len(set(targets)):
        raise MigrationError("migration transaction contains duplicate target paths")
    backup_dir.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path]] = []
    backups: list[Path] = []
    try:
        for change in changes:
            change.target.parent.mkdir(parents=True, exist_ok=True)
            handle, name = tempfile.mkstemp(prefix=f".{change.target.name}.", dir=change.target.parent)
            with os.fdopen(handle, "wb") as stream:
                stream.write(change.content)
                stream.flush()
                os.fsync(stream.fileno())
            staged_path = Path(name)
            if validate is not None:
                validate(staged_path)
            staged.append((staged_path, change.target))
        for _staged, target in staged:
            if target.exists():
                backup = backup_dir / f"{len(backups):04d}-{target.name}"
                shutil.copy2(target, backup)
                backups.append(backup)
        for staged_path, target in staged:
            os.replace(staged_path, target)
        return TransactionResult(tuple(target for _staged, target in staged), tuple(backups))
    except BaseException as exc:
        for staged_path, _target in staged:
            staged_path.unlink(missing_ok=True)
        if isinstance(exc, MigrationError):
            raise
        raise MigrationError(f"filesystem migration transaction failed: {exc}") from exc
