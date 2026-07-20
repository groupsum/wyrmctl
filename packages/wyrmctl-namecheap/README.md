<h1 align="center">wyrmctl-namecheap</h1>

<p align="center"><strong>Namecheap DNS provider plugin for wyrmctl</strong></p>

<p align="center">
  Extend <code>wyrmctl</code> with Namecheap-backed DNS record management for declarative workflows, provider discovery, and DNS-aware automation.
</p>

<p align="center">
  <a href="https://pypi.org/project/wyrmctl-namecheap/"><img src="https://img.shields.io/pypi/v/wyrmctl-namecheap.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/wyrmctl-namecheap/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue" alt="Python 3.10, 3.11, 3.12, 3.13, and 3.14"></a>
  <a href="https://github.com/groupsum/wyrmctl/actions/workflows/ci.yml"><img src="https://github.com/groupsum/wyrmctl/actions/workflows/ci.yml/badge.svg?branch=master" alt="CI"></a>
  <a href="https://github.com/groupsum/wyrmctl/blob/master/.ssot/registry.json"><img src="https://img.shields.io/badge/SSOT-governed-2f6f4e.svg" alt="SSOT governed"></a>
  <a href="https://github.com/groupsum/wyrmctl/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="Apache 2.0 License"></a>
</p>

<p align="center">
  <a href="https://hits.sh/github.com/groupsum/wyrmctl/blob/master/packages/wyrmctl-namecheap/README.md/"><img src="https://hits.sh/github.com/groupsum/wyrmctl/blob/master/packages/wyrmctl-namecheap/README.md.svg?label=wyrmctl-namecheap%20package%20hits" alt="wyrmctl-namecheap package hits"></a>
  <a href="https://pepy.tech/projects/wyrmctl-namecheap"><img src="https://static.pepy.tech/badge/wyrmctl-namecheap" alt="wyrmctl-namecheap downloads"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/groupsum/wyrmctl/master/docs/images/marketing/wyrmctl-architecture-infographic.png" alt="wyrmctl architecture infographic">
</p>

`wyrmctl-namecheap` is the Namecheap DNS provider package for `wyrmctl`. Install it when you want desired-state DNS records or DNS diagnostics to resolve through Namecheap instead of using only the base `wyrmctl` package.

## Supported Python Versions

`wyrmctl-namecheap` supports Python `3.10`, `3.11`, `3.12`, `3.13`, and `3.14`.

## Why wyrmctl-namecheap

- Adds Namecheap DNS provider discovery to `wyrmctl`
- Lets DNS workflows live beside proxy and certificate desired state
- Keeps provider-specific credentials out of the core CLI package
- Supports operator diagnostics through `wyrmctl dns doctor`
- Persists A, AAAA, CNAME, TXT, MX, SRV, and CAA records through Namecheap `setHosts` during `wyrmctl apply`

## FAQ

### What is wyrmctl-namecheap?

**Answer:** `wyrmctl-namecheap` is a plugin package that teaches `wyrmctl` how to talk to the Namecheap DNS API for DNS record operations and DNS provider diagnostics.

### When do I need wyrmctl-namecheap?

**Answer:** You need `wyrmctl-namecheap` when your `wyrmctl` workflow includes Namecheap-managed DNS records or when you want `wyrmctl` to validate Namecheap DNS connectivity and credentials.

### Does wyrmctl-namecheap work without wyrmctl?

**Answer:** No. `wyrmctl-namecheap` is an extension package for `wyrmctl`, not a standalone CLI.

### What credentials are required?

**Answer:** Namecheap API access requires `NAMECHEAP_API_USER`, `NAMECHEAP_API_KEY`, `NAMECHEAP_USERNAME`, and `NAMECHEAP_CLIENT_IP`. You can also override the endpoint with `NAMECHEAP_API_BASE_URL` for tests or non-default environments.

## Install

Install the base CLI and the Namecheap provider package together:

```bash
pipx install wyrmctl
pipx inject wyrmctl wyrmctl-namecheap
wyrmctl plugins list
```

With `uv`:

```bash
uv tool install wyrmctl
uv tool install wyrmctl-namecheap
wyrmctl plugins list
```

Inside a virtual environment:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install wyrmctl wyrmctl-namecheap
wyrmctl plugins list
```

## Configure Namecheap

Set the required environment variables:

```bash
export NAMECHEAP_API_USER=your-api-user
export NAMECHEAP_API_KEY=your-api-key
export NAMECHEAP_USERNAME=your-username
export NAMECHEAP_CLIENT_IP=your-public-ip
```

Optional for tests or alternate endpoints:

```bash
export NAMECHEAP_API_BASE_URL=https://api.namecheap.com/xml.response
```

## Verify Plugin Discovery

Check that `wyrmctl` can discover the provider:

```bash
wyrmctl plugins list
wyrmctl dns doctor --provider namecheap
```

## Minimal DNS Workflow

Once the provider is installed and configured, `wyrmctl` can validate, plan, apply,
and diagnose Namecheap-backed DNS behavior through the base CLI:

```bash
wyrmctl validate desired-state/dns.yaml
wyrmctl plan desired-state/dns.yaml --owner site-a
wyrmctl apply desired-state/dns.yaml --owner site-a
wyrmctl dns doctor --provider namecheap
wyrmctl dns records --provider namecheap --zone example.com
```

Namecheap apply uses `namecheap.domains.dns.setHosts`, so wyrmctl sends the full
zone host set required by the Namecheap XML API. Unmanaged records returned by
Namecheap are preserved; stale wyrmctl-owned records can be removed with
owner-scoped prune behavior when they are omitted from desired state.
The supported declarative record types are A, AAAA, CNAME, TXT, MX, SRV, and
CAA. MX records require `priority`.

## More Documentation

- Related PyPI package: https://pypi.org/project/wyrmctl/
- Repository: https://github.com/groupsum/wyrmctl
- Provider docs: https://github.com/groupsum/wyrmctl/tree/master/docs/namecheap.md
