<h1 align="center">wyrmctl-godaddy</h1>

<p align="center"><strong>GoDaddy DNS provider plugin for Portwyrm through wyrmctl</strong></p>

<p align="center">
  Extend <code>wyrmctl</code> with GoDaddy-backed DNS record management for declarative workflows, provider discovery, and DNS-aware automation.
</p>

<p align="center">
  <a href="https://pypi.org/project/wyrmctl-godaddy/"><img src="https://img.shields.io/pypi/v/wyrmctl-godaddy.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/wyrmctl-godaddy/"><img src="https://img.shields.io/pypi/pyversions/wyrmctl-godaddy.svg" alt="Python versions"></a>
  <a href="https://github.com/groupsum/wyrmctl/actions/workflows/ci.yml"><img src="https://github.com/groupsum/wyrmctl/actions/workflows/ci.yml/badge.svg?branch=master" alt="CI"></a>
  <a href="https://github.com/groupsum/wyrmctl/blob/master/.ssot/registry.json"><img src="https://img.shields.io/badge/SSOT-governed-2f6f4e.svg" alt="SSOT governed"></a>
  <a href="https://github.com/groupsum/wyrmctl/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="Apache 2.0 License"></a>
</p>

<p align="center">
  <a href="https://hits.sh/github.com/groupsum/wyrmctl/blob/master/packages/wyrmctl-godaddy/README.md/"><img src="https://hits.sh/github.com/groupsum/wyrmctl/blob/master/packages/wyrmctl-godaddy/README.md.svg?label=wyrmctl-godaddy%20package%20hits" alt="wyrmctl-godaddy package hits"></a>
  <a href="https://pepy.tech/projects/wyrmctl-godaddy"><img src="https://static.pepy.tech/badge/wyrmctl-godaddy" alt="wyrmctl-godaddy downloads"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/groupsum/wyrmctl/master/docs/images/marketing/wyrmctl-architecture-infographic.png" alt="wyrmctl architecture infographic">
</p>

`wyrmctl-godaddy` is the GoDaddy DNS provider package for the Portwyrm wyrmctl CLI. Install it when you want desired-state DNS records or DNS diagnostics to resolve through GoDaddy instead of using only the base `wyrmctl` package.

## Supported Python Versions

`wyrmctl-godaddy` supports Python `3.10`, `3.11`, `3.12`, `3.13`, and `3.14`.

## Why wyrmctl-godaddy

- Adds GoDaddy DNS provider discovery to `wyrmctl`
- Lets DNS workflows live beside proxy and certificate desired state
- Keeps GoDaddy API keys out of the core CLI package
- Supports operator diagnostics through `wyrmctl dns doctor`
- Documents GoDaddy's record-set replacement behavior for safer automation

## FAQ

### What is wyrmctl-godaddy?

**Answer:** `wyrmctl-godaddy` is a Portwyrm extension package that teaches wyrmctl how to talk to the GoDaddy Domains API for DNS record operations and DNS provider diagnostics.

### When do I need wyrmctl-godaddy?

**Answer:** You need `wyrmctl-godaddy` when your `wyrmctl` workflow includes GoDaddy-managed DNS records or when you want `wyrmctl` to validate GoDaddy DNS connectivity and credentials.

### Does wyrmctl-godaddy work without wyrmctl?

**Answer:** No. `wyrmctl-godaddy` is an extension package for `wyrmctl`, not a standalone CLI.

### Can wyrmctl-godaddy set DNS records?

**Answer:** Yes. The GoDaddy provider supports declarative A, AAAA, CNAME, TXT, MX, SRV, and CAA writes. MX records require `priority`. Its DNS mutation endpoint replaces all records for one `{type, name}` pair, so preserve existing values when managing multi-value records.

### What credentials are required?

**Answer:** GoDaddy API access requires `GODADDY_API_KEY` and `GODADDY_API_SECRET`. Account protection, domain locks, or product eligibility can still block DNS mutations even when credentials are valid.

## Install

Install the base CLI and the GoDaddy provider package together:

```bash
pipx install wyrmctl
pipx inject wyrmctl wyrmctl-godaddy
wyrmctl plugins list
```

With `uv`:

```bash
uv tool install wyrmctl
uv tool install wyrmctl-godaddy
wyrmctl plugins list
```

Inside a virtual environment:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install wyrmctl wyrmctl-godaddy
wyrmctl plugins list
```

## Configure GoDaddy

Set the required environment variables:

```bash
export GODADDY_API_KEY=your-api-key
export GODADDY_API_SECRET=your-api-secret
```

Optional for tests or alternate endpoints:

```bash
export GODADDY_API_BASE_URL=https://api.godaddy.com
```

## Verify Plugin Discovery

Check that `wyrmctl` can discover the provider:

```bash
wyrmctl plugins list
wyrmctl dns doctor --provider godaddy
```

## Minimal DNS Workflow

Once the provider is installed and configured, `wyrmctl` can validate, plan, apply, or diagnose GoDaddy-backed DNS behavior through the base CLI:

```bash
wyrmctl validate desired-state/dns.yaml
wyrmctl plan desired-state/dns.yaml --owner site-a
wyrmctl apply desired-state/dns.yaml --owner site-a
wyrmctl dns providers
wyrmctl dns zones --provider godaddy
wyrmctl dns records --provider godaddy --zone example.com
```

## GoDaddy API Surface

The provider follows the GoDaddy Domains API DNS record surface:

- `GET /v1/domains`: discover domains in the account.
- `GET /v1/domains/{domain}/records`: list all DNS records for one domain.
- `GET /v1/domains/{domain}/records/{type}/{name}`: list records for one type and name.
- `PUT /v1/domains/{domain}/records/{type}/{name}`: replace the full record set for one type and name.
- `DELETE /v1/domains/{domain}/records/{type}/{name}`: delete records for one type and name.

## Programmatic Record Operations

`create_record()` is a convenience wrapper that replaces a `{type, name}` pair with one record. Use `replace_records()` when preserving multiple values for the same record name and type:

```python
from wyrmctl_godaddy import GoDaddyClient, GoDaddyConfig

client = GoDaddyClient(GoDaddyConfig.from_env())
client.create_record("example.com", type="A", name="www", value="192.0.2.10", ttl=600)
client.replace_records(
    "example.com",
    type="CNAME",
    name="app",
    records=[{"data": "target.example.net", "ttl": 600}],
)
client.delete_records("example.com", type="A", name="www")
```

## Safety Notes

- GoDaddy `PUT` replaces all records for the selected `{type, name}` pair.
- Account-level domain locks, premium DNS status, protection settings, or product eligibility may block API changes even when credentials are valid.
- Use least-privilege keys where available and avoid broad automation over unrelated domains.
- Use wyrmctl owner metadata for desired DNS records so apply remains owner-scoped.

## More Documentation

- Related PyPI package: https://pypi.org/project/wyrmctl/
- Repository: https://github.com/groupsum/wyrmctl
- DNS provider docs: https://github.com/groupsum/wyrmctl/tree/master/docs/dns-providers.md
