"""Provider-backed DNS reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from wyrmctl.contracts import semantic_digest
from wyrmctl.models import DesiredDnsRecord, PlanAction
from wyrmctl.plugins import DnsProvider, dns_capabilities
from wyrmctl.providers import DnsMutationContext, ProviderMutationResult
from wyrmctl.profile import current_profile


@dataclass(frozen=True, slots=True)
class DnsPlanConflict:
    """A DNS safety conflict that blocks apply."""

    code: str
    message: str
    provider: str | None = None
    zone: str | None = None
    owner: str | None = None
    resource_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "provider": self.provider,
            "zone": self.zone,
            "owner": self.owner,
            "resource_id": self.resource_id,
        }


@dataclass(frozen=True, slots=True)
class DnsPlanOperation:
    """One DNS planned mutation or no-op."""

    action: PlanAction
    provider: str
    zone: str
    name: str
    type: str
    desired: dict[str, Any] | None = None
    existing: dict[str, Any] | None = None
    reason: str = ""
    diff: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def owner(self) -> str | None:
        identity = _identity(self.desired) or _identity(self.existing)
        return identity[0] if identity is not None else None

    @property
    def resource_id(self) -> str | None:
        identity = _identity(self.desired) or _identity(self.existing)
        return identity[1] if identity is not None else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "kind": "dns_record",
            "provider": self.provider,
            "zone": self.zone,
            "name": self.name,
            "type": self.type,
            "owner": self.owner,
            "resource_id": self.resource_id,
            "existing": self.existing,
            "reason": self.reason,
            "diff": self.diff,
        }


@dataclass(frozen=True, slots=True)
class DnsPlan:
    """Complete provider-backed DNS plan."""

    operations: tuple[DnsPlanOperation, ...] = ()
    conflicts: tuple[DnsPlanConflict, ...] = ()
    existing_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.conflicts

    def by_action(self, action: PlanAction) -> tuple[DnsPlanOperation, ...]:
        return tuple(op for op in self.operations if op.action == action)

    def has_mutations(self) -> bool:
        return any(op.action in {PlanAction.CREATE, PlanAction.UPDATE, PlanAction.DELETE} for op in self.operations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "existing_count": self.existing_count,
            "summary": {
                action.value: len(self.by_action(action)) for action in PlanAction if action != PlanAction.CONFLICT
            }
            | {"conflict": len(self.conflicts)},
            "operations": [op.to_dict() for op in self.operations],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
        }


@dataclass(frozen=True, slots=True)
class DnsApplyResult:
    """Result of applying DNS operations."""

    applied: bool
    mutations: list[dict[str, Any]] = field(default_factory=list)
    provider_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "applied": self.applied,
            "mutations": list(self.mutations),
            "provider_results": list(self.provider_results),
        }


def compute_dns_plan(
    desired_records: tuple[DesiredDnsRecord, ...],
    providers: Mapping[str, DnsProvider],
    *,
    owner: str | None = None,
    prune_owned: bool = False,
) -> DnsPlan:
    """Compute DNS create/update/delete/no-op operations against provider state."""

    selected = tuple(record for record in desired_records if owner is None or record.identity.owner == owner)
    if not selected and not prune_owned:
        return DnsPlan()

    operations: list[DnsPlanOperation] = []
    conflicts: list[DnsPlanConflict] = []
    existing_count = 0
    desired_by_scope: dict[tuple[str, str], list[DesiredDnsRecord]] = {}
    scopes = {(record.provider, record.zone) for record in selected}
    if prune_owned:
        scopes.update(
            (provider_name, zone) for provider_name, provider in providers.items() for zone in provider.zones()
        )
    for record in selected:
        desired_by_scope.setdefault((record.provider, record.zone), []).append(record)

    for provider_name, zone in sorted(scopes):
        provider = providers.get(provider_name)
        if provider is None:
            for record in desired_by_scope.get((provider_name, zone), []):
                conflicts.append(
                    DnsPlanConflict(
                        code="missing_dns_provider",
                        message=f"DNS provider {provider_name!r} is not installed",
                        provider=provider_name,
                        zone=zone,
                        owner=record.identity.owner,
                        resource_id=record.identity.resource_id,
                    )
                )
            continue
        existing = tuple(_normalized_record(provider_name, zone, record) for record in provider.records(zone))
        existing_count += len(existing)
        existing_by_key = {_record_key(record): record for record in existing}
        desired_keys: set[tuple[str, str, str, str]] = set()
        mutating = False

        for record in desired_by_scope.get((provider_name, zone), []):
            desired = record.to_payload()
            key = _record_key(desired)
            desired_keys.add(key)
            current = existing_by_key.get(key)
            if current is None:
                mutating = True
                operations.append(
                    DnsPlanOperation(
                        PlanAction.CREATE,
                        provider_name,
                        zone,
                        record.name,
                        record.type.value,
                        desired=desired,
                        reason="missing",
                    )
                )
                continue
            diff = diff_dns_record(desired, current)
            if diff:
                mutating = True
                operations.append(
                    DnsPlanOperation(
                        PlanAction.UPDATE,
                        provider_name,
                        zone,
                        record.name,
                        record.type.value,
                        desired=desired,
                        existing=current,
                        reason="record drift",
                        diff=diff,
                    )
                )
            else:
                operations.append(
                    DnsPlanOperation(
                        PlanAction.NOOP,
                        provider_name,
                        zone,
                        record.name,
                        record.type.value,
                        desired=desired,
                        existing=current,
                        reason="already converged",
                    )
                )

        if prune_owned:
            prune_owner = owner
            for current in existing:
                identity = _identity(current)
                if identity is None or (prune_owner is not None and identity[0] != prune_owner):
                    continue
                key = _record_key(current)
                if key in desired_keys:
                    continue
                mutating = True
                operations.append(
                    DnsPlanOperation(
                        PlanAction.DELETE,
                        provider_name,
                        zone,
                        str(current["name"]),
                        str(current["type"]),
                        existing=current,
                        reason="owned DNS record absent from desired state",
                    )
                )

        if mutating and not hasattr(provider, "apply_records"):
            conflicts.append(
                DnsPlanConflict(
                    code="read_only_dns_provider",
                    message=f"DNS provider {provider_name!r} does not support apply_records",
                    provider=provider_name,
                    zone=zone,
                )
            )

    return DnsPlan(operations=tuple(operations), conflicts=tuple(conflicts), existing_count=existing_count)


def apply_dns_plan(plan: DnsPlan, providers: Mapping[str, DnsProvider]) -> DnsApplyResult:
    """Apply DNS plan operations provider-by-provider and zone-by-zone."""

    if plan.conflicts:
        messages = "; ".join(conflict.message for conflict in plan.conflicts)
        raise ValueError(f"refusing to apply DNS plan with conflicts: {messages}")

    by_scope: dict[tuple[str, str], list[DnsPlanOperation]] = {}
    for operation in plan.operations:
        if operation.action in {PlanAction.CREATE, PlanAction.UPDATE, PlanAction.DELETE}:
            by_scope.setdefault((operation.provider, operation.zone), []).append(operation)

    mutations: list[dict[str, Any]] = []
    provider_results: list[dict[str, Any]] = []
    for (provider_name, zone), operations in sorted(by_scope.items()):
        provider = providers[provider_name]
        if not hasattr(provider, "apply_records"):
            raise ValueError(f"DNS provider {provider_name!r} does not support apply_records")
        next_records = {
            _record_key(record): _normalized_record(provider_name, zone, record) for record in provider.records(zone)
        }
        for operation in operations:
            if operation.action == PlanAction.DELETE and operation.existing is not None:
                next_records.pop(_record_key(operation.existing), None)
            elif operation.desired is not None:
                next_records[_record_key(operation.desired)] = dict(operation.desired)
            mutations.append(operation.to_dict())
        target = tuple(next_records[key] for key in sorted(next_records))
        operation_id = semantic_digest([operation.to_dict() for operation in operations])
        context = DnsMutationContext(
            operation_id=operation_id,
            idempotency_key=semantic_digest({"provider": provider_name, "zone": zone, "target": target}),
            expected_before_digest=semantic_digest(provider.records(zone)),
        )
        if hasattr(provider, "capabilities"):
            capabilities = dns_capabilities(provider)
            for record in target:
                capabilities.require_record_type(str(record["type"]))
            result = provider.apply_records(zone, target, context)
            if not isinstance(result, ProviderMutationResult) or not result.verified:
                raise ValueError(f"DNS provider {provider_name!r} did not verify mutation readback")
            provider_results.append(result.to_dict())
        else:
            provider.apply_records(zone, target)

    return DnsApplyResult(applied=True, mutations=mutations, provider_results=provider_results)


def diff_dns_record(desired: Mapping[str, Any], existing: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Return desired-vs-existing diff for DNS record fields controlled by desired."""

    diff: dict[str, dict[str, Any]] = {}
    for key in ("value", "ttl", "priority"):
        desired_value = desired.get(key)
        existing_value = existing.get(key)
        if desired_value != existing_value:
            diff[key] = {"actual": existing_value, "desired": desired_value}
    return diff


