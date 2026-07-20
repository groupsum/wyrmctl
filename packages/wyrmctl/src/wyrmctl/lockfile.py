"""Reproducible wyrmctl lockfile construction and checking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from wyrmctl.contracts import BUILTIN_CONTRACTS, check_document, semantic_digest
from wyrmctl.profile import current_profile
from wyrmctl.errors import ValidationError


@dataclass(frozen=True, slots=True)
class LockCheck:
    ok: bool
    differences: tuple[str, ...]


def build_lock(
    *,
    repository: str,
    commit: str,
    package_version: str,
    python_version: str,
    providers: dict[str, dict[str, Any]],
    api_profiles: dict[str, str],
    inputs: dict[str, str],
) -> dict[str, Any]:
    contracts = {kind: row["current"] for kind, row in BUILTIN_CONTRACTS.matrix().items()}
    return {
        "apiVersion": current_profile().api_version,
        "kind": "NpmctlLock",
        "schemaVersion": 1,
        "metadata": {"repository": repository},
        "spec": {
            "source": {"commit": commit},
            "tooling": {"wyrmctl": package_version, "python": python_version},
            "contracts": contracts,
            "providers": providers,
            "targets": api_profiles,
            "inputs": inputs,
        },
    }


def check_lock(expected: dict[str, Any], actual: dict[str, Any]) -> LockCheck:
    check_document(expected, BUILTIN_CONTRACTS)
    check_document(actual, BUILTIN_CONTRACTS)
    if expected.get("kind") != "NpmctlLock" or actual.get("kind") != "NpmctlLock":
        raise ValidationError("lock documents must use kind NpmctlLock")
    differences = tuple(_differences(expected, actual))
    return LockCheck(not differences, differences)


def lock_digest(lock: dict[str, Any]) -> str:
    check_document(lock, BUILTIN_CONTRACTS)
    return semantic_digest(lock)


def _differences(expected: Any, actual: Any, path: str = "$") -> list[str]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        out: list[str] = []
        for key in sorted(set(expected) | set(actual)):
            if key not in expected:
                out.append(f"{path}.{key}: unexpected")
            elif key not in actual:
                out.append(f"{path}.{key}: missing")
            else:
                out.extend(_differences(expected[key], actual[key], f"{path}.{key}"))
        return out
    if expected != actual:
        return [f"{path}: expected {expected!r}, got {actual!r}"]
    return []
