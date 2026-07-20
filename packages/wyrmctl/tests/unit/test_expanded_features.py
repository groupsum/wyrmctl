from __future__ import annotations

import json
from pathlib import Path

import yaml

from wyrmctl.cli import EXIT_CONFLICT, EXIT_OK, EXIT_USAGE_OR_VALIDATION, main
from wyrmctl.client.access_lists import list_access_lists
from wyrmctl.client.proxy_hosts import list_proxy_hosts
from wyrmctl.diagnostics import environment_report
from wyrmctl.loader import load_desired_state
from wyrmctl.logging import redact
from wyrmctl.models import ExistingState, ResourceKind
from wyrmctl.operational import compliance_artifacts, validate_plan_output
from wyrmctl.plugins import PluginRegistry
from wyrmctl.planner import compute_plan
from wyrmctl.schema import Capabilities
from wyrmctl.validation import load_desired_state as validation_load_desired_state


def _expanded_doc() -> dict:
    meta = {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": "resource.one"}
    return {
        "apiVersion": "wyrmctl.com/v1",
        "schemaVersion": 2,
        "redirection_hosts": [
            {
                "domain_names": ["Old.Example.Com"],
                "forward_domain_name": "new.example.com",
                "meta": meta | {"resource_id": "redir.old"},
            }
        ],
        "dead_hosts": [{"domain_names": ["gone.example.com"], "meta": meta | {"resource_id": "dead.gone"}}],
        "streams": [
            {
                "incoming_port": 5432,
                "forward_host": "db",
                "forward_port": 5432,
                "protocol": "tcp",
                "meta": meta | {"resource_id": "stream.db"},
            }
        ],
        "users": [{"email": "Ops@Example.Com", "meta": meta | {"resource_id": "user.ops"}}],
        "settings": [
            {"name": "default-site", "value": "congratulations", "meta": meta | {"resource_id": "setting.default-site"}}
        ],
    }


def test_expanded_desired_resources_plan_and_validate(tmp_path: Path) -> None:
    path = tmp_path / "expanded.yaml"
    path.write_text(yaml.safe_dump(_expanded_doc(), sort_keys=False), encoding="utf-8")

    desired = load_desired_state(path)
    assert len(desired.redirection_hosts) == 1
    assert len(desired.dead_hosts) == 1
    assert len(desired.streams) == 1
    assert len(desired.users) == 1
    assert len(desired.settings) == 1
    assert validation_load_desired_state(path).users[0].natural_key == "ops@example.com"

    plan = compute_plan(desired=desired, existing=ExistingState(), capabilities=Capabilities.full_for_tests())
    assert plan.ok
    assert {op.kind for op in plan.by_action("create")} == {
        ResourceKind.REDIRECTION_HOST,
        ResourceKind.DEAD_HOST,
        ResourceKind.STREAM,
        ResourceKind.USER,
        ResourceKind.SETTING,
    }


def test_expanded_cli_operator_surface(fake_npm_server, tmp_path: Path, capsys) -> None:
    state, base_url = fake_npm_server
    state.audit_log.append({"message": "created proxy host"})
    desired = tmp_path / "desired.yaml"
    desired.write_text(yaml.safe_dump(_expanded_doc(), sort_keys=False), encoding="utf-8")
    common = ["--base-url", base_url, "--identity", "admin@example.com", "--secret", "changeme"]

    assert main(["--output", "json", "version"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["version"]

    assert main(["completion", "bash"]) == EXIT_OK
    assert "complete -W" in capsys.readouterr().out

    assert main(["--output", "json", *common, "doctor"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["ok"] is True

    assert main(["--output", "json", *common, "audit-log", "--since", "24h"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["entries"] == [{"message": "created proxy host"}]

    assert main(["--output", "json", *common, "drift", str(desired)]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["drift_count"] == 5

    report = tmp_path / "apply-report.json"
    rollback = tmp_path / "rollback.json"
    audit = tmp_path / "audit.json"
    backup_dir = tmp_path / "backups"
    assert (
        main(
            [
                "--output",
                "json",
                *common,
                "apply",
                str(desired),
                "--backup-dir",
                str(backup_dir),
                "--report",
                str(report),
                "--rollback-plan",
                str(rollback),
                "--audit-log",
                str(audit),
                "--validate-output",
            ]
        )
        == EXIT_OK
    )
    assert report.exists()
    assert rollback.exists()
    assert audit.exists()
    assert list(backup_dir.glob("wyrmctl-state-*.json"))
    capsys.readouterr()

    assert main(["--output", "json", *common, "drift", str(desired)]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["drift_count"] == 0


def test_config_env_compliance_plugins_wrappers_and_validation(tmp_path: Path, capsys) -> None:
    config = tmp_path / "wyrmctl.toml"
    config.write_text("[wyrmctl]\nsecret='supersecret'\n", encoding="utf-8")
    assert main(["--config", str(config), "--output", "json", "doctor"]) == EXIT_USAGE_OR_VALIDATION
    assert json.loads(capsys.readouterr().out)["config"]["secret"] is True

    assert environment_report({"NPM_SECRET": "supersecret"})["NPM_SECRET"]["value"] == "***"
    assert "supersecret" not in redact("secret=supersecret token=abc")

    paths = compliance_artifacts(tmp_path / "compliance", package_name="wyrmctl", version="0.2.0")
    assert {path.name for path in paths} == {
        "sbom.spdx.json",
        "provenance.intoto.json",
        "security-scan.json",
        "dependency-vulnerability.json",
        "release-gates.json",
    }

    validate_plan_output({"ok": True, "existing_count": 0, "summary": {}, "operations": [], "conflicts": []})

    registry = PluginRegistry()
    registry.register_resource_provider("custom", object())  # type: ignore[arg-type]
    registry.register_certificate_provider("certs", object())  # type: ignore[arg-type]
    registry.register_dns_provider("namecheap", object())  # type: ignore[arg-type]
    assert "custom" in registry.resource_providers
    assert "certs" in registry.certificate_providers
    assert "namecheap" in registry.dns_providers
    assert registry.to_dict()["dns_providers"] == ["namecheap"]

    class Client:
        def list_resource(self, kind: ResourceKind):
            return (kind,)

    assert list_proxy_hosts(Client()) == (ResourceKind.PROXY_HOST,)  # type: ignore[arg-type]
    assert list_access_lists(Client()) == (ResourceKind.ACCESS_LIST,)  # type: ignore[arg-type]


def test_cli_plan_output_schema_validation_rejects_conflicts(fake_npm_server, desired_file: Path) -> None:
    state, base_url = fake_npm_server
    state.create("proxy_hosts", {"domain_names": ["app.example.com"], "meta": {}, "id": 999})
    result = main(
        [
            "--base-url",
            base_url,
            "--identity",
            "admin@example.com",
            "--secret",
            "changeme",
            "plan",
            str(desired_file),
            "--validate-output",
        ]
    )
    assert result == EXIT_CONFLICT
