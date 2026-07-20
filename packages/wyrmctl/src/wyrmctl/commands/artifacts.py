"""Execution artifact command handlers."""

from typing import Any

from wyrmctl.artifacts import artifact_digest, read_artifact
from wyrmctl.output import command_result


def artifact_inspect_command(path: str, *, strict: bool = False) -> dict[str, Any]:
    artifact = read_artifact(path, strict=strict)
    return command_result(
        ok=True,
        code="ARTIFACT_VALID",
        data={
            "kind": artifact["kind"],
            "schemaVersion": artifact["schemaVersion"],
            "digest": artifact_digest(artifact),
            "signed": "signature" in artifact,
        },
    )


def artifact_digest_command(path: str) -> dict[str, Any]:
    artifact = read_artifact(path)
    return command_result(ok=True, code="ARTIFACT_DIGESTED", data={"digest": artifact_digest(artifact)})
