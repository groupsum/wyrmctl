"""Apply owner-scoped plans to NPM."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wyrmctl.client import NpmClient
from wyrmctl.errors import ApiError, CertificateApiError, ConflictError, ValidationError
from wyrmctl.issuance import CertificateIssuanceGuard
from wyrmctl.metadata import merge_managed_meta
from wyrmctl.models import (
    DesiredAccessList,
    DesiredCertificate,
    DesiredGenericResource,
    DesiredProxyHost,
    ExistingResource,
    ExistingState,
    PlanAction,
    ResourceKind,
)
from wyrmctl.planner import Plan, PlanOperation
from wyrmctl.schema import Capabilities


@dataclass(slots=True)
class ApplyResult:
    """Result of applying a plan."""

    applied: bool
    mutations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"applied": self.applied, "mutations": list(self.mutations)}


class ApplyEngine:
    """Executes a validated plan in dependency order."""

    def __init__(
        self,
        *,
        client: NpmClient,
        capabilities: Capabilities,
        existing_state: ExistingState | None = None,
        issuance_guard: CertificateIssuanceGuard | None = None,
    ) -> None:
        self.client = client
        self.capabilities = capabilities
        self.created_by_resource_id: dict[str, ExistingResource] = {}
        self.issuance_guard = issuance_guard or CertificateIssuanceGuard()
        if existing_state is not None:
            for resource in existing_state.resources():
                if resource.identity is not None:
                    self.created_by_resource_id.setdefault(resource.identity.resource_id, resource)

    def apply(self, plan: Plan) -> ApplyResult:
        """Apply the plan. Conflicts prevent all mutations."""

        if plan.conflicts:
            raise ConflictError("refusing to apply plan with conflicts")
        for operation in plan.operations:
            if operation.desired is not None and operation.existing is not None:
                self.created_by_resource_id.setdefault(operation.desired.identity.resource_id, operation.existing)
        result = ApplyResult(applied=True)
        for operation in _ordered_operations(plan.operations):
            if operation.action == PlanAction.NOOP:
                continue
            mutation = self._apply_operation(operation)
            result.mutations.append(mutation)
        return result

    def _apply_operation(self, operation: PlanOperation) -> dict[str, Any]:
        if operation.action == PlanAction.CREATE:
            return self._create(operation)
        if operation.action == PlanAction.UPDATE:
            return self._update(operation)
        if operation.action == PlanAction.ADOPT:
            return self._adopt(operation)
        if operation.action == PlanAction.DELETE:
            return self._delete(operation)
        raise ValidationError(f"unsupported apply operation {operation.action}")

    def _create(self, operation: PlanOperation) -> dict[str, Any]:
        desired = _require_desired(operation)
        payload = self._payload_for(desired)
        issuance_key: str | None = None
        try:
            if isinstance(desired, DesiredCertificate):
                issuance_key = self.issuance_guard.begin(desired)
            if (
                isinstance(desired, DesiredCertificate)
                and desired.certificate_type == "letsencrypt"
                and self.capabilities.certificate_request
            ):
                payload["meta"] = merge_managed_meta(payload.get("meta"), desired.meta)
                created = self.client.request_certificate(payload)
                if created.identity != desired.identity:
                    certificate_capabilities = self.capabilities.for_kind(ResourceKind.CERTIFICATE)
                    if not certificate_capabilities.update:
                        raise ValidationError(
                            "certificate request did not persist managed identity and the provider "
                            "does not advertise certificate update support"
                        )
                    identity_payload = _updateable_existing_payload(created)
                    identity_payload["meta"] = merge_managed_meta(created.raw.get("meta"), desired.meta)
                    created = self.client.update_resource(
                        ResourceKind.CERTIFICATE,
                        created.id,
                        identity_payload,
                        method=certificate_capabilities.update_method or "put",
                    )
            else:
                if isinstance(desired, DesiredCertificate):
                    payload = self._generic_certificate_payload(desired, payload)
                created = self.client.create_resource(desired.kind, payload)
        except CertificateApiError:
            if issuance_key is not None:
                self.issuance_guard.fail(issuance_key, error_code="certificate_api_error")
            raise
        except Exception:
            if issuance_key is not None:
                self.issuance_guard.fail(issuance_key, error_code="certificate_create_failed")
            raise
        if issuance_key is not None:
            self.issuance_guard.succeed(issuance_key)
        self.created_by_resource_id[desired.identity.resource_id] = created
        return {
            "action": "create",
            "kind": desired.kind.value,
            "resource_id": desired.identity.resource_id,
            "id": created.id,
        }

    def _update(self, operation: PlanOperation) -> dict[str, Any]:
        desired = _require_desired(operation)
        existing = _require_existing(operation)
        payload = self._merge_existing_with_desired(existing, desired)
        cap = self.capabilities.for_kind(desired.kind)
        issuance_key: str | None = None
        try:
            if isinstance(desired, DesiredCertificate):
                issuance_key = self.issuance_guard.begin(desired)
            updated = self.client.update_resource(desired.kind, existing.id, payload, method=cap.update_method or "put")
        except CertificateApiError:
            if issuance_key is not None:
                self.issuance_guard.fail(issuance_key, error_code="certificate_api_error")
            raise
        except Exception:
            if issuance_key is not None:
                self.issuance_guard.fail(issuance_key, error_code="certificate_update_failed")
            raise
        if issuance_key is not None:
            self.issuance_guard.succeed(issuance_key)
        return {
            "action": "update",
            "kind": desired.kind.value,
            "resource_id": desired.identity.resource_id,
            "id": updated.id,
        }

    def _adopt(self, operation: PlanOperation) -> dict[str, Any]:
        desired = _require_desired(operation)
        existing = _require_existing(operation)
        payload = _updateable_existing_payload(existing)
        payload["meta"] = merge_managed_meta(payload.get("meta"), desired.meta)
        cap = self.capabilities.for_kind(desired.kind)
        updated = self.client.update_resource(desired.kind, existing.id, payload, method=cap.update_method or "put")
        return {
            "action": "adopt",
            "kind": desired.kind.value,
            "resource_id": desired.identity.resource_id,
            "id": updated.id,
        }

    def _delete(self, operation: PlanOperation) -> dict[str, Any]:
        existing = _require_existing(operation)
        deleted = self.client.delete_resource(existing.kind, existing.id)
        if not deleted:
            raise ApiError(f"delete failed for {existing.kind.value} id={existing.id}")
        resource_id = existing.identity.resource_id if existing.identity else None
        return {"action": "delete", "kind": existing.kind.value, "resource_id": resource_id, "id": existing.id}

    def _merge_existing_with_desired(
        self,
        existing: ExistingResource,
        desired: DesiredProxyHost | DesiredCertificate | DesiredAccessList | DesiredGenericResource,
    ) -> dict[str, Any]:
        payload = self._payload_for(desired)
        payload["meta"] = merge_managed_meta(existing.raw.get("meta"), desired.meta)
        return payload

    def _payload_for(
        self, desired: DesiredProxyHost | DesiredCertificate | DesiredAccessList | DesiredGenericResource
    ) -> dict[str, Any]:
        if isinstance(desired, DesiredProxyHost):
            certificate_id = self._resolve_reference(desired.certificate_ref, ResourceKind.CERTIFICATE)
            access_list_id = self._resolve_reference(desired.access_list_ref, ResourceKind.ACCESS_LIST)
            return desired.to_payload(certificate_id=certificate_id, access_list_id=access_list_id)
        return desired.to_payload()

    @staticmethod
    def _generic_certificate_payload(desired: DesiredCertificate, payload: dict[str, Any]) -> dict[str, Any]:
        """Keep provider metadata but omit Portwyrm-only ownership keys for legacy NPM."""

        generic = dict(payload)
        if "meta" in desired.api_payload:
            provider_meta = desired.api_payload.get("meta")
            if isinstance(provider_meta, dict):
                generic["meta"] = dict(provider_meta)
            else:
                generic.pop("meta", None)
        return generic

    def _resolve_reference(self, ref: str | None, kind: ResourceKind) -> int | None:
        if ref is None:
            return None
        created = self.created_by_resource_id.get(ref)
        if created is not None:
            if created.kind != kind:
                raise ValidationError(f"reference {ref!r} resolved to {created.kind.value}, expected {kind.value}")
            return created.id
        raise ValidationError(f"unresolved {kind.value} reference: {ref}")


def _ordered_operations(operations: tuple[PlanOperation, ...]) -> list[PlanOperation]:
    creates_updates_adopts = [
        op for op in operations if op.action in {PlanAction.CREATE, PlanAction.UPDATE, PlanAction.ADOPT}
    ]
    deletes = [op for op in operations if op.action == PlanAction.DELETE]
    order = {
        ResourceKind.CERTIFICATE: 0,
        ResourceKind.ACCESS_LIST: 1,
        ResourceKind.REDIRECTION_HOST: 2,
        ResourceKind.DEAD_HOST: 2,
        ResourceKind.STREAM: 2,
        ResourceKind.QUIC_PASSTHROUGH_HOST: 2,
        ResourceKind.USER: 2,
        ResourceKind.SETTING: 2,
        ResourceKind.PROXY_HOST: 3,
    }
    delete_order = {
        ResourceKind.PROXY_HOST: 0,
        ResourceKind.REDIRECTION_HOST: 1,
        ResourceKind.DEAD_HOST: 1,
        ResourceKind.STREAM: 1,
        ResourceKind.QUIC_PASSTHROUGH_HOST: 1,
        ResourceKind.USER: 1,
        ResourceKind.SETTING: 1,
        ResourceKind.ACCESS_LIST: 2,
        ResourceKind.CERTIFICATE: 3,
    }
    return sorted(creates_updates_adopts, key=lambda op: order[op.kind]) + sorted(
        deletes, key=lambda op: delete_order[op.kind]
    )


def _require_desired(
    operation: PlanOperation,
) -> DesiredProxyHost | DesiredCertificate | DesiredAccessList | DesiredGenericResource:
    if operation.desired is None:
        raise ValidationError(f"operation {operation.action} requires desired resource")
    return operation.desired


def _require_existing(operation: PlanOperation) -> ExistingResource:
    if operation.existing is None:
        raise ValidationError(f"operation {operation.action} requires existing resource")
    return operation.existing


def _updateable_existing_payload(existing: ExistingResource) -> dict[str, Any]:
    fields = {
        ResourceKind.PROXY_HOST: (
            "domain_names",
            "forward_scheme",
            "forward_host",
            "forward_port",
            "certificate_id",
            "ssl_forced",
            "hsts_enabled",
            "hsts_subdomains",
            "http2_support",
            "block_exploits",
            "caching_enabled",
            "allow_websocket_upgrade",
            "access_list_id",
            "advanced_config",
            "enabled",
            "locations",
            "meta",
        ),
        ResourceKind.ACCESS_LIST: ("name", "satisfy_any", "pass_auth", "items", "clients", "meta"),
        ResourceKind.CERTIFICATE: ("provider", "nice_name", "domain_names", "meta"),
        ResourceKind.REDIRECTION_HOST: ("domain_names", "forward_domain_name", "meta"),
        ResourceKind.DEAD_HOST: ("domain_names", "meta"),
        ResourceKind.STREAM: ("incoming_port", "forward_host", "forward_port", "protocol", "meta"),
        ResourceKind.QUIC_PASSTHROUGH_HOST: (
            "listen_address",
            "incoming_port",
            "server_name",
            "alpn",
            "target_kind",
            "target",
            "target_port",
            "idle_timeout_seconds",
            "enabled",
            "meta",
        ),
        ResourceKind.USER: ("name", "email", "roles", "is_disabled", "meta"),
        ResourceKind.SETTING: ("name", "value", "meta"),
    }[existing.kind]
    payload = {field: existing.raw[field] for field in fields if field in existing.raw}
    if existing.kind == ResourceKind.PROXY_HOST:
        defaults = {
            "access_list_id": 0,
            "certificate_id": 0,
            "ssl_forced": 0,
            "hsts_enabled": 0,
            "hsts_subdomains": 0,
            "http2_support": 0,
            "block_exploits": 0,
            "caching_enabled": 0,
            "allow_websocket_upgrade": 0,
            "advanced_config": "",
            "enabled": 1,
            "locations": [],
        }
        for field, default in defaults.items():
            if payload.get(field) is None:
                payload[field] = default
    return payload
