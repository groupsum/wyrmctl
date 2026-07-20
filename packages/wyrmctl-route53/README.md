<h1 align="center">wyrmctl-route53</h1>

<p align="center"><strong>AWS Route 53 DNS provider plugin for wyrmctl</strong></p>

<p align="center">
  Extend <code>wyrmctl</code> with Route 53-backed DNS record management for declarative workflows, provider discovery, and DNS-aware automation.
</p>

<p align="center">
  <a href="https://pypi.org/project/wyrmctl-route53/"><img src="https://img.shields.io/pypi/v/wyrmctl-route53.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/wyrmctl-route53/"><img src="https://img.shields.io/pypi/pyversions/wyrmctl-route53.svg" alt="Python versions"></a>
  <a href="https://github.com/groupsum/wyrmctl/actions/workflows/ci.yml"><img src="https://github.com/groupsum/wyrmctl/actions/workflows/ci.yml/badge.svg?branch=master" alt="CI"></a>
  <a href="https://github.com/groupsum/wyrmctl/blob/master/.ssot/registry.json"><img src="https://img.shields.io/badge/SSOT-governed-2f6f4e.svg" alt="SSOT governed"></a>
  <a href="https://github.com/groupsum/wyrmctl/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="Apache 2.0 License"></a>
</p>

<p align="center">
  <a href="https://hits.sh/github.com/groupsum/wyrmctl/blob/master/packages/wyrmctl-route53/README.md/"><img src="https://hits.sh/github.com/groupsum/wyrmctl/blob/master/packages/wyrmctl-route53/README.md.svg?label=wyrmctl-route53%20package%20hits" alt="wyrmctl-route53 package hits"></a>
  <a href="https://pepy.tech/projects/wyrmctl-route53"><img src="https://static.pepy.tech/badge/wyrmctl-route53" alt="wyrmctl-route53 downloads"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/groupsum/wyrmctl/master/docs/images/marketing/wyrmctl-architecture-infographic.png" alt="wyrmctl architecture infographic">
</p>

`wyrmctl-route53` is the AWS Route 53 DNS provider package for `wyrmctl`. Install it when you want desired-state DNS records or DNS diagnostics to resolve through Route 53 instead of using only the base `wyrmctl` package.

## Supported Python Versions

`wyrmctl-route53` supports Python `3.10`, `3.11`, `3.12`, `3.13`, and `3.14`.

## Why wyrmctl-route53

- Adds Route 53 DNS provider discovery to `wyrmctl`
- Lets DNS workflows live beside proxy and certificate desired state
- Keeps AWS DNS dependencies out of the core CLI package
- Supports operator diagnostics through `wyrmctl dns doctor`
- Provides client helpers for Route 53 DNS change-batch workflows

## FAQ

### What is wyrmctl-route53?

**Answer:** `wyrmctl-route53` is a plugin package that teaches `wyrmctl` how to talk to AWS Route 53 through `boto3` for DNS record operations and DNS provider diagnostics.

### When do I need wyrmctl-route53?

**Answer:** You need `wyrmctl-route53` when your `wyrmctl` workflow includes Route 53 hosted-zone DNS records or when you want `wyrmctl` to validate Route 53 DNS connectivity and credentials.

### Does wyrmctl-route53 work without wyrmctl?

**Answer:** No. `wyrmctl-route53` is an extension package for `wyrmctl`, not a standalone CLI.

### Can wyrmctl-route53 set DNS records?

**Answer:** Yes. The Route 53 provider supports declarative A, AAAA, CNAME, TXT, MX, SRV, and CAA writes through `ChangeResourceRecordSets`. MX records require `priority`.

### What credentials are required?

**Answer:** Route 53 access uses the standard AWS credential chain or `ROUTE53_PROFILE`. Diagnostics require hosted-zone and record-set list permissions; mutation helpers require `route53:ChangeResourceRecordSets`.

## Install

Install the base CLI and the Route 53 provider package together:

```bash
pipx install wyrmctl
pipx inject wyrmctl wyrmctl-route53
wyrmctl plugins list
```

With `uv`:

```bash
uv tool install wyrmctl
uv tool install wyrmctl-route53
wyrmctl plugins list
```

Inside a virtual environment:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install wyrmctl wyrmctl-route53
wyrmctl plugins list
```

## Configure Route 53

Use the standard AWS credential chain:

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
```

Or use a named profile:

```bash
export AWS_PROFILE=production-dns
```

Optional package-specific override:

```bash
export ROUTE53_PROFILE=production-dns
```

## Verify Plugin Discovery

Check that `wyrmctl` can discover the provider:

```bash
wyrmctl plugins list
wyrmctl dns doctor --provider route53
```

## Minimal DNS Workflow

Once the provider is installed and configured, `wyrmctl` can validate, plan, apply, or diagnose Route 53-backed DNS behavior through the base CLI:

```bash
wyrmctl validate desired-state/dns.yaml
wyrmctl plan desired-state/dns.yaml --owner site-a
wyrmctl apply desired-state/dns.yaml --owner site-a
wyrmctl dns providers
wyrmctl dns zones --provider route53
wyrmctl dns records --provider route53 --zone example.com
```

## Route 53 API Surface

The provider follows the AWS Route 53 API through `boto3`:

- `ListHostedZones`: discover hosted zones.
- `ListResourceRecordSets`: list records in one hosted zone.
- `ChangeResourceRecordSets` with `CREATE`: create record sets.
- `ChangeResourceRecordSets` with `UPSERT`: create or update record sets.
- `ChangeResourceRecordSets` with `DELETE`: delete record sets.

Required IAM actions for diagnostics:

- `route53:ListHostedZones`
- `route53:ListResourceRecordSets`

Required IAM action for mutation helpers:

- `route53:ChangeResourceRecordSets`

## Programmatic Record Operations

```python
from wyrmctl_route53 import Route53Client, Route53Config

client = Route53Client(Route53Config.from_env())
client.create_record("example.com", type="A", name="www", value="192.0.2.10", ttl=300)
client.upsert_record("example.com", type="CNAME", name="app", value="target.example.net", ttl=300)
client.upsert_record("example.com", type="MX", name="@", value="mail.example.com", ttl=300, priority=10)
client.delete_record("example.com", type="A", name="www", value="192.0.2.10", ttl=300)
```

## Safety Notes

- Route 53 changes are hosted-zone scoped. Confirm the selected hosted zone before mutation.
- Prefer IAM policies scoped to the intended hosted zone ARN.
- `UPSERT` can overwrite live DNS answers. Use create-only workflows when adoption is not explicit.
- Use wyrmctl owner metadata for desired DNS records so apply remains owner-scoped.

## More Documentation

- Related PyPI package: https://pypi.org/project/wyrmctl/
- Repository: https://github.com/groupsum/wyrmctl
- DNS provider docs: https://github.com/groupsum/wyrmctl/tree/master/docs/dns-providers.md
