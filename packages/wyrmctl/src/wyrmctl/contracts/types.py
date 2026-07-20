"""Versioned contract datatypes shared by wyrmctl documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

DocumentParser = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True, slots=True)
class ContractSupport:
    """Supported versions and parsers for one document kind."""

    kind: str
    current: int
    readable: frozenset[int]
    writable: frozenset[int]
    deprecated: frozenset[int] = frozenset()
    parsers: dict[int, DocumentParser] = field(default_factory=dict, compare=False, hash=False, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "current": self.current,
            "read": sorted(self.readable),
            "write": sorted(self.writable),
            "deprecated": sorted(self.deprecated),
        }


@dataclass(frozen=True, slots=True)
class DocumentEnvelope:
    """Common identity fields present on every native wyrmctl contract."""

    api_version: str
    kind: str
    schema_version: int
    metadata: dict[str, Any]
    spec: dict[str, Any]

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> DocumentEnvelope:
        metadata = value.get("metadata", {})
        spec = value.get("spec", {})
        if not isinstance(metadata, dict) or not isinstance(spec, dict):
            raise ValueError("contract metadata and spec must be objects")
        return cls(
            api_version=str(value.get("apiVersion", "")),
            kind=str(value.get("kind", "")),
            schema_version=int(value.get("schemaVersion", 0)),
            metadata=dict(metadata),
            spec=dict(spec),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "apiVersion": self.api_version,
            "kind": self.kind,
            "schemaVersion": self.schema_version,
            "metadata": self.metadata,
            "spec": self.spec,
        }
