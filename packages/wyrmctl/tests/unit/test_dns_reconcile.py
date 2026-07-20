from __future__ import annotations

import pytest

from wyrmctl.dns import DnsPlan, DnsPlanConflict, DnsPlanOperation, apply_dns_plan, compute_dns_plan
from wyrmctl.models import DesiredDnsRecord, PlanAction


def _record(resource_id: str, *, name: str = "@", value: str = "192.0.2.10", owner: str = "site") -> DesiredDnsRecord:
    return DesiredDnsRecord.from_mapping(
        {
            "provider": "namecheap",
            "zone": "example.com",
            "type": "A",
            "name": name,
            "value": value,
            "ttl": 300,
            "meta": {"managed_by": "wyrmctl", "owner": owner, "resource_id": resource_id},
        },
        path="dns",
    )


class ReadOnlyProvider:
    name = "namecheap"

    def __init__(self, records=()) -> None:
        self._records = tuple(records)

    def zones(self):
        return ("example.com",)

    def records(self, zone: str):
        assert zone == "example.com"
        return self._records


class WritableProvider(ReadOnlyProvider):
    def __init__(self, records=()) -> None:
        super().__init__(records)
        self.applied: list[tuple[str, tuple[dict, ...]]] = []

    def apply_records(self, zone: str, records: tuple[dict, ...]) -> None:
        self.applied.append((zone, records))


def test_empty_dns_plan_has_no_mutations() -> None:
    plan = compute_dns_plan((), {})

    assert plan.ok
    assert not plan.has_mutations()
    assert plan.by_action(PlanAction.CREATE) == ()
    assert plan.to_dict()["summary"]["noop"] == 0


def test_dns_plan_conflicts_for_missing_provider() -> None:
    plan = compute_dns_plan((_record("dns.apex"),), {})

    assert not plan.ok
    assert plan.conflicts[0].to_dict() == {
        "code": "missing_dns_provider",
        "message": "DNS provider 'namecheap' is not installed",
        "provider": "namecheap",
        "zone": "example.com",
        "owner": "site",
        "resource_id": "dns.apex",
    }


def test_dns_plan_create_update_noop_and_readonly_conflict() -> None:
    provider = ReadOnlyProvider(
        (
            {"provider": "namecheap", "zone": "example.com", "name": "www", "type": "A", "value": "192.0.2.9"},
            {
                "provider": "namecheap",
                "zone": "example.com",
                "name": "api",
                "type": "A",
                "value": "192.0.2.10",
                "ttl": 300,
            },
        )
    )

    plan = compute_dns_plan(
        (
            _record("dns.apex"),
            _record("dns.www", name="www", value="192.0.2.10"),
            _record("dns.api", name="api", value="192.0.2.10"),
        ),
        {"namecheap": provider},
    )

    assert [op.action for op in plan.operations] == [PlanAction.CREATE, PlanAction.UPDATE, PlanAction.NOOP]
    assert plan.operations[0].resource_id == "dns.apex"
    assert plan.operations[1].diff == {
        "ttl": {"actual": None, "desired": 300},
        "value": {"actual": "192.0.2.9", "desired": "192.0.2.10"},
    }
    assert plan.conflicts[0].code == "read_only_dns_provider"


def test_dns_plan_prunes_only_owned_records_for_selected_owner() -> None:
    provider = WritableProvider(
        (
            {
                "provider": "namecheap",
                "zone": "example.com",
                "name": "@",
                "type": "A",
                "value": "192.0.2.10",
                "ttl": 300,
                "priority": 10,
                "meta": {"managed_by": "wyrmctl", "owner": "site", "resource_id": "dns.apex"},
            },
            {
                "provider": "namecheap",
                "zone": "example.com",
                "name": "old",
                "type": "A",
                "value": "192.0.2.9",
                "meta": {"managed_by": "wyrmctl", "owner": "site", "resource_id": "dns.old"},
            },
            {
                "provider": "namecheap",
                "zone": "example.com",
                "name": "foreign",
                "type": "A",
                "value": "192.0.2.8",
                "meta": {"managed_by": "wyrmctl", "owner": "other", "resource_id": "dns.foreign"},
            },
            {"provider": "namecheap", "zone": "example.com", "name": "manual", "type": "A", "value": "192.0.2.7"},
            {
                "provider": "namecheap",
                "zone": "example.com",
                "name": "bad-meta",
                "type": "A",
                "value": "192.0.2.6",
                "meta": {"managed_by": "manual", "owner": "site", "resource_id": "dns.bad"},
            },
        )
    )

    plan = compute_dns_plan((_record("dns.apex"),), {"namecheap": provider}, owner="site", prune_owned=True)

    assert [op.action for op in plan.operations] == [PlanAction.UPDATE, PlanAction.DELETE]
    assert plan.operations[1].resource_id == "dns.old"
    assert plan.operations[1].to_dict()["name"] == "old"


def test_dns_apply_preserves_unmanaged_records_and_applies_once_per_zone() -> None:
    provider = WritableProvider(
        (
            {"provider": "namecheap", "zone": "example.com", "name": "www", "type": "A", "value": "192.0.2.9"},
            {"provider": "namecheap", "zone": "example.com", "name": "manual", "type": "A", "value": "192.0.2.8"},
            {
                "provider": "namecheap",
                "zone": "example.com",
                "name": "old",
                "type": "A",
                "value": "192.0.2.7",
                "meta": {"managed_by": "wyrmctl", "owner": "site", "resource_id": "dns.old"},
            },
        )
    )
    plan = compute_dns_plan(
        (_record("dns.www", name="www", value="192.0.2.10"),),
        {"namecheap": provider},
        owner="site",
        prune_owned=True,
    )

    result = apply_dns_plan(plan, {"namecheap": provider})

    assert result.applied
    assert [item["action"] for item in result.mutations] == ["update", "delete"]
    assert len(provider.applied) == 1
    applied = {record["name"]: record for record in provider.applied[0][1]}
    assert applied["www"]["value"] == "192.0.2.10"
    assert applied["manual"]["value"] == "192.0.2.8"
    assert "old" not in applied


def test_dns_apply_rejects_conflicts_and_readonly_provider() -> None:
    with pytest.raises(ValueError, match="refusing to apply DNS plan"):
        apply_dns_plan(DnsPlan(conflicts=(DnsPlanConflict("blocked", "blocked"),)), {})

    operation = DnsPlanOperation(
        PlanAction.CREATE, "namecheap", "example.com", "@", "A", desired=_record("dns.apex").to_payload()
    )
    with pytest.raises(ValueError, match="does not support apply_records"):
        apply_dns_plan(DnsPlan(operations=(operation,)), {"namecheap": ReadOnlyProvider()})


def test_dns_apply_ignores_noops_and_delete_without_existing() -> None:
    provider = WritableProvider()
    result = apply_dns_plan(
        DnsPlan(
            operations=(
                DnsPlanOperation(PlanAction.NOOP, "namecheap", "example.com", "@", "A"),
                DnsPlanOperation(PlanAction.DELETE, "namecheap", "example.com", "missing", "A"),
            )
        ),
        {"namecheap": provider},
    )

    assert result.mutations == [
        {
            "action": "delete",
            "kind": "dns_record",
            "provider": "namecheap",
            "zone": "example.com",
            "name": "missing",
            "type": "A",
            "owner": None,
            "resource_id": None,
            "existing": None,
            "reason": "",
            "diff": {},
        }
    ]
    assert provider.applied == [("example.com", ())]
