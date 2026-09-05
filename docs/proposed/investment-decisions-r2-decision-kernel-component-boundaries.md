# R2 Decision Kernel and Historical Truth — Component Boundaries

**Status:** Approved  
**Release:** 0.2.0  
**Approved:** 2026-09-04  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define the implementation-facing boundary for the first greenfield durable Decision kernel while preventing unresolved semantic design from leaking into Specs.

## Authority

This plan is subordinate to:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- proposed audit reconciliation [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md), where frozen domain doctrine already outranks conflicting older wording;
- [`../roadmap/0.2.0.md`](../roadmap/0.2.0.md);
- [`../product/domain-model.md`](../product/domain-model.md) and [`../../CONTEXT.md`](../../CONTEXT.md);
- accepted ADRs under [`../adr/`](../adr/).

This plan does not reopen R1 architecture. `legacy/v0_1/` remains donor material only.

The component-boundary decision remains approved, but its **pre-Spec design gate is reopened** until the audit-remediated design set and requirements amendment are reviewed and approved.

---

# 1. R2 destination

R2 should leave Polaris able to answer, without workflow replay:

> What Decision Need and Investment Decision exist; why is work continuing, deferred, withdrawn, renewed, or superseding; what Scope was known; what substantive judgment or external elimination occurred; what was known then versus what is currently understood to have been effective; and can that truth survive retry, restart, correction, and concurrent work without semantic duplication?

The R2 path is deliberately narrower than the complete 0.2.0 lifecycle:

```text
Decision Need
      ↓
Investment Decision identity
      ↓
Subject + zero/partial/established Decision Scope
      ↓
Need status + judgment-resolution status + unresolved work posture
      ↓
renewal / Supersession relationships
      ↓
immutable facts + non-destructive correction
      ↓
Decision Memory current/historical queries
```

R2 does **not** implement Recommendation, full Evidence/Decision Context, Governance persistence, Action Intent, or Learning.

---

# 2. Earned source boundaries

R2 earns only:

```text
src/polaris/
├── domain/
│   └── decisions/
├── application/
│   ├── use_cases/
│   ├── queries/
│   └── ports/
└── infrastructure/
    └── persistence/
```

plus minimum tests and architecture enforcement.

Do not scaffold other R1 entities merely because they exist architecturally.

---

# 3. Decisions domain boundary

R2 must establish:

- durable one-Need/one-Decision identity relationship;
- Decision Subject;
- Decision Scope with explicit zero-known, partially known, and established applicability;
- Decision Need status;
- substantive judgment-resolution status;
- unresolved work posture;
- Deferral as a Decisions-side consequence of a trusted Human Investment Decision basis;
- work withdrawal distinct from Deferral or investment judgment;
- External Resolution as external elimination of the Decision Need, not substantive judgment;
- non-destructive Decision Need retraction when the original Need was erroneous/unsupported;
- renewal relationships;
- Supersession as an orthogonal many-to-many relationship that may apply to unresolved or resolved Decisions;
- explicit lifecycle correction when late knowledge changes supported effective interpretation;
- Actor Attribution distinct from trigger/source/technical provenance;
- fail-closed same-vs-new continuity under concurrent initiation.

## 3.1 Four independent lifecycle dimensions

R2 must preserve, not collapse:

```text
Decision Need status
    ACTIVE
    EXTERNALLY_ELIMINATED
    RETRACTED_UNSUPPORTED

judgment-resolution status
    UNRESOLVED
    SUBSTANTIVELY_RESOLVED

work posture while Need ACTIVE + judgment UNRESOLVED + Decision operative
    ACTIVE
    DEFERRED
    WITHDRAWN

continuing applicability
    typed SUPERSEDES relationship(s)
```

The labels are implementation/design vocabulary; they do not create new canonical product nouns by themselves.

External Resolution changes the **Decision Need** axis. Supersession changes **continuing applicability**. Neither may be represented by overwriting substantive judgment history.

---

# 4. Decision relationship boundary

R2 implements:

- `RENEWED_FROM`;
- `SUPERSEDES`.

Required semantics:

- supported renewal/Supersession lineage is acyclic;
- no fixed one-to-one Supersession cardinality;
- unresolved or resolved Decisions may be superseded;
- Supersession never rewrites Need/judgment/work history;
- relationship facts preserve effective and recorded time;
- relationship correction is append-only;
- storage remains compatible with later many-to-many `PRIOR_DECISION_CONTEXT`;
- future contextual binding preserves the target Decision **as known when actually used**, not its later current state.

