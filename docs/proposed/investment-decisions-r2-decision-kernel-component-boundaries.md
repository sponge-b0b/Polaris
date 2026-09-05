# R2 Decision Kernel and Historical Truth — Component Boundaries

**Status:** Proposed  
**Release:** 0.2.0  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define the implementation-facing component boundaries for the first greenfield product slice without introducing new architectural choices or inheriting legacy business topology.

## Authority

This plan is subordinate to:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md) — approved architecture;
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md) — approved requirements;
- [`../roadmap/0.2.0.md`](../roadmap/0.2.0.md) — approved roadmap;
- [`../product/domain-model.md`](../product/domain-model.md) and [`../../CONTEXT.md`](../../CONTEXT.md) — frozen domain semantics;
- accepted ADRs under [`../adr/`](../adr/).

This document does not reopen the R1 architecture. It translates the approved owners into the smallest R2 implementation boundary that can establish first-class Investment Decision identity and durable historical truth.

`legacy/v0_1/` is donor material only. Donor findings below are scoped by current R2 owners and do not grant legacy types, schemas, or runtime mechanisms architectural authority.

---

# 1. R2 destination

R2 should leave Polaris with a small but real durable business core capable of answering, without workflow replay:

> What Investment Decision exists, why is it the same or a different decision, what lifecycle state has it passed through, what was true at a relevant historical point, and can that truth survive retry, restart, and concurrent work without semantic duplication?

The R2 path is deliberately narrower than the full 0.2.0 lifecycle:

```text
Decision Need
      ↓
Investment Decision identity
      ↓
resume / defer / resolve / externally resolve / supersede
      ↓
durable current + historical truth
      ↓
Decision Memory query
```

R2 does **not** yet need to form an Investment Recommendation, perform AI reasoning, record Human Investment Decision authority, establish Action Intent, or evaluate Outcomes.

Those later facts must be able to attach to the R2 decision identity without redefining it.

---

# 2. R2 architectural slices

R2 earns only the following current source boundaries:

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

Plus the smallest test structure required to enforce architecture and verify behavior.

Do not create the other R1 domain or infrastructure directories merely because the architecture names them. Evidence, intelligence, portfolio, governance, continuity, learning, follow-up, model, source, identity, scheduling, observability, configuration, and interface packages should wait until a current milestone actually needs them.

---

# 3. Decisions domain boundary

The Decisions domain owns decision lifecycle identity and invariants. It must remain persistence- and transport-agnostic.

## 3.1 First-class identities

R2 must establish explicit types or equivalent domain representations for at least:

- Investment Decision identity;
- Decision Need identity where a durable Decision Need is represented independently;
- Subject identity/reference;
- Decision Scope;
- causal relationship to a prior Investment Decision when a resolved choice is renewed;
- Supersession relationship when one decision replaces another.

Investment Decision identity must not be derived from:

- workflow/job/run identity;
- model invocation identity;
- report/output identity;
- database row ordering;
- Subject alone;
- Evidence arrival alone;
- a changed Recommendation alone;
- a changed market state alone.

## 3.2 Lifecycle semantics

The domain must represent enough state/history to distinguish:

- unresolved active decision work;
- Deferral while preserving the same unresolved decision;
- later resumption of that deferred decision;
- substantive resolution;
- External Resolution caused by circumstances before substantive human resolution;
- Supersession;
- a new causally linked Investment Decision after a previous decision has resolved.

A resolved Investment Decision never reopens.

A renewed judgment after resolution creates a new Investment Decision linked to the prior one.

Deferral does not create a new Investment Decision.

A material change in Evidence, state, Risk, or Recommendation does not by itself create a new Investment Decision.

## 3.3 Lifecycle facts vs mutable convenience state

The domain may expose a convenient current lifecycle view, but durable history must preserve the facts required to reconstruct prior state.

Implementation may use a current-state record plus immutable lifecycle facts, or another representation satisfying the same semantic contract. R2 must not force future modules to infer historical truth from overwritten current fields.

## 3.4 No giant aggregate

Investment Decision is the lifecycle root, not a container for all future decision-related facts.

R2 must not pre-create placeholders for Evidence, Recommendation, authority, Action Intent, Outcome, Decision Evaluation, or Lesson inside the Investment Decision object merely because those concepts will later reference it.

