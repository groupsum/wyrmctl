<h1 align="center">wyrmctl</h1>

<p align="center"><strong>Owner-scoped GitOps for Nginx Proxy Manager</strong></p>

<p align="center">
  Validate desired-state YAML, plan safe owner-scoped changes, apply clean reconciles, and adopt existing NPM resources only when you ask for it.
</p>

<p align="center">
  <a href="https://pypi.org/project/wyrmctl/"><img src="https://img.shields.io/pypi/v/wyrmctl.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/wyrmctl/"><img src="https://img.shields.io/pypi/pyversions/wyrmctl.svg" alt="Python versions"></a>
  <a href="https://github.com/groupsum/wyrmctl/actions/workflows/ci.yml"><img src="https://github.com/groupsum/wyrmctl/actions/workflows/ci.yml/badge.svg?branch=master" alt="CI"></a>
  <a href="https://github.com/groupsum/wyrmctl/actions/workflows/live-npm-gate.yml"><img src="https://github.com/groupsum/wyrmctl/actions/workflows/live-npm-gate.yml/badge.svg?branch=master" alt="Live NPM Gate"></a>
  <a href="https://github.com/groupsum/wyrmctl/blob/master/.ssot/registry.json"><img src="https://img.shields.io/badge/SSOT-governed-2f6f4e.svg" alt="SSOT governed"></a>
  <a href="https://github.com/groupsum/wyrmctl/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="Apache 2.0 License"></a>
</p>

<p align="center">
  <a href="https://hits.sh/github.com/groupsum/wyrmctl/blob/master/packages/wyrmctl/README.md/"><img src="https://hits.sh/github.com/groupsum/wyrmctl/blob/master/packages/wyrmctl/README.md.svg?label=wyrmctl%20package%20hits" alt="wyrmctl package hits"></a>
  <a href="https://pepy.tech/projects/wyrmctl"><img src="https://static.pepy.tech/badge/wyrmctl" alt="wyrmctl downloads"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/groupsum/wyrmctl/master/docs/images/marketing/wyrmctl-architecture-infographic.png" alt="wyrmctl architecture infographic">
</p>

`wyrmctl` is the Python package and console script for declarative, owner-scoped Nginx Proxy Manager automation. It manages proxy hosts, certificates, access lists, redirection hosts, dead hosts, streams, users, settings, and provider-backed DNS records without silently mutating foreign-owned resources.

## Supported Python Versions

`wyrmctl` supports Python `3.10`, `3.11`, `3.12`, `3.13`, and `3.14`.

## Why wyrmctl

- Owner-scoped reconciliation instead of global mutable state
- Explicit `plan`, `apply`, and `adopt` flows instead of ad hoc API scripting
- Safe reference handling for certificates and access lists
- Fail-closed behavior when the target NPM schema does not support a required operation
- CLI-first workflows that fit GitOps, CI, and controlled repair operations
- Independently versioned contracts, reproducibility lockfiles, and immutable reviewed plan artifacts
- Transactional adjacent migrations with backups, chained ledgers, leases, and explicit recovery classification

## FAQ

### What is wyrmctl?

**Answer:** `wyrmctl` is a GitOps-style controller for Nginx Proxy Manager that reads desired-state YAML, compares it to the live NPM API, and produces safe owner-scoped plans before any mutation happens.

### What problem does wyrmctl solve?

**Answer:** `wyrmctl` replaces manual NPM clicking and one-off API scripts with repeatable desired state, explicit adoption, conflict detection, and controlled reconciliation for reverse-proxy resources.

### Does wyrmctl modify resources it does not own?

**Answer:** No. `wyrmctl` treats NPM resources as owner-scoped, refuses to mutate foreign-owned resources, and only attaches metadata to unmanaged resources when you run `wyrmctl adopt`.

### How does wyrmctl handle certificate issuance and rotation?

**Answer:** `wyrmctl` treats certificates as declarative resources in the same desired state as proxy hosts. Issuance happens when a desired certificate must be created, and rotation happens through explicit reconcile policy rather than hidden mutation of unrelated resources.

### Can wyrmctl adopt existing manually created NPM resources?

**Answer:** Yes. `wyrmctl adopt` can attach wyrmctl ownership metadata to compatible unmanaged resources so future plans and applies can manage them under explicit owner scope.

## Install

Use `pipx` for an isolated CLI install:

```bash
pipx install wyrmctl
wyrmctl --version
```

Use `uv` if you manage tools with uv:

```bash
uv tool install wyrmctl
wyrmctl --help
```

Use `pip` inside an existing virtual environment:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install wyrmctl
wyrmctl --help
```

PowerShell activation:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install wyrmctl
wyrmctl --help
```

## Configure NPM

Set Nginx Proxy Manager API credentials as environment variables:

```bash
export NPM_BASE_URL=http://127.0.0.1:81/api
export NPM_IDENTITY=admin@example.com
export NPM_SECRET=changeme
```

Or pass them directly:

```bash
wyrmctl --base-url http://127.0.0.1:81/api --identity admin@example.com --secret changeme health
```

## Quick Start

Validate desired state without touching the API:

```bash
wyrmctl validate ./desired-state
wyrmctl --output json validate ./desired-state
```

Plan owner-scoped changes:

```bash
wyrmctl plan ./desired-state --owner workload-a
```

Apply a clean plan:

```bash
wyrmctl apply ./desired-state --owner workload-a
```

Adopt unmanaged matching resources:

```bash
wyrmctl adopt ./desired-state --owner workload-a
wyrmctl adopt ./desired-state --owner workload-a --allow-field-drift
```

## Desired State

Every managed resource needs wyrmctl ownership metadata:

```yaml
apiVersion: wyrmctl.com/v1
schemaVersion: 2
proxy_hosts:
  - domain_names: [app.example.com]
    forward_scheme: http
    forward_host: app
    forward_port: 3000
    meta:
      managed_by: wyrmctl
      owner: workload-a
      resource_id: proxy.app
```

References use `resource_id` values:

```yaml
apiVersion: wyrmctl.com/v1
schemaVersion: 2
certificates:
  - name: wildcard-example
    domain_names: ["*.example.com", example.com]
    certificate_type: letsencrypt
    api_payload:
      provider: letsencrypt
    meta:
      managed_by: wyrmctl
      owner: workload-a
      resource_id: cert.wildcard-example
access_lists:
  - name: private-admins
    api_payload:
      satisfy_any: 0
      items: []
      clients: []
    meta:
      managed_by: wyrmctl
      owner: workload-a
      resource_id: acl.private-admins
proxy_hosts:
  - domain_names: [app.example.com]
    forward_host: app
    forward_port: 3000
    certificate_ref: cert.wildcard-example
    access_list_ref: acl.private-admins
    ssl_forced: 1
    allow_websocket_upgrade: 1
    caching_enabled: 1
    block_exploits: 1
    meta:
      managed_by: wyrmctl
      owner: workload-a
      resource_id: proxy.app
```

## More Documentation

- Related PyPI package: https://pypi.org/project/wyrmctl-namecheap/
- Repository: https://github.com/groupsum/wyrmctl
- Examples: https://github.com/groupsum/wyrmctl/tree/master/examples/desired-state
- Docs: https://github.com/groupsum/wyrmctl/tree/master/docs
