<h1 align="center">wyrmctl-cloudflare</h1>

<p align="center"><strong>Cloudflare DNS provider plugin for wyrmctl</strong></p>

<p align="center">
  Extend <code>wyrmctl</code> with Cloudflare-backed DNS record management for declarative workflows, provider discovery, and DNS-aware automation.
</p>

<p align="center">
  <a href="https://pypi.org/project/wyrmctl-cloudflare/"><img src="https://img.shields.io/pypi/v/wyrmctl-cloudflare.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/wyrmctl-cloudflare/"><img src="https://img.shields.io/pypi/pyversions/wyrmctl-cloudflare.svg" alt="Python versions"></a>
  <a href="https://github.com/groupsum/wyrmctl/actions/workflows/ci.yml"><img src="https://github.com/groupsum/wyrmctl/actions/workflows/ci.yml/badge.svg?branch=master" alt="CI"></a>
  <a href="https://github.com/groupsum/wyrmctl/blob/master/.ssot/registry.json"><img src="https://img.shields.io/badge/SSOT-governed-2f6f4e.svg" alt="SSOT governed"></a>
  <a href="https://github.com/groupsum/wyrmctl/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="Apache 2.0 License"></a>
</p>

<p align="center">
  <a href="https://hits.sh/github.com/groupsum/wyrmctl/blob/master/packages/wyrmctl-cloudflare/README.md/"><img src="https://hits.sh/github.com/groupsum/wyrmctl/blob/master/packages/wyrmctl-cloudflare/README.md.svg?label=wyrmctl-cloudflare%20package%20hits" alt="wyrmctl-cloudflare package hits"></a>
  <a href="https://pepy.tech/projects/wyrmctl-cloudflare"><img src="https://static.pepy.tech/badge/wyrmctl-cloudflare" alt="wyrmctl-cloudflare downloads"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/groupsum/wyrmctl/master/docs/images/marketing/wyrmctl-architecture-infographic.png" alt="wyrmctl architecture infographic">
</p>

`wyrmctl-cloudflare` is the Cloudflare DNS provider package for `wyrmctl`. Install it when you want desired-state DNS records or DNS diagnostics to resolve through Cloudflare instead of using only the base `wyrmctl` package.

## Supported Python Versions

`wyrmctl-cloudflare` supports Python `3.10`, `3.11`, `3.12`, `3.13`, and `3.14`.

## Why wyrmctl-cloudflare

- Adds Cloudflare DNS provider discovery to `wyrmctl`
- Lets DNS workflows live beside proxy and certificate desired state
- Keeps Cloudflare API tokens out of the core CLI package
- Supports operator diagnostics through `wyrmctl dns doctor`
- Provides client helpers for Cloudflare DNS record workflows

## FAQ

### What is wyrmctl-cloudflare?

**Answer:** `wyrmctl-cloudflare` is a plugin package that teaches `wyrmctl` how to talk to the Cloudflare DNS Records API for DNS record operations and DNS provider diagnostics.

### When do I need wyrmctl-cloudflare?

**Answer:** You need `wyrmctl-cloudflare` when your `wyrmctl` workflow includes Cloudflare-managed DNS records or when you want `wyrmctl` to validate Cloudflare DNS connectivity and credentials.

### Does wyrmctl-cloudflare work without wyrmctl?

**Answer:** No. `wyrmctl-cloudflare` is an extension package for `wyrmctl`, not a standalone CLI.

### Can wyrmctl-cloudflare set DNS records?

**Answer:** Yes. The Cloudflare provider supports declarative A, AAAA, CNAME, TXT, MX, SRV, and CAA writes. MX records require `priority`.

### What credentials are required?

**Answer:** Cloudflare API access requires `CLOUDFLARE_API_TOKEN`. For diagnostics, grant zone read and DNS read access. For record changes, grant DNS write access to the target zone.

## Install

Install the base CLI and the Cloudflare provider package together:

```bash
pipx install wyrmctl
pipx inject wyrmctl wyrmctl-cloudflare
wyrmctl plugins list
```

With `uv`:

```bash
uv tool install wyrmctl
uv tool install wyrmctl-cloudflare
wyrmctl plugins list
```

Inside a virtual environment:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install wyrmctl wyrmctl-cloudflare
wyrmctl plugins list
```

## Configure Cloudflare

Set the required environment variable:

```bash
export CLOUDFLARE_API_TOKEN=your-cloudflare-api-token
```

Optional for tests, proxies, or alternate endpoints:

```bash
export CLOUDFLARE_API_BASE_URL=https://api.cloudflare.com/client/v4
```

## Verify Plugin Discovery

Check that `wyrmctl` can discover the provider:

```bash
wyrmctl plugins list
wyrmctl dns doctor --provider cloudflare
```

## Minimal DNS Workflow

Once the provider is installed and configured, `wyrmctl` can validate, plan, apply, or diagnose Cloudflare-backed DNS behavior through the base CLI:

```bash
wyrmctl validate desired-state/dns.yaml
wyrmctl plan desired-state/dns.yaml --owner site-a
wyrmctl apply desired-state/dns.yaml --owner site-a
wyrmctl dns providers
wyrmctl dns zones --provider cloudflare
wyrmctl dns records --provider cloudflare --zone example.com
```

## Cloudflare API Surface

The provider follows the Cloudflare DNS Records API:

- `GET /zones`: discover zones available to the token.
- `GET /zones/{zone_id}/dns_records`: list DNS records in one zone.
- `POST /zones/{zone_id}/dns_records`: create supported DNS records.
- `PUT /zones/{zone_id}/dns_records/{dns_record_id}`: overwrite an existing record.
- `PATCH /zones/{zone_id}/dns_records/{dns_record_id}`: partially update an existing record.
- `DELETE /zones/{zone_id}/dns_records/{dns_record_id}`: delete a record.

## Programmatic Record Operations

The wyrmctl DNS provider contract requires `zones()` and `records(zone)`. This package also exposes client helpers for API-backed record mutation:

```python
from wyrmctl_cloudflare import CloudflareClient, CloudflareConfig

client = CloudflareClient(CloudflareConfig.from_env())
record = client.create_record("example.com", type="A", name="www", value="192.0.2.10", ttl=300)
client.patch_record("example.com", str(record.record_id), value="192.0.2.11")
client.delete_record("example.com", str(record.record_id))
```

CNAME and other supported record types use the same method. MX records pass
`priority`:

```python
client.create_record("example.com", type="CNAME", name="app", value="target.example.net", ttl=300)
client.create_record("example.com", type="MX", name="@", value="mail.example.com", ttl=300, priority=10)
```

## Safety Notes

- Only operate on zones that are authoritative in Cloudflare.
- Use least-privilege API tokens scoped to the intended zone.
- Keep `CLOUDFLARE_API_TOKEN` out of desired-state files and logs.
- Cloudflare prevents CNAME records from coexisting with A or AAAA records on the same name.
- Use wyrmctl owner metadata for desired DNS records so apply remains owner-scoped.

## More Documentation

- Related PyPI package: https://pypi.org/project/wyrmctl/
- Repository: https://github.com/groupsum/wyrmctl
- DNS provider docs: https://github.com/groupsum/wyrmctl/tree/master/docs/dns-providers.md
