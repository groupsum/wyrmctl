from __future__ import annotations

import argparse
import ast
import json
import runpy
import time
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

import pytest

import wyrmctl.adoption as adoption
import wyrmctl.client.auth as auth
import wyrmctl.migrations.v1 as migration_v1
from wyrmctl.apply import ApplyEngine, _ordered_operations, _updateable_existing_payload
from wyrmctl.cli import (
    EXIT_API,
    EXIT_CAPABILITY,
    EXIT_CONFLICT,
    EXIT_OK,
    EXIT_USAGE_OR_VALIDATION,
    _dispatch,
    _schema_command,
    main,
)
from wyrmctl.client.base import NpmClient, _extract_token, _parse_created, _redact, _with_npm_2104_compatibility
from wyrmctl.client.certificates import list_certificates
from wyrmctl.config import apply_config, load_config
from wyrmctl.errors import ApiError, CapabilityError, ConflictError, MigrationError, NpmctlError, ValidationError
from wyrmctl.loader import load_desired_state
from wyrmctl.metadata import ManagedIdentity, identity_from_meta, merge_managed_meta, validate_metadata
from wyrmctl.models import (
    DesiredAccessList,
    DesiredCertificate,
    DesiredGenericResource,
    DesiredProxyHost,
    DesiredState,
    ExistingResource,
    ExistingState,
    PlanAction,
    ResourceKind,
    canonical_domain_set,
    canonicalize_domain,
    desired_by_resource_id,
    mapping_or_empty,
    optional_int,
    require_mapping,
    resource_kind_of,
    validate_forward_host,
    validate_name,
    validate_port,
    validate_scheme,
    validate_toggle,
)
from wyrmctl.operational import (
    _artifact_subjects,
    _call_name,
    _dependency_audit,
    _security_scan,
    compliance_artifacts,
    drift_report,
    rollback_plan,
    transaction_report,
    validate_compliance_gate,
    validate_plan_output,
)
from wyrmctl.output import format_plan_text, write_error, write_output
from wyrmctl.planner import (
    Plan,
    PlanConflict,
    PlanOperation,
    PlannerOptions,
    _coerce_existing_value,
    _normalized_payload,
    compute_plan,
    diff_resource,
)
from wyrmctl.plugins import (
    PluginRegistry,
    _validate_certificate_provider,
    _validate_dns_provider,
    _validate_resource_provider,
)
from wyrmctl.schema import Capabilities, ResourceCapabilities, _methods, load_openapi_schema

META = {"managed_by": "wyrmctl", "owner": "owner-a", "resource_id": "rid"}


class Response:
    def __init__(self, status_code: int, payload: Any = None, *, text: str = "", bad_json: bool = False) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.content = b"" if payload is None and not text else b"x"
        self.bad_json = bad_json

    def json(self) -> Any:
        if self.bad_json:
            raise ValueError("bad json")
        return self._payload


class Session:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> Response:
        self.calls.append({"method": method, "url": url, **kwargs})
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def _client(responses: list[Any]) -> tuple[NpmClient, Session]:
    client = NpmClient(base_url="http://npm.test/api/", identity="admin@example.com", secret="secret")
    session = Session(responses)
    client.session = session  # type: ignore[assignment]
    return client, session


def _proxy(**overrides: Any) -> DesiredProxyHost:
    return DesiredProxyHost.from_mapping(_proxy_raw(**overrides), path="proxy")


def _proxy_raw(**overrides: Any) -> dict[str, Any]:
    raw = {
        "domain_names": ["app.example.com"],
        "forward_host": "app",
        "forward_port": 3000,
        "meta": META,
    }
    raw.update(overrides)
    return raw


def _existing_proxy(**overrides: Any) -> ExistingResource:
    raw = _proxy().to_payload()
    raw.update({"id": 1, "meta": dict(META)})
    raw.update(overrides)
    return ExistingResource.from_proxy_host(raw)


def _generic(kind: ResourceKind, **overrides: Any) -> DesiredGenericResource:
    base: dict[str, Any] = {"meta": META}
    if kind in {ResourceKind.REDIRECTION_HOST, ResourceKind.DEAD_HOST}:
        base["domain_names"] = ["old.example.com"]
    elif kind == ResourceKind.STREAM:
        base["incoming_port"] = 8443
    elif kind == ResourceKind.USER:
        base["email"] = "Ops@Example.Com"
    elif kind == ResourceKind.SETTING:
        base["name"] = "default-site"
    base.update(overrides)
    return DesiredGenericResource.from_mapping(kind, base, path=kind.value)


def test_public_wrapper_modules_and_python_m_entrypoint(monkeypatch) -> None:
    assert adoption.compute_plan is compute_plan
    assert auth.NpmClient is NpmClient
    assert migration_v1.CURRENT == 1

    class Client:
        def list_resource(self, kind: ResourceKind) -> tuple[ResourceKind]:
            return (kind,)

    assert list_certificates(Client()) == (ResourceKind.CERTIFICATE,)  # type: ignore[arg-type]
    monkeypatch.setattr("wyrmctl.cli.main", lambda: 7)
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("wyrmctl.__main__", run_name="__main__")
    assert exc_info.value.code == 7


