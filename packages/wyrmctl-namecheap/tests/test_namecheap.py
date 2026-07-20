from __future__ import annotations

import pytest

from wyrmctl_namecheap.client import NamecheapClient
from wyrmctl_namecheap.config import NamecheapConfig
from wyrmctl_namecheap.errors import NamecheapError
from wyrmctl_namecheap.models import NamecheapRecord, split_zone
from wyrmctl_namecheap.provider import NamecheapDnsProvider


class FakeResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def get(self, url: str, **kwargs) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)


def _config() -> NamecheapConfig:
    return NamecheapConfig(
        api_user="api-user",
        api_key="api-key",
        username="username",
        client_ip="192.0.2.10",
        api_base_url="https://namecheap.test/xml.response",
    )


def test_config_from_env_and_redaction() -> None:
    config = NamecheapConfig.from_env(
        {
            "NAMECHEAP_API_USER": "api-user",
            "NAMECHEAP_API_KEY": "api-key",
            "NAMECHEAP_USERNAME": "username",
            "NAMECHEAP_CLIENT_IP": "192.0.2.10",
        }
    )

    assert config.redacted()["api_key"] is True
    assert config.api_base_url == "https://api.namecheap.com/xml.response"


def test_config_requires_credentials() -> None:
    with pytest.raises(ValueError, match="missing Namecheap config"):
        NamecheapConfig.from_env({})


def test_split_zone_and_record_parsing() -> None:
    assert split_zone("Example.Com.") == ("example", "com")
    with pytest.raises(ValueError, match="zone must be"):
        split_zone("localhost")

    record = NamecheapRecord.from_attrs(
        {"HostId": "10", "Name": "WWW", "Type": "a", "Address": "192.0.2.10", "TTL": "300", "MXPref": ""}
    )

    assert record.to_dict() == {
        "id": "10",
        "name": "www",
        "type": "A",
        "value": "192.0.2.10",
        "ttl": 300,
        "priority": None,
    }


def test_client_lists_zones_and_records() -> None:
    client = NamecheapClient(_config())
    session = FakeSession(
        [
            FakeResponse(
                200,
                """<?xml version="1.0" encoding="utf-8"?>
                <ApiResponse Status="OK" xmlns="http://api.namecheap.com/xml.response">
                  <CommandResponse>
                    <DomainGetListResult>
                      <Domain Name="example.com" />
                    </DomainGetListResult>
                  </CommandResponse>
                </ApiResponse>""",
            ),
            FakeResponse(
                200,
                """<?xml version="1.0" encoding="utf-8"?>
                <ApiResponse Status="OK" xmlns="http://api.namecheap.com/xml.response">
                  <CommandResponse>
                    <DomainDNSGetHostsResult>
                      <host HostId="1" Name="@" Type="A" Address="192.0.2.10" TTL="300" />
                    </DomainDNSGetHostsResult>
                  </CommandResponse>
                </ApiResponse>""",
            ),
        ]
    )
    client.session = session  # type: ignore[assignment]

    assert client.zones() == ("example.com",)
    assert client.records("example.com")[0].address == "192.0.2.10"
    assert session.calls[0]["params"]["Command"] == "namecheap.domains.getList"  # type: ignore[index]
    assert session.calls[1]["params"]["SLD"] == "example"  # type: ignore[index]


