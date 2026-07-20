from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from wyrmctl.artifacts import (
    ApplyReport,
    LiveStateSnapshot,
    PlanArtifact,
    artifact_digest,
    build_plan_artifact,
    read_artifact,
    redact_artifact,
    sign_plan,
    validate_plan_binding,
    verify_plan,
    write_artifact,
)
from wyrmctl.artifacts.execution import plan_from_artifact
from wyrmctl.artifacts.models import ArtifactSignature
from wyrmctl.artifacts.retention import disposal_candidates
from wyrmctl.commands.artifacts import artifact_digest_command, artifact_inspect_command
from wyrmctl.commands.contracts import contract_check, contract_list, contract_show
from wyrmctl.commands.import_live import import_live
from wyrmctl.commands.lock import lock_check
from wyrmctl.commands.repository import repository_status, repository_validate
from wyrmctl.errors import ArtifactError, ValidationError
from wyrmctl.lockfile import build_lock, check_lock, lock_digest
from wyrmctl.repository import load_repository, repository_document


class FakePlan:
    def to_dict(self):
        return {
            "operations": [
                {"sequence": "10", "kind": "b", "action": "update"},
                {"sequence": 2, "kind": "a", "action": "create"},
                {"sequence": "bad", "kind": "z", "action": "noop"},
            ],
            "conflicts": [{"code": "z"}, {"code": "a"}],
        }


def _artifact(**overrides) -> PlanArtifact:
    values = {
        "artifact_id": "plan-1",
        "repository": "org/repo",
        "environment": "production",
        "commit": "abc",
        "desired_state_digest": "desired",
        "live_state_fingerprint": "live",
        "operations": (),
        "provider_capabilities": {"dns": 1},
        "api_profiles": {"npm": "profile"},
        "created_at": "2025-01-01T00:00:00Z",
    }
    values.update(overrides)
    return PlanArtifact(**values)


def test_artifact_models_build_and_binding() -> None:
    artifact = build_plan_artifact(
        FakePlan(),
        artifact_id="id",
        repository="org/repo",
        environment="production",
        commit="abc",
        desired_state_digest="desired",
        live_state_fingerprint="live",
        provider_capabilities={"dns": 1},
        api_profiles={"npm": "profile"},
    )
    assert [item["sequence"] for item in artifact.operations] == ["bad", 2, "10"]
    assert artifact.to_dict()["spec"]["conflicts"][0]["code"] == "a"
    assert artifact.digest.startswith("sha256:")
    snapshot = LiveStateSnapshot("org/repo", "prod", ({"id": 1},), observed_at="2025-01-01T00:00:00Z")
    assert snapshot.to_dict()["kind"] == "LiveStateSnapshot"
    assert snapshot.fingerprint.startswith("sha256:")
    report = ApplyReport("id", artifact.digest, "complete", (), {"ok": True})
    assert report.to_dict()["spec"]["status"] == "complete"
    validate_plan_binding(
        _artifact(),
        repository="org/repo",
        environment="production",
        commit="abc",
        desired_state_digest="desired",
        live_state_fingerprint="live",
        provider_capabilities={"dns": 1},
        api_profiles={"npm": "profile"},
    )
    cases = {
        "repository": {"repository": "other"},
        "environment": {"environment": "dev"},
        "commit": {"commit": "def"},
        "desired state": {"desired_state_digest": "other"},
        "live state": {"live_state_fingerprint": "other"},
        "provider capabilities": {"provider_capabilities": {}},
        "API profiles": {"api_profiles": {}},
    }
    base = {
        "repository": "org/repo",
        "environment": "production",
        "commit": "abc",
        "desired_state_digest": "desired",
        "live_state_fingerprint": "live",
        "provider_capabilities": {"dns": 1},
        "api_profiles": {"npm": "profile"},
    }
    for message, override in cases.items():
        with pytest.raises(ArtifactError, match=message):
            validate_plan_binding(_artifact(), **(base | override))
    expired = _artifact(expires_at="2025-01-02T00:00:00Z")
    with pytest.raises(ArtifactError, match="expired"):
        validate_plan_binding(expired, **base, now=datetime(2025, 1, 2, tzinfo=timezone.utc))
    validate_plan_binding(
        _artifact(expires_at="2099-01-01T00:00:00Z"),
        **base,
        now=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )


