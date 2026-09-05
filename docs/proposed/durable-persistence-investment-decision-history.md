# Durable Persistence for Investment Decision History

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `durable-persistence`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define R2 persistence semantics and the initial PostgreSQL adapter precisely enough that Specs can choose concrete libraries/schema details without redefining lifecycle truth, continuity, temporal correction, idempotency, concurrency, or graph relationships.

## Authority

This design refines:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md);
- [`investment-decisions-lifecycle-model.md`](investment-decisions-lifecycle-model.md);
- [`investment-decisions-decision-relationship-model.md`](investment-decisions-decision-relationship-model.md);
- [`application-use-cases-investment-decision-lifecycle.md`](application-use-cases-investment-decision-lifecycle.md);
- [`investment-decisions-r2-decision-kernel-component-boundaries.md`](investment-decisions-r2-decision-kernel-component-boundaries.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md);
- accepted ADR 0002 and ADR 0003 under [`../adr/`](../adr/).

PostgreSQL is the initial/reference adapter, not the persistence architecture.

---

# 1. Persistence objective

R2 persistence must make these statements true independently of workflow/job/runtime replay:

1. Decision Need and Investment Decision survive restart;
2. Decision Scope may remain explicitly unresolved and later be established historically;
3. lifecycle facts and corrections are immutable/reconstructable;
4. current supported resolution/work state is efficiently readable;
5. retries do not duplicate business facts;
6. stale concurrent mutations cannot overwrite newer state;
7. distinct concurrent initiation operations cannot silently bypass continuity arbitration;
8. renewal and many-to-many Supersession relationships are durable/queryable without rewriting predecessor resolution;
9. as-known-at and effective-as-understood historical queries remain distinct;
10. late lifecycle correction does not delete prior recorded facts;
11. Actor Attribution remains distinguishable from trigger/technical provenance;
12. persistence-native types do not leak inward;
13. greenfield schema/migrations remain independent of `legacy/`.

---

# 2. Inward-owned persistence contracts

## 2.1 Decision command store

The application needs a semantic write capability that can:

- load current Decision state/version;
- inspect prior command result by operation identity;
- atomically commit one-Decision lifecycle change;
- atomically establish a new Decision after continuity revalidation;
- atomically establish one or multiple typed Decision relationships;
- atomically combine successor initiation with Supersession relationships when requested;
- persist immutable lifecycle facts/corrections;
- persist/update current-state projection;
- persist command idempotency receipt/result;
- fail explicitly on uniqueness, continuity, or version conflict.

The port must not expose SQL, PostgreSQL connections/sessions, ORM rows, database transaction handles, table names, or vendor exceptions.

## 2.2 Decision memory reader

The application needs a semantic read capability that can:

- return current Decision state inputs;
- return ordered lifecycle facts and relationship facts;
- reconstruct as-known-at state;
- reconstruct effective-at state under a stated knowledge cutoff;
- retrieve renewal/Supersession lineage;
- return conservative unresolved candidate Decisions plus a continuity observation guard suitable for atomic revalidation.

Optimized projections may exist internally but cannot be sole historical authority.

---

# 3. No platform-wide Unit of Work yet

R2 still does not require a generic platform Unit of Work.

The Decisions command store may expose purpose-specific atomic commit operations because R2 owner facts are within the Decisions boundary.

A broader Unit of Work should be introduced only when a later use case must coordinate independently owned stores, such as Governance-owned Human Investment Decision plus Decisions-owned resolution/Deferral consequence.

---

# 4. Logical durable record set

Exact tables/classes are adapter details. Semantically R2 needs:

## 4.1 Decision Need record

Preserves at least:

- Decision Need ID;
- need statement;
- effective raised/recognized time;
- recorded time;
- current supported Need status (`established` vs explicitly retracted/qualified as unsupported);
- Actor Attribution for Need determination where material;
- trigger/origin provenance separately;
- immutable creation metadata.

Retraction does not delete the original record/history.

## 4.2 Investment Decision current record

Efficient current projection/concurrency root preserving at least:

- Investment Decision ID;
- Decision Need ID;
- current Subject;
- current Scope representation including explicit unresolved Scope;
- supported current resolution disposition;
- supported current work disposition when unresolved;
- current domain version;
- creation time;
- latest supported correction/application markers needed for deterministic reads.

Supersession is **not** stored as a replacement current lifecycle state. Current read models may derive whether the Decision is presently operative from relationship facts/projections.

## 4.3 Investment Decision lifecycle fact record

Append-only typed history preserving at least:

