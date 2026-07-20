from __future__ import annotations

from pathlib import Path

import pytest

from wyrmctl.cli import main
from wyrmctl.models import ResourceKind
from real_npm_helpers import (
    cleanup_marker,
    client,
    common_args,
    marker,
    proxy_by_resource_id,
    require_real_npm,
    wait_until_absent,
    write_doc,
)

pytestmark = pytest.mark.npm


def test_real_npm_proxy_host_field_readback_update_adopt_owner_scope_and_cleanup(tmp_path: Path) -> None:
    require_real_npm()
    npm = client()
    run = marker()
    owner_a = f"{run}-a"
    owner_b = f"{run}-b"
    common = common_args()
    cleanup_marker(npm, run)
    try:
        cert_name = f"{run}-cert"
        acl_name = f"{run}-acl"
        domain = f"{run}.example.invalid"
        desired = {
            "apiVersion": "wyrmctl.com/v1",
            "schemaVersion": 2,
            "certificates": [
                {
                    "name": cert_name,
                    "domain_names": [domain],
                    "certificate_type": "other",
                    "api_payload": {"provider": "other", "nice_name": cert_name, "meta": {}},
                    "meta": {"managed_by": "wyrmctl", "owner": owner_a, "resource_id": f"{run}.cert"},
                }
            ],
            "access_lists": [
                {
                    "name": acl_name,
                    "api_payload": {"satisfy_any": 0, "pass_auth": 0, "items": [], "clients": []},
                    "meta": {"managed_by": "wyrmctl", "owner": owner_a, "resource_id": f"{run}.acl"},
                }
            ],
            "proxy_hosts": [
                {
                    "domain_names": [domain],
                    "forward_scheme": "https",
                    "forward_host": "127.0.0.1",
                    "forward_port": 8443,
                    "certificate_ref": f"{run}.cert",
                    "access_list_ref": f"{run}.acl",
                    "ssl_forced": 1,
                    "caching_enabled": 1,
                    "block_exploits": 1,
                    "advanced_config": "add_header X-Npmctl-E2E yes;",
                    "allow_websocket_upgrade": 1,
                    "http2_support": 1,
                    "enabled": 1,
                    "locations": [
                        {
                            "path": "/api",
                            "forward_scheme": "http",
                            "forward_host": "127.0.0.1",
                            "forward_port": 8081,
                            "forward_path": "/",
                            "advanced_config": "",
                        }
                    ],
                    "hsts_enabled": 1,
                    "hsts_subdomains": 1,
                    "meta": {"managed_by": "wyrmctl", "owner": owner_a, "resource_id": f"{run}.proxy"},
                }
            ],
        }
        assert main([*common, "apply", str(write_doc(tmp_path, desired))]) == 0

        proxy = proxy_by_resource_id(npm, f"{run}.proxy")
        raw = proxy.raw
        assert raw["domain_names"] == [domain]
        assert raw["forward_scheme"] == "https"
        assert raw["forward_host"] == "127.0.0.1"
        assert raw["forward_port"] == 8443
        assert raw["ssl_forced"] == 1
        assert raw["caching_enabled"] == 1
        assert raw["block_exploits"] == 1
        assert raw["advanced_config"] == "add_header X-Npmctl-E2E yes;"
        assert raw["allow_websocket_upgrade"] == 1
        assert raw["http2_support"] == 1
        assert raw["enabled"] == 1
        assert raw["hsts_enabled"] == 1
        assert raw["hsts_subdomains"] == 1
        assert raw["certificate_id"] > 0
        assert raw["access_list_id"] > 0
        assert raw["locations"][0]["path"] == "/api"
        assert {key: raw["meta"][key] for key in ("managed_by", "owner", "resource_id")} == {
            "managed_by": "wyrmctl",
            "owner": owner_a,
            "resource_id": f"{run}.proxy",
        }

        update_doc = {
            "apiVersion": "wyrmctl.com/v1",
            "schemaVersion": 2,
            "proxy_hosts": [
                {
                    "domain_names": [domain],
                    "forward_scheme": "http",
                    "forward_host": "127.0.0.1",
                    "forward_port": 8080,
                    "certificate_id": raw["certificate_id"],
                    "access_list_id": raw["access_list_id"],
                    "ssl_forced": 0,
                    "caching_enabled": 0,
                    "block_exploits": 1,
                    "advanced_config": "add_header X-Npmctl-E2E updated;",
                    "allow_websocket_upgrade": 0,
                    "http2_support": 0,
                    "enabled": 1,
                    "locations": [],
                    "hsts_enabled": 0,
                    "hsts_subdomains": 0,
                    "meta": {"managed_by": "wyrmctl", "owner": owner_a, "resource_id": f"{run}.proxy"},
                }
            ],
        }
        assert main([*common, "apply", str(write_doc(tmp_path, update_doc))]) == 0
        updated = proxy_by_resource_id(npm, f"{run}.proxy").raw
        assert updated["forward_scheme"] == "http"
        assert updated["forward_port"] == 8080
        assert updated["advanced_config"] == "add_header X-Npmctl-E2E updated;"
        assert updated["caching_enabled"] == 0

        adopt_domain = f"{run}-adopt.example.invalid"
        unmanaged = npm.create_resource(
            ResourceKind.PROXY_HOST,
            {
                "domain_names": [adopt_domain],
                "forward_scheme": "http",
                "forward_host": "127.0.0.1",
                "forward_port": 8080,
                "meta": {},
            },
        )
        adopt_doc = {
            "apiVersion": "wyrmctl.com/v1",
            "schemaVersion": 2,
            "proxy_hosts": [
                {
                    "domain_names": [adopt_domain],
                    "forward_scheme": "http",
                    "forward_host": "127.0.0.1",
                    "forward_port": 8080,
                    "meta": {"managed_by": "wyrmctl", "owner": owner_a, "resource_id": f"{run}.adopt"},
                }
            ],
        }
        assert main([*common, "adopt", str(write_doc(tmp_path, adopt_doc))]) == 0
        adopted = proxy_by_resource_id(npm, f"{run}.adopt")
        assert adopted.id == unmanaged.id

        foreign_domain = f"{run}-foreign.example.invalid"
        npm.create_resource(
            ResourceKind.PROXY_HOST,
            {
                "domain_names": [foreign_domain],
                "forward_scheme": "http",
                "forward_host": "127.0.0.1",
                "forward_port": 8080,
                "meta": {"managed_by": "wyrmctl", "owner": owner_b, "resource_id": f"{run}.foreign"},
            },
        )
        foreign_doc = {
            "apiVersion": "wyrmctl.com/v1",
            "schemaVersion": 2,
            "proxy_hosts": [
                {
                    "domain_names": [foreign_domain],
                    "forward_host": "127.0.0.1",
                    "forward_port": 8080,
                    "meta": {"managed_by": "wyrmctl", "owner": owner_a, "resource_id": f"{run}.foreign-wanted"},
                }
            ],
        }
        assert main([*common, "plan", str(write_doc(tmp_path, foreign_doc))]) == 1

        selected_doc = {
            "apiVersion": "wyrmctl.com/v1",
            "schemaVersion": 2,
            "proxy_hosts": [
                {
                    "domain_names": [f"{run}-selected-a.example.invalid"],
                    "forward_host": "127.0.0.1",
                    "forward_port": 8080,
                    "meta": {"managed_by": "wyrmctl", "owner": owner_a, "resource_id": f"{run}.selected-a"},
                },
                {
                    "domain_names": [f"{run}-selected-b.example.invalid"],
                    "forward_host": "127.0.0.1",
                    "forward_port": 8080,
                    "meta": {"managed_by": "wyrmctl", "owner": owner_b, "resource_id": f"{run}.selected-b"},
                },
            ],
        }
        assert main([*common, "apply", str(write_doc(tmp_path, selected_doc)), "--owner", owner_a]) == 0
        assert proxy_by_resource_id(npm, f"{run}.selected-a").identity.owner == owner_a
        assert not [
            item
            for item in npm.list_resource(ResourceKind.PROXY_HOST)
            if item.identity and item.identity.resource_id == f"{run}.selected-b"
        ]

        empty_doc = {"apiVersion": "wyrmctl.com/v1", "schemaVersion": 2, "proxy_hosts": []}
        assert main([*common, "apply", str(write_doc(tmp_path, empty_doc)), "--owner", owner_a, "--prune-owned"]) == 0
        remaining_ids = {
            item.identity.resource_id
            for item in npm.list_resource(ResourceKind.PROXY_HOST)
            if item.identity and item.identity.resource_id.startswith(run)
        }
        assert f"{run}.selected-a" not in remaining_ids
        assert f"{run}.foreign" in remaining_ids
    finally:
        cleanup_marker(npm, run)
        wait_until_absent(
            npm,
            ResourceKind.PROXY_HOST,
            lambda item: any(run in domain for domain in item.domain_names),
        )


def test_real_npm_domain_collision_is_blocked(tmp_path: Path) -> None:
    require_real_npm()
    npm = client()
    run = marker()
    owner = f"{run}-owner"
    cleanup_marker(npm, run)
    try:
        shared = f"{run}-shared.example.invalid"
        npm.create_resource(
            ResourceKind.PROXY_HOST,
            {
                "domain_names": [shared, f"{run}-other.example.invalid"],
                "forward_scheme": "http",
                "forward_host": "127.0.0.1",
                "forward_port": 8080,
                "meta": {"managed_by": "wyrmctl", "owner": owner, "resource_id": f"{run}.existing"},
            },
        )
        desired = {
            "apiVersion": "wyrmctl.com/v1",
            "schemaVersion": 2,
            "proxy_hosts": [
                {
                    "domain_names": [shared],
                    "forward_host": "127.0.0.1",
                    "forward_port": 8080,
                    "meta": {"managed_by": "wyrmctl", "owner": owner, "resource_id": f"{run}.wanted"},
                }
            ],
        }

        assert main([*common_args(), "plan", str(write_doc(tmp_path, desired))]) == 1
    finally:
        cleanup_marker(npm, run)
