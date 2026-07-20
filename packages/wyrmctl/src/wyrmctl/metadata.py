"""Managed metadata validation and ownership helpers."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from wyrmctl.errors import MetadataError
from wyrmctl.profile import current_profile

MANAGED_BY = current_profile().managed_by
_RESOURCE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,191}$")
_OWNER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")


@dataclass(frozen=True, slots=True)
class ManagedIdentity:
    """Stable owner-scoped resource identity."""

    owner: str
    resource_id: str

    def to_dict(self) -> dict[str, str]:
        """Serialize the identity."""

        return {"owner": self.owner, "resource_id": self.resource_id}


def validate_metadata(meta: Any, *, path: str) -> dict[str, Any]:
    """Validate metadata for a desired managed resource.

    Every desired resource must carry metadata. Existing resources may be unmanaged,
    but desired resources must declare the controlling owner and stable resource id.
    """

    if not isinstance(meta, Mapping):
        raise MetadataError(f"{path}.meta must be an object")
    normalized = dict(meta)
    managed_by = normalized.get("managed_by")
    owner = normalized.get("owner")
    resource_id = normalized.get("resource_id")
    if managed_by != current_profile().managed_by:
        raise MetadataError(f"{path}.meta.managed_by must be {current_profile().managed_by!r}")
    if not isinstance(owner, str) or not _OWNER_RE.fullmatch(owner):
        raise MetadataError(f"{path}.meta.owner must be a non-empty stable owner token")
    if not isinstance(resource_id, str) or not _RESOURCE_ID_RE.fullmatch(resource_id):
        raise MetadataError(f"{path}.meta.resource_id must be a non-empty stable resource id")
    return normalized


def identity_from_meta(meta: Any) -> ManagedIdentity | None:
    """Return wyrmctl identity from existing API metadata, if present and valid.

    Invalid or absent wyrmctl metadata is treated as unmanaged by the planner; desired
    resources still use validate_metadata and fail hard.
    """

    if not isinstance(meta, Mapping):
        return None
    if meta.get("managed_by") != current_profile().managed_by:
        return None
    owner = meta.get("owner")
    resource_id = meta.get("resource_id")
    if not isinstance(owner, str) or not isinstance(resource_id, str):
        return None
    if not _OWNER_RE.fullmatch(owner) or not _RESOURCE_ID_RE.fullmatch(resource_id):
        return None
    return ManagedIdentity(owner=owner, resource_id=resource_id)


def merge_managed_meta(existing: Any, desired: Mapping[str, Any]) -> dict[str, Any]:
    """Merge metadata while ensuring desired ownership keys win."""

    base = dict(existing) if isinstance(existing, Mapping) else {}
    base.update(dict(desired))
    validate_metadata(base, path="merged")
    return base