R2 does not implement contextual prior-Decision retrieval/binding itself.

---

# 5. Application boundary

R2 application responsibilities include:

```text
initiate_decision
establish_or_refine_decision_scope
revise_decision_subject
record_deferral_consequence
resume_decision_work
withdraw_decision_work
record_substantive_resolution
record_external_resolution
retract_unsupported_decision_need
initiate_renewed_decision
record_supersession
correct_decision_lifecycle
```

Queries include:

```text
current Decision
recorded history
as-known-at
historically effective state under a knowledge cutoff
continuity candidates
renewal/Supersession lineage
```

## 5.1 Continuity arbitration

Different operation IDs must not bypass same-vs-new Decision semantics.

For initial R2, correctness is favored over clever matching:

- the continuity query MAY return all currently unresolved, non-superseded Decisions;
- caller/application makes explicit `CONTINUE / CREATE_NEW / AMBIGUOUS` determination;
- commit atomically revalidates the observed candidate universe;
- changed universe or ambiguity creates no new Decision.

The initial PostgreSQL adapter MAY globally serialize Decision initiation if that is the smallest correct implementation. Later Attention may earn optimized candidate narrowing without changing Decision identity semantics.

## 5.2 Cross-owner human seams

R2 designs but does not own:

- Human Investment Decision of Deferral;
- Human Investment Decision or other valid business basis that substantively resolves judgment.

Trusted fixture references may exercise the Decisions-side consequences. No arbitrary caller may manufacture Governance facts.

---

# 6. Temporal Decision Memory boundary

R2 must provide two distinct historical semantics.

## `as_known_at(K)`

What Polaris durably knew by knowledge cutoff `K`.

Later-recorded facts/corrections are excluded even when their effective time is earlier.

## `effective_at(T, knowledge_cutoff=K)`

Using only knowledge admitted by `K`, what Need/judgment/work/applicability state is supported as having been effective at `T`?

Default current knowledge provides the current best supported effective history.

These Decision lifecycle queries are not substitutes for future Evidence Judgment-Time Availability.

---

# 7. Non-destructive correction

R2 gives ADR-0002's correction rule executable shape.

When later information changes supported lifecycle understanding:

- original facts remain immutable;
- append explicit correction referencing the prior interpretation/fact;
- preserve effective time separately from recorded time;
- preserve Human Investment Decision or other historical acts that really occurred;
- update current/effective projections from supported corrected history;
- earlier `as_known_at` views remain unchanged.

This applies especially to:

- late External Resolution;
- later discovery that a Decision Need was erroneous/unsupported;
- incorrectly asserted relationship/lifecycle interpretation.

No generic cross-domain correction framework is required in R2.

---

# 8. Persistence boundary

Logical R2 persistence responsibilities include:

```text
Decision Need
Investment Decision current projection
multi-Portfolio Scope representation + completeness
immutable lifecycle facts/corrections
typed many-to-many Decision relationships
command idempotency receipts
minimal continuity-initiation serialization/guard state if needed
```

Required guarantees:

- one Need grounds at most one Decision;
- atomic related writes;
- expected-version protection;
- distinct-operation continuity protection;
- effective/recorded time;
- Actor Attribution separated from source/technical provenance;
- many-to-many renewal/Supersession-compatible relationship representation;
- lifecycle-lineage cycle prevention;
- restart recovery;
- fresh greenfield migration lineage;
- no legacy schema dependency.

PostgreSQL remains the initial/reference adapter only.

---

# 9. Architecture enforcement

R2 checks must fail when:

1. current source/tests import `legacy/`;
2. domain imports application/infrastructure/interfaces;
3. application imports concrete infrastructure/interfaces;
4. inward ports expose PostgreSQL/ORM/SQL/vendor-native types;
5. infrastructure bypasses domain/application semantics to invent lifecycle business state;
6. runtime/work/output IDs become Investment Decision identity;
7. current migrations target legacy schema objects;
8. persistence represents Supersession as one-to-one or as a replacement lifecycle status;
9. unresolved Decision Scope is silently encoded as a fake/default Portfolio identity.

Prefer small custom/static enforcement unless a framework independently earns its dependency.

