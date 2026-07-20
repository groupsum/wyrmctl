"""Lockfile command handlers."""

import json
from pathlib import Path
from typing import Any

import yaml

from wyrmctl.lockfile import check_lock
from wyrmctl.output import command_result


def lock_check(expected_path: str, actual_path: str) -> dict[str, Any]:
    expected = _read(expected_path)
    actual = _read(actual_path)
    result = check_lock(expected, actual)
    return command_result(
        ok=result.ok,
        code="LOCK_MATCH" if result.ok else "LOCK_MISMATCH",
        data={"differences": list(result.differences)},
    )


def _read(path: str) -> dict[str, Any]:
    source = Path(path)
    value = (
        json.loads(source.read_text(encoding="utf-8"))
        if source.suffix == ".json"
        else yaml.safe_load(source.read_text(encoding="utf-8"))
    )
    if not isinstance(value, dict):
        raise ValueError(f"lockfile must contain an object: {source}")
    return value
