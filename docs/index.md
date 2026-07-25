# wyrmctl documentation

`wyrmctl` is the dedicated Portwyrm CLI helper for Nginx Proxy Manager. It provides the local and CI-facing command surface for desired-state validation, owner-scoped planning and reconciliation, DNS provider operations, migrations, diagnostics, and release evidence.

Portwyrm is the service and control-plane project. This repository contains the reusable Python CLI and provider packages that Portwyrm operators can install and run independently.


## Portwyrm distribution status

Portwyrm currently has a public [GHCR container package](https://github.com/groupsum/portwyrm/pkgs/container/portwyrm). Its Python metadata and release workflow are prepared for [PyPI](https://pypi.org/project/portwyrm/), but the PyPI project is not published yet.

The recommended distribution model is both channels with clear roles:

- GHCR is the canonical production channel for the complete Portwyrm service, UI, API, and database-backed runtime.
- PyPI is the Python-native channel for embedding, local development, CLI-adjacent automation, integration tests, and environments that do not need the full container runtime.

The two artifacts should share the same version and release provenance, while documentation makes clear that installing the PyPI package is not equivalent to deploying the production container.
## Product relationship

- [Portwyrm](https://github.com/groupsum/portwyrm): service, API, persistence, and control-plane distribution.
- [wyrmctl](https://github.com/groupsum/wyrmctl): Portwyrm operator CLI/helper and Python provider packages.
- [npmctl](https://github.com/groupsum/npmctl): compatibility-facing CLI that depends on Wyrmctl components and exposes npmctl-specific aliases.

Use native `wyrmctl` commands and `wyrmctl.com/v1` documents for new Portwyrm work. Existing `npmctl` profiles and `npmctl.com/v1` documents remain supported as compatibility surfaces.