def test_artifact_codec_signing_redaction_and_retention(tmp_path: Path) -> None:
    artifact = _artifact()
    yaml_path = write_artifact(tmp_path / "plan.yaml", artifact.to_dict())
    json_path = write_artifact(tmp_path / "plan.json", artifact.to_dict())
    assert read_artifact(yaml_path)["kind"] == "PlanArtifact"
    assert read_artifact(json_path)["kind"] == "PlanArtifact"
    assert artifact_digest(read_artifact(json_path)) == artifact.digest
    assert artifact_inspect_command(str(json_path))["data"]["signed"] is False
    assert artifact_digest_command(str(json_path))["code"] == "ARTIFACT_DIGESTED"
    bad = tmp_path / "bad.yaml"
    bad.write_text("[x]", encoding="utf-8")
    with pytest.raises(ArtifactError, match="object"):
        read_artifact(bad)
    bad.write_text("[", encoding="utf-8")
    with pytest.raises(ArtifactError, match="failed to read"):
        read_artifact(bad)
    import wyrmctl.artifacts.codec as codec

    original_replace = codec.os.replace
    codec.os.replace = lambda *_args: (_ for _ in ()).throw(OSError("replace failed"))
    try:
        with pytest.raises(OSError, match="replace failed"):
            write_artifact(tmp_path / "failed.yaml", artifact.to_dict())
    finally:
        codec.os.replace = original_replace

    class Private:
        def sign(self, value: bytes) -> bytes:
            return b"signed:" + value

    class Public:
        def verify(self, signature: bytes, value: bytes) -> None:
            if signature != b"signed:" + value:
                raise ValueError("bad")

    signed = sign_plan(artifact, key_id="key", private_key=Private())
    assert signed.to_dict()["signature"]["keyId"] == "key"
    verify_plan(signed, trusted_keys={"key": Public()})
    verify_plan(artifact, trusted_keys={}, require_signature=False)
    with pytest.raises(ArtifactError, match="unsigned"):
        verify_plan(artifact, trusted_keys={})
    with pytest.raises(ArtifactError, match="unsupported"):
        verify_plan(_artifact(signature=ArtifactSignature("rsa", "key", "x", "now")), trusted_keys={})
    with pytest.raises(ArtifactError, match="untrusted"):
        verify_plan(signed, trusted_keys={})
    corrupt = _artifact(signature=ArtifactSignature("ed25519", "key", "!!!", "now"))
    with pytest.raises(ArtifactError, match="validation failed"):
        verify_plan(corrupt, trusted_keys={"key": Public()})
    assert redact_artifact({"token": "x", "nested": [{"Password": "x"}], "tuple": ({"ok": 1},)}) == {
        "token": "<redacted>",
        "nested": [{"Password": "<redacted>"}],
        "tuple": ({"ok": 1},),
    }
    old = tmp_path / "old"
    new = tmp_path / "new"
    old.write_text("x", encoding="utf-8")
    new.write_text("x", encoding="utf-8")
    now = datetime(2025, 1, 10, tzinfo=timezone.utc)
    os.utime(old, (now.timestamp() - 10 * 86400,) * 2)
    os.utime(new, (now.timestamp(),) * 2)
    assert disposal_candidates([new, old], retain_days=5, now=now)[0].age_days == 10
    with pytest.raises(ValueError, match="positive"):
        disposal_candidates([], retain_days=0)


