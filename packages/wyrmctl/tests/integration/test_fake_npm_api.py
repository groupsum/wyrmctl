from __future__ import annotations

import json
from pathlib import Path

from wyrmctl.apply import ApplyEngine
from wyrmctl.client import NpmClient
from wyrmctl.loader import load_desired_state
from wyrmctl.planner import PlannerOptions, compute_plan


def _client(base_url: str) -> NpmClient:
    return NpmClient(base_url=base_url, identity="admin@example.com", secret="changeme", timeout_s=5)


def _write_doc(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_apply_full_stack_and_idempotent(fake_npm_server, desired_file: Path) -> None:
    _, base_url = fake_npm_server
    client = _client(base_url)
    desired = load_desired_state(desired_file)
    caps = client.capabilities()
    existing = client.existing_state(include_certificates=True, include_access_lists=True)
    plan = compute_plan(desired=desired, existing=existing, capabilities=caps)
    result = ApplyEngine(client=client, capabilities=caps).apply(plan)
    assert len(result.mutations) == 3

    second_existing = client.existing_state(include_certificates=True, include_access_lists=True)
    second_plan = compute_plan(desired=desired, existing=second_existing, capabilities=caps)
    assert second_plan.ok
    assert len(second_plan.by_action("create")) == 0
    assert len(second_plan.by_action("noop")) == 3


def test_update_owned_proxy_host(fake_npm_server, desired_file: Path) -> None:
    state, base_url = fake_npm_server
    state.create(
        "proxy_hosts",
        {
            "domain_names": ["app.example.com"],
            "forward_host": "app",
            "forward_port": 8080,
            "forward_scheme": "http",
            "access_list_id": 0,
            "certificate_id": 0,
            "ssl_forced": 1,
            "caching_enabled": 0,
            "block_exploits": 1,
            "advanced_config": "",
            "meta": {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": "proxy.app"},
            "allow_websocket_upgrade": 1,
            "http2_support": 1,
            "enabled": 1,
            "locations": [],
            "hsts_enabled": 0,
            "hsts_subdomains": 0,
            "use_default_location": True,
            "ipv6": True,
        },
    )
    client = _client(base_url)
    desired = load_desired_state(desired_file)
    caps = client.capabilities()
    plan = compute_plan(
        desired=desired,
        existing=client.existing_state(include_certificates=True, include_access_lists=True),
        capabilities=caps,
    )
    ApplyEngine(client=client, capabilities=caps).apply(plan)
    assert state.proxy_hosts[0]["forward_port"] == 3000


def test_adopt_unmanaged_proxy_host(fake_npm_server, desired_file: Path) -> None:
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
            "use_default_location": True,
            "ipv6": True,
        },
    )
    client = _client(base_url)
    desired = load_desired_state(desired_file)
    caps = client.capabilities()
    plan = compute_plan(
        desired=desired,
        existing=client.existing_state(include_certificates=True, include_access_lists=True),
        capabilities=caps,
        options=PlannerOptions(adopt=True),
    )
    ApplyEngine(client=client, capabilities=caps).apply(plan)
    assert state.proxy_hosts[0]["meta"]["managed_by"] == "wyrmctl"


def test_cli_apply_and_plan_json(fake_npm_server, desired_file: Path, capsys) -> None:
    from wyrmctl.cli import main

    _, base_url = fake_npm_server
    code = main(
        [
            "--base-url",
            base_url,
            "--identity",
            "admin@example.com",
            "--secret",
            "changeme",
            "--output",
            "json",
            "apply",
            str(desired_file),
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert '"applied": true' in out


def test_metadata_only_adopt_skips_missing_certificate_creation(fake_npm_server, tmp_path: Path) -> None:
    state, base_url = fake_npm_server
    state.create(
        "proxy_hosts",
        {
            "domain_names": ["app.example.com"],
            "forward_host": "app",
            "forward_port": 3000,
            "forward_scheme": "http",
            "access_list_id": 0,
            "certificate_id": 99,
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
            "use_default_location": True,
            "ipv6": True,
        },
    )
    desired = load_desired_state(
        _write_doc(
            tmp_path / "metadata-only.json",
            {
                "apiVersion": "wyrmctl.com/v1",
                "schemaVersion": 2,
                "certificates": [
                    {
                        "name": "cert-one",
                        "domain_names": ["app.example.com"],
                        "certificate_type": "other",
                        "api_payload": {"provider": "other"},
                        "meta": {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": "cert.one"},
                    }
                ],
                "proxy_hosts": [
                    {
                        "domain_names": ["app.example.com"],
                        "forward_host": "app",
                        "forward_port": 3000,
                        "certificate_ref": "cert.one",
                        "meta": {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": "proxy.app"},
                    }
                ],
            },
        )
    )
    client = _client(base_url)
    caps = client.capabilities()
    plan = compute_plan(
        desired=desired,
        existing=client.existing_state(include_certificates=True, include_access_lists=True),
        capabilities=caps,
        options=PlannerOptions(
            adopt=True,
            metadata_only_adopt=True,
            allow_field_drift=True,
            resource_kinds=frozenset({desired.proxy_hosts[0].kind}),
        ),
    )

    ApplyEngine(client=client, capabilities=caps, existing_state=client.existing_state()).apply(plan)

    assert state.certificates == []
    assert state.proxy_hosts[0]["meta"]["managed_by"] == "wyrmctl"
    assert state.proxy_hosts[0]["certificate_id"] == 99


def test_reuse_mode_rebinds_proxy_to_compatible_existing_certificate(fake_npm_server, tmp_path: Path) -> None:
    state, base_url = fake_npm_server
    existing_cert = state.create(
        "certificates",
        {
            "name": "legacy-cert",
            "nice_name": "legacy-cert",
            "provider": "letsencrypt",
            "domain_names": ["app.example.com"],
            "meta": {},
        },
    )
    desired = load_desired_state(
        _write_doc(
            tmp_path / "reuse.json",
            {
                "apiVersion": "wyrmctl.com/v1",
                "schemaVersion": 2,
                "certificates": [
                    {
                        "name": "desired-cert",
                        "domain_names": ["app.example.com"],
                        "certificate_type": "letsencrypt",
                        "meta": {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": "cert.one"},
                    }
                ],
                "proxy_hosts": [
                    {
                        "domain_names": ["app.example.com"],
                        "forward_host": "app",
                        "forward_port": 3000,
                        "certificate_ref": "cert.one",
                        "meta": {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": "proxy.app"},
                    }
                ],
            },
        )
    )
    client = _client(base_url)
    caps = client.capabilities()
    existing = client.existing_state(include_certificates=True, include_access_lists=True)
    plan = compute_plan(
        desired=desired,
        existing=existing,
        capabilities=caps,
        options=PlannerOptions(certificate_mode="reuse"),
    )

    result = ApplyEngine(client=client, capabilities=caps, existing_state=existing).apply(plan)

    assert [mutation["kind"] for mutation in result.mutations] == ["proxy_host"]
    assert state.proxy_hosts[0]["certificate_id"] == existing_cert["id"]
    assert len(state.certificates) == 1
