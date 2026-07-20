from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture
def desired_doc() -> dict[str, Any]:
    return {
        "apiVersion": "wyrmctl.com/v1",
        "schemaVersion": 2,
        "certificates": [
            {
                "name": "wildcard-example",
                "domain_names": ["*.example.com", "example.com"],
                "meta": {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": "cert.wildcard-example"},
                "api_payload": {"provider": "letsencrypt"},
            }
        ],
        "access_lists": [
            {
                "name": "private-admins",
                "meta": {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": "acl.private-admins"},
                "api_payload": {"satisfy_any": 0, "items": []},
            }
        ],
        "proxy_hosts": [
            {
                "domain_names": ["app.example.com"],
                "forward_host": "app",
                "forward_port": 3000,
                "certificate_ref": "cert.wildcard-example",
                "access_list_ref": "acl.private-admins",
                "ssl_forced": 1,
                "http2_support": 1,
                "allow_websocket_upgrade": 1,
                "block_exploits": 1,
                "meta": {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": "proxy.app"},
            }
        ],
    }


@pytest.fixture
def desired_file(tmp_path: Path, desired_doc: dict[str, Any]) -> Path:
    path = tmp_path / "desired.yaml"
    path.write_text(yaml.safe_dump(desired_doc, sort_keys=False), encoding="utf-8")
    return path


FULL_OPENAPI = {
    "openapi": "3.0.0",
    "info": {"title": "Nginx Proxy Manager API", "version": "2.10.4"},
    "paths": {
        "/": {"get": {}},
        "/schema": {"get": {}},
        "/tokens": {"get": {}, "post": {}},
        "/nginx/proxy-hosts": {"get": {}, "post": {}},
        "/nginx/proxy-hosts/{id}": {"get": {}, "put": {}, "delete": {}},
        "/nginx/certificates": {"get": {}, "post": {}},
        "/nginx/certificates/{id}": {"get": {}, "put": {}, "delete": {}},
        "/nginx/access-lists": {"get": {}, "post": {}},
        "/nginx/access-lists/{id}": {"get": {}, "put": {}, "delete": {}},
        "/nginx/redirection-hosts": {"get": {}, "post": {}},
        "/nginx/redirection-hosts/{id}": {"get": {}, "put": {}, "delete": {}},
        "/nginx/dead-hosts": {"get": {}, "post": {}},
        "/nginx/dead-hosts/{id}": {"get": {}, "put": {}, "delete": {}},
        "/nginx/streams": {"get": {}, "post": {}},
        "/nginx/streams/{id}": {"get": {}, "put": {}, "delete": {}},
        "/users": {"get": {}, "post": {}},
        "/users/{id}": {"get": {}, "put": {}, "delete": {}},
        "/settings": {"get": {}, "post": {}},
        "/settings/{id}": {"get": {}, "put": {}, "delete": {}},
        "/audit-log": {"get": {}},
    },
}


class FakeNpmState:
    def __init__(self) -> None:
        self.proxy_hosts: list[dict[str, Any]] = []
        self.certificates: list[dict[str, Any]] = []
        self.access_lists: list[dict[str, Any]] = []
        self.redirection_hosts: list[dict[str, Any]] = []
        self.dead_hosts: list[dict[str, Any]] = []
        self.streams: list[dict[str, Any]] = []
        self.users: list[dict[str, Any]] = []
        self.settings: list[dict[str, Any]] = []
        self.audit_log: list[dict[str, Any]] = []
        self.next_id = 1
        self.schema = FULL_OPENAPI

    def create(self, collection: str, payload: dict[str, Any]) -> dict[str, Any]:
        item = dict(payload)
        item.setdefault("created_on", "2026-01-01T00:00:00.000Z")
        item.setdefault("modified_on", "2026-01-01T00:00:00.000Z")
        item["id"] = self.next_id
        self.next_id += 1
        getattr(self, collection).append(item)
        return item

    def update(self, collection: str, resource_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        items = getattr(self, collection)
        for idx, item in enumerate(items):
            if item["id"] == resource_id:
                updated = dict(item)
                updated.update(payload)
                updated["id"] = resource_id
                items[idx] = updated
                return updated
        return None

    def delete(self, collection: str, resource_id: int) -> bool:
        items = getattr(self, collection)
        for idx, item in enumerate(items):
            if item["id"] == resource_id:
                del items[idx]
                return True
        return False


class Handler(BaseHTTPRequestHandler):
    state: FakeNpmState

    def log_message(self, *_: Any) -> None:  # pragma: no cover
        return

    def _json(self, status: int, payload: Any) -> None:
        encoded = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode())

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.removeprefix("/api")
        if path == "/":
            self._json(200, {"status": "OK", "version": {"major": 2, "minor": 10, "revision": 4}})
        elif path == "/schema":
            self._json(200, self.state.schema)
        elif path == "/tokens":
            self._json(200, {"token": "fake-token", "expires": int(time.time()) + 3600})
        elif path == "/nginx/proxy-hosts":
            self._json(200, self.state.proxy_hosts)
        elif path == "/nginx/certificates":
            self._json(200, self.state.certificates)
        elif path == "/nginx/access-lists":
            self._json(200, self.state.access_lists)
        elif path == "/nginx/redirection-hosts":
            self._json(200, self.state.redirection_hosts)
        elif path == "/nginx/dead-hosts":
            self._json(200, self.state.dead_hosts)
        elif path == "/nginx/streams":
            self._json(200, self.state.streams)
        elif path == "/users":
            self._json(200, self.state.users)
        elif path == "/settings":
            self._json(200, self.state.settings)
        elif path.startswith("/audit-log"):
            self._json(200, self.state.audit_log)
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.removeprefix("/api")
        if path == "/tokens":
            self._json(200, {"result": {"token": "fake-token", "expires": int(time.time()) + 3600}})
        elif path == "/nginx/proxy-hosts":
            self._json(201, self.state.create("proxy_hosts", self._read()))
        elif path == "/nginx/certificates":
            self._json(201, self.state.create("certificates", self._read()))
        elif path == "/nginx/access-lists":
            self._json(201, self.state.create("access_lists", self._read()))
        elif path == "/nginx/redirection-hosts":
            self._json(201, self.state.create("redirection_hosts", self._read()))
        elif path == "/nginx/dead-hosts":
            self._json(201, self.state.create("dead_hosts", self._read()))
        elif path == "/nginx/streams":
            self._json(201, self.state.create("streams", self._read()))
        elif path == "/users":
            self._json(201, self.state.create("users", self._read()))
        elif path == "/settings":
            self._json(201, self.state.create("settings", self._read()))
        else:
            self._json(404, {"error": "not found"})

    def do_PUT(self) -> None:  # noqa: N802
        self._mutate("put")

    def do_DELETE(self) -> None:  # noqa: N802
        path = self.path.removeprefix("/api")
        collection, resource_id = _collection_and_id(path)
        if collection and self.state.delete(collection, resource_id):
            self._json(200, True)
        else:
            self._json(404, {"error": "not found"})

    def _mutate(self, _: str) -> None:
        path = self.path.removeprefix("/api")
        collection, resource_id = _collection_and_id(path)
        if not collection:
            self._json(404, {"error": "not found"})
            return
        updated = self.state.update(collection, resource_id, self._read())
        self._json(200, updated if updated else {"error": "not found"})


def _collection_and_id(path: str) -> tuple[str | None, int]:
    mapping = {
        "/nginx/proxy-hosts/": "proxy_hosts",
        "/nginx/certificates/": "certificates",
        "/nginx/access-lists/": "access_lists",
        "/nginx/redirection-hosts/": "redirection_hosts",
        "/nginx/dead-hosts/": "dead_hosts",
        "/nginx/streams/": "streams",
        "/users/": "users",
        "/settings/": "settings",
    }
    for prefix, collection in mapping.items():
        if path.startswith(prefix):
            return collection, int(path.removeprefix(prefix))
    return None, 0


@pytest.fixture
def fake_npm_server():
    state = FakeNpmState()

    class BoundHandler(Handler):
        pass

    BoundHandler.state = state
    server = ThreadingHTTPServer(("127.0.0.1", 0), BoundHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state, f"http://127.0.0.1:{server.server_port}/api"
    finally:
        server.shutdown()
        thread.join(timeout=5)
