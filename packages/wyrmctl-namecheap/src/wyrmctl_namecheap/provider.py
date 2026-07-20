"""wyrmctl DNS provider implementation for Namecheap."""

from __future__ import annotations

from wyrmctl.providers import DnsMutationContext, ProviderCapabilities, ProviderMutationResult, dns_records_digest

from wyrmctl_namecheap.capabilities import CAPABILITIES
from wyrmctl_namecheap.client import NamecheapClient
from wyrmctl_namecheap.config import NamecheapConfig


class NamecheapDnsProvider:
    """DNS provider backed by the Namecheap XML API."""

    name = "namecheap"

    def __init__(self, client: NamecheapClient | None = None) -> None:
        self._client = client

    @property
    def client(self) -> NamecheapClient:
        if self._client is None:
            self._client = NamecheapClient(NamecheapConfig.from_env())
        return self._client

    def zones(self) -> tuple[str, ...]:
        return self.client.zones()

    def records(self, zone: str) -> tuple[dict[str, object], ...]:
        return tuple(record.to_dict() for record in self.client.records(zone))

    def capabilities(self) -> ProviderCapabilities:
        return CAPABILITIES

    def apply_records(
        self,
        zone: str,
        records: tuple[dict[str, object], ...],
        context: DnsMutationContext | None = None,
    ) -> ProviderMutationResult:
        self.client.set_hosts(zone, records)
        observed = self.records(zone)
        return ProviderMutationResult(
            self.name,
            context.operation_id if context else f"dns:{zone}",
            None,
            dns_records_digest(observed),
            dns_records_digest(observed) == dns_records_digest(records),
        )
