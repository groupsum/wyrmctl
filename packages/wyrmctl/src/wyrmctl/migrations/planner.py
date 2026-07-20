"""Side-effect-free migration manifest planning."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from wyrmctl.contracts import semantic_digest
from wyrmctl.errors import MigrationError
from wyrmctl.migrations.manifest import MigrationManifest
from wyrmctl.migrations.registry import CURRENT_SCHEMA_VERSION, migrate_document


def plan_schema_migration(
    path: str | Path,
    *,
    migration_id: str,
    owner: str,
    environment: str,
) -> MigrationManifest:
    root = Path(path)
    files = [root] if root.is_file() else sorted(root.rglob("*.y*ml"))
    operations: list[dict[str, Any]] = []
    source_documents: list[dict[str, Any]] = []
    target_documents: list[dict[str, Any]] = []
    source_versions: list[int] = []
    for source in files:
        raw = yaml.safe_load(source.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise MigrationError(f"migration source must contain an object: {source}")
        migrated, changed, before = migrate_document(raw)
        source_documents.append(raw)
        target_documents.append(migrated)
        source_versions.append(before or 0)
        if changed:
            operations.append(
                {
                    "action": "rewrite",
                    "path": str(source.resolve()),
                    "beforeDigest": semantic_digest(raw),
                    "afterDigest": semantic_digest(migrated),
                    "afterDocument": migrated,
                }
            )
    return MigrationManifest(
        migration_id=migration_id,
        migration_type="schema",
        owner=owner,
        environment=environment,
        source_kind="DesiredState",
        source_version=min(source_versions, default=CURRENT_SCHEMA_VERSION),
        target_version=CURRENT_SCHEMA_VERSION,
        source_digest=semantic_digest(source_documents),
        target_digest=semantic_digest(target_documents),
        operations=tuple(operations),
        recovery="reversible",
    )
