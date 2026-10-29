from __future__ import annotations

from wyrmctl.artifacts.live_state import scoped_live_state_fingerprint
from wyrmctl.models import (
    DesiredCertificate,
    DesiredProxyHost,
    ExistingResource,
    ExistingState,
    PlanAction,
)
from wyrmctl.planner import Plan, PlanOperation


def _proxy(
    resource_id: int,
    domains: list[str],
    *,
    owner: str | None = None,
    managed_resource_id: str | None = None,
    forward_port: int = 8080,
) -> ExistingResource:
    meta = {}
    if owner is not None:
        meta = {"managed_by": "wyrmctl", "owner": owner, "resource_id": managed_resource_id or f"proxy.{resource_id}"}
    return ExistingResource.from_proxy_host(
        {
            "id": resource_id,
            "domain_names": domains,
            "forward_host": "app",
            "forward_port": forward_port,
            "meta": meta,
        }
    )


def _certificate(resource_id: int, domains: list[str], *, owner: str | None = None) -> ExistingResource:
    meta = {}
    if owner is not None:
        meta = {"managed_by": "wyrmctl", "owner": owner, "resource_id": f"cert.{resource_id}"}
    return ExistingResource.from_certificate(
        {
            "id": resource_id,
            "nice_name": f"certificate-{resource_id}",
            "provider": "letsencrypt",
            "domain_names": domains,
            "meta": meta,
        }
    )


def _access_list(resource_id: int, *, owner: str | None = None, name: str = "private") -> ExistingResource:
    meta = {}
    if owner is not None:
        meta = {"managed_by": "wyrmctl", "owner": owner, "resource_id": f"acl.{resource_id}"}
    return ExistingResource.from_access_list({"id": resource_id, "name": name, "meta": meta})


def _proxy_plan(*, certificate_id: int | None = None, access_list_id: int | None = None) -> Plan:
    desired = DesiredProxyHost.from_mapping(
        {
            "domain_names": ["app.example.com", "www.example.com"],
            "forward_host": "app",
            "forward_port": 8080,
            "certificate_id": certificate_id,
            "access_list_id": access_list_id,
            "meta": {"managed_by": "wyrmctl", "owner": "owner-a", "resource_id": "proxy.app"},
        },
        path="proxy",
    )
    return Plan((PlanOperation(PlanAction.CREATE, desired.kind, desired=desired),), (), 0)


def test_unrelated_owner_mutation_does_not_invalidate_plan() -> None:
    plan = _proxy_plan()
    before = ExistingState(proxy_hosts=(_proxy(1, ["other.example.net"], owner="owner-b"),))
    after = ExistingState(proxy_hosts=(_proxy(1, ["other.example.net"], owner="owner-b", forward_port=9090),))

    assert scoped_live_state_fingerprint(plan, before) == scoped_live_state_fingerprint(plan, after)


def test_same_owner_mutation_invalidates_plan_even_for_another_resource() -> None:
    plan = _proxy_plan()
    before = ExistingState(proxy_hosts=(_proxy(1, ["other.example.net"], owner="owner-a"),))
    after = ExistingState(proxy_hosts=(_proxy(1, ["other.example.net"], owner="owner-a", forward_port=9090),))

    assert scoped_live_state_fingerprint(plan, before) != scoped_live_state_fingerprint(plan, after)


def test_foreign_natural_key_collision_invalidates_plan() -> None:
    plan = _proxy_plan()

    assert scoped_live_state_fingerprint(plan, ExistingState()) != scoped_live_state_fingerprint(
        plan,
        ExistingState(proxy_hosts=(_proxy(1, ["app.example.com", "www.example.com"], owner="owner-b"),)),
    )


def test_foreign_overlapping_proxy_domain_invalidates_plan() -> None:
    plan = _proxy_plan()

    assert scoped_live_state_fingerprint(plan, ExistingState()) != scoped_live_state_fingerprint(
        plan,
        ExistingState(proxy_hosts=(_proxy(1, ["app.example.com", "extra.example.com"], owner="owner-b"),)),
    )


def test_reusable_certificate_domain_change_invalidates_plan() -> None:
    desired = DesiredCertificate.from_mapping(
        {
            "name": "app-certificate",
            "domain_names": ["app.example.com"],
            "meta": {"managed_by": "wyrmctl", "owner": "owner-a", "resource_id": "cert.app"},
        },
        path="certificate",
    )
    plan = Plan((PlanOperation(PlanAction.CREATE, desired.kind, desired=desired),), (), 0)

    assert scoped_live_state_fingerprint(plan, ExistingState()) != scoped_live_state_fingerprint(
        plan,
        ExistingState(certificates=(_certificate(2, ["app.example.com"], owner="owner-b"),)),
    )


def test_explicit_certificate_id_change_invalidates_plan() -> None:
    plan = _proxy_plan(certificate_id=7)
    before = ExistingState(certificates=(_certificate(7, ["old.example.net"], owner="owner-b"),))
    after = ExistingState(certificates=(_certificate(7, ["changed.example.net"], owner="owner-b"),))

    assert scoped_live_state_fingerprint(plan, before) != scoped_live_state_fingerprint(plan, after)


def test_explicit_access_list_id_change_invalidates_plan() -> None:
    plan = _proxy_plan(access_list_id=8)
    before = ExistingState(access_lists=(_access_list(8, owner="owner-b"),))
    after = ExistingState(access_lists=(_access_list(8, owner="owner-b", name="changed"),))

    assert scoped_live_state_fingerprint(plan, before) != scoped_live_state_fingerprint(plan, after)


def test_fingerprint_is_deterministic_across_live_resource_order() -> None:
    plan = _proxy_plan()
    first = _proxy(1, ["first.example.net"], owner="owner-a")
    second = _proxy(2, ["second.example.net"], owner="owner-a")

    assert scoped_live_state_fingerprint(
        plan, ExistingState(proxy_hosts=(first, second))
    ) == scoped_live_state_fingerprint(plan, ExistingState(proxy_hosts=(second, first)))
