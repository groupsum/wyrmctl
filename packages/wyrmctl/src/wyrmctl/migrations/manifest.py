"""Versioned migration manifest model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wyrmctl.contracts import semantic_digest
from wyrmctl.profile import current_profile
from wyrmctl.errors import MigrationError


@dataclass(frozen=True, slots=True)
class MigrationManifest:
    migration_id: str
    migration_type: str
    owner: str
    environment: str
    source_kind: str
    source_version: int
    target_version: int
    source_digest: str
    target_digest: str
    operations: tuple[dict[str, Any], ...]
    destructive: bool = False
    adoption: bool = False
    recovery: str = "forward-repair-only"
    approvals: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.migration_id or not self.owner or not self.environment:
            raise MigrationError("migration id, owner, and environment are required")
        if self.recovery not in {"reversible", "forward-repair-only"}:
            raise MigrationError("migration recovery must be reversible or forward-repair-only")

    def to_dict(self) -> dict[str, Any]:
        return {
            "apiVersion": current_profile().api_version,
            "kind": "NpmctlMigration",
            "schemaVersion": 1,
            "metadata": {"id": self.migration_id, "owner": self.owner, "environment": self.environment} | self.metadata,
            "spec": {
                "migrationType": self.migration_type,
                "source": {
                    "kind": self.source_kind,
                    "schemaVersion": self.source_version,
                    "digest": self.source_digest,
                },
                "target": {"kind": self.source_kind, "schemaVersion": self.target_version},
                "targetDigest": self.target_digest,
                "operations": list(self.operations),
                "policies": {"destructive": self.destructive, "adoption": self.adoption},
                "approvals": list(self.approvals),
                "recovery": {"classification": self.recovery},
            },
        }

    @property
    def digest(self) -> str:
        return semantic_digest(self.to_dict())


MIGRATION_ONLY_ACTIONS = frozenset({"adopt", "transfer", "prune", "delete"})


def reject_migration_only_operations(operations: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> None:
    blocked = sorted({str(item.get("action")) for item in operations if item.get("action") in MIGRATION_ONLY_ACTIONS})
    if blocked:
        raise MigrationError(f"ordinary apply cannot execute migration-only actions: {', '.join(blocked)}")
