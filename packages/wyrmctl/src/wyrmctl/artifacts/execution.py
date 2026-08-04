"""Rehydrate an exact reviewed PlanArtifact for execution."""

from __future__ import annotations

from typing import Any

from wyrmctl.dns import DnsPlan, DnsPlanConflict, DnsPlanOperation
from wyrmctl.errors import ArtifactError
from wyrmctl.models import (
    DesiredAccessList,
    DesiredCertificate,
    DesiredGenericResource,
    DesiredProxyHost,
    ExistingResource,
    PlanAction,
    ResourceKind,
)
from wyrmctl.planner import Plan, PlanConflict, PlanOperation


def plan_from_artifact(document: dict[str, Any]) -> Plan:
    if document.get("kind") != "PlanArtifact" or document.get("schemaVersion") != 1:
        raise ArtifactError("INVALID_PLAN_ARTIFACT", "apply requires a PlanArtifact schema 1 document")
    spec = document.get("spec")
    if not isinstance(spec, dict):
        raise ArtifactError("INVALID_PLAN_ARTIFACT", "plan artifact spec must be an object")
    operations = tuple(_operation(item, index) for index, item in enumerate(_items(spec, "operations")))
    conflicts = tuple(_conflict(item, index) for index, item in enumerate(_items(spec, "conflicts")))
    return Plan(operations, conflicts, sum(operation.existing is not None for operation in operations))


def dns_plan_from_artifact(document: dict[str, Any]) -> DnsPlan:
    if document.get("kind") != "PlanArtifact" or document.get("schemaVersion") != 1:
        raise ArtifactError("INVALID_PLAN_ARTIFACT", "apply requires a PlanArtifact schema 1 document")
    spec = _mapping(document.get("spec"), "spec")
    dns = _mapping(spec.get("dns", {}), "spec.dns")
    operations = tuple(_dns_operation(item, index) for index, item in enumerate(_items(dns, "operations")))
    conflicts = tuple(_dns_conflict(item, index) for index, item in enumerate(_items(dns, "conflicts")))
    existing_count = sum(operation.existing is not None for operation in operations)
    return DnsPlan(operations=operations, conflicts=conflicts, existing_count=existing_count)


def _dns_operation(value: Any, index: int) -> DnsPlanOperation:
    item = _mapping(value, f"dns.operations[{index}]")
    if item.get("kind") != "dns_record":
        raise ArtifactError("INVALID_DNS_PLAN_OPERATION", f"invalid DNS operation at index {index}")
    try:
        action = PlanAction(str(item["action"]))
        provider = str(item["provider"])
        zone = str(item["zone"])
        name = str(item["name"])
        record_type = str(item["type"])
    except (KeyError, ValueError) as exc:
        raise ArtifactError("INVALID_DNS_PLAN_OPERATION", f"invalid DNS operation at index {index}") from exc
    return DnsPlanOperation(
        action=action,
        provider=provider,
        zone=zone,
        name=name,
        type=record_type,
        desired=_optional_mapping(item.get("desired"), f"dns.operations[{index}].desired"),
        existing=_optional_mapping(item.get("existing"), f"dns.operations[{index}].existing"),
        reason=str(item.get("reason", "")),
        diff=_mapping(item.get("diff", {}), f"dns.operations[{index}].diff"),
    )


def _dns_conflict(value: Any, index: int) -> DnsPlanConflict:
    item = _mapping(value, f"dns.conflicts[{index}]")
    return DnsPlanConflict(
        code=str(item.get("code", "artifact_dns_conflict")),
        message=str(item.get("message", "artifact contains a DNS conflict")),
        provider=item.get("provider"),
        zone=item.get("zone"),
        owner=item.get("owner"),
        resource_id=item.get("resource_id"),
    )


def _optional_mapping(value: Any, path: str) -> dict[str, Any] | None:
    return None if value is None else _mapping(value, path)


def _operation(value: Any, index: int) -> PlanOperation:
    item = _mapping(value, f"operations[{index}]")
    try:
        action = PlanAction(str(item["action"]))
        kind = ResourceKind(str(item["kind"]))
    except (KeyError, ValueError) as exc:
        raise ArtifactError("INVALID_PLAN_OPERATION", f"invalid operation at index {index}") from exc
    if action in {PlanAction.ADOPT, PlanAction.DELETE}:
        raise ArtifactError(
            "MIGRATION_REQUIRED",
            f"{action.value} requires an NpmctlMigration artifact, not an ordinary PlanArtifact",
        )
    return PlanOperation(
        action=action,
        kind=kind,
        desired=_desired(kind, item.get("desired"), index),
        existing=_existing(kind, item.get("existing"), index),
        reason=str(item.get("reason", "")),
        diff=_mapping(item.get("diff", {}), f"operations[{index}].diff"),
    )


def _desired(kind: ResourceKind, value: Any, index: int) -> Any:
    if value is None:
        return None
    item = _mapping(value, f"operations[{index}].desired")
    path = f"artifact.operations[{index}].desired"
    if kind == ResourceKind.PROXY_HOST:
        return DesiredProxyHost.from_mapping(item, path=path)
    if kind == ResourceKind.CERTIFICATE:
        return DesiredCertificate.from_mapping(item, path=path)
    if kind == ResourceKind.ACCESS_LIST:
        return DesiredAccessList.from_mapping(item, path=path)
    api_payload = item.get("api_payload")
    if isinstance(api_payload, dict):
        item = {**api_payload, **{key: value for key, value in item.items() if key != "api_payload"}}
    return DesiredGenericResource.from_mapping(kind, item, path=path)


def _existing(kind: ResourceKind, value: Any, index: int) -> ExistingResource | None:
    if value is None:
        return None
    item = _mapping(value, f"operations[{index}].existing")
    raw = _mapping(item.get("raw"), f"operations[{index}].existing.raw")
    factories = {
        ResourceKind.PROXY_HOST: ExistingResource.from_proxy_host,
        ResourceKind.CERTIFICATE: ExistingResource.from_certificate,
        ResourceKind.ACCESS_LIST: ExistingResource.from_access_list,
    }
    factory = factories.get(kind)
    return factory(raw) if factory else ExistingResource.from_generic(kind, raw)


def _conflict(value: Any, index: int) -> PlanConflict:
    item = _mapping(value, f"conflicts[{index}]")
    raw_kind = item.get("kind")
    return PlanConflict(
        code=str(item.get("code", "artifact_conflict")),
        message=str(item.get("message", "artifact contains a conflict")),
        kind=ResourceKind(str(raw_kind)) if raw_kind else None,
        owner=item.get("owner"),
        resource_id=item.get("resource_id"),
        existing_id=item.get("existing_id"),
        domain=item.get("domain"),
    )


def _items(spec: dict[str, Any], key: str) -> list[Any]:
    value = spec.get(key, [])
    if not isinstance(value, list):
        raise ArtifactError("INVALID_PLAN_ARTIFACT", f"plan artifact spec.{key} must be an array")
    return value


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ArtifactError("INVALID_PLAN_ARTIFACT", f"{path} must be an object")
    return dict(value)
