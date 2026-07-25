"""Immutable execution artifact models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from wyrmctl.contracts import semantic_digest
from wyrmctl.profile import current_profile


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ArtifactSignature:
    algorithm: str
    key_id: str
    value: str
    signed_at: str

    def to_dict(self) -> dict[str, str]:
        return {"algorithm": self.algorithm, "keyId": self.key_id, "value": self.value, "signedAt": self.signed_at}


@dataclass(frozen=True, slots=True)
class PlanArtifact:
    artifact_id: str
    repository: str
    environment: str
    commit: str
    desired_state_digest: str
    live_state_fingerprint: str
    operations: tuple[dict[str, Any], ...]
    conflicts: tuple[dict[str, Any], ...] = ()
    dns_operations: tuple[dict[str, Any], ...] = ()
    dns_conflicts: tuple[dict[str, Any], ...] = ()
    dns_live_state_fingerprint: str = ""
    provider_capabilities: dict[str, int] = field(default_factory=dict)
    api_profiles: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    expires_at: str | None = None
    signature: ArtifactSignature | None = None

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "apiVersion": current_profile().api_version,
            "kind": "PlanArtifact",
            "schemaVersion": 1,
            "metadata": {
                "id": self.artifact_id,
                "repository": self.repository,
                "environment": self.environment,
                "createdAt": self.created_at,
                "expiresAt": self.expires_at,
            },
            "spec": {
                "source": {"commit": self.commit},
                "inputs": {
                    "desiredStateDigest": self.desired_state_digest,
                    "liveStateFingerprint": self.live_state_fingerprint,
                },
                "providerCapabilities": self.provider_capabilities,
                "apiProfiles": self.api_profiles,
                "operations": list(self.operations),
                "conflicts": list(self.conflicts),
                "dns": {
                    "liveStateFingerprint": self.dns_live_state_fingerprint,
                    "operations": list(self.dns_operations),
                    "conflicts": list(self.dns_conflicts),
                },
            },
        }

    @property
    def digest(self) -> str:
        return semantic_digest(self.unsigned_dict())

    def to_dict(self) -> dict[str, Any]:
        payload = self.unsigned_dict()
        if self.signature is not None:
            payload["signature"] = self.signature.to_dict()
        return payload


@dataclass(frozen=True, slots=True)
class LiveStateSnapshot:
    repository: str
    environment: str
    resources: tuple[dict[str, Any], ...]
    observed_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "apiVersion": current_profile().api_version,
            "kind": "LiveStateSnapshot",
            "schemaVersion": 1,
            "metadata": {
                "repository": self.repository,
                "environment": self.environment,
                "observedAt": self.observed_at,
            },
            "spec": {"resources": list(self.resources)},
        }

    @property
    def fingerprint(self) -> str:
        return semantic_digest(self.to_dict()["spec"])


@dataclass(frozen=True, slots=True)
class ApplyReport:
    plan_id: str
    plan_digest: str
    status: str
    results: tuple[dict[str, Any], ...]
    verification: dict[str, Any]
    completed_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "apiVersion": current_profile().api_version,
            "kind": "ApplyReport",
            "schemaVersion": 1,
            "metadata": {"planId": self.plan_id, "completedAt": self.completed_at},
            "spec": {
                "planArtifactDigest": self.plan_digest,
                "status": self.status,
                "results": list(self.results),
                "verification": self.verification,
            },
        }
