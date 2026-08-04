from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from wyrmctl.apply import ApplyEngine
from wyrmctl.artifacts import plan_from_artifact
from wyrmctl.errors import ValidationError
from wyrmctl.loader import load_desired_state
from wyrmctl.models import ExistingResource, ExistingState, ResourceKind
from wyrmctl.planner import compute_plan
from wyrmctl.schema import Capabilities


def _document(server_name: str = "present.example") -> dict[str, Any]:
    return {
        "apiVersion": "wyrmctl.com/v1",
        "kind": "DesiredState",
        "schemaVersion": 3,
        "metadata": {},
        "spec": {
            "quicPassthroughHosts": [
                {
                    "server_name": server_name,
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


def test_v3_loader_parses_quic_passthrough_host(tmp_path: Path) -> None:
    desired = load_desired_state(_write(tmp_path / "desired.yaml", _document()))

    route = desired.quic_passthrough_hosts[0]
    assert route.kind == ResourceKind.QUIC_PASSTHROUGH_HOST
    assert route.natural_key == "present.example"
    assert route.to_payload() == {
        "listen_address": "0.0.0.0",
        "incoming_port": 443,
        "server_name": "present.example",
        "alpn": "h3",
        "target_kind": "docker",
        "target": "presentation-backend",
        "target_port": 4443,
        "idle_timeout_seconds": 1800,
        "enabled": 1,
        "meta": {
            "managed_by": "wyrmctl",
            "owner": "presentation-demo",
            "resource_id": "quic.presentation",
        },
    }


def test_quic_passthrough_requires_exact_hostname(tmp_path: Path) -> None:
    path = _write(tmp_path / "desired.yaml", _document("*.sub.example"))

    with pytest.raises(ValidationError, match="exact hostname"):
        load_desired_state(path)


def test_openapi_detects_portwyrm_native_quic_crud() -> None:
    capabilities = Capabilities.from_openapi(
        {
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
    )

    assert capabilities.quic_passthrough_hosts.to_dict() == {
        "list": True,
        "create": True,
        "get": True,
        "update": True,
        "delete": True,
        "update_method": "put",
    }


class RecordingClient:
    def __init__(self) -> None:
        self.created: list[tuple[ResourceKind, dict[str, Any]]] = []

    def create_resource(self, kind: ResourceKind, payload: dict[str, Any]) -> ExistingResource:
        self.created.append((kind, payload))
        return ExistingResource.from_generic(kind, {"id": 7, **payload})


def test_plan_and_apply_create_quic_passthrough_route(tmp_path: Path) -> None:
    desired = load_desired_state(_write(tmp_path / "desired.yaml", _document()))
    capabilities = Capabilities.full_for_tests()
    plan = compute_plan(desired=desired, existing=ExistingState(), capabilities=capabilities)
    client = RecordingClient()

    result = ApplyEngine(client=client, capabilities=capabilities).apply(plan)  # type: ignore[arg-type]

    assert plan.ok
    assert result.mutations == [
        {
            "action": "create",
            "kind": "quic_passthrough_host",
            "resource_id": "quic.presentation",
            "id": 7,
        }
    ]
    assert client.created[0][0] == ResourceKind.QUIC_PASSTHROUGH_HOST
    assert client.created[0][1]["server_name"] == "present.example"


def test_quic_plan_operation_round_trips_through_artifact(tmp_path: Path) -> None:
    desired = load_desired_state(_write(tmp_path / "desired.yaml", _document()))
    plan = compute_plan(
        desired=desired,
        existing=ExistingState(),
        capabilities=Capabilities.full_for_tests(),
    )
    document = {
        "kind": "PlanArtifact",
        "schemaVersion": 1,
        "spec": {"operations": [plan.operations[0].to_dict()], "conflicts": []},
    }

    restored = plan_from_artifact(document)

    assert restored.operations[0].desired is not None
    assert restored.operations[0].desired.to_payload()["server_name"] == "present.example"
