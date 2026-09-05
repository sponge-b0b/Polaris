# R2 Decision Kernel and Historical Truth — Component Boundaries

**Status:** Approved  
**Release:** 0.2.0  
**Approved:** 2026-09-04  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define the implementation-facing component boundaries for the first greenfield product slice without introducing new architectural choices or inheriting legacy business topology.

## Authority

This plan is subordinate to:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- proposed [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md);
- [`../roadmap/0.2.0.md`](../roadmap/0.2.0.md);
- [`../product/domain-model.md`](../product/domain-model.md) and [`../../CONTEXT.md`](../../CONTEXT.md);
- accepted ADRs under [`../adr/`](../adr/).

Approval of this component-boundary plan authorizes detailed R2 design, not immediate implementation. The detailed design set below must be approved and pass adversarial Spec-readiness review before `to-specs`.

`legacy/v0_1/` is donor material only.

---

# 1. R2 destination

R2 establishes the smallest durable business kernel capable of answering, without workflow replay:

> What Investment Decision exists, why is it the same or a different Decision, what supported lifecycle/work state is known now or was known historically, how is it related to prior Decisions, and can that truth survive retry, restart, correction, and concurrency without semantic duplication?

R2 path:

```text
Decision Need
      ↓
Investment Decision identity
      ↓
Scope/Subject refinement
      ↓
active / human-deferred / withdrawn work
      ↓
substantive resolution | External Resolution | unsupported-Need correction
      ↓
renewal / Supersession relationships
      ↓
durable current + historical truth
      ↓
Decision Memory query
```

R2 does not yet form Recommendations, perform AI reasoning, implement Governance, establish Action Intent, or evaluate Outcomes.

---

# 2. Earned source boundaries

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

Plus minimum tests/architecture enforcement.

Do not scaffold Evidence, intelligence, portfolio, governance, continuity, learning, follow-up, model, source, identity, scheduling, observability, configuration, or interface packages before a current milestone earns them.

---

# 3. Decisions domain boundary

R2 owns:

- `InvestmentDecisionId` and `DecisionNeedId` semantics;
- Decision Subject;
- Decision Scope with explicit unresolved/partial/established semantics;
- supported lifecycle disposition:
  - `UNRESOLVED`;
  - `SUBSTANTIVELY_RESOLVED`;
  - `EXTERNALLY_RESOLVED`;
  - `NEED_RETRACTED_UNSUPPORTED`;
- unresolved work posture:
  - `ACTIVE`;
  - `DEFERRED`;
  - `WITHDRAWN`;
- immutable lifecycle facts and explicit correction semantics;
- Decision-to-Decision relationship validation;
- same-vs-new continuity invariants;
- determinate vs contested lifecycle interpretation.

Supersession is not a lifecycle disposition. It is an orthogonal typed relationship affecting continuing applicability.

Investment Decision remains a lifecycle root, not a giant aggregate for Evidence/Recommendations/authority/Action Intent/Outcome/Lesson.

---

# 4. Application boundary

R2 application owns:

- commands/queries;
- continuity arbitration;
- expected-version protection;
- operation-scoped idempotency;
- semantic transaction boundaries;
- actor/trigger/technical-provenance separation;
- trusted Deferral/substantive-resolution seams;
- correction coordination;
- relationship establishment;
- Decision Memory views.

Conceptual commands:

```text
initiate_decision
establish_or_revise_scope
revise_subject
apply_human_deferral
resume_decision_work
withdraw_decision_work
apply_substantive_resolution
apply_external_resolution
retract_unsupported_decision_need
record_lifecycle_correction
renew_decision
establish_supersession
```

No speculative async framework is earned in R2.

---

# 5. Continuity and concurrent initiation

R2 must not silently create two Decisions for the same coherent unresolved choice merely because requests use different operation IDs.

Application must:

1. discover conservative unresolved, operative candidate Decisions;
2. determine `CONTINUE_EXISTING`, `CREATE_NEW`, or `AMBIGUOUS`;
3. fail closed on ambiguity;
4. atomically revalidate candidate basis before committing `CREATE_NEW`;
5. return continuity conflict when concurrent work invalidates the basis.

R2 may use broad/global initiation serialization in PostgreSQL if that is the smallest correct implementation. No universal semantic matching heuristic or hash-derived identity is required.

---

# 6. Governance seam

R2 does not implement Governance.

Deferral and substantive resolution consume trusted references to Governance-owned Human Investment Decision or deterministic trusted fixtures in R2 tests.

R2 must not expose a generic arbitrary caller path that fabricates Human Investment Decision, Approval, Mandate Exception, or another authority act.

When Governance arrives, cross-owner atomicity may earn a broader Application Unit of Work.

---

# 7. Query / Durable Decision Memory boundary

Required semantic query capabilities:

- Decision current view by ID;
- raw immutable lifecycle history;
- current determinate or contested lifecycle interpretation;
- current Scope/Subject/work posture;
- typed renewal/Supersession lineage;
- `as_known_at(K)`;
- `effective_at(T, known_at=K)`;
- conservative unresolved continuity candidates.

Decision Memory view is not a canonical `DecisionRecord` entity.

Historical query must never leak later-recorded facts into earlier `as_known_at` views.

---

# 8. Persistence contract

Persistence ports express:

