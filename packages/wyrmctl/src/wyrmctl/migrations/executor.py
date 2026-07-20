"""Transactional execution of reviewed migration manifests."""

from __future__ import annotations

from pathlib import Path
import yaml

from wyrmctl.contracts import semantic_digest
from wyrmctl.errors import MigrationError
from wyrmctl.migrations.ledger import MigrationLedger
from wyrmctl.migrations.manifest import MigrationManifest
from wyrmctl.migrations.transaction import FileChange, TransactionResult, apply_file_transaction


def execute_migration(
    manifest: MigrationManifest,
    *,
    repository_root: str | Path,
    backup_dir: str | Path,
    ledger: MigrationLedger,
) -> TransactionResult:
    root = Path(repository_root).resolve()
    changes: list[FileChange] = []
    for index, operation in enumerate(manifest.operations):
        if operation.get("action") != "rewrite":
            raise MigrationError(f"unsupported migration operation at index {index}")
        target = Path(str(operation.get("path", ""))).resolve()
        if target != root and root not in target.parents:
            raise MigrationError(f"migration target escapes repository root: {target}")
        current = yaml.safe_load(target.read_text(encoding="utf-8"))
        if semantic_digest(current) != operation.get("beforeDigest"):
            raise MigrationError(f"migration source changed after review: {target}")
        after = operation.get("afterDocument")
        if not isinstance(after, dict) or semantic_digest(after) != operation.get("afterDigest"):
            raise MigrationError(f"invalid reviewed migration output: {target}")
        changes.append(FileChange(target, yaml.safe_dump(after, sort_keys=False).encode("utf-8")))
    ledger.append({"migrationId": manifest.migration_id, "phase": "started", "digest": manifest.digest})
    result = apply_file_transaction(tuple(changes), backup_dir=Path(backup_dir))
    ledger.append(
        {
            "migrationId": manifest.migration_id,
            "phase": "completed",
            "digest": manifest.digest,
            "changed": [str(path) for path in result.changed],
        }
    )
    return result
