from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from wyrmctl.client.base import NpmClient
from wyrmctl.errors import CapabilityError, ValidationError
from wyrmctl.loader import load_desired_state
from wyrmctl.models import ExistingState, ResourceKind
from wyrmctl.planner import compute_plan
from wyrmctl.plugins import PluginRegistry
from wyrmctl.profile import NPMCTL_PROFILE, use_profile
from wyrmctl.schema import Capabilities


def _document() -> dict[str, Any]:
    return {
        "apiVersion": "wyrmctl.com/v1",
        "kind": "DesiredState",
        "schemaVersion": 3,
        "metadata": {},
        "spec": {
            "quicPassthroughHosts": [
                {
                    "server_name": "present.example",
                    "target": "presentation-backend",
                    "target_port": 4443,
                    "meta": {
                        "managed_by": "wyrmctl",
                        "owner": "presentation-demo",
                        "resource_id": "quic.presentation",
                    },
                }
            ]
        },
    }


def _write(path: Path, document: dict[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def _portwyrm_openapi() -> dict[str, Any]:
    return {
        "info": {"version": "portwyrm"},
        "paths": {
            "/v2/quic-passthrough-hosts": {"get": {}, "post": {}},
            "/v2/quic-passthrough-hosts/{resource_id}": {
                "get": {},
                "put": {},
                "delete": {},
            },
        },
    }


@pytest.mark.parametrize(
    ("native", "message"),
    [
        ({"quic_sni_passthrough": {"supported": False, "tls_termination": False}}, "supported"),
        ({"quic_sni_passthrough": {"supported": True, "tls_termination": True}}, "backend TLS"),
        ({}, "supported"),
    ],
)
def test_client_fails_closed_on_invalid_quic_provider_capability(
    monkeypatch: pytest.MonkeyPatch,
    native: dict[str, Any],
    message: str,
) -> None:
    client = NpmClient(base_url="http://portwyrm/api", identity="admin@example.com", secret="secret")
    monkeypatch.setattr(client, "openapi_schema", _portwyrm_openapi)
    monkeypatch.setattr(client, "_request", lambda *_args, **_kwargs: native)

    with pytest.raises(CapabilityError, match=message):
        client.capabilities()


def test_client_accepts_opaque_quic_passthrough_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    client = NpmClient(base_url="http://portwyrm/api", identity="admin@example.com", secret="secret")
    monkeypatch.setattr(client, "openapi_schema", _portwyrm_openapi)
    monkeypatch.setattr(
        client,
        "_request",
        lambda *_args, **_kwargs: {"quic_sni_passthrough": {"supported": True, "tls_termination": False}},
    )

    assert client.capabilities().quic_passthrough_hosts.create


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (("pop", "target", None), "missing required keys"),
        (("set", "target_kind", "other"), "target_kind"),
        (("set", "alpn", "hq"), "alpn"),
        (("set", "idle_timeout_seconds", True), "must be an integer"),
        (("set", "idle_timeout_seconds", 4), "between 5 and 86400"),
        (("set", "listen_address", ""), "non-empty string"),
    ],
)
def test_quic_route_validation_rejects_invalid_fields(
    tmp_path: Path,
    mutation: tuple[str, str, Any],
    message: str,
) -> None:
    document = _document()
    route = document["spec"]["quicPassthroughHosts"][0]
    operation, key, value = mutation
    if operation == "pop":
        route.pop(key)
    else:
        route[key] = value

    with pytest.raises(ValidationError, match=message):
        load_desired_state(_write(tmp_path / "desired.yaml", document))


def test_npmctl_profile_recommends_portwyrm_for_missing_quic_capability(tmp_path: Path) -> None:
    desired = load_desired_state(_write(tmp_path / "desired.yaml", _document()))

    with use_profile(NPMCTL_PROFILE):
        plan = compute_plan(
            desired=desired,
            existing=ExistingState(),
            capabilities=Capabilities.empty(),
        )

    assert plan.conflicts[0].message == (
        "Nginx Proxy Manager cannot manage hostname-routed QUIC passthrough; "
        "use Portwyrm with wyrmctl for this resource"
    )


class QuicResourceProvider:
    kind = ResourceKind.QUIC_PASSTHROUGH_HOST

    def identity(self, _payload: dict[str, Any]) -> tuple[str, str]:
        return "presentation-demo", "quic.presentation"

    def natural_key(self, payload: dict[str, Any]) -> str:
        return str(payload["server_name"])

    def desired_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return dict(payload)


def test_plugin_quic_resource_is_routed_to_quic_collection(tmp_path: Path) -> None:
    document = _document()
    document["spec"] = {
        "pluginResources": [
            {
                "provider": "quic",
                "payload": {
                    "server_name": "present.example",
                    "target": "presentation-backend",
                    "target_port": 4443,
                },
            }
        ]
    }
    plugins = PluginRegistry()
    plugins.register_resource_provider("quic", QuicResourceProvider())

    desired = load_desired_state(
        _write(tmp_path / "desired.yaml", document),
        plugin_registry=plugins,
    )

    assert desired.quic_passthrough_hosts[0].natural_key == "present.example"
