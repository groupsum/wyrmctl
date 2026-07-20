"""Non-mutating live-state import command handler."""

from typing import Any

from wyrmctl.migrations.import_live import classify_live_resources
from wyrmctl.output import command_result


def import_live(live: list[dict[str, Any]], desired: list[dict[str, Any]], *, owner: str) -> dict[str, Any]:
    classifications = classify_live_resources(live, desired, owner=owner)
    return command_result(
        ok=True,
        code="LIVE_STATE_CLASSIFIED",
        data={
            "classifications": [
                {
                    "identity": item.identity,
                    "classification": item.classification,
                    "desired": item.desired,
                    "observed": item.observed,
                }
                for item in classifications
            ]
        },
    )
