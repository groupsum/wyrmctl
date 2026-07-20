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


def test_real_npm_certificate_create_readback_delete_and_proxy_reference(tmp_path: Path) -> None:
    require_real_npm()
    npm = client()
    caps = npm.capabilities()
    if not caps.certificates.list:
        pytest.fail("this NPM schema does not expose certificate list")
    if not caps.certificates.create:
        pytest.fail("this NPM schema does not expose certificate create")
    run = marker()
    cert_name = f"{run}-cert"
    domain = f"{run}.example.invalid"
    cleanup_marker(npm, run)
    try:
        desired = {
            "apiVersion": "wyrmctl.com/v1",
            "schemaVersion": 2,
            "certificates": [
                {
                    "name": cert_name,
                    "domain_names": [domain],
                    "certificate_type": "other",
                    "api_payload": {"provider": "other", "nice_name": cert_name, "meta": {}},
                    "meta": {"managed_by": "wyrmctl", "owner": run, "resource_id": f"{run}.cert"},
                }
            ],
            "proxy_hosts": [
                {
                    "domain_names": [f"{run}-host.example.invalid"],
                    "forward_scheme": "http",
                    "forward_host": "127.0.0.1",
                    "forward_port": 8080,
                    "certificate_ref": f"{run}.cert",
                    "ssl_forced": 1,
                    "http2_support": 1,
                    "hsts_enabled": 1,
                    "hsts_subdomains": 1,
                    "meta": {"managed_by": "wyrmctl", "owner": run, "resource_id": f"{run}.proxy"},
                }
            ],
        }

        assert main([*common_args(), "apply", str(write_doc(tmp_path, desired))]) == 0

        cert = list_by_name(npm, ResourceKind.CERTIFICATE, cert_name)
        assert cert.raw["provider"] == "other"
        assert cert.domain_names == (domain,)
        proxy = [
            item
            for item in npm.list_resource(ResourceKind.PROXY_HOST)
            if item.identity and item.identity.resource_id == f"{run}.proxy"
        ][0]
        assert proxy.raw["certificate_id"] == cert.id
        assert proxy.raw["ssl_forced"] == 1
        assert proxy.raw["http2_support"] == 1
        assert proxy.raw["hsts_enabled"] == 1
        assert proxy.raw["hsts_subdomains"] == 1

        if caps.certificates.update:
            updated = npm.update_resource(
                ResourceKind.CERTIFICATE,
                cert.id,
                {"provider": "other", "nice_name": f"{cert_name}-updated", "domain_names": [domain], "meta": {}},
                method=caps.certificates.update_method or "put",
            )
            assert updated.name == f"{cert_name}-updated"
        if caps.certificates.delete:
            best_effort_delete(npm, ResourceKind.PROXY_HOST, proxy.id)
            wait_until_absent(
                npm,
                ResourceKind.PROXY_HOST,
                lambda item: item.identity is not None and item.identity.resource_id == f"{run}.proxy",
            )
            assert npm.delete_resource(ResourceKind.CERTIFICATE, cert.id) is True
            wait_until_absent(npm, ResourceKind.CERTIFICATE, lambda item: item.name == cert.name)
    finally:
        cleanup_marker(npm, run)


def test_missing_and_ambiguous_certificate_refs_fail_before_apply(tmp_path: Path) -> None:
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
                "certificate_ref": "missing-cert",
                "meta": {"managed_by": "wyrmctl", "owner": run, "resource_id": f"{run}.proxy"},
            }
        ],
    }

    assert main([*common_args(), "apply", str(write_doc(tmp_path, missing))]) == 2
