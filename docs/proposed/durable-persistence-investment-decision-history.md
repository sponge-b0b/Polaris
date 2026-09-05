# Durable Persistence for Investment Decision History

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `durable-persistence`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define R2 persistence semantics and the initial PostgreSQL adapter precisely enough that Specs can choose concrete libraries/schema details without redefining lifecycle truth, continuity, temporal correction, idempotency, concurrency, or Decision relationship semantics.

## Authority

This design refines:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md);
- [`investment-decisions-lifecycle-model.md`](investment-decisions-lifecycle-model.md);
- [`investment-decisions-decision-relationship-model.md`](investment-decisions-decision-relationship-model.md);
- [`application-use-cases-investment-decision-lifecycle.md`](application-use-cases-investment-decision-lifecycle.md);
- [`investment-decisions-r2-decision-kernel-component-boundaries.md`](investment-decisions-r2-decision-kernel-component-boundaries.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- proposed [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md);
- accepted ADR 0002 and ADR 0003.

PostgreSQL is the initial/reference adapter, not the persistence architecture.

---

# 1. Persistence objective

R2 persistence must make these statements true independently of workflow/job/runtime replay:

1. Decision Need and Investment Decision survive restart;
2. Scope may remain explicitly unresolved/partial and later be established historically;
3. lifecycle facts and corrections are immutable/reconstructable;
4. current supported lifecycle interpretation/work posture is efficiently readable;
5. retries do not duplicate business facts;
6. stale concurrent mutations cannot overwrite newer truth;
7. distinct concurrent initiation operations cannot silently bypass continuity arbitration;
8. renewal and many-to-many Supersession relationships are durable/queryable without rewriting predecessor lifecycle disposition;
9. `as-known-at` and `effective-at-under-knowledge-cutoff` remain distinct;
10. late correction does not delete prior recorded facts;
11. contested lifecycle interpretation remains representable;
12. Actor Attribution remains distinct from trigger/technical provenance;
13. persistence-native types do not leak inward;
14. greenfield schema/migrations remain independent of `legacy/`.

---

# 2. Inward-owned ports

## 2.1 Decisions command store

Semantic write capability must support:

- load current Decision state/version;
- inspect prior command result by operation ID;
- atomically commit one-Decision lifecycle mutation/correction;
- atomically establish new Decision after continuity revalidation;
- atomically establish one/multiple typed relationships;
- persist/update current convenience projection;
- persist command receipt/result;
- fail explicitly on uniqueness, continuity, version, relationship, or correction conflict.

No SQL/PostgreSQL/session/ORM/table/vendor exception leaks inward.

## 2.2 Decision Memory reader

Semantic read capability must support:

- current Decision/Need/Scope/work/lifecycle view;
- immutable history + corrections;
- `as_known_at` reconstruction;
- `effective_at(T, known_at=K)` reconstruction;
- determinate vs contested lifecycle interpretation;
- renewal/Supersession lineage;
- conservative unresolved, operative continuity candidates + observation guard for atomic revalidation.

Optimized projections may exist but are never sole historical authority.

---

# 3. No platform-wide Unit of Work yet

R2 owner facts live in the Decisions boundary, so a purpose-specific atomic command-store contract is sufficient.

A broader application Unit of Work is earned only when a later use case must atomically coordinate independently owned stores, such as Governance Human Investment Decision + Decisions consequence.

If introduced later, it exposes Polaris transaction semantics, not DB sessions.

---

# 4. Logical durable record set

Exact physical names remain adapter details. Semantically R2 needs:

## 4.1 Decision Need

Preserves:

- Need ID;
- need statement;
- effective establishment time;
- recorded time;
- Actor Attribution where material;
- trigger/origin provenance separately;
- immutable creation metadata.

Need lifecycle correction/disposition is represented through immutable Decision lifecycle facts/corrections rather than destructive replacement.

## 4.2 Investment Decision current projection

Preserves at least:

- Decision ID;
- Need ID;
- current Subject;
- current Scope (`confirmed_portfolio_refs` + completeness);
- current supported lifecycle interpretation summary: determinate disposition or contested marker;
- work posture when applicable;
- current domain version;
- creation time;
- projection/correction marker sufficient to detect/rebuild drift.

Supersession is not a replacement status column. Operative state may be projected from supported relationship facts.

## 4.3 Lifecycle fact

Append-only record preserving:

- fact ID;
- Decision ID;
- monotonic recorded sequence/version;
- fact kind;
- effective time;
- recorded/committed time;
- operation ID;
- Actor Attribution where applicable;
- trigger/technical provenance separately;
- typed business basis/reference;
- fact-specific payload;
- correction target/reference when applicable.

Stable/query-critical dimensions must not live only in opaque metadata.

## 4.4 Decision relationship

Many-to-many-capable record preserving:

- relationship ID;
- source Decision ID;
- target Decision ID;
- relationship type;
- effective time;
- recorded time;
- operation ID;
- Actor Attribution/provenance where material;
- typed basis/scope;
- context target knowledge/version boundary when applicable later;
- correction/support reference when applicable.

No one-to-one Supersession uniqueness is allowed by default.

## 4.5 Command receipt

Preserves:

- operation ID;
- command kind;
- semantic request fingerprint/equivalent comparison data;
- affected Decision IDs;
- committed result/version(s);
- stable semantic replay result;
- committed time.

Receipt is application durability metadata, not business identity.

## 4.6 Continuity arbitration state

Persistence must allow atomic detection that the bounded unresolved candidate basis observed before `CREATE_NEW` changed before commit.

Possible physical mechanisms:

- serializable transaction/predicate protection;
- global or scoped initiation lock for R2;
- continuity-generation token;
- keyed/advisory lock + re-query;
- equivalent correct mechanism.

Inward contract:

```text
candidate basis observed
        ↓
CREATE_NEW chosen
        ↓
commit only if basis still compatible
```

Changed basis -> `ContinuityConflict`, not a silent second Decision.

---

# 5. Atomic consistency

Ordinary lifecycle mutation:

```text
immutable lifecycle fact/correction
+ current projection/version
+ command receipt
```

New initiation:

```text
continuity revalidation
+ Decision Need
+ Investment Decision current projection
+ DecisionInitiated fact
+ optional lineage relationships
+ receipt
```

Relationship command:

```text
all relationship facts
+ any affected operative projections/guards
+ receipt
```

All-or-nothing semantic visibility is required.

---

# 6. Scope persistence

Scope must distinguish:

```text
[] + UNRESOLVED
[some confirmed portfolios] + UNRESOLVED
[confirmed portfolio set] + ESTABLISHED
```

Do not overload null/empty/default Portfolio ID to mean multiple semantics.

`DecisionScopeEstablished` / revision history remains immutable even if current Scope is denormalized.

---

# 7. Lifecycle/work persistence

Projection must represent:

```text
supported lifecycle interpretation:
  determinate(UNRESOLVED | SUBSTANTIVELY_RESOLVED | EXTERNALLY_RESOLVED | NEED_RETRACTED_UNSUPPORTED)
  or contested

work posture, when unresolved + operative:
  ACTIVE | DEFERRED | WITHDRAWN
```

Deferral persists trusted Human Investment Decision basis reference only; Governance payload remains outside Decisions store.

Withdrawal does not imply judgment/resolution.

Need retraction/correction preserves original Need/facts.

---

# 8. Relationship persistence

`RENEWED_FROM` and `SUPERSEDES` use many-to-many-capable relationship storage.

Rules:

- resolved target may be superseded;
- unresolved target may be superseded and become non-operative without lifecycle mutation;
- one source may supersede multiple targets;
- multiple sources may supersede one target where supported;
- no one-to-one unique constraint;
- supported lifecycle-lineage graph is acyclic;
- cycle validation fails closed when relevant edge support is contested;
- later relationship corrections are append-only.

R2 does not yet persist `PRIOR_DECISION_CONTEXT`, but schema/port shape must not prevent it and must allow a future target historical knowledge boundary.

---

# 9. Version / compare-and-set

- initiation sets version 1;
- each committed Decisions mutation increments version once;
- lifecycle fact uses resulting recorded sequence/version;
- stale expected version commits nothing;
- relationship commands touching multiple Decisions use sufficient guards;
- continuity conflict is distinct from expected-version conflict.

---

# 10. Idempotency

Persisted semantics:

1. no receipt -> command may attempt;
2. same operation/same semantic request -> replay prior result;
3. same operation/different semantic request -> idempotency conflict.

Crash after commit/before response is recoverable.

Idempotency does not solve different-operation duplicate initiation.

---

# 11. Temporal reconstruction

Every lifecycle/relationship fact/correction carries effective and recorded time; recorded sequence is canonical commit ordering.

## 11.1 `as_known_at(K)`

- use only records committed by K;
- apply correction relationships known by K;
- derive lifecycle interpretation from that knowledge set;
- exclude later-recorded facts even if effective time is earlier.

## 11.2 `effective_at(T, known_at=K)`

- use only records known by K;
- apply their effective times/corrections relative to T;
- return determinate supported disposition or contested interpretation.

Default `K=now` gives current best supported effective history.

## 11.3 Correction model

Correction is append-only and references what it qualifies.

It can change the supported projection/effective interpretation without deleting original facts.

Example:

```text
DecisionSubstantivelyResolved recorded 10:05
late external basis recorded 10:10, effective 10:00
DecisionLifecycleCorrected records supported EXTERNALLY_RESOLVED effective 10:00
```

The substantive-resolution fact remains historical.

## 11.4 Competing corrections

Database/port semantics must not treat newest correction as automatically semantically dominant.

If typed support cannot deterministically establish one current interpretation, projection/query returns contested state with basis references. A new authoritative resolution of that contest is another append-only fact/correction.

---

# 12. Actor Attribution vs provenance

Do not force these into one `created_by` field.

Preserve separately where material:

- domain Actor Attribution/reference;
- trigger/source provenance;
- technical request/work/model/provider provenance.

A model/provider/workflow identifier cannot satisfy Actor Attribution merely because it contributed technically.

---

# 13. Initial PostgreSQL adapter

PostgreSQL may use:

- UUID IDs;
- foreign keys;
- check constraints/typed values;
- unique `(decision_id, recorded_sequence)`;
- operation receipt uniqueness;
- conditional updates/row locks;
- serializable transactions/predicate protection;
- advisory/global initiation lock if simplest for R2 correctness;
- JSONB for purpose-named payload not used as stable query dimension;
- recursive CTEs for bounded lineage/cycle checks;
- transactional migrations.

These are adapter details, not inward contracts.

---

# 14. Expected greenfield schema family

Roughly:

```text
decision_needs
investment_decisions
investment_decision_lifecycle_facts
investment_decision_relationships
investment_decision_command_receipts
<optional narrow continuity guard structure>
```

No R2 tables for workflow/job/agent/report/RAG/Recommendation/Governance/Action Intent/Outcome/Lesson/generic event sourcing.

---

# 15. Constraint strategy

Mechanical DB constraints should cover where practical:

- unique IDs/receipts/recorded sequence;
- FK integrity;
- non-null effective/recorded times;
- valid Scope completeness representation;
- valid work posture values;
- no self-relationship;
- recognized relationship types;
- correction references valid records;
- absence of one-to-one Supersession constraints.

History-dependent semantics remain domain/application validated with transactional defense in depth.

---

# 16. Fresh migration lineage

- fresh greenfield root;
- no legacy revision/table dependency;
- migration metadata imports only current greenfield persistence definitions;
- empty DB migrates root -> head;
- legacy data conversion outside R2.

Alembic is optional until Spec selects smallest suitable tool.

---

# 17. Failure translation

Translate adapter failures to semantic outcomes:

- receipt uniqueness -> idempotency replay/conflict evaluation;
- expected-version miss -> concurrency conflict;
- initiation serialization/guard failure -> continuity conflict/re-evaluation;
- cycle/support ambiguity -> relationship conflict/contested result;
- FK/correction integrity -> invariant/persistence error;
- transient outage -> retryable persistence unavailable;
- schema/config defect -> explicit startup/operation failure.

Raw DB exceptions are not application API.

---

# 18. Recovery

After restart:

- current Decision/Need/Scope loads;
- unresolved Scope remains explicit;
- immutable facts/corrections remain complete/ordered;
- receipts replay results;
- supported determinate/contested lifecycle interpretation rebuilds from durable truth;
- continuity correctness does not depend on in-memory locks;
- relationship lineage remains queryable;
- no generic replay engine is required.

---

# 19. Read/index expectations

Support bounded efficient reads for:

- Decision/Need by ID;
- lifecycle history by Decision + recorded sequence;
- operation receipt;
- unresolved operative candidate discovery;
- renewal/Supersession adjacency + bounded ancestry;
- recorded-time cutoff;
- effective-time lookup under knowledge cutoff;
- correction/support references.

No speculative analytics/reporting indexes.

---

# 20. Adapter contract tests

## Atomicity

- lifecycle fact/correction + projection + receipt together;
- initiation revalidation + Need + Decision + fact + receipt together;
- many-target Supersession all-or-nothing;
- injected failures leave no partial semantic success.

## Scope

- no Scope established;
- partial Scope;
- established Scope;
- revisions reconstruct historically.

## Idempotency/concurrency

- replay returns prior result;
- same operation/different request conflicts;
- restart preserves receipt;
- stale expected version commits nothing;
- different operation IDs racing on initiation cannot silently duplicate one coherent choice.

## Temporal/correction

- later-recorded earlier-effective fact excluded from earlier `as_known_at`;
- current effective query applies supported correction;
- original fact remains queryable;
- competing corrections yield contested interpretation, not newest-wins.

## Relationships

- resolved Decision can be superseded without lifecycle mutation;
- many-to-many Supersession persists;
- direct/indirect mixed lineage cycles blocked;
- ambiguous cycle support fails closed.

## Technology insulation

- same port contract testable without PostgreSQL-native types leaking inward.

---

# 21. Spec-readiness rule

Specs may choose driver/ORM/migration library, exact tables/indexes, lock/isolation strategy, and reconstruction implementation.

Specs may not weaken atomicity, continuity arbitration, many-to-many relationship semantics, append-only correction, contested interpretation, dual temporal queries, or actor/provenance separation.