def test_client_set_hosts_renders_supported_record_types() -> None:
    client = NamecheapClient(_config())
    client.session = FakeSession(
        [
            FakeResponse(
                200,
                """<ApiResponse Status="OK" xmlns="http://api.namecheap.com/xml.response" />""",
            )
        ]
    )  # type: ignore[assignment]

    client.set_hosts(
        "example.com",
        (
            {"name": "@", "type": "A", "value": "192.0.2.10", "ttl": 300},
            {"name": "www", "type": "CNAME", "value": "example.com", "ttl": 600},
            {"name": "v6", "type": "AAAA", "value": "2001:db8::1", "ttl": 300},
            {"name": "txt", "type": "TXT", "value": "hello", "ttl": 300},
            {"name": "@", "type": "MX", "value": "mail.example.com", "ttl": 300, "priority": 10},
            {"name": "_sip._tcp", "type": "SRV", "value": "10 20 5060 sip.example.com", "ttl": 300},
            {"name": "@", "type": "CAA", "value": '0 issue "letsencrypt.org"', "ttl": 300},
        ),
    )

    params = client.session.calls[0]["params"]  # type: ignore[index]
    assert params["Command"] == "namecheap.domains.dns.setHosts"
    assert params["HostName1"] == "@"
    assert params["RecordType1"] == "A"
    assert params["Address1"] == "192.0.2.10"
    assert params["TTL1"] == "300"
    assert params["MXPref1"] == ""
    assert params["HostName2"] == "www"
    assert params["RecordType2"] == "CNAME"
    assert params["Address2"] == "example.com"
    assert params["RecordType3"] == "AAAA"
    assert params["Address3"] == "2001:db8::1"
    assert params["RecordType4"] == "TXT"
    assert params["Address4"] == "hello"
    assert params["RecordType5"] == "MX"
    assert params["Address5"] == "mail.example.com"
    assert params["MXPref5"] == "10"
    assert params["RecordType6"] == "SRV"
    assert params["Address6"] == "10 20 5060 sip.example.com"
    assert params["RecordType7"] == "CAA"
    assert params["Address7"] == '0 issue "letsencrypt.org"'


def test_client_set_hosts_rejects_unsupported_records_missing_mx_priority_and_missing_client_ip() -> None:
    client = NamecheapClient(_config())
    with pytest.raises(NamecheapError, match="unsupported Namecheap DNS record type"):
        client.set_hosts("example.com", ({"name": "@", "type": "NS", "value": "ns1.example.com"},))
    with pytest.raises(NamecheapError, match="priority is required for MX records"):
        client.set_hosts("example.com", ({"name": "@", "type": "MX", "value": "mail.example.com"},))

    missing_ip = NamecheapConfig(
        api_user="api-user",
        api_key="api-key",
        username="username",
        client_ip="",
        api_base_url="https://namecheap.test/xml.response",
    )
    with pytest.raises(NamecheapError, match="client_ip"):
        NamecheapClient(missing_ip).set_hosts("example.com", ())


def test_client_reports_http_api_and_xml_errors() -> None:
    client = NamecheapClient(_config())
    client.session = FakeSession([FakeResponse(500, "broken")])  # type: ignore[assignment]
    with pytest.raises(NamecheapError, match="HTTP 500"):
        client.zones()

    client.session = FakeSession([FakeResponse(200, "<not xml")])  # type: ignore[assignment]
    with pytest.raises(NamecheapError, match="invalid XML"):
        client.zones()

    client.session = FakeSession(
        [
            FakeResponse(
                200,
                """<ApiResponse Status="ERROR" xmlns="http://api.namecheap.com/xml.response">
                <Errors><Error>denied api-key username 192.0.2.10</Error></Errors>
                </ApiResponse>""",
            )
        ]
    )  # type: ignore[assignment]
    with pytest.raises(NamecheapError, match=r"denied \*\*\* \*\*\* \*\*\*") as exc_info:
        client.zones()
    assert "api-key" not in str(exc_info.value)


def test_provider_returns_record_dicts() -> None:
    class Client:
        def zones(self):
            return ("example.com",)

        def records(self, zone: str):
            assert zone == "example.com"
            return (NamecheapRecord.from_attrs({"Name": "@", "Type": "A", "Address": "192.0.2.10"}),)

    provider = NamecheapDnsProvider(Client())  # type: ignore[arg-type]

    assert provider.zones() == ("example.com",)
    assert provider.records("example.com")[0]["value"] == "192.0.2.10"


def test_provider_applies_record_dicts() -> None:
    class Client:
        def __init__(self) -> None:
            self.calls = []

        def zones(self):
            return ("example.com",)

        def records(self, zone: str):
            assert zone == "example.com"
            return ()

        def set_hosts(self, zone: str, records: tuple[dict[str, object], ...]) -> None:
            self.calls.append((zone, records))

    client = Client()
    provider = NamecheapDnsProvider(client)  # type: ignore[arg-type]

    provider.apply_records("example.com", ({"name": "@", "type": "A", "value": "192.0.2.10"},))

    assert client.calls == [("example.com", ({"name": "@", "type": "A", "value": "192.0.2.10"},))]
