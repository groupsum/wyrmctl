"""Cloudflare provider capability declaration."""

from wyrmctl.providers import ProviderCapabilities

CAPABILITIES = ProviderCapabilities(
    provider="cloudflare",
    capability_version=1,
    mutation_model="record-level",
    record_types=frozenset({"A", "AAAA", "CAA", "CNAME", "MX", "SRV", "TXT"}),
    supports_idempotency=True,
)
