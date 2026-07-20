"""Configuration loading for the Route 53 DNS provider."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class Route53Config:
    """Route 53 API configuration."""

    profile: str | None = None
    region_name: str | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Route53Config:
        values = os.environ if env is None else env
        return cls(
            profile=values.get("ROUTE53_PROFILE") or values.get("AWS_PROFILE") or None,
            region_name=values.get("AWS_REGION") or values.get("AWS_DEFAULT_REGION") or None,
        )

    def redacted(self) -> dict[str, str | bool | None]:
        return {"profile": self.profile, "region_name": self.region_name, "aws_credentials": "standard-chain"}
