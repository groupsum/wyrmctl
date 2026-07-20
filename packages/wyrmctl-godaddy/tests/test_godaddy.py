from __future__ import annotations

import pytest

from wyrmctl_godaddy.client import GoDaddyClient
from wyrmctl_godaddy.config import GoDaddyConfig
from wyrmctl_godaddy.errors import GoDaddyError
from wyrmctl_godaddy.models import GoDaddyRecord
from wyrmctl_godaddy.provider import GoDaddyDnsProvider


class FakeResponse:
    def __init__(self, status_code: int, payload: object | None = None) -> None:
        self.status_code = status_code
        self.payload = payload

    def json(self) -> object:
        if isinstance(self.payload, BaseException):
            raise self.payload
        return self.payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs) -> FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


def _config() -> GoDaddyConfig:
    return GoDaddyConfig(api_key="key", api_secret="secret", api_base_url="https://godaddy.test")


def test_config_from_env_and_redaction() -> None:
    config = GoDaddyConfig.from_env({"GODADDY_API_KEY": "key", "GODADDY_API_SECRET": "secret"})

    assert config.redacted()["api_key"] is True
    assert config.redacted()["api_secret"] is True
    assert config.api_base_url == "https://api.godaddy.com"


def test_config_requires_credentials() -> None:
    with pytest.raises(ValueError, match="missing GoDaddy config"):
        GoDaddyConfig.from_env({})


def test_client_lists_zones_and_records() -> None:
    client = GoDaddyClient(_config())
    session = FakeSession(
        [
            FakeResponse(200, [{"domain": "Example.com."}]),
            FakeResponse(200, [{"type": "A", "name": "www", "data": "192.0.2.10", "ttl": 600}]),
        ]
    )
    client.session = session  # type: ignore[assignment]

    assert client.zones() == ("example.com",)
    assert client.records("Example.com.")[0].to_dict()["value"] == "192.0.2.10"
    assert session.calls[1]["url"] == "https://godaddy.test/v1/domains/example.com/records"


def test_client_reads_replaces_creates_and_deletes_record_sets() -> None:
    client = GoDaddyClient(_config())
    session = FakeSession(
        [
            FakeResponse(200, [{"data": "192.0.2.10", "ttl": 600}]),
            FakeResponse(200, []),
            FakeResponse(200, []),
            FakeResponse(204),
        ]
    )
    client.session = session  # type: ignore[assignment]

    records = client.records_by_name("example.com", type="A", name="www")
    client.replace_records(
        "example.com", type="CNAME", name="app", records=[{"data": "target.example.net", "ttl": 600}]
    )
    client.create_record("example.com", type="A", name="www", value="192.0.2.11", ttl=600)
    client.delete_records("example.com", type="A", name="www")

    assert records[0].value == "192.0.2.10"
    assert session.calls[0]["url"] == "https://godaddy.test/v1/domains/example.com/records/A/www"
    assert session.calls[1]["json"] == [{"data": "target.example.net", "ttl": 600}]
    assert session.calls[2]["json"] == [{"data": "192.0.2.11", "ttl": 600}]
    assert session.calls[3]["method"] == "DELETE"


def test_client_reports_http_and_json_errors() -> None:
    client = GoDaddyClient(_config())
    client.session = FakeSession([FakeResponse(403, {})])  # type: ignore[assignment]
    with pytest.raises(GoDaddyError, match="HTTP 403"):
        client.zones()

    client.session = FakeSession([FakeResponse(200, ValueError("bad"))])  # type: ignore[assignment]
    with pytest.raises(GoDaddyError, match="invalid JSON"):
        client.zones()


def test_provider_returns_record_dicts() -> None:
    class Client:
        def zones(self):
            return ("example.com",)

        def records(self, zone: str):
            assert zone == "example.com"
            return (GoDaddyRecord.from_mapping({"type": "A", "name": "@", "data": "192.0.2.10"}),)

    provider = GoDaddyDnsProvider(Client())  # type: ignore[arg-type]

    assert provider.zones() == ("example.com",)
    assert provider.records("example.com")[0]["value"] == "192.0.2.10"


def test_provider_applies_supported_record_types() -> None:
    class Client:
        def __init__(self) -> None:
            self.replaced = []

        def zones(self):
            return ("example.com",)

        def records(self, zone: str):
            assert zone == "example.com"
            return ()

        def replace_records(self, zone: str, **payload):
            self.replaced.append((zone, payload))

    client = Client()
    provider = GoDaddyDnsProvider(client)  # type: ignore[arg-type]
    records = tuple(
        {"name": f"r{idx}", "type": record_type, "value": value, "ttl": 300, **extra}
        for idx, (record_type, value, extra) in enumerate(
            [
                ("A", "192.0.2.10", {}),
                ("AAAA", "2001:db8::1", {}),
                ("CNAME", "target.example.net", {}),
                ("TXT", "hello", {}),
                ("MX", "mail.example.com", {"priority": 10}),
                ("SRV", "10 20 5060 sip.example.com", {}),
                ("CAA", '0 issue "letsencrypt.org"', {}),
            ],
            start=1,
        )
    )

    provider.apply_records("example.com", records)

    assert [item[1]["type"] for item in client.replaced] == ["A", "AAAA", "CNAME", "TXT", "MX", "SRV", "CAA"]
    assert next(item for _, item in client.replaced if item["type"] == "MX")["records"][0]["priority"] == 10
