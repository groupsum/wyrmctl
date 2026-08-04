"""HTTP client for the Nginx Proxy Manager API."""

from __future__ import annotations

import time
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

import requests

from wyrmctl.client.contracts import CONTRACTS
from wyrmctl.errors import ApiError, CapabilityError, CertificateApiError
from wyrmctl.models import ExistingResource, ExistingState, ResourceId, ResourceKind
from wyrmctl.schema import Capabilities, ResourceCapabilities

_TRANSIENT_STATUSES = frozenset({502, 503, 504})


class NpmClient:
    """Small typed client for the NPM OpenAPI surface."""

    def __init__(self, *, base_url: str, identity: str, secret: str, timeout_s: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.identity = identity
        self.secret = secret
        self.timeout_s = timeout_s
        self.session = requests.Session()
        self._token: str | None = None
        self._expires: int | None = None

    def health(self) -> dict[str, Any]:
        return self._request("get", "/", authenticated=False)

    def login(self) -> None:
        payload = {"identity": self.identity, "secret": self.secret, "scope": "user"}
        data = self._request("post", "/tokens", authenticated=False, json=payload)
        token, expires = _extract_token(data)
        self._token = token
        self._expires = expires

    def refresh(self) -> None:
        try:
            data = self._request("get", "/tokens", authenticated=True, ensure_token=False)
        except ApiError:
            self.login()
            return
        token, expires = _extract_token(data)
        self._token = token
        self._expires = expires

    def openapi_schema(self) -> dict[str, Any]:
        return self._request("get", "/schema", authenticated=False)

    def capabilities(self) -> Capabilities:
        caps = Capabilities.from_openapi(self.openapi_schema())
        if caps.quic_passthrough_hosts.list:
            native = self._request("get", "/v2/capabilities", authenticated=True)
            quic = native.get("quic_sni_passthrough") if isinstance(native, dict) else None
            if not isinstance(quic, dict) or quic.get("supported") is not True:
                raise CapabilityError("provider advertises QUIC routes without supported QUIC SNI passthrough")
            if quic.get("tls_termination") is not False:
                raise CapabilityError("QUIC passthrough provider must preserve backend TLS termination")
        if caps.schema_version == "2.10.4":
            return _with_npm_2104_compatibility(caps)
        return caps

    def list_resource(self, kind: ResourceKind) -> tuple[ExistingResource, ...]:
        contract = CONTRACTS[kind]
        data = self._request("get", contract.collection_path, authenticated=True)
        if not isinstance(data, list):
            raise ApiError(f"expected list response for {kind.value}, got {type(data).__name__}")
        if kind == ResourceKind.PROXY_HOST:
            return tuple(ExistingResource.from_proxy_host(item) for item in data)
        if kind == ResourceKind.CERTIFICATE:
            return tuple(ExistingResource.from_certificate(item) for item in data)
        if kind == ResourceKind.ACCESS_LIST:
            return tuple(ExistingResource.from_access_list(item) for item in data)
        if kind in {
            ResourceKind.REDIRECTION_HOST,
            ResourceKind.DEAD_HOST,
            ResourceKind.STREAM,
            ResourceKind.QUIC_PASSTHROUGH_HOST,
            ResourceKind.USER,
            ResourceKind.SETTING,
        }:
            return tuple(ExistingResource.from_generic(kind, item) for item in data)
        raise CapabilityError(f"unsupported resource kind: {kind}")

    def existing_state(self, *, include_certificates: bool = True, include_access_lists: bool = True) -> ExistingState:
        caps = self.capabilities()
        proxy_hosts = self.list_resource(ResourceKind.PROXY_HOST)
        certificates = self.list_resource(ResourceKind.CERTIFICATE) if include_certificates else ()
        access_lists = self.list_resource(ResourceKind.ACCESS_LIST) if include_access_lists else ()
        redirection_hosts = self.list_resource(ResourceKind.REDIRECTION_HOST) if caps.redirection_hosts.list else ()
        dead_hosts = self.list_resource(ResourceKind.DEAD_HOST) if caps.dead_hosts.list else ()
        streams = self.list_resource(ResourceKind.STREAM) if caps.streams.list else ()
        quic_passthrough_hosts = (
            self.list_resource(ResourceKind.QUIC_PASSTHROUGH_HOST) if caps.quic_passthrough_hosts.list else ()
        )
        users = self._optional_list_resource(ResourceKind.USER) if caps.users.list else ()
        settings = self._optional_list_resource(ResourceKind.SETTING) if caps.settings.list else ()
        return ExistingState(
            proxy_hosts=proxy_hosts,
            certificates=certificates,
            access_lists=access_lists,
            redirection_hosts=redirection_hosts,
            dead_hosts=dead_hosts,
            streams=streams,
            quic_passthrough_hosts=quic_passthrough_hosts,
            users=users,
            settings=settings,
        )

    def _optional_list_resource(self, kind: ResourceKind) -> tuple[ExistingResource, ...]:
        try:
            return self.list_resource(kind)
        except ApiError as exc:
            if "HTTP 403" in str(exc):
                return ()
            raise

    def create_resource(self, kind: ResourceKind, payload: Mapping[str, Any]) -> ExistingResource:
        contract = CONTRACTS[kind]
        data = self._request("post", contract.collection_path, authenticated=True, json=dict(payload))
        return _parse_created(kind, data)

    def update_resource(
        self, kind: ResourceKind, resource_id: ResourceId, payload: Mapping[str, Any], *, method: str = "put"
    ) -> ExistingResource:
        contract = CONTRACTS[kind]
        data = self._request(method, contract.item_path(resource_id), authenticated=True, json=dict(payload))
        return _parse_created(kind, data)

    def delete_resource(self, kind: ResourceKind, resource_id: ResourceId) -> bool:
        contract = CONTRACTS[kind]
        data = self._request("delete", contract.item_path(resource_id), authenticated=True, allow_empty=True)
        return data is True or data == {} or data is None

    def audit_log(self, *, since: str | None = None) -> Any:
        path = "/audit-log"
        if since:
            path = f"{path}?since={since}"
        return self._request("get", path, authenticated=True)

    def _ensure_token(self) -> None:
        if self._token is None or self._expires is None:
            self.login()
            return
        if int(time.time()) >= self._expires - 30:
            self.refresh()

    def _request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool,
        json: Mapping[str, Any] | None = None,
        allow_empty: bool = False,
        ensure_token: bool = True,
    ) -> Any:
        if authenticated and ensure_token:
            self._ensure_token()
        headers = {"Content-Type": "application/json"}
        if authenticated and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        url = f"{self.base_url}{path}"
        attempts = 3 if method.lower() == "get" else 1
        last_error: ApiError | None = None
        for attempt in range(attempts):
            try:
                response = self.session.request(
                    method.upper(),
                    url,
                    headers=headers,
                    json=json,
                    timeout=self.timeout_s,
                )
            except requests.RequestException as exc:
                last_error = ApiError(f"{method.upper()} {path} transport error: {exc}")
                if attempt + 1 < attempts:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise last_error from exc
            if response.status_code in _TRANSIENT_STATUSES and attempt + 1 < attempts:
                last_error = ApiError(
                    f"{method.upper()} {path} failed: HTTP {response.status_code}: {self._redact(response.text)}"
                )
                time.sleep(0.5 * (attempt + 1))
                continue
            break
        else:  # pragma: no cover - attempts is always positive for supported methods
            if last_error is not None:
                raise last_error
            raise ApiError(f"{method.upper()} {path} request did not complete")
        if response.status_code < 200 or response.status_code >= 300:
            raise _classify_api_error(
                method.upper(),
                path,
                response.status_code,
                self._redact(response.text),
            )
        if allow_empty and not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            if allow_empty:
                return {}
            raise ApiError(f"{method.upper()} {path} returned invalid JSON") from exc

    def _redact(self, text: str) -> str:
        return _redact(text, self.identity, self.secret, self._token)


