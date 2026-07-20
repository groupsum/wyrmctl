"""Cloudflare provider errors."""

from __future__ import annotations


class CloudflareError(RuntimeError):
    """Raised when the Cloudflare API returns an error."""