def _normalized_record(provider: str, zone: str, record: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(record)
    out.setdefault("provider", provider)
    out.setdefault("zone", zone)
    out["provider"] = str(out["provider"]).strip().lower()
    out["zone"] = str(out["zone"]).strip().lower().rstrip(".")
    out["name"] = str(out.get("name", "")).strip().lower().rstrip(".") or "@"
    out["type"] = str(out.get("type", "")).strip().upper()
    if "ttl" in out and out["ttl"] is not None:
        out["ttl"] = int(out["ttl"])
    if "priority" in out and out["priority"] is not None:
        out["priority"] = int(out["priority"])
    return out


def _record_key(record: Mapping[str, Any]) -> tuple[str, str, str, str]:
    normalized = _normalized_record(str(record.get("provider", "")), str(record.get("zone", "")), record)
    return (
        str(normalized["provider"]),
        str(normalized["zone"]),
        str(normalized["name"]),
        str(normalized["type"]),
    )


def _identity(record: Mapping[str, Any] | None) -> tuple[str, str] | None:
    if record is None:
        return None
    meta = record.get("meta")
    if not isinstance(meta, Mapping):
        return None
    if meta.get("managed_by") != current_profile().managed_by or not meta.get("owner") or not meta.get("resource_id"):
        return None
    return str(meta["owner"]), str(meta["resource_id"])
