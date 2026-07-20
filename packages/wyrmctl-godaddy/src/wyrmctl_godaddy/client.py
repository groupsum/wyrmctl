"""Small GoDaddy Domains API client."""

from __future__ import annotations

from typing import Any, Mapping

import requests

from wyrmctl_godaddy.config import GoDaddyConfig
from wyrmctl_godaddy.errors import GoDaddyError
from wyrmctl_godaddy.models import GoDaddyRecord


class GoDaddyClient:
    """HTTP client for GoDaddy domain DNS records."""

    def __init__(self, config: GoDaddyConfig, *, timeout_s: float = 15.0) -> None:
        self.config = config
        self.timeout_s = timeout_s
        self.session = requests.Session()

    def zones(self) -> tuple[str, ...]:
        data = self._request("GET", "/v1/domains")
        return tuple(sorted(str(item.get("domain", "")).lower().rstrip(".") for item in data if item.get("domain")))

    def records(self, zone: str) -> tuple[GoDaddyRecord, ...]:
        data = self._request("GET", f"/v1/domains/{_zone(zone)}/records")
        return tuple(GoDaddyRecord.from_mapping(item) for item in data)

    def records_by_name(self, zone: str, *, type: str, name: str) -> tuple[GoDaddyRecord, ...]:
        data = self._request("GET", f"/v1/domains/{_zone(zone)}/records/{type.upper()}/{_name(name)}")
        return tuple(GoDaddyRecord.from_mapping({**item, "type": type.upper(), "name": name}) for item in data)

    def create_record(self, zone: str, *, type: str, name: str, value: str, ttl: int | None = None) -> None:
        record: dict[str, object] = {"data": value}
        if ttl is not None:
            record["ttl"] = ttl
        self.replace_records(zone, type=type, name=name, records=[record])

    def replace_records(self, zone: str, *, type: str, name: str, records: list[Mapping[str, object]]) -> None:
        payload = [_record_payload(item) for item in records]
        self._request("PUT", f"/v1/domains/{_zone(zone)}/records/{type.upper()}/{_name(name)}", json=payload)

    def delete_records(self, zone: str, *, type: str, name: str) -> None:
        self._request("DELETE", f"/v1/domains/{_zone(zone)}/records/{type.upper()}/{_name(name)}")

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.session.request(
            method,
            f"{self.config.api_base_url}{path}",
            headers={"Authorization": f"sso-key {self.config.api_key}:{self.config.api_secret}"},
            timeout=self.timeout_s,
            **kwargs,
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise GoDaddyError(f"GoDaddy API failed: HTTP {response.status_code}")
        if response.status_code == 204:
            return []
        try:
            return response.json()
        except ValueError as exc:
            raise GoDaddyError("GoDaddy API returned invalid JSON") from exc


def _record_payload(item: Mapping[str, object]) -> dict[str, object]:
    payload = {"data": item["data"]}
    for key in ("ttl", "priority", "port", "protocol", "service", "weight"):
        if key in item and item[key] is not None:
            payload[key] = item[key]
    return payload


def _name(name: str) -> str:
    return name.strip().lower().rstrip(".")


def _zone(zone: str) -> str:
    return zone.strip().lower().rstrip(".")
