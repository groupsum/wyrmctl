"""Configuration loading for the GoDaddy DNS provider."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class GoDaddyConfig:
    """GoDaddy API configuration."""

    api_key: str
    api_secret: str
    api_base_url: str = "https://api.godaddy.com"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> GoDaddyConfig:
        values = os.environ if env is None else env
        required = {"api_key": values.get("GODADDY_API_KEY"), "api_secret": values.get("GODADDY_API_SECRET")}
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"missing GoDaddy config: {', '.join(missing)}")
        return cls(
            api_key=str(required["api_key"]),
            api_secret=str(required["api_secret"]),
            api_base_url=values.get("GODADDY_API_BASE_URL", "https://api.godaddy.com"),
        )

    def redacted(self) -> dict[str, str | bool]:
        return {"api_key": bool(self.api_key), "api_secret": bool(self.api_secret), "api_base_url": self.api_base_url}
