from __future__ import annotations

from wyrmctl.schema import Capabilities

FULL_OPENAPI = {
    "openapi": "3.0.0",
    "info": {"version": "2.10.4"},
    "paths": {
        "/nginx/proxy-hosts": {"get": {}, "post": {}},
        "/nginx/proxy-hosts/{id}": {"get": {}, "put": {}, "delete": {}},
        "/nginx/certificates": {"get": {}, "post": {}},
        "/nginx/certificates/{id}": {"get": {}, "put": {}, "delete": {}},
        "/nginx/access-lists": {"get": {}, "post": {}},
        "/nginx/access-lists/{id}": {"get": {}, "put": {}, "delete": {}},
    },
}


def test_capabilities_detect_full_crud() -> None:
    caps = Capabilities.from_openapi(FULL_OPENAPI)
    assert caps.proxy_hosts.create
    assert caps.proxy_hosts.update
    assert caps.proxy_hosts.delete
    assert caps.certificates.update
    assert caps.access_lists.delete


def test_capabilities_fail_closed_when_item_paths_absent() -> None:
    spec = {"openapi": "3.0.0", "paths": {"/nginx/proxy-hosts": {"get": {}, "post": {}}}}
    caps = Capabilities.from_openapi(spec)
    assert caps.proxy_hosts.create
    assert not caps.proxy_hosts.update
    assert not caps.proxy_hosts.delete
