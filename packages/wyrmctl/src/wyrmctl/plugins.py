"""Extension and plugin contracts for wyrmctl."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from typing import Any, Protocol

from wyrmctl.models import ResourceKind
from wyrmctl.providers import DnsMutationContext, ProviderCapabilities, ProviderMutationResult
from wyrmctl.profile import current_profile


class ResourceProvider(Protocol):
    """Provider contract for custom resource kinds."""

    kind: ResourceKind

    def identity(self, payload: dict[str, Any]) -> tuple[str, str]:
        """Return owner and resource id for a payload."""

    def natural_key(self, payload: dict[str, Any]) -> Any:
        """Return the resource natural key."""

    def desired_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return the provider-specific API payload."""


class CertificateProvider(Protocol):
    """Provider contract for external certificate resolution."""

    name: str

    def resolve(self, reference: str) -> dict[str, Any]:
        """Resolve a certificate reference into an NPM-compatible payload."""


class DnsProvider(Protocol):
    """Provider contract for DNS zone, record inspection, and reconciliation."""

    name: str

    def capabilities(self) -> ProviderCapabilities:
        """Return the provider's versioned mutation contract."""

    def zones(self) -> tuple[str, ...]:
        """Return zones available to the configured provider account."""

    def records(self, zone: str) -> tuple[dict[str, Any], ...]:
        """Return DNS records for one zone."""

    def apply_records(
        self,
        zone: str,
        records: tuple[dict[str, Any], ...],
        context: DnsMutationContext | None = None,
    ) -> ProviderMutationResult:
        """Replace provider records for one zone with the supplied reconciled set."""


@dataclass(slots=True)
class PluginRegistry:
    """In-memory plugin registry used by tests and embedded consumers."""

    resource_providers: dict[str, ResourceProvider]
    certificate_providers: dict[str, CertificateProvider]
    dns_providers: dict[str, DnsProvider]
    contract_plugins: dict[str, Any]
    migration_plugins: dict[str, Any]

    def __init__(self) -> None:
        self.resource_providers = {}
        self.certificate_providers = {}
        self.dns_providers = {}
        self.contract_plugins: dict[str, Any] = {}
        self.migration_plugins: dict[str, Any] = {}

    def register_resource_provider(self, name: str, provider: ResourceProvider) -> None:
        self.resource_providers[name] = provider

    def register_certificate_provider(self, name: str, provider: CertificateProvider) -> None:
        self.certificate_providers[name] = provider

    def register_dns_provider(self, name: str, provider: DnsProvider) -> None:
        self.dns_providers[name] = provider

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "resource_providers": sorted(self.resource_providers),
            "certificate_providers": sorted(self.certificate_providers),
            "dns_providers": sorted(self.dns_providers),
            "contract_plugins": sorted(self.contract_plugins),
            "migration_plugins": sorted(self.migration_plugins),
        }

    def capability_matrix(self) -> dict[str, dict[str, Any]]:
        return {name: dns_capabilities(provider).to_dict() for name, provider in sorted(self.dns_providers.items())}

    @classmethod
    def discover(cls, *, entry_points: metadata.EntryPoints | None = None) -> PluginRegistry:
        """Load providers exposed through wyrmctl entry point groups."""

        registry = cls()
        groups = entry_points if entry_points is not None else metadata.entry_points()
        prefix = current_profile().entry_point_group.rsplit(".", 1)[0]
        _load_group(registry, groups, f"{prefix}.resource_providers", "resource")
        _load_group(registry, groups, f"{prefix}.certificate_providers", "certificate")
        _load_group(registry, groups, current_profile().entry_point_group, "dns")
        _load_extension_group(registry.contract_plugins, groups, f"{prefix}.contracts")
        _load_extension_group(registry.migration_plugins, groups, f"{prefix}.migrations")
        return registry


def _load_group(registry: PluginRegistry, groups: metadata.EntryPoints, group: str, provider_type: str) -> None:
    for entry_point in groups.select(group=group):
        provider = entry_point.load()
        if isinstance(provider, type):
            provider = provider()
        if provider_type == "resource":
            _validate_resource_provider(entry_point.name, provider)
            registry.register_resource_provider(entry_point.name, provider)
        elif provider_type == "certificate":
            _validate_certificate_provider(entry_point.name, provider)
            registry.register_certificate_provider(entry_point.name, provider)
        else:
            _validate_dns_provider(entry_point.name, provider)
            registry.register_dns_provider(entry_point.name, provider)


def _validate_resource_provider(name: str, provider: Any) -> None:
    for attr in ("kind", "identity", "natural_key", "desired_payload"):
        if not hasattr(provider, attr):
            raise ValueError(f"resource provider {name!r} missing {attr}")
    kind = getattr(provider, "kind")
    if not isinstance(kind, str) and not hasattr(kind, "value"):
        raise ValueError(f"resource provider {name!r} has invalid kind")


def _validate_certificate_provider(name: str, provider: Any) -> None:
    for attr in ("name", "resolve"):
        if not hasattr(provider, attr):
            raise ValueError(f"certificate provider {name!r} missing {attr}")


def _validate_dns_provider(name: str, provider: Any) -> None:
    for attr in ("name", "zones", "records"):
        if not hasattr(provider, attr):
            raise ValueError(f"dns provider {name!r} missing {attr}")


def dns_capabilities(provider: Any) -> ProviderCapabilities:
    """Return declared capabilities or a conservative legacy contract."""

    if hasattr(provider, "capabilities"):
        result = provider.capabilities()
        if not isinstance(result, ProviderCapabilities):
            raise ValueError(f"dns provider {provider.name!r} returned invalid capabilities")
        return result
    return ProviderCapabilities(
        provider=str(provider.name),
        capability_version=1,
        mutation_model="legacy-unknown",
        record_types=frozenset(),
        supports_readback=False,
        supports_forward_repair=False,
    )


def _load_extension_group(target: dict[str, Any], groups: metadata.EntryPoints, group: str) -> None:
    for entry_point in groups.select(group=group):
        if entry_point.name in target:
            raise ValueError(f"duplicate plugin registration in {group}: {entry_point.name}")
        target[entry_point.name] = entry_point.load()
