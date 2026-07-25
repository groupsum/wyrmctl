<h1 align="center">wyrmctl</h1>

<p align="center"><strong>Portwyrm owner-scoped GitOps CLI for Nginx Proxy Manager</strong></p>

<p align="center">
  Validate desired-state YAML, plan safe owner-scoped changes, apply clean reconciles, and adopt existing NPM resources only when you ask for it.
</p>

<p align="center">
  <a href="https://pypi.org/project/wyrmctl/"><img src="https://img.shields.io/pypi/v/wyrmctl.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/wyrmctl/"><img src="https://img.shields.io/pypi/pyversions/wyrmctl.svg" alt="Python versions"></a>
  <a href="https://github.com/groupsum/wyrmctl/actions/workflows/ci.yml"><img src="https://github.com/groupsum/wyrmctl/actions/workflows/ci.yml/badge.svg?branch=master" alt="CI"></a>
  <a href="https://github.com/groupsum/wyrmctl/actions/workflows/python-matrix.yml"><img src="https://github.com/groupsum/wyrmctl/actions/workflows/python-matrix.yml/badge.svg?branch=master" alt="Python Matrix"></a>
  <a href="https://github.com/groupsum/wyrmctl/actions/workflows/live-npm-gate.yml"><img src="https://github.com/groupsum/wyrmctl/actions/workflows/live-npm-gate.yml/badge.svg?branch=master" alt="Live NPM Gate"></a>
  <a href="https://github.com/groupsum/wyrmctl/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="Apache 2.0 License"></a>
</p>

<p align="center">
  <a href="https://hits.sh/github.com/groupsum/wyrmctl/blob/master/README.md/"><img src="https://hits.sh/github.com/groupsum/wyrmctl/blob/master/README.md.svg?label=wyrmctl%20repository%20hits" alt="wyrmctl repository hits"></a>
  <a href="https://pepy.tech/projects/wyrmctl"><img src="https://static.pepy.tech/badge/wyrmctl" alt="wyrmctl downloads"></a>
  <a href="https://pepy.tech/projects/wyrmctl-namecheap"><img src="https://static.pepy.tech/badge/wyrmctl-namecheap" alt="wyrmctl-namecheap downloads"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/groupsum/wyrmctl/master/docs/images/marketing/wyrmctl-architecture-infographic.png" alt="wyrmctl architecture infographic">
</p>

`wyrmctl` is the dedicated Portwyrm CLI helper for Nginx Proxy Manager. Portwyrm provides the service and control-plane surface; wyrmctl provides the operator-facing Python CLI for validating desired state, planning safe changes against a live NPM API, applying clean plans, and explicitly adopting unmanaged resources.


## Portwyrm relationship

