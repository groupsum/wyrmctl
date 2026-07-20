from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from wyrmctl.contracts import semantic_digest
from wyrmctl.errors import LeaseError, MigrationError, RecoveryError
from wyrmctl.migrations.builtin.desired_state_v1_v2 import migrate as v1_v2, reverse as v2_v1
from wyrmctl.migrations.builtin.desired_state_v2_v3 import migrate as v2_v3, reverse as v3_v2
from wyrmctl.migrations.builtin.repository_v0_v1 import migrate as repository_v0_v1
from wyrmctl.migrations.executor import execute_migration
from wyrmctl.migrations.graph import MigrationGraph, MigrationStep
from wyrmctl.migrations.leases import FileLeaseBackend, Lease
from wyrmctl.migrations.ledger import MigrationLedger
from wyrmctl.migrations.manifest import MigrationManifest, reject_migration_only_operations
from wyrmctl.migrations.planner import plan_schema_migration
from wyrmctl.migrations.recovery import forward_repair, rollback
from wyrmctl.migrations.transaction import FileChange, apply_file_transaction


def test_migration_graph_paths_and_guards() -> None:
    graph = MigrationGraph()
    step = MigrationStep("Thing", 0, 1, lambda value: value | {"schemaVersion": 1}, lambda value: {"x": value["x"]})
    graph.register(step)
    graph.register(MigrationStep("Thing", 1, 2, lambda value: value | {"schemaVersion": 2}))
    assert step.reversible is True
    assert graph.path("Thing", 1, 1) == ()
    assert len(graph.path("Thing", 0, 2)) == 2
    assert graph.path("Thing", 1, 0)[0].to_version == 0
    assert graph.migrate("Thing", {"x": 1}, to_version=2)["schemaVersion"] == 2
    assert len(graph.steps()) == 2
    with pytest.raises(ValueError, match="adjacent"):
        MigrationGraph().register(MigrationStep("Thing", 0, 2, lambda value: value))
    with pytest.raises(ValueError, match="already registered"):
        graph.register(step)
    with pytest.raises(MigrationError, match="no migration path"):
        graph.path("Thing", 2, 0)
    with pytest.raises(MigrationError, match="integer"):
        graph.migrate("Thing", {"schemaVersion": "1"}, to_version=2)
    broken = MigrationGraph()
    broken.register(MigrationStep("Thing", 0, 1, lambda value: value))
    with pytest.raises(MigrationError, match="wrong schemaVersion"):
        broken.migrate("Thing", {}, to_version=1)


def test_builtin_adjacent_migrations_round_trip() -> None:
    legacy = {"proxy_hosts": [{"name": "x"}]}
    v1 = {"apiVersion": "wyrmctl.com/v1", "schemaVersion": 1, **legacy}
    v2 = v1_v2(v1)
    assert v2["dns_records"] == []
    assert v2_v1(v2)["schemaVersion"] == 1
    with pytest.raises(MigrationError, match="DNS records"):
        v2_v1(v2 | {"dns_records": [{"type": "A"}]})
    v3 = v2_v3(v2)
    assert v3["kind"] == "DesiredState" and v3["spec"]["proxyHosts"] == legacy["proxy_hosts"]
    assert v3_v2(v3)["schemaVersion"] == 2
    multiple = v2 | {
        "proxy_hosts": [
            {"meta": {"owner": "one"}},
            {"meta": {"owner": "two"}},
            "ignored",
            {"meta": []},
            {"meta": {"owner": 1}},
        ]
    }
    assert v2_v3(multiple)["metadata"]["owner"] == "unresolved"
    with pytest.raises(MigrationError):
        v1_v2({"schemaVersion": 2})
    with pytest.raises(MigrationError):
        v2_v1({"schemaVersion": 1})
    with pytest.raises(MigrationError):
        v2_v3({"schemaVersion": 1})
    with pytest.raises(MigrationError):
        v3_v2({"schemaVersion": 2})
    with pytest.raises(MigrationError):
        v3_v2({"schemaVersion": 3, "spec": []})
    repository = repository_v0_v1({"name": "repo", "owners": ["a"], "environments": {}, "domains": []})
    assert repository["kind"] == "NpmctlRepository"