- fact ID;
- Decision ID;
- monotonic recorded sequence/version;
- fact kind;
- effective/occurred time;
- recorded/committed time;
- operation ID;
- Actor Attribution where applicable;
- trigger/technical provenance reference where material;
- typed business basis/reference;
- fact-specific payload;
- correction target/reference where fact is a lifecycle correction.

Stable/query-critical dimensions must not be hidden solely in opaque generic metadata.

## 4.4 Decision relationship record

R2 now requires an explicit many-to-many capable relationship representation rather than fixed single predecessor columns as the canonical physical assumption.

Preserves at least:

- relationship ID;
- source Decision ID;
- target Decision ID;
- relationship type (`RENEWED_FROM`, `SUPERSEDES`; later `PRIOR_DECISION_CONTEXT`);
- effective time;
- recorded time;
- operation ID;
- typed basis/scope;
- Actor Attribution/provenance where material;
- relationship correction/reference state when needed;
- future-compatible target knowledge cutoff for context edges.

Inverse navigation is derived; reverse duplicate facts are unnecessary unless the physical adapter independently needs them.

## 4.5 Command idempotency receipt

Preserves:

- operation ID;
- command kind;
- canonical semantic request fingerprint/equivalent comparison data;
- affected Decision IDs;
- committed result/version(s);
- stable semantic replay result;
- committed time.

Receipt is application durability metadata, not Decision identity.

## 4.6 Continuity arbitration state

R2 persistence must provide a technology-neutral way to detect that the bounded unresolved candidate basis used to decide `CREATE_NEW` changed before initiation committed.

This may be represented physically through:

- serializable predicate protection;
- a bounded continuity-generation row/token;
- keyed/advisory locking plus re-query;
- another mechanism satisfying the same contract.

The inward semantic contract is:

```text
candidate basis observed
        ↓
CREATE_NEW determination
        ↓
commit succeeds only if relevant continuity basis remains compatible
```

A stale/changed candidate basis yields `ContinuityConflict`, not a second silently created Decision.

---

# 5. Atomic consistency

A successful ordinary lifecycle mutation commits atomically:

```text
immutable lifecycle fact
+ current Decision projection/version
+ command receipt
```

A successful relationship operation commits atomically:

```text
relationship fact(s)
+ any affected operative/current projections
+ expected-version checks where required
+ command receipt
```

A successful new initiation commits atomically:

```text
continuity revalidation
+ Decision Need
+ Investment Decision current record
+ DecisionInitiated fact
+ any initiation relationship facts
+ command receipt
```

No partial semantic success is visible.

---

# 6. Version / compare-and-set

Expected-version semantics are enforced durably.

On a normal Decision mutation:

- exactly one new recorded Decision version is committed;
- current version increments once;
- lifecycle fact uses that recorded sequence/version.

On conflict:

- no fact/relationship/current projection from stale command remains;
- no receipt claims success;
- adapter translates to technology-neutral concurrency conflict.

Relationship commands touching multiple Decisions may require multiple expected versions or equivalent semantic conflict detection.

---

# 7. Idempotency

Idempotency survives restart.

Atomic distinctions:

1. no receipt -> command may attempt;
2. same operation/same semantic request -> return recorded result;
3. same operation/different semantic request -> idempotency conflict.

Crash after commit but before response is recoverable by replaying same operation ID.

Idempotency does not replace continuity arbitration for different operation IDs.

---

# 8. Scope persistence

Decision Scope may be unresolved at initiation.

The physical schema must therefore represent at least three meanings distinctly where applicable:

```text
unresolved / not yet established
established value
later revised established value
```

Do not collapse unresolved Scope into empty/default Portfolio identifiers.

`DecisionScopeEstablished` and later revisions remain immutable lifecycle history even if current Scope is denormalized on the current Decision row.

---

# 9. Deferral, withdrawal, and resolution persistence

The current projection must distinguish:

- unresolved + active;
- unresolved + deferred;
- unresolved + withdrawn;
- substantively resolved;
- externally resolved;
- Decision Need retracted/unsupported.

Deferral fact includes trusted human-decision basis reference but does not persist Governance-owned Human Investment Decision payload in the Decisions store.

Withdrawal fact does not imply Deferral/resolution.

Need retraction preserves original Need and correction basis.

---

# 10. Supersession persistence

Supersession is represented in `investment_decision_relationships` or equivalent many-to-many relation.

Rules:

