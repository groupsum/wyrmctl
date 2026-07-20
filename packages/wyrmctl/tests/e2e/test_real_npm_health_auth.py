from __future__ import annotations

import os

import pytest

from wyrmctl.client import NpmClient

pytestmark = pytest.mark.npm


def _client() -> NpmClient:
    return NpmClient(
        base_url=os.environ["NPM_BASE_URL"],
        identity=os.environ["NPM_IDENTITY"],
        secret=os.environ["NPM_SECRET"],
        timeout_s=20,
    )


@pytest.mark.skipif(os.environ.get("NPMCTL_REAL_NPM") != "1", reason="real NPM E2E is opt-in")
def test_real_npm_health_auth_and_schema() -> None:
    client = _client()
    assert client.health()["status"] == "OK"
    caps = client.capabilities()
    assert caps.proxy_hosts.list
    assert caps.proxy_hosts.create
