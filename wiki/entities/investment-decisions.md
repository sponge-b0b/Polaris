# Investment Decisions (Entity ID: investment-decisions)

**Boundary Rationale:** This boundary owns first-class Investment Decision identity and lifecycle continuity: Decision Need, Subject and Decision Scope relationships, unresolved/resumable state, Deferral, substantive resolution, External Resolution, Supersession, and causally linked renewed decisions. The boundary is distinct because later Evidence, Recommendations, authority acts, Action Intents, Outcomes, and technical runtime activity must reference decision identity without being allowed to redefine it.
(source: owner-approved entity boundary determination)

### Strict Invariants

* An Investment Decision represents one coherent unresolved portfolio-relevant choice; a resolved decision never reopens, and renewed judgment after resolution creates a new causally linked Investment Decision. (source: docs/current/platform-architecture-0.2.0.md)
* Deferral preserves the same unresolved Investment Decision, while new Evidence, state, Risk, or Recommendation change does not by itself create a new decision. (source: docs/current/platform-architecture-0.2.0.md)
* Investment Decision identity must remain independent of workflow, job, model invocation, report/output, and other technical execution identity because technical provenance is not business identity. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0002-platform-persist-direct-business-truth-with-immutable-history.md)
* Investment Decision is a lifecycle root referenced by other semantic owners, not a giant aggregate that absorbs Evidence, judgment, authority, Action Intent, Outcome, or Lesson ownership. (source: docs/current/platform-architecture-0.2.0.md)
* Durable historical truth is preserved directly under business semantics and later change is represented explicitly rather than silently rewriting earlier decision facts. (source: docs/adr/0002-platform-persist-direct-business-truth-with-immutable-history.md)

### Planned

* **R2 decision kernel and historical truth** — establish the smallest durable implementation of Investment Decision identity, lifecycle transitions, historical reconstruction, transaction/idempotency semantics, and technology-neutral persistence contracts. (source: docs/proposed/investment-decisions-r2-decision-kernel-component-boundaries.md)
* **R2 lifecycle design** — use explicit `ACTIVE`, `DEFERRED`, `RESOLVED`, `EXTERNALLY_RESOLVED`, and `SUPERSEDED` lifecycle states backed by immutable typed lifecycle facts; preserve renewal and Supersession as relationships between distinct Decision identities; and keep substantive resolution separate from the Governance-owned Human Investment Decision that may justify it. (source: docs/proposed/investment-decisions-lifecycle-model.md)
* **Decision relationship model** — represent Decision-to-Decision relationships as separate typed durable facts rather than aggregate-owned adjacency; distinguish acyclic lifecycle lineage (`RENEWED_FROM`, `SUPERSEDES`) from materially used prior-Decision context (`PRIOR_DECISION_CONTEXT`); treat retrieval as candidate discovery rather than durable context; and permit graph-shaped Decision Memory without requiring a graph database. R2 implements only the lifecycle-lineage edges while preserving a clean path to later many-to-many contextual bindings. (source: docs/proposed/investment-decisions-decision-relationship-model.md)
