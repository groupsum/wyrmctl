"""Plan-scoped optimistic-concurrency fingerprints for NPM live state."""

from __future__ import annotations

from typing import Any

from wyrmctl.contracts import canonical_json, semantic_digest
from wyrmctl.models import DesiredProxyHost, ExistingResource, ExistingState, ResourceKind
from wyrmctl.planner import Plan

_SCOPE_VERSION = 1


def scoped_live_state_fingerprint(plan: Plan, existing: ExistingState) -> str:
    """Fingerprint live resources that can affect the reviewed plan.

    The scope is deliberately conservative: it includes every resource owned by
    an owner represented in the plan, plus foreign or unmanaged resources that
    collide with a desired natural key, proxy domain, reusable certificate
    domain set, or explicitly referenced certificate/access-list id.
    """

    owners = sorted({owner for operation in plan.operations if (owner := operation.owner) is not None})
    targets = tuple(_target(operation.desired or operation.existing) for operation in plan.operations)
    target_keys = {(target["kind"], _key_digest(target["natural_key"])) for target in targets}
    proxy_domains = {
        domain
        for target in targets
        if target["kind"] == ResourceKind.PROXY_HOST.value
        for domain in target["domain_names"]
    }
    certificate_domain_sets = {
        tuple(target["domain_names"]) for target in targets if target["kind"] == ResourceKind.CERTIFICATE.value
    }
    referenced_ids = {
        (kind.value, resource_id)
        for operation in plan.operations
        if isinstance(operation.desired, DesiredProxyHost)
        for kind, resource_id in (
            (ResourceKind.CERTIFICATE, operation.desired.certificate_id),
            (ResourceKind.ACCESS_LIST, operation.desired.access_list_id),
        )
        if resource_id is not None
    }

    selected = [
        resource.to_dict()
        for resource in existing.resources()
        if _resource_is_in_scope(
            resource,
            owners=set(owners),
            target_keys=target_keys,
            proxy_domains=proxy_domains,
            certificate_domain_sets=certificate_domain_sets,
            referenced_ids=referenced_ids,
        )
    ]
    selected.sort(key=lambda item: (str(item["kind"]), str(item["id"]), canonical_json(item)))
    target_payloads = sorted(targets, key=canonical_json)
    return semantic_digest(
        {
            "scopeVersion": _SCOPE_VERSION,
            "owners": owners,
            "targets": target_payloads,
            "resources": selected,
        }
    )


def _target(resource: Any) -> dict[str, Any]:
    return {
        "kind": resource.kind.value,
        "natural_key": _json_key(resource.natural_key),
        "domain_names": sorted(resource.domain_names),
    }


def _resource_is_in_scope(
    resource: ExistingResource,
    *,
    owners: set[str],
    target_keys: set[tuple[str, str]],
    proxy_domains: set[str],
    certificate_domain_sets: set[tuple[str, ...]],
    referenced_ids: set[tuple[str, int]],
) -> bool:
    if resource.identity is not None and resource.identity.owner in owners:
        return True
    if (resource.kind.value, _key_digest(resource.natural_key)) in target_keys:
        return True
    if resource.kind == ResourceKind.PROXY_HOST and proxy_domains.intersection(resource.domain_names):
        return True
    if resource.kind == ResourceKind.CERTIFICATE and tuple(sorted(resource.domain_names)) in certificate_domain_sets:
        return True
    return (resource.kind.value, resource.id) in referenced_ids


def _key_digest(value: Any) -> str:
    return semantic_digest(_json_key(value))


def _json_key(value: Any) -> Any:
    return list(value) if isinstance(value, tuple) else value
