# R2 Decision Kernel and Historical Truth — Component Boundaries

**Status:** Approved  
**Release:** 0.2.0  
**Approved:** 2026-09-04  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define the implementation-facing boundary for the first greenfield durable Decision kernel while keeping unresolved design work out of Specs.

## Authority

This plan is subordinate to:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md);
- [`../roadmap/0.2.0.md`](../roadmap/0.2.0.md);
- [`../product/domain-model.md`](../product/domain-model.md) and [`../../CONTEXT.md`](../../CONTEXT.md);
- accepted ADRs under [`../adr/`](../adr/).

This plan does not reopen R1 architecture. `legacy/v0_1/` remains donor material only.

Approval of this plan authorizes detailed design. The design gate remains closed to `to-specs` until the complete design set below is reviewed after the R2 pre-Spec adversarial audit remediation.

---

# 1. R2 destination

R2 should leave Polaris able to answer, without workflow replay:

> What Investment Decision exists; why is it the same, different, renewed, or superseding Decision; what Decision Need/Subject/Scope and lifecycle facts were known; what is currently supported as having been effective; and can that truth survive retry, restart, correction, and concurrent work without semantic duplication?

R2 is deliberately narrower than the full 0.2.0 lifecycle.

```text
Decision Need
      ↓
Investment Decision identity
      ↓
Scope establishment/refinement
      ↓
unresolved work posture
  active / human-deferred / withdrawn
      ↓
substantive resolution / External Resolution / Need correction
      ↓
renewal + Supersession relationships
      ↓
immutable historical truth + non-destructive correction
      ↓
Decision Memory queries
```

R2 does **not** implement Recommendation, AI reasoning, full Evidence, Governance-owned Human Investment Decision, Action Intent, or Learning.

Later facts must attach to the R2 Decision identity without redefining it.

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

plus minimum tests/enforcement.

Do not scaffold other R1 entities merely because they exist architecturally.

---

# 3. Decisions boundary

R2 Decisions must establish:

- explicit Investment Decision/Decision Need identities;
- Decision Subject;
- Decision Scope with explicit unresolved state;
- resolution disposition distinct from work disposition;
- Deferral as a Decisions-side consequence of a trusted Human Investment Decision basis, not a fabricated R2 human fact;
- explicit work withdrawal distinct from Deferral/resolution;
- substantive resolution;
- External Resolution;
- non-destructive retraction/correction when the original Decision Need was erroneous/unsupported;
- renewal relationships;
- Supersession as an orthogonal relationship that may apply to unresolved or resolved Decisions;
- lifecycle correction when late knowledge changes supported effective interpretation;
- Actor Attribution separate from trigger/technical provenance;
- continuity ambiguity/concurrency semantics.

## 3.1 State decomposition

R2 must not use the rejected single enum:

```text
ACTIVE / DEFERRED / RESOLVED / EXTERNALLY_RESOLVED / SUPERSEDED
```

as though those concepts were one dimension.

Instead design/implementation must preserve:

```text
resolution disposition
    unresolved
    substantively resolved
    externally resolved
    Decision Need retracted/unsupported

work disposition while unresolved
    active
    deferred
    withdrawn

continuing applicability
    typed Supersession relationship(s)
```

Supersession never rewrites a resolved Decision into a fake `SUPERSEDED` resolution state.

---

# 4. Decision relationships

R2 implements typed durable:

- `RENEWED_FROM`;
- `SUPERSEDES`.

Rules:

- lifecycle-lineage graph is acyclic;
- no fixed one-to-one Supersession cardinality;
- resolved or unresolved Decisions may be superseded;
- relationships preserve effective/recorded time;
- late relationship corrections are non-destructive;
- physical representation must remain compatible with later many-to-many `PRIOR_DECISION_CONTEXT`;
- later `PRIOR_DECISION_CONTEXT` must bind the target historical Decision state actually used (`target_as_known_at`/equivalent), not merely target current identity.

R2 does not yet implement contextual prior-Decision retrieval/binding.

---

# 5. Application boundary

