"""Small Namecheap XML API client."""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree

import requests

from wyrmctl_namecheap.config import NamecheapConfig
from wyrmctl_namecheap.errors import NamecheapError
from wyrmctl_namecheap.models import NamecheapRecord, split_zone

_NAMESPACE = {"nc": "http://api.namecheap.com/xml.response"}
_SUPPORTED_RECORD_TYPES = {"A", "AAAA", "CNAME", "TXT", "MX", "SRV", "CAA"}


class NamecheapClient:
    """HTTP client for the Namecheap XML API."""

    def __init__(self, config: NamecheapConfig, *, timeout_s: float = 15.0) -> None:
        self.config = config
        self.timeout_s = timeout_s
        self.session = requests.Session()

    def zones(self) -> tuple[str, ...]:
        data = self._request("namecheap.domains.getList")
        domains = data.findall(".//nc:Domain", _NAMESPACE)
        return tuple(sorted(str(item.attrib["Name"]).lower() for item in domains if item.attrib.get("Name")))

    def records(self, zone: str) -> tuple[NamecheapRecord, ...]:
        sld, tld = split_zone(zone)
        data = self._request("namecheap.domains.dns.getHosts", SLD=sld, TLD=tld)
        result = data.find(".//nc:DomainDNSGetHostsResult", _NAMESPACE)
        if result is None or result.attrib.get("IsUsingOurDNS", "true").casefold() != "true":
            raise NamecheapError("Namecheap did not return an authoritative host record list")
        if any(
            host.tag.rsplit("}", 1)[-1].casefold() != "host" or not {"Name", "Type", "Address"} <= host.attrib.keys()
            for host in result
        ):
            raise NamecheapError("Namecheap returned an unexpected host record element")
        return tuple(NamecheapRecord.from_attrs(host.attrib) for host in result)

    def set_hosts(self, zone: str, records: tuple[dict[str, Any], ...]) -> None:
        sld, tld = split_zone(zone)
        if not self.config.client_ip:
            raise NamecheapError("missing Namecheap config: client_ip")
        params: dict[str, str] = {"SLD": sld, "TLD": tld}
        for index, record in enumerate(records, start=1):
            host = _host_payload(record)
            params[f"HostName{index}"] = host["HostName"]
            params[f"RecordType{index}"] = host["RecordType"]
            params[f"Address{index}"] = host["Address"]
            params[f"TTL{index}"] = host["TTL"]
            params[f"MXPref{index}"] = host["MXPref"]
        self._request("namecheap.domains.dns.setHosts", post=len(records) > 10, **params)

    def _request(self, command: str, *, post: bool = False, **params: str) -> ElementTree.Element:
        query: dict[str, Any] = {
            "ApiUser": self.config.api_user,
            "ApiKey": self.config.api_key,
            "UserName": self.config.username,
            "ClientIp": self.config.client_ip,
            "Command": command,
        }
        try:
            if post:
                response = self.session.post(
                    self.config.api_base_url, params=query, data=params, timeout=self.timeout_s
                )
            else:
                response = self.session.get(
                    self.config.api_base_url, params={**query, **params}, timeout=self.timeout_s
                )
        except requests.RequestException:
            raise NamecheapError("Namecheap API transport failed") from None
        if response.status_code < 200 or response.status_code >= 300:
            raise NamecheapError(f"Namecheap API failed: HTTP {response.status_code}")
        try:
            parsed = ElementTree.fromstring(response.text)
        except ElementTree.ParseError as exc:
            raise NamecheapError("Namecheap API returned invalid XML") from exc
        if parsed.attrib.get("Status", "").casefold() != "ok":
            errors = [item.text or "unknown error" for item in parsed.findall(".//nc:Error", _NAMESPACE)]
            raise NamecheapError(self._redact("; ".join(errors)) or "Namecheap API did not report success")
        return parsed

    def _redact(self, message: str) -> str:
        redacted = message
        for value in (self.config.api_user, self.config.api_key, self.config.username, self.config.client_ip):
            if value:
                redacted = redacted.replace(value, "***")
        return redacted


def _host_payload(record: dict[str, Any]) -> dict[str, str]:
    record_type = str(record.get("type", "")).upper()
    if record_type not in _SUPPORTED_RECORD_TYPES:
        raise NamecheapError(f"unsupported Namecheap DNS record type: {record_type}")
    if record_type == "MX" and record.get("priority") is None:
        raise NamecheapError("priority is required for MX records")
    name = str(record.get("name", "")).strip().lower() or "@"
    ttl = record.get("ttl", 300)
    if ttl is None:
        ttl = 300
    return {
        "HostName": name,
        "RecordType": record_type,
        "Address": str(record.get("value") or record.get("address") or ""),
        "TTL": str(int(ttl)),
        "MXPref": "" if record.get("priority") is None else str(int(record["priority"])),
    }
