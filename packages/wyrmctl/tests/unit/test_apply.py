from __future__ import annotations

from dataclasses import replace

import pytest

from wyrmctl.apply import ApplyEngine
from wyrmctl.errors import ApiError, CertificateApiError, ConflictError, ValidationError
from wyrmctl.issuance import CertificateIssuanceGuard
from wyrmctl.models import (
    DesiredAccessList,
    DesiredCertificate,
    DesiredProxyHost,
    ExistingResource,
    PlanAction,
    ResourceKind,
)
from wyrmctl.planner import Plan, PlanConflict, PlanOperation
from wyrmctl.schema import Capabilities


def _meta(resource_id: str, owner: str = "workload-a") -> dict[str, str]:
    return {"managed_by": "wyrmctl", "owner": owner, "resource_id": resource_id}


def _cert(resource_id: str = "cert.one") -> DesiredCertificate:
    return DesiredCertificate.from_mapping(
        {
            "name": "cert-one",
            "domain_names": ["app.example.com"],
            "meta": _meta(resource_id),
            "api_payload": {"provider": "other"},
        },
        path="cert",
    )


def _acl(resource_id: str = "acl.one") -> DesiredAccessList:
    return DesiredAccessList.from_mapping(
        {"name": "acl-one", "meta": _meta(resource_id), "api_payload": {"items": [], "clients": []}},
        path="acl",
    )


def _proxy(
    resource_id: str = "proxy.one",
    *,
    certificate_ref: str | None = "cert.one",
    access_list_ref: str | None = "acl.one",
) -> DesiredProxyHost:
    raw = {
        "domain_names": ["app.example.com"],
        "forward_host": "app",
        "forward_port": 3000,
        "meta": _meta(resource_id),
        "certificate_ref": certificate_ref,
        "access_list_ref": access_list_ref,
    }
    return DesiredProxyHost.from_mapping(raw, path="proxy")


def _existing(kind: ResourceKind, resource_id: str, item_id: int, **overrides) -> ExistingResource:
    if kind == ResourceKind.CERTIFICATE:
        raw = {
            "id": item_id,
            "name": "cert-one",
            "domain_names": ["app.example.com"],
            "provider": "other",
            "meta": _meta(resource_id),
        }
        raw.update(overrides)
        return ExistingResource.from_certificate(raw)
    if kind == ResourceKind.ACCESS_LIST:
        raw = {"id": item_id, "name": "acl-one", "items": [], "clients": [], "meta": _meta(resource_id)}
        raw.update(overrides)
        return ExistingResource.from_access_list(raw)
    raw = {
        "id": item_id,
        "domain_names": ["app.example.com"],
        "forward_host": "app",
        "forward_port": 3000,
        "forward_scheme": "http",
        "meta": _meta(resource_id),
    }
    raw.update(overrides)
    return ExistingResource.from_proxy_host(raw)


class RecordingClient:
    def __init__(self, *, delete_ok: bool = True) -> None:
        self.events: list[tuple[str, ResourceKind, int | None, dict | None]] = []
        self.next_id = 100
        self.delete_ok = delete_ok

    def create_resource(self, kind: ResourceKind, payload: dict) -> ExistingResource:
        self.events.append(("create", kind, None, payload))
        self.next_id += 1
        raw = dict(payload) | {"id": self.next_id}
        if kind == ResourceKind.CERTIFICATE:
            return ExistingResource.from_certificate(raw)
        if kind == ResourceKind.ACCESS_LIST:
            return ExistingResource.from_access_list(raw)
        return ExistingResource.from_proxy_host(raw)

    def request_certificate(self, payload: dict) -> ExistingResource:
        self.events.append(("request", ResourceKind.CERTIFICATE, None, payload))
        self.next_id += 1
        return ExistingResource.from_certificate(dict(payload) | {"id": self.next_id})

    def update_resource(
        self, kind: ResourceKind, resource_id: int, payload: dict, *, method: str = "put"
    ) -> ExistingResource:
        self.events.append((f"update:{method}", kind, resource_id, payload))
        raw = dict(payload) | {"id": resource_id}
        if kind == ResourceKind.CERTIFICATE:
            return ExistingResource.from_certificate(raw)
        if kind == ResourceKind.ACCESS_LIST:
            return ExistingResource.from_access_list(raw)
        return ExistingResource.from_proxy_host(raw)

    def delete_resource(self, kind: ResourceKind, resource_id: int) -> bool:
        self.events.append(("delete", kind, resource_id, None))
        return self.delete_ok


