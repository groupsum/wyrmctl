"""wyrmctl DNS provider implementation for DigitalOcean."""

from __future__ import annotations

from typing import Any

from wyrmctl.providers import DnsMutationContext, ProviderCapabilities, ProviderMutationResult, dns_records_digest

from wyrmctl_digitalocean.capabilities import CAPABILITIES
from wyrmctl_digitalocean.client import DigitalOceanClient
from wyrmctl_digitalocean.config import DigitalOceanConfig


class DigitalOceanDnsProvider:
    """DNS provider backed by the DigitalOcean Domain Records API."""

    name = "digitalocean"

    def __init__(self, client: DigitalOceanClient | None = None) -> None:
        self._client = client

    @property
    def client(self) -> DigitalOceanClient:
        if self._client is None:
            self._client = DigitalOceanClient(DigitalOceanConfig.from_env())
        return self._client

    def zones(self) -> tuple[str, ...]:
        return self.client.zones()

    def records(self, zone: str) -> tuple[dict[str, object], ...]:
        return tuple(record.to_dict() for record in self.client.records(zone))

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
            if key not in desired and record.get("id") is not None:
                self.client.delete_record(zone, int(record["id"]))
        for key, record in sorted(desired.items()):
            existing = current.get(key)
            if existing is None:
                self.client.create_record(zone, **_record_payload(record))
            elif _record_changed(existing, record) and existing.get("id") is not None:
                self.client.update_record(zone, int(existing["id"]), **_record_payload(record))
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
    }
    for key in ("ttl", "priority"):
        if record.get(key) is not None:
            payload[key] = record[key]
    return payload


def _record_changed(existing: dict[str, Any], desired: dict[str, Any]) -> bool:
    for key in ("value", "ttl", "priority"):
        if desired.get(key) != existing.get(key):
            return True
    return False
