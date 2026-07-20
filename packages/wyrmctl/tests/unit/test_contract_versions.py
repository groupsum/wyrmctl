from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path

import pytest

from wyrmctl.contracts import canonical_json, canonicalize, check_document, semantic_digest
from wyrmctl.contracts.registry import ContractRegistry
from wyrmctl.contracts.types import ContractSupport, DocumentEnvelope
from wyrmctl.dns import DnsPlan, DnsPlanOperation, apply_dns_plan
from wyrmctl.errors import ContractCompatibilityError
from wyrmctl.output import command_result
from wyrmctl.plugins import PluginRegistry, dns_capabilities
from wyrmctl.providers import DnsMutationContext, ProviderCapabilities, ProviderMutationResult, dns_records_digest
from wyrmctl.models import PlanAction
from wyrmctl.schema import Capabilities


class Choice(Enum):
    A = "a"


@dataclass
class Value:
    item: str


def test_canonical_values_are_stable() -> None:
    value = {
        "dataclass": Value("x"),
        "enum": Choice.A,
        "mapping": {2: "b", 1: "a"},
        "sequence": (1, 2),
        "set": {"b", "a"},
        "aware": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "naive": datetime(2025, 1, 1),
        "date": date(2025, 1, 1),
        "path": Path("a/b"),
        "scalars": [None, "x", 1, 1.5, True],
    }
    normalized = canonicalize(value)
    assert normalized["set"] == ["a", "b"]
    assert normalized["naive"].endswith("Z")
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert semantic_digest(value) == semantic_digest(value)
    with pytest.raises(TypeError, match="unsupported canonical value"):
        canonicalize(object())


def test_contract_registry_success_and_failures() -> None:
    registry = ContractRegistry()

    def parser(value):
        return value["x"]

    support = ContractSupport("Thing", 2, frozenset({1, 2}), frozenset({2}), frozenset({1}), {2: parser})
    registry.register(support)
    assert registry.support("Thing") is support
    assert registry.require_readable("Thing", 1) == ["Thing schema 1 is deprecated"]
    assert registry.parser("Thing", 2)({"x": 3}) == 3
    assert registry.matrix()["Thing"]["current"] == 2
    registry.require_writable("Thing", 2)
    with pytest.raises(ContractCompatibilityError, match="unknown contract"):
        registry.support("Missing")
    with pytest.raises(ContractCompatibilityError, match="future"):
        registry.require_readable("Thing", 3)
    with pytest.raises(ContractCompatibilityError, match="deprecated"):
        registry.require_readable("Thing", 1, strict=True)
    with pytest.raises(ContractCompatibilityError, match="not writable"):
        registry.require_writable("Thing", 1)
    with pytest.raises(ContractCompatibilityError, match="no parser"):
        registry.parser("Thing", 1)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(support)
    for bad in (
        ContractSupport("", 1, frozenset({1}), frozenset({1})),
        ContractSupport("Bad", 0, frozenset({1}), frozenset({1})),
        ContractSupport("Bad", 2, frozenset({1}), frozenset({2})),
    ):
        with pytest.raises(ValueError):
            ContractRegistry().register(bad)


def test_document_envelope_and_compatibility() -> None:
    raw = {"apiVersion": "wyrmctl.com/v1", "kind": "Thing", "schemaVersion": 1, "metadata": {}, "spec": {}}
    envelope = DocumentEnvelope.from_mapping(raw)
    assert envelope.to_dict() == raw
    with pytest.raises(ValueError, match="objects"):
        DocumentEnvelope.from_mapping(raw | {"metadata": []})
    registry = ContractRegistry()
    registry.register(ContractSupport("Thing", 1, frozenset({1}), frozenset({1})))
    assert check_document(raw, registry) == []
    for document, message in (
        (raw | {"apiVersion": "bad"}, "apiVersion"),
        (raw | {"kind": ""}, "kind"),
        (raw | {"schemaVersion": True}, "schemaVersion"),
        (raw | {"schemaVersion": 0}, "schemaVersion"),
    ):
        with pytest.raises(ContractCompatibilityError, match=message):
            check_document(document, registry)