def _engine(client: RecordingClient) -> ApplyEngine:
    return ApplyEngine(
        client=client, capabilities=Capabilities.full_for_tests(), issuance_guard=RecordingIssuanceGuard()
    )


class RecordingIssuanceGuard(CertificateIssuanceGuard):
    def __init__(self) -> None:
        super().__init__(state_file="NUL", cooldown_seconds=1, inflight_ttl_seconds=1)
        self.events: list[tuple[str, str]] = []

    def begin(self, certificate: DesiredCertificate) -> str:
        key = certificate.identity.resource_id
        self.events.append(("begin", key))
        return key

    def succeed(self, key: str) -> None:
        self.events.append(("succeed", key))

    def fail(self, key: str, *, error_code: str) -> None:
        self.events.append(("fail", f"{key}:{error_code}"))


def test_apply_orders_dependencies_and_reverse_deletes() -> None:
    client = RecordingClient()
    old_cert = _existing(ResourceKind.CERTIFICATE, "cert.old", 1, name="old-cert")
    old_acl = _existing(ResourceKind.ACCESS_LIST, "acl.old", 2, name="old-acl")
    old_proxy = _existing(ResourceKind.PROXY_HOST, "proxy.old", 3, domain_names=["old.example.com"])
    plan = Plan(
        operations=(
            PlanOperation(PlanAction.DELETE, ResourceKind.CERTIFICATE, existing=old_cert),
            PlanOperation(PlanAction.CREATE, ResourceKind.PROXY_HOST, desired=_proxy()),
            PlanOperation(PlanAction.DELETE, ResourceKind.ACCESS_LIST, existing=old_acl),
            PlanOperation(PlanAction.CREATE, ResourceKind.ACCESS_LIST, desired=_acl()),
            PlanOperation(PlanAction.DELETE, ResourceKind.PROXY_HOST, existing=old_proxy),
            PlanOperation(PlanAction.CREATE, ResourceKind.CERTIFICATE, desired=_cert()),
        ),
        conflicts=(),
        existing_count=3,
    )

    result = _engine(client).apply(plan)

    assert [f"{event}:{kind.value}" for event, kind, _, _ in client.events] == [
        "create:certificate",
        "create:access_list",
        "create:proxy_host",
        "delete:proxy_host",
        "delete:access_list",
        "delete:certificate",
    ]
    proxy_payload = client.events[2][3]
    assert proxy_payload["certificate_id"] == result.mutations[0]["id"]
    assert proxy_payload["access_list_id"] == result.mutations[1]["id"]


def test_apply_resolves_references_from_existing_noop_operations() -> None:
    client = RecordingClient()
    plan = Plan(
        operations=(
            PlanOperation(
                PlanAction.NOOP,
                ResourceKind.CERTIFICATE,
                desired=_cert(),
                existing=_existing(ResourceKind.CERTIFICATE, "cert.one", 41),
            ),
            PlanOperation(
                PlanAction.NOOP,
                ResourceKind.ACCESS_LIST,
                desired=_acl(),
                existing=_existing(ResourceKind.ACCESS_LIST, "acl.one", 42),
            ),
            PlanOperation(PlanAction.CREATE, ResourceKind.PROXY_HOST, desired=_proxy()),
        ),
        conflicts=(),
        existing_count=2,
    )

    _engine(client).apply(plan)

    proxy_payload = client.events[0][3]
    assert proxy_payload["certificate_id"] == 41
    assert proxy_payload["access_list_id"] == 42


