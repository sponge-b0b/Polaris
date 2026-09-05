# Durable Persistence for Investment Decision History

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `durable-persistence`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define the R2 persistence semantics and initial PostgreSQL adapter design precisely enough that implementation Specs can choose concrete libraries/schema details without redefining business truth, history, idempotency, or concurrency.

## Authority

This design refines:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md);
- [`investment-decisions-lifecycle-model.md`](investment-decisions-lifecycle-model.md);
- [`application-use-cases-investment-decision-lifecycle.md`](application-use-cases-investment-decision-lifecycle.md);
- [`investment-decisions-r2-decision-kernel-component-boundaries.md`](investment-decisions-r2-decision-kernel-component-boundaries.md);
- accepted ADR 0002 and ADR 0003 under [`../adr/`](../adr/).

PostgreSQL is the initial/reference adapter, not the persistence architecture.

---

# 1. Persistence objective

R2 persistence must make these statements true independently of workflow/job/runtime replay:

1. an Investment Decision and its Decision Need survive restart;
2. lifecycle facts are immutable and historically reconstructable;
3. current Decision state is efficiently readable;
4. retries do not duplicate business facts;
5. stale concurrent commands cannot silently overwrite newer state;
6. Supersession is atomically visible as predecessor + successor relationship;
7. historical as-known-at queries do not leak later-recorded facts backward;
8. persistence-native types do not leak into domain/application contracts;
9. current greenfield storage has no runtime/schema dependency on `legacy/`.

---

# 2. Inward-owned persistence contracts

R2 needs two narrow capabilities.

## 2.1 Decision command store

The application needs a semantic write capability that can:

- load one current Investment Decision and its version;
- inspect a prior command result by operation identity;
- commit a one-Decision lifecycle change atomically;
- commit a Supersession change spanning predecessor and successor atomically;
- preserve immutable lifecycle facts;
- preserve/update current-state projection;
- persist idempotency receipt/result;
- fail explicitly on uniqueness/concurrency conflict.

The port must not expose:

- SQL strings;
- PostgreSQL connection/session objects;
- ORM model instances;
- database transaction handles;
- table names;
- vendor-specific exceptions.

## 2.2 Decision memory reader

The application needs a semantic read capability that can:

- return current Decision state inputs;
- return ordered lifecycle facts;
- return an as-known-at historical view or enough facts to assemble one;
- retrieve causal/supersession relationships;
- find bounded candidate unresolved Decisions for later continuity/navigation use.

The reader may use optimized projections internally but must not make those projections the sole historical authority.

---

# 3. No platform-wide Unit of Work yet

R2 does not need a generic platform Unit of Work merely because the architecture permits one later.

The Decisions command store itself can expose atomic semantic commit operations sufficient for R2 because all currently coordinated durable business facts belong to the same domain owner.

A broader application Unit of Work should be introduced only when a later use case must atomically coordinate independently owned stores—for example a future Governance-owned Human Investment Decision plus the Decisions-owned substantive-resolution fact.

This avoids premature transaction abstraction while preserving the future seam.

---

# 4. Logical durable record set

The initial adapter needs a small logical record set. Exact table/class names remain implementation details, but the semantic records are:

## 4.1 Decision Need record

Preserves:

- Decision Need ID;
- attributable need statement;
- origin/source reference;
- raised/recognized time;
- recorded time;
- immutable creation metadata.

A Decision Need is not a workflow trigger row.

## 4.2 Investment Decision current record

Provides efficient current-state access and concurrency protection.

Preserves at least:

- Investment Decision ID;
- Decision Need ID;
- current Subject representation/reference;
- current Scope representation;
- current lifecycle state;
- current domain version;
- creation time;
- terminal time/type where applicable;
- renewed-from predecessor reference where applicable;
- superseded-by successor reference where applicable.

This current record is a convenience/current-state authority backed by immutable lifecycle history. It must never be the only historical record.

## 4.3 Investment Decision lifecycle fact record

Append-only record for typed lifecycle facts.

Preserves at least:

