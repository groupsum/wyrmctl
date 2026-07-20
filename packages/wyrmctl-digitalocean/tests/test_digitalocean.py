from __future__ import annotations

import pytest

from wyrmctl_digitalocean.client import DigitalOceanClient
from wyrmctl_digitalocean.config import DigitalOceanConfig
from wyrmctl_digitalocean.errors import DigitalOceanError
from wyrmctl_digitalocean.models import DigitalOceanRecord
from wyrmctl_digitalocean.provider import DigitalOceanDnsProvider


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


def _config() -> DigitalOceanConfig:
    return DigitalOceanConfig(token="token", api_base_url="https://do.test")


def test_config_from_env_and_redaction() -> None:
    config = DigitalOceanConfig.from_env({"DIGITALOCEAN_TOKEN": "token"})

    assert config.redacted()["token"] is True
    assert config.api_base_url == "https://api.digitalocean.com"


def test_config_requires_token() -> None:
    with pytest.raises(ValueError, match="missing DigitalOcean config"):
        DigitalOceanConfig.from_env({})


def test_client_lists_zones_and_records() -> None:
    client = DigitalOceanClient(_config())
    session = FakeSession(
        [
            FakeResponse(200, {"domains": [{"name": "Example.com."}]}),
            FakeResponse(
                200,
                {"domain_records": [{"id": 1, "type": "A", "name": "www", "data": "192.0.2.10", "ttl": 300}]},
            ),
        ]
    )
    client.session = session  # type: ignore[assignment]

    assert client.zones() == ("example.com",)
    assert client.records("Example.com.")[0].to_dict()["value"] == "192.0.2.10"
    assert session.calls[1]["url"] == "https://do.test/v2/domains/example.com/records"


def test_client_creates_updates_and_deletes_records() -> None:
    client = DigitalOceanClient(_config())
    session = FakeSession(
        [
            FakeResponse(
                201, {"domain_record": {"id": 10, "type": "CNAME", "name": "app", "data": "target.example.net"}}
            ),
            FakeResponse(200, {"domain_record": {"id": 10, "type": "A", "name": "app", "data": "192.0.2.10"}}),
            FakeResponse(204),
        ]
    )
    client.session = session  # type: ignore[assignment]

    created = client.create_record("example.com", type="CNAME", name="app", value="target.example.net", ttl=300)
    updated = client.update_record("example.com", 10, type="A", name="app", value="192.0.2.10")
    client.delete_record("example.com", 10)

    assert created.type == "CNAME"
    assert updated.value == "192.0.2.10"
    assert session.calls[0]["json"] == {"type": "CNAME", "name": "app", "data": "target.example.net", "ttl": 300}
    assert session.calls[2]["method"] == "DELETE"


def test_client_reports_http_json_and_api_errors() -> None:
    client = DigitalOceanClient(_config())
    client.session = FakeSession([FakeResponse(500, {})])  # type: ignore[assignment]
    with pytest.raises(DigitalOceanError, match="HTTP 500"):
        client.zones()

    client.session = FakeSession([FakeResponse(200, ValueError("bad"))])  # type: ignore[assignment]
    with pytest.raises(DigitalOceanError, match="invalid JSON"):
        client.zones()

    client.session = FakeSession([FakeResponse(200, {"id": "unauthorized", "message": "denied"})])  # type: ignore[assignment]
    with pytest.raises(DigitalOceanError, match="denied"):
        client.zones()


def test_provider_returns_record_dicts() -> None:
    class Client:
        def zones(self):
            return ("example.com",)

        def records(self, zone: str):
            assert zone == "example.com"
            return (DigitalOceanRecord.from_mapping({"type": "A", "name": "@", "data": "192.0.2.10"}),)

    provider = DigitalOceanDnsProvider(Client())  # type: ignore[arg-type]

    assert provider.zones() == ("example.com",)
    assert provider.records("example.com")[0]["value"] == "192.0.2.10"


def test_provider_applies_supported_record_types() -> None:
    class Client:
        def __init__(self) -> None:
            self.created = []

        def zones(self):
            return ("example.com",)

        def records(self, zone: str):
            assert zone == "example.com"
            return ()

        def create_record(self, zone: str, **payload):
            self.created.append((zone, payload))

    client = Client()
    provider = DigitalOceanDnsProvider(client)  # type: ignore[arg-type]
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

    assert [item[1]["type"] for item in client.created] == ["A", "AAAA", "CNAME", "TXT", "MX", "SRV", "CAA"]
    assert next(item for _, item in client.created if item["type"] == "MX")["priority"] == 10
