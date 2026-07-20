"""Versioned artifact encoding with atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from wyrmctl.contracts import BUILTIN_CONTRACTS, check_document, semantic_digest
from wyrmctl.errors import ArtifactError


def read_artifact(path: str | Path, *, strict: bool = False) -> dict[str, Any]:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
        value = json.loads(text) if source.suffix.lower() == ".json" else yaml.safe_load(text)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ArtifactError("ARTIFACT_READ_FAILED", f"failed to read artifact {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise ArtifactError("INVALID_ARTIFACT", "artifact must contain an object")
    check_document(value, BUILTIN_CONTRACTS, strict=strict)
    return value


def write_artifact(path: str | Path, value: dict[str, Any]) -> Path:
    check_document(value, BUILTIN_CONTRACTS)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = (
        json.dumps(value, indent=2, sort_keys=True) + "\n"
        if target.suffix.lower() == ".json"
        else yaml.safe_dump(value, sort_keys=False)
    )
    handle, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise
    return target


def artifact_digest(value: dict[str, Any]) -> str:
    unsigned = {key: item for key, item in value.items() if key != "signature"}
    return semantic_digest(unsigned)
