# Features

Generated entries: 214

| id | title | implementation_status | horizon | target_tier | claims | tests |
| --- | --- | --- | --- | --- | --- | --- |
| feat:access-list-crud | Owner-scoped ACL CRUD | implemented | current | T2 | clm:owner-scoped-integrity | tst:e2e-real-npm, tst:integration-fake-npm, tst:unit-planner |
| feat:adopt-metadata-only | Metadata-only adoption | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-adoption-controls | tst:expanded-feature-scope-planning, tst:repair-safe-adoption-controls |
| feat:adopt-resource-family-scope | Resource-family repair scope | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-adoption-controls | tst:expanded-feature-scope-planning, tst:repair-safe-adoption-controls |
| feat:adoption | Explicit adoption of unmanaged resources | implemented | current | T2 | clm:owner-scoped-integrity | tst:e2e-real-npm, tst:integration-fake-npm, tst:unit-planner |
| feat:apply-reviewed-plan-artifact | Apply reviewed plan artifact | implemented | backlog |  | clm:versioning-migration-contracts | tst:plan-artifact-tamper-rejection |
| feat:apply-structured-certificate-error-output | Structured certificate apply error output | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-certificate-issuance-safety | tst:expanded-feature-scope-planning, tst:repair-safe-certificate-issuance-safety |
| feat:artifact-data-minimization | Artifact data minimization | implemented | backlog |  | clm:versioning-migration-contracts | tst:snapshot-sensitive-field-omission |
| feat:artifact-retention-policy | Artifact retention policy | implemented | backlog |  | clm:versioning-migration-contracts | tst:artifact-retention-expiry |
| feat:artifact-secret-redaction | Artifact secret redaction | implemented | backlog |  | clm:versioning-migration-contracts | tst:artifact-secret-redaction |
| feat:artifact-signature-verification | Artifact signature verification | implemented | backlog |  | clm:versioning-migration-contracts | tst:artifact-valid-signature, tst:artifact-invalid-signature |
| feat:auth-token | Authenticate to NPM API | implemented | current | T2 | clm:create-only-integrity | tst:e2e-real-npm, tst:integration-fake-npm, tst:unit-client-cli |
| feat:canonical-document-digests | Canonical document digests | absent | backlog |  | clm:versioning-migration-contracts | tst:canonical-digest-stability |
| feat:certificate-crud | Owner-scoped SSL certificate CRUD | implemented | current | T2 | clm:owner-scoped-integrity | tst:e2e-real-npm, tst:integration-fake-npm, tst:unit-planner |
| feat:certificate-domain-set-reuse-detection | Certificate domain-set reuse detection | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-certificate-policy | tst:expanded-feature-scope-planning, tst:repair-safe-certificate-policy |
| feat:certificate-failure-classification | Structured certificate failure classification | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-certificate-issuance-safety | tst:expanded-feature-scope-planning, tst:repair-safe-certificate-issuance-safety |
| feat:certificate-issuance-cooldown | Certificate issuance cooldown | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-certificate-issuance-safety | tst:expanded-feature-scope-planning, tst:repair-safe-certificate-issuance-safety |
| feat:certificate-issuance-deduplication | Certificate issuance deduplication | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-certificate-issuance-safety | tst:expanded-feature-scope-planning, tst:repair-safe-certificate-issuance-safety |
| feat:certificate-lock-retryable-class | Retryable certificate lock class | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-certificate-issuance-safety | tst:expanded-feature-scope-planning, tst:repair-safe-certificate-issuance-safety |
| feat:certificate-order-stale-class | Stale certificate order class | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-certificate-issuance-safety | tst:expanded-feature-scope-planning, tst:repair-safe-certificate-issuance-safety |
| feat:certificate-policy-mode-create | Certificate policy mode create | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-certificate-policy | tst:expanded-feature-scope-planning, tst:repair-safe-certificate-policy |
| feat:certificate-policy-mode-reuse | Certificate policy mode reuse | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-certificate-policy | tst:expanded-feature-scope-planning, tst:repair-safe-certificate-policy |
| feat:certificate-policy-mode-rotate | Certificate policy mode rotate | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-certificate-policy | tst:expanded-feature-scope-planning, tst:repair-safe-certificate-policy |
| feat:ci-real-npm-coverage-artifact | Real NPM coverage artifact | implemented | explicit | T2 | clm:conformance-release-blocking-live-npm, clm:expanded-feature-scope-planning | tst:conformance-release-blocking-live-npm, tst:expanded-feature-scope-planning |
| feat:ci-real-npm-scheduled-e2e | Scheduled live NPM gate CI | implemented | explicit | T2 | clm:conformance-release-blocking-live-npm, clm:expanded-feature-scope-planning | tst:conformance-release-blocking-live-npm, tst:expanded-feature-scope-planning |
| feat:cli-completion | CLI shell completions | implemented | explicit | T2 | clm:cli-operator-certification, clm:expanded-feature-scope-planning | tst:cli-operator-certification, tst:expanded-feature-scope-planning |
| feat:cli-config-file | CLI config file | implemented | explicit | T2 | clm:cli-operator-certification, clm:expanded-feature-scope-planning | tst:cli-operator-certification, tst:expanded-feature-scope-planning |
| feat:cli-doctor | CLI doctor diagnostics | implemented | explicit | T2 | clm:cli-operator-certification, clm:expanded-feature-scope-planning | tst:cli-operator-certification, tst:expanded-feature-scope-planning |
| feat:cli-env-diagnostics | CLI environment diagnostics | implemented | explicit | T2 | clm:cli-operator-certification, clm:expanded-feature-scope-planning | tst:cli-operator-certification, tst:expanded-feature-scope-planning |
| feat:cli-plan-output-schema-validation | CLI plan output schema validation | implemented | explicit | T2 | clm:cli-operator-certification, clm:expanded-feature-scope-planning | tst:cli-operator-certification, tst:expanded-feature-scope-planning |
| feat:cli-stable-error-envelope | Stable versioned CLI error envelope | absent | backlog |  | clm:versioning-migration-contracts | tst:cli-versioned-error-envelope |
| feat:cli-stable-exit-code-contract | Stable CLI exit-code contract | partial | backlog |  | clm:versioning-migration-contracts | tst:cli-versioned-exit-code-matrix |
| feat:cli-surface | Operator CLI surface | implemented | current | T2 | clm:create-only-integrity | tst:unit-client-cli |
| feat:cli-version-json | CLI JSON version output | implemented | explicit | T2 | clm:cli-operator-certification, clm:expanded-feature-scope-planning | tst:cli-operator-certification, tst:expanded-feature-scope-planning |
| feat:cloudflare-dns-provider | Cloudflare DNS provider package | implemented | current | T2 | clm:plugin-runtime-certification | tst:plugin-runtime-certification, tst:cloudflare-supported-record-type-writes |
| feat:complete-zone-lock-policy | Complete-zone mutation lock policy | partial | backlog |  | clm:versioning-migration-contracts | tst:complete-zone-concurrency |
| feat:compliance-dependency-vulnerability-gate | Dependency vulnerability compliance gate | implemented | explicit | T2 | clm:compliance-real-oss-release, clm:expanded-feature-scope-planning | tst:compliance-real-oss-release, tst:expanded-feature-scope-planning |
| feat:compliance-owner-scope-safety-profile | Owner scope safety compliance profile | implemented | explicit | T2 | clm:compliance-real-oss-release, clm:expanded-feature-scope-planning | tst:compliance-real-oss-release, tst:expanded-feature-scope-planning |
| feat:compliance-provenance-attestation | Release provenance attestation | implemented | explicit | T2 | clm:compliance-real-oss-release, clm:expanded-feature-scope-planning | tst:compliance-real-oss-release, tst:expanded-feature-scope-planning |
| feat:compliance-real-oss-artifacts | Real OSS compliance artifacts | implemented | explicit | T2 | clm:compliance-real-oss-release | tst:compliance-real-oss-release |
| feat:compliance-release-gate-profile | Release gate compliance profile | implemented | explicit | T2 | clm:compliance-real-oss-release, clm:expanded-feature-scope-planning | tst:compliance-real-oss-release, tst:expanded-feature-scope-planning |
| feat:compliance-sbom | Release SBOM | implemented | explicit | T2 | clm:compliance-real-oss-release, clm:expanded-feature-scope-planning | tst:compliance-real-oss-release, tst:expanded-feature-scope-planning |
| feat:compliance-security-scan-gate | Security scan compliance gate | implemented | explicit | T2 | clm:compliance-real-oss-release, clm:expanded-feature-scope-planning | tst:compliance-real-oss-release, tst:expanded-feature-scope-planning |
| feat:conformance-live-api-version-matrix | Live API version conformance matrix | implemented | explicit | T2 | clm:conformance-release-blocking-live-npm, clm:expanded-feature-scope-planning | tst:conformance-release-blocking-live-npm, tst:expanded-feature-scope-planning |
| feat:conformance-npm-2-10-4-api-profile | NPM 2.10.4 API conformance profile | implemented | explicit | T2 | clm:conformance-release-blocking-live-npm, clm:expanded-feature-scope-planning | tst:conformance-release-blocking-live-npm, tst:expanded-feature-scope-planning |
| feat:conformance-openapi-subset-doc | OpenAPI subset conformance document | implemented | explicit | T2 | clm:conformance-release-blocking-live-npm, clm:expanded-feature-scope-planning | tst:conformance-release-blocking-live-npm, tst:expanded-feature-scope-planning |
| feat:conformance-release-blocking-live-npm | Release-blocking live NPM conformance | implemented | explicit | T2 | clm:conformance-release-blocking-live-npm | tst:conformance-release-blocking-live-npm |
| feat:conformance-schema-drift-report | Schema drift conformance report | implemented | explicit | T2 | clm:conformance-release-blocking-live-npm, clm:expanded-feature-scope-planning | tst:conformance-release-blocking-live-npm, tst:expanded-feature-scope-planning |
| feat:contract-compatibility-policy | Contract compatibility policy | implemented | backlog |  | clm:versioning-migration-contracts | tst:contract-future-version-rejection, tst:contract-deprecation-policy |
| feat:contract-registry | Versioned contract registry | implemented | backlog |  | clm:versioning-migration-contracts | tst:contract-version-matrix |
| feat:contract-version-reporting | Contract version reporting | implemented | backlog |  | clm:versioning-migration-contracts | tst:contract-version-matrix |
| feat:coverage-cli-exception-branches | CLI exception branch coverage | implemented | explicit | T2 | clm:coverage-total-100-percent, clm:expanded-feature-scope-planning | tst:coverage-total-100-percent, tst:expanded-feature-scope-planning |
| feat:coverage-client-auth-wrapper | Client auth wrapper coverage | implemented | explicit | T2 | clm:coverage-total-100-percent, clm:expanded-feature-scope-planning | tst:coverage-total-100-percent, tst:expanded-feature-scope-planning |
| feat:coverage-client-wrapper-functions | Client wrapper coverage | implemented | explicit | T2 | clm:coverage-total-100-percent, clm:expanded-feature-scope-planning | tst:coverage-total-100-percent, tst:expanded-feature-scope-planning |
| feat:coverage-entrypoint-main | Entrypoint coverage | implemented | explicit | T2 | clm:coverage-total-100-percent, clm:expanded-feature-scope-planning | tst:coverage-total-100-percent, tst:expanded-feature-scope-planning |
| feat:coverage-logging-redaction | Logging redaction coverage | implemented | explicit | T2 | clm:coverage-total-100-percent, clm:expanded-feature-scope-planning | tst:coverage-total-100-percent, tst:expanded-feature-scope-planning |
| feat:coverage-model-validation-edges | Model validation edge coverage | implemented | explicit | T2 | clm:coverage-total-100-percent, clm:expanded-feature-scope-planning | tst:coverage-total-100-percent, tst:expanded-feature-scope-planning |
| feat:coverage-total-100-percent | 100 percent statement and branch coverage | implemented | explicit | T2 | clm:coverage-total-100-percent | tst:coverage-total-100-percent |
| feat:coverage-validation-module | Validation module coverage | implemented | explicit | T2 | clm:coverage-total-100-percent, clm:expanded-feature-scope-planning | tst:coverage-total-100-percent, tst:expanded-feature-scope-planning |
| feat:create-missing-proxy-hosts | Create missing proxy hosts | implemented | current | T2 | clm:create-only-integrity | tst:e2e-real-npm, tst:integration-fake-npm, tst:unit-planner |
| feat:deterministic-plan-artifact | Deterministic plan artifact | implemented | backlog |  | clm:versioning-migration-contracts | tst:repeated-plan-determinism, tst:operation-order-determinism |
| feat:dev-coverage-threshold-ratchet | Development coverage threshold ratchet | implemented | explicit | T2 | clm:coverage-total-100-percent, clm:expanded-feature-scope-planning | tst:coverage-total-100-percent, tst:expanded-feature-scope-planning |
| feat:dev-real-e2e-coverage-measurement | Live NPM Gate coverage measurement | implemented | explicit | T2 | clm:conformance-release-blocking-live-npm, clm:expanded-feature-scope-planning | tst:conformance-release-blocking-live-npm, tst:expanded-feature-scope-planning |
| feat:dev-schema-fixture-roundtrip | Schema fixture roundtrip gate | implemented | explicit | T2 | clm:development-gate-certification, clm:expanded-feature-scope-planning | tst:development-gate-certification, tst:expanded-feature-scope-planning |
| feat:dev-type-checking | Development type checking gate | implemented | explicit | T2 | clm:development-gate-certification, clm:expanded-feature-scope-planning | tst:development-gate-certification, tst:expanded-feature-scope-planning |
| feat:digitalocean-dns-provider | DigitalOcean DNS provider package | implemented | current | T2 | clm:plugin-runtime-certification | tst:plugin-runtime-certification, tst:digitalocean-supported-record-type-writes |
| feat:discover-proxy-hosts | Discover current proxy hosts | implemented | current | T2 | clm:create-only-integrity | tst:e2e-real-npm, tst:integration-fake-npm, tst:unit-client-cli |
| feat:dns-mutation-reporting | DNS mutation reporting | implemented | current | T2 | clm:owner-scoped-integrity | tst:dns-mixed-npm-and-dns-plan |
| feat:dns-owner-scoped-record-prune | Owner-scoped DNS record pruning | implemented | current | T2 | clm:owner-scoped-integrity | tst:dns-owner-scoped-record-prune |
| feat:dns-provider-cli | DNS provider CLI diagnostics | implemented | current | T2 | clm:cli-operator-certification | tst:cli-operator-certification |
| feat:dns-provider-write-contract | DNS provider write contract | implemented | current | T2 | clm:plugin-runtime-certification | tst:dns-readonly-provider-apply-fails |
| feat:dns-readonly-provider-fail-closed | Read-only DNS providers fail apply | implemented | current | T2 | clm:plugin-runtime-certification | tst:dns-readonly-provider-apply-fails |
| feat:dns-reconciliation-plan-apply | DNS records participate in plan and apply | implemented | current | T2 | clm:owner-scoped-integrity | tst:dns-planner-record-operations, tst:dns-mixed-npm-and-dns-plan |
| feat:dns-record-schema-v2 | DNS record schema v2 | implemented | current | T2 | clm:owner-scoped-integrity | tst:unit-migrations |
| feat:dns-supported-record-type-writes | DNS supported record type writes | implemented | current | T2 | clm:plugin-runtime-certification | tst:namecheap-sethosts-a-cname-payload, tst:route53-supported-record-type-writes, tst:cloudflare-supported-record-type-writes, tst:digitalocean-supported-record-type-writes, tst:godaddy-supported-record-type-writes |
| feat:extension-resource-contract-api | Extension resource contract API | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:plugin-runtime-certification | tst:expanded-feature-scope-planning, tst:plugin-runtime-certification |
| feat:gap-acl-ref-negative | Access-list reference negative coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-acl-ref-negative |
| feat:gap-apply-adopt-merge | Apply adopt merge coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-apply-adopt-merge |
| feat:gap-apply-conflict-no-mutation | Apply conflict no-mutation coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-apply-conflict-no-mutation |
| feat:gap-apply-delete-results | Apply delete result coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-apply-delete-results |
| feat:gap-apply-operation-ordering | Apply operation ordering coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-apply-operation-ordering |
| feat:gap-apply-resolve-reference | Apply reference resolution coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-apply-resolve-reference |
| feat:gap-apply-unresolved-reference | Apply unresolved reference coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-apply-unresolved-reference |
| feat:gap-cert-ref-negative | Certificate reference negative coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-cert-ref-negative |
| feat:gap-cli-command-matrix | CLI command matrix coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-cli-command-matrix |
| feat:gap-cli-exit-code-mapping | CLI exit-code mapping coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-cli-exit-code-mapping |
| feat:gap-cli-json-error-shape | CLI JSON error shape coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-cli-json-error-shape |
| feat:gap-cli-option-combinations | CLI option combination coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-cli-option-combinations |
| feat:gap-cli-required-api-args | CLI required API argument coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-cli-required-api-args |
| feat:gap-cli-schema-output | CLI schema output coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-cli-schema-output |
| feat:gap-cli-secret-redaction | CLI secret redaction coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-cli-secret-redaction |
| feat:gap-cli-validate-output | CLI validate output coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-cli-validate-output |
| feat:gap-client-authz-errors | Client authorization error coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-client-authz-errors |
| feat:gap-client-error-redaction | Client API error redaction coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-client-error-redaction |
| feat:gap-client-login-failures | Client login failure coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-client-login-failures |
| feat:gap-client-malformed-success | Client malformed success payload coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-client-malformed-success |
| feat:gap-client-non-json-errors | Client non-JSON error coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-client-non-json-errors |
| feat:gap-client-nonget-no-retry | Client non-GET no-retry coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-client-nonget-no-retry |
| feat:gap-client-token-refresh-expiry | Client token refresh and expiry coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-client-token-refresh-expiry |
| feat:gap-client-transient-get-retry | Client transient GET retry coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-client-transient-get-retry |
| feat:gap-loader-api-version-validation | Loader API version validation coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-loader-api-version-validation |
| feat:gap-loader-discovery-ordering | Loader discovery ordering coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-loader-discovery-ordering |
| feat:gap-loader-duplicate-identities | Loader duplicate identity coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-loader-duplicate-identities |
| feat:gap-loader-malformed-documents | Loader malformed document coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-loader-malformed-documents |
| feat:gap-model-advanced-config-validation | Model advanced-config validation coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-model-advanced-config-validation |
| feat:gap-model-api-payload-validation | Model API payload validation coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-model-api-payload-validation |
| feat:gap-model-forward-host-validation | Model forward-host validation coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-model-forward-host-validation |
| feat:gap-model-forward-scheme-validation | Model forward-scheme validation coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-model-forward-scheme-validation |
| feat:gap-model-locations-validation | Model locations validation coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-model-locations-validation |
| feat:gap-model-toggle-validation | Model toggle validation coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-model-toggle-validation |
| feat:gap-package-metadata-urls | Package metadata URL coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-package-metadata-urls |
| feat:gap-packaging-console-script | Package console script smoke coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-packaging-console-script |
| feat:gap-planner-duplicate-domains | Planner duplicate domain coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-planner-duplicate-domains |
| feat:gap-planner-nonproxy-drift-foreign-owner | Planner non-proxy drift and foreign-owner coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-planner-nonproxy-drift-foreign-owner |
| feat:gap-planner-nonproxy-duplicate-identity | Planner non-proxy duplicate identity coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-planner-nonproxy-duplicate-identity |
| feat:gap-planner-owner-filtering | Planner owner filtering coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-planner-owner-filtering |
| feat:gap-planner-partial-capabilities | Planner partial capability coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-planner-partial-capabilities |
| feat:gap-planner-prune-selected-owner | Planner selected-owner prune coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-planner-prune-selected-owner |
| feat:gap-real-npm-acl-capability | Real NPM access-list capability coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-acl-capability |
| feat:gap-real-npm-acl-create-readback | Real NPM access-list create read-back coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-acl-create-readback |
| feat:gap-real-npm-acl-update-delete-prune | Real NPM access-list update delete prune coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-acl-update-delete-prune |
| feat:gap-real-npm-advanced-config | Real NPM advanced config assertions | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-advanced-config |
| feat:gap-real-npm-block-exploits | Real NPM block exploits assertions | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-block-exploits |
| feat:gap-real-npm-cache-assets | Real NPM cache asset assertions | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-cache-assets |
| feat:gap-real-npm-cert-capability | Real NPM certificate capability coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-cert-capability |
| feat:gap-real-npm-cert-create-readback | Real NPM certificate create read-back coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-cert-create-readback |
| feat:gap-real-npm-cert-ref-applied | Real NPM certificate ID application coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-cert-ref-applied |
| feat:gap-real-npm-cert-update-delete-prune | Real NPM certificate update delete prune coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-cert-update-delete-prune |
| feat:gap-real-npm-cleanup | Live NPM Gate cleanup assertions | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-cleanup |
| feat:gap-real-npm-domain-collision | Real NPM domain collision coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-domain-collision |
| feat:gap-real-npm-enabled-hsts | Real NPM enabled and HSTS assertions | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-enabled-hsts |
| feat:gap-real-npm-foreign-owner | Real NPM foreign-owner protection | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-foreign-owner |
| feat:gap-real-npm-forward-scheme | Real NPM forward scheme assertions | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-forward-scheme |
| feat:gap-real-npm-http2 | Real NPM HTTP/2 assertions | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-http2 |
| feat:gap-real-npm-locations | Real NPM custom locations assertions | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-locations |
| feat:gap-real-npm-meta-readback | Real NPM metadata persistence assertions | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-meta-readback |
| feat:gap-real-npm-owner-filtering | Real NPM owner filtering | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-owner-filtering |
| feat:gap-real-npm-proxy-acl-ref | Real NPM proxy access-list reference coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-proxy-acl-ref |
| feat:gap-real-npm-proxy-adopt | Real NPM proxy host adoption coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-proxy-adopt |
| feat:gap-real-npm-proxy-cert-ref | Real NPM proxy certificate reference coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-proxy-cert-ref |
| feat:gap-real-npm-proxy-delete-prune | Real NPM proxy host delete and prune coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-proxy-delete-prune |
| feat:gap-real-npm-proxy-readback | Real NPM proxy host read-back assertions | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-proxy-readback |
| feat:gap-real-npm-proxy-update | Real NPM proxy host update coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-proxy-update |
| feat:gap-real-npm-prune-owner-isolation | Real NPM prune owner isolation | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-prune-owner-isolation |
| feat:gap-real-npm-ssl-forced | Real NPM force HTTPS assertions | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-ssl-forced |
| feat:gap-real-npm-websockets | Real NPM WebSocket assertions | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-real-npm-websockets |
| feat:gap-workflow-semantics | GitHub workflow semantics coverage | implemented | current | T2 | clm:test-coverage-gap-plan | tst:gap-workflow-semantics |
| feat:github-actions-gates | Gated GitHub Actions with live NPM gate | implemented | current | T2 | clm:owner-scoped-integrity | tst:e2e-real-npm, tst:integration-fake-npm, tst:unit-planner |
| feat:godaddy-dns-provider | GoDaddy DNS provider package | implemented | current | T2 | clm:plugin-runtime-certification | tst:plugin-runtime-certification, tst:godaddy-supported-record-type-writes |
| feat:immutable-plan-artifact | Immutable plan artifact | implemented | backlog |  | clm:versioning-migration-contracts | tst:plan-artifact-roundtrip |
| feat:live-state-import-classification | Live-state import classification | absent | backlog |  | clm:versioning-migration-contracts | tst:live-state-classification |
| feat:lost-response-reconciliation | Lost provider response reconciliation | absent | backlog |  | clm:versioning-migration-contracts | tst:provider-response-loss, tst:resume-after-provider-success |
| feat:metadata-ownership | Validate metadata ownership | implemented | current | T2 | clm:metadata-conflict-guard | tst:integration-fake-npm, tst:unit-planner, tst:unit-validation |
| feat:migration-execution-lease | Migration execution lease | implemented | backlog |  | clm:versioning-migration-contracts | tst:concurrent-migration-rejection, tst:migration-lease-expiry |
| feat:migration-forward-repair | Migration forward repair | implemented | backlog |  | clm:versioning-migration-contracts | tst:forward-repair-from-snapshot |
| feat:migration-idempotency-key | Migration operation idempotency keys | partial | backlog |  | clm:versioning-migration-contracts | tst:duplicate-operation-idempotency |
| feat:migration-lease-recovery | Migration lease recovery | implemented | backlog |  | clm:versioning-migration-contracts | tst:migration-lease-expiry, tst:resume-after-provider-success |
| feat:migration-ledger | Append-only migration ledger | implemented | backlog |  | clm:versioning-migration-contracts | tst:migration-ledger-append-only |
| feat:migration-manifest | Versioned migration manifest | implemented | backlog |  | clm:versioning-migration-contracts | tst:migration-manifest-schema |
| feat:migration-ownership-transfer | Manifest-controlled ownership transfer | absent | backlog |  | clm:versioning-migration-contracts | tst:ownership-transfer |
| feat:migration-prechange-snapshot | Migration prechange snapshot | implemented | backlog |  | clm:versioning-migration-contracts | tst:forward-repair-from-snapshot |
| feat:migration-prune-delete | Manifest-controlled prune and delete | absent | backlog |  | clm:versioning-migration-contracts | tst:migration-delete-gates |
| feat:migration-resource-adoption | Manifest-controlled resource adoption | absent | backlog |  | clm:versioning-migration-contracts | tst:migration-adoption-gates |
| feat:migration-resume | Idempotent migration resume | partial | backlog |  | clm:versioning-migration-contracts | tst:migration-resume |
| feat:migration-reversibility-classification | Migration reversibility classification | implemented | backlog |  | clm:versioning-migration-contracts | tst:migration-reversibility-classification, tst:reversible-migration-rollback, tst:irreversible-migration-rejects-rollback |
| feat:migration-verification | Migration verification | partial | backlog |  | clm:versioning-migration-contracts | tst:migration-verification |
| feat:namecheap-dns-env-validation | Namecheap DNS apply environment validation | implemented | current | T2 | clm:plugin-runtime-certification | tst:namecheap-client-ip-required, tst:namecheap-api-error-redaction |
| feat:namecheap-dns-provider | Namecheap DNS provider package | implemented | current | T2 | clm:plugin-runtime-certification | tst:plugin-runtime-certification |
| feat:namecheap-dns-sethosts-apply | Namecheap setHosts apply | implemented | current | T2 | clm:plugin-runtime-certification | tst:namecheap-sethosts-a-cname-payload, tst:namecheap-post-apply-record-readback |
| feat:namecheap-dns-unmanaged-preservation | Namecheap unmanaged record preservation | implemented | current | T2 | clm:owner-scoped-integrity, clm:plugin-runtime-certification | tst:namecheap-preserve-unmanaged-records, tst:namecheap-remove-stale-owned-records |
| feat:no-implicit-contract-migration | No implicit contract migration | implemented | backlog |  | clm:versioning-migration-contracts | tst:validate-never-migrates, tst:plan-never-migrates, tst:apply-never-migrates |
| feat:npm-api-profile-negotiation | NPM API profile negotiation | absent | backlog |  | clm:versioning-migration-contracts | tst:npm-api-profile-drift |
| feat:npmctl-lockfile | Reproducible npmctl lockfile | implemented | backlog |  | clm:versioning-migration-contracts | tst:lockfile-reproducibility |
| feat:ops-apply-transaction-report | Apply transaction report | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:operational-hardening-certification | tst:expanded-feature-scope-planning, tst:operational-hardening-certification |
| feat:ops-audit-log-output | Operational audit log output | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:operational-hardening-certification | tst:expanded-feature-scope-planning, tst:operational-hardening-certification |
| feat:ops-containerized-cli-image | Containerized CLI image | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:operational-hardening-certification | tst:expanded-feature-scope-planning, tst:operational-hardening-certification |
| feat:ops-resource-drift-report | Resource drift report | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:operational-hardening-certification | tst:expanded-feature-scope-planning, tst:operational-hardening-certification |
| feat:ops-rollback-plan | Operational rollback plan | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:operational-hardening-certification | tst:expanded-feature-scope-planning, tst:operational-hardening-certification |
| feat:ops-state-backup-before-apply | State backup before apply | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:operational-hardening-certification | tst:expanded-feature-scope-planning, tst:operational-hardening-certification |
| feat:ordinary-apply-migration-guard | Ordinary apply migration guard | implemented | backlog |  | clm:versioning-migration-contracts | tst:apply-rejects-migration-operations |
| feat:owner-scoped-reconcile | Owner-scoped plan and apply | implemented | current | T2 | clm:owner-scoped-integrity | tst:e2e-real-npm, tst:integration-fake-npm, tst:unit-planner |
| feat:plan-adoptable-compatible-unmanaged | Adoptable compatible unmanaged planning | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-adoption-controls | tst:expanded-feature-scope-planning, tst:repair-safe-adoption-controls |
| feat:plan-certificate-policy-conflicts | Planned certificate policy conflicts | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-certificate-policy | tst:expanded-feature-scope-planning, tst:repair-safe-certificate-policy |
| feat:plan-staleness-detection | Plan artifact staleness detection | implemented | backlog |  | clm:versioning-migration-contracts | tst:plan-artifact-staleness |
| feat:plugin-contract-version-negotiation | Plugin contract version negotiation | partial | backlog |  | clm:versioning-migration-contracts | tst:plugin-supported-contract-version, tst:plugin-future-schema-rejection |
| feat:plugin-custom-cert-provider | Plugin custom certificate provider | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:plugin-runtime-certification | tst:expanded-feature-scope-planning, tst:plugin-runtime-certification |
| feat:plugin-custom-resource-kind | Plugin custom resource kind | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:plugin-runtime-certification | tst:expanded-feature-scope-planning, tst:plugin-runtime-certification |
| feat:plugin-custom-resource-schema-registry | Plugin custom-resource schema registry | absent | backlog |  | clm:versioning-migration-contracts | tst:plugin-future-schema-rejection |
| feat:plugin-migration-conflict-detection | Plugin migration conflict detection | partial | backlog |  | clm:versioning-migration-contracts | tst:plugin-migration-path-conflict, tst:plugin-missing-migration-step |
| feat:plugin-migration-step-registration | Plugin migration step registration | partial | backlog |  | clm:versioning-migration-contracts | tst:plugin-migration-discovery |
| feat:plugin-provider-interface | Plugin provider interface | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:plugin-runtime-certification | tst:expanded-feature-scope-planning, tst:plugin-runtime-certification |
| feat:plugin-runtime-loading | Runtime plugin discovery and diagnostics | implemented | explicit | T2 | clm:plugin-runtime-certification | tst:plugin-runtime-certification |
| feat:provider-capability-contract | Versioned provider capability contract | implemented | backlog |  | clm:versioning-migration-contracts | tst:provider-capability-matrix |
| feat:provider-capability-negotiation | Provider capability negotiation | implemented | backlog |  | clm:versioning-migration-contracts | tst:unsupported-provider-capability |
| feat:provider-request-correlation | Provider request correlation | absent | backlog |  | clm:versioning-migration-contracts | tst:provider-response-loss |
| feat:proxy-host-crud | Owner-scoped proxy host CRUD | implemented | current | T2 | clm:owner-scoped-integrity | tst:e2e-real-npm, tst:integration-fake-npm, tst:unit-planner |
| feat:repair-safe-public-endpoint-workflow | Repair-safe public endpoint workflow | implemented | explicit | T3 | clm:expanded-feature-scope-planning, clm:repair-safe-adoption-controls | tst:expanded-feature-scope-planning, tst:repair-safe-adoption-controls |
| feat:repository-environment-resolution | Repository environment isolation | absent | backlog |  | clm:versioning-migration-contracts | tst:repository-cross-environment-isolation |
| feat:repository-layout-validation | Canonical repository layout validation | absent | backlog |  | clm:versioning-migration-contracts | tst:repository-layout-validation |
| feat:repository-manifest | Versioned repository manifest | implemented | backlog |  | clm:versioning-migration-contracts | tst:repository-manifest-validation |
| feat:resource-audit-log | Audit log resource reporting | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:resource-expanded-certification | tst:expanded-feature-scope-planning, tst:resource-expanded-certification |
| feat:resource-dead-hosts | Dead host resource support | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:resource-expanded-certification | tst:expanded-feature-scope-planning, tst:resource-expanded-certification |
| feat:resource-redirection-hosts | Redirection host resource support | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:resource-expanded-certification | tst:expanded-feature-scope-planning, tst:resource-expanded-certification |
| feat:resource-settings | Settings resource support | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:resource-expanded-certification | tst:expanded-feature-scope-planning, tst:resource-expanded-certification |
| feat:resource-streams | Stream resource support | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:resource-expanded-certification | tst:expanded-feature-scope-planning, tst:resource-expanded-certification |
| feat:resource-users | User resource support | implemented | explicit | T2 | clm:expanded-feature-scope-planning, clm:resource-expanded-certification | tst:expanded-feature-scope-planning, tst:resource-expanded-certification |
| feat:route53-dns-provider | Route 53 DNS provider package | implemented | current | T2 | clm:plugin-runtime-certification | tst:plugin-runtime-certification, tst:route53-supported-record-type-writes |
| feat:safe-contract-downgrade | Safe contract downgrade | implemented | backlog |  | clm:versioning-migration-contracts | tst:safe-downgrade-roundtrip, tst:irreversible-downgrade-rejection |
| feat:schema-capabilities | OpenAPI capability detection | implemented | current | T2 | clm:owner-scoped-integrity, clm:schema-gated-api | tst:e2e-real-npm, tst:integration-fake-npm, tst:unit-planner |
| feat:schema-migrations | Legacy desired-state v1 to v2 migration | implemented | current | T2 | clm:owner-scoped-integrity | tst:integration-fake-npm, tst:unit-migrations, tst:unit-schema |
| feat:ssot-feature-family-proof-closure | Feature-family SSOT proof closure | implemented | explicit | T2 | clm:development-gate-certification | tst:development-gate-certification |
| feat:stepwise-migration-graph | Stepwise migration graph | implemented | backlog |  | clm:versioning-migration-contracts | tst:migration-step-matrix |
| feat:strict-plan | Compute strict owner-scoped plans | implemented | current | T2 | clm:create-only-integrity, clm:metadata-conflict-guard | tst:integration-fake-npm, tst:unit-planner |
| feat:transactional-filesystem-migration | Transactional filesystem migration | implemented | backlog |  | clm:versioning-migration-contracts | tst:migration-atomic-failure |
| feat:trusted-artifact-key-policy | Trusted artifact key policy | implemented | backlog |  | clm:versioning-migration-contracts | tst:artifact-untrusted-signer |