def test_model_validation_edges_and_resource_helpers() -> None:
    assert canonical_domain_set(None, path="domains", allow_empty=True) == ()
    assert validate_forward_host("[::1]", path="host") == "[::1]"
    assert validate_toggle(True, path="toggle") == 1
    assert optional_int(None, path="x") is None
    assert require_mapping({"a": 1}, path="x") == {"a": 1}
    assert mapping_or_empty(None, path="x") == {}
    assert ManagedIdentity("owner", "res").to_dict() == {"owner": "owner", "resource_id": "res"}

    invalid = [
        lambda: canonicalize_domain(1, path="d"),
        lambda: canonicalize_domain("", path="d"),
        lambda: canonicalize_domain("a" * 254, path="d"),
        lambda: canonicalize_domain("*.com", path="d"),
        lambda: canonical_domain_set("bad", path="d"),
        lambda: canonical_domain_set([], path="d"),
        lambda: validate_name(1, path="n"),
        lambda: validate_name("bad$", path="n"),
        lambda: validate_forward_host(1, path="h"),
        lambda: validate_forward_host("", path="h"),
        lambda: validate_port(True, path="p"),
        lambda: validate_port(0, path="p"),
        lambda: optional_int(True, path="i"),
        lambda: optional_int(-1, path="i"),
        lambda: validate_scheme(1, path="s"),
        lambda: require_mapping([], path="m"),
        lambda: mapping_or_empty([], path="m"),
        lambda: validate_metadata({"managed_by": "other"}, path="meta"),
        lambda: validate_metadata({"managed_by": "wyrmctl", "owner": "", "resource_id": "r"}, path="meta"),
        lambda: validate_metadata({"managed_by": "wyrmctl", "owner": "o", "resource_id": ""}, path="meta"),
        lambda: DesiredProxyHost.from_mapping({}, path="proxy"),
        lambda: DesiredProxyHost.from_mapping(_proxy_raw(use_default_location="yes"), path="proxy"),
        lambda: DesiredProxyHost.from_mapping(_proxy_raw(ipv6="yes"), path="proxy"),
        lambda: DesiredProxyHost.from_mapping(_proxy_raw(access_list_ref=1), path="proxy"),
        lambda: DesiredProxyHost.from_mapping(_proxy_raw(certificate_ref=1), path="proxy"),
        lambda: DesiredProxyHost.from_mapping(_proxy_raw(certificate_id=1, certificate_ref="cert"), path="proxy"),
        lambda: DesiredCertificate.from_mapping({}, path="cert"),
        lambda: DesiredCertificate.from_mapping(
            {"name": "cert", "domain_names": ["example.com"], "meta": META, "certificate_type": ""},
            path="cert",
        ),
        lambda: DesiredAccessList.from_mapping({}, path="acl"),
    ]
    for call in invalid:
        with pytest.raises(ValidationError):
            call()

    assert identity_from_meta([]) is None
    assert identity_from_meta({"managed_by": "other"}) is None
    assert identity_from_meta({"managed_by": "wyrmctl", "owner": 1, "resource_id": "r"}) is None
    assert identity_from_meta({"managed_by": "wyrmctl", "owner": "bad space", "resource_id": "r"}) is None
    assert merge_managed_meta(None, META)["owner"] == "owner-a"
    from wyrmctl.diagnostics import environment_report

    assert environment_report({"NPM_SECRET": ""})["NPM_SECRET"]["value"] == ""


def test_generic_resource_model_edges_and_state_accessors() -> None:
    redir = _generic(ResourceKind.REDIRECTION_HOST, forward_domain_name="New.Example.Com")
    dead = _generic(ResourceKind.DEAD_HOST)
    stream = _generic(ResourceKind.STREAM, forward_host="svc", forward_port=443, protocol="udp")
    user = _generic(ResourceKind.USER)
    setting = _generic(ResourceKind.SETTING, value="ok")
    setting_without_value = _generic(ResourceKind.SETTING)
    desired = DesiredState(
        proxy_hosts=(_proxy(),),
        certificates=(
            DesiredCertificate.from_mapping({"name": "c", "domain_names": ["c.example.com"], "meta": META}, path="c"),
        ),
        access_lists=(DesiredAccessList.from_mapping({"name": "a", "meta": META}, path="a"),),
        redirection_hosts=(redir,),
        dead_hosts=(dead,),
        streams=(stream,),
        users=(user,),
        settings=(setting,),
    )
    existing = ExistingState(
        proxy_hosts=(_existing_proxy(),),
        certificates=(ExistingResource.from_certificate({"id": 2, "provider": "p", "domains": ["c.example.com"]}),),
        access_lists=(ExistingResource.from_access_list({"id": 3}),),
        redirection_hosts=(
            ExistingResource.from_generic(ResourceKind.REDIRECTION_HOST, {"id": 4, "domain_names": []}),
        ),
        streams=(ExistingResource.from_generic(ResourceKind.STREAM, {"id": 5, "tcp_forwarding": 9000}),),
        users=(ExistingResource.from_generic(ResourceKind.USER, {"id": 6, "email": "u@example.com"}),),
        settings=(ExistingResource.from_generic(ResourceKind.SETTING, {"id": 7, "key": "theme"}),),
    )
    for kind in ResourceKind:
        assert isinstance(desired.resources_by_kind(kind), tuple)
        assert isinstance(existing.resources_by_kind(kind), tuple)
    assert desired.owners == frozenset({"owner-a"})
    assert resource_kind_of(_proxy()) == ResourceKind.PROXY_HOST
    assert resource_kind_of(_existing_proxy()) == ResourceKind.PROXY_HOST
    assert desired_by_resource_id(desired.resources())[(ResourceKind.PROXY_HOST, "owner-a", "rid")]
    assert stream.to_payload()["protocol"] == "udp"
    assert "value" not in setting_without_value.to_payload()
    assert DesiredGenericResource.from_mapping(
        ResourceKind.DEAD_HOST, {"domain_names": ["dead.example.com"], "meta": META}, path="dead"
    ).domain_names

    bad_cases = [
        (ResourceKind.REDIRECTION_HOST, {}),
        (ResourceKind.STREAM, {}),
        (ResourceKind.STREAM, {"incoming_port": 1, "protocol": "icmp"}),
        (ResourceKind.USER, {}),
        (ResourceKind.USER, {"email": "bad"}),
        (ResourceKind.SETTING, {}),
    ]
    for kind, raw in bad_cases:
        with pytest.raises(ValidationError):
            DesiredGenericResource.from_mapping(kind, {"meta": META} | raw, path=kind.value)
    with pytest.raises(ValidationError):
        DesiredGenericResource.from_mapping(ResourceKind.STREAM, {"incoming_port": 8000}, path="stream")
    with pytest.raises(ValidationError):
        DesiredGenericResource.from_mapping(ResourceKind.PROXY_HOST, {"meta": META}, path="generic")
    with pytest.raises(ValidationError):
        ExistingResource.from_proxy_host({"id": True, "domain_names": []})
    assert (
        ExistingResource.from_generic(ResourceKind.SETTING, {"id": "default-site", "name": "Default Site"}).id
        == "default-site"
    )
    for raw in ({"id": ""}, {"id": 0}, {"id": "not-an-int", "domain_names": []}):
        with pytest.raises(ValidationError):
            if "domain_names" in raw:
                ExistingResource.from_proxy_host(raw)
            else:
                ExistingResource.from_generic(ResourceKind.SETTING, raw)
    assert DesiredState().resources_by_kind("bad") == ()  # type: ignore[arg-type]
    assert ExistingState().resources_by_kind("bad") == ()  # type: ignore[arg-type]


