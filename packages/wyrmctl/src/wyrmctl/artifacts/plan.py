"""PlanArtifact construction and staleness checks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from wyrmctl.artifacts.models import PlanArtifact
from wyrmctl.errors import ArtifactError


def build_plan_artifact(
    plan: Any,
    *,
    artifact_id: str,
    repository: str,
    environment: str,
    commit: str,
    desired_state_digest: str,
    live_state_fingerprint: str,
    dns_plan: Any | None = None,
    dns_live_state_fingerprint: str = "",
    provider_capabilities: dict[str, int] | None = None,
    api_profiles: dict[str, str] | None = None,
    expires_at: str | None = None,
) -> PlanArtifact:
    payload = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan)
    operations = tuple(sorted(payload.get("operations", []), key=_operation_key))
    conflicts = tuple(sorted(payload.get("conflicts", []), key=lambda item: (str(item.get("code", "")), str(item))))
    dns_payload = dns_plan.to_dict() if hasattr(dns_plan, "to_dict") else dict(dns_plan or {})
    dns_operations = tuple(sorted(dns_payload.get("operations", []), key=_operation_key))
    dns_conflicts = tuple(
        sorted(dns_payload.get("conflicts", []), key=lambda item: (str(item.get("code", "")), str(item)))
    )
    return PlanArtifact(
        artifact_id=artifact_id,
        repository=repository,
        environment=environment,
        commit=commit,
        desired_state_digest=desired_state_digest,
        live_state_fingerprint=live_state_fingerprint,
        operations=operations,
        conflicts=conflicts,
        dns_operations=dns_operations,
        dns_conflicts=dns_conflicts,
        dns_live_state_fingerprint=dns_live_state_fingerprint,
        provider_capabilities=provider_capabilities or {},
        api_profiles=api_profiles or {},
        expires_at=expires_at,
    )


def validate_plan_binding(
    artifact: PlanArtifact,
    *,
    repository: str,
    environment: str,
    commit: str,
    desired_state_digest: str,
    live_state_fingerprint: str,
    dns_live_state_fingerprint: str = "",
    provider_capabilities: dict[str, int],
    api_profiles: dict[str, str],
    now: datetime | None = None,
) -> None:
    checks = {
        "repository": (artifact.repository, repository),
        "environment": (artifact.environment, environment),
        "commit": (artifact.commit, commit),
        "desired state": (artifact.desired_state_digest, desired_state_digest),
        "live state": (artifact.live_state_fingerprint, live_state_fingerprint),
        "DNS live state": (artifact.dns_live_state_fingerprint, dns_live_state_fingerprint),
        "provider capabilities": (artifact.provider_capabilities, provider_capabilities),
        "API profiles": (artifact.api_profiles, api_profiles),
    }
    for label, (planned, current) in checks.items():
        if planned != current:
            raise ArtifactError("PLAN_STALE", f"{label} changed after planning")
    if artifact.expires_at is not None:
        current_time = now or datetime.now(timezone.utc)
        expiry = datetime.fromisoformat(artifact.expires_at.replace("Z", "+00:00"))
        if current_time >= expiry:
            raise ArtifactError("PLAN_EXPIRED", "plan artifact has expired")


def _operation_key(item: dict[str, Any]) -> tuple[int, str, str, str]:
    raw_sequence = item.get("sequence", 0)
    try:
        sequence = int(raw_sequence)
    except (TypeError, ValueError):
        sequence = 0
    return (
        sequence,
        str(item.get("kind", "")),
        str(item.get("resource_id", item.get("identity", ""))),
        str(item.get("action", "")),
    )
