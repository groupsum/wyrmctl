"""Cloudflare DNS response models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class CloudflareZone:
    """One Cloudflare zone."""

    zone_id: str
    name: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> CloudflareZone:
        return cls(zone_id=str(raw.get("id", "")), name=str(raw.get("name", "")).lower().rstrip("."))


@dataclass(frozen=True, slots=True)
class CloudflareRecord:
    """One Cloudflare DNS record."""

    record_id: str | None
    name: str
    type: str
    value: str
    ttl: int | None = None
    priority: int | None = None
    proxied: bool | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> CloudflareRecord:
        return cls(
            record_id=_optional_str(raw.get("id")),
            name=str(raw.get("name", "")).lower().rstrip("."),
            type=str(raw.get("type", "")).upper(),
            value=str(raw.get("content", "")),
            ttl=_optional_int(raw.get("ttl")),
            priority=_optional_int(raw.get("priority")),
            proxied=_optional_bool(raw.get("proxied")),
        )

    def to_dict(self) -> dict[str, str | int | bool | None]:
        return {
            "id": self.record_id,
            "name": self.name,
            "type": self.type,
            "value": self.value,
            "ttl": self.ttl,
            "priority": self.priority,
            "proxied": self.proxied,
        }


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
