"""Public contract compatibility API."""

from wyrmctl.contracts.builtin import BUILTIN_CONTRACTS, build_builtin_registry
from wyrmctl.contracts.canonical import canonical_json, canonicalize, semantic_digest
from wyrmctl.contracts.compatibility import API_VERSION, check_document
from wyrmctl.contracts.registry import ContractRegistry
from wyrmctl.contracts.types import ContractSupport, DocumentEnvelope

__all__ = [
    "API_VERSION",
    "BUILTIN_CONTRACTS",
    "ContractRegistry",
    "ContractSupport",
    "DocumentEnvelope",
    "build_builtin_registry",
    "canonical_json",
    "canonicalize",
    "check_document",
    "semantic_digest",
]