def _repository(tmp_path: Path) -> Path:
    directory = tmp_path / ".wyrmctl"
    directory.mkdir()
    (directory / "prod.yaml").write_text(
        "apiVersion: wyrmctl.com/v1\nkind: DesiredState\nschemaVersion: 3\nmetadata: {}\nspec: {}\n", encoding="utf-8"
    )
    document = repository_document(
        "site",
        owners=["b", "a", "a"],
        environments={"production": {"main": "prod.yaml"}},
        domains=["Example.COM.", "example.com"],
    )
    path = directory / "repository.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def test_repository_lock_and_command_handlers(tmp_path: Path) -> None:
    path = _repository(tmp_path)
    repository = load_repository(path)
    assert repository.root == tmp_path.resolve()
    assert repository.environment("production").desired_state["main"].name == "prod.yaml"
    assert repository.domains == ("example.com",)
    assert repository_validate(str(path))["data"]["name"] == "site"
    assert repository_status(str(path), "production")["data"]["environment"] == "production"
    with pytest.raises(ValidationError, match="unknown repository environment"):
        repository.environment("missing")
    assert contract_list()["data"]["contracts"]["DesiredState"]["current"] == 3
    assert contract_show("DesiredState")["data"]["write"] == [3]
    assert contract_check(json.loads(json.dumps(repository.raw)))["code"] == "CONTRACT_COMPATIBLE"

    lock = build_lock(
        repository="org/repo",
        commit="abc",
        package_version="0.4.0",
        python_version="3.13",
        providers={},
        api_profiles={"npm": "profile"},
        inputs={"main": repository.digest},
    )
    assert lock_digest(lock).startswith("sha256:")
    assert check_lock(lock, lock).ok is True
    changed = json.loads(json.dumps(lock))
    changed["spec"]["source"]["commit"] = "def"
    changed["spec"]["extra"] = True
    del changed["spec"]["targets"]
    result = check_lock(lock, changed)
    assert result.ok is False and len(result.differences) == 3
    expected = tmp_path / "expected.yaml"
    actual = tmp_path / "actual.json"
    expected.write_text(yaml.safe_dump(lock), encoding="utf-8")
    actual.write_text(json.dumps(changed), encoding="utf-8")
    assert lock_check(str(expected), str(actual))["code"] == "LOCK_MISMATCH"
    scalar = tmp_path / "scalar.yaml"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="object"):
        lock_check(str(scalar), str(actual))


def test_repository_validation_errors(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="does not exist"):
        load_repository(tmp_path / "missing.yaml")
    path = _repository(tmp_path)
    base = yaml.safe_load(path.read_text(encoding="utf-8"))
    variants = (
        (base | {"kind": "PlanArtifact"}, "kind"),
        (base | {"metadata": []}, "metadata"),
        (base | {"metadata": {"name": ""}}, "metadata.name"),
        (base | {"spec": []}, "spec"),
        (base | {"spec": base["spec"] | {"owners": []}}, "owners"),
        (base | {"spec": base["spec"] | {"domains": {}}}, "domains"),
        (base | {"spec": base["spec"] | {"environments": {}}}, "environment"),
    )
    for value, message in variants:
        path.write_text(yaml.safe_dump(value), encoding="utf-8")
        with pytest.raises(ValidationError, match=message):
            load_repository(path)
    base["spec"]["environments"] = {"production": {"desiredState": {"main": "../outside.yaml"}}}
    path.write_text(yaml.safe_dump(base), encoding="utf-8")
    with pytest.raises(ValidationError, match="escapes"):
        load_repository(path)
    base["spec"]["environments"] = {"production": {"desiredState": {"main": "missing.yaml"}}}
    path.write_text(yaml.safe_dump(base), encoding="utf-8")
    with pytest.raises(ValidationError, match="does not exist"):
        load_repository(path)
    for environments, message in (
        ({"": {"desiredState": {}}}, "environment names"),
        ({"production": []}, "production"),
        ({"production": {"desiredState": []}}, "desiredState"),
        ({"production": {"desiredState": {"main": 1}}}, "non-empty string"),
    ):
        base["spec"]["environments"] = environments
        path.write_text(yaml.safe_dump(base), encoding="utf-8")
        with pytest.raises(ValidationError, match=message):
            load_repository(path)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ValidationError, match="failed to read"):
        load_repository(path)
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValidationError, match="must be an object"):
        load_repository(path)