- predecessor historical resolution/work facts are unchanged;
- resolved predecessor can be superseded;
- unresolved predecessor can be superseded and becomes non-operative while relationship remains supported;
- one source may supersede multiple targets;
- one target may have multiple supported superseding sources when domain basis permits;
- no one-to-one unique constraint may be added unless later authority changes this design;
- graph cycle prevention applies across supported renewal/Supersession lineage.

An initiation+Supersession command may atomically create successor and several relationship rows.

A later-recorded Supersession between existing Decisions is also supported.

---

# 11. Renewal persistence

`RENEWED_FROM` is a typed relationship row/reference from new Decision to one or more substantively/external-resolved causal predecessors when independently supportable.

Predecessor current/history rows are not reopened.

Self-reference and lineage cycles are rejected.

---

# 12. Temporal persistence and correction

Every lifecycle/relationship fact preserves effective and recorded time.

Recorded sequence/version is canonical ordering of committed knowledge. Timestamps are not the sole ordering primitive.

## 12.1 As-known-at

For knowledge cutoff `K`:

- exclude facts/relationships/corrections recorded after `K`;
- reconstruct from remaining recorded sequence and correction relationships;
- late facts with earlier effective times remain invisible before their recorded time.

## 12.2 Effective-at under knowledge cutoff

For effective time `T` and knowledge cutoff `K`:

- use only facts recorded by `K`;
- apply their effective times and supported corrections;
- return the lifecycle state supported as effective at `T` under that knowledge boundary.

Default `K=now` produces current best supported effective history.

## 12.3 Lifecycle correction

A correction is append-only and references the earlier fact/interpretation it qualifies.

It may alter the **supported current/effective projection** without deleting the earlier fact.

Database invariants should ensure a correction references valid Decision/fact identities and cannot silently produce two unqualified competing current interpretations.

Example:

- `DecisionResolved` recorded at 10:05;
- at 10:10 a fact proves External Resolution effective 10:00;
- append correction establishing External Resolution as supported effective disposition from 10:00;
- keep `DecisionResolved` and Human Investment Decision historical facts;
- as-known-at 10:06 remains what Polaris knew then.

---

# 13. Actor Attribution vs provenance

Persistence must not force actor and trigger into one generic `created_by` field.

Where material, preserve separate semantics for:

- domain Actor Attribution/reference;
- trigger/source reference;
- technical request/work/model/provider provenance.

A model/provider/workflow identifier cannot satisfy the Actor Attribution field merely because it participated technically.

---

# 14. PostgreSQL initial adapter

PostgreSQL is the initial/reference adapter because its transaction, relational integrity, uniqueness, indexing, and concurrency capabilities fit R2 well.

Adapter may use:

- UUID identity columns;
- foreign keys;
- typed/check constrained enums/values;
- unique constraints for operation ID and `(decision_id, recorded_sequence)`;
- conditional updates/row locks;
- serializable transactions/predicate protection where appropriate for continuity arbitration;
- JSONB for purpose-named structured payloads that are not stable query dimensions;
- recursive CTEs for bounded lineage/cycle checks if useful;
- transactional migrations.

These remain adapter details.

---

# 15. Expected logical schema

Roughly:

```text
decision_needs
investment_decisions
investment_decision_lifecycle_facts
investment_decision_relationships
investment_decision_command_receipts
<optional narrow continuity guard structure if chosen>
```

Do not add R2 tables for workflows/jobs, agents/models, reports, RAG, Recommendation, Governance, Action Intent, Outcome/Lesson, generic event sourcing, or global persistence taxonomy.

---

# 16. Constraint strategy

Good mechanical constraints include:

- unique Decision/Need/fact/relationship IDs;
- unique operation receipts;
- unique recorded sequence per Decision;
- foreign-key integrity;
- non-null required effective/recorded time;
- valid resolution/work value combinations;
- explicit unresolved Scope representation;
- no relationship self-reference;
- relationship type constraints;
- correction references valid original fact/relationship;
- no one-to-one Supersession uniqueness restriction.

History-dependent semantics remain domain/application validation with transactional defense in depth.

---

# 17. Fresh migration lineage

Rules:

- fresh greenfield root;
- no dependency on legacy revisions/tables;
- current migration metadata imports only current greenfield persistence definitions;
- empty database can migrate current root -> head;
- legacy data conversion out of R2 scope.

The Spec may choose Alembic if it is the smallest suitable tool.

---

# 18. ORM / driver choice

No ORM/driver is mandated by design.

Spec should choose smallest maintained stack satisfying:

- explicit transaction control;
- compare-and-set and continuity arbitration;
- migration support;
- async/sync needs of selected execution style;
- testability;
- clean inward contract separation.

