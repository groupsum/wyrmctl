# Immutable plan artifacts

`npmctl plan DESIRED --artifact-out plan.yaml` records exact ordered NPM
resource operations plus the source commit, repository, environment,
desired-state digest, live-state fingerprint, and NPM API profile. `npmctl apply
--artifact plan.yaml` rejects expired, conflicting, stale, or differently bound
plans before mutation. DNS execution artifacts remain planned; npmctl fails
artifact creation when the desired state contains DNS records instead of
silently omitting those operations.

The NPM live-state fingerprint is scoped to the reviewed plan. It covers all
resources owned by every owner represented in the plan, together with foreign
or unmanaged resources that could collide with a target natural key, proxy
domain, reusable certificate domain set, or explicit certificate/access-list
ID. This permits independent owners to plan and apply concurrently without
weakening optimistic concurrency for the resources that can affect either
plan. A same-owner change or a newly introduced collision still makes the plan
stale and fails closed. Artifacts produced by versions that used the former
instance-wide fingerprint must be replanned before apply.

Adoption and deletion are deliberately excluded from ordinary plan artifacts; those actions require a reviewed migration manifest.
