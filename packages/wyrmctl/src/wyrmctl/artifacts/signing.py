"""Optional Ed25519 signatures over canonical artifact digests."""

from __future__ import annotations

import base64
from dataclasses import replace
from typing import Any

from wyrmctl.artifacts.models import ArtifactSignature, PlanArtifact, utc_now
from wyrmctl.errors import ArtifactError


def sign_plan(artifact: PlanArtifact, *, key_id: str, private_key: Any) -> PlanArtifact:
    signature = private_key.sign(artifact.digest.encode("ascii"))
    envelope = ArtifactSignature("ed25519", key_id, base64.b64encode(signature).decode("ascii"), utc_now())
    return replace(artifact, signature=envelope)


def verify_plan(artifact: PlanArtifact, *, trusted_keys: dict[str, Any], require_signature: bool = True) -> None:
    envelope = artifact.signature
    if envelope is None:
        if require_signature:
            raise ArtifactError("SIGNATURE_REQUIRED", "plan artifact is unsigned")
        return
    if envelope.algorithm != "ed25519":
        raise ArtifactError("UNSUPPORTED_SIGNATURE", f"unsupported signature algorithm: {envelope.algorithm}")
    key = trusted_keys.get(envelope.key_id)
    if key is None:
        raise ArtifactError("UNTRUSTED_SIGNER", f"untrusted artifact signer: {envelope.key_id}")
    try:
        key.verify(base64.b64decode(envelope.value, validate=True), artifact.digest.encode("ascii"))
    except Exception as exc:
        raise ArtifactError("INVALID_SIGNATURE", "artifact signature validation failed") from exc
