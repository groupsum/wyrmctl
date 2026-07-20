"""CLI output formatting."""

from __future__ import annotations

import json
import sys
from typing import Any

from wyrmctl.planner import Plan
from wyrmctl.profile import current_profile


def command_result(
    *,
    ok: bool,
    code: str,
    data: Any = None,
    mutated: bool = False,
    retryable: bool = False,
) -> dict[str, Any]:
    """Build the stable machine-readable command envelope."""

    return {
        "apiVersion": current_profile().api_version,
        "kind": "CommandResult",
        "schemaVersion": 1,
        "ok": ok,
        "code": code,
        "mutated": mutated,
        "retryable": retryable,
        "data": data,
    }


def write_output(output: str, payload: Any, text: str) -> None:
    """Write JSON or text output to stdout."""

    if output == "json":
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")


def write_error(output: str, code: str, message: str, **extra: Any) -> None:
    """Write JSON or text error output to stderr."""

    if output == "json":
        payload = {"ok": False, "error": {"code": code, "message": message} | extra}
        sys.stderr.write(json.dumps(payload, indent=2, sort_keys=True))
        sys.stderr.write("\n")
    else:
        detail = ""
        if extra:
            detail = " " + " ".join(f"{key}={value!r}" for key, value in sorted(extra.items()))
        sys.stderr.write(f"{code}: {message}{detail}\n")


def format_plan_text(plan: Plan) -> str:
    """Format a plan for humans."""

    payload = plan.to_dict()
    lines = [f"plan ok: {str(plan.ok).lower()}", f"existing: {payload['existing_count']}"]
    for key, value in payload["summary"].items():
        lines.append(f"{key}: {value}")
    for operation in plan.operations:
        rid = operation.resource_id or "-"
        lines.append(f"  {operation.action.value:<6} {operation.kind.value:<12} {rid} {operation.reason}")
        for field, values in operation.diff.items():
            lines.append(f"    ~ {field}: {values.get('actual')!r} -> {values.get('desired')!r}")
    for conflict in plan.conflicts:
        lines.append(f"  ! {conflict.code}: {conflict.message}")
    return "\n".join(lines)
