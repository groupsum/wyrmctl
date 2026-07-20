"""Small DigitalOcean DNS API client."""

from __future__ import annotations

from typing import Any

import requests

from wyrmctl_digitalocean.config import DigitalOceanConfig
from wyrmctl_digitalocean.errors import DigitalOceanError
from wyrmctl_digitalocean.models import DigitalOceanRecord


class DigitalOceanClient:
    """HTTP client for DigitalOcean domain records."""

    def __init__(self, config: DigitalOceanConfig, *, timeout_s: float = 15.0) -> None:
        self.config = config
        self.timeout_s = timeout_s
        self.session = requests.Session()

    def zones(self) -> tuple[str, ...]:
        data = self._request("GET", "/v2/domains")
        return tuple(sorted(_zone(str(item.get("name", ""))) for item in data.get("domains", []) if item.get("name")))

    def records(self, zone: str) -> tuple[DigitalOceanRecord, ...]:
        data = self._request("GET", f"/v2/domains/{_zone(zone)}/records")
        return tuple(DigitalOceanRecord.from_mapping(item) for item in data.get("domain_records", []))

    def create_record(
        self,
        zone: str,
        *,
        type: str,
        name: str,
        value: str,
        ttl: int | None = None,
        priority: int | None = None,
    ) -> DigitalOceanRecord:
        data = self._request(
            "POST", f"/v2/domains/{_zone(zone)}/records", json=_record_payload(type, name, value, ttl, priority)
        )
        return DigitalOceanRecord.from_mapping(data.get("domain_record", {}))

    def update_record(
        self,
        zone: str,
        record_id: int,
        *,
        type: str,
        name: str,
        value: str,
        ttl: int | None = None,
        priority: int | None = None,
    ) -> DigitalOceanRecord:
        data = self._request(
            "PUT",
            f"/v2/domains/{_zone(zone)}/records/{record_id}",
            json=_record_payload(type, name, value, ttl, priority),
        )
        return DigitalOceanRecord.from_mapping(data.get("domain_record", {}))

    def delete_record(self, zone: str, record_id: int) -> None:
        self._request("DELETE", f"/v2/domains/{_zone(zone)}/records/{record_id}")

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self.session.request(
            method,
            f"{self.config.api_base_url}{path}",
            headers={"Authorization": f"Bearer {self.config.token}"},
            timeout=self.timeout_s,
            **kwargs,
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise DigitalOceanError(f"DigitalOcean API failed: HTTP {response.status_code}")
        if response.status_code == 204:
            return {}
        try:
            data = response.json()
        except ValueError as exc:
            raise DigitalOceanError("DigitalOcean API returned invalid JSON") from exc
        if isinstance(data, dict) and data.get("id") == "unauthorized":
            raise DigitalOceanError(str(data.get("message", "DigitalOcean API request failed")))
        return data


def _record_payload(type: str, name: str, value: str, ttl: int | None, priority: int | None) -> dict[str, object]:
    payload: dict[str, object] = {"type": type.upper(), "name": name, "data": value}
    if ttl is not None:
        payload["ttl"] = ttl
    if priority is not None:
        payload["priority"] = priority
    return payload


def _zone(zone: str) -> str:
    return zone.strip().lower().rstrip(".")
