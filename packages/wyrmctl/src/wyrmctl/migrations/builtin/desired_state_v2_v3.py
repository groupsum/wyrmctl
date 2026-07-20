"""DesiredState schema 2 to envelope-based schema 3 migration."""

from __future__ import annotations

from typing import Any

from wyrmctl.errors import MigrationError
from wyrmctl.profile import current_profile

KEYS = {
    "proxy_hosts": "proxyHosts",
    "certificates": "certificates",
    "access_lists": "accessLists",
    "redirection_hosts": "redirectionHosts",
    "dead_hosts": "deadHosts",
    "streams": "streams",
    "users": "users",
    "settings": "settings",
    "dns_records": "dnsRecords",
    "plugin_resources": "pluginResources",
    "external_certificates": "externalCertificates",
}


def migrate(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("schemaVersion") != 2:
        raise MigrationError("DesiredState v2 to v3 migration requires schemaVersion 2")
    owner = _single_owner(document)
    name = str(document.get("name") or f"{owner}-desired-state")
    spec = {target: list(document.get(source) or []) for source, target in KEYS.items()}
    return {
        "apiVersion": current_profile().api_version,
        "kind": "DesiredState",
        "schemaVersion": 3,
        "metadata": {"name": name, "owner": owner},
        "spec": spec,
    }


def reverse(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("schemaVersion") != 3:
        raise MigrationError("DesiredState v3 to v2 migration requires schemaVersion 3")
    spec = document.get("spec")
    if not isinstance(spec, dict):
        raise MigrationError("DesiredState v3 spec must be an object")
    reverse_keys = {target: source for source, target in KEYS.items()}
    out = {reverse_keys[key]: list(value or []) for key, value in spec.items() if key in reverse_keys}
    out["apiVersion"] = current_profile().api_version
    out["schemaVersion"] = 2
    return out


def _single_owner(document: dict[str, Any]) -> str:
    owners: set[str] = set()
    for key in KEYS:
        for item in document.get(key) or []:
            if isinstance(item, dict):
                meta = item.get("meta")
                if isinstance(meta, dict) and isinstance(meta.get("owner"), str):
                    owners.add(meta["owner"])
    return next(iter(owners)) if len(owners) == 1 else "unresolved"
