"""Certificate client helpers."""

from wyrmctl.client.base import NpmClient
from wyrmctl.models import ResourceKind


def list_certificates(client: NpmClient):
    """List SSL certificates."""

    return client.list_resource(ResourceKind.CERTIFICATE)