def _extract_token(data: Any) -> tuple[str, int]:
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        data = data["result"]
    if not isinstance(data, dict):
        raise ApiError("token response must be an object")
    token = data.get("token")
    expires = data.get("expires")
    if not isinstance(token, str) or not token:
        raise ApiError("token response missing token")
    if isinstance(expires, str):
        expires = _parse_iso_expiry(expires)
    if isinstance(expires, bool) or not isinstance(expires, int | float):
        raise ApiError("token response missing numeric expires")
    return token, int(expires)


def _parse_iso_expiry(value: str) -> int:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApiError("token response expires must be numeric or ISO-8601") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


def _parse_created(kind: ResourceKind, data: Any) -> ExistingResource:
    if not isinstance(data, dict):
        raise ApiError(f"{kind.value} mutation response must be an object")
    if kind == ResourceKind.PROXY_HOST:
        return ExistingResource.from_proxy_host(data)
    if kind == ResourceKind.CERTIFICATE:
        return ExistingResource.from_certificate(data)
    if kind == ResourceKind.ACCESS_LIST:
        return ExistingResource.from_access_list(data)
    if kind in {
        ResourceKind.REDIRECTION_HOST,
        ResourceKind.DEAD_HOST,
        ResourceKind.STREAM,
        ResourceKind.QUIC_PASSTHROUGH_HOST,
        ResourceKind.USER,
        ResourceKind.SETTING,
    }:
        return ExistingResource.from_generic(kind, data)
    raise CapabilityError(f"unsupported resource kind: {kind}")


