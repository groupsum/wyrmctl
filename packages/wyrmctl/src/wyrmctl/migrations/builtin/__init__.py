"""Built-in migration graph registrations."""

from __future__ import annotations

from typing import Any

from wyrmctl.migrations.builtin.desired_state_v1_v2 import migrate as desired_v1_v2
from wyrmctl.migrations.builtin.desired_state_v1_v2 import reverse as desired_v2_v1
from wyrmctl.migrations.builtin.desired_state_v2_v3 import migrate as desired_v2_v3
from wyrmctl.migrations.builtin.desired_state_v2_v3 import reverse as desired_v3_v2
from wyrmctl.migrations.graph import MigrationGraph, MigrationStep
from wyrmctl.profile import current_profile


def _legacy_v0_v1(document: dict[str, Any]) -> dict[str, Any]:
    out = dict(document)
    for key in (
        "proxy_hosts",
        "certificates",
        "access_lists",
        "redirection_hosts",
        "dead_hosts",
        "streams",
        "users",
        "settings",
    ):
        out.setdefault(key, [])
    out["apiVersion"] = current_profile().api_version
    out["schemaVersion"] = 1
    return out


def build_migration_graph() -> MigrationGraph:
    graph = MigrationGraph()
    graph.register(MigrationStep("DesiredState", 0, 1, _legacy_v0_v1))
    graph.register(MigrationStep("DesiredState", 1, 2, desired_v1_v2, desired_v2_v1))
    graph.register(MigrationStep("DesiredState", 2, 3, desired_v2_v3, desired_v3_v2))
    return graph


BUILTIN_MIGRATIONS = build_migration_graph()
