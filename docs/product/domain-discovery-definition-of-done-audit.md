# Polaris Domain Discovery Definition-of-Done Audit

**Status:** GREEN  
**Audit date:** 2026-09-04  
**Purpose:** Record the final Definition-of-Done audit for Polaris domain discovery and determine whether 0.2.0 requirements and architecture work may begin.

## Authority and audit basis

The authoritative completion gate is the eleven-item **Definition of done for Polaris Domain Discovery and Definition** in [`domain-model.md`](./domain-model.md).

This audit evaluates that gate against the repository's durable current state, principally:

- [`../../CONTEXT.md`](../../CONTEXT.md) — canonical domain vocabulary;
- [`domain-model.md`](./domain-model.md) — resolved invariants, relationship reasoning, temporal semantics, and preserved scenario fixtures;
- [`product-definition.md`](./product-definition.md) and the harmonized product doctrine — current product purpose, boundary, lifecycle, and authority semantics;
- [`../research/platform-implementation-semantic-reconciliation.md`](../research/platform-implementation-semantic-reconciliation.md) — implementation-to-domain reconciliation.

The audit does not use current implementation behavior to redefine product or domain semantics.

## Discovery-era wording in the original gate

The original DoD was written before several canonical naming decisions were frozen. Its semantic intent remains valid, but three labels are historical:

- `Portfolio Decision` is evaluated as the canonical **Investment Decision**;
- `Human Portfolio Decision` is evaluated as the canonical **Human Investment Decision**;
- `reopening` / `closure` are evaluated using the resolved lifecycle semantics: unresolved work may resume; substantive judgment resolution and External Resolution are distinct; renewed judgment after substantive resolution creates a new causally linked Investment Decision rather than reopening and rewriting the resolved decision.

This is a terminology mapping, not a relaxation of the gate. Historical discovery prose remains preserved in `domain-model.md` where it documents how the model was derived; superseding resolved sections and `CONTEXT.md` govern current semantics.

## Audit result

| # | Definition-of-Done criterion | Result | Durable evidence / finding |
| --- | --- | --- | --- |
| 1 | Core Polaris domain purpose and ownership boundary are explicit. | **PASS** | `product-definition.md` defines Polaris as an AI-assisted portfolio decision system whose product center is Investment Decision quality and explicitly places Polaris in the decision layer between specialist information systems and action/execution systems. `domain-model.md` frames the core domain as decision formation, governance, continuity, memory, and evaluation under uncertainty. |
| 2 | Major domain areas are understood well enough that responsibilities do not materially overlap by accident. | **PASS** | Resolved semantics distinguish Portfolio/Portfolio State/Exposure/Allocation/Risk; Evidence/Signal/View/Recommendation; Policy/Formal Constraint/Governance/Approval/Human Investment Decision; Proposed Action/Action Intent/Order; Outcome/Decision Evaluation/Lesson; and architecture/runtime representations from investment-domain concepts. Cross-cutting responsibilities such as Attention and Durable Decision Memory are explicitly modeled as such rather than forced into competing business entities. |
| 3 | Investment Decision has a precise meaning, identity, lifecycle, and temporal model. | **PASS** | `CONTEXT.md` defines explicit durable Investment Decision identity independent of subject, scope, Evidence, Recommendation, workflow execution, or mutable Portfolio State. `domain-model.md` freezes same-versus-new identity, Deferral, substantive resolution, External Resolution, Review Conditions, Supersession, temporal reconstruction, and renewed-decision semantics. |
| 4 | Investment Recommendation and Human Investment Decision have precise meanings and relationships to Investment Decision. | **PASS** | Both are canonical and separately attributable. An Investment Decision may contain zero, one, or multiple Investment Recommendations; Human Investment Decision is separate even when it adopts a Recommendation unchanged and may exist without a Recommendation. Recommendation rejection does not by itself determine Investment Decision resolution. |
| 5 | Decision initiation, reassessment/resumption, Deferral, resolution, External Resolution, and Supersession are semantically distinguishable. | **PASS** | Decision Need and initiation are explicit. Deferral preserves an unresolved need; deliberate hold/no-action may substantively resolve it; External Resolution eliminates the need without inventing human judgment; Review Conditions may create renewed Attention; post-resolution renewed judgment creates a new linked Investment Decision; Supersession preserves both histories. The older generic `reopening` model is intentionally retired. |
| 6 | Evidence, reasoning, Portfolio/Risk, Governance, action continuity, memory, Outcome, and learning have known relationships to the decision lifecycle. | **PASS** | Canonical vocabulary and frozen scenarios establish Evidence roles and Judgment-Time Availability; Investment Hypothesis/View/Uncertainty; Portfolio State, Projected Portfolio Consequence, Portfolio Risk and Risk Assessment; Investment Authority Regime and power-specific authority acts; Proposed Action and post-human Action Intent; decision-relative Outcome; retrospective Decision Evaluation; durable Lesson; and cross-cutting Durable Decision Memory. |
| 7 | External specialist authority is explicit for operational facts Polaris does not own. | **PASS** | Market, broker, account, Order, fill, execution, and resulting operational Portfolio facts retain external authority and provenance. Polaris may normalize, reason over, observe, and reconcile them without acquiring execution or accounting authority. Action Intent remains distinct from externally authoritative execution facts. |
| 8 | Important current-language collisions are resolved. | **PASS** | Major collisions have been frozen and harmonized: Investment Decision vs older Portfolio Decision wording; Human Investment Decision vs generic approval/review; Investment Strategy vs Trading System; Investment Hypothesis/View vs legacy Strategy Decision; Proposed Action vs Action Intent; Portfolio Risk vs Policy/Formal Constraint/Risk Score; Judgment Confidence vs generic confidence; Outcome vs Decision Evaluation; investment Backtest/Investment Simulation vs runtime meanings; governed `Release` retired in favor of Admissibility/Approval/Publication/Durable Promotion; bare architecture `Projection` removed from investment-domain vocabulary while remaining valid architecture language. |
| 9 | `CONTEXT.md` contains resolved canonical vocabulary without architecture/runtime pollution. | **PASS** | The dedicated cleanup/re-parenting pass removed architecture/runtime glossary entries such as Workflow Identity, Workflow Invocation, Completed-Run Archive, Application Service, Provider, Client, System of Record, and architecture Projection as canonical investment-domain entries. Implementation/database choices such as PostgreSQL are absent from the glossary. Architecture vocabulary is referenced only where needed to state a domain distinction. |
| 10 | Current implementation concepts have been reconciled sufficiently to identify major KEEP / RENAME / RE-PARENT / SPLIT / MERGE / DEMOTE / REMOVE implications. | **PASS** | `platform-implementation-semantic-reconciliation.md` freezes the implementation mapping. It identifies high-impact SPLIT/RENAME/RE-PARENT/DEMOTE implications, useful predecessors to retain, missing first-class lifecycle concepts, and records that no broad behavioral REMOVE or major MERGE campaign is justified. No production refactoring was performed during classification. |
| 11 | Unresolved semantic questions that could change 0.2.0 requirements or architecture have been resolved rather than deferred into implementation. | **PASS** | The previously open semantic families are now represented by canonical definitions, frozen invariants, and pressure-test scenarios. Remaining implementation gaps are implementation/architecture work, not unresolved domain meaning. No live semantic question was found whose answer must be guessed by 0.2.0 requirements or architecture. |

