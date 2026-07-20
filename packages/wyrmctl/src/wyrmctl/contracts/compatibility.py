"""Contract-envelope checks that never rewrite source documents."""

from __future__ import annotations

from typing import Any

from wyrmctl.contracts.registry import ContractRegistry
from wyrmctl.errors import ContractCompatibilityError
from wyrmctl.profile import current_profile

API_VERSION = "wyrmctl.com/v1"


def check_document(document: dict[str, Any], registry: ContractRegistry, *, strict: bool = False) -> list[str]:
    expected = current_profile().api_version
    if document.get("apiVersion") != expected:
        raise ContractCompatibilityError("UNSUPPORTED_API_VERSION", f"apiVersion must be {expected!r}")
    kind = document.get("kind")
    version = document.get("schemaVersion")
    if not isinstance(kind, str) or not kind:
        raise ContractCompatibilityError("MISSING_CONTRACT_KIND", "kind must be a non-empty string")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ContractCompatibilityError("INVALID_SCHEMA_VERSION", "schemaVersion must be a positive integer")
    return registry.require_readable(kind, version, strict=strict)