def _with_npm_2104_compatibility(caps: Capabilities) -> Capabilities:
    """Fill endpoints that NPM 2.10.4 implements but omits from /schema."""

    proxy = caps.proxy_hosts
    if not (proxy.list and proxy.create and proxy.update and proxy.delete):
        proxy = ResourceCapabilities(list=True, create=True, get=True, update=True, delete=True, update_method="put")
    certs = caps.certificates
    if not (certs.list and certs.create and certs.delete):
        certs = ResourceCapabilities(list=True, create=True, get=False, update=False, delete=True)
    access_lists = caps.access_lists
    if not (access_lists.list and access_lists.create and access_lists.update and access_lists.delete):
        access_lists = ResourceCapabilities(
            list=True, create=True, get=True, update=True, delete=True, update_method="put"
        )
    return Capabilities(
        proxy_hosts=proxy,
        certificates=certs,
        access_lists=access_lists,
        redirection_hosts=caps.redirection_hosts,
        dead_hosts=caps.dead_hosts,
        streams=caps.streams,
        quic_passthrough_hosts=caps.quic_passthrough_hosts,
        users=caps.users,
        settings=caps.settings,
        audit_log=caps.audit_log,
        schema_version=caps.schema_version,
    )


def _redact(text: str, *secrets: str | None) -> str:
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "***")
    for marker in ("token", "secret", "password"):
        redacted = redacted.replace(marker, f"{marker[0]}***")
    return redacted[:1000]


def _classify_api_error(method: str, path: str, status_code: int, text: str) -> ApiError:
    lowered = text.lower()
    message = f"{method} {path} failed: HTTP {status_code}: {text}"
    if "another instance of certbot is already running" in lowered:
        return CertificateApiError(
            "certificate_lock_retryable",
            message,
            retryable=True,
            suggested_action="retry after the active certbot operation finishes",
            details={"http_status": status_code, "path": path},
        )
    if "no order for id" in lowered or "no order for" in lowered:
        return CertificateApiError(
            "certificate_order_stale",
            message,
            retryable=False,
            suggested_action="clean up the stale certificate order in NPM before retrying",
            details={"http_status": status_code, "path": path},
        )
    return ApiError(message)
