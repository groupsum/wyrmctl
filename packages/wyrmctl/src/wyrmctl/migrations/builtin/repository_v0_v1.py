"""Legacy repository layout to NpmctlRepository schema 1."""

from __future__ import annotations

from wyrmctl.profile import current_profile

from typing import Any


def migrate(document: dict[str, Any]) -> dict[str, Any]:
    name = str(document.get("name") or "wyrmctl-repository")
    return {
        "apiVersion": current_profile().api_version,
        "kind": "NpmctlRepository",
        "schemaVersion": 1,
        "metadata": {"name": name},
        "spec": dict(document.get("spec") or {}),
    }