- atomic direct business-fact commit;
- immutable lifecycle facts/corrections;
- current projection reconstruction;
- idempotency receipts;
- expected-version concurrency;
- continuity arbitration/revalidation;
- many-to-many Decision relationships;
- lifecycle-lineage cycle prevention;
- dual-time historical reconstruction;
- contested interpretation preservation;
- recovery after restart.

No PostgreSQL/ORM/SQL types leak inward.

PostgreSQL remains initial/reference adapter only.

---

# 9. Fresh PostgreSQL lineage

R2 establishes fresh current migration/schema lineage. No current migration targets/reuses legacy tables because analogous legacy structures exist.

Likely logical structures:

```text
decision_needs
investment_decisions
investment_decision_lifecycle_facts
investment_decision_relationships
investment_decision_command_receipts
<optional narrow continuity guard>
```

Library/ORM/migration choices remain Spec decisions unless they alter inward semantics.

---

# 10. Architecture enforcement

Before substantial production code accumulates, executable checks fail when:

1. current source/tests import `legacy/`;
2. `domain` imports application/infrastructure/interfaces;
3. application imports concrete infrastructure/interfaces;
4. inward ports expose vendor persistence/messaging/model/source types;
5. adapter/interface bypasses application/domain to invent business lifecycle facts;
6. runtime/job/output identity becomes Investment Decision identity;
7. current migrations target legacy schema objects.

Prefer a small custom import/AST check over a framework unless one is earned.

---

# 11. R2 test seams

## Pure domain tests

Lifecycle, work posture, Scope, correction, relationship, and identity invariants.

## Application tests with fakes

Continuity, trusted-basis seams, transactions, idempotency, concurrency, correction, and queries without PostgreSQL adapter imports.

## Persistence adapter contract tests

Atomicity, uniqueness, recovery, idempotency, continuity concurrency, dual-time history, contested correction, many-to-many lineage, cycle prevention.

## Foundational product acceptance evidence

R2 supplies **foundational Decision-kernel evidence** for:

- AS-001 New material Decision Need;
- AS-002 Same unresolved Decision resumes;
- AS-003 Deferral and later resumption;
- AS-004 Resolved Decision followed by renewed judgment;
- AS-005 External Resolution;
- full AS-022 Legacy isolation.

R2 does **not** claim full AS-001–005 closure while Attention, Evidence/full Decision Context, Governance Human Investment Decision, or other required participants are intentionally absent.

---

# 12. Owner-scoped donor findings

## PostgreSQL settings

`legacy/v0_1/core/database/settings.py` and tests: **mine/transplant generic connection-validation mechanics only**.

## Engine/session mechanics

`legacy/v0_1/core/database/postgres.py`: **mine mechanics; rewrite boundary/lifetime**. Do not transplant module-global lifecycle or import-time config.

## Migration bootstrap

Legacy Alembic mechanics/tests: **mine bootstrap/test mechanics only**. Do not inherit legacy global schema taxonomy.

## Legacy persistence taxonomy

Completed-run/workflow/event/report/agent/RAG/telemetry generic persistence: **leave in legacy by default**.

## Legacy decision model

No first-class donor `InvestmentDecision` matches frozen greenfield semantics: **new domain kernel**.

---

# 13. Explicit R2 exclusions

Do not implement/pre-scaffold:

- AI/model gateway/reasoning;
- Evidence acquisition/full bindings;
- Recommendation formation;
- Portfolio Risk analysis;
- Governance/authority domain;
- Human Investment Decision payload ownership;
- Action Intent/broker reconciliation;
- Outcome/Evaluation/Lesson;
- Attention scheduling/autonomous monitoring;
- prior-Decision candidate retrieval/context binding;
- graph database/framework;
- generic workflow/event-runtime architecture;
- plugin framework;
- RAG/report architecture.

---

# 14. Pre-Spec design set

Required proposed design artifacts:

1. [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md)
2. [`investment-decisions-lifecycle-model.md`](investment-decisions-lifecycle-model.md)
3. [`investment-decisions-decision-relationship-model.md`](investment-decisions-decision-relationship-model.md)
4. [`application-use-cases-investment-decision-lifecycle.md`](application-use-cases-investment-decision-lifecycle.md)
5. [`durable-persistence-investment-decision-history.md`](durable-persistence-investment-decision-history.md)

Before `to-specs`, the complete set must be owner-approved and pass an adversarial Spec-readiness audit demonstrating that Specs need implementation decomposition rather than unresolved domain/architecture invention.

---

# 15. R2 exit criteria

R2 is complete only when implementation proves:

- first-class Decision Need/Decision identity;
- unresolved/partial Scope is honest and durable;
- human Deferral preserves same Decision;
- withdrawal is distinct from investment judgment;
- substantive vs External Resolution vs unsupported-Need correction are distinct;
- resolved Decisions never reopen;
- renewal creates new linked identity;
- Supersession is orthogonal to lifecycle and many-to-many capable;
- retries/restarts do not duplicate committed business truth;
- concurrent initiation cannot silently duplicate one coherent unresolved choice;
- append-only corrections preserve prior as-known-at history;
- contested lifecycle interpretation is not silently collapsed;
- historical queries separate recorded knowledge from effective understanding;
- actor attribution and technical provenance remain distinct;
- current paths remain independent of `legacy/`.