---

# 10. Testing seams

## Domain

Prove:

- Need/Decision identity;
- partial/unresolved Scope;
- Need vs judgment vs work vs Supersession separation;
- Deferral/re-Deferral;
- withdrawal/resumption;
- External Resolution;
- unsupported Need retraction;
- renewal/Supersession/cycle rules;
- correction semantics.

## Application with deterministic fakes

Prove:

- command/query contracts;
- Actor Attribution/provenance separation;
- operation idempotency;
- expected-version conflict;
- continuity arbitration for different operation IDs;
- trusted human-basis seams;
- dual temporal queries;
- transaction outcomes.

## PostgreSQL adapter contract

Prove:

- atomicity/restart durability;
- one Need -> at most one Decision;
- zero/partial/established Scope;
- continuity-safe initiation;
- immutable/corrected history;
- many-to-many Supersession;
- cycle rejection;
- dual temporal reads;
- fresh migration lineage.

## Acceptance

R2 provides **foundational acceptance evidence** for the Decision-kernel portions of:

- `AS-001`;
- `AS-002`;
- proposed amended `AS-003`;
- `AS-004`;
- `AS-005`.

R2 may fully close:

- `AS-022` Legacy isolation.

R2 must not claim full closure of scenarios requiring not-yet-implemented Attention, Evidence/Decision Context, Governance-owned Human Investment Decision, or other deferred owners.

---

# 11. Donor disposition

Existing owner-scoped donor conclusions remain:

- PostgreSQL settings mechanics/tests → transplant with boundary cleanup / mine test logic;
- engine/session mechanics → mine mechanics, rewrite boundary;
- Alembic bootstrap/test mechanics → mine mechanics only;
- legacy global persistence taxonomy/completed-run/workflow identity → leave in legacy;
- no first-class legacy `InvestmentDecision` matching greenfield semantics → new domain kernel.

Donor findings never determine domain/design semantics.

---

# 12. Explicit exclusions

R2 does not implement/pre-scaffold:

- Attention engine/scheduler;
- Evidence owner/store;
- Investment Intelligence/Recommendation;
- Portfolio Risk internals;
- Governance/Human Investment Decision persistence;
- Review Condition domain implementation;
- Action Continuity;
- Learning;
- prior-Decision contextual retrieval/binding;
- graph database;
- generic asynchronous runtime;
- generic event-sourcing/correction/workflow/plugin framework;
- legacy data migration.

---

# 13. Required pre-Spec design set

The complete design set remains:

1. [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md)
2. [`investment-decisions-lifecycle-model.md`](investment-decisions-lifecycle-model.md)
3. [`investment-decisions-decision-relationship-model.md`](investment-decisions-decision-relationship-model.md)
4. [`application-use-cases-investment-decision-lifecycle.md`](application-use-cases-investment-decision-lifecycle.md)
5. [`durable-persistence-investment-decision-history.md`](durable-persistence-investment-decision-history.md)

The audit also produced a proposed requirements reconciliation:

- [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md)

The five design files and requirement amendment remain **Proposed** pending owner review.

---

# 14. R2 pre-Spec exit criteria

The design gate can close only when:

- one Need / one Decision identity is explicit;
- zero/partial/established Scope semantics are explicit;
- Decision Need status, substantive judgment status, unresolved work posture, and Supersession are independent;
- Deferral/re-Deferral require proper human basis;
- work withdrawal is not investment judgment;
- External Resolution changes Need status, not judgment history;
- unsupported Need retraction may occur without deleting later human acts;
- Supersession is many-to-many and may apply after resolution;
- lineage is acyclic;
- different concurrent initiation operations fail closed on continuity change/ambiguity;
- Actor Attribution is distinct from trigger/technical provenance;
- late facts use explicit correction;
- as-known-at and effective-at semantics are distinct;
- future prior-Decision context binds target historical state;
- Action Continuity ↔ Portfolio & Risk interaction is documented;
- acceptance claims are milestone-honest;
- persistence remains technology-neutral;
- no implementation Spec must invent any remaining load-bearing semantic choice.

---

# 15. Immediate transition

Only after owner approval of the audit-remediated design set and requirements amendment, followed by a final adversarial Spec-readiness audit with no blockers, may R2 transition to `to-specs`.

No implementation ticket or production code is authorized before that transition.
