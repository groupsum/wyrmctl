from __future__ import annotations

import pytest

from wyrmctl_route53.client import Route53Client
from wyrmctl_route53.config import Route53Config
from wyrmctl_route53.errors import Route53Error
from wyrmctl_route53.models import Route53Record
from wyrmctl_route53.provider import Route53DnsProvider


class FakeRoute53Api:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def list_hosted_zones(self):
        self.calls.append({"method": "list_hosted_zones"})
        return {"HostedZones": [{"Id": "/hostedzone/Z1", "Name": "Example.com."}]}

    def list_resource_record_sets(self, **kwargs):
        self.calls.append({"method": "list_resource_record_sets", **kwargs})
        return {
            "ResourceRecordSets": [
                {"Name": "www.example.com.", "Type": "A", "TTL": 300, "ResourceRecords": [{"Value": "192.0.2.10"}]}
            ]
        }

    def change_resource_record_sets(self, **kwargs):
        self.calls.append({"method": "change_resource_record_sets", **kwargs})
        return {"ChangeInfo": {"Id": "/change/C1"}}


def test_config_from_env_and_redaction() -> None:
    config = Route53Config.from_env({"AWS_PROFILE": "dns-prod", "AWS_REGION": "us-east-1"})

    assert config.profile == "dns-prod"
    assert config.region_name == "us-east-1"
    assert config.redacted()["aws_credentials"] == "standard-chain"


def test_route53_profile_overrides_aws_profile() -> None:
    config = Route53Config.from_env({"AWS_PROFILE": "default", "ROUTE53_PROFILE": "dns-prod"})

    assert config.profile == "dns-prod"


def test_client_lists_zones_and_records() -> None:
    api = FakeRoute53Api()
    client = Route53Client(Route53Config(), api=api)

    assert client.zones() == ("example.com",)
    assert client.records("example.com")[0].to_dict()["value"] == "192.0.2.10"
    assert api.calls[2]["HostedZoneId"] == "Z1"


def test_client_creates_upserts_and_deletes_records() -> None:
    api = FakeRoute53Api()
    client = Route53Client(Route53Config(), api=api)

    assert client.create_record("example.com", type="A", name="www", value="192.0.2.10", ttl=300) == "/change/C1"
    assert (
        client.upsert_record("example.com", type="CNAME", name="app", value="target.example.net", ttl=300)
        == "/change/C1"
    )
    assert client.delete_record("example.com", type="A", name="www", value="192.0.2.10", ttl=300) == "/change/C1"

    create_call = api.calls[1]
    upsert_call = api.calls[3]
    delete_call = api.calls[5]
    assert create_call["ChangeBatch"]["Changes"][0]["Action"] == "CREATE"  # type: ignore[index]
    assert upsert_call["ChangeBatch"]["Changes"][0]["Action"] == "UPSERT"  # type: ignore[index]
    assert delete_call["ChangeBatch"]["Changes"][0]["Action"] == "DELETE"  # type: ignore[index]
    assert upsert_call["ChangeBatch"]["Changes"][0]["ResourceRecordSet"]["Name"] == "app.example.com."  # type: ignore[index]


def test_client_renders_mx_priority() -> None:
    api = FakeRoute53Api()
    client = Route53Client(Route53Config(), api=api)

    client.upsert_record("example.com", type="MX", name="@", value="mail.example.com", ttl=300, priority=10)

    record_set = api.calls[1]["ChangeBatch"]["Changes"][0]["ResourceRecordSet"]  # type: ignore[index]
    assert record_set["ResourceRecords"] == [{"Value": "10 mail.example.com"}]

    with pytest.raises(Route53Error, match="priority is required for MX records"):
        client.upsert_record("example.com", type="MX", name="@", value="mail.example.com", ttl=300)


def test_client_reports_missing_zone() -> None:
    class EmptyApi:
        def list_hosted_zones(self):
            return {"HostedZones": []}

    client = Route53Client(Route53Config(), api=EmptyApi())

    with pytest.raises(Route53Error, match="hosted zone not found"):
        client.records("missing.example")


def test_record_parses_alias_target() -> None:
    record = Route53Record.from_mapping(
        {"Name": "cdn.example.com.", "Type": "A", "AliasTarget": {"DNSName": "target.elb.amazonaws.com."}}
    )

    assert record.to_dict()["value"] == "target.elb.amazonaws.com."


def test_provider_returns_record_dicts() -> None:
    class Client:
        def zones(self):
            return ("example.com",)

        def records(self, zone: str):
            assert zone == "example.com"
            return (
                Route53Record.from_mapping(
                    {"Name": "www.example.com.", "Type": "A", "ResourceRecords": [{"Value": "192.0.2.10"}]}
                ),
            )

    provider = Route53DnsProvider(Client())  # type: ignore[arg-type]

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
    provider = Route53DnsProvider(client)  # type: ignore[arg-type]
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
