"""wyrmctl DNS provider implementation for Route 53."""

from __future__ import annotations

from typing import Any

from wyrmctl.providers import DnsMutationContext, ProviderCapabilities, ProviderMutationResult, dns_records_digest

from wyrmctl_route53.capabilities import CAPABILITIES
from wyrmctl_route53.client import Route53Client
from wyrmctl_route53.config import Route53Config


class Route53DnsProvider:
    """DNS provider backed by AWS Route 53."""

    name = "route53"

    def __init__(self, client: Route53Client | None = None) -> None:
        self._client = client

    @property
    def client(self) -> Route53Client:
        if self._client is None:
            self._client = Route53Client(Route53Config.from_env())
        return self._client

    def zones(self) -> tuple[str, ...]:
        return self.client.zones()

    def records(self, zone: str) -> tuple[dict[str, object], ...]:
        return tuple(_relative_record(zone, record.to_dict()) for record in self.client.records(zone))

    def capabilities(self) -> ProviderCapabilities:
        return CAPABILITIES

    def apply_records(
        self,
        zone: str,
        records: tuple[dict[str, object], ...],
        context: DnsMutationContext | None = None,
    ) -> ProviderMutationResult:
        current = {_record_key(record): record for record in self.records(zone)}
        desired = {_record_key(record): _normalized_record(record) for record in records}
        for key, record in sorted(current.items()):
            if key not in desired:
                self.client.delete_record(zone, **_record_payload(record))
        for key, record in sorted(desired.items()):
            existing = current.get(key)
            if existing is None:
                self.client.create_record(zone, **_record_payload(record))
            elif _record_changed(existing, record):
                self.client.upsert_record(zone, **_record_payload(record))
        observed = self.records(zone)
        return ProviderMutationResult(
            self.name,
            context.operation_id if context else f"dns:{zone}",
            None,
            dns_records_digest(observed),
            dns_records_digest(observed) == dns_records_digest(tuple(desired.values())),
        )


def _record_key(record: dict[str, Any]) -> tuple[str, str]:
    return (str(record.get("name", "")).lower().rstrip(".") or "@", str(record.get("type", "")).upper())


def _relative_record(zone: str, record: dict[str, Any]) -> dict[str, Any]:
    out = dict(record)
    zone_name = zone.lower().rstrip(".")
    name = str(out.get("name", "")).lower().rstrip(".")
    if name == zone_name:
        out["name"] = "@"
    elif name.endswith(f".{zone_name}"):
        out["name"] = name[: -len(zone_name) - 1]
    else:
        out["name"] = name
    return out


def _normalized_record(record: dict[str, Any]) -> dict[str, Any]:
    out = dict(record)
    out["name"] = str(out.get("name", "")).lower().rstrip(".") or "@"
    out["type"] = str(out.get("type", "")).upper()
    if "ttl" in out and out["ttl"] is not None:
        out["ttl"] = int(out["ttl"])
    if "priority" in out and out["priority"] is not None:
        out["priority"] = int(out["priority"])
    return out


def _record_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "type": str(record["type"]),
        "name": str(record["name"]),
        "value": str(record.get("value", "")),
        "ttl": int(record.get("ttl") or 300),
    }
    if record.get("priority") is not None:
        payload["priority"] = int(record["priority"])
    return payload


def _record_changed(existing: dict[str, Any], desired: dict[str, Any]) -> bool:
    for key in ("value", "ttl", "priority"):
        if desired.get(key) != existing.get(key):
            return True
    return False