def test_apply_rejects_unresolved_references_before_mutation() -> None:
    client = RecordingClient()
    plan = Plan(
        operations=(
            PlanOperation(PlanAction.CREATE, ResourceKind.PROXY_HOST, desired=_proxy(certificate_ref="missing")),
        ),
        conflicts=(),
        existing_count=0,
    )

    with pytest.raises(ValidationError, match="unresolved certificate reference"):
        _engine(client).apply(plan)

    assert client.events == []


def test_apply_adopt_merges_metadata_without_overwriting_payload_fields() -> None:
    client = RecordingClient()
    existing = _existing(
        ResourceKind.PROXY_HOST,
        "legacy",
        5,
        meta={"manual": "keep"},
        forward_host="manual-host",
        forward_port=8080,
    )
    plan = Plan(
        operations=(PlanOperation(PlanAction.ADOPT, ResourceKind.PROXY_HOST, desired=_proxy(), existing=existing),),
        conflicts=(),
        existing_count=1,
    )

    _engine(client).apply(plan)

    payload = client.events[0][3]
    assert payload["forward_host"] == "manual-host"
    assert payload["forward_port"] == 8080
    assert payload["meta"]["manual"] == "keep"
    assert payload["meta"]["managed_by"] == "wyrmctl"
    assert payload["meta"]["owner"] == "workload-a"
    assert payload["meta"]["resource_id"] == "proxy.one"


def test_apply_refuses_conflicted_plan_without_mutation() -> None:
    client = RecordingClient()
    plan = Plan(
        operations=(PlanOperation(PlanAction.CREATE, ResourceKind.PROXY_HOST, desired=_proxy()),),
        conflicts=(PlanConflict(code="foreign_owner", message="blocked"),),
        existing_count=1,
    )

    with pytest.raises(ConflictError):
        _engine(client).apply(plan)

    assert client.events == []


def test_apply_reports_delete_success_and_failure() -> None:
    existing = _existing(ResourceKind.PROXY_HOST, "proxy.old", 7)
    plan = Plan(
        operations=(PlanOperation(PlanAction.DELETE, ResourceKind.PROXY_HOST, existing=existing),),
        conflicts=(),
        existing_count=1,
    )
    ok_client = RecordingClient()
    result = _engine(ok_client).apply(plan)
    assert result.mutations == [{"action": "delete", "kind": "proxy_host", "resource_id": "proxy.old", "id": 7}]

    failing_client = RecordingClient(delete_ok=False)
    with pytest.raises(ApiError, match="delete failed"):
        _engine(failing_client).apply(plan)


def test_apply_resolves_references_from_existing_state_scope() -> None:
    client = RecordingClient()
    existing_state = type(
        "ExistingStateStub",
        (),
        {
            "resources": lambda self: (
                _existing(ResourceKind.CERTIFICATE, "cert.one", 41),
                _existing(ResourceKind.ACCESS_LIST, "acl.one", 42),
            )
        },
    )()
    plan = Plan(
        operations=(PlanOperation(PlanAction.CREATE, ResourceKind.PROXY_HOST, desired=_proxy()),),
        conflicts=(),
        existing_count=2,
    )

    ApplyEngine(client=client, capabilities=Capabilities.full_for_tests(), existing_state=existing_state).apply(plan)  # type: ignore[arg-type]

    proxy_payload = client.events[0][3]
    assert proxy_payload["certificate_id"] == 41
    assert proxy_payload["access_list_id"] == 42


def test_apply_certificate_mutations_use_issuance_guard() -> None:
    client = RecordingClient()
    guard = RecordingIssuanceGuard()
    plan = Plan(
        operations=(PlanOperation(PlanAction.CREATE, ResourceKind.CERTIFICATE, desired=_cert()),),
        conflicts=(),
        existing_count=0,
    )

    ApplyEngine(client=client, capabilities=Capabilities.full_for_tests(), issuance_guard=guard).apply(plan)

    assert guard.events == [("begin", "cert.one"), ("succeed", "cert.one")]


