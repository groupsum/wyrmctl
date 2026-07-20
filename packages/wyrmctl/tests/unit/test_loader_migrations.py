from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from wyrmctl.errors import MigrationError, ValidationError
from wyrmctl.loader import load_desired_state
from wyrmctl.migrations import migrate_document, migrate_path
from wyrmctl.migrations.v2 import CURRENT as CURRENT_V2


def test_load_desired_state_full(desired_file: Path) -> None:
    state = load_desired_state(desired_file)
    assert len(state.proxy_hosts) == 1
    assert len(state.certificates) == 1
    assert len(state.access_lists) == 1


def test_load_desired_state_dns_records(tmp_path: Path) -> None:
    path = tmp_path / "dns.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "apiVersion": "wyrmctl.com/v1",
                "schemaVersion": 2,
                "dns_records": [
                    {
                        "provider": "namecheap",
                        "zone": "example.com",
                        "type": "A",
                        "name": "@",
                        "value": "192.0.2.10",
                        "meta": {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": "dns.root"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    state = load_desired_state(path)

    assert state.dns_records[0].natural_key == ("namecheap", "example.com", "@", "A")
    assert state.owners == frozenset({"workload-a"})


def test_load_rejects_duplicate_dns_record_identity_and_natural_key(tmp_path: Path) -> None:
    base = {
        "provider": "namecheap",
        "zone": "example.com",
        "type": "A",
        "name": "@",
        "value": "192.0.2.10",
        "meta": {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": "dns.root"},
    }
    path = tmp_path / "dns.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "apiVersion": "wyrmctl.com/v1",
                "schemaVersion": 2,
                "dns_records": [base, base | {"value": "192.0.2.11"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="duplicate meta.resource_id"):
        load_desired_state(path)

    path.write_text(
        yaml.safe_dump(
            {
                "apiVersion": "wyrmctl.com/v1",
                "schemaVersion": 2,
                "dns_records": [
                    base,
                    base | {"meta": {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": "dns.root-2"}},
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="duplicate dns_record natural key"):
        load_desired_state(path)


def test_load_rejects_missing_schema_header(tmp_path: Path, desired_doc) -> None:
    desired_doc.pop("apiVersion")
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(desired_doc), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_desired_state(path)


def test_load_rejects_unsupported_api_version(tmp_path: Path, desired_doc) -> None:
    desired_doc["apiVersion"] = "wyrmctl.com/v2"
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(desired_doc), encoding="utf-8")

    with pytest.raises(ValidationError, match="apiVersion"):
        load_desired_state(path)


def test_load_rejects_duplicate_domains(tmp_path: Path, desired_doc) -> None:
    duplicate = dict(desired_doc["proxy_hosts"][0])
    duplicate["meta"] = {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": "proxy.dupe"}
    desired_doc["proxy_hosts"].append(duplicate)
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(desired_doc), encoding="utf-8")
    with pytest.raises(ValidationError, match="duplicate proxy host domain"):
        load_desired_state(path)


def test_load_rejects_duplicate_metadata_identities_across_files(tmp_path: Path, desired_doc) -> None:
    first = dict(desired_doc)
    second = {
        "apiVersion": "wyrmctl.com/v1",
        "schemaVersion": 2,
        "proxy_hosts": [
            {
                "domain_names": ["other.example.com"],
                "forward_host": "other",
                "forward_port": 3000,
                "meta": {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": "proxy.app"},
            }
        ],
    }
    (tmp_path / "a.yaml").write_text(yaml.safe_dump(first), encoding="utf-8")
    (tmp_path / "b.yaml").write_text(yaml.safe_dump(second), encoding="utf-8")

    with pytest.raises(ValidationError, match="duplicate meta.resource_id"):
        load_desired_state(tmp_path)


def test_load_discovers_directory_files_in_stable_order(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    docs = {
        "b.yaml": ("proxy.b", "b.example.com"),
        "a.yaml": ("proxy.a", "a.example.com"),
        "nested/c.yaml": ("proxy.c", "c.example.com"),
    }
    for relative, (resource_id, domain) in docs.items():
        path = tmp_path / relative
        path.write_text(
            yaml.safe_dump(
                {
                    "apiVersion": "wyrmctl.com/v1",
                    "schemaVersion": 2,
                    "proxy_hosts": [
                        {
                            "domain_names": [domain],
                            "forward_host": "app",
                            "forward_port": 3000,
                            "meta": {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": resource_id},
                        }
                    ],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

    state = load_desired_state(tmp_path)

    assert [Path(path).name for path in state.source_files] == ["a.yaml", "b.yaml", "c.yaml"]
    assert [host.identity.resource_id for host in state.proxy_hosts] == ["proxy.a", "proxy.b", "proxy.c"]


@pytest.mark.parametrize("content", ["[not, an, object]\n", "proxy_hosts: [\n"])
def test_load_rejects_malformed_or_non_object_documents(tmp_path: Path, content: str) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValidationError):
        load_desired_state(path)


def test_migrate_legacy_document_adds_v1_headers() -> None:
    assert CURRENT_V2 == 2
    migrated, changed, before = migrate_document({"proxy_hosts": []})
    assert changed is True
    assert before is None
    assert migrated["apiVersion"] == "wyrmctl.com/v1"
    assert migrated["schemaVersion"] == 3
    assert migrated["kind"] == "DesiredState"
    assert migrated["spec"]["dnsRecords"] == []


def test_migrate_v1_document_adds_dns_records() -> None:
    migrated, changed, before = migrate_document({"apiVersion": "wyrmctl.com/v1", "schemaVersion": 1})
    assert changed is True
    assert before == 1
    assert migrated["schemaVersion"] == 3
    assert migrated["kind"] == "DesiredState"
    assert migrated["spec"]["dnsRecords"] == []


def test_load_v3_envelope_and_reject_invalid_v3(tmp_path: Path) -> None:
    path = tmp_path / "desired.yaml"
    document = {
        "apiVersion": "wyrmctl.com/v1",
        "kind": "DesiredState",
        "schemaVersion": 3,
        "metadata": {"name": "site", "owner": "owner"},
        "spec": {
            "proxyHosts": [
                {
                    "domain_names": ["app.example.com"],
                    "forward_host": "app",
                    "forward_port": 3000,
                    "meta": {"managed_by": "wyrmctl", "owner": "owner", "resource_id": "proxy.app"},
                }
            ]
        },
    }
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    state = load_desired_state(path)
    assert state.schema_version == 3 and state.proxy_hosts[0].identity.resource_id == "proxy.app"
    for update, message in (
        ({"kind": "Bad"}, "kind"),
        ({"spec": []}, "spec"),
        ({"spec": {"unknown": []}}, "unsupported fields"),
        ({"schemaVersion": "3"}, "integer"),
        ({"schemaVersion": True}, "integer"),
    ):
        path.write_text(yaml.safe_dump(document | update), encoding="utf-8")
        with pytest.raises(ValidationError, match=message):
            load_desired_state(path)


def test_migrate_path_check_and_write(tmp_path: Path) -> None:
    path = tmp_path / "legacy.yaml"
    path.write_text("proxy_hosts: []\n", encoding="utf-8")
    results = migrate_path(path, write=False)
    assert results[0].changed is True
    assert "apiVersion" not in path.read_text()
    migrate_path(path, write=True)
    assert "apiVersion" in path.read_text()


def test_migrate_rejects_unknown_future_version() -> None:
    with pytest.raises(MigrationError):
        migrate_document({"apiVersion": "wyrmctl.com/v1", "schemaVersion": 999})
