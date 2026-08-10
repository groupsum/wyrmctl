# SSL certificate CRUD

npmctl models certificates as owner-scoped resources. Because NPM certificate payloads vary by DNS provider and API version, certificate declarations support an `api_payload` pass-through merged with `name`, `domain_names`, `certificate_type`, and managed metadata.

Proxy hosts should reference certificates by `certificate_ref` whenever the certificate is declared in the same desired state.

Certificate reconcile policy is explicit:

- `--certificate-mode=reuse` reuses one compatible live certificate for the same provider and normalized domain set and blocks new issuance when none exists.
- `--certificate-mode=create` reuses a compatible live certificate when present and otherwise allows creation.
- `--certificate-mode=rotate` opts into create-new certificate behavior instead of silently reusing a compatible live certificate.

Issuance safety is local and fail-closed:

- repeated issuance attempts for the same provider and normalized domain set are deduplicated while one is in flight
- failed issuance attempts enter a cooldown window before npmctl will try again
- Certbot lock contention is classified as retryable, while stale `No order for ID ...` failures are surfaced as cleanup-required certificate errors
- after native certificate issuance, Wyrmctl verifies that managed identity was returned and immediately persists it on that newly created certificate when the request endpoint omits it
- if the provider cannot persist that identity, apply fails instead of reporting an unmanaged certificate as a successful create