`wyrmctl` is part of the [Portwyrm](https://github.com/groupsum/portwyrm) project. Use it when you want Portwyrm-compatible desired-state validation, owner-scoped planning, NPM reconciliation, DNS provider discovery, and operator diagnostics from a local shell, CI job, or `uv` tool environment.

Portwyrm remains the service/control-plane repository. `wyrmctl` is its dedicated CLI/helper distribution. The `npmctl` profile and `npmctl` aliases remain available only for compatibility with existing Nginx Proxy Manager workflows; new Portwyrm integrations should use the native `wyrmctl` profile and `wyrmctl.*` contracts.

- Portwyrm: [github.com/groupsum/portwyrm](https://github.com/groupsum/portwyrm)
- Wyrmctl: [github.com/groupsum/wyrmctl](https://github.com/groupsum/wyrmctl)
- Container distribution: [ghcr.io/groupsum/portwyrm](https://github.com/groupsum/portwyrm/pkgs/container/portwyrm)

### Portwyrm distribution status

Portwyrm currently publishes its canonical runtime image through [GHCR](https://github.com/groupsum/portwyrm/pkgs/container/portwyrm). The Portwyrm Python project metadata and release workflow also reserve the [PyPI project](https://pypi.org/project/portwyrm/), but that distribution is not published yet. The recommended model is to keep GHCR as the production runtime channel and publish PyPI for Python-native embedding, local development, CLI-adjacent automation, and integration testing once the release gates and package scope are finalized.
## Versioned execution

wyrmctl 0.4 adds independently versioned contracts, DesiredState v3, canonical semantic digests, repository manifests, lockfiles, immutable plan artifacts, transactional migration manifests, provider capability negotiation, and stable machine-readable command results.

```bash
wyrmctl contract list
wyrmctl repo validate .wyrmctl/repository.yaml
wyrmctl plan .wyrmctl/production --artifact-out .wyrmctl/artifacts/plan.yaml \
  --repository groupsum/example --environment production --commit "$GITHUB_SHA"
wyrmctl apply --artifact .wyrmctl/artifacts/plan.yaml \
  --repository groupsum/example --environment production --commit "$GITHUB_SHA"
```

Ordinary plan artifacts may create, update, or verify resources. Adoption, transfer, prune, and delete require an explicit reviewed migration artifact.

## FAQ

### What is wyrmctl?

**Answer:** `wyrmctl` is a declarative controller for Nginx Proxy Manager that turns YAML desired state into safe owner-scoped plans, applies clean reconciles, and blocks unsafe mutations before they hit production.

### What problem does wyrmctl solve?

**Answer:** `wyrmctl` replaces manual NPM clicking and brittle API scripts with repeatable plan/apply/adopt workflows for proxy hosts, certificates, access lists, and related resources.

### Does wyrmctl modify resources it does not own?

**Answer:** No. `wyrmctl` treats NPM resources as owner-scoped, refuses to mutate foreign-owned resources, and requires explicit adoption before unmanaged resources come under wyrmctl control.

### How does wyrmctl handle certificate issuance and rotation?

**Answer:** `wyrmctl` treats certificates as declarative resources in desired state. Issuance happens when a desired certificate must be created, and rotation is controlled through reconcile policy rather than implicit side effects during unrelated repair work.

### Can wyrmctl adopt existing manual resources safely?

**Answer:** Yes. `wyrmctl adopt` is the explicit path for attaching wyrmctl ownership metadata to compatible unmanaged resources so later plans and applies remain conservative and traceable.

It manages:

- Proxy hosts
- SSL certificates
- Access lists
- Redirection hosts
- Dead hosts
- Streams
- Users
- Settings
- Provider-backed DNS records

It also provides read-only audit log reporting, operator diagnostics, compliance
artifact generation, and plugin contracts for future custom resource and
certificate and DNS providers.

## Safety Model

- Every managed resource must carry `meta.managed_by: wyrmctl`, `meta.owner`, and `meta.resource_id`.
- `--owner` limits planning and mutation to one owner scope.
- Foreign-owned resources are immutable to the current owner.
- Unmanaged resources are not changed by `plan` or `apply`; use `adopt` to attach wyrmctl metadata.
- Deletes are opt-in with `--prune-owned`.
- API operations are gated by the NPM OpenAPI schema and fail closed when a required endpoint is unavailable.

## Requirements

- Python `3.10`, `3.11`, `3.12`, `3.13`, or `3.14`
- Access to a Nginx Proxy Manager API, usually `http://host:81/api`
- NPM admin credentials or an account with permissions for the resources you want to manage
- Optional for local development: Docker and Docker Compose

## Install

Install the published CLI with `pipx`:

```bash
pipx install wyrmctl
wyrmctl --version
wyrmctl --help
```

Install with `uv` as a tool:

```bash
uv tool install wyrmctl
wyrmctl --help
```

Install from a local checkout:

```bash
git clone https://github.com/groupsum/wyrmctl.git
cd wyrmctl
uv sync
uv run wyrmctl --help
```

Run directly from the workspace while developing:

```bash
uv run wyrmctl validate examples/desired-state
uv run pytest
```

## Configure API Access

You can pass API credentials on every command:

```bash
wyrmctl --base-url http://127.0.0.1:81/api --identity admin@example.com --secret changeme health
```

For regular use, set environment variables:

```bash
export NPM_BASE_URL=http://127.0.0.1:81/api
export NPM_IDENTITY=admin@example.com
export NPM_SECRET=changeme
export NPM_TIMEOUT_S=15
```

PowerShell:

```powershell
$env:NPM_BASE_URL = "http://127.0.0.1:81/api"
$env:NPM_IDENTITY = "admin@example.com"
$env:NPM_SECRET = "changeme"
$env:NPM_TIMEOUT_S = "15"
```

Then verify connectivity:

```bash
wyrmctl health
```

## Local NPM Stack

The repo includes a SQLite-backed NPM stack for local testing:

```bash
docker compose -f deploy/npm/docker-compose.yml up -d
export NPM_BASE_URL=http://127.0.0.1:81/api
export NPM_IDENTITY=admin@example.com
export NPM_SECRET=changeme
wyrmctl health
```

For details, see [deploy/npm/README.md](deploy/npm/README.md).

## Desired State

A minimal proxy host:

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

A proxy host with certificate and access-list references:

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
    forward_scheme: http
    forward_host: app
    forward_port: 3000
    certificate_ref: cert.wildcard-example
    access_list_ref: acl.private-admins
    ssl_forced: 1
    http2_support: 1
    allow_websocket_upgrade: 1
    caching_enabled: 1
    block_exploits: 1
    meta:
      managed_by: wyrmctl
      owner: workload-a
      resource_id: proxy.app
```

More examples are in [examples/desired-state](examples/desired-state).

## Usage

Validate desired state without calling NPM:

```bash
wyrmctl validate examples/desired-state
wyrmctl --output json validate examples/desired-state
```

Check whether files need schema migration:

```bash
wyrmctl migrate examples/desired-state --check
wyrmctl migrate examples/desired-state --write
```

Fetch the live NPM OpenAPI schema:

```bash
wyrmctl schema fetch --write schemas/npm/live-openapi.json
```

Inspect endpoint capabilities from a schema file or from the live API:

```bash
wyrmctl schema capabilities --schema schemas/npm/2.10.4/openapi.json
wyrmctl schema capabilities
wyrmctl schema check
```

Plan owner-scoped changes:

```bash
wyrmctl plan examples/desired-state --owner workload-a
wyrmctl --output json plan examples/desired-state --owner workload-a
```

Apply a clean plan:

```bash
wyrmctl apply examples/desired-state --owner workload-a
```

Preview the apply path without mutation:

```bash
wyrmctl apply examples/desired-state --owner workload-a --dry-run
```

Delete owned resources that are no longer present in desired state:

```bash
wyrmctl apply examples/desired-state --owner workload-a --prune-owned
```

Adopt unmanaged matching resources by writing wyrmctl metadata:

```bash
wyrmctl adopt examples/desired-state --owner workload-a
```

Strict adoption requires the unmanaged resource fields to match desired state. To allow field drift while attaching metadata:

```bash
wyrmctl adopt examples/desired-state --owner workload-a --allow-field-drift
```

## Operational Flow

1. Author YAML with explicit `meta.owner` and `meta.resource_id`.
2. Run `wyrmctl validate`.
3. Run `wyrmctl schema check` against the target NPM instance.
4. Run `wyrmctl plan --owner <owner>`.
5. Review creates, updates, deletes, adopts, noops, and conflicts.
6. Run `wyrmctl apply --owner <owner>` only when the plan is clean.
7. Use `--prune-owned` only when absent owned resources should be deleted.

## Exit Codes

- `0`: success
- `1`: plan conflict
- `2`: usage, validation, or migration error
- `3`: API error
- `4`: endpoint capability error

## Development

Run the normal local checks:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv build --package wyrmctl
```

Run real NPM E2E tests against the bundled CI stack:

```bash
docker compose -f deploy/npm/compose.ci.yml up -d
export NPMCTL_REAL_NPM=1
export NPM_BASE_URL=http://127.0.0.1:8181/api
export NPM_IDENTITY=admin@example.com
export NPM_SECRET=changeme
uv run pytest --no-cov -m npm packages/wyrmctl/tests/e2e
docker compose -f deploy/npm/compose.ci.yml down
```

## Documentation

- [Portwyrm relationship](docs/index.md)
- [CLI](docs/cli.md)
- [Desired state](docs/desired-state.md)
- [Owner-scoped reconciliation](docs/owner-scoped-reconcile.md)
- [Schema migrations](docs/schema-migrations.md)
- [NPM API compatibility](docs/npm-api-compatibility.md)
- [SSL certificates](docs/ssl-certificates.md)
- [Access lists](docs/access-lists.md)
- [DNS records](docs/dns.md)
- [DNS provider packages](docs/dns-providers.md)
- [Namecheap DNS extension](docs/namecheap.md)
- [Adoption](docs/adoption.md)
- [GitHub Actions](docs/github-actions.md)