def _manifest(**overrides) -> MigrationManifest:
    values = {
        "migration_id": "migration-1",
        "migration_type": "schema",
        "owner": "owner",
        "environment": "prod",
        "source_kind": "DesiredState",
        "source_version": 2,
        "target_version": 3,
        "source_digest": "before",
        "target_digest": "after",
        "operations": (),
    }
    values.update(overrides)
    return MigrationManifest(**values)


def test_manifest_recovery_and_import_guards() -> None:
    manifest = _manifest(destructive=True, adoption=True, approvals=("ops",), metadata={"ticket": "1"})
    assert manifest.to_dict()["spec"]["targetDigest"] == "after"
    assert manifest.digest.startswith("sha256:")
    for overrides in ({"migration_id": ""}, {"owner": ""}, {"environment": ""}, {"recovery": "unknown"}):
        with pytest.raises(MigrationError):
            _manifest(**overrides)
    reject_migration_only_operations([{"action": "create"}])
    with pytest.raises(MigrationError, match="delete"):
        reject_migration_only_operations([{"action": "delete"}])
    assert rollback({"x": 1}, lambda value: value | {"x": 0}) == {"x": 0}
    with pytest.raises(RecoveryError, match="forward-repair-only"):
        rollback({}, None)
    repair = forward_repair(
        expected=[{"identity": "create", "v": 1}, {"identity": "update", "v": 2}],
        observed=[{"identity": "delete", "v": 1}, {"identity": "update", "v": 1}],
    )
    assert [item["action"] for item in repair] == ["create", "delete", "update"]


def test_transaction_ledger_planner_and_executor(tmp_path: Path) -> None:
    target = tmp_path / "desired.yaml"
    original = {"apiVersion": "wyrmctl.com/v1", "schemaVersion": 2, "proxy_hosts": []}
    target.write_text(yaml.safe_dump(original), encoding="utf-8")
    manifest = plan_schema_migration(target, migration_id="m1", owner="owner", environment="prod")
    assert manifest.target_version == 3 and len(manifest.operations) == 1
    ledger = MigrationLedger(tmp_path / "ledger.jsonl")
    result = execute_migration(
        manifest,
        repository_root=tmp_path,
        backup_dir=tmp_path / "backups",
        ledger=ledger,
    )
    assert result.changed == (target.resolve(),)
    assert yaml.safe_load(target.read_text(encoding="utf-8"))["schemaVersion"] == 3
    assert [entry.payload["phase"] for entry in ledger.entries()] == ["started", "completed"]
    assert len(result.backups) == 1
    entry = ledger.append({"phase": "verified"})
    assert entry.sequence == 3
    ledger.path.write_text(
        ledger.path.read_text(encoding="utf-8").replace('"sequence": 1', '"sequence": 9', 1), encoding="utf-8"
    )
    with pytest.raises(MigrationError, match="integrity"):
        ledger.entries()
    invalid = tmp_path / "invalid-ledger.jsonl"
    invalid.write_text("{", encoding="utf-8")
    with pytest.raises(MigrationError, match="invalid migration ledger"):
        MigrationLedger(invalid).entries()


