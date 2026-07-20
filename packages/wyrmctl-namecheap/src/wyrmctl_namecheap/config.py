"""Configuration loading for the Namecheap DNS provider."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class NamecheapConfig:
    """Namecheap API configuration."""

    api_user: str
    api_key: str
    username: str
    client_ip: str
    api_base_url: str = "https://api.namecheap.com/xml.response"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> NamecheapConfig:
        values = os.environ if env is None else env
        required = {
            "api_user": values.get("NAMECHEAP_API_USER"),
            "api_key": values.get("NAMECHEAP_API_KEY"),
            "username": values.get("NAMECHEAP_USERNAME"),
            "client_ip": values.get("NAMECHEAP_CLIENT_IP"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"missing Namecheap config: {', '.join(missing)}")
        return cls(
            api_user=str(required["api_user"]),
            api_key=str(required["api_key"]),
            username=str(required["username"]),
            client_ip=str(required["client_ip"]),
            api_base_url=values.get("NAMECHEAP_API_BASE_URL", "https://api.namecheap.com/xml.response"),
        )

    def redacted(self) -> dict[str, str | bool]:
        return {
            "api_user": bool(self.api_user),
            "api_key": bool(self.api_key),
            "username": bool(self.username),
            "client_ip": bool(self.client_ip),
            "api_base_url": self.api_base_url,
        }
