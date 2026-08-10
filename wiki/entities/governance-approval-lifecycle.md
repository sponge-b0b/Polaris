# Governance Approval Lifecycle (Entity ID: governance-approval-lifecycle)

**Boundary Rationale:** This boundary owns audit/review tasks, decisions, residual-risk acceptance, and release decisions as an approval lifecycle rather than simple telemetry or report metadata.
(source: owner-approved entity promotion)

### Strict Invariants

* `AutomatedDecisionAuditService` is the authoritative application owner for governance audit records, review tasks, read models, immutable review decisions, residual-risk acceptance, and release decisions, because approval lifecycle state must be centralized. (source: docs/adr/0010-governance-approval-lifecycle-contestability-residual-risk.md)
* `AutomatedDecisionAuditRepository` and PostgreSQL form the canonical persistence boundary for approval lifecycle data; logs, metrics, traces, runtime events, report files, CLI, MCP, Qdrant, and Neo4j are not approval sources of truth. (source: docs/adr/0010-governance-approval-lifecycle-contestability-residual-risk.md)
* Human or organizational reviewers remain attributable for review actions; model output cannot approve, contest, override, request changes, accept residual risk, or lower an authority tier, because governance authority cannot be delegated to generated text. (source: docs/adr/0010-governance-approval-lifecycle-contestability-residual-risk.md)
* Governed outputs fail closed when review or residual-risk acceptance is missing, stale, or blocking, because absence of approval is not implicit approval. (source: docs/adr/0010-governance-approval-lifecycle-contestability-residual-risk.md)
* Automated governance outcomes reached through canonical workflow execution that require approval must be recorded through `AutomatedDecisionAuditService` before the blocking outcome is surfaced, so the evidence-scoped review task is durable rather than a manual after-the-fact audit write. (source: docs/adr/0010-governance-approval-lifecycle-contestability-residual-risk.md; docs/adr/0001-runtime-workflow-platform-execution-boundaries.md)

### Planned

* **Sink-scoped governance review-task identity** — accepted, implementation pending. Review-task ID, persistence uniqueness, and upsert semantics must distinguish intended sink alongside subject, evidence packet/version, review scope, and requested action, because approval for one controlled boundary cannot authorize another. (source: docs/adr/0010-governance-approval-lifecycle-contestability-residual-risk.md; docs/current/platform-architecture-ownership-ledger.md)
* **Runtime-integrated approval engine expansion** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
