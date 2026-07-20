"""Versioned provider capabilities and mutation result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from wyrmctl.errors import CapabilityError
from wyrmctl.contracts import semantic_digest


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    provider: str
    capability_version: int
    mutation_model: str
    record_types: frozenset[str]
    requires_zone_lease: bool = False
    replan_inside_lease: bool = False
    supports_readback: bool = True
    supports_idempotency: bool = False
    supports_automatic_rollback: bool = False
    supports_forward_repair: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "capabilityVersion": self.capability_version,
            "mutationModel": self.mutation_model,
            "recordTypes": sorted(self.record_types),
            "requiresZoneLease": self.requires_zone_lease,
            "replanInsideLease": self.replan_inside_lease,
            "supportsReadback": self.supports_readback,
            "supportsIdempotency": self.supports_idempotency,
            "supportsAutomaticRollback": self.supports_automatic_rollback,
            "supportsForwardRepair": self.supports_forward_repair,
        }

    def require_record_type(self, value: str) -> None:
        if value.upper() not in self.record_types:
            raise CapabilityError(f"provider {self.provider} does not support {value.upper()} records")


@dataclass(frozen=True, slots=True)
class DnsMutationContext:
    operation_id: str
    idempotency_key: str
    expected_before_digest: str


@dataclass(frozen=True, slots=True)
class ProviderMutationResult:
    provider: str
    operation_id: str
    request_id: str | None
    observed_digest: str
    verified: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "operationId": self.operation_id,
            "requestId": self.request_id,
            "observedDigest": self.observed_digest,
            "verified": self.verified,
        }


def dns_records_digest(records: tuple[dict[str, object], ...]) -> str:
    """Digest provider-independent DNS fields in deterministic record order."""

    fields = ("name", "type", "value", "ttl", "priority")
    normalized = [
        {key: record[key] for key in fields if key in record and record[key] is not None} for record in records
    ]
    normalized.sort(key=lambda item: (str(item.get("name", "")).lower(), str(item.get("type", "")).upper()))
    return semantic_digest(normalized)
