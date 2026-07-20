from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from wyrmctl import cli
from wyrmctl.cli import EXIT_API, EXIT_CONFLICT, _default_certificate_mode, _parse_resource_kinds, main
from wyrmctl.client.base import _classify_api_error
from wyrmctl.errors import CertificateApiError, CertificateSafetyError
from wyrmctl.issuance import CertificateIssuanceGuard, certificate_issuance_key
from wyrmctl.models import DesiredCertificate, ResourceKind
from wyrmctl.output import write_error


def _certificate(resource_id: str = "cert.one") -> DesiredCertificate:
    return DesiredCertificate.from_mapping(
        {
            "name": "cert-one",
            "domain_names": ["app.example.com"],
            "meta": {"managed_by": "wyrmctl", "owner": "workload-a", "resource_id": resource_id},
            "api_payload": {"provider": "letsencrypt"},
        },
        path="cert",
    )


def test_certificate_issuance_guard_detects_inflight_and_cooldown(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "state.json"
    guard = CertificateIssuanceGuard(state_file=state_file, cooldown_seconds=30, inflight_ttl_seconds=30)
    certificate = _certificate()
    monkeypatch.setattr("wyrmctl.issuance.time.time", lambda: 1000.0)

    key = guard.begin(certificate)
    assert key == certificate_issuance_key(certificate)
    payload = json.loads(state_file.read_text(encoding="utf-8"))
    assert payload[key]["provider"] == "letsencrypt"

    with pytest.raises(CertificateSafetyError, match="already in flight"):
        guard.begin(certificate)

    guard.fail(key, error_code="certificate_api_error")
    with pytest.raises(CertificateSafetyError, match="cooldown window"):
        guard.begin(certificate)

    payload = json.loads(state_file.read_text(encoding="utf-8"))
    assert payload[key]["last_error_code"] == "certificate_api_error"

    monkeypatch.setattr("wyrmctl.issuance.time.time", lambda: 2000.0)
    key = guard.begin(certificate)
    guard.succeed(key)
    assert json.loads(state_file.read_text(encoding="utf-8")) == {}


def test_certificate_issuance_guard_handles_missing_and_invalid_state(tmp_path: Path) -> None:
    state_file = tmp_path / "invalid.json"
    state_file.write_text("{not-json", encoding="utf-8")
    guard = CertificateIssuanceGuard(state_file=state_file, cooldown_seconds=1, inflight_ttl_seconds=1)

    key = guard.begin(_certificate("cert.two"))

    assert key in json.loads(state_file.read_text(encoding="utf-8"))

    state_file.write_text("[]", encoding="utf-8")
    assert guard._read() == {}
    guard.succeed("missing")


def test_certificate_issuance_default_paths(monkeypatch) -> None:
    monkeypatch.setenv("NPMCTL_CERTIFICATE_STATE_DIR", "C:/custom-wyrmctl")
    guard = CertificateIssuanceGuard()
    assert guard.state_file == Path("C:/custom-wyrmctl") / "certificate-issuance-state.json"

    monkeypatch.delenv("NPMCTL_CERTIFICATE_STATE_DIR")
    monkeypatch.setenv("LOCALAPPDATA", "C:/Users/test/AppData/Local")
    assert (
        CertificateIssuanceGuard().state_file
        == Path(tempfile.gettempdir()) / "wyrmctl" / "certificate-issuance-state.json"
    )


def test_certificate_api_error_classification() -> None:
    lock = _classify_api_error("POST", "/nginx/certificates", 500, "Another instance of Certbot is already running.")
    assert isinstance(lock, CertificateApiError)
    assert lock.code == "certificate_lock_retryable"
    assert lock.retryable is True

    stale = _classify_api_error("PUT", "/nginx/certificates/1", 500, "No order for ID abc")
    assert isinstance(stale, CertificateApiError)
    assert stale.code == "certificate_order_stale"
    assert stale.retryable is False

    generic = _classify_api_error("GET", "/nginx/proxy-hosts", 500, "broken")
    assert generic.__class__.__name__ == "ApiError"


def test_cli_reports_structured_certificate_errors(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "wyrmctl.cli._dispatch",
        lambda _args, _parser: (_ for _ in ()).throw(
            CertificateApiError(
                "certificate_lock_retryable",
                "backend error",
                retryable=True,
                suggested_action="retry later",
                details={"http_status": 500},
            )
        ),
    )

    assert main(["--output", "json", "env"]) == EXIT_API
    payload = json.loads(capsys.readouterr().err)
    assert payload["error"]["code"] == "certificate_lock_retryable"
    assert payload["error"]["retryable"] is True
    assert payload["error"]["suggested_action"] == "retry later"


def test_cli_reports_structured_certificate_safety_conflicts(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "wyrmctl.cli._dispatch",
        lambda _args, _parser: (_ for _ in ()).throw(
            CertificateSafetyError(
                "certificate_recent_failure_cooldown",
                "cooldown active",
                suggested_action="wait",
                details={"retry_at": "2026-05-12T00:00:00Z"},
            )
        ),
    )

    assert main(["--output", "json", "env"]) == EXIT_CONFLICT
    payload = json.loads(capsys.readouterr().err)
    assert payload["error"]["code"] == "certificate_recent_failure_cooldown"
    assert payload["error"]["details"]["retry_at"] == "2026-05-12T00:00:00Z"


def test_cli_resource_scope_and_adopt_certificate_mode_helpers() -> None:
    args = type("Args", (), {"command": "adopt", "certificate_mode": "create"})()
    assert _default_certificate_mode(args) == "reuse"
    args.command = "apply"
    assert _default_certificate_mode(args) == "create"
    assert _parse_resource_kinds(["proxy_hosts", "certificates"]) == frozenset(
        {ResourceKind.PROXY_HOST, ResourceKind.CERTIFICATE}
    )
    assert _parse_resource_kinds(None) is None


def test_cli_plugin_registry_cache_helper_returns_cached_impl() -> None:
    original = cli._PLUGIN_REGISTRY_IMPL
    sentinel = object()
    cli._PLUGIN_REGISTRY_IMPL = sentinel
    try:
        assert cli._plugin_registry_cls() is sentinel
    finally:
        cli._PLUGIN_REGISTRY_IMPL = original


def test_text_error_output_includes_structured_details(capsys) -> None:
    write_error("text", "certificate_lock_retryable", "busy", retryable=True)
    assert "retryable=True" in capsys.readouterr().err