def test_provider_and_command_contracts() -> None:
    capabilities = ProviderCapabilities("dns", 1, "record-level", frozenset({"A", "TXT"}))
    assert capabilities.to_dict()["recordTypes"] == ["A", "TXT"]
    capabilities.require_record_type("a")
    with pytest.raises(Exception, match="does not support MX"):
        capabilities.require_record_type("MX")
    context = DnsMutationContext("op", "key", "before")
    assert context.operation_id == "op"
    result = ProviderMutationResult("dns", "op", None, "digest", True)
    assert result.to_dict()["verified"] is True
    assert dns_records_digest(({"id": 1, "name": "@", "type": "A", "value": "1.2.3.4"},)) == dns_records_digest(
        ({"name": "@", "type": "A", "value": "1.2.3.4"},)
    )
    payload = command_result(ok=True, code="OK", data={"x": 1}, mutated=True, retryable=True)
    assert payload["kind"] == "CommandResult" and payload["mutated"] is True
    assert Capabilities.full_for_tests().api_profile.startswith("npm:test:sha256:")


def test_plugin_contract_and_migration_extensions() -> None:
    class EntryPoint:
        def __init__(self, name, group, value):
            self.name, self.group, self.value = name, group, value

        def load(self):
            return self.value

    class EntryPoints(list):
        def select(self, *, group):
            return EntryPoints(item for item in self if item.group == group)

    class LegacyDns:
        name = "legacy"

        def zones(self):
            return ()

        def records(self, _zone):
            return ()

    registry = PluginRegistry.discover(
        entry_points=EntryPoints(
            [
                EntryPoint("contract", "wyrmctl.contracts", object()),
                EntryPoint("migration", "wyrmctl.migrations", object()),
                EntryPoint("legacy", "wyrmctl.dns_providers", LegacyDns()),
            ]
        )
    )
    assert registry.to_dict()["contract_plugins"] == ["contract"]
    assert registry.to_dict()["migration_plugins"] == ["migration"]
    assert registry.capability_matrix()["legacy"]["supportsReadback"] is False
    assert dns_capabilities(registry.dns_providers["legacy"]).mutation_model == "legacy-unknown"

    class BadDns(LegacyDns):
        def capabilities(self):
            return {}

    with pytest.raises(ValueError, match="invalid capabilities"):
        dns_capabilities(BadDns())

    target = {}
    from wyrmctl.plugins import _load_extension_group

    entries = EntryPoints([EntryPoint("same", "wyrmctl.contracts", 1), EntryPoint("same", "wyrmctl.contracts", 2)])
    with pytest.raises(ValueError, match="duplicate"):
        _load_extension_group(target, entries, "wyrmctl.contracts")


def test_modern_dns_provider_mutation_contract() -> None:
    operation = DnsPlanOperation(
        PlanAction.CREATE,
        "modern",
        "example.com",
        "@",
        "A",
        desired={"provider": "modern", "zone": "example.com", "name": "@", "type": "A", "value": "1.2.3.4"},
    )

    class Modern:
        name = "modern"

        def __init__(self, result=True):
            self.result = result

        def records(self, _zone):
            return ()

        def capabilities(self):
            return ProviderCapabilities("modern", 1, "record-level", frozenset({"A"}))

        def apply_records(self, _zone, _records, context):
            if self.result == "invalid":
                return None
            return ProviderMutationResult("modern", context.operation_id, "request", "digest", self.result)

    result = apply_dns_plan(DnsPlan((operation,)), {"modern": Modern()})
    assert result.provider_results[0]["requestId"] == "request"
    assert result.to_dict()["provider_results"]
    for value in (False, "invalid"):
        with pytest.raises(ValueError, match="did not verify"):
            apply_dns_plan(DnsPlan((operation,)), {"modern": Modern(value)})
    unsupported = DnsPlanOperation(
        PlanAction.CREATE,
        "modern",
        "example.com",
        "@",
        "MX",
        desired={"provider": "modern", "zone": "example.com", "name": "@", "type": "MX", "value": "mail"},
    )
    with pytest.raises(Exception, match="does not support MX"):
        apply_dns_plan(DnsPlan((unsupported,)), {"modern": Modern()})
