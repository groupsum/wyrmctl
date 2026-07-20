"""Configuration loading for the DigitalOcean DNS provider."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class DigitalOceanConfig:
    """DigitalOcean API configuration."""

    token: str
    api_base_url: str = "https://api.digitalocean.com"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> DigitalOceanConfig:
        values = os.environ if env is None else env
        token = values.get("DIGITALOCEAN_TOKEN")
        if not token:
            raise ValueError("missing DigitalOcean config: token")
        return cls(token=token, api_base_url=values.get("DIGITALOCEAN_API_BASE_URL", "https://api.digitalocean.com"))

    def redacted(self) -> dict[str, str | bool]:
        return {"token": bool(self.token), "api_base_url": self.api_base_url}
