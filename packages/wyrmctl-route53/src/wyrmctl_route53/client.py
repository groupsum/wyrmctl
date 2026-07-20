"""Small AWS Route 53 API client."""

from __future__ import annotations

from wyrmctl_route53.config import Route53Config
from wyrmctl_route53.errors import Route53Error
from wyrmctl_route53.models import Route53Record, Route53Zone


class Route53Client:
    """Client wrapper for Route 53 hosted zones and record sets."""

    def __init__(self, config: Route53Config, *, api: object | None = None) -> None:
        self.config = config
        self._api = api

    @property
    def api(self) -> object:
        if self._api is None:
            self._api = _default_api(self.config)
        return self._api

    def zones(self) -> tuple[str, ...]:
        return tuple(zone.name for zone in self._zones())

    def records(self, zone: str) -> tuple[Route53Record, ...]:
        zone_id = self._zone_id(zone)
        data = self.api.list_resource_record_sets(HostedZoneId=zone_id)  # type: ignore[attr-defined]
        return tuple(Route53Record.from_mapping(item) for item in data.get("ResourceRecordSets", []))

    def create_record(
        self, zone: str, *, type: str, name: str, value: str, ttl: int = 300, priority: int | None = None
    ) -> str | None:
        return self._change_record("CREATE", zone, type=type, name=name, value=value, ttl=ttl, priority=priority)

    def upsert_record(
        self, zone: str, *, type: str, name: str, value: str, ttl: int = 300, priority: int | None = None
    ) -> str | None:
        return self._change_record("UPSERT", zone, type=type, name=name, value=value, ttl=ttl, priority=priority)

    def delete_record(
        self, zone: str, *, type: str, name: str, value: str, ttl: int = 300, priority: int | None = None
    ) -> str | None:
        return self._change_record("DELETE", zone, type=type, name=name, value=value, ttl=ttl, priority=priority)

    def _zones(self) -> tuple[Route53Zone, ...]:
        data = self.api.list_hosted_zones()  # type: ignore[attr-defined]
        return tuple(Route53Zone.from_mapping(item) for item in data.get("HostedZones", []))

    def _zone_id(self, zone: str) -> str:
        target = _dns_name(zone)
        for item in self._zones():
            if item.name == target:
                return item.zone_id
        raise Route53Error(f"Route 53 hosted zone not found: {zone}")

    def _change_record(
        self, action: str, zone: str, *, type: str, name: str, value: str, ttl: int, priority: int | None = None
    ) -> str | None:
        record_type = type.upper()
        data = self.api.change_resource_record_sets(  # type: ignore[attr-defined]
            HostedZoneId=self._zone_id(zone),
            ChangeBatch={
                "Changes": [
                    {
                        "Action": action,
                        "ResourceRecordSet": {
                            "Name": _absolute_name(name, zone),
                            "Type": record_type,
                            "TTL": ttl,
                            "ResourceRecords": [{"Value": _record_value(record_type, value, priority)}],
                        },
                    }
                ]
            },
        )
        change = data.get("ChangeInfo", {})
        change_id = change.get("Id")
        return None if change_id is None else str(change_id)


def _default_api(config: Route53Config) -> object:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - exercised only without package dependency installed.
        raise Route53Error("boto3 is required for live Route 53 access") from exc
    session_kwargs: dict[str, str] = {}
    if config.profile:
        session_kwargs["profile_name"] = config.profile
    if config.region_name:
        session_kwargs["region_name"] = config.region_name
    session = boto3.Session(**session_kwargs)
    return session.client("route53")


def _record_value(record_type: str, value: str, priority: int | None) -> str:
    if record_type == "MX":
        if priority is None:
            raise Route53Error("priority is required for MX records")
        return f"{priority} {value}"
    return value


def _absolute_name(name: str, zone: str) -> str:
    normalized_name = _dns_name(name)
    normalized_zone = _dns_name(zone)
    if normalized_name in ("", "@"):
        return f"{normalized_zone}."
    if normalized_name.endswith(f".{normalized_zone}"):
        return f"{normalized_name}."
    return f"{normalized_name}.{normalized_zone}."


def _dns_name(value: str) -> str:
    return value.strip().lower().rstrip(".")
