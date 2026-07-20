"""Route 53 provider errors."""

from __future__ import annotations


class Route53Error(RuntimeError):
    """Raised when the Route 53 API returns an error."""
