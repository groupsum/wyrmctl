from __future__ import annotations

import pytest

from wyrmctl_cloudflare.client import CloudflareClient
from wyrmctl_cloudflare.config import CloudflareConfig
from wyrmctl_cloudflare.errors import CloudflareError
from wyrmctl_cloudflare.models import CloudflareRecord
from wyrmctl_cloudflare.provider import CloudflareDnsProvider


class FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
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


def _config() -> CloudflareConfig:
    return CloudflareConfig(api_token="token", api_base_url="https://cloudflare.test/client/v4")


def test_config_from_env_and_redaction() -> None:
    config = CloudflareConfig.from_env({"CLOUDFLARE_API_TOKEN": "token"})

    assert config.redacted()["api_token"] is True
    assert config.api_base_url == "https://api.cloudflare.com/client/v4"


def test_config_requires_token() -> None:
    with pytest.raises(ValueError, match="missing Cloudflare config"):
        CloudflareConfig.from_env({})


def test_client_lists_zones_and_records() -> None:
    client = CloudflareClient(_config())
    session = FakeSession(
        [
            FakeResponse(200, {"success": True, "result": [{"id": "zone-1", "name": "Example.com."}]}),
            FakeResponse(200, {"success": True, "result": [{"id": "zone-1", "name": "Example.com."}]}),
            FakeResponse(
                200,
                {
                    "success": True,
                    "result": [
                        {"id": "rec-1", "name": "www.example.com.", "type": "A", "content": "192.0.2.10", "ttl": 300}
                    ],
                },
            ),
        ]
    )
    client.session = session  # type: ignore[assignment]

    assert client.zones() == ("example.com",)
    assert client.records("example.com")[0].to_dict()["value"] == "192.0.2.10"
    assert session.calls[0]["method"] == "GET"
    assert session.calls[2]["url"] == "https://cloudflare.test/client/v4/zones/zone-1/dns_records"


def test_client_creates_patches_and_deletes_records() -> None:
    client = CloudflareClient(_config())
    session = FakeSession(
        [
            FakeResponse(200, {"success": True, "result": [{"id": "zone-1", "name": "example.com"}]}),
            FakeResponse(
                200,
                {
                    "success": True,
                    "result": {"id": "rec-1", "name": "www.example.com", "type": "A", "content": "192.0.2.10"},
                },
            ),
            FakeResponse(200, {"success": True, "result": [{"id": "zone-1", "name": "example.com"}]}),
            FakeResponse(
                200,
                {
                    "success": True,
                    "result": {"id": "rec-1", "name": "www.example.com", "type": "A", "content": "192.0.2.11"},
                },
            ),
            FakeResponse(200, {"success": True, "result": [{"id": "zone-1", "name": "example.com"}]}),
            FakeResponse(200, {"success": True, "result": {"id": "rec-1"}}),
        ]
    )
    client.session = session  # type: ignore[assignment]

    created = client.create_record("example.com", type="A", name="www", value="192.0.2.10", ttl=300, proxied=False)
    patched = client.patch_record("example.com", "rec-1", value="192.0.2.11")
    deleted = client.delete_record("example.com", "rec-1")

    assert created.value == "192.0.2.10"
    assert patched.value == "192.0.2.11"
    assert deleted == "rec-1"
    assert session.calls[1]["json"] == {
        "type": "A",
        "name": "www",
        "content": "192.0.2.10",
        "ttl": 300,
        "proxied": False,
    }
    assert session.calls[3]["json"] == {"content": "192.0.2.11"}


def test_client_reports_http_json_api_and_missing_zone_errors() -> None:
    client = CloudflareClient(_config())
    client.session = FakeSession([FakeResponse(500, {})])  # type: ignore[assignment]
    with pytest.raises(CloudflareError, match="HTTP 500"):
        client.zones()

    client.session = FakeSession([FakeResponse(200, ValueError("bad"))])  # type: ignore[assignment]
    with pytest.raises(CloudflareError, match="invalid JSON"):
        client.zones()

    client.session = FakeSession([FakeResponse(200, {"success": False, "errors": [{"message": "denied"}]})])  # type: ignore[assignment]
    with pytest.raises(CloudflareError, match="denied"):
        client.zones()

    client.session = FakeSession([FakeResponse(200, {"success": True, "result": []})])  # type: ignore[assignment]
    with pytest.raises(CloudflareError, match="zone not found"):
        client.records("missing.example")


def test_provider_returns_record_dicts() -> None:
    class Client:
        def zones(self):
            return ("example.com",)

        def records(self, zone: str):
            assert zone == "example.com"
            return (
                CloudflareRecord.from_mapping(
                    {"name": "www.example.com", "type": "CNAME", "content": "target.example.net"}
                ),
            )

    provider = CloudflareDnsProvider(Client())  # type: ignore[arg-type]

    assert provider.zones() == ("example.com",)
    assert provider.records("example.com")[0]["type"] == "CNAME"


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
    provider = CloudflareDnsProvider(client)  # type: ignore[arg-type]
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
