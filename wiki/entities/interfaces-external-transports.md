# Interfaces & External Transports (Entity ID: interfaces-external-transports)

**Boundary Rationale:** This boundary owns user/external entrypoints and transport adaptation. It is meaningful because interfaces must remain thin over canonical services/runtime and must not create alternate domain authority.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Interfaces remain thin transports over canonical application services and `WorkflowFacade`, because user entrypoints should adapt requests without owning domain, runtime, persistence, or governance authority. (source: docs/current/platform-architecture-and-operations.md)
* Transport serialization belongs at interface edges, while internal semantics remain typed contracts, because interface-specific payload shapes must not become internal platform data models. (source: docs/adr/0006-domain-contracts-data-semantics-typed-internal-contracts.md)
* Interface governance or release behavior must delegate into canonical services rather than storing local approval state, because approval authority belongs to governance lifecycle records. (source: docs/adr/0010-governance-approval-lifecycle-contestability-residual-risk.md)
* Interfaces may authenticate and adapt request context, but authorization evaluation and permission policy must delegate to the canonical Polaris authorization boundary rather than embedding transport-local role or permission rules. (source: docs/adr/0020-platform-authorization-contract-cerbos-pdp.md)
* Interfaces may extract transport-specific credentials, but canonical identity resolution must delegate to the Polaris authentication boundary; raw credentials must not become application/runtime semantics, and failed authentication must not silently fall through to another authenticator. (source: docs/adr/0021-platform-authentication-credential-resolution-boundary.md)

### Planned

* **API, web UI, customer-facing AI agent, and expanded external transport surfaces** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
