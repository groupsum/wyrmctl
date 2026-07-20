"""Verified inverse and forward-repair recovery planning."""

from __future__ import annotations

from typing import Any, Callable

from wyrmctl.errors import RecoveryError


def rollback(value: dict[str, Any], inverse: Callable[[dict[str, Any]], dict[str, Any]] | None) -> dict[str, Any]:
    if inverse is None:
        raise RecoveryError("ROLLBACK_UNAVAILABLE", "migration is forward-repair-only")
    return inverse(dict(value))


def forward_repair(
    *, expected: list[dict[str, Any]], observed: list[dict[str, Any]], key: str = "identity"
) -> tuple[dict[str, Any], ...]:
    wanted = {str(item[key]): item for item in expected}
    actual = {str(item[key]): item for item in observed}
    operations: list[dict[str, Any]] = []
    for identity in sorted(set(wanted) | set(actual)):
        if identity not in actual:
            operations.append({"action": "create", "identity": identity, "after": wanted[identity]})
        elif identity not in wanted:
            operations.append({"action": "delete", "identity": identity, "before": actual[identity]})
        elif wanted[identity] != actual[identity]:
            operations.append(
                {"action": "update", "identity": identity, "before": actual[identity], "after": wanted[identity]}
            )
    return tuple(operations)