---

# 4. Application boundary

The application layer owns coordination, idempotency, expected-version checks, and durable transaction semantics.

## 4.1 R2 commands

R2 should support the minimum command responsibilities needed for its acceptance scenarios:

```text
initiate_decision
resume_decision_work
defer_decision
resolve_decision
externally_resolve_decision
supersede_decision
```

These are conceptual use cases, not required function/class names.

The exact public API should remain small and domain-oriented.

## 4.2 Command invariants

Every mutating use case must:

1. load required current state through inward-owned ports;
2. validate domain preconditions;
3. reject invalid lifecycle transitions explicitly;
4. apply expected-version/concurrency protection where stale concurrent work could overwrite newer truth;
5. persist the resulting business facts atomically where the invariant requires it;
6. use an operation-specific idempotency identity for retryable commands;
7. return success only after required durable state commits.

Investment Decision ID is not a universal idempotency key.

## 4.3 No asynchronous framework yet

R2 does not currently require guaranteed asynchronous follow-up to satisfy its milestone acceptance scenarios.

Therefore R2 should **not** implement a durable-follow-up port, outbox, broker integration, event bus, or worker framework speculatively.

If an R2 implementation detail later demonstrates a genuine required asynchronous obligation, it must use the approved technology-neutral durable-follow-up architecture rather than bypassing it.

---

# 5. Query boundary and Decision Memory

R2 needs a query boundary that can assemble current or historical decision state without exposing persistence-native representations.

## 5.1 Required query capabilities

At minimum, the application must be able to retrieve:

- one Investment Decision by identity;
- its current lifecycle state;
- its lifecycle history in attributable temporal order;
- its Subject and Decision Scope;
- its Deferral/resumption history where present;
- resolution type and time where present;
- causal prior/new-decision relationship where present;
- Supersession relationships where present;
- a historically faithful view as of a supported prior point where required by the R2 acceptance scenarios.

The query result is a Decision Memory view, not a new canonical `DecisionRecord` entity.

## 5.2 Historical fidelity

A historical query must not silently project facts that became known only later into an earlier state.

R2 does not yet need full future Evidence/Judgment-Time Availability reconstruction, but its temporal model must leave that later capability possible without redefining Decision identity or replacing historical facts.

---

# 6. Inward-owned persistence contracts

Persistence ports are defined around R2 semantics rather than around PostgreSQL, SQLAlchemy, or tables.

## 6.1 Owner-specific store

The Decisions application boundary needs an owner-specific persistence capability for loading and committing Investment Decision lifecycle truth.

The contract should express operations such as:

- load current decision state by Investment Decision identity;
- determine whether an unresolved decision matching the explicit identity/continuity criteria already exists;
- persist newly established lifecycle facts;
- persist current-state convenience data if used;
- preserve expected-version / compare-and-set semantics;
- enforce operation idempotency;
- retrieve ordered historical lifecycle facts.

The exact interface should be the smallest shape needed by the use cases. Do not create a generic CRUD repository or generic persistence service.

## 6.2 Application Unit of Work

R2 should establish a semantic application transaction boundary only if multiple persistence operations must be coordinated as one business commit.

If a Unit of Work is introduced, it must expose Polaris transaction semantics, not ORM sessions or database connections.

It may internally coordinate one or more adapter-specific stores.

Do not introduce a Unit of Work merely because the pattern is common; earn it from an actual atomicity requirement in the R2 commands.

## 6.3 Required guarantees

The initial persistence adapter must prove:

- atomicity for related R2 business changes;
- uniqueness of first-class Investment Decision identity;
- idempotent retry behavior for retryable commands;
- optimistic concurrency/version protection or equivalent compare-and-set semantics;
- immutable preservation of lifecycle history;
- durable recovery after process restart;
- deterministic temporal ordering sufficient for historical reconstruction.

---

# 7. Initial PostgreSQL adapter

PostgreSQL remains the initial/reference R2 persistence adapter, but no domain/application contract may expose PostgreSQL or ORM-specific types.

## 7.1 Fresh schema lineage

R2 must establish a fresh current migration lineage and greenfield schema for the selected initial adapter.

No migration may alter or reuse a legacy table merely because an analogous table exists in `legacy/v0_1/`.

The initial schema should contain only the structures earned by R2 semantics.

