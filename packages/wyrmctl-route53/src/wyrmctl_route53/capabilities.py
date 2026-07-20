"""Route 53 provider capability declaration."""

from wyrmctl.providers import ProviderCapabilities

CAPABILITIES = ProviderCapabilities(
    provider="route53",
    capability_version=1,
    mutation_model="change-batch",
    record_types=frozenset({"A", "AAAA", "CAA", "CNAME", "MX", "SRV", "TXT"}),
    supports_idempotency=True,
)
