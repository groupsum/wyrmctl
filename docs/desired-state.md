# Desired-state schema

DesiredState v3 is the writable contract. It requires `apiVersion:
npmctl.com/v1`, `kind: DesiredState`, `schemaVersion: 3`, `metadata`, and
`spec`. Resource collections in `spec` use camel case: `certificates`,
`accessLists`, `proxyHosts`, `redirectionHosts`, `deadHosts`, `streams`,
`users`, `settings`, `pluginResources`, `externalCertificates`, and `quicPassthroughHosts`.

```yaml
---
apiVersion: npmctl.com/v1
kind: DesiredState
schemaVersion: 3
metadata:
  name: workload-a
  owner: workload-a
spec:
  proxyHosts: []
```

Schemas v1 and v2 remain readable during the compatibility window, but npmctl
does not rewrite them during validate, plan, or apply. Use an explicit
migration to produce v3.

Every managed resource requires metadata:

```yaml
meta:
  managed_by: npmctl
  owner: workload-a
  resource_id: proxy.app
```

`resource_id` is the stable identity. Domain names and names are natural keys used for collision detection.

Repair-safe reconcile uses the same desired-state document with CLI policy controls. The main operator toggles are:

- `--only ...` to limit reconcile to selected resource families
- `--metadata-only` during `adopt` to attach ownership without adjacent creation
- `--certificate-mode=reuse|create|rotate` to control whether certificates are only reused, created when missing, or explicitly rotated

Additional resource kinds use pass-through `api_payload` fields while keeping
the same owner metadata contract. The following snippets are collection fields
inside `spec`:

For certificates, provider-specific `api_payload.meta` remains the exact legacy
NPM payload. When the provider advertises the native certificate-request
capability, Wyrmctl merges the validated `managed_by`, `owner`, and `resource_id`
identity into that request so Portwyrm can persist ownership without violating
upstream NPM's narrower certificate metadata schema.

```yaml
redirectionHosts:
  - domain_names: [old.example.com]
    forward_domain_name: new.example.com
    meta: {managed_by: npmctl, owner: workload-a, resource_id: redir.old}
streams:
  - incoming_port: 5432
    forward_host: db
    forward_port: 5432
    protocol: tcp
    meta: {managed_by: npmctl, owner: workload-a, resource_id: stream.db}
```

Runtime plugin providers can contribute desired resources without bypassing the
owner metadata contract. A resource provider is selected by name and converts a
provider-specific payload into one supported generic NPM resource kind:

```yaml
pluginResources:
  - provider: stream-provider
    payload:
      incoming_port: 15432
      owner: workload-a
      resource_id: stream.plugin-db
```

Certificate providers can resolve external references into certificate payloads.
The resolved payload is still parsed as a normal managed certificate:

```yaml
externalCertificates:
  - provider: vault-certificates
    reference: prod/example
    name: prod-example
    domain_names: [example.com]
    meta: {managed_by: npmctl, owner: workload-a, resource_id: cert.example}
```

## QUIC passthrough hosts

`quicPassthroughHosts` is a Portwyrm-native schema v3 resource. Before planning it, Wyrmctl authenticates to `/v2/capabilities` and fails closed unless the server explicitly reports hostname-routed QUIC passthrough with `tls_termination: false`. Nginx Proxy Manager profiles cannot apply this resource.

```yaml
spec:
  quicPassthroughHosts:
    - server_name: video.example.com
      listen_address: 0.0.0.0
      incoming_port: 443
      alpn: h3
      target_kind: docker
      target: video-backend
      target_port: 4443
      idle_timeout_seconds: 1800
      enabled: true
      meta:
        managed_by: wyrmctl
        owner: video-demo
        resource_id: quic.video-demo
```

The reviewed plan artifact preserves this exact resource and is the only accepted apply input. Portwyrm forwards encrypted QUIC; the target owns TLS, certificates, HTTP/3, and WebTransport.