- fact ID;
- Decision ID;
- per-Decision sequence/version;
- fact kind;
- effective/occurred time;
- recorded/committed time;
- operation ID;
- attributable context/reference;
- related Decision ID when applicable;
- typed fact-specific payload/columns.

The adapter may use a discriminated structured payload for fact-specific detail where that is the smallest clean design, but stable/query-critical dimensions must not be hidden only in opaque generic metadata.

## 4.4 Decision relationship record or equivalent relational representation

Preserves explicit relationships such as:

- `renewed_from`;
- `supersedes` / `superseded_by`.

The physical representation may use dedicated relationship rows or constrained foreign-key columns where cardinality remains unambiguous. The semantic requirement is explicit durable relationship identity and queryability, not a particular schema form.

## 4.5 Command idempotency receipt

Preserves enough application durability metadata to support exact retry semantics:

- operation ID;
- command kind;
- canonical semantic request fingerprint or equivalent comparison data;
- affected Decision ID(s);
- committed resulting version(s);
- stable semantic result needed for replay;
- committed time.

This record is not domain identity and is not part of Decision Memory except as technical/application provenance when debugging.

---

# 5. Current state + immutable history consistency

A successful lifecycle mutation must atomically maintain both:

```text
immutable lifecycle fact
        +
current Decision projection/version
        +
command idempotency receipt
```

The adapter must never commit a new current state without the corresponding immutable fact, or append the fact while leaving the required current projection/version stale.

If the transaction fails, the semantic command is not successful.

---

# 6. Version and compare-and-set persistence

The adapter must enforce application expected-version semantics in the durable store.

Equivalent behavior:

```text
UPDATE/commit Decision
ONLY IF persisted version == expected version
```

On success:

- exactly one new lifecycle version is committed for a normal single-Decision mutation;
- current version increments once;
- corresponding lifecycle fact uses the new sequence/version.

On conflict:

- no lifecycle fact from the stale command remains;
- no idempotency receipt claims success;
- application receives a technology-neutral concurrency conflict.

The PostgreSQL adapter may implement this through conditional `UPDATE`, locking, constraints, transaction isolation, or another correct mechanism. The port does not mandate the mechanism.

---

# 7. Idempotency persistence

Idempotency must survive process restart.

The adapter must distinguish atomically:

1. no receipt exists → command may attempt commit;
2. receipt exists with same semantic request → return recorded result;
3. receipt exists with different semantic request → idempotency conflict.

The receipt must be committed in the same transaction as the business changes whose success it represents.

A crash after the business transaction commits but before the caller receives the response must therefore be recoverable by retrying the same operation ID and receiving the original semantic result.

---

# 8. Supersession transaction

Supersession is the most demanding R2 persistence transaction.

One atomic commit must include:

- predecessor expected-version validation;
- predecessor terminal state/version update;
- predecessor `DecisionSuperseded` fact;
- successor Decision Need when newly created;
- successor Investment Decision current record;
- successor `DecisionInitiated` fact;
- predecessor/successor relationship;
- one idempotency receipt/result describing both IDs/versions.

No committed observer may see a half-superseded topology.

Database constraints should reinforce this invariant where practical.

---

# 9. Renewal persistence

Renewed judgment after terminal resolution creates a new Decision record/history.

The predecessor row/history is not reopened or updated merely to make it current again.

The successor preserves explicit `renewed_from` relationship to the terminal predecessor.

A relational constraint or adapter validation must reject impossible self-reference and should prevent relationship cycles where the chosen physical representation could otherwise permit them.

---

# 10. Subject and Scope history

Current Subject/Scope may be stored on the current Decision record for efficient access.

Every material revision must also be preserved in immutable lifecycle history so historical views can reconstruct prior Subject/Scope values.

The adapter must not rely on database temporal-table magic as the only representation of domain history. Native temporal features may be used internally if useful, but the inward semantic contract remains explicit lifecycle facts.

---

# 11. Temporal persistence model

Every lifecycle fact preserves both:

- effective/occurred time;
- recorded/committed time.

The database commit timestamp alone is insufficient because some legitimate business facts may be recorded after their effective time.

