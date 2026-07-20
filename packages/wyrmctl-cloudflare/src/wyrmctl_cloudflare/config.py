"""Configuration loading for the Cloudflare DNS provider."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class CloudflareConfig:
    """Cloudflare API configuration."""

    api_token: str
    api_base_url: str = "https://api.cloudflare.com/client/v4"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> CloudflareConfig:
        values = os.environ if env is None else env
        api_token = values.get("CLOUDFLARE_API_TOKEN")
        if not api_token:
            raise ValueError("missing Cloudflare config: api_token")
        return cls(
            api_token=api_token,
            api_base_url=values.get("CLOUDFLARE_API_BASE_URL", "https://api.cloudflare.com/client/v4"),
        )

    def redacted(self) -> dict[str, str | bool]:
        return {"api_token": bool(self.api_token), "api_base_url": self.api_base_url}
