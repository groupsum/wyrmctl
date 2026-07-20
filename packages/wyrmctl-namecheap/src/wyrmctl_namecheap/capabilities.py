"""Namecheap provider capability declaration."""

from wyrmctl.providers import ProviderCapabilities

CAPABILITIES = ProviderCapabilities(
    provider="namecheap",
    capability_version=1,
    mutation_model="complete-zone-replacement",
    record_types=frozenset({"A", "AAAA", "CAA", "CNAME", "MX", "SRV", "TXT"}),
    requires_zone_lease=True,
    replan_inside_lease=True,
    supports_idempotency=True,
)
