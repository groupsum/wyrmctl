# Project tree status

```text
wyrmctl/ [COMPLETE | HARDENED: repo checks passed]
├── .codex/
│   └── agents/
│       ├── api-contracts/
│       │   └── AGENTS.md [COMPLETE | HARDENED: Codex agent guidance]
│       ├── architect/
│       │   └── AGENTS.md [COMPLETE | HARDENED: Codex agent guidance]
│       ├── docs-governance/
│       │   └── AGENTS.md [COMPLETE | HARDENED: Codex agent guidance]
│       ├── release-engineer/
│       │   └── AGENTS.md [COMPLETE | HARDENED: Codex agent guidance]
│       └── test-engineer/
│           └── AGENTS.md [COMPLETE | HARDENED: Codex agent guidance]
├── .github/
│   ├── actions/
│   │   ├── wyrmctl-check/
│   │   │   └── action.yml [COMPLETE | HARDENED: reusable composite action]
│   │   ├── wyrmctl-real-npm-e2e/
│   │   │   └── action.yml [COMPLETE | HARDENED: reusable composite action]
│   │   ├── wyrmctl-release-build/
│   │   │   └── action.yml [COMPLETE | HARDENED: reusable composite action]
│   │   ├── wyrmctl-schema-gate/
│   │   │   └── action.yml [COMPLETE | HARDENED: reusable composite action]
│   │   ├── wyrmctl-ssot-gate/
│   │   │   └── action.yml [COMPLETE | HARDENED: reusable composite action]
│   │   └── setup-uv-python/
│   │       └── action.yml [COMPLETE | HARDENED: reusable composite action]
│   └── workflows/
│       ├── ci.yml [COMPLETE | HARDENED: concurrency + gated workflow]
│       ├── docs-ssot.yml [COMPLETE | HARDENED: concurrency + gated workflow]
│       ├── e2e-npm.yml [COMPLETE | HARDENED: concurrency + gated workflow]
│       └── release.yml [COMPLETE | HARDENED: concurrency + gated workflow]
├── .ssot/
│   ├── adr/
│   │   ├── ADR-0600-canonical-json-registry.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-0601-features-are-targetable-units.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-0602-issues-are-plannable-work-items.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-0603-entity-centric-registry-derived-graph.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-0604-normalized-prefixed-ids.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-0605-claim-status-vs-tier.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-0606-feature-implementation-vs-lifecycle.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-0607-immutable-boundary-and-release-snapshots.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-0608-fail-closed-guards.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-0609-generated-projections-are-non-canonical.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-0610-explicit-schema-versioning.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-0611-portable-core-repo-specific-evidence-adapters.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-0612-ssot-path-and-filename-length-limits.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-0613-profiles-as-reusable-feature-bundles.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-0615-downstream-assurance-language-ceilings.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── ADR-1000-create-only-reconciliation.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   └── ADR-1001-metadata-ownership-markers.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   ├── reports/
│   │   └── validation.report.json [COMPLETE | HARDENED: SSOT registry validated]
│   ├── schemas/
│   │   ├── adr.schema.json [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── boundary.snapshot.schema.json [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── certification.report.schema.json [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── graph.export.schema.json [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── published.snapshot.schema.json [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── registry.schema.json [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── release.snapshot.schema.json [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── spec.schema.json [COMPLETE | HARDENED: SSOT registry validated]
│   │   └── validation.report.schema.json [COMPLETE | HARDENED: SSOT registry validated]
│   ├── specs/
│   │   ├── SPEC-0600-registry-core.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-0601-cli.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-0602-graph-model.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-0603-feature-lifecycle.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-0604-claim-statuses.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-0605-claim-tiers.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-0606-snapshots-and-reports.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-0607-repo-policy.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-0608-gates-and-fences.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-0609-id-normalization.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-0610-file-tree.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-0611-planning-horizons.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-0612-python-api.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-0613-ssot-path-length-policy.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-0614-profile-evaluation-and-boundary-resolution.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   ├── SPEC-1000-create-only-controller-contract.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   │   └── SPEC-1001-metadata-ownership-and-conflict-guards.yaml [COMPLETE | HARDENED: SSOT registry validated]
│   └── registry.json [COMPLETE | HARDENED: SSOT registry validated]
├── branding/
│   ├── badges.md [COMPLETE | HARDENED: branding/crawlable fragments]
│   ├── repo-description.md [COMPLETE | HARDENED: branding/crawlable fragments]
│   ├── seo-snippets.md [COMPLETE | HARDENED: branding/crawlable fragments]
│   └── social-preview-copy.md [COMPLETE | HARDENED: branding/crawlable fragments]
├── deploy/
│   └── npm/
│       ├── compose.ci.yml [COMPLETE | HARDENED: CI-ready NPM compose; local Docker not executed here]
│       ├── docker-compose.yml [COMPLETE | HARDENED: CI-ready NPM compose; local Docker not executed here]
│       ├── env.example [COMPLETE | HARDENED: CI-ready NPM compose; local Docker not executed here]
│       └── README.md [COMPLETE | HARDENED: CI-ready NPM compose; local Docker not executed here]
├── dist/
│   ├── .gitignore [COMPLETE | BUILT: package artifact]
│   ├── wyrmctl-0.2.0-py3-none-any.whl [COMPLETE | BUILT: package artifact]
│   └── wyrmctl-0.2.0.tar.gz [COMPLETE | BUILT: package artifact]
├── docs/
│   ├── adrs/
│   │   ├── ADR-0001-owner-scoped-reconciliation.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   ├── ADR-0002-schema-gated-api-compatibility.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   ├── ADR-0003-managed-metadata-ownership.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   ├── ADR-0004-adoption-semantics.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   └── ADR-0005-github-actions-gated-delivery.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── brand/
│   │   └── identity.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── evidence/
│   │   ├── e2e-real-npm.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   ├── integration-fake-npm.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   ├── unit-client-cli.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   ├── unit-planner.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   └── unit-validation.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── examples/
│   │   └── desired-state.yaml [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── fragments/
│   │   └── badges.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── seo/
│   │   ├── answer-engine-overview.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   └── structured-data.json [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── specs/
│   │   ├── SPEC-access-list-crud.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   ├── SPEC-certificate-crud.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   ├── SPEC-desired-state-schema.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   ├── SPEC-plan-apply-adopt.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   ├── SPEC-proxy-host-crud.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   └── SPEC-schema-migrations.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── ssot/
│   │   ├── adrs.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   ├── claims.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   ├── features.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   ├── index.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   ├── specs.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   │   └── tests.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── access-lists.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── adoption.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── AGENTS.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── cli.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── desired-state.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── github-actions.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── index.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── npm-api-compatibility.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── owner-scoped-reconcile.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── schema-migrations.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── security.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   ├── seo-aeo-aieo.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
│   └── ssl-certificates.md [COMPLETE | HARDENED: docs/ADR/spec/SEO copy linted]
├── examples/
│   ├── desired-state/
│   │   ├── access-list-and-host.yaml [COMPLETE | HARDENED: desired-state/workflow examples linted]
│   │   ├── full-owner-scope.yaml [COMPLETE | HARDENED: desired-state/workflow examples linted]
│   │   ├── minimal-proxy-host.yaml [COMPLETE | HARDENED: desired-state/workflow examples linted]
│   │   ├── proxy-host-with-existing-cert.yaml [COMPLETE | HARDENED: desired-state/workflow examples linted]
│   │   └── wildcard-cert-and-host.yaml [COMPLETE | HARDENED: desired-state/workflow examples linted]
│   └── github-actions/
│       ├── apply-owned-resources.yml [COMPLETE | HARDENED: desired-state/workflow examples linted]
│       ├── gated-release.yml [COMPLETE | HARDENED: desired-state/workflow examples linted]
│       └── real-npm-e2e.yml [COMPLETE | HARDENED: desired-state/workflow examples linted]
├── packages/
│   └── wyrmctl/
│       ├── src/
│       │   └── wyrmctl/
│       │       ├── client/
│       │       │   ├── __init__.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       │   ├── access_lists.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       │   ├── auth.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       │   ├── base.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       │   ├── certificates.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       │   ├── contracts.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       │   └── proxy_hosts.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── migrations/
│       │       │   ├── __init__.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       │   ├── base.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       │   ├── registry.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       │   └── v1.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── __init__.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── __main__.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── adoption.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── apply.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── cli.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── errors.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── loader.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── logging.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── metadata.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── models.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── output.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── planner.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── py.typed [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       ├── schema.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       │       └── validation.py [COMPLETE | HARDENED: typed core, owner-scoped, ruff+pytest]
│       ├── tests/
│       │   ├── e2e/
│       │   │   ├── test_real_npm_access_lists.py [COMPLETE | HARDENED: real NPM pytest, opt-in/workflow-run]
│       │   │   ├── test_real_npm_certificates.py [COMPLETE | HARDENED: real NPM pytest, opt-in/workflow-run]
│       │   │   ├── test_real_npm_health_auth.py [COMPLETE | HARDENED: real NPM pytest, opt-in/workflow-run]
│       │   │   └── test_real_npm_proxy_hosts.py [COMPLETE | HARDENED: real NPM pytest, opt-in/workflow-run]
│       │   ├── integration/
│       │   │   └── test_fake_npm_api.py [COMPLETE | HARDENED: fake NPM integration pytest passing]
│       │   ├── unit/
│       │   │   ├── test_loader_migrations.py [COMPLETE | HARDENED: unit pytest passing]
│       │   │   ├── test_metadata.py [COMPLETE | HARDENED: unit pytest passing]
│       │   │   ├── test_models.py [COMPLETE | HARDENED: unit pytest passing]
│       │   │   ├── test_planner.py [COMPLETE | HARDENED: unit pytest passing]
│       │   │   └── test_schema.py [COMPLETE | HARDENED: unit pytest passing]
│       │   └── conftest.py [COMPLETE | HARDENED: unit pytest passing]
│       ├── AGENTS.md [COMPLETE | HARDENED: Codex agent guidance]
│       ├── pyproject.toml [COMPLETE | HARDENED]
│       └── README.md [COMPLETE | HARDENED]
├── schemas/
│   ├── npm/
│   │   └── 2.10.4/
│   │       ├── endpoint-capabilities.json [COMPLETE | HARDENED: JSON schema/capability contract validated]
│   │       └── openapi.json [COMPLETE | HARDENED: JSON schema/capability contract validated]
│   └── wyrmctl/
│       ├── desired-state.v1.schema.json [COMPLETE | HARDENED: JSON schema/capability contract validated]
│       ├── migration-manifest.schema.json [COMPLETE | HARDENED: JSON schema/capability contract validated]
│       └── plan-output.v1.schema.json [COMPLETE | HARDENED: JSON schema/capability contract validated]
├── scripts/
│   ├── capture_npm_schema.py [COMPLETE | HARDENED: automation utility checked]
│   ├── check.sh [COMPLETE | HARDENED: automation utility checked]
│   ├── render_ssot_docs.py [COMPLETE | HARDENED: automation utility checked]
│   └── validate_schemas.py [COMPLETE | HARDENED: automation utility checked]
├── tools/
│   └── render_ssot_docs.py [COMPLETE | HARDENED: automation utility checked]
├── .gitignore [COMPLETE | HARDENED: repo metadata/documentation]
├── .yamllint.yml [COMPLETE | HARDENED: workspace/tooling config verified]
├── AGENTS.md [COMPLETE | HARDENED: Codex agent guidance]
├── LICENSE [COMPLETE | HARDENED: repo metadata/documentation]
├── mkdocs.yml [COMPLETE | HARDENED: repo metadata/documentation]
├── PROJECT_TREE_STATUS.md [COMPLETE | HARDENED: generated completion/hardening inventory]
├── pyproject.toml [COMPLETE | HARDENED: workspace/tooling config verified]
├── README.md [COMPLETE | HARDENED: repo metadata/documentation]
├── ruff.toml [COMPLETE | HARDENED: workspace/tooling config verified]
└── uv.lock [COMPLETE | HARDENED: workspace/tooling config verified]
```