## 7.2 Physical design rules

The physical schema may use PostgreSQL-specific strengths internally where they help satisfy the port contract, including:

- relational uniqueness/foreign-key constraints;
- transactional writes;
- indexes supporting current and historical reads;
- version columns or equivalent concurrency primitives;
- structured payload support where justified.

Do not make a future adapter reproduce PostgreSQL's physical model exactly. Adapter contract equivalence is semantic, not schema equivalence.

## 7.3 ORM/library choice

ORM, migration, and PostgreSQL-driver choices remain implementation decisions for the R2 Spec unless a choice would materially change the inward-owned contract.

The Spec should prefer the smallest dependency set that satisfies the approved semantics and testing requirements.

---

# 8. Architecture enforcement boundary

R2 is the point where the documented architecture becomes executable policy.

Before substantial greenfield production code accumulates, tests/checks must fail when:

1. current source or tests import from `legacy/`;
2. `domain` imports `application`, `infrastructure`, or `interfaces`;
3. `application` imports concrete `infrastructure` implementations;
4. domain/application ports expose PostgreSQL, SQLAlchemy/ORM, SQL-expression, or other adapter-native types;
5. an infrastructure adapter bypasses domain/application semantics to invent business lifecycle transitions;
6. runtime/job/output identifiers are used as Investment Decision identity;
7. current migrations target legacy schema objects.

Use a small custom import/AST check if sufficient. Do not add an architecture-lint framework unless it independently earns its dependency.

---

# 9. Testing seams

R2 should establish four test seams and no more than necessary.

## 9.1 Pure domain tests

Verify lifecycle identity and transition invariants without database or services.

These tests should be the primary executable specification for same-decision vs new-decision behavior.

## 9.2 Application tests with deterministic fakes

Verify use-case coordination, idempotency expectations, concurrency handling, and transaction outcomes through inward-owned persistence fakes.

These tests must not import the PostgreSQL adapter.

## 9.3 Persistence adapter contract tests

Run the same semantic contract against the PostgreSQL adapter where practical:

- atomic commit;
- uniqueness;
- idempotent retry;
- concurrency conflict;
- immutable history;
- historical ordering/retrieval.

## 9.4 Product acceptance tests

R2 should supply objective acceptance evidence for the roadmap scenarios it owns:

- `AS-001` New material Decision Need;
- `AS-002` Same unresolved decision resumes;
- `AS-003` Deferral and later resumption;
- `AS-004` Resolved decision followed by renewed judgment;
- `AS-005` External Resolution;
- `AS-022` Legacy isolation.

Acceptance tests assert canonical business facts and historical relationships, not technical job/workflow completion.

---

# 10. Owner-scoped donor findings

Donor inspection was performed only after the current R2 owners were established.

## 10.1 PostgreSQL settings mechanics

**Donor:** `legacy/v0_1/core/database/settings.py` and its unit tests.

**Classification:** `TRANSPLANT WITH BOUNDARY CLEANUP / MINE TEST LOGIC`.

Useful mechanics include:

- typed PostgreSQL connection configuration;
- `POLARIS_DATABASE_URL` override behavior;
- safe URL construction/escaping;
- boolean/integer configuration validation;
- credential-safe `repr` behavior.

The current adapter should own these as infrastructure configuration. They must not become application/domain configuration semantics.

## 10.2 PostgreSQL engine/session mechanics

**Donor:** `legacy/v0_1/core/database/postgres.py`.

**Classification:** `MINE MECHANICS; REWRITE BOUNDARY`.

Useful mechanics include:

- async SQLAlchemy engine creation;
- async session factory configuration;
- `pool_pre_ping` and adapter-level engine options.

Do **not** transplant the module-level global engine/session lifecycle or import-time environment resolution. Current composition should own adapter lifetime explicitly.

Do not assume SQLAlchemy survives until the R2 Spec confirms it is the smallest suitable initial implementation.

## 10.3 Migration bootstrap

**Donor:** legacy Alembic bootstrap and its foundation tests.

**Classification:** `MINE BOOTSTRAP/TEST MECHANICS ONLY`.

The old schema taxonomy must not survive. The legacy foundation test treats workflow runs/events, reports, agents, RAG, telemetry, evaluation, market/macro/news, and many other concerns as one global persistence metadata universe. That is incompatible with the greenfield owner-driven R2 boundary.

