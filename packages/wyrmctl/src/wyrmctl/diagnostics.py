"""Operator diagnostics helpers."""

from __future__ import annotations

from typing import Any

SENSITIVE_ENV = ("NPM_SECRET", "NPM_IDENTITY", "NPM_BASE_URL", "NPM_TIMEOUT_S")


def redact_value(value: Any) -> str | None:
    """Return a display-safe value."""

    if value is None:
        return None
    text = str(value)
    if not text:
        return ""
    return "***"


def environment_report(env: dict[str, str]) -> dict[str, Any]:
    """Build a redacted environment diagnostic payload."""

    return {key: {"set": key in env and bool(env[key]), "value": redact_value(env.get(key))} for key in SENSITIVE_ENV}


def doctor_report(*, args: Any, health: dict[str, Any] | None, capabilities: dict[str, Any] | None) -> dict[str, Any]:
    """Build a machine-readable doctor report."""

    missing = [name for name in ("base_url", "identity", "secret") if not getattr(args, name, None)]
    return {
        "ok": not missing and health is not None and capabilities is not None,
        "config": {
            "base_url": bool(getattr(args, "base_url", None)),
            "identity": bool(getattr(args, "identity", None)),
            "secret": bool(getattr(args, "secret", None)),
            "missing": missing,
        },
        "api": {"reachable": health is not None, "health": health},
        "capabilities": capabilities,
    }
