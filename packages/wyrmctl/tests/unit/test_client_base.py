from __future__ import annotations

import time
from typing import Any

import pytest

from wyrmctl.client import NpmClient
from wyrmctl.client.base import _extract_token
from wyrmctl.errors import ApiError
from wyrmctl.models import ResourceKind
from wyrmctl.schema import Capabilities, ResourceCapabilities


class FakeResponse:
    def __init__(
        self, status_code: int, payload: Any = None, *, text: str | None = None, json_error: bool = False
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text if text is not None else ""
        self.content = b"" if payload is None and text is None else b"x"
        self.json_error = json_error

    def json(self) -> Any:
        if self.json_error:
            raise ValueError("invalid json")
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs) -> FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


def _client(responses: list[FakeResponse]) -> tuple[NpmClient, FakeSession]:
    client = NpmClient(base_url="http://npm.test/api", identity="admin@example.com", secret="supersecret")
    session = FakeSession(responses)
    client.session = session
    return client, session


def test_extract_token_accepts_numeric_expiry() -> None:
    assert _extract_token({"token": "abc", "expires": 1893456000}) == ("abc", 1893456000)


def test_extract_token_accepts_iso_expiry() -> None:
    token, expires = _extract_token({"token": "abc", "expires": "2030-01-01T00:00:00.000Z"})

    assert token == "abc"
    assert expires == 1893456000


@pytest.mark.parametrize(
    "payload", [{}, {"token": "", "expires": 1}, {"token": "abc"}, {"token": "abc", "expires": "bad"}]
)
def test_extract_token_rejects_login_failure_shapes(payload) -> None:
    with pytest.raises(ApiError):
        _extract_token(payload)


@pytest.mark.parametrize("status", [401, 403])
def test_request_reports_authorization_errors(status: int) -> None:
    client, _ = _client([FakeResponse(status, text='{"error":"denied"}')])

    with pytest.raises(ApiError, match=f"HTTP {status}"):
        client.health()


def test_request_reports_non_json_api_errors() -> None:
    client, _ = _client([FakeResponse(500, text="<html>bad</html>", json_error=True)])

    with pytest.raises(ApiError, match="HTTP 500"):
        client.health()


def test_request_reports_malformed_success_payloads() -> None:
    client, _ = _client([FakeResponse(200, {"token": "abc", "expires": time.time() + 3600}), FakeResponse(200, {})])

    with pytest.raises(ApiError, match="expected list response"):
        client.list_resource(ResourceKind.PROXY_HOST)


def test_request_retries_transient_get_failures(monkeypatch) -> None:
    monkeypatch.setattr("wyrmctl.client.base.time.sleep", lambda *_: None)
    client, session = _client(
        [
            FakeResponse(503, text="try later"),
            FakeResponse(502, text="try later"),
            FakeResponse(200, {"status": "OK"}),
        ]
    )

    assert client.health() == {"status": "OK"}
    assert [call["method"] for call in session.calls] == ["GET", "GET", "GET"]


def test_request_does_not_retry_non_get_mutations(monkeypatch) -> None:
    monkeypatch.setattr("wyrmctl.client.base.time.sleep", lambda *_: None)
    client, session = _client([FakeResponse(503, text="try later")])
    client._token = "token-value"
    client._expires = int(time.time()) + 3600

    with pytest.raises(ApiError, match="HTTP 503"):
        client.create_resource(ResourceKind.PROXY_HOST, {"domain_names": ["app.example.com"]})

    assert len(session.calls) == 1
    assert session.calls[0]["method"] == "POST"


def test_request_certificate_uses_provider_acme_endpoint() -> None:
    payload = {
        "nice_name": "demo.example.com",
        "domain_names": ["demo.example.com"],
        "provider": "letsencrypt",
        "meta": {"owner": "demo", "resource_id": "cert.demo"},
    }
    client, session = _client([FakeResponse(201, {"id": 2, **payload})])
    client._token = "token-value"
    client._expires = int(time.time()) + 3600

    certificate = client.request_certificate(payload)

    assert certificate.id == 2
    assert session.calls[0]["url"].endswith("/nginx/certificates/request")
    assert session.calls[0]["json"] == payload


