<h1 align="center">wyrmctl-digitalocean</h1>

<p align="center"><strong>DigitalOcean DNS provider plugin for Portwyrm through wyrmctl</strong></p>

<p align="center">
  Extend <code>wyrmctl</code> with DigitalOcean-backed DNS record management for declarative workflows, provider discovery, and DNS-aware automation.
</p>

<p align="center">
  <a href="https://pypi.org/project/wyrmctl-digitalocean/"><img src="https://img.shields.io/pypi/v/wyrmctl-digitalocean.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/wyrmctl-digitalocean/"><img src="https://img.shields.io/pypi/pyversions/wyrmctl-digitalocean.svg" alt="Python versions"></a>
  <a href="https://github.com/groupsum/wyrmctl/actions/workflows/ci.yml"><img src="https://github.com/groupsum/wyrmctl/actions/workflows/ci.yml/badge.svg?branch=master" alt="CI"></a>
  <a href="https://github.com/groupsum/wyrmctl/blob/master/.ssot/registry.json"><img src="https://img.shields.io/badge/SSOT-governed-2f6f4e.svg" alt="SSOT governed"></a>
  <a href="https://github.com/groupsum/wyrmctl/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="Apache 2.0 License"></a>
</p>

<p align="center">
  <a href="https://hits.sh/github.com/groupsum/wyrmctl/blob/master/packages/wyrmctl-digitalocean/README.md/"><img src="https://hits.sh/github.com/groupsum/wyrmctl/blob/master/packages/wyrmctl-digitalocean/README.md.svg?label=wyrmctl-digitalocean%20package%20hits" alt="wyrmctl-digitalocean package hits"></a>
  <a href="https://pepy.tech/projects/wyrmctl-digitalocean"><img src="https://static.pepy.tech/badge/wyrmctl-digitalocean" alt="wyrmctl-digitalocean downloads"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/groupsum/wyrmctl/master/docs/images/marketing/wyrmctl-architecture-infographic.png" alt="wyrmctl architecture infographic">
</p>

`wyrmctl-digitalocean` is the DigitalOcean DNS provider package for the Portwyrm wyrmctl CLI. Install it when you want desired-state DNS records or DNS diagnostics to resolve through DigitalOcean instead of using only the base `wyrmctl` package.

## Supported Python Versions

`wyrmctl-digitalocean` supports Python `3.10`, `3.11`, `3.12`, `3.13`, and `3.14`.

## Why wyrmctl-digitalocean

- Adds DigitalOcean DNS provider discovery to `wyrmctl`
- Lets DNS workflows live beside proxy and certificate desired state
- Keeps DigitalOcean tokens out of the core CLI package
- Supports operator diagnostics through `wyrmctl dns doctor`
- Provides client helpers for DigitalOcean DNS record workflows

## FAQ

### What is wyrmctl-digitalocean?

**Answer:** `wyrmctl-digitalocean` is a Portwyrm extension package that teaches wyrmctl how to talk to the DigitalOcean Domain Records API for DNS record operations and DNS provider diagnostics.

### When do I need wyrmctl-digitalocean?

**Answer:** You need `wyrmctl-digitalocean` when your `wyrmctl` workflow includes DigitalOcean-managed DNS records or when you want `wyrmctl` to validate DigitalOcean DNS connectivity and credentials.

### Does wyrmctl-digitalocean work without wyrmctl?

**Answer:** No. `wyrmctl-digitalocean` is an extension package for `wyrmctl`, not a standalone CLI.

### Can wyrmctl-digitalocean set DNS records?

**Answer:** Yes. The DigitalOcean provider supports declarative A, AAAA, CNAME, TXT, MX, SRV, and CAA writes. MX records require `priority`.

### What credentials are required?

**Answer:** DigitalOcean API access requires `DIGITALOCEAN_TOKEN`. For diagnostics, the token needs domain read permissions. For record changes, it needs write access to target domain records.

## Install

Install the base CLI and the DigitalOcean provider package together:

```bash
pipx install wyrmctl
pipx inject wyrmctl wyrmctl-digitalocean
wyrmctl plugins list
```

With `uv`:

```bash
uv tool install wyrmctl
uv tool install wyrmctl-digitalocean
wyrmctl plugins list
```

Inside a virtual environment:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install wyrmctl wyrmctl-digitalocean
wyrmctl plugins list
```

## Configure DigitalOcean

Set the required environment variable:

```bash
export DIGITALOCEAN_TOKEN=your-digitalocean-token
```

Optional for tests or alternate endpoints:

```bash
export DIGITALOCEAN_API_BASE_URL=https://api.digitalocean.com
```

## Verify Plugin Discovery

Check that `wyrmctl` can discover the provider:

```bash
wyrmctl plugins list
wyrmctl dns doctor --provider digitalocean
```

## Minimal DNS Workflow

Once the provider is installed and configured, `wyrmctl` can validate, plan, apply, or diagnose DigitalOcean-backed DNS behavior through the base CLI:

```bash
wyrmctl validate desired-state/dns.yaml
wyrmctl plan desired-state/dns.yaml --owner site-a
wyrmctl apply desired-state/dns.yaml --owner site-a
wyrmctl dns providers
wyrmctl dns zones --provider digitalocean
wyrmctl dns records --provider digitalocean --zone example.com
```

## DigitalOcean API Surface

The provider follows the DigitalOcean Domains and Domain Records API:

- `GET /v2/domains`: discover domains managed in the account.
- `GET /v2/domains/{domain_name}/records`: list DNS records for one domain.
- `POST /v2/domains/{domain_name}/records`: create supported DNS records.
- `PUT /v2/domains/{domain_name}/records/{domain_record_id}`: update a record.
- `DELETE /v2/domains/{domain_name}/records/{domain_record_id}`: delete a record.

## Programmatic Record Operations

```python
from wyrmctl_digitalocean import DigitalOceanClient, DigitalOceanConfig

client = DigitalOceanClient(DigitalOceanConfig.from_env())
record = client.create_record("example.com", type="A", name="www", value="192.0.2.10", ttl=300)
client.update_record("example.com", int(record.record_id), type="A", name="www", value="192.0.2.11", ttl=300)
client.delete_record("example.com", int(record.record_id))
```

CNAME and other supported record types use the same `type`, `name`, `value`,
and `ttl` shape. MX records pass `priority`.

## Safety Notes

- DigitalOcean record `name` is relative to the zone; use `@` for the root where applicable.
- Keep `DIGITALOCEAN_TOKEN` out of desired-state files and logs.
- Use account and token scoping to avoid mutating foreign-owned DNS.
- Use wyrmctl owner metadata for desired DNS records so apply remains owner-scoped.

## More Documentation

- Related PyPI package: https://pypi.org/project/wyrmctl/
- Repository: https://github.com/groupsum/wyrmctl
- DNS provider docs: https://github.com/groupsum/wyrmctl/tree/master/docs/dns-providers.md
