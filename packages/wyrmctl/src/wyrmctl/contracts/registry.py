"""Contract registration and fail-closed version compatibility."""

from __future__ import annotations

from typing import Any

from wyrmctl.contracts.types import ContractSupport
from wyrmctl.errors import ContractCompatibilityError


class ContractRegistry:
    """Registry of independently versioned document contracts."""

    def __init__(self) -> None:
        self._contracts: dict[str, ContractSupport] = {}

    def register(self, support: ContractSupport) -> None:
        if not support.kind or support.current < 1:
            raise ValueError("contract kind and positive current version are required")
        if support.kind in self._contracts:
            raise ValueError(f"contract already registered: {support.kind}")
        if support.current not in support.writable or not support.writable <= support.readable:
            raise ValueError("current must be writable and every writable version must be readable")
        self._contracts[support.kind] = support

    def support(self, kind: str) -> ContractSupport:
        try:
            return self._contracts[kind]
        except KeyError as exc:
            raise ContractCompatibilityError("UNKNOWN_CONTRACT", f"unknown contract kind: {kind}") from exc

    def require_readable(self, kind: str, version: int, *, strict: bool = False) -> list[str]:
        support = self.support(kind)
        if version not in support.readable:
            direction = "future" if version > support.current else "unsupported"
            raise ContractCompatibilityError(
                "UNSUPPORTED_CONTRACT_VERSION",
                f"{kind} schemaVersion {version} is {direction}; readable versions: {sorted(support.readable)}",
            )
        warnings = [f"{kind} schema {version} is deprecated"] if version in support.deprecated else []
        if warnings and strict:
            raise ContractCompatibilityError("DEPRECATED_CONTRACT_VERSION", warnings[0])
        return warnings

    def require_writable(self, kind: str, version: int) -> None:
        support = self.support(kind)
        if version not in support.writable:
            raise ContractCompatibilityError(
                "UNWRITABLE_CONTRACT_VERSION",
                f"{kind} schema {version} is not writable; writable versions: {sorted(support.writable)}",
            )

    def parser(self, kind: str, version: int) -> Any:
        self.require_readable(kind, version)
        try:
            return self.support(kind).parsers[version]
        except KeyError as exc:
            raise ContractCompatibilityError(
                "MISSING_CONTRACT_PARSER", f"no parser registered for {kind} schema {version}"
            ) from exc

    def matrix(self) -> dict[str, dict[str, Any]]:
        return {kind: self._contracts[kind].to_dict() for kind in sorted(self._contracts)}
