"""Runtime identity profiles for native and compatibility executions."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True, slots=True)
class ToolProfile:
    """Observable identity selected by a client distribution."""

    name: str
    api_version: str
    managed_by: str
    config_section: str
    entry_point_group: str
    repository_dir: str


WYRMCTL_PROFILE = ToolProfile(
    name="wyrmctl",
    api_version="wyrmctl.com/v1",
    managed_by="wyrmctl",
    config_section="wyrmctl",
    entry_point_group="wyrmctl.dns_providers",
    repository_dir=".wyrmctl",
)

NPMCTL_PROFILE = ToolProfile(
    name="npmctl",
    api_version="npmctl.com/v1",
    managed_by="npmctl",
    config_section="npmctl",
    entry_point_group="npmctl.dns_providers",
    repository_dir=".npmctl",
)

_active_profile: ContextVar[ToolProfile] = ContextVar("wyrmctl_profile", default=WYRMCTL_PROFILE)


def current_profile() -> ToolProfile:
    """Return the profile active for the current execution context."""

    return _active_profile.get()


def set_profile(profile: ToolProfile) -> None:
    """Set the process context profile for compatibility facade imports."""

    _active_profile.set(profile)


@contextmanager
def use_profile(profile: ToolProfile) -> Iterator[None]:
    """Temporarily select a profile for nested library and CLI operations."""

    token = _active_profile.set(profile)
    try:
        yield
    finally:
        _active_profile.reset(token)
