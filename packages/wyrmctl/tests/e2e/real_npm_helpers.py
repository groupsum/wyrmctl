from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import pytest
import yaml

from wyrmctl.client import NpmClient
from wyrmctl.errors import ApiError
from wyrmctl.models import ExistingResource, ResourceKind


def require_real_npm() -> None:
    if os.environ.get("NPMCTL_REAL_NPM") != "1":
        pytest.skip("real NPM E2E is opt-in")


def client() -> NpmClient:
    return NpmClient(
        base_url=os.environ["NPM_BASE_URL"],
        identity=os.environ["NPM_IDENTITY"],
        secret=os.environ["NPM_SECRET"],
        timeout_s=20,
    )


def common_args() -> list[str]:
    return [
        "--base-url",
        os.environ["NPM_BASE_URL"],
        "--identity",
        os.environ["NPM_IDENTITY"],
        "--secret",
        os.environ["NPM_SECRET"],
    ]


def marker(prefix: str = "wyrmctl-ci") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def write_doc(tmp_path: Path, doc: dict[str, Any]) -> Path:
    path = tmp_path / f"{uuid.uuid4().hex}.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return path


def cleanup_marker(npm: NpmClient, text: str) -> None:
    caps = npm.capabilities()
    state = npm.existing_state(include_certificates=caps.certificates.list, include_access_lists=caps.access_lists.list)
    for item in state.proxy_hosts:
        if _matches(item, text) and caps.proxy_hosts.delete:
            best_effort_delete(npm, ResourceKind.PROXY_HOST, item.id)
    for item in state.access_lists:
        if _matches(item, text) and caps.access_lists.delete:
            best_effort_delete(npm, ResourceKind.ACCESS_LIST, item.id)
    for item in state.certificates:
        if _matches(item, text) and caps.certificates.delete:
            best_effort_delete(npm, ResourceKind.CERTIFICATE, item.id)


def proxy_by_resource_id(npm: NpmClient, resource_id: str) -> ExistingResource:
    matches = [
        item
        for item in npm.list_resource(ResourceKind.PROXY_HOST)
        if item.identity and item.identity.resource_id == resource_id
    ]
    assert len(matches) == 1
    return matches[0]


def list_by_name(npm: NpmClient, kind: ResourceKind, name: str) -> ExistingResource:
    matches = [item for item in npm.list_resource(kind) if item.name == name]
    assert len(matches) == 1
    return matches[0]


def best_effort_delete(npm: NpmClient, kind: ResourceKind, resource_id: int) -> None:
    deadline = time.monotonic() + 15
    while True:
        if not _resource_present(npm, kind, resource_id):
            return
        try:
            if npm.delete_resource(kind, resource_id):
                return
        except ApiError:
            if time.monotonic() >= deadline:
                return
        if time.monotonic() >= deadline:
            return
        time.sleep(0.5)


def wait_until_absent(
    npm: NpmClient,
    kind: ResourceKind,
    predicate: Callable[[ExistingResource], bool],
    *,
    timeout_s: float = 20,
    interval_s: float = 0.25,
) -> None:
    deadline = time.monotonic() + timeout_s
    while True:
        matches = [item for item in npm.list_resource(kind) if predicate(item)]
        if not matches:
            return
        if time.monotonic() >= deadline:
            rendered = ", ".join(_describe_resource(item) for item in matches)
            raise AssertionError(f"{kind.value} resources still present after {timeout_s}s: {rendered}")
        time.sleep(interval_s)


def _matches(item: ExistingResource, text: str) -> bool:
    if item.identity and (item.identity.owner == text or text in item.identity.resource_id):
        return True
    if item.name and text in item.name:
        return True
    return any(text in domain for domain in item.domain_names)


def _resource_present(npm: NpmClient, kind: ResourceKind, resource_id: int) -> bool:
    return any(item.id == resource_id for item in npm.list_resource(kind))


def _describe_resource(item: ExistingResource) -> str:
    parts = [f"id={item.id}"]
    if item.name:
        parts.append(f"name={item.name}")
    if item.identity is not None:
        parts.append(f"resource_id={item.identity.resource_id}")
    if item.domain_names:
        parts.append(f"domains={list(item.domain_names)}")
    return " ".join(parts)
