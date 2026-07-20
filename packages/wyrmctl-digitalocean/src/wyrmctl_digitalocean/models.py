"""DigitalOcean DNS response models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class DigitalOceanRecord:
    """One DigitalOcean domain record."""

    record_id: int | None
    name: str
    type: str
    value: str
    ttl: int | None = None
    priority: int | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> DigitalOceanRecord:
        return cls(
            record_id=_optional_int(raw.get("id")),
            name=str(raw.get("name", "")).lower().rstrip("."),
            type=str(raw.get("type", "")).upper(),
            value=str(raw.get("data", "")),
            ttl=_optional_int(raw.get("ttl")),
            priority=_optional_int(raw.get("priority")),
        )

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "id": self.record_id,
            "name": self.name,
            "type": self.type,
            "value": self.value,
            "ttl": self.ttl,
            "priority": self.priority,
        }


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)
