"""NPM REST endpoint contracts used by wyrmctl."""

from __future__ import annotations

from dataclasses import dataclass

from wyrmctl.models import ResourceId, ResourceKind


@dataclass(frozen=True, slots=True)
class ResourceContract:
    """REST path contract for a managed resource kind."""

    kind: ResourceKind
    collection_path: str

    def item_path(self, resource_id: ResourceId) -> str:
        return f"{self.collection_path}/{resource_id}"


CONTRACTS: dict[ResourceKind, ResourceContract] = {
    ResourceKind.PROXY_HOST: ResourceContract(ResourceKind.PROXY_HOST, "/nginx/proxy-hosts"),
    ResourceKind.CERTIFICATE: ResourceContract(ResourceKind.CERTIFICATE, "/nginx/certificates"),
    ResourceKind.ACCESS_LIST: ResourceContract(ResourceKind.ACCESS_LIST, "/nginx/access-lists"),
    ResourceKind.REDIRECTION_HOST: ResourceContract(ResourceKind.REDIRECTION_HOST, "/nginx/redirection-hosts"),
    ResourceKind.DEAD_HOST: ResourceContract(ResourceKind.DEAD_HOST, "/nginx/dead-hosts"),
    ResourceKind.STREAM: ResourceContract(ResourceKind.STREAM, "/nginx/streams"),
    ResourceKind.USER: ResourceContract(ResourceKind.USER, "/users"),
    ResourceKind.SETTING: ResourceContract(ResourceKind.SETTING, "/settings"),
}
