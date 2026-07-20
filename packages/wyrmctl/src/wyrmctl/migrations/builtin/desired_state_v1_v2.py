"""DesiredState schema 1 to 2 migration."""

from __future__ import annotations

from typing import Any

from wyrmctl.errors import MigrationError
from wyrmctl.profile import current_profile


def migrate(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("schemaVersion") != 1:
        raise MigrationError("DesiredState v1 to v2 migration requires schemaVersion 1")
    out = dict(document)
    out.setdefault("dns_records", [])
    out["apiVersion"] = current_profile().api_version
    out["schemaVersion"] = 2
    return out


def reverse(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("schemaVersion") != 2:
        raise MigrationError("DesiredState v2 to v1 migration requires schemaVersion 2")
    out = dict(document)
    if out.get("dns_records") not in (None, []):
        raise MigrationError("DesiredState v2 with DNS records cannot be downgraded to v1")
    out.pop("dns_records", None)
    out["schemaVersion"] = 1
    return out
