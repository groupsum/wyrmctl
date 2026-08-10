# Portwyrm / wyrmctl GitHub Actions

The repository contains the Portwyrm CLI helper local composite actions and gated workflows.

## Local actions

- `.github/actions/setup-uv-python`
- `.github/actions/wyrmctl-check`
- `.github/actions/wyrmctl-schema-gate`
- `.github/actions/wyrmctl-ssot-gate`
- `.github/actions/wyrmctl-real-npm-e2e`
- `.github/actions/wyrmctl-release-build`

## Workflows

- `CI`: lint, format, YAML lint, pytest, schema gate.
- `Docs and SSOT`: runs after CI succeeds.
- `Python Matrix`: runs pytest on Python 3.10, 3.11, 3.12, 3.13, and 3.14.
- `Live NPM Gate`: starts Nginx Proxy Manager in Docker and runs opt-in pytest E2E.
- `Release`: dispatches CI, Docs/SSOT, `Python Matrix`, and `Live NPM Gate`, waits for all to pass on the release ref, then builds. When PyPI publishing is enabled, PyPI upload must succeed before the GitHub Release is created or updated. Dispatch checkboxes control GitHub Release creation and PyPI publishing.

Each workflow uses concurrency groups to avoid overlapping mutable runs.

## PyPI Publishing

The `Release` workflow can publish Python distributions after the required
release gates pass. Publication happens before the GitHub Release step so a
package publish failure does not leave a GitHub-only release artifact behind.

The core `wyrmctl` distribution is the default PyPI publication scope. Optional
provider distributions remain attached to the GitHub Release and are included
in the PyPI upload only when `publish_provider_packages` is explicitly enabled.
