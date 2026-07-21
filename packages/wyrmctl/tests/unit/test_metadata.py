from __future__ import annotations

import pytest

from wyrmctl.errors import MetadataError
from wyrmctl.metadata import MANAGED_BY, identity_from_meta, validate_metadata
from wyrmctl.profile import NPMCTL_PROFILE, WYRMCTL_PROFILE, current_profile, set_profile, use_profile


def test_validate_metadata_accepts_required_identity() -> None:
    meta = {"managed_by": MANAGED_BY, "owner": "team-a", "resource_id": "proxy.app"}
    assert validate_metadata(meta, path="x") == meta
    assert identity_from_meta(meta).resource_id == "proxy.app"


@pytest.mark.parametrize(
    "meta",
    [
        None,
        [],
        {"managed_by": "other"},
        {"managed_by": MANAGED_BY},
        {"managed_by": MANAGED_BY, "owner": "bad space", "resource_id": "x"},
    ],
)
def test_validate_metadata_rejects_invalid(meta) -> None:
    with pytest.raises(MetadataError):
        validate_metadata(meta, path="x")


def test_identity_from_meta_treats_unmanaged_as_none() -> None:
    assert identity_from_meta({}) is None
    assert identity_from_meta({"managed_by": "terraform", "owner": "x", "resource_id": "y"}) is None


def test_profile_context_restores_native_identity() -> None:
    set_profile(WYRMCTL_PROFILE)
    assert current_profile() is WYRMCTL_PROFILE
    with use_profile(NPMCTL_PROFILE):
        assert current_profile() is NPMCTL_PROFILE
    assert current_profile() is WYRMCTL_PROFILE
