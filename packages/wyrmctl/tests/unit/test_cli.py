from __future__ import annotations

import json
from pathlib import Path

import pytest

from wyrmctl.cli import (
    EXIT_API,
    EXIT_CAPABILITY,
    EXIT_CONFLICT,
    EXIT_OK,
    EXIT_USAGE_OR_VALIDATION,
    main,
)
from wyrmctl.errors import ApiError


def test_validate_command_text_and_json_output(desired_file: Path, capsys) -> None:
    assert main(["validate", str(desired_file)]) == EXIT_OK
    text = capsys.readouterr().out
    assert "desired state valid" in text
    assert "proxy hosts: 1" in text
    assert "dns records: 0" in text

    assert main(["--output", "json", "validate", str(desired_file)]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["proxy_hosts"] == 1
    assert payload["certificates"] == 1
    assert payload["access_lists"] == 1
    assert payload["dns_records"] == 0


def test_schema_command_outputs_capabilities_json(tmp_path: Path, capsys) -> None:
    schema = {
        "openapi": "3.0.0",
        "paths": {
            "/nginx/proxy-hosts": {"get": {}, "post": {}},
            "/nginx/proxy-hosts/{id}": {"put": {}, "delete": {}},
        },
    }
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    assert main(["--output", "json", "schema", "capabilities", "--schema", str(schema_path)]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["proxy_hosts"]["create"] is True
    assert payload["proxy_hosts"]["delete"] is True
    assert payload["certificates"]["list"] is False


def test_missing_api_arguments_exit_with_usage_error(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["health"])

    assert exc_info.value.code == EXIT_USAGE_OR_VALIDATION
    assert "--base-url, --identity, and --secret are required" in capsys.readouterr().err


def test_bad_command_line_option_combination_is_rejected(tmp_path: Path, capsys) -> None:
    path = tmp_path / "legacy.yaml"
    path.write_text("proxy_hosts: []\n", encoding="utf-8")

    assert main(["migrate", str(path), "--write", "--check"]) == EXIT_USAGE_OR_VALIDATION

    assert "cannot be combined" in capsys.readouterr().err


def test_json_error_output_shape_for_validation_errors(tmp_path: Path, capsys) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("apiVersion: wrong\nschemaVersion: 2\n", encoding="utf-8")

    assert main(["--output", "json", "validate", str(path)]) == EXIT_USAGE_OR_VALIDATION
    payload = json.loads(capsys.readouterr().err)
    assert payload == {
        "ok": False,
        "error": {
            "code": "validation_error",
            "message": f"{path}.apiVersion must be 'wyrmctl.com/v1'; run wyrmctl migrate if needed",
        },
    }


def test_cli_redacts_secret_in_api_errors(monkeypatch, capsys) -> None:
    class FailingClient:
        def __init__(self, *, base_url: str, identity: str, secret: str, timeout_s: float) -> None:
            self.secret = secret

        def health(self):
            raise ApiError(f"backend echoed secret {self.secret}")

    monkeypatch.setattr("wyrmctl.cli.NpmClient", FailingClient)

    assert (
        main(
            [
                "--base-url",
                "http://npm.test/api",
                "--identity",
                "admin@example.com",
                "--secret",
                "supersecret",
                "health",
            ]
        )
        == EXIT_API
    )

    err = capsys.readouterr().err
    assert "supersecret" not in err
    assert "***" in err


def test_dns_cli_uses_discovered_provider(monkeypatch, capsys) -> None:
    class Provider:
        name = "namecheap"

        def zones(self):
            return ("example.com",)

        def records(self, zone: str):
            return ({"zone": zone, "name": "@", "type": "A", "value": "192.0.2.10"},)

    class Registry:
        dns_providers = {"namecheap": Provider()}

        def to_dict(self):
            return {"resource_providers": [], "certificate_providers": [], "dns_providers": ["namecheap"]}

    monkeypatch.setattr("wyrmctl.cli.PluginRegistry.discover", lambda: Registry())

    assert main(["--output", "json", "plugins", "list"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["plugins"]["dns_providers"] == ["namecheap"]

    assert main(["--output", "json", "dns", "providers"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["providers"] == ["namecheap"]

    assert main(["--output", "json", "dns", "doctor", "--provider", "namecheap"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["ok"] is True

    assert main(["--output", "json", "dns", "zones", "--provider", "namecheap"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["zones"] == ["example.com"]

    assert main(["--output", "json", "dns", "records", "--provider", "namecheap", "--zone", "example.com"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["records"][0]["name"] == "@"


def test_dns_cli_rejects_unknown_provider(monkeypatch) -> None:
    class Registry:
        dns_providers = {}

    monkeypatch.setattr("wyrmctl.cli.PluginRegistry.discover", lambda: Registry())

    assert main(["dns", "doctor", "--provider", "missing"]) == EXIT_USAGE_OR_VALIDATION


def test_npm_only_plan_does_not_discover_dns_providers(monkeypatch, fake_npm_server, desired_file: Path) -> None:
    _, base_url = fake_npm_server

    def fail_discover():
        raise AssertionError("DNS provider discovery should be skipped without dns_records")

    monkeypatch.setattr("wyrmctl.cli.PluginRegistry.discover", fail_discover)
    common = ["--base-url", base_url, "--identity", "admin@example.com", "--secret", "changeme"]

    assert main([*common, "plan", str(desired_file), "--owner", "workload-a"]) == EXIT_OK


def test_plan_and_apply_include_dns_operations(monkeypatch, fake_npm_server, tmp_path: Path, capsys) -> None:
    _, base_url = fake_npm_server
    desired = tmp_path / "desired.yaml"
    desired.write_text(
        """
apiVersion: wyrmctl.com/v1
schemaVersion: 2
dns_records:
  - provider: namecheap
    zone: example.com
    type: A
    name: "@"
    value: 192.0.2.10
    ttl: 300
    meta:
      managed_by: wyrmctl
      owner: site
      resource_id: dns.apex
""",
        encoding="utf-8",
    )

    class Provider:
        name = "namecheap"

        def __init__(self) -> None:
            self.applied = []

        def zones(self):
            return ("example.com",)

        def records(self, zone: str):
            assert zone == "example.com"
            return ()

        def apply_records(self, zone: str, records: tuple[dict, ...]) -> None:
            self.applied.append((zone, records))

    provider = Provider()

    class Registry:
        dns_providers = {"namecheap": provider}

    monkeypatch.setattr("wyrmctl.cli.PluginRegistry.discover", lambda: Registry())
    common = ["--base-url", base_url, "--identity", "admin@example.com", "--secret", "changeme"]

    assert main([*common, "--output", "json", "plan", str(desired), "--owner", "site"]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["dns"]["operations"][0]["action"] == "create"
    assert payload["summary"]["dns"]["create"] == 1

    assert main([*common, "apply", str(desired), "--owner", "site"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "dns mutations: 1" in out
    assert provider.applied[0][1][0]["value"] == "192.0.2.10"


def test_dns_plan_readonly_provider_conflicts(monkeypatch, fake_npm_server, tmp_path: Path, capsys) -> None:
    _, base_url = fake_npm_server
    desired = tmp_path / "desired.yaml"
    desired.write_text(
        """
apiVersion: wyrmctl.com/v1
schemaVersion: 2
dns_records:
  - provider: namecheap
    zone: example.com
    type: A
    name: "@"
    value: 192.0.2.10
    meta:
      managed_by: wyrmctl
      owner: site
      resource_id: dns.apex
""",
        encoding="utf-8",
    )

    class Provider:
        name = "namecheap"

        def zones(self):
            return ("example.com",)

        def records(self, zone: str):
            return ({"provider": "namecheap", "zone": "example.com", "name": "@", "type": "A", "value": "192.0.2.9"},)

    class Registry:
        dns_providers = {"namecheap": Provider()}

    monkeypatch.setattr("wyrmctl.cli.PluginRegistry.discover", lambda: Registry())
    common = ["--base-url", base_url, "--identity", "admin@example.com", "--secret", "changeme"]

    assert main([*common, "plan", str(desired), "--owner", "site"]) == EXIT_CONFLICT
    out = capsys.readouterr().out
    assert "read_only_dns_provider" in out
    assert "~ value: '192.0.2.9' -> '192.0.2.10'" in out


def test_exit_code_mapping_for_conflict_api_capability_and_migration_errors(
    fake_npm_server, desired_file: Path, tmp_path: Path, capsys
) -> None:
    state, base_url = fake_npm_server
    state.create(
        "proxy_hosts",
        {
            "domain_names": ["app.example.com"],
            "forward_host": "app",
            "forward_port": 3000,
            "forward_scheme": "http",
            "access_list_id": 0,
            "certificate_id": 0,
            "ssl_forced": 1,
            "caching_enabled": 0,
            "block_exploits": 1,
            "advanced_config": "",
            "meta": {},
            "allow_websocket_upgrade": 1,
            "http2_support": 1,
            "enabled": 1,
            "locations": [],
            "hsts_enabled": 0,
            "hsts_subdomains": 0,
        },
    )
    common = ["--base-url", base_url, "--identity", "admin@example.com", "--secret", "changeme"]
    assert main([*common, "plan", str(desired_file)]) == EXIT_CONFLICT

    missing_caps = tmp_path / "missing-caps.json"
    missing_caps.write_text(json.dumps({"openapi": "3.0.0", "paths": {}}), encoding="utf-8")
    assert main(["schema", "check", "--schema", str(missing_caps)]) == EXIT_CAPABILITY

    future = tmp_path / "future.yaml"
    future.write_text("apiVersion: wyrmctl.com/v1\nschemaVersion: 999\n", encoding="utf-8")
    assert main(["migrate", str(future)]) == EXIT_USAGE_OR_VALIDATION

    class FailingClient:
        def __init__(self, **_: object) -> None:
            pass

        def health(self):
            raise ApiError("backend failed")

    from wyrmctl import cli

    original_client = cli.NpmClient
    try:
        cli.NpmClient = FailingClient
        assert main([*common, "health"]) == EXIT_API
    finally:
        cli.NpmClient = original_client

    capsys.readouterr()
