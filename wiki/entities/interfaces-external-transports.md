# Interfaces & External Transports (Entity ID: interfaces-external-transports)

**Boundary Rationale:** This boundary owns user/external entrypoints and transport adaptation. It is meaningful because interfaces must remain thin over canonical services/runtime and must not create alternate domain authority.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Interfaces remain thin transports over canonical application services and `WorkflowFacade`, because user entrypoints should adapt requests without owning domain, runtime, persistence, or governance authority. (source: docs/current/platform-architecture-and-operations.md)
* Transport serialization belongs at interface edges, while internal semantics remain typed contracts, because interface-specific payload shapes must not become internal platform data models. (source: docs/adr/0006-domain-contracts-data-semantics-typed-internal-contracts.md)
* Interface governance or release behavior must delegate into canonical services rather than storing local approval state, because approval authority belongs to governance lifecycle records. (source: docs/adr/0010-governance-approval-lifecycle-contestability-residual-risk.md)
* Governed CLI and backtest execution submit typed execution requests only; the request-scoped application service resolves workflow identity, tier, and durable evidence, because transports must not become authority or evidence-selection boundaries. (source: docs/adr/0015-dependency-composition-governed-execution-evidence-acquisition.md)
### Planned

* **API, web UI, customer-facing AI agent, and expanded external transport surfaces** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
