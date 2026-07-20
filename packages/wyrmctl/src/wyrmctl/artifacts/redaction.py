"""Recursive artifact and automation-output redaction."""

from __future__ import annotations

from typing import Any

DEFAULT_SECRET_FIELDS = frozenset({"secret", "password", "token", "api_key", "apikey", "authorization", "private_key"})


def redact_artifact(value: Any, *, secret_fields: frozenset[str] = DEFAULT_SECRET_FIELDS) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "<redacted>"
            if str(key).lower() in secret_fields
            else redact_artifact(item, secret_fields=secret_fields)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_artifact(item, secret_fields=secret_fields) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_artifact(item, secret_fields=secret_fields) for item in value)
    return value