R2 application responsibilities include:

```text
initiate_decision
establish_decision_scope
revise_decision_subject
revise_decision_scope
record_deferral_consequence
resume_decision_work
withdraw_decision_work
record_substantive_resolution
externally_resolve_decision
retract_unsupported_decision_need
initiate_renewed_decision
record_supersession
correct_decision_lifecycle
```

Queries include current/history/as-known-at/effective-at/continuity candidates/lineage.

## 5.1 Continuity arbitration

R2 must not rely on operation-id idempotency to prevent semantically duplicate Decisions from different concurrent initiation operations.

Required semantic pattern:

```text
conservative unresolved candidates
        ↓
explicit same/new/ambiguous continuity determination
        ↓
atomic revalidation at commit
        ↓
changed or ambiguous -> no new Decision
```

The adapter may implement this with serialization/locking/versioning, but the inward contract owns fail-closed semantics.

## 5.2 Cross-owner seams

R2 designs but does not own:

- Human Investment Decision of Deferral;
- Human Investment Decision/substantive resolution basis.

Trusted fixture references may exercise the Decisions-side seams. No arbitrary caller may fabricate Governance facts.

---

# 6. Decision Memory / temporal query boundary

R2 must provide:

- current Decision view;
- immutable lifecycle/relationship history;
- `as_known_at(knowledge_cutoff)`;
- `effective_at(effective_time, knowledge_cutoff)`;
- conservative unresolved continuity candidates;
- renewal/Supersession lineage.

## 6.1 Dual temporal semantics

`as_known_at` answers what Polaris durably knew at a cutoff.

`effective_at` answers what lifecycle disposition is supported as having been effective at a time, using only knowledge admitted by a stated cutoff.

Late facts may change current supported effective history but never leak backward into earlier as-known-at views.

---

# 7. Non-destructive correction

R2 must give ADR-0002's correction rule executable shape.

When later information changes supported lifecycle interpretation:

- preserve original fact;
- append explicit correction referencing prior fact/interpretation;
- preserve effective and recorded time;
- preserve Actor Attribution/provenance;
- recompute current supported projection;
- preserve earlier as-known-at history.

This is required for late External Resolution and erroneous/unsupported Decision Need cases.

No generic cross-domain correction framework is required yet.

---

# 8. Persistence boundary

R2 requires narrow semantic capabilities rather than generic CRUD/UoW.

Logical durable records:

```text
Decision Need
Investment Decision current projection
immutable lifecycle facts/corrections
many-to-many typed Decision relationships
command idempotency receipts
optional narrow continuity-arbitration physical state
```

Persistence guarantees:

- atomic related writes;
- expected-version concurrency;
- distinct-operation continuity arbitration;
- immutable history;
- effective/recorded time;
- actor/provenance separation;
- many-to-many lineage relationships;
- cycle prevention;
- recovery after restart;
- no legacy schema dependency.

PostgreSQL is initial/reference adapter only.

---

# 9. Architecture enforcement

R2 checks must fail when:

1. current source/tests import `legacy/`;
2. domain imports application/infrastructure/interfaces;
3. application imports concrete infrastructure/interfaces;
4. inward ports expose PostgreSQL/ORM/SQL/vendor-native types;
5. infrastructure bypasses application/domain to invent lifecycle business state;
6. runtime/work/output IDs become Decision identity;
7. current migrations target legacy schema objects;
8. a persistence convenience encodes Supersession as one-to-one or as a replacement resolution state contrary to approved design.

Prefer small custom/static checks unless a framework independently earns its dependency.

---

# 10. Testing seams

## Domain

Prove identity, unresolved Scope, work/resolution separation, Deferral seam, withdrawal, External Resolution, Need retraction, renewal, Supersession, corrections, and lineage cycles.

## Application with deterministic fakes

Prove command/query semantics, actor/provenance split, idempotency, continuity arbitration, expected-version conflict, cross-owner trusted bases, dual temporal queries, and transaction outcomes.

## PostgreSQL contract