Legacy SQLAlchemy/Alembic mechanics may be mined after the Spec selects the stack; legacy schema taxonomy must not be transplanted.

---

# 19. Failure translation

Database-native failures translate to semantic outcomes, including:

- operation uniqueness collision -> idempotency replay/conflict evaluation;
- expected-version miss -> concurrency conflict;
- continuity serialization/guard conflict -> continuity conflict/retry/re-evaluation;
- relationship/cycle integrity failure -> relationship semantic error;
- FK/correction integrity failure -> persistence/invariant error;
- transient database outage -> retryable persistence unavailable;
- schema/configuration defect -> explicit startup/operation failure.

Raw database exceptions are not application API.

---

# 20. Recovery behavior

After restart:

- current Decisions/Needs load;
- unresolved Scope remains unresolved rather than defaulted;
- lifecycle/relationship facts remain complete/ordered;
- receipts replay committed results;
- current supported projections can be reconstructed/verified from immutable facts/corrections;
- continuity semantics do not depend on in-memory locks alone;
- no generic replay engine is required.

---

# 21. Read/index expectations

Support efficient bounded reads for:

- Decision by ID;
- Need by ID;
- lifecycle history by Decision + recorded sequence;
- operation receipt by ID;
- unresolved candidate lookup by conservative continuity dimensions actually used;
- renewal/Supersession adjacency and bounded ancestry;
- recorded-time cutoff;
- effective-time lookup under knowledge cutoff;
- correction references.

Do not add speculative analytics/reporting indexes.

---

# 22. Adapter contract tests

## Atomicity

- single mutation current+fact+receipt together;
- initiation continuity revalidation + Need + Decision + fact + receipt together;
- many-target Supersession all-or-nothing;
- injected failures leave no partial semantic success.

## Idempotency

- replay returns prior result;
- same operation/different request conflicts;
- restart preserves receipt.

## Concurrency / continuity

- two stale mutations cannot both succeed;
- loser leaves no false history/receipt;
- two distinct initiations against overlapping continuity basis cannot silently both create new Decisions;
- continuity conflict forces re-query/re-evaluation.

## Scope

- unresolved Scope persists distinctly;
- later establishment/revision is historical.

## Dispositions

- Deferral/withdrawal/resolution/external resolution/Need retraction remain distinct in current/history records.

## Relationships

- renewal durable/queryable;
- resolved target can be superseded without resolution rewrite;
- one-to-many and many-to-one Supersession supported;
- self/cycles rejected;
- late relationships respect as-known-at cutoff.

## Temporal correction

- corrected fact cannot be mutated/deleted;
- as-known-at before correction remains stable;
- effective-at current knowledge reflects supported late correction;
- current projection agrees with currently supported corrected history.

## Fresh lineage

- empty DB migrates root -> head;
- no legacy metadata/schema dependency.

---

# 23. Requirements traceability

| Requirement | Persistence consequence |
|---|---|
| `GF-003`–`GF-005` | fresh schema; Decision identity independent of rows/runtime. |
| `DEC-001`–`DEC-004` | durable explicit identity + identity-safe history. |
| `DEC-013` | unresolved Scope persists explicitly. |
| `DEC-014`–`DEC-016` | withdrawal/retraction/Supersession distinctions preserved. |
| `DEC-017` | continuity arbitration survives concurrent distinct operations. |
| `DEC-018` | effective/recorded time + corrections + dual temporal queries. |
| `DEC-019` | actor and trigger/provenance storage remain distinct. |
| `MEM-005`, `MEM-009` | non-destructive direct business truth. |
| `MEM-011` | future relationship schema supports target knowledge cutoff. |
| `REL-*` | durable retry/atomicity/concurrency/recovery. |

---

# 24. Out of scope

- full Evidence/Recommendation/Portfolio/Governance/Continuity/Learning stores;
- generic outbox/event bus;
- generic persistence registry/UoW;
- warehouse/vector/graph database;
- prior-Decision context binding implementation;
- legacy data conversion.

---

# 25. Spec-readiness gate

Persistence design is Spec-ready only when:

1. unresolved Scope is representable;
2. disposition/work/Supersession separation survives physical schema choices;
3. continuity arbitration is stronger than operation idempotency;
4. relationship representation is many-to-many capable and cycle-safe;
5. correction is append-only and dual temporal queries are deterministic;
6. actor/provenance fields cannot be collapsed semantically;
7. PostgreSQL-specific mechanisms remain adapter-internal;
8. fresh migration lineage is explicit;
9. no persistence Spec must invent these guarantees.
