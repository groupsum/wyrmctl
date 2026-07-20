"""Built-in wyrmctl contract matrix."""

from wyrmctl.contracts.registry import ContractRegistry
from wyrmctl.contracts.types import ContractSupport


def build_builtin_registry() -> ContractRegistry:
    registry = ContractRegistry()
    rows = {
        "DesiredState": (3, {1, 2, 3}, {3}, {1}),
        "NpmctlRepository": (1, {1}, {1}, set()),
        "NpmctlLock": (1, {1}, {1}, set()),
        "PlanArtifact": (1, {1}, {1}, set()),
        "LiveStateSnapshot": (1, {1}, {1}, set()),
        "NpmctlMigration": (1, {1}, {1}, set()),
        "ApplyReport": (1, {1}, {1}, set()),
        "ProviderCapabilities": (1, {1}, {1}, set()),
        "CommandResult": (1, {1}, {1}, set()),
    }
    for kind, (current, readable, writable, deprecated) in rows.items():
        registry.register(
            ContractSupport(
                kind=kind,
                current=current,
                readable=frozenset(readable),
                writable=frozenset(writable),
                deprecated=frozenset(deprecated),
            )
        )
    return registry


BUILTIN_CONTRACTS = build_builtin_registry()
