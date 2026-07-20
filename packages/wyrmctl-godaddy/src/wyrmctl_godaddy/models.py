"""GoDaddy DNS response models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class GoDaddyRecord:
    """One GoDaddy DNS record."""

    name: str
    type: str
    value: str
    ttl: int | None = None
    priority: int | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> GoDaddyRecord:
        return cls(
            name=str(raw.get("name", "")).lower().rstrip("."),
            type=str(raw.get("type", "")).upper(),
            value=str(raw.get("data", "")),
            ttl=_optional_int(raw.get("ttl")),
            priority=_optional_int(raw.get("priority")),
        )

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "id": None,
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
