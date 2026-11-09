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

Certificate updates also converge the certificate material, not just the
database row. When an owner-scoped existing Let's Encrypt certificate changes
its normalized `domain_names`, Wyrmctl updates the certificate metadata and
domain set, calls the Portwyrm renewal endpoint with `force=true`, and then
re-reads the certificate before reporting success. The apply fails before the
first mutation unless provider capabilities advertise both forced renewal and
certificate readback. Metadata-only updates, no-op plans, and custom
certificates never trigger renewal.

## Namecheap DNS-01 on Portwyrm

For a Let's Encrypt certificate, set `challenge_type: dns-01`, `dns_provider: namecheap`,
`email`, and `namecheap_credentials_from_env: true` under `api_payload`.
Set `NAMECHEAP_API_USER` and `NAMECHEAP_API_KEY` only in the protected apply job. Wyrmctl
reads them when it issues the certificate through Portwyrm's native request endpoint.
The desired state and plan contain only the opt-in flag. Portwyrm holds the credentials
for subsequent renewal. Issue a new certificate with a new resource ID to change the
domain set, then update the route reference.

Manage the wildcard A record in a separate DNS plan or in the provider console.
Wyrmctl accepts a relative DNS record name such as `*.login` for the zone
`priv.pw`. The proxy route and certificate use the full `*.login.priv.pw` name.
