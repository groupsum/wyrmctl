# wyrmctl DNS records

These provider-backed DNS operations are the Portwyrm DNS surface exposed through wyrmctl.

wyrmctl schema v2 supports provider-backed DNS records through `dns_records`.
DNS records are declared with the same owner-scoped metadata contract as NPM
resources, so adoption and pruning can remain explicit and owner-scoped when DNS
apply support is enabled for a provider.

```yaml
apiVersion: wyrmctl.com/v1
schemaVersion: 2
dns_records:
  - provider: namecheap
    zone: wyrmctl.com
    type: A
    name: "@"
    value: 172.16.0.10
    ttl: 300
    meta:
      managed_by: wyrmctl
      owner: wyrmctl-lander
      resource_id: dns.wyrmctl-com.root-a
```

DNS provider inspection is available through:

```bash
wyrmctl plugins list
wyrmctl dns providers
wyrmctl dns doctor --provider namecheap
wyrmctl dns zones --provider namecheap
wyrmctl dns records --provider namecheap --zone wyrmctl.com
```

DNS records also participate in `plan` and `apply` when the selected provider
implements write support:

```bash
wyrmctl plan desired-state/dns.yaml --owner wyrmctl-lander
wyrmctl apply desired-state/dns.yaml --owner wyrmctl-lander
```

`plan` reports DNS creates, updates, deletes, and no-ops under a separate DNS
summary. `apply` fails closed when a desired DNS mutation targets a read-only
provider. Owner-scoped pruning removes only records that carry wyrmctl ownership
metadata for the selected owner; unmanaged records in the same provider zone are
preserved in the reconciled provider payload.
