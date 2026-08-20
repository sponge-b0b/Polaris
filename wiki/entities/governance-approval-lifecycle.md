# Governance Approval Lifecycle (Entity ID: governance-approval-lifecycle)

**Boundary Rationale:** This boundary owns audit/review tasks, decisions, residual-risk acceptance, and release decisions as an approval lifecycle rather than simple telemetry or report metadata.
(source: owner-approved entity promotion)

### Strict Invariants

* `AutomatedDecisionAuditService` is the authoritative application owner for governance audit records, review tasks, read models, immutable review decisions, residual-risk acceptance, and release decisions, because approval lifecycle state must be centralized. (source: docs/adr/0010-governance-approval-lifecycle-contestability-residual-risk.md)
* `AutomatedDecisionAuditRepository` and PostgreSQL form the canonical persistence boundary for approval lifecycle data; logs, metrics, traces, runtime events, report files, CLI, MCP, Qdrant, and Neo4j are not approval sources of truth. (source: docs/adr/0010-governance-approval-lifecycle-contestability-residual-risk.md)
* Human or organizational reviewers remain attributable for review actions; model output cannot approve, contest, override, request changes, accept residual risk, or lower an authority tier, because governance authority cannot be delegated to generated text. (source: docs/adr/0010-governance-approval-lifecycle-contestability-residual-risk.md)
* Governed outputs fail closed when review or residual-risk acceptance is missing, stale, or blocking, because absence of approval is not implicit approval. (source: docs/adr/0010-governance-approval-lifecycle-contestability-residual-risk.md)

### Planned

* **Canonical governance actor/security attribution** — accepted, implementation pending: actor-sensitive governance transitions persist canonical principal attribution, and durable protected mutations retain reconstructable references to the authorization decisions that permitted them without merging authorization evidence into governance/risk evidence. (source: docs/adr/0023-identity-access-propagation-audit-attribution.md)
* **Runtime-integrated approval engine expansion** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