def test_apply_generic_certificate_keeps_only_provider_metadata() -> None:
    client = RecordingClient()
    desired = DesiredCertificate.from_mapping(
        {
            "name": "legacy-cert",
            "domain_names": ["legacy.example.com"],
            "meta": _meta("cert.legacy"),
            "api_payload": {"provider": "other", "meta": {"certificate": "pem"}},
        },
        path="cert",
    )
    plan = Plan(
        operations=(PlanOperation(PlanAction.CREATE, ResourceKind.CERTIFICATE, desired=desired),),
        conflicts=(),
        existing_count=0,
    )

    ApplyEngine(
        client=client,
        capabilities=replace(Capabilities.full_for_tests(), certificate_request=False),
        issuance_guard=RecordingIssuanceGuard(),
    ).apply(plan)

    assert client.events[0][0] == "create"
    assert client.events[0][3]["meta"] == {"certificate": "pem"}


def test_apply_generic_certificate_omits_invalid_provider_metadata() -> None:
    desired = _cert()
    payload = desired.to_payload()
    desired.api_payload["meta"] = "unsupported"

    assert ApplyEngine._generic_certificate_payload(desired, payload).get("meta") is None


def test_apply_uses_provider_acme_request_endpoint_when_advertised() -> None:
    client = RecordingClient()
    guard = RecordingIssuanceGuard()
    plan = Plan(
        operations=(PlanOperation(PlanAction.CREATE, ResourceKind.CERTIFICATE, desired=_cert()),),
        conflicts=(),
        existing_count=0,
    )
    capabilities = replace(Capabilities.full_for_tests(), certificate_request=True)

    ApplyEngine(client=client, capabilities=capabilities, issuance_guard=guard).apply(plan)

    assert client.events[0][0] == "request"
    assert client.events[0][3]["meta"] == _meta("cert.one")
    assert guard.events == [("begin", "cert.one"), ("succeed", "cert.one")]


def test_apply_persists_identity_when_certificate_request_drops_metadata() -> None:
    class MetadataDroppingClient(RecordingClient):
        def request_certificate(self, payload: dict) -> ExistingResource:
            self.events.append(("request", ResourceKind.CERTIFICATE, None, payload))
            self.next_id += 1
            created = dict(payload) | {"id": self.next_id}
            created["meta"] = {"letsencrypt_email": "ops@example.com"}
            return ExistingResource.from_certificate(created)

    client = MetadataDroppingClient()
    guard = RecordingIssuanceGuard()
    plan = Plan(
        operations=(PlanOperation(PlanAction.CREATE, ResourceKind.CERTIFICATE, desired=_cert()),),
        conflicts=(),
        existing_count=0,
    )
    capabilities = replace(Capabilities.full_for_tests(), certificate_request=True)

    result = ApplyEngine(client=client, capabilities=capabilities, issuance_guard=guard).apply(plan)

    assert [event[0] for event in client.events] == ["request", "update:put"]
    assert client.events[1][2] == result.mutations[0]["id"]
    assert client.events[1][3]["meta"] == {
        "letsencrypt_email": "ops@example.com",
        **_meta("cert.one"),
    }
    assert guard.events == [("begin", "cert.one"), ("succeed", "cert.one")]


def test_apply_fails_closed_when_issued_certificate_identity_cannot_be_persisted() -> None:
    class MetadataDroppingClient(RecordingClient):
        def request_certificate(self, payload: dict) -> ExistingResource:
            self.events.append(("request", ResourceKind.CERTIFICATE, None, payload))
            self.next_id += 1
            created = dict(payload) | {"id": self.next_id, "meta": {}}
            return ExistingResource.from_certificate(created)

    client = MetadataDroppingClient()
    guard = RecordingIssuanceGuard()
    plan = Plan(
        operations=(PlanOperation(PlanAction.CREATE, ResourceKind.CERTIFICATE, desired=_cert()),),
        conflicts=(),
        existing_count=0,
    )
    capabilities = replace(
        Capabilities.full_for_tests(),
        certificate_request=True,
        certificates=replace(Capabilities.full_for_tests().certificates, update=False, update_method=None),
    )

    with pytest.raises(ValidationError, match="did not persist managed identity"):
        ApplyEngine(client=client, capabilities=capabilities, issuance_guard=guard).apply(plan)

    assert [event[0] for event in client.events] == ["request"]
    assert guard.events == [("begin", "cert.one"), ("fail", "cert.one:certificate_create_failed")]


