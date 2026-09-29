---
status: accepted
---

# Compose R3 Decision Memory from domain-owned facts

## Context

R3 now has accepted contracts for Evidence, Investment Intelligence, Portfolio & Risk, Human Investment Decision, the human CLI, Outcome, Decision Evaluation, and Lesson. The remaining architecture question is how these facts persist and compose into current and historical Decision Memory without creating a second source of truth.

The current platform architecture already requires direct persistence of business truth, application-owned transaction semantics, immutable historical reconstruction, and one shared command/query boundary. Durable Decision Memory is explicitly a cross-lifecycle responsibility rather than one mandated entity.

## Decision

R3 persists direct business facts under their owning domain semantics and composes Decision Memory through application queries. There is no monolithic persisted DecisionRecord, generic event-store source of truth, workflow archive, or report-owned decision model.

Decisions retains the R2 Investment Decision lifecycle and relationship truth.

Evidence persists Evidence observations, judgment bindings, and the historical availability/freshness/sufficiency semantics required by ADR 0006.

Investment Intelligence persists material Investment Views, challenge results, material Decision Alternatives, Investment Recommendations, Recommendation-withholding judgments, and their typed relationships under ADR 0007.

Portfolio & Risk persists decision-grade actual Portfolio State representations, material Projected Portfolio Consequences or States, and Portfolio Risk Assessments under ADR 0008.

Governance & Authority persists Human Investment Decisions and the minimum R3 authority-regime facts needed to validate them under ADR 0009.

Learning persists Outcome, Decision Evaluation, and Lesson facts under ADR 0010.

Every new first-class R3 fact uses an opaque identity owned by its domain. Cross-domain relationships reference those canonical identities rather than duplicating nested payloads as identity. Where a material relationship contract is known, use typed references rather than a universal polymorphic entity graph.

Historical material facts are append-only. Correction, qualification, challenge, supersession, reassessment, and later support changes append attributable facts or relationships rather than destructively rewriting the earlier business fact. Current views are derived.

Persist information when losing it would change historical business meaning. Presentation-only values may remain derived when they are deterministically recomputable from durable facts without changing the historical interpretation. Inputs, methods/bases, assumptions, versions, provenance, and temporal boundaries required to preserve material historical meaning must remain durable.

Decision Context remains assembled rather than persisted as a monolithic context snapshot.

Durable Decision Memory is an application-owned query/composition capability. The minimum R3 query surface supports:

- current decision summary for the human CLI;
- historical decision state at explicit effective/knowledge boundaries where applicable;
- judgment-specific Evidence availability and support;
- Recommendation/withholding history and derived current support;
- actual Portfolio State plus alternative-relative projected consequence/Risk basis;
- Human Investment Decision, authority basis, and resolution relationship;
- Outcome, Decision Evaluation, and Lesson history;
- a complete hindsight-safe reconstruction suitable for Decision Evaluation.

Composed query results preserve owning provenance and temporal meaning. They may denormalize for reading but never become a new authoritative business writer.

Application transaction boundaries follow semantic invariants rather than domain-count boundaries. A command that establishes a material judgment together with required Evidence bindings or another inseparable cross-domain fact commits them atomically when partial commit would make the business statement false or unreconstructable. Human Investment Decision and the Decisions-side lifecycle consequence commit atomically when resolution or Deferral semantics require both.

Cross-domain reads do not require one giant transaction. They use explicit version/as-of/known-at boundaries and re-check or fail when the use case requires a stable basis.

Long-running Evidence acquisition and model calls remain outside durable-store transactions. Expected versions, Evidence fitness, Portfolio State basis, and governing preconditions are re-checked before accepted judgment commits.

Idempotency is operation-specific. Exact retry of one accepted semantic operation must not duplicate the business fact, while distinct attributable judgments remain distinct even when economically equivalent.

PostgreSQL remains the reference persistence adapter and extends the existing greenfield migration lineage. The adapter does not define the inward contract.

R3 Decision Memory composition excludes R5 execution continuity facts and R6 future-Attention behavior.

## Rationale

This preserves direct ownership, immutable history, and truthful historical reconstruction while avoiding a duplicate cross-domain aggregate or replay-centric persistence model. It lets the CLI and Decision Evaluation see one coherent decision history without moving authority away from the domains that own each fact.

## Considered Options

### Persist one cross-domain DecisionRecord snapshot

Rejected because it duplicates domain truth and creates a competing authority source.

### Use a generic event store or workflow replay as canonical history

Rejected because business meaning would depend on replaying implementation mechanics rather than direct domain facts.

### Recompute historical semantics from current source data

Rejected because later source changes, model changes, or knowledge would rewrite historical meaning.

### Persist domain-owned facts and compose Decision Memory in Application

Accepted because it preserves domain ownership, truthful history, and a shared current/historical query surface.
