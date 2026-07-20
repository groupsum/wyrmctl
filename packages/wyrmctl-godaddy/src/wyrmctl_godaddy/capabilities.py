"""GoDaddy provider capability declaration."""

from wyrmctl.providers import ProviderCapabilities

CAPABILITIES = ProviderCapabilities(
    provider="godaddy",
    capability_version=1,
    mutation_model="record-set-replacement",
    record_types=frozenset({"A", "AAAA", "CAA", "CNAME", "MX", "SRV", "TXT"}),
)