def test_apply_certificate_update_uses_issuance_guard_on_success() -> None:
    client = RecordingClient()
    guard = RecordingIssuanceGuard()
    existing = _existing(ResourceKind.CERTIFICATE, "cert.one", 12)
    plan = Plan(
        operations=(
            PlanOperation(
                PlanAction.UPDATE,
                ResourceKind.CERTIFICATE,
                desired=_cert(),
                existing=existing,
            ),
        ),
        conflicts=(),
        existing_count=1,
    )

    ApplyEngine(client=client, capabilities=Capabilities.full_for_tests(), issuance_guard=guard).apply(plan)

    assert guard.events == [("begin", "cert.one"), ("succeed", "cert.one")]


def test_apply_certificate_mutations_record_guard_failure_on_certificate_api_error() -> None:
    class FailingClient(RecordingClient):
        def create_resource(self, kind: ResourceKind, payload: dict) -> ExistingResource:
            raise CertificateApiError(
                "certificate_lock_retryable",
                "certbot busy",
                retryable=True,
                suggested_action="retry later",
            )

    guard = RecordingIssuanceGuard()
    plan = Plan(
        operations=(PlanOperation(PlanAction.CREATE, ResourceKind.CERTIFICATE, desired=_cert()),),
        conflicts=(),
        existing_count=0,
    )

    with pytest.raises(CertificateApiError):
        ApplyEngine(client=FailingClient(), capabilities=Capabilities.full_for_tests(), issuance_guard=guard).apply(
            plan
        )

    assert guard.events == [("begin", "cert.one"), ("fail", "cert.one:certificate_api_error")]


def test_apply_certificate_update_records_guard_failure_on_certificate_api_error() -> None:
    class FailingClient(RecordingClient):
        def update_resource(
            self, kind: ResourceKind, resource_id: int, payload: dict, *, method: str = "put"
        ) -> ExistingResource:
            raise CertificateApiError(
                "certificate_lock_retryable",
                "certbot busy",
                retryable=True,
                suggested_action="retry later",
            )

    guard = RecordingIssuanceGuard()
    existing = _existing(ResourceKind.CERTIFICATE, "cert.one", 9)
    plan = Plan(
        operations=(
            PlanOperation(
                PlanAction.UPDATE,
                ResourceKind.CERTIFICATE,
                desired=_cert(),
                existing=existing,
            ),
        ),
        conflicts=(),
        existing_count=1,
    )

    with pytest.raises(CertificateApiError):
        ApplyEngine(client=FailingClient(), capabilities=Capabilities.full_for_tests(), issuance_guard=guard).apply(
            plan
        )

    assert guard.events == [("begin", "cert.one"), ("fail", "cert.one:certificate_api_error")]


def test_apply_certificate_create_records_guard_failure_on_generic_error() -> None:
    class FailingClient(RecordingClient):
        def create_resource(self, kind: ResourceKind, payload: dict) -> ExistingResource:
            raise RuntimeError("boom")

    guard = RecordingIssuanceGuard()
    plan = Plan(
        operations=(PlanOperation(PlanAction.CREATE, ResourceKind.CERTIFICATE, desired=_cert()),),
        conflicts=(),
        existing_count=0,
    )

    with pytest.raises(RuntimeError, match="boom"):
        ApplyEngine(client=FailingClient(), capabilities=Capabilities.full_for_tests(), issuance_guard=guard).apply(
            plan
        )

    assert guard.events == [("begin", "cert.one"), ("fail", "cert.one:certificate_create_failed")]