Conversely, effective time alone is insufficient because it would allow hindsight leakage into an earlier `as-known-at` query.

## 11.1 As-known-at query

A query for knowledge cutoff `T` must exclude any fact whose recorded/committed time is after `T`, regardless of its effective time.

Within the eligible fact set, deterministic per-Decision sequence/version governs lifecycle reconstruction.

This is a minimal R2 foundation for later Judgment-Time Availability semantics; it does not claim that all future Evidence temporality is solved by Decision timestamps.

---

# 12. Deterministic ordering

Lifecycle facts require a stable per-Decision total order.

R2 uses the monotonic Decision version/sequence as canonical ordering inside one Decision history.

Timestamps are descriptive temporal facts and query cutoffs; they must not be the sole ordering primitive because equal/low-resolution clocks and late-recorded facts can create ambiguity.

The store must enforce uniqueness of `(decision_id, sequence/version)` or an equivalent invariant.

---

# 13. PostgreSQL initial adapter design

PostgreSQL is selected as the initial/reference adapter because its transaction, relational-integrity, uniqueness, indexing, and concurrency capabilities fit the R2 contract well.

The adapter may use:

- UUID/native identity columns;
- foreign keys for Decision Need and Decision relationships;
- unique constraints for operation ID and per-Decision sequence;
- check constraints for constrained lifecycle/state values where useful;
- conditional updates/row locks for expected-version behavior;
- JSON/JSONB for purpose-named structured payloads that are not stable query dimensions;
- transactional DDL/migration capabilities where supported by the migration tool.

The adapter must not make PostgreSQL representations part of the domain/application API.

---

# 14. Physical schema guidance

The first schema should be small and owner-scoped.

Expected logical tables are roughly:

```text
decision_needs
investment_decisions
investment_decision_lifecycle_facts
investment_decision_relationships   # only if not represented cleanly on constrained decision columns
investment_decision_command_receipts
```

This is design guidance, not mandatory final SQL naming.

Do not add tables for:

- workflows/jobs;
- agents/models;
- reports;
- RAG;
- Recommendation;
- Governance;
- Action Intent;
- Outcome/Lesson;
- generic platform persistence lineage;
- generic event sourcing.

Those owners have not been earned by R2 persistence work.

---

# 15. Constraint strategy

The initial adapter should encode mechanically enforceable invariants in the database when doing so reduces invalid states without duplicating domain policy.

Good candidates include:

- unique Decision IDs;
- unique Decision Need IDs;
- unique command operation IDs;
- unique per-Decision lifecycle sequence;
- foreign-key integrity for Decision relationships;
- non-null required timestamps/versions;
- valid current lifecycle state values;
- no direct self-reference for renewal/Supersession.

Rules whose meaning depends on domain history—such as whether a predecessor is terminal before renewal—remain primarily domain/application validation, with adapter transaction checks as defense in depth where practical.

---

# 16. Migration lineage

R2 establishes a **fresh greenfield migration root**.

Rules:

- no current migration depends on a legacy migration revision;
- no current migration alters a `legacy/v0_1/` table or assumes legacy schema existence;
- current migration metadata imports only current greenfield persistence models/definitions;
- migration tests prove a new empty development database can be created from current lineage alone;
- legacy data migration is explicitly out of scope for R2.

The implementation Spec may choose Alembic if it remains the smallest suitable migration tool, but that choice is not architectural authority.

---

# 17. ORM and driver choice

The persistence design intentionally does not require SQLAlchemy, psycopg, asyncpg, SQLModel, or another specific library.

The R2 Spec should choose the smallest well-supported stack that satisfies:

- async/sync model appropriate to the application execution style;
- explicit transaction control;
- compare-and-set/concurrency behavior;
- migration support;
- testability;
- clear separation between ORM/database types and inward-owned contracts.

Legacy SQLAlchemy/Alembic mechanics may be mined as donor implementation knowledge after the Spec makes this choice; their old schema/model taxonomy must not be transplanted.

---

# 18. Adapter failure translation

Database-native failures are translated into application-facing semantics.

Examples:

