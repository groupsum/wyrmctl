from __future__ import annotations

import pytest

import real_npm_helpers as helpers
from wyrmctl.errors import ApiError
from wyrmctl.models import ExistingResource, ResourceKind


def _proxy(resource_id: str, item_id: int = 1) -> ExistingResource:
    return ExistingResource.from_proxy_host(
        {
            "id": item_id,
            "domain_names": [f"{resource_id}.example.invalid"],
            "forward_scheme": "http",
            "forward_host": "127.0.0.1",
            "forward_port": 8080,
            "meta": {"managed_by": "wyrmctl", "owner": "tests", "resource_id": resource_id},
        }
    )


def _access_list(name: str, item_id: int = 2) -> ExistingResource:
    return ExistingResource.from_access_list(
        {
            "id": item_id,
            "name": name,
            "satisfy_any": 0,
            "pass_auth": 0,
            "items": [],
            "clients": [],
            "meta": {"managed_by": "wyrmctl", "owner": "tests", "resource_id": f"{name}.acl"},
        }
    )


class _DeleteRetryClient:
    def __init__(self) -> None:
        self.items = [_proxy("retry.proxy", item_id=7)]
        self.delete_calls = 0

    def list_resource(self, _: ResourceKind) -> tuple[ExistingResource, ...]:
        return tuple(self.items)

    def delete_resource(self, _: ResourceKind, resource_id: int) -> bool:
        self.delete_calls += 1
        if self.delete_calls == 1:
            raise ApiError("transient delete failure")
        self.items = [item for item in self.items if item.id != resource_id]
        return True


def test_best_effort_delete_retries_after_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _DeleteRetryClient()
    monkeypatch.setattr(helpers.time, "sleep", lambda _: None)

    helpers.best_effort_delete(client, ResourceKind.PROXY_HOST, 7)

    assert client.delete_calls == 2
    assert client.list_resource(ResourceKind.PROXY_HOST) == ()


class _StickyListClient:
    def __init__(self) -> None:
        self.items = (_access_list("sticky-acl"),)

    def list_resource(self, _: ResourceKind) -> tuple[ExistingResource, ...]:
        return self.items


def test_wait_until_absent_includes_resource_details_on_timeout() -> None:
    client = _StickyListClient()

    with pytest.raises(
        AssertionError, match=r"access_list resources still present.*name=sticky-acl.*resource_id=sticky-acl.acl"
    ):
        helpers.wait_until_absent(client, ResourceKind.ACCESS_LIST, lambda _: True, timeout_s=0, interval_s=0)