def test_apply_non_certificate_failures_do_not_touch_issuance_guard() -> None:
    class FailingCreateApiClient(RecordingClient):
        def create_resource(self, kind: ResourceKind, payload: dict) -> ExistingResource:
            raise CertificateApiError(
                "certificate_lock_retryable",
                "proxy create hit certbot lock",
                retryable=True,
                suggested_action="retry later",
            )

    class FailingCreateGenericClient(RecordingClient):
        def create_resource(self, kind: ResourceKind, payload: dict) -> ExistingResource:
            raise RuntimeError("proxy create failed")

    class FailingUpdateGenericClient(RecordingClient):
        def update_resource(
            self, kind: ResourceKind, resource_id: int, payload: dict, *, method: str = "put"
        ) -> ExistingResource:
            raise RuntimeError("proxy update failed")

    class FailingUpdateApiClient(RecordingClient):
        def update_resource(
            self, kind: ResourceKind, resource_id: int, payload: dict, *, method: str = "put"
        ) -> ExistingResource:
            raise CertificateApiError(
                "certificate_lock_retryable",
                "proxy update hit certbot lock",
                retryable=True,
                suggested_action="retry later",
            )

    create_guard = RecordingIssuanceGuard()
    create_plan = Plan(
        operations=(
            PlanOperation(
                PlanAction.CREATE,
                ResourceKind.PROXY_HOST,
                desired=_proxy(certificate_ref=None, access_list_ref=None),
            ),
        ),
        conflicts=(),
        existing_count=0,
    )
    with pytest.raises(CertificateApiError):
        ApplyEngine(
            client=FailingCreateApiClient(),
            capabilities=Capabilities.full_for_tests(),
            issuance_guard=create_guard,
        ).apply(create_plan)
    assert create_guard.events == []

    create_guard = RecordingIssuanceGuard()
    with pytest.raises(RuntimeError, match="proxy create failed"):
        ApplyEngine(
            client=FailingCreateGenericClient(),
            capabilities=Capabilities.full_for_tests(),
            issuance_guard=create_guard,
        ).apply(create_plan)
    assert create_guard.events == []

    update_guard = RecordingIssuanceGuard()
    update_plan = Plan(
        operations=(
            PlanOperation(
                PlanAction.UPDATE,
                ResourceKind.PROXY_HOST,
                desired=_proxy(certificate_ref=None, access_list_ref=None),
                existing=_existing(ResourceKind.PROXY_HOST, "proxy.one", 13),
            ),
        ),
        conflicts=(),
        existing_count=1,
    )
    with pytest.raises(RuntimeError, match="proxy update failed"):
        ApplyEngine(
            client=FailingUpdateGenericClient(),
            capabilities=Capabilities.full_for_tests(),
            issuance_guard=update_guard,
        ).apply(update_plan)
    assert update_guard.events == []

    update_guard = RecordingIssuanceGuard()
    with pytest.raises(CertificateApiError):
        ApplyEngine(
            client=FailingUpdateApiClient(),
            capabilities=Capabilities.full_for_tests(),
            issuance_guard=update_guard,
        ).apply(update_plan)
    assert update_guard.events == []


def test_apply_certificate_update_records_guard_failure_on_generic_error() -> None:
    class FailingClient(RecordingClient):
        def update_resource(
            self, kind: ResourceKind, resource_id: int, payload: dict, *, method: str = "put"
        ) -> ExistingResource:
            raise RuntimeError("boom")

    guard = RecordingIssuanceGuard()
    existing = _existing(ResourceKind.CERTIFICATE, "cert.one", 7)
    plan = Plan(
        operations=(
            PlanOperation(
                PlanAction.UPDATE,
                ResourceKind.CERTIFICATE,
                desired=_cert(),
                existing=existing,
            ),
        ),
        conflicts=(),
        existing_count=1,
    )

    with pytest.raises(RuntimeError, match="boom"):
        ApplyEngine(client=FailingClient(), capabilities=Capabilities.full_for_tests(), issuance_guard=guard).apply(
            plan
        )

    assert guard.events == [("begin", "cert.one"), ("fail", "cert.one:certificate_update_failed")]