Prove atomicity, restart durability, idempotency, continuity concurrency, immutable/corrected history, Scope states, many-to-many Supersession, cycle rejection, dual temporal reads, and fresh migration lineage.

## Acceptance

R2 provides **foundational acceptance evidence** for Decision-kernel portions of:

- `AS-001` New material Decision Need;
- `AS-002` Same unresolved decision resumes;
- amended `AS-003` Deferral and later resumption;
- `AS-004` Resolved decision followed by renewed judgment;
- `AS-005` External Resolution.

R2 may fully close:

- `AS-022` Legacy isolation.

R2 must **not** claim full scenario closure for scenarios requiring Attention, Evidence, Decision Context, Governance-owned Human Investment Decision, or another intentionally deferred owner.

---

# 11. Owner-scoped donor disposition

Current donor conclusions remain:

- PostgreSQL settings mechanics/tests -> `TRANSPLANT WITH BOUNDARY CLEANUP / MINE TEST LOGIC`;
- engine/session mechanics -> `MINE MECHANICS; REWRITE BOUNDARY`;
- Alembic bootstrap/test mechanics -> `MINE BOOTSTRAP/TEST MECHANICS ONLY`;
- legacy persistence taxonomy/global metadata universe -> `LEAVE IN LEGACY`;
- legacy workflow/completed-run identity -> `LEAVE IN LEGACY`;
- no first-class legacy `InvestmentDecision` matching greenfield semantics -> `NEW DOMAIN KERNEL`.

No donor finding changes domain/design authority.

---

# 12. Explicit exclusions

R2 does not implement/pre-scaffold:

- Attention engine/scheduler;
- Evidence owner/store;
- Investment Intelligence/Recommendation;
- Portfolio Risk internals;
- Governance/Human Investment Decision store;
- Review Condition domain implementation;
- Action Continuity;
- Learning;
- prior-Decision contextual retrieval/binding;
- graph database;
- generic asynchronous runtime;
- generic correction/event-sourcing framework;
- generic plugin/workflow/runtime spine.

---

# 13. Required pre-Spec design set

The complete R2 design set is:

1. [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md)
2. [`investment-decisions-lifecycle-model.md`](investment-decisions-lifecycle-model.md)
3. [`investment-decisions-decision-relationship-model.md`](investment-decisions-decision-relationship-model.md)
4. [`application-use-cases-investment-decision-lifecycle.md`](application-use-cases-investment-decision-lifecycle.md)
5. [`durable-persistence-investment-decision-history.md`](durable-persistence-investment-decision-history.md)

The pre-Spec adversarial audit found material gaps and reopened this design gate. The revised documents remain **Proposed** until reviewed/approved as a set.

Only after approval and a final adversarial Spec-readiness audit may this plan hand to `to-specs`.

---

# 14. R2 design exit criteria

Design is ready for Specs only when all are true:

- Scope-unresolved initiation is explicit;
- Deferral requires proper human-decision basis;
- work withdrawal is distinct from Deferral/resolution;
- unsupported Decision Need correction is explicit/non-destructive;
- Supersession is an orthogonal many-to-many relationship and resolved Decisions can be superseded;
- renewal/Supersession lineage is acyclic;
- distinct concurrent initiation operations fail closed on continuity ambiguity;
- Actor Attribution is distinct from trigger/technical provenance;
- late lifecycle facts use explicit correction;
- as-known-at and effective-at query semantics are distinct;
- future prior-Decision context binds target historical state;
- Action Continuity ↔ Portfolio & Risk interaction is documented;
- R2 acceptance evidence is not overstated;
- persistence remains technology-neutral with PostgreSQL as initial adapter;
- no unresolved design choice is deferred into an implementation Spec.

---

# 15. Immediate transition

After the revised five-document design set is approved:

```text
approved R2 component boundary
        +
approved pre-Spec design set
        +
final adversarial Spec-readiness audit = GREEN
        ↓
`to-specs`
        ↓
multiple narrow R2 Specs
```

No implementation ticket or production code is authorized before that transition.
