"""Non-mutating live-resource import classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ImportClassification:
    identity: str
    classification: str
    desired: dict[str, Any] | None
    observed: dict[str, Any]


def classify_live_resources(
    observed: list[dict[str, Any]], desired: list[dict[str, Any]], *, owner: str
) -> tuple[ImportClassification, ...]:
    wanted = {str(item["identity"]): item for item in desired}
    out: list[ImportClassification] = []
    for item in observed:
        identity = str(item.get("identity", ""))
        live_owner = item.get("owner")
        target = wanted.get(identity)
        if not identity:
            classification = "ambiguous"
        elif live_owner == owner:
            classification = "owned"
        elif live_owner:
            classification = "foreign-owned"
        elif target is None:
            classification = "ambiguous"
        elif _comparable(item) == _comparable(target):
            classification = "unmanaged-matching"
        else:
            classification = "unmanaged-drifting"
        out.append(ImportClassification(identity, classification, target, dict(item)))
    return tuple(sorted(out, key=lambda row: row.identity))


def _comparable(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in {"owner", "managed_by", "resource_id"}}
