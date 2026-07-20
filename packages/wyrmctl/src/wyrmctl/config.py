"""CLI configuration file support."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from wyrmctl.errors import ValidationError
from wyrmctl.profile import ToolProfile, current_profile

CONFIG_FIELDS = frozenset({"base_url", "identity", "secret", "timeout", "output"})


def load_config(path: str | None, *, profile: ToolProfile | None = None) -> dict[str, Any]:
    """Load wyrmctl TOML config values."""

    if not path:
        return {}
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
        import tomli as tomllib
    config_path = Path(path)
    try:
        parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValidationError(f"failed to read config file {config_path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ValidationError(f"failed to parse config file {config_path}: {exc}") from exc
    if not isinstance(parsed, dict):  # pragma: no cover - tomllib.loads always returns a dict
        raise ValidationError("config file must contain a TOML table")
    selected = profile or current_profile()
    raw = parsed.get(selected.config_section, parsed)
    if not isinstance(raw, dict):
        raise ValidationError(f"config file [{selected.config_section}] must be a table")
    return {key: raw[key] for key in CONFIG_FIELDS if key in raw}


def apply_config(args: Any, values: dict[str, Any]) -> None:
    """Fill unset argparse fields from config values."""

    for field_name, value in values.items():
        current = getattr(args, field_name, None)
        if current in (None, ""):
            setattr(args, field_name, value)