def test_import_live_command() -> None:
    live = [
        {"identity": "owned", "owner": "me", "value": 1},
        {"identity": "foreign", "owner": "them", "value": 1},
        {"identity": "same", "value": 1},
        {"identity": "drift", "value": 2},
        {"identity": "unknown", "value": 1},
        {"identity": "", "value": 1},
    ]
    desired = [{"identity": "same", "value": 1}, {"identity": "drift", "value": 1}]
    values = import_live(live, desired, owner="me")["data"]["classifications"]
    assert {item["classification"] for item in values} == {
        "owned",
        "foreign-owned",
        "unmanaged-matching",
        "unmanaged-drifting",
        "ambiguous",
    }


def _plan_document(operations=None, conflicts=None):
    return {
        "apiVersion": "wyrmctl.com/v1",
        "kind": "PlanArtifact",
        "schemaVersion": 1,
        "metadata": {"id": "id", "repository": "org/repo", "environment": "prod", "createdAt": "now"},
        "spec": {
            "operations": [] if operations is None else operations,
            "conflicts": [] if conflicts is None else conflicts,
        },
    }


def test_plan_artifact_rehydration_and_guards() -> None:
    meta = {"managed_by": "wyrmctl", "owner": "o", "resource_id": "r"}
    desired_by_kind = {
        "proxy_host": {"domain_names": ["app.example.com"], "forward_host": "app", "forward_port": 80, "meta": meta},
        "certificate": {"name": "cert", "domain_names": ["app.example.com"], "meta": meta},
        "access_list": {"name": "acl", "api_payload": {}, "meta": meta},
        "stream": {"incoming_port": 443, "forward_host": "app", "forward_port": 443, "meta": meta},
    }
    existing_by_kind = {
        "proxy_host": {"id": 1, "domain_names": ["app.example.com"], "meta": meta},
        "certificate": {"id": 2, "name": "cert", "domain_names": ["app.example.com"], "meta": meta},
        "access_list": {"id": 3, "name": "acl", "meta": meta},
        "stream": {"id": 4, "incoming_port": 443, "meta": meta},
    }
    operations = [
        {
            "action": "noop",
            "kind": kind,
            "desired": desired,
            "existing": {"raw": existing_by_kind[kind]},
            "reason": "same",
            "diff": {},
        }
        for kind, desired in desired_by_kind.items()
    ]
    plan = plan_from_artifact(_plan_document(operations, [{"code": "blocked", "message": "blocked", "kind": "stream"}]))
    assert len(plan.operations) == 4 and plan.conflicts[0].code == "blocked"
    no_existing = plan_from_artifact(
        _plan_document([{"action": "noop", "kind": "stream", "desired": desired_by_kind["stream"], "existing": None}])
    )
    assert no_existing.operations[0].existing is None
    for document, message in (
        ({"kind": "Bad", "schemaVersion": 1}, "requires"),
        (_plan_document() | {"spec": []}, "spec"),
        (_plan_document(operations={}), "operations"),
        (_plan_document([{"action": "bad", "kind": "stream"}]), "invalid operation"),
        (_plan_document([{"action": "delete", "kind": "stream"}]), "requires an NpmctlMigration"),
        (_plan_document([{"action": "noop", "kind": "stream", "desired": []}]), "must be an object"),
        (_plan_document([{"action": "noop", "kind": "stream", "existing": {}}]), "existing.raw"),
        (_plan_document(conflicts={}), "conflicts"),
    ):
        with pytest.raises(ArtifactError, match=message):
            plan_from_artifact(document)


def test_lock_rejects_other_known_contract_kind() -> None:
    plan = _artifact().to_dict()
    with pytest.raises(ValidationError, match="NpmctlLock"):
        check_lock(plan, plan)
