"""Small Cloudflare DNS API client."""

from __future__ import annotations

from typing import Any

import requests

from wyrmctl_cloudflare.config import CloudflareConfig
from wyrmctl_cloudflare.errors import CloudflareError
from wyrmctl_cloudflare.models import CloudflareRecord, CloudflareZone


class CloudflareClient:
    """HTTP client for Cloudflare DNS records."""

    def __init__(self, config: CloudflareConfig, *, timeout_s: float = 15.0) -> None:
        self.config = config
        self.timeout_s = timeout_s
        self.session = requests.Session()

    def zones(self) -> tuple[str, ...]:
        return tuple(zone.name for zone in self._zones())

    def records(self, zone: str) -> tuple[CloudflareRecord, ...]:
        zone_id = self._zone_id(zone)
        return tuple(
            CloudflareRecord.from_mapping(item)
            for item in self._request("GET", f"/zones/{zone_id}/dns_records").get("result", [])
        )

    def create_record(
        self,
        zone: str,
        *,
        type: str,
        name: str,
        value: str,
        ttl: int | None = None,
        priority: int | None = None,
        proxied: bool | None = None,
    ) -> CloudflareRecord:
        payload: dict[str, object] = {"type": type.upper(), "name": name, "content": value}
        if ttl is not None:
            payload["ttl"] = ttl
        if priority is not None:
            payload["priority"] = priority
        if proxied is not None:
            payload["proxied"] = proxied
        data = self._request("POST", f"/zones/{self._zone_id(zone)}/dns_records", json=payload)
        return CloudflareRecord.from_mapping(data.get("result", {}))

    def put_record(
        self,
        zone: str,
        record_id: str,
        *,
        type: str,
        name: str,
        value: str,
        ttl: int | None = None,
        priority: int | None = None,
        proxied: bool | None = None,
    ) -> CloudflareRecord:
        payload: dict[str, object] = {"type": type.upper(), "name": name, "content": value}
        if ttl is not None:
            payload["ttl"] = ttl
        if priority is not None:
            payload["priority"] = priority
        if proxied is not None:
            payload["proxied"] = proxied
        data = self._request("PUT", f"/zones/{self._zone_id(zone)}/dns_records/{record_id}", json=payload)
        return CloudflareRecord.from_mapping(data.get("result", {}))

    def patch_record(self, zone: str, record_id: str, **changes: object) -> CloudflareRecord:
        payload = _cloudflare_payload(changes)
        data = self._request("PATCH", f"/zones/{self._zone_id(zone)}/dns_records/{record_id}", json=payload)
        return CloudflareRecord.from_mapping(data.get("result", {}))

    def delete_record(self, zone: str, record_id: str) -> str | None:
        data = self._request("DELETE", f"/zones/{self._zone_id(zone)}/dns_records/{record_id}")
        result = data.get("result")
        if isinstance(result, dict):
            deleted_id = result.get("id")
            return None if deleted_id is None else str(deleted_id)
        return None

    def _zones(self) -> tuple[CloudflareZone, ...]:
        data = self._request("GET", "/zones")
        return tuple(CloudflareZone.from_mapping(item) for item in data.get("result", []))

    def _zone_id(self, zone: str) -> str:
        target = zone.lower().rstrip(".")
        for item in self._zones():
            if item.name == target:
                return item.zone_id
        raise CloudflareError(f"Cloudflare zone not found: {zone}")

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self.session.request(
            method,
            f"{self.config.api_base_url}{path}",
            headers={"Authorization": f"Bearer {self.config.api_token}"},
            timeout=self.timeout_s,
            **kwargs,
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise CloudflareError(f"Cloudflare API failed: HTTP {response.status_code}")
        try:
            data = response.json()
        except ValueError as exc:
            raise CloudflareError("Cloudflare API returned invalid JSON") from exc
        if data.get("success") is False:
            messages = [
                str(item.get("message", "unknown error")) for item in data.get("errors", []) if isinstance(item, dict)
            ]
            raise CloudflareError("; ".join(messages) or "Cloudflare API request failed")
        return data


def _cloudflare_payload(changes: dict[str, object]) -> dict[str, object]:
    payload = dict(changes)
    if "value" in payload:
        payload["content"] = payload.pop("value")
    if "type" in payload and isinstance(payload["type"], str):
        payload["type"] = payload["type"].upper()
    return payload
