"""Certificate issuance dedupe and cooldown safety helpers."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from wyrmctl.errors import CertificateSafetyError
from wyrmctl.models import DesiredCertificate
from wyrmctl.profile import current_profile


def certificate_issuance_key(certificate: DesiredCertificate) -> str:
    """Return the normalized provider/domain-set key for certificate issuance safety."""

    provider = str(certificate.to_payload().get("provider") or certificate.certificate_type).strip().lower()
    return f"{provider}|{'|'.join(certificate.domain_names)}"


class CertificateIssuanceGuard:
    """Persist local anti-spam state for certificate issuance attempts."""

    def __init__(
        self,
        *,
        state_file: str | Path | None = None,
        cooldown_seconds: int | None = None,
        inflight_ttl_seconds: int | None = None,
    ) -> None:
        self.state_file = Path(state_file) if state_file is not None else _default_state_file()
        self.cooldown_seconds = (
            cooldown_seconds
            if cooldown_seconds is not None
            else int(os.getenv("NPMCTL_CERTIFICATE_COOLDOWN_SECONDS", "900"))
        )
        self.inflight_ttl_seconds = (
            inflight_ttl_seconds
            if inflight_ttl_seconds is not None
            else int(os.getenv("NPMCTL_CERTIFICATE_INFLIGHT_TTL_SECONDS", "900"))
        )

    def begin(self, certificate: DesiredCertificate) -> str:
        """Reserve an issuance slot or raise a structured safety conflict."""

        key = certificate_issuance_key(certificate)
        now = time.time()
        state = self._read()
        record = state.get(key, {})
        inflight_until = float(record.get("inflight_until", 0))
        cooldown_until = float(record.get("cooldown_until", 0))
        if inflight_until > now:
            raise CertificateSafetyError(
                "certificate_issuance_deduplicated",
                "certificate issuance is already in flight for the same provider and domain set",
                suggested_action="wait for the in-flight issuance to finish before retrying",
                details={
                    "issuance_key": key,
                    "provider": str(certificate.to_payload().get("provider") or certificate.certificate_type),
                    "domain_names": list(certificate.domain_names),
                    "retry_at": _isoformat(inflight_until),
                },
            )
        if cooldown_until > now:
            raise CertificateSafetyError(
                "certificate_recent_failure_cooldown",
                "certificate issuance is in a cooldown window after a recent failure",
                suggested_action="wait for the cooldown window to expire or clear the stale state before retrying",
                details={
                    "issuance_key": key,
                    "provider": str(certificate.to_payload().get("provider") or certificate.certificate_type),
                    "domain_names": list(certificate.domain_names),
                    "retry_at": _isoformat(cooldown_until),
                    "last_error_code": record.get("last_error_code"),
                },
            )
        state[key] = {
            "provider": str(certificate.to_payload().get("provider") or certificate.certificate_type),
            "domain_names": list(certificate.domain_names),
            "inflight_until": now + self.inflight_ttl_seconds,
            "cooldown_until": 0,
            "last_error_code": record.get("last_error_code"),
        }
        self._write(state)
        return key

    def succeed(self, key: str) -> None:
        """Clear any anti-spam state after a successful issuance mutation."""

        state = self._read()
        if key in state:
            del state[key]
            self._write(state)

    def fail(self, key: str, *, error_code: str) -> None:
        """Record a failure and start the cooldown window."""

        now = time.time()
        state = self._read()
        record = state.get(key, {})
        record.update(
            {
                "inflight_until": 0,
                "cooldown_until": now + self.cooldown_seconds,
                "last_error_code": error_code,
            }
        )
        state[key] = record
        self._write(state)

    def _read(self) -> dict[str, dict[str, Any]]:
        if not self.state_file.is_file():
            return {}
        try:
            payload = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(payload, dict):
            return {}
        return {str(key): value for key, value in payload.items() if isinstance(value, dict)}

    def _write(self, payload: dict[str, dict[str, Any]]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _default_state_file() -> Path:
    base = os.getenv("NPMCTL_CERTIFICATE_STATE_DIR")
    if base:
        return Path(base) / "certificate-issuance-state.json"
    return Path(tempfile.gettempdir()) / current_profile().name / "certificate-issuance-state.json"


def _isoformat(timestamp: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))