def test_refresh_uses_existing_token_without_recursive_refresh(monkeypatch) -> None:
    monkeypatch.setattr("wyrmctl.client.base.time.time", lambda: 1000)
    client, session = _client(
        [
            FakeResponse(200, {"token": "new-token", "expires": 2000}),
            FakeResponse(200, []),
        ]
    )
    client._token = "old-token"
    client._expires = 1005

    assert client.list_resource(ResourceKind.PROXY_HOST) == ()

    assert [call["url"] for call in session.calls] == [
        "http://npm.test/api/tokens",
        "http://npm.test/api/nginx/proxy-hosts",
    ]
    assert session.calls[0]["headers"]["Authorization"] == "Bearer old-token"
    assert session.calls[1]["headers"]["Authorization"] == "Bearer new-token"


def test_settings_accept_string_ids_from_real_npm() -> None:
    client, session = _client(
        [
            FakeResponse(200, [{"id": "default-site", "name": "Default Site", "value": "congratulations"}]),
            FakeResponse(200, {"id": "default-site", "name": "Default Site", "value": "updated"}),
            FakeResponse(200, True),
        ]
    )
    client._token = "token-value"
    client._expires = int(time.time()) + 3600

    settings = client.list_resource(ResourceKind.SETTING)

    assert settings[0].id == "default-site"
    assert settings[0].natural_key == "Default Site"
    assert client.update_resource(ResourceKind.SETTING, settings[0].id, {"value": "updated"}).id == "default-site"
    assert client.delete_resource(ResourceKind.SETTING, settings[0].id)
    assert session.calls[1]["url"].endswith("/settings/default-site")
    assert session.calls[2]["url"].endswith("/settings/default-site")


def test_optional_resource_discovery_tolerates_permission_denied(monkeypatch) -> None:
    client, _ = _client([])

    def deny(_: ResourceKind) -> None:
        raise ApiError('GET /users failed: HTTP 403: {"error":"Permission Denied"}')

    monkeypatch.setattr(client, "list_resource", deny)

    assert client._optional_list_resource(ResourceKind.USER) == ()


def test_optional_resource_discovery_reraises_non_permission_errors(monkeypatch) -> None:
    client, _ = _client([])

    def fail(_: ResourceKind) -> None:
        raise ApiError("GET /users failed: HTTP 500: broken")

    monkeypatch.setattr(client, "list_resource", fail)

    with pytest.raises(ApiError, match="HTTP 500"):
        client._optional_list_resource(ResourceKind.USER)


def test_existing_state_tolerates_optional_permission_denied(monkeypatch) -> None:
    client, session = _client(
        [
            FakeResponse(200, []),
            FakeResponse(200, []),
            FakeResponse(200, []),
            FakeResponse(403, text='{"error":"Permission Denied"}'),
            FakeResponse(403, text='{"error":"Permission Denied"}'),
        ]
    )
    client._token = "token-value"
    client._expires = int(time.time()) + 3600
    caps = Capabilities(
        proxy_hosts=ResourceCapabilities(list=True),
        certificates=ResourceCapabilities(list=True),
        access_lists=ResourceCapabilities(list=True),
        users=ResourceCapabilities(list=True),
        settings=ResourceCapabilities(list=True),
    )
    monkeypatch.setattr(client, "capabilities", lambda: caps)

    state = client.existing_state()

    assert state.proxy_hosts == ()
    assert state.certificates == ()
    assert state.access_lists == ()
    assert state.users == ()
    assert state.settings == ()
    assert [call["url"] for call in session.calls] == [
        "http://npm.test/api/nginx/proxy-hosts",
        "http://npm.test/api/nginx/certificates",
        "http://npm.test/api/nginx/access-lists",
        "http://npm.test/api/users",
        "http://npm.test/api/settings",
    ]


def test_existing_state_still_fails_on_required_permission_denied(monkeypatch) -> None:
    client, _ = _client([FakeResponse(403, text='{"error":"Permission Denied"}')])
    client._token = "token-value"
    client._expires = int(time.time()) + 3600
    caps = Capabilities(
        proxy_hosts=ResourceCapabilities(list=True),
        certificates=ResourceCapabilities(list=True),
        access_lists=ResourceCapabilities(list=True),
    )
    monkeypatch.setattr(client, "capabilities", lambda: caps)

    with pytest.raises(ApiError, match="GET /nginx/proxy-hosts failed: HTTP 403"):
        client.existing_state()


def test_api_errors_redact_configured_secrets_and_sensitive_markers() -> None:
    client, _ = _client(
        [
            FakeResponse(
                500,
                text="admin@example.com supersecret token password secret",
            )
        ]
    )
    client._token = "token-value"

    with pytest.raises(ApiError) as exc_info:
        client.health()

    message = str(exc_info.value)
    assert "admin@example.com" not in message
    assert "supersecret" not in message
    assert "password" not in message
    assert "secret" not in message