If Alembic is retained, establish a fresh migration lineage that imports only current greenfield persistence models.

## 10.4 Legacy persistence taxonomy and lineage

**Donor:** legacy application persistence packages, persistence-lineage abstractions, completed-run/workflow storage, and generic model registry.

**Classification:** `LEAVE IN LEGACY BY DEFAULT`.

R2 should not resurrect:

- completed-run archive as business memory;
- workflow/event persistence as Decision identity;
- generic PersistenceLineage as the domain history model;
- report/agent/RAG/telemetry tables because they already exist;
- a single global persistence taxonomy spanning unrelated future owners.

Specific algorithms may be reconsidered later only when a current owner has a matching need.

## 10.5 Legacy decision model

Repository search found no first-class `InvestmentDecision` implementation matching the approved greenfield lifecycle.

**Classification:** `REWRITE / NEW DOMAIN KERNEL`.

Do not adapt legacy `StrategySynthesisDecision`, workflow-output identity, recommendation records, or trade packaging into Investment Decision simply to save code.

---

# 11. Explicit R2 exclusions

R2 must not implement or pre-scaffold:

- AI/model gateway or reasoning orchestration;
- Evidence acquisition/binding beyond references needed to keep future compatibility possible;
- Investment Recommendation formation;
- Portfolio Risk analysis;
- Governance/authority review;
- Human Investment Decision;
- Action Intent or broker reconciliation;
- Outcome/Decision Evaluation/Lesson;
- Attention scheduling or autonomous monitoring;
- durable asynchronous follow-up infrastructure unless an R2 use case proves it necessary;
- RAG/vector storage;
- reports/PDF/email/MCP surfaces;
- generic workflow/runtime/plugin frameworks;
- microservices or service extraction;
- generic event bus;
- migration of legacy business data/schema.

---

# 12. R2 implementation order

The implementation should proceed inside-out:

```text
1. Decisions domain identity + lifecycle invariants
        ↓
2. Pure domain tests / AS-001..005 semantics
        ↓
3. Application commands + query contracts
        ↓
4. Technology-neutral persistence ports
        ↓
5. Architecture/vendor-isolation checks
        ↓
6. Initial PostgreSQL adapter + fresh migration lineage
        ↓
7. Adapter contract tests
        ↓
8. Product-level R2 acceptance evidence
```

Do not begin from database tables and work inward. The schema follows the domain/application contract.

---

# 13. R2 exit criteria

R2 is complete only when all of the following are demonstrated:

1. Investment Decision is a first-class durable identity independent of workflow/job/report/model identity;
2. the same unresolved decision can resume without creating a duplicate decision;
3. Deferral preserves the same unresolved decision and later resumption is reconstructable;
4. resolved decisions never reopen;
5. renewed judgment after resolution creates a distinct causally linked Investment Decision;
6. External Resolution is distinct from substantive human resolution;
7. Supersession preserves historical identity/relationships;
8. current and historical decision lifecycle views are reconstructable from direct business facts;
9. retry cannot create duplicate business truth for an idempotent operation;
10. stale concurrent mutation cannot silently overwrite newer decision state;
11. persistence contracts contain no PostgreSQL/ORM/vendor-native types;
12. the initial PostgreSQL adapter satisfies the same inward-owned contract as deterministic test fakes;
13. greenfield migrations establish a fresh schema lineage and do not target legacy tables;
14. executable architecture checks prevent inward vendor leakage and legacy imports;
15. `AS-001` through `AS-005` and `AS-022` have objective acceptance evidence;
16. no later 0.2.0 domain owner has been prematurely collapsed into the Decisions aggregate or persistence taxonomy.

# Handoff after approval

Once this component-boundary plan is approved, it is decision-complete enough to act as an intentionally non-Wayfinder planning source for `to-specs`.

The next delivery transition should therefore be:

```text
approved R2 component-boundary plan
        ↓
`to-specs`
        ↓
R2 implementation Spec(s)
        ↓
`to-tickets`
        ↓
normal ticket implementation/review/verification lifecycle
```

A Wayfinder should be introduced only if implementation planning exposes a genuinely unresolved material architectural choice that cannot be resolved from the approved architecture and this plan.