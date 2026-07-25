# wyrmctl CLI reference

This is the operator CLI for [Portwyrm](https://github.com/groupsum/portwyrm).

## Commands

- `wyrmctl validate PATH`: validate desired state and metadata.
- `wyrmctl migrate PATH --check|--write`: check or write schema migrations.
- `wyrmctl schema fetch`: fetch `/schema` from NPM.
- `wyrmctl schema capabilities`: print endpoint capabilities.
- `wyrmctl schema check`: require proxy-host CRUD endpoints.
- `wyrmctl plan PATH`: compute side-effect-free plan.
- `wyrmctl apply PATH`: apply a clean plan.
- `wyrmctl adopt PATH`: explicitly adopt unmanaged matching resources.
- `wyrmctl drift PATH`: report remote drift without mutation.
- `wyrmctl doctor`: diagnose config, API reachability, and capabilities.
- `wyrmctl env`: show redacted environment diagnostics.
- `wyrmctl version --json`: show machine-readable package metadata.
- `wyrmctl contract list|show|check`: inspect independent contract compatibility.
- `wyrmctl repo validate|status`: validate a repository manifest and resolve an environment.
- `wyrmctl lock check EXPECTED ACTUAL`: compare reproducibility pins.
- `wyrmctl artifact inspect|digest`: validate and identify immutable artifacts.
- `wyrmctl completion bash|powershell|zsh`: generate shell completion output.
- `wyrmctl audit-log`: read NPM audit log entries.
- `wyrmctl compliance artifacts --output-dir DIR`: generate SBOM, provenance, scan, and gate artifacts.
- `wyrmctl compliance gate --artifact-dir DIR`: fail closed when required compliance artifacts are missing or failing.
- `wyrmctl plugins list`: discover configured and entry-point plugin providers.
- `wyrmctl dns providers`: list discovered DNS providers.
- `wyrmctl dns doctor --provider PROVIDER`: validate one DNS provider is loaded.
- `wyrmctl dns zones --provider PROVIDER`: list zones for one DNS provider.
- `wyrmctl dns records --provider PROVIDER --zone ZONE`: list records for one DNS provider zone.

## Common options

- `--owner OWNER`: scope plan/apply/adopt to one owner.
- `--output text|json`: human or machine-readable output.
- `--no-updates`: turn owned drift into a conflict.
- `--prune-owned`: delete owned resources absent from desired state.
- `--config FILE`: load `[wyrmctl]` TOML configuration.
- `--validate-output`: validate plan output shape.
- `--backup-dir DIR`, `--report PATH`, `--rollback-plan PATH`, `--audit-log PATH`: write apply artifacts.

## Reviewed artifacts

Use `wyrmctl plan PATH --artifact-out PLAN --repository ORG/REPO
--environment production --commit SHA` to persist exact ordered operations.
Apply the reviewed result with `wyrmctl apply --artifact PLAN` and the same
binding values. Changed commits, live state, NPM API profiles, environments,
repositories, or expiry timestamps fail before
mutation.
