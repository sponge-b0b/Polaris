# Identity & Access (Entity ID: identity-access)

**Boundary Rationale:** This boundary owns canonical principal identity, authentication and credential resolution, authorization policy/evaluation, request security context, ownership-sensitive access facts, and actor/security attribution. It is distinct because these security semantics cut across interfaces, runtime, persistence, governance, and observability while remaining separate from governance authority, trace identity, and transport/session mechanics.
(source: owner-approved entity promotion)

### Strict Invariants

* Principal identity, authentication, authorization, resource ownership, governance/risk authority, and trace/execution identity remain distinct contracts, because substituting one for another would leak transport/provider semantics and collapse independent security, governance, and observability lifecycles. (source: docs/adr/0023-identity-access-propagation-audit-attribution.md)
* One Polaris deployment is one organizational trust/data boundary; Identity & Access must not introduce tenant, organization, workspace, or Cerbos-scope tenancy semantics into ordinary platform contracts, because deployment isolation is the canonical tenancy boundary. (source: docs/adr/0022-single-tenant-resource-ownership-attribution-semantics.md)

### Planned

* **Canonical principal identity** — accepted, implementation pending: Polaris will use a minimal immutable `Principal` with an opaque deployment-scoped `principal_id` and exactly `HUMAN`, `SERVICE`, or `SYSTEM` actor kinds; credentials resolve to principals rather than becoming identity. (source: docs/adr/0019-platform-principal-identity-and-actor-taxonomy.md)
* **Canonical authorization contract** — accepted, implementation pending: Polaris will use a provider-neutral, fail-closed typed authorization boundary over canonical principals, stable actions, typed resources, and trusted context, with Cerbos PDP as the initial provider behind a Polaris-owned adapter. (source: docs/adr/0020-platform-authorization-contract-cerbos-pdp.md)
* **Canonical authentication boundary** — accepted, implementation pending: transport/deployment credentials or explicit trusted-execution bindings resolve through a provider-neutral boundary into canonical principals and non-secret authentication context, while raw credentials terminate at authentication. (source: docs/adr/0021-platform-authentication-credential-resolution-boundary.md)
* **Resource ownership and access facts** — accepted, implementation pending: durable resources are platform-owned by default, principal ownership exists only where resource semantics require it, and ownership-sensitive authorization receives only trusted Polaris-derived ownership facts. (source: docs/adr/0022-single-tenant-resource-ownership-attribution-semantics.md)
* **Security-context propagation and actor attribution** — accepted, implementation pending: request-scoped security context remains within the application boundary, identity becomes explicit typed actor attribution across runtime/durable/governance boundaries, and protected durable mutations retain reconstructable authorization evidence where materially required. (source: docs/adr/0023-identity-access-propagation-audit-attribution.md)
