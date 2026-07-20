"""wyrmctl exception taxonomy."""

from __future__ import annotations

from typing import Any


class NpmctlError(Exception):
    """Base exception for all wyrmctl errors."""


class ValidationError(NpmctlError):
    """Input validation failed."""


class MetadataError(ValidationError):
    """Managed metadata was missing or invalid."""


class ConflictError(NpmctlError):
    """A requested mutation would violate ownership or integrity constraints."""


class CapabilityError(NpmctlError):
    """The live NPM API schema does not expose a required operation."""


class ApiError(NpmctlError):
    """The NPM API returned an error or an invalid response."""


class CertificateApiError(ApiError):
    """Structured certificate API failure with automation-friendly metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool,
        suggested_action: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.suggested_action = suggested_action
        self.details = details or {}


class CertificateSafetyError(ConflictError):
    """Structured certificate safety conflict raised before mutation."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        suggested_action: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.suggested_action = suggested_action
        self.details = details or {}


class MigrationError(NpmctlError):
    """Desired-state schema migration failed."""


class StructuredError(NpmctlError):
    """Automation-safe failure with stable semantics."""

    def __init__(self, code: str, message: str, *, retryable: bool = False, mutated: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.mutated = mutated


class ContractCompatibilityError(StructuredError, ValidationError):
    """A versioned document is not compatible with the active registry."""


class ArtifactError(StructuredError, ValidationError):
    """An immutable artifact failed validation."""


class LeaseError(StructuredError, ConflictError):
    """A migration or provider mutation lease could not be acquired."""


class RecoveryError(StructuredError, ConflictError):
    """A requested recovery operation is not safe or available."""