def test_transaction_and_executor_failure_edges(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_text("old", encoding="utf-8")
    result = apply_file_transaction(
        (FileChange(target, b"new"), FileChange(tmp_path / "new", b"created")),
        backup_dir=tmp_path / "backup",
        validate=lambda path: path.read_bytes(),
    )
    assert target.read_text(encoding="utf-8") == "new" and len(result.backups) == 1
    with pytest.raises(MigrationError, match="duplicate"):
        apply_file_transaction((FileChange(target, b"a"), FileChange(target, b"b")), backup_dir=tmp_path / "duplicate")
    with pytest.raises(MigrationError, match="transaction failed"):
        apply_file_transaction(
            (FileChange(target, b"bad"),),
            backup_dir=tmp_path / "bad-backup",
            validate=lambda _path: (_ for _ in ()).throw(ValueError("invalid")),
        )
    with pytest.raises(MigrationError, match="invalid"):
        apply_file_transaction(
            (FileChange(target, b"bad"),),
            backup_dir=tmp_path / "migration-error",
            validate=lambda _path: (_ for _ in ()).throw(MigrationError("invalid")),
        )
    calls = [0]

    def fail_second(_path):
        calls[0] += 1
        if calls[0] == 2:
            raise MigrationError("second invalid")

    with pytest.raises(MigrationError, match="second invalid"):
        apply_file_transaction(
            (FileChange(tmp_path / "one", b"1"), FileChange(tmp_path / "two", b"2")),
            backup_dir=tmp_path / "second-failure",
            validate=fail_second,
        )

    outside = tmp_path.parent / "outside.yaml"
    outside.write_text("x: 1", encoding="utf-8")
    ledger = MigrationLedger(tmp_path / "execution-ledger")
    with pytest.raises(MigrationError, match="escapes"):
        execute_migration(
            _manifest(operations=({"action": "rewrite", "path": str(outside)},)),
            repository_root=tmp_path,
            backup_dir=tmp_path / "backup2",
            ledger=ledger,
        )
    with pytest.raises(MigrationError, match="unsupported"):
        execute_migration(
            _manifest(operations=({"action": "delete", "path": str(target)},)),
            repository_root=tmp_path,
            backup_dir=tmp_path / "backup3",
            ledger=ledger,
        )
    operation = {
        "action": "rewrite",
        "path": str(target),
        "beforeDigest": "wrong",
        "afterDigest": semantic_digest({"x": 2}),
        "afterDocument": {"x": 2},
    }
    with pytest.raises(MigrationError, match="changed after review"):
        execute_migration(
            _manifest(operations=(operation,)),
            repository_root=tmp_path,
            backup_dir=tmp_path / "backup4",
            ledger=ledger,
        )
    current = yaml.safe_load(target.read_text(encoding="utf-8"))
    operation |= {"beforeDigest": semantic_digest(current), "afterDigest": "wrong"}
    with pytest.raises(MigrationError, match="invalid reviewed"):
        execute_migration(
            _manifest(operations=(operation,)),
            repository_root=tmp_path,
            backup_dir=tmp_path / "backup5",
            ledger=ledger,
        )


def test_file_leases(tmp_path: Path, monkeypatch) -> None:
    now = [100.0]
    backend = FileLeaseBackend(tmp_path, clock=lambda: now[0])
    lease = backend.acquire("zone/example.com", "runner", ttl_s=10)
    assert lease.expires_at == 110
    with pytest.raises(LeaseError, match="held"):
        backend.acquire("zone/example.com", "other")
    renewed = backend.renew(lease, ttl_s=20)
    assert renewed.expires_at == 120
    backend.release(renewed)
    assert not list(tmp_path.glob("*.lease.json"))
    with pytest.raises(ValueError, match="positive"):
        backend.acquire("x", "runner", ttl_s=0)
    stale = backend.acquire("x", "runner", ttl_s=1)
    now[0] = 102
    replacement = backend.acquire("x", "other", ttl_s=1)
    with pytest.raises(LeaseError, match="no longer owned"):
        backend.renew(stale)
    backend.release(replacement)
    invalid = tmp_path / "bad.lease.json"
    invalid.write_text("{", encoding="utf-8")
    with pytest.raises(LeaseError, match="invalid lease"):
        backend._read(invalid)
    with pytest.raises(LeaseError, match="no longer owned"):
        backend.release(Lease("missing", "x", "token", 0))
    import wyrmctl.migrations.leases as leases

    original_open = leases.os.open
    monkeypatch.setattr(leases.os, "open", lambda *_args: (_ for _ in ()).throw(FileExistsError()))
    with pytest.raises(LeaseError, match="acquired concurrently"):
        FileLeaseBackend(tmp_path / "race").acquire("race", "runner")
    monkeypatch.setattr(leases.os, "open", original_open)


def test_planner_input_errors(tmp_path: Path) -> None:
    scalar = tmp_path / "scalar.yaml"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(MigrationError, match="object"):
        plan_schema_migration(scalar, migration_id="m", owner="o", environment="e")
    empty = tmp_path / "empty"
    empty.mkdir()
    manifest = plan_schema_migration(empty, migration_id="m", owner="o", environment="e")
    assert manifest.operations == ()
    current = {
        "apiVersion": "wyrmctl.com/v1",
        "kind": "DesiredState",
        "schemaVersion": 3,
        "metadata": {},
        "spec": {},
    }
    (empty / "current.yaml").write_text(yaml.safe_dump(current), encoding="utf-8")
    (empty / "legacy.yaml").write_text(yaml.safe_dump({"proxy_hosts": []}), encoding="utf-8")
    mixed = plan_schema_migration(empty, migration_id="m2", owner="o", environment="e")
    assert len(mixed.operations) == 1
    assert forward_repair(expected=[{"identity": "same"}], observed=[{"identity": "same"}]) == ()
