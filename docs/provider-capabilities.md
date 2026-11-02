# Provider capabilities

Every bundled DNS provider declares a versioned mutation model, supported record types, readback behavior, lease requirements, idempotency, rollback, and forward-repair support. npmctl checks the declaration before mutation and requires a verified post-mutation digest from modern providers. Legacy providers remain usable through a conservative read-only capability adapter during the 0.x transition.

Portwyrm API capability discovery is similarly fail-closed for certificate
material changes. A Let's Encrypt `domain_names` update requires the member
renew action (`POST /nginx/certificates/{id}/renew`) and certificate item
readback. Wyrmctl will not write the new domain set when either capability is
absent, because doing so would leave stored metadata ahead of the issued
certificate.
