# Repair-safe certificate reconciliation implementation

Date: 2026-11-01

Implemented boundary: `bnd:npmctl-repair-safe-certificate-reconciliation`

Delivered behavior:

- adopt supports `--metadata-only` and `--only ...` resource-family scoping
- planner distinguishes compatible unmanaged resources that are adoptable from unmanaged conflicts that remain unsafe
- certificate reconcile supports `--certificate-mode=reuse|create|rotate`
- compatible live certificates are reused by normalized provider and domain set when policy allows reuse
- owner-scoped Let's Encrypt domain-set updates force-renew certificate material and re-read the resulting certificate before apply reports success
- metadata-only, no-op, and custom-certificate updates do not trigger renewal
- certificate domain-set updates fail before mutation when forced renewal or certificate readback is unavailable
- certificate issuance attempts are deduplicated locally while in flight and cooled down after failure
- certificate lock contention and stale order failures are emitted as structured certificate errors for automation

Verification sources:

- `packages/wyrmctl/tests/unit/test_planner.py`
- `packages/wyrmctl/tests/unit/test_apply.py`
- `packages/wyrmctl/tests/unit/test_client_base.py`
- `packages/wyrmctl/tests/unit/test_schema.py`
- `packages/wyrmctl/tests/unit/test_repair_safe_certificates.py`
- `packages/wyrmctl/tests/integration/test_fake_npm_api.py`