## Cross-checks

### Canonical lifecycle is closed

The current doctrine can express the complete product loop without relying on workflow/runtime vocabulary:

```text
Attention
  ↓
Decision Need
  ↓
Investment Decision reasoning / challenge
  ↓
Investment Recommendation where supportable
  ↓
Human Investment Decision
  ↓
Action Intent where applicable
  ↓
authoritative external reality
  ↓
Outcome
  ↓
Decision Evaluation
  ↓
Lesson
  └────────→ future Attention
```

Durable Decision Memory spans this lifecycle rather than competing with it as another business entity.

### Authority boundaries remain non-collapsed

The frozen model preserves these independent meanings:

```text
Polaris investment judgment
≠ deterministic Policy / Formal Constraint result
≠ Admissibility
≠ Approval / Mandate Exception / Residual-Risk Acceptance
≠ Human Investment Decision
≠ external execution authority
```

No score threshold, model output, external fill, or later Portfolio State is allowed to manufacture a missing authority fact retroactively.

### Historical fidelity remains intact

Resolved Investment Decisions, Recommendations, Human Investment Decisions, authority acts, Action Intents, Outcomes, Decision Evaluations, and Lessons remain historical facts once attributable. Later evidence, corrections, evaluations, or renewed judgment may change current understanding or create new linked judgments without destructively rewriting the historical basis actually available at the earlier judgment time.

### Implementation gaps do not fail domain discovery

The reconciliation found missing first-class implementation for several canonical lifecycle identities, including Decision Need, Investment Decision, post-human Action Intent, Decision Evaluation, Lesson, and explicit Durable Decision Memory composition. Those are now known semantic requirements for subsequent work. Their absence from the current implementation is exactly what requirements and architecture must address; it is not an unresolved domain-model question.

## Source-conflict result

**No blocking `[source-conflict]` was found for the domain-discovery gate.**

Current implementation differs materially from the frozen domain model in several places, but those differences are already classified as implementation-semantic reconciliation findings rather than competing authoritative domain definitions. Product doctrine is not re-derived from those implementation accidents.

## Final gate decision

> **GREEN — Polaris Domain Discovery and Definition satisfies its Definition of Done.**

The domain vocabulary, identities, boundaries, lifecycle semantics, authority distinctions, temporal rules, scenario fixtures, product terminology, and implementation reconciliation are sufficiently stable for requirements and architecture to constrain the next release against the domain rather than rediscovering it during coding.

**0.2.0 requirements and architecture work may now begin.**

This decision does not authorize opportunistic production refactoring. Requirements and architecture should consume the frozen domain model and the implementation reconciliation as inputs, then define the intended 0.2.0 change set deliberately.
