"""OpenAPI schema compatibility and endpoint capability detection."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wyrmctl.contracts import semantic_digest
from wyrmctl.errors import CapabilityError, ValidationError
from wyrmctl.models import ResourceKind


@dataclass(frozen=True, slots=True)
class ResourceCapabilities:
    """CRUD capabilities for one resource kind."""

    list: bool = False
    create: bool = False
    get: bool = False
    update: bool = False
    delete: bool = False
    update_method: str | None = None

    def has(self, operation: str) -> bool:
        return bool(getattr(self, operation))

    def to_dict(self) -> dict[str, Any]:
        return {
            "list": self.list,
            "create": self.create,
            "get": self.get,
            "update": self.update,
            "delete": self.delete,
            "update_method": self.update_method,
        }


@dataclass(frozen=True, slots=True)
class Capabilities:
    """NPM API capability matrix."""

    proxy_hosts: ResourceCapabilities
    certificates: ResourceCapabilities
    access_lists: ResourceCapabilities
    redirection_hosts: ResourceCapabilities = field(default_factory=ResourceCapabilities)
    dead_hosts: ResourceCapabilities = field(default_factory=ResourceCapabilities)
    streams: ResourceCapabilities = field(default_factory=ResourceCapabilities)
    users: ResourceCapabilities = field(default_factory=ResourceCapabilities)
    settings: ResourceCapabilities = field(default_factory=ResourceCapabilities)
    audit_log: ResourceCapabilities = field(default_factory=ResourceCapabilities)
    schema_version: str | None = None

    @classmethod
    def empty(cls) -> Capabilities:
        empty = ResourceCapabilities()
        return cls(empty, empty, empty, empty, empty, empty, empty, empty, empty)

    @classmethod
    def full_for_tests(cls) -> Capabilities:
        cap = ResourceCapabilities(list=True, create=True, get=True, update=True, delete=True, update_method="put")
        read_only = ResourceCapabilities(list=True, get=True)
        return cls(
            proxy_hosts=cap,
            certificates=cap,
            access_lists=cap,
            redirection_hosts=cap,
            dead_hosts=cap,
            streams=cap,
            users=cap,
            settings=cap,
            audit_log=read_only,
            schema_version="test",
        )

    @classmethod
    def from_openapi(cls, spec: dict[str, Any]) -> Capabilities:
        if not isinstance(spec, dict):
            raise ValidationError("OpenAPI schema must be an object")
        paths = spec.get("paths")
        if not isinstance(paths, dict):
            raise ValidationError("OpenAPI schema missing paths object")
        version = None
        info = spec.get("info")
        if isinstance(info, dict):
            raw_version = info.get("version")
            version = str(raw_version) if raw_version is not None else None
        return cls(
            proxy_hosts=_detect(paths, "/nginx/proxy-hosts"),
            certificates=_detect(paths, "/nginx/certificates"),
            access_lists=_detect(paths, "/nginx/access-lists"),
            redirection_hosts=_detect(paths, "/nginx/redirection-hosts"),
            dead_hosts=_detect(paths, "/nginx/dead-hosts"),
            streams=_detect(paths, "/nginx/streams"),
            users=_detect(paths, "/users"),
            settings=_detect(paths, "/settings"),
            audit_log=_detect(paths, "/audit-log"),
            schema_version=version,
        )

    def for_kind(self, kind: ResourceKind) -> ResourceCapabilities:
        if kind == ResourceKind.PROXY_HOST:
            return self.proxy_hosts
        if kind == ResourceKind.CERTIFICATE:
            return self.certificates
        if kind == ResourceKind.ACCESS_LIST:
            return self.access_lists
        if kind == ResourceKind.REDIRECTION_HOST:
            return self.redirection_hosts
        if kind == ResourceKind.DEAD_HOST:
            return self.dead_hosts
        if kind == ResourceKind.STREAM:
            return self.streams
        if kind == ResourceKind.USER:
            return self.users
        if kind == ResourceKind.SETTING:
            return self.settings
        raise CapabilityError(f"unsupported resource kind: {kind}")

    def require(self, kind: ResourceKind, operation: str) -> None:
        cap = self.for_kind(kind)
        if not cap.has(operation):
            raise CapabilityError(f"NPM API does not expose {operation} for {kind.value}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "proxy_hosts": self.proxy_hosts.to_dict(),
            "certificates": self.certificates.to_dict(),
            "access_lists": self.access_lists.to_dict(),
            "redirection_hosts": self.redirection_hosts.to_dict(),
            "dead_hosts": self.dead_hosts.to_dict(),
            "streams": self.streams.to_dict(),
            "users": self.users.to_dict(),
            "settings": self.settings.to_dict(),
            "audit_log": self.audit_log.to_dict(),
        }

    @property
    def api_profile(self) -> str:
        """Stable identity for the observed NPM API surface."""

        version = self.schema_version or "unknown"
        return f"npm:{version}:{semantic_digest(self.to_dict())[:16]}"


def _detect(paths: dict[str, Any], collection: str) -> ResourceCapabilities:
    collection_methods = _methods(paths.get(collection, {}))
    item_methods: set[str] = set()
    for path, value in paths.items():
        if path.startswith(f"{collection}/") and "{" in path and "}" in path:
            item_methods |= _methods(value)
    update_method = "put" if "put" in item_methods else "patch" if "patch" in item_methods else None
    return ResourceCapabilities(
        list="get" in collection_methods,
        create="post" in collection_methods,
        get="get" in item_methods,
        update=update_method is not None,
        delete="delete" in item_methods,
        update_method=update_method,
    )


def _methods(path_item: Any) -> set[str]:
    if not isinstance(path_item, dict):
        return set()
    return {method.lower() for method in path_item if method.lower() in {"get", "post", "put", "patch", "delete"}}


def load_openapi_schema(path: str | Path) -> dict[str, Any]:
    """Load an OpenAPI schema from JSON."""

    with Path(path).open("r", encoding="utf-8") as handle:
        parsed = json.load(handle)
    if not isinstance(parsed, dict):
        raise ValidationError("schema file must contain an object")
    return parsed