- uniqueness collision on operation receipt → idempotency replay/conflict evaluation;
- expected-version update affecting zero rows → concurrency conflict;
- foreign-key/relationship integrity violation → semantic persistence/invariant error;
- transient database outage → persistence unavailable/retryable technical failure;
- irrecoverable schema/configuration problem → explicit startup/operation failure.

Raw database exceptions must not become the public application contract.

---

# 19. Recovery behavior

After ordinary process termination/restart:

- current Decisions remain loadable;
- lifecycle facts remain complete and ordered;
- successful command receipts remain available for idempotent replay;
- no in-memory worker/session state is needed to reconstruct Decision truth;
- partial uncommitted transactions are not visible as successful business changes.

R2 does not require a generic replay engine.

---

# 20. Read/query indexing expectations

The initial adapter should support efficient bounded reads for:

- Decision by ID;
- lifecycle history by Decision ID + sequence;
- idempotency receipt by operation ID;
- unresolved Decisions by bounded Subject/Scope/Portfolio-oriented search dimensions actually required by the application;
- causal predecessor/successor relationships;
- recorded-time cutoffs for historical queries.

Do not add speculative indexing for future analytics/reporting workloads not in R2.

---

# 21. Adapter contract tests

The same semantic contract used by deterministic application fakes should be exercised against the PostgreSQL adapter where practical.

Required tests include:

## Atomicity

- single-Decision mutation updates current state + fact + receipt together;
- injected failure before commit leaves none of them committed;
- Supersession is all-or-nothing across both Decisions.

## Idempotency

- retry after successful commit returns prior result;
- same operation/different request conflicts;
- restart does not lose receipt.

## Concurrency

- two commands with same expected version cannot both succeed;
- loser leaves no lifecycle fact or false receipt;
- resulting history remains contiguous.

## History

- lifecycle facts cannot be updated/deleted through ordinary store API;
- sequence order is deterministic;
- current projection matches reconstructed latest state;
- as-known-at cutoff excludes later-recorded facts.

## Relationships

- renewal preserves predecessor + successor;
- Supersession relationship is durable and queryable;
- invalid self-reference is rejected.

## Fresh lineage

- empty database migrates from greenfield root to head;
- migration metadata contains no legacy tables/modules;
- current tests run without legacy schema.

---

# 22. Requirements traceability

| Requirement | Persistence consequence |
|---|---|
| `GF-003`, `GF-004` | Fresh current schema/migration lineage; no legacy runtime dependency. |
| `GF-005` | Row/table identity does not define Investment Decision identity. |
| `DEC-001` | Durable explicit Decision identity. |
| `DEC-006`, `DEC-008`–`DEC-012` | Append-only lifecycle facts preserve Deferral, terminal states, renewal, Supersession, history. |
| `MEM-*` | Direct owner facts + immutable history, not workflow/event replay. |
| `REL-*` | Durable retry, atomicity, restart recovery, concurrency behavior. |
| `TMP-*` | Effective + recorded time and as-known-at cutoff. |
| `AS-001`–`AS-005` | Database contract tests support objective lifecycle evidence. |
| `AS-022` | Migration/schema tests prove legacy isolation. |

---

# 23. Out of scope

R2 persistence does not implement:

- full Evidence store;
- Recommendation/View store;
- Portfolio/Risk store;
- Governance/Human Investment Decision store;
- Action Intent or execution reconciliation store;
- Outcome/Evaluation/Lesson store;
- universal outbox/event bus;
- generic persistence registry;
- data warehouse/analytics schema;
- vector/graph storage;
- legacy data conversion.

---

# 24. Spec-readiness gate

This design is Spec-ready only when review confirms:

1. the logical record set is sufficient for Decision current state, history, relationships, idempotency, and temporal reconstruction;
2. one-owner R2 transactions do not prematurely require a platform Unit of Work;
3. Supersession atomicity is fully represented;
4. PostgreSQL-specific mechanisms remain adapter-internal;
5. fresh migration lineage is explicit;
6. application Specs can be written without inventing persistence guarantees or retry/concurrency behavior.