def test_loader_error_edges(tmp_path: Path, monkeypatch) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(ValidationError, match="does not exist"):
        load_desired_state(missing)
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValidationError, match="contains no YAML"):
        load_desired_state(empty)
    unsupported = tmp_path / "desired.txt"
    unsupported.write_text("x", encoding="utf-8")
    with pytest.raises(ValidationError, match="unsupported"):
        load_desired_state(unsupported)
    invalid_json = tmp_path / "bad.json"
    invalid_json.write_text("{", encoding="utf-8")
    with pytest.raises(ValidationError, match="failed to parse"):
        load_desired_state(invalid_json)
    scalar = tmp_path / "scalar.yaml"
    scalar.write_text("- item\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="must contain"):
        load_desired_state(scalar)
    empty_doc = tmp_path / "empty-doc.yaml"
    empty_doc.write_text("", encoding="utf-8")
    with pytest.raises(ValidationError, match="apiVersion"):
        load_desired_state(empty_doc)
    header = tmp_path / "header.yaml"
    header.write_text("apiVersion: bad\nschemaVersion: 2\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="apiVersion"):
        load_desired_state(header)
    header.write_text("apiVersion: wyrmctl.com/v1\nschemaVersion: 999\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="schemaVersion"):
        load_desired_state(header)
    header.write_text("apiVersion: wyrmctl.com/v1\nschemaVersion: 2\nproxy_hosts: {}\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="proxy_hosts"):
        load_desired_state(header)

    original = Path.read_text

    def fail_read(self: Path, *args: Any, **kwargs: Any) -> str:
        if self.name == "io.yaml":
            raise OSError("denied")
        return original(self, *args, **kwargs)

    io_path = tmp_path / "io.yaml"
    io_path.write_text("apiVersion: wyrmctl.com/v1\nschemaVersion: 2\n", encoding="utf-8")
    monkeypatch.setattr(Path, "read_text", fail_read)
    with pytest.raises(ValidationError, match="failed to read"):
        load_desired_state(io_path)
    monkeypatch.undo()
    duplicate = tmp_path / "duplicate.yaml"
    duplicate.write_text(
        "apiVersion: wyrmctl.com/v1\nschemaVersion: 2\nsettings:\n"
        "- name: theme\n  meta: {managed_by: wyrmctl, owner: owner-a, resource_id: one}\n"
        "- name: theme\n  meta: {managed_by: wyrmctl, owner: owner-a, resource_id: two}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="duplicate setting natural key"):
        load_desired_state(duplicate)
    bad_ref = tmp_path / "bad-ref.yaml"
    bad_ref.write_text(
        "apiVersion: wyrmctl.com/v1\nschemaVersion: 2\nproxy_hosts:\n"
        "- domain_names: [app.example.com]\n  forward_host: app\n  forward_port: 3000\n"
        "  certificate_ref: missing\n  access_list_ref: missing\n"
        "  meta: {managed_by: wyrmctl, owner: owner-a, resource_id: proxy}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="unknown certificate"):
        load_desired_state(bad_ref)
    bad_acl_ref = tmp_path / "bad-acl-ref.yaml"
    bad_acl_ref.write_text(
        "apiVersion: wyrmctl.com/v1\nschemaVersion: 2\nproxy_hosts:\n"
        "- domain_names: [app.example.com]\n  forward_host: app\n  forward_port: 3000\n"
        "  access_list_ref: missing\n"
        "  meta: {managed_by: wyrmctl, owner: owner-a, resource_id: proxy}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="unknown access list"):
        load_desired_state(bad_acl_ref)


def test_config_and_migration_edges(tmp_path: Path, monkeypatch) -> None:
    assert load_config(None) == {}
    missing = tmp_path / "missing.toml"
    with pytest.raises(ValidationError, match="failed to read"):
        load_config(str(missing))
    bad = tmp_path / "bad.toml"
    bad.write_text("[wyrmctl\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="failed to parse"):
        load_config(str(bad))
    bad.write_text("wyrmctl = 'bad'\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="must be a table"):
        load_config(str(bad))
    config = tmp_path / "wyrmctl.toml"
    config.write_text("base_url = 'http://example.test'\nidentity = 'admin'\n", encoding="utf-8")
    args = argparse.Namespace(base_url=None, identity="", secret="cli")
    apply_config(args, load_config(str(config)))
    assert args.base_url == "http://example.test"
    assert args.identity == "admin"
    assert args.secret == "cli"
    apply_config(args, {"base_url": "http://other.test"})
    assert args.base_url == "http://example.test"

    from wyrmctl.migrations.registry import migrate_document, migrate_path, needs_migration

    assert needs_migration({}) is True
    current = {
        "apiVersion": "wyrmctl.com/v1",
        "kind": "DesiredState",
        "schemaVersion": 3,
        "metadata": {"name": "test", "owner": "test"},
        "spec": {},
    }
    assert migrate_document(current) == (current, False, 3)
    with pytest.raises(MigrationError):
        migrate_document([])
    with pytest.raises(MigrationError):
        migrate_document({"schemaVersion": 2})
    with pytest.raises(MigrationError):
        migrate_path(tmp_path / "absent", write=False)
    json_file = tmp_path / "desired.json"
    json_file.write_text("null", encoding="utf-8")
    result = migrate_path(json_file, write=True)[0]
    assert result.changed is True
    assert json.loads(json_file.read_text(encoding="utf-8"))["schemaVersion"] == 3
    scalar = tmp_path / "scalar.yaml"
    scalar.write_text("- item\n", encoding="utf-8")
    with pytest.raises(MigrationError):
        migrate_path(scalar, write=False)


def test_cli_exception_mapping_and_auxiliary_commands(monkeypatch, tmp_path: Path, capsys) -> None:
    class Parser:
        def error(self, message: str) -> None:
            raise ValidationError(message)

    cases = [
        (ValidationError("v"), EXIT_USAGE_OR_VALIDATION, "validation_error"),
        (MigrationError("m"), EXIT_USAGE_OR_VALIDATION, "migration_error"),
        (ConflictError("c"), EXIT_CONFLICT, "conflict_error"),
        (CapabilityError("cap secret"), EXIT_CAPABILITY, "capability_error"),
        (ApiError("api secret"), EXIT_API, "api_error"),
        (NpmctlError("n"), EXIT_USAGE_OR_VALIDATION, "wyrmctl_error"),
    ]
    for exc, code, label in cases:
        monkeypatch.setattr("wyrmctl.cli._dispatch", lambda _args, _parser, exc=exc: (_ for _ in ()).throw(exc))
        assert main(["--output", "json", "--secret", "secret", "env"]) == code
        err = json.loads(capsys.readouterr().err)
        assert err["error"]["code"] == label
        assert "secret" not in err["error"]["message"]

    monkeypatch.setattr("wyrmctl.cli._dispatch", lambda args, parser: parser.error("bad command"))
    with pytest.raises(SystemExit):
        main(["env"])

    monkeypatch.undo()
    assert main(["--output", "json", "env"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["environment"]["NPM_SECRET"]["set"] in {True, False}
    assert main(["completion", "powershell"]) == EXIT_OK
    assert "Register-ArgumentCompleter" in capsys.readouterr().out
    assert main(["completion", "zsh"]) == EXIT_OK
    assert "#compdef" in capsys.readouterr().out

    artifact_dir = tmp_path / "compliance"
    assert main(["--output", "json", "compliance", "artifacts", "--output-dir", str(artifact_dir)]) == EXIT_OK
    capsys.readouterr()
    assert main(["--output", "json", "compliance", "gate", "--artifact-dir", str(artifact_dir)]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["ok"] is True

    migrated = tmp_path / "legacy.yaml"
    migrated.write_text("proxy_hosts: []\n", encoding="utf-8")
    assert main(["--output", "json", "migrate", str(migrated), "--check"]) == EXIT_USAGE_OR_VALIDATION
    assert json.loads(capsys.readouterr().out)["changed"] == 1
    assert main(["--output", "json", "migrate", str(migrated), "--write"]) == EXIT_OK
    capsys.readouterr()
    with pytest.raises(SystemExit):
        _dispatch(argparse.Namespace(command="unknown"), argparse.ArgumentParser())

    class Client:
        def capabilities(self) -> Capabilities:
            return Capabilities.full_for_tests()

        def existing_state(self, **_: Any) -> ExistingState:
            return ExistingState()

    monkeypatch.setattr("wyrmctl.cli.NpmClient", lambda **_: Client())
    monkeypatch.setattr("wyrmctl.cli.load_desired_state", lambda _path: DesiredState())
    monkeypatch.setattr(
        "wyrmctl.cli.validate_plan_output",
        lambda _payload: (_ for _ in ()).throw(ValueError("bad output")),
    )
    assert (
        main(
            [
                "--base-url",
                "http://npm.test/api",
                "--identity",
                "admin",
                "--secret",
                "secret",
                "plan",
                "desired.yaml",
                "--validate-output",
            ]
        )
        == EXIT_USAGE_OR_VALIDATION
    )
    capsys.readouterr()


def test_cli_api_commands_and_failure_paths(fake_npm_server, desired_file: Path, tmp_path: Path, capsys) -> None:
    state, base_url = fake_npm_server
    common = ["--base-url", base_url, "--identity", "admin@example.com", "--secret", "changeme", "--output", "json"]
    schema_path = tmp_path / "schema.json"
    assert main([*common, "health"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["status"] == "OK"
    assert main([*common, "schema", "fetch", "--write", str(schema_path)]) == EXIT_OK
    assert schema_path.exists()
    capsys.readouterr()
    assert main(["--output", "json", "schema", "capabilities", "--schema", str(schema_path)]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["proxy_hosts"]["list"] is True
    state.schema = {"openapi": "3.0.0", "info": {"version": "other"}, "paths": {}}
    assert main([*common, "schema", "check"]) == EXIT_CAPABILITY
    assert json.loads(capsys.readouterr().out)["ok"] is False
    assert main(["--output", "json", "schema", "capabilities", "--schema", str(schema_path)]) == EXIT_OK
    capsys.readouterr()
    state.schema = {
        "openapi": "3.0.0",
        "info": {"version": "2.10.4"},
        "paths": {"/": {"get": {}}, "/schema": {"get": {}}, "/tokens": {"post": {}, "get": {}}},
    }
    assert main([*common, "plan", str(desired_file)]) == EXIT_OK
    state.create("proxy_hosts", {"domain_names": ["app.example.com"], "meta": {}})
    assert main([*common, "apply", str(desired_file)]) == EXIT_CONFLICT
    capsys.readouterr()
    fake_client = type("Client", (), {"openapi_schema": lambda self: {"paths": {}}})()
    assert (
        _schema_command(argparse.Namespace(schema_command="fetch", write=None, output="json"), fake_client) == EXIT_OK
    )
    capsys.readouterr()


def test_client_request_and_capability_edges(monkeypatch) -> None:
    import requests

    monkeypatch.setattr("wyrmctl.client.base.time.sleep", lambda *_: None)
    client, session = _client([requests.RequestException("down"), Response(200, {"status": "OK"})])
    assert client.health() == {"status": "OK"}
    assert len(session.calls) == 2

    client, _ = _client(
        [requests.RequestException("down"), requests.RequestException("down"), requests.RequestException("down")]
    )
    with pytest.raises(ApiError, match="transport error"):
        client.health()

    client, _ = _client([Response(504, text="later"), Response(504, text="later"), Response(200, {"status": "OK"})])
    assert client.health() == {"status": "OK"}

    client, _ = _client([Response(200, None), Response(204, None)])
    client._token = "token"
    client._expires = int(time.time()) + 3600
    assert client.delete_resource(ResourceKind.PROXY_HOST, 1) is True

    client, _ = _client([Response(200, None, text="x", bad_json=True)])
    assert client._request("get", "/", authenticated=False, allow_empty=True) == {}

    client, _ = _client([Response(200, None, bad_json=True)])
    with pytest.raises(ApiError, match="invalid JSON"):
        client.health()

    client, _ = _client([Response(200, {"token": "new", "expires": 1}), Response(200, [])])
    client._token = "old"
    client._expires = 1
    assert client.list_resource(ResourceKind.ACCESS_LIST) == ()

    client, _ = _client(
        [Response(500, text="refresh failed"), Response(200, {"token": "new", "expires": 1}), Response(200, [])]
    )
    client._token = "old"
    client._expires = 1
    assert client.list_resource(ResourceKind.CERTIFICATE) == ()
    client, _ = _client([Response(200, {"info": {"version": "other"}, "paths": {}})])
    assert client.capabilities().schema_version == "other"
    client, _ = _client([Response(200, {"result": {"token": "wrapped", "expires": "2030-01-01T00:00:00"}})])
    client.login()
    assert client._token == "wrapped"
    client, session = _client([Response(200, [])])
    client._token = "token"
    client._expires = int(time.time()) + 3600
    assert client.audit_log() == []
    assert session.calls[0]["url"].endswith("/audit-log")
    with pytest.raises(ApiError, match="token response"):
        _extract_token([])

    caps = Capabilities.empty()
    compat = _with_npm_2104_compatibility(caps)
    assert compat.proxy_hosts.update_method == "put"
    full = Capabilities.full_for_tests()
    assert _with_npm_2104_compatibility(full).proxy_hosts is full.proxy_hosts
    for kind in (
        ResourceKind.REDIRECTION_HOST,
        ResourceKind.DEAD_HOST,
        ResourceKind.STREAM,
        ResourceKind.USER,
        ResourceKind.SETTING,
    ):
        assert _parse_created(kind, {"id": 1}).kind == kind
    with pytest.raises(ApiError):
        _parse_created(ResourceKind.PROXY_HOST, [])
    fake_kind = type("Kind", (), {"value": "custom"})()
    with pytest.raises(CapabilityError):
        _parse_created(fake_kind, {"id": 1})  # type: ignore[arg-type]
    from wyrmctl.client import base as client_base

    old_contracts = dict(client_base.CONTRACTS)
    client_base.CONTRACTS[fake_kind] = type("Contract", (), {"collection_path": "/custom"})()  # type: ignore[index]
    try:
        client, _ = _client([Response(200, [])])
        client._token = "token"
        client._expires = int(time.time()) + 3600
        with pytest.raises(CapabilityError):
            client.list_resource(fake_kind)  # type: ignore[arg-type]
    finally:
        client_base.CONTRACTS.clear()
        client_base.CONTRACTS.update(old_contracts)
    assert "secret" not in _redact("secret token password admin@example.com", "admin@example.com")


def test_apply_engine_operation_edges() -> None:
    class Client:
        def __init__(self) -> None:
            self.deleted = True

        def create_resource(self, kind: ResourceKind, payload: dict[str, Any]) -> ExistingResource:
            return ExistingResource.from_generic(kind, {"id": 9} | payload)

        def update_resource(
            self, kind: ResourceKind, resource_id: int, payload: dict[str, Any], *, method: str
        ) -> ExistingResource:
            return ExistingResource.from_generic(kind, {"id": resource_id} | payload)

        def delete_resource(self, kind: ResourceKind, resource_id: int) -> bool:
            return self.deleted

    client = Client()
    engine = ApplyEngine(client=client, capabilities=Capabilities.full_for_tests())  # type: ignore[arg-type]
    desired = _generic(ResourceKind.STREAM)
    existing = ExistingResource.from_generic(ResourceKind.STREAM, {"id": 4, "incoming_port": 8443, "meta": META})
    ops = (
        PlanOperation(PlanAction.NOOP, ResourceKind.STREAM, desired=desired, existing=existing),
        PlanOperation(PlanAction.CREATE, ResourceKind.STREAM, desired=desired),
        PlanOperation(PlanAction.UPDATE, ResourceKind.STREAM, desired=desired, existing=existing),
        PlanOperation(PlanAction.ADOPT, ResourceKind.STREAM, desired=desired, existing=existing),
        PlanOperation(PlanAction.DELETE, ResourceKind.STREAM, existing=existing),
    )
    result = engine.apply(Plan(operations=ops, conflicts=(), existing_count=1))
    assert [item["action"] for item in result.mutations] == ["create", "update", "adopt", "delete"]
    with pytest.raises(ConflictError):
        engine.apply(Plan(operations=(), conflicts=(PlanConflict("x", "x"),), existing_count=0))
    with pytest.raises(ValidationError):
        engine._apply_operation(PlanOperation(PlanAction.CONFLICT, ResourceKind.STREAM))
    with pytest.raises(ValidationError):
        engine._apply_operation(PlanOperation(PlanAction.CREATE, ResourceKind.STREAM))
    from wyrmctl import apply as apply_module

    monkeypatch_engine = ApplyEngine(client=client, capabilities=Capabilities.full_for_tests())  # type: ignore[arg-type]
    original_ordered = apply_module._ordered_operations
    apply_module._ordered_operations = lambda _ops: [PlanOperation(PlanAction.NOOP, ResourceKind.STREAM)]
    try:
        assert (
            monkeypatch_engine.apply(Plan((PlanOperation(PlanAction.NOOP, ResourceKind.STREAM),), (), 0)).mutations
            == []
        )
    finally:
        apply_module._ordered_operations = original_ordered
    wrong_created = ExistingResource.from_generic(ResourceKind.USER, {"id": 8, "email": "u@example.com"})
    engine.created_by_resource_id["cert-ref"] = wrong_created
    assert engine._resolve_reference(None, ResourceKind.CERTIFICATE) is None
    with pytest.raises(ValidationError, match="expected certificate"):
        engine._resolve_reference("cert-ref", ResourceKind.CERTIFICATE)
    with pytest.raises(ValidationError, match="unresolved"):
        engine._resolve_reference("missing", ResourceKind.CERTIFICATE)
    with pytest.raises(ValidationError):
        engine._apply_operation(PlanOperation(PlanAction.UPDATE, ResourceKind.STREAM, desired=desired))
    client.deleted = False
    with pytest.raises(ApiError):
        engine._apply_operation(PlanOperation(PlanAction.DELETE, ResourceKind.STREAM, existing=existing))

    cert = ExistingResource.from_certificate({"id": 2, "name": "cert", "domain_names": ["example.com"], "meta": META})
    acl = ExistingResource.from_access_list({"id": 3, "name": "acl", "meta": META})
    assert (
        _ordered_operations(
            (
                PlanOperation(PlanAction.DELETE, ResourceKind.CERTIFICATE, existing=cert),
                PlanOperation(PlanAction.DELETE, ResourceKind.ACCESS_LIST, existing=acl),
                PlanOperation(PlanAction.DELETE, ResourceKind.PROXY_HOST, existing=_existing_proxy()),
            )
        )[-1].kind
        == ResourceKind.CERTIFICATE
    )
    for kind in ResourceKind:
        raw = {
            "id": 10,
            "domain_names": ["x.example.com"],
            "incoming_port": 1,
            "server_name": "x.example.com",
            "target": "backend.internal",
            "target_port": 4443,
            "alpn": "h3",
            "name": "n",
            "email": "u@example.com",
            "meta": None,
        }
        existing_item = (
            ExistingResource.from_generic(kind, raw) if kind != ResourceKind.PROXY_HOST else _existing_proxy()
        )
        assert isinstance(_updateable_existing_payload(existing_item), dict)


def test_operational_reports_compliance_and_output_edges(tmp_path: Path, capsys) -> None:
    existing = ExistingResource.from_generic(ResourceKind.STREAM, {"id": 1, "incoming_port": 8000, "meta": META})
    desired = _generic(ResourceKind.STREAM)
    plan = Plan(
        operations=(
            PlanOperation(PlanAction.CREATE, ResourceKind.STREAM, desired=desired),
            PlanOperation(PlanAction.ADOPT, ResourceKind.STREAM, desired=desired, existing=existing),
            PlanOperation(PlanAction.DELETE, ResourceKind.STREAM, existing=existing),
            PlanOperation(PlanAction.NOOP, ResourceKind.STREAM, desired=desired, existing=existing),
        ),
        conflicts=(PlanConflict("conflict", "message"),),
        existing_count=1,
    )
    assert len(rollback_plan(plan)["steps"]) == 3
    assert transaction_report(plan)["generated_at"]
    assert transaction_report(plan, type("Result", (), {"to_dict": lambda self: {"applied": True}})())["apply"]
    assert drift_report(plan)["drift_count"] == 3
    with pytest.raises(ValueError, match="missing"):
        validate_plan_output({"ok": True})
    with pytest.raises(ValueError, match="boolean"):
        validate_plan_output({"ok": "yes", "existing_count": 0, "summary": {}, "operations": [], "conflicts": []})
    with pytest.raises(ValueError, match="arrays"):
        validate_plan_output({"ok": True, "existing_count": 0, "summary": {}, "operations": {}, "conflicts": []})

    artifact_dir = tmp_path / "artifacts"
    paths = compliance_artifacts(artifact_dir, package_name="wyrmctl", version="1.0.0", source_dir=Path.cwd())
    assert len(paths) == 5
    assert validate_compliance_gate(artifact_dir)["ok"] is True
    (artifact_dir / "security-scan.json").write_text('{"ok": false}\n', encoding="utf-8")
    assert validate_compliance_gate(artifact_dir)["ok"] is False
    assert validate_compliance_gate(tmp_path / "missing")["missing"]
    single = tmp_path / "artifact.whl"
    single.write_text("wheel", encoding="utf-8")
    assert _artifact_subjects(single, package_name="wyrmctl")[0]["digest"]["sha256"]
    many = tmp_path / "many"
    many.mkdir()
    for index in range(205):
        (many / f"{index:03}.txt").write_text(str(index), encoding="utf-8")
    assert len(_artifact_subjects(many, package_name="wyrmctl")) == 200
    skipped = tmp_path / ".git" / "ignored.py"
    skipped.parent.mkdir()
    skipped.write_text("ignored", encoding="utf-8")
    assert all(".git" not in item["name"] for item in _artifact_subjects(tmp_path, package_name="wyrmctl"))
    scan_root = tmp_path / "scan"
    src = scan_root / "packages" / "wyrmctl" / "src"
    src.mkdir(parents=True)
    (src / "bad.py").write_text(
        "eval('1')\nimport subprocess\nsubprocess.run('x')\nsubprocess.run('x', shell=True)\n",
        encoding="utf-8",
    )
    assert _security_scan(scan_root)["ok"] is False
    assert _dependency_audit([{"name": "requests", "version": "2.19.0"}])["ok"] is False
    assert _call_name(ast.Constant(value=1)) == ""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "wyrmctl.operational.metadata.version",
        lambda _name: (_ for _ in ()).throw(metadata.PackageNotFoundError("x")),
    )
    try:
        assert compliance_artifacts(tmp_path / "missing-dep", package_name="wyrmctl", version="1.0.0")
    finally:
        monkeypatch.undo()

    write_output("json", {"b": 1}, "")
    assert json.loads(capsys.readouterr().out) == {"b": 1}
    write_output("text", {}, "hello")
    assert capsys.readouterr().out.endswith("\n")
    write_error("json", "code", "message")
    assert json.loads(capsys.readouterr().err)["error"]["code"] == "code"
    assert "~ field" in format_plan_text(
        Plan(
            (
                PlanOperation(
                    PlanAction.UPDATE,
                    ResourceKind.STREAM,
                    desired=desired,
                    existing=existing,
                    diff={"field": {"actual": 1, "desired": 2}},
                ),
            ),
            (),
            1,
        )
    )


def test_planner_remaining_branches() -> None:
    desired = DesiredState(proxy_hosts=(_proxy(),), streams=(_generic(ResourceKind.STREAM),))
    same_key_foreign_identity = _existing_proxy(
        meta={"managed_by": "wyrmctl", "owner": "other", "resource_id": "other"}
    )
    same_identity_same_key = _existing_proxy()
    existing = ExistingState(
        proxy_hosts=(same_key_foreign_identity,),
        streams=(ExistingResource.from_generic(ResourceKind.STREAM, {"id": 7, "incoming_port": 8443, "meta": META}),),
    )
    plan = compute_plan(desired=desired, existing=existing, capabilities=Capabilities.full_for_tests())
    assert any(conflict.code == "foreign_owner" for conflict in plan.conflicts)
    assert PlanOperation(PlanAction.DELETE, ResourceKind.PROXY_HOST, existing=_existing_proxy()).owner == "owner-a"
    assert PlanOperation(PlanAction.CREATE, ResourceKind.PROXY_HOST).owner is None
    assert (
        PlanOperation(
            PlanAction.DELETE,
            ResourceKind.PROXY_HOST,
            existing=ExistingResource.from_generic(ResourceKind.USER, {"id": 9}),
        ).resource_id
        is None
    )
    assert PlanConflict("c", "m").to_dict()["kind"] is None
    assert diff_resource(_proxy(locations=[]), _existing_proxy(locations=None)) == {}
    assert diff_resource(_proxy(forward_port=1), _existing_proxy(forward_port="1")) == {}
    assert diff_resource(_proxy(forward_port=1), _existing_proxy(forward_port=True)) == {}
    assert _normalized_payload({"plain": 1}) == {"plain": 1}
    assert _coerce_existing_value(None, []) == []
    cert_existing = ExistingResource.from_certificate(
        {"id": 2, "provider": "fallback", "domain_names": ["c.example.com"]}
    )
    assert diff_resource(
        DesiredCertificate.from_mapping(
            {"name": "fallback", "domain_names": ["c.example.com"], "meta": META},
            path="c",
        ),
        cert_existing,
    )
    acl_existing = ExistingResource.from_access_list({"id": 3})
    assert diff_resource(
        DesiredAccessList.from_mapping({"name": "access-list-3", "meta": META}, path="a"), acl_existing
    )
    assert (
        compute_plan(
            desired=DesiredState(proxy_hosts=(_proxy(forward_port=4000),)),
            existing=ExistingState(proxy_hosts=(same_identity_same_key,)),
            capabilities=Capabilities.full_for_tests(),
            options=PlannerOptions(allow_updates=False),
        )
        .conflicts[0]
        .code
        == "owned_drift_updates_disabled"
    )
    assert (
        compute_plan(
            desired=DesiredState(proxy_hosts=(_proxy(forward_port=4000),)),
            existing=ExistingState(proxy_hosts=(same_identity_same_key,)),
            capabilities=Capabilities.empty(),
        )
        .conflicts[0]
        .code
        == "missing_update_capability"
    )
    assert (
        compute_plan(
            desired=DesiredState(),
            existing=ExistingState(proxy_hosts=(same_identity_same_key,)),
            capabilities=Capabilities.empty(),
            options=PlannerOptions(owner="owner-a", prune_owned=True),
        )
        .conflicts[0]
        .code
        == "missing_delete_capability"
    )
    assert (
        compute_plan(
            desired=DesiredState(streams=(_generic(ResourceKind.STREAM),)),
            existing=ExistingState(),
            capabilities=Capabilities.empty(),
        )
        .conflicts[0]
        .code
        == "missing_create_capability"
    )
    unmanaged_drift = ExistingResource.from_generic(
        ResourceKind.STREAM, {"id": 20, "incoming_port": 8443, "forward_port": 1}
    )
    assert (
        compute_plan(
            desired=DesiredState(streams=(_generic(ResourceKind.STREAM, forward_port=2),)),
            existing=ExistingState(streams=(unmanaged_drift,)),
            capabilities=Capabilities.full_for_tests(),
            options=PlannerOptions(adopt=True),
        )
        .conflicts[0]
        .code
        == "adopt_field_drift"
    )
    assert (
        compute_plan(
            desired=DesiredState(streams=(_generic(ResourceKind.STREAM),)),
            existing=ExistingState(streams=(unmanaged_drift,)),
            capabilities=Capabilities.empty(),
            options=PlannerOptions(adopt=True, allow_field_drift=True),
        )
        .conflicts[0]
        .code
        == "missing_update_capability"
    )
    collision = compute_plan(
        desired=DesiredState(proxy_hosts=(_proxy(domain_names=["app.example.com", "new.example.com"]),)),
        existing=ExistingState(
            proxy_hosts=(
                _existing_proxy(
                    id=30,
                    meta={"managed_by": "wyrmctl", "owner": "other", "resource_id": "other"},
                ),
            )
        ),
        capabilities=Capabilities.full_for_tests(),
    )
    assert any(conflict.code == "domain_collision" for conflict in collision.conflicts)
    existing_same = ExistingState(proxy_hosts=(same_identity_same_key,))
    assert (
        compute_plan(
            desired=DesiredState(proxy_hosts=(_proxy(),)),
            existing=existing_same,
            capabilities=Capabilities.full_for_tests(),
            options=PlannerOptions(prune_owned=True),
        ).by_action(PlanAction.DELETE)
        == ()
    )


def test_schema_and_plugin_edges(tmp_path: Path, monkeypatch) -> None:
    assert ResourceCapabilities(list=True).has("list") is True
    with pytest.raises(ValidationError):
        Capabilities.from_openapi([])
    with pytest.raises(ValidationError):
        Capabilities.from_openapi({"paths": []})
    caps = Capabilities.from_openapi(
        {
            "info": {"version": 1},
            "paths": {
                "/x": [],
                "/nginx/proxy-hosts": {"get": {}, "post": {}},
                "/nginx/proxy-hosts/{id}": {"patch": {}, "delete": {}},
            },
        }
    )
    assert caps.proxy_hosts.update_method == "patch"
    with pytest.raises(CapabilityError):
        caps.for_kind("bad")  # type: ignore[arg-type]
    with pytest.raises(CapabilityError):
        Capabilities.empty().require(ResourceKind.PROXY_HOST, "create")
    Capabilities.full_for_tests().require(ResourceKind.PROXY_HOST, "create")
    assert _methods([]) == set()
    Capabilities.full_for_tests().require(ResourceKind.PROXY_HOST, "create")
    assert _methods([]) == set()
    schema_path = tmp_path / "schema.json"
    schema_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_openapi_schema(schema_path)

    @dataclass
    class EP:
        name: str
        group: str
        obj: Any

        def load(self) -> Any:
            return self.obj

    class EPs(list):
        def select(self, *, group: str) -> "EPs":
            return EPs([item for item in self if item.group == group])

    class Resource:
        kind = ResourceKind.STREAM

        def identity(self, payload: dict[str, Any]) -> tuple[str, str]:
            return "o", "r"

        def natural_key(self, payload: dict[str, Any]) -> int:
            return 1

        def desired_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
            return payload

    class Cert:
        name = "cert"

        def resolve(self, reference: str) -> dict[str, Any]:
            return {"api_payload": {"reference": reference}}

    class Dns:
        name = "dns"

        def zones(self) -> tuple[str, ...]:
            return ("example.com",)

        def records(self, zone: str) -> tuple[dict[str, Any], ...]:
            return ({"zone": zone},)

    discovered = PluginRegistry.discover(
        entry_points=EPs(
            [
                EP("res", "wyrmctl.resource_providers", Resource),
                EP("cert", "wyrmctl.certificate_providers", Cert()),
                EP("dns", "wyrmctl.dns_providers", Dns()),
            ]
        )
    )
    assert discovered.to_dict() == {
        "resource_providers": ["res"],
        "certificate_providers": ["cert"],
        "dns_providers": ["dns"],
        "contract_plugins": [],
        "migration_plugins": [],
    }
    desired_file = tmp_path / "plugin-state.json"
    desired_file.write_text(
        json.dumps(
            {
                "apiVersion": "wyrmctl.com/v1",
                "schemaVersion": 2,
                "plugin_resources": [{"provider": "res", "payload": {"incoming_port": 9443}}],
                "external_certificates": [
                    {
                        "provider": "cert",
                        "reference": "external-cert",
                        "name": "external-cert",
                        "domain_names": ["external.example.com"],
                        "meta": {"managed_by": "wyrmctl", "owner": "owner-a", "resource_id": "cert-from-plugin"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    desired = load_desired_state(desired_file, plugin_registry=discovered)
    assert desired.streams[0].identity == ManagedIdentity(owner="o", resource_id="r")
    assert desired.streams[0].to_payload()["incoming_port"] == 9443
    assert desired.certificates[0].to_payload()["reference"] == "external-cert"

    class Client:
        def create_resource(self, kind: ResourceKind, payload: dict[str, Any]) -> ExistingResource:
            if kind == ResourceKind.CERTIFICATE:
                return ExistingResource.from_certificate({"id": 10, **payload})
            return ExistingResource.from_generic(kind, {"id": 11, **payload})

        def update_resource(
            self, kind: ResourceKind, resource_id: int, payload: dict[str, Any], *, method: str
        ) -> ExistingResource:
            return self.create_resource(kind, {"id": resource_id, **payload})

        def delete_resource(self, kind: ResourceKind, resource_id: int) -> bool:
            return True

    plugin_plan = compute_plan(desired=desired, existing=ExistingState(), capabilities=Capabilities.full_for_tests())
    plugin_result = ApplyEngine(client=Client(), capabilities=Capabilities.full_for_tests()).apply(plugin_plan)  # type: ignore[arg-type]
    assert [item["kind"] for item in plugin_result.mutations] == ["certificate", "stream"]

    with pytest.raises(ValueError):
        PluginRegistry.discover(entry_points=EPs([EP("bad", "wyrmctl.resource_providers", object())]))
    with pytest.raises(ValueError):
        _validate_resource_provider(
            "bad-kind",
            type(
                "Bad",
                (),
                {
                    "kind": object(),
                    "identity": lambda self, payload: ("o", "r"),
                    "natural_key": lambda self, payload: "r",
                    "desired_payload": lambda self, payload: payload,
                },
            )(),
        )
    with pytest.raises(ValueError):
        _validate_certificate_provider("bad", object())
    with pytest.raises(ValueError):
        _validate_dns_provider("bad", object())
    for payload, message in (
        ({"plugin_resources": [{"payload": {}}]}, "provider"),
        ({"plugin_resources": [{"provider": "missing", "payload": {}}]}, "unknown resource provider"),
        ({"plugin_resources": [{"provider": "res"}]}, "payload"),
        ({"external_certificates": [{"reference": "x"}]}, "provider"),
        ({"external_certificates": [{"provider": "missing", "reference": "x"}]}, "unknown certificate provider"),
        ({"external_certificates": [{"provider": "cert"}]}, "reference"),
    ):
        bad_file = tmp_path / f"bad-{abs(hash(message))}.json"
        bad_file.write_text(
            json.dumps({"apiVersion": "wyrmctl.com/v1", "schemaVersion": 2, **payload}), encoding="utf-8"
        )
        with pytest.raises(ValidationError, match=message):
            load_desired_state(bad_file, plugin_registry=discovered)

    class BadIdentity(Resource):
        def identity(self, payload: dict[str, Any]) -> dict[str, str]:
            return {"owner": ""}

    class BadKind(Resource):
        kind = ResourceKind.PROXY_HOST

    class UnknownKind(Resource):
        kind = "not_real"

    class ListIdentity(Resource):
        def identity(self, payload: dict[str, Any]) -> list[str]:
            return ["owner", "rid"]

    for provider, message in (
        (BadIdentity(), "identity"),
        (ListIdentity(), "identity"),
        (BadKind(), "generic resource kind"),
        (UnknownKind(), "supported resource kind"),
    ):
        registry = PluginRegistry()
        registry.register_resource_provider("res", provider)
        with pytest.raises(ValidationError, match=message):
            load_desired_state(desired_file, plugin_registry=registry)

    class ManagedIdentityResource(Resource):
        kind = "redirection_host"

        def identity(self, payload: dict[str, Any]) -> ManagedIdentity:
            return ManagedIdentity(owner="owner-a", resource_id="redir-plugin")

        def natural_key(self, payload: dict[str, Any]) -> tuple[str, ...]:
            return ("redir.example.com",)

        def desired_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
            return {"domain_names": ["redir.example.com"], "forward_domain_name": "target.example.com"}

    class DictIdentityResource(Resource):
        kind = ResourceKind.DEAD_HOST

        def identity(self, payload: dict[str, Any]) -> dict[str, str]:
            return {"owner": "owner-a", "resource_id": "dead-plugin"}

        def natural_key(self, payload: dict[str, Any]) -> tuple[str, ...]:
            return ("dead.example.com",)

        def desired_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
            return {"domain_names": ["dead.example.com"]}

    class UserResource(Resource):
        kind = ResourceKind.USER

        def identity(self, payload: dict[str, Any]) -> tuple[str, str]:
            return "owner-a", "user-plugin"

        def natural_key(self, payload: dict[str, Any]) -> str:
            return "user@example.com"

        def desired_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
            return {"email": "user@example.com"}

    class SettingResource(UserResource):
        kind = ResourceKind.SETTING

        def identity(self, payload: dict[str, Any]) -> tuple[str, str]:
            return "owner-a", "setting-plugin"

        def natural_key(self, payload: dict[str, Any]) -> str:
            return "setting-name"

        def desired_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
            return {"name": "setting-name", "value": "on"}

    mixed_registry = PluginRegistry()
    mixed_registry.register_resource_provider("redir", ManagedIdentityResource())
    mixed_registry.register_resource_provider("dead", DictIdentityResource())
    mixed_registry.register_resource_provider("user", UserResource())
    mixed_registry.register_resource_provider("setting", SettingResource())
    mixed_file = tmp_path / "mixed-plugin-state.json"
    mixed_file.write_text(
        json.dumps(
            {
                "apiVersion": "wyrmctl.com/v1",
                "schemaVersion": 2,
                "plugin_resources": [
                    {"provider": "redir", "payload": {}},
                    {"provider": "dead", "payload": {}},
                    {"provider": "user", "payload": {}},
                    {"provider": "setting", "payload": {}},
                ],
            }
        ),
        encoding="utf-8",
    )
    mixed = load_desired_state(mixed_file, plugin_registry=mixed_registry)
    assert [resource.identity.resource_id for resource in mixed.resources()] == [
        "redir-plugin",
        "dead-plugin",
        "user-plugin",
        "setting-plugin",
    ]

    monkeypatch.setattr(metadata, "entry_points", lambda: EPs([]))
    assert main(["--output", "json", "plugins", "list"]) == EXIT_OK
