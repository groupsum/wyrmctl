"""Scoped local leases for migration and complete-zone mutation."""

from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from wyrmctl.errors import LeaseError


@dataclass(frozen=True, slots=True)
class Lease:
    scope: str
    owner: str
    token: str
    expires_at: float


class FileLeaseBackend:
    def __init__(self, directory: str | Path, *, clock: Callable[[], float] = time.time) -> None:
        self.directory = Path(directory)
        self.clock = clock

    def acquire(self, scope: str, owner: str, *, ttl_s: float = 300.0) -> Lease:
        if ttl_s <= 0:
            raise ValueError("lease ttl must be positive")
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(scope)
        current = self._read(path)
        now = float(self.clock())
        if current is not None and current.expires_at > now:
            raise LeaseError("LEASE_HELD", f"lease {scope!r} is held by {current.owner}", retryable=True)
        token = uuid.uuid4().hex
        lease = Lease(scope, owner, token, now + ttl_s)
        flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if current is None else os.O_TRUNC)
        try:
            fd = os.open(path, flags, 0o600)
        except FileExistsError as exc:
            raise LeaseError("LEASE_RACE", f"lease {scope!r} was acquired concurrently", retryable=True) from exc
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(asdict(lease), stream, sort_keys=True)
        return lease

    def renew(self, lease: Lease, *, ttl_s: float = 300.0) -> Lease:
        current = self._require_owner(lease)
        renewed = Lease(current.scope, current.owner, current.token, float(self.clock()) + ttl_s)
        self._path(lease.scope).write_text(json.dumps(asdict(renewed), sort_keys=True), encoding="utf-8")
        return renewed

    def release(self, lease: Lease) -> None:
        self._require_owner(lease)
        self._path(lease.scope).unlink()

    def _require_owner(self, lease: Lease) -> Lease:
        current = self._read(self._path(lease.scope))
        if current is None or current.token != lease.token:
            raise LeaseError("STALE_LEASE", f"lease {lease.scope!r} is no longer owned by this executor")
        return current

    def _path(self, scope: str) -> Path:
        safe = "".join(char if char.isalnum() or char in "-." else "_" for char in scope)
        return self.directory / f"{safe}.lease.json"

    @staticmethod
    def _read(path: Path) -> Lease | None:
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return Lease(str(raw["scope"]), str(raw["owner"]), str(raw["token"]), float(raw["expires_at"]))
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise LeaseError("INVALID_LEASE", f"invalid lease file: {path}") from exc
