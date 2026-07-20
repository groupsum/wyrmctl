"""Namecheap DNS response models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class NamecheapRecord:
    """One Namecheap host record."""

    host_id: str | None
    name: str
    type: str
    address: str
    ttl: int | None = None
    mx_pref: int | None = None

    @classmethod
    def from_attrs(cls, attrs: Mapping[str, Any]) -> NamecheapRecord:
        ttl = _optional_int(attrs.get("TTL"))
        mx_pref = _optional_int(attrs.get("MXPref"))
        return cls(
            host_id=_optional_str(attrs.get("HostId")),
            name=str(attrs.get("Name", "")).lower(),
            type=str(attrs.get("Type", "")).upper(),
            address=str(attrs.get("Address", "")),
            ttl=ttl,
            mx_pref=mx_pref,
        )

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "id": self.host_id,
            "name": self.name,
            "type": self.type,
            "value": self.address,
            "ttl": self.ttl,
            "priority": self.mx_pref,
        }


def split_zone(zone: str) -> tuple[str, str]:
    labels = zone.strip().lower().rstrip(".").split(".")
    if len(labels) < 2 or any(not label for label in labels):
        raise ValueError("zone must be a domain such as example.com")
    return ".".join(labels[:-1]), labels[-1]


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
