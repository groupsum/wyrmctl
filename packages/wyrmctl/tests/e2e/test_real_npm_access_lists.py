from __future__ import annotations

from pathlib import Path

import pytest

from wyrmctl.cli import main
from wyrmctl.models import ResourceKind
from real_npm_helpers import (
    best_effort_delete,
    cleanup_marker,
    client,
    common_args,
    list_by_name,
    marker,
    require_real_npm,
    wait_until_absent,
    write_doc,
)

pytestmark = pytest.mark.npm


def test_real_npm_access_list_create_readback_update_delete_and_proxy_reference(tmp_path: Path) -> None:
    require_real_npm()
    npm = client()
    caps = npm.capabilities()
    if not caps.access_lists.list:
        pytest.fail("this NPM schema does not expose access-list list")
    if not caps.access_lists.create:
        pytest.fail("this NPM schema does not expose access-list create")
    run = marker()
    acl_name = f"{run}-acl"
    cleanup_marker(npm, run)
    try:
        desired = {
            "apiVersion": "wyrmctl.com/v1",
            "schemaVersion": 2,
            "access_lists": [
                {
                    "name": acl_name,
                    "api_payload": {"satisfy_any": 0, "pass_auth": 0, "items": [], "clients": []},
                    "meta": {"managed_by": "wyrmctl", "owner": run, "resource_id": f"{run}.acl"},
                }
            ],
            "proxy_hosts": [
                {
                    "domain_names": [f"{run}.example.invalid"],
                    "forward_scheme": "http",
                    "forward_host": "127.0.0.1",
                    "forward_port": 8080,
                    "access_list_ref": f"{run}.acl",
                    "meta": {"managed_by": "wyrmctl", "owner": run, "resource_id": f"{run}.proxy"},
                }
            ],
        }

        assert main([*common_args(), "apply", str(write_doc(tmp_path, desired))]) == 0

        acl = list_by_name(npm, ResourceKind.ACCESS_LIST, acl_name)
        assert acl.raw["satisfy_any"] == 0
        assert acl.raw.get("items", []) == []
        assert acl.raw.get("clients", []) == []
        proxy = [
            item
            for item in npm.list_resource(ResourceKind.PROXY_HOST)
            if item.identity and item.identity.resource_id == f"{run}.proxy"
        ][0]
        assert proxy.raw["access_list_id"] == acl.id

        if caps.access_lists.update:
            updated = npm.update_resource(
                ResourceKind.ACCESS_LIST,
                acl.id,
                {"name": acl_name, "satisfy_any": 1, "pass_auth": 0, "items": [], "clients": []},
                method=caps.access_lists.update_method or "put",
            )
            assert updated.raw["satisfy_any"] == 1
        if caps.access_lists.delete:
            best_effort_delete(npm, ResourceKind.PROXY_HOST, proxy.id)
            wait_until_absent(
                npm,
                ResourceKind.PROXY_HOST,
                lambda item: item.identity is not None and item.identity.resource_id == f"{run}.proxy",
            )
            assert npm.delete_resource(ResourceKind.ACCESS_LIST, acl.id) is True
            wait_until_absent(npm, ResourceKind.ACCESS_LIST, lambda item: item.name == acl_name)
    finally:
        cleanup_marker(npm, run)


def test_missing_access_list_ref_fails_before_apply(tmp_path: Path) -> None:
    require_real_npm()
    run = marker()
    missing = {
        "apiVersion": "wyrmctl.com/v1",
        "schemaVersion": 2,
        "proxy_hosts": [
            {
                "domain_names": [f"{run}.example.invalid"],
                "forward_host": "127.0.0.1",
                "forward_port": 8080,
                "access_list_ref": "missing-acl",
                "meta": {"managed_by": "wyrmctl", "owner": run, "resource_id": f"{run}.proxy"},
            }
        ],
    }

    assert main([*common_args(), "apply", str(write_doc(tmp_path, missing))]) == 2
