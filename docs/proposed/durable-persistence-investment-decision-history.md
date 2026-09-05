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
4. current lifecycle/work/operative interpretation is efficiently readable;
5. retries do not duplicate business facts;
6. stale concurrent mutations cannot overwrite newer truth;
7. distinct concurrent initiation operations cannot silently bypass continuity arbitration;
8. the durable record explains why a new Decision was considered distinct when unresolved candidates existed;
9. renewal and many-to-many Supersession relationships are durable without rewriting predecessor lifecycle disposition;
10. `as-known-at` and `effective-at-under-knowledge-cutoff` remain distinct;
11. late correction does not delete prior recorded facts;
12. contested lifecycle or operative interpretation remains representable;
13. Actor Attribution remains distinct from trigger/technical provenance;
14. persistence-native types do not leak inward;
15. greenfield schema/migrations remain independent of `legacy/`.

---

# 2. Inward-owned ports

## Decisions command store

Must support loading current state/version; prior command result; atomic lifecycle mutation/correction; new Decision establishment after continuity revalidation; one/multiple typed relationships; projection update; receipt persistence; and explicit uniqueness/continuity/version/relationship/correction failure.

No SQL/PostgreSQL/session/ORM/table/vendor exception leaks inward.

## Decision Memory reader

Must support current view; immutable history/corrections; `as_known_at`; `effective_at(T, known_at=K)`; determinate vs contested lifecycle/operative interpretation; renewal/Supersession lineage; conservative unresolved operative candidates; initiation continuity basis; and observation guard for atomic revalidation.

Optimized projections are never sole historical authority.

---

# 3. No platform-wide Unit of Work yet

R2 owner facts live within Decisions, so a purpose-specific atomic command-store contract is enough. A broader UoW is earned later when independently owned stores must commit together, e.g. Governance Human Investment Decision + Decisions consequence.

---

# 4. Logical durable record set

## 4.1 Decision Need

Preserve Need ID, statement, effective establishment time, recorded time, Actor Attribution where material, trigger/origin provenance separately, and immutable creation metadata. Later Need correction is append-only lifecycle history.

## 4.2 Investment Decision current projection

Preserve Decision/Need IDs, current Subject, current Scope (`confirmed_portfolio_refs` + completeness), supported lifecycle interpretation summary (determinate or contested), work posture when applicable, supported operative-applicability summary (operative/non-operative/contested), current version, creation time, and projection/correction marker sufficient to rebuild/verify drift.

Supersession is not a replacement lifecycle status.

## 4.3 Lifecycle fact

Append-only record preserving fact ID, Decision ID, recorded sequence/version, fact kind, effective time, recorded time, operation ID, Actor Attribution where applicable, trigger/technical provenance separately, typed business basis/reference, fact-specific payload, and correction target/reference where applicable.

### `DecisionInitiated` continuity provenance

The initiation fact (or an inseparable typed initiation record referenced by it) preserves:

- continuity determination kind (`NO_CANDIDATES`, `EXPLICIT_CREATE_NEW`, or equivalent);
- candidate Decision IDs materially considered when non-empty;
- attributable actor/basis/rationale for explicit create-new determination;
- candidate knowledge cutoff / continuity observation-guard reference;
- any lineage relationship basis established in the same initiation.

This makes Decision identity explainable without creating a generic thread entity.

## 4.4 Decision relationship

Many-to-many-capable record preserving relationship ID, source/target Decision IDs, type, effective/recorded time, operation ID, Actor Attribution/provenance where material, typed basis/scope, future context target knowledge/version boundary, and correction/support reference when applicable.

No one-to-one Supersession uniqueness by default.

## 4.5 Command receipt

Preserves operation ID, command kind, semantic request fingerprint/equivalent, affected Decision IDs, committed result/version(s), stable replay result, committed time.

## 4.6 Continuity arbitration state

Persistence must atomically detect whether the unresolved operative candidate basis observed before `CREATE_NEW` changed before commit.

Physical mechanisms may include serializable predicate protection, global/scoped initiation lock, continuity-generation token, keyed/advisory lock + re-query, or equivalent.

Inward contract:

```text
candidate basis + explicit continuity determination observed
        ↓
CREATE_NEW chosen
        ↓
commit only if candidate basis remains compatible
```

Changed basis -> `ContinuityConflict`, not a second silent Decision.

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
durable continuity determination/candidate basis
+ atomic candidate-basis revalidation
+ Decision Need
+ Investment Decision projection
+ DecisionInitiated fact
+ optional lineage relationships
+ receipt
```

Relationship command:

```text
all relationship facts
+ affected operative projections/guards
+ receipt
```

No partial semantic success.

---

# 6. Scope persistence

Must distinguish:

```text
[] + UNRESOLVED
[some confirmed] + UNRESOLVED
[confirmed set] + ESTABLISHED
```

No null/sentinel Portfolio identity overload. Scope establishment/revision remains immutable history even if denormalized currently.

---

# 7. Lifecycle/work/operative persistence

Current projection represents:

```text
lifecycle interpretation:
  determinate(UNRESOLVED | SUBSTANTIVELY_RESOLVED | EXTERNALLY_RESOLVED | NEED_RETRACTED_UNSUPPORTED)
  or contested

work posture, only when unresolved + determinate operative:
  ACTIVE | DEFERRED | WITHDRAWN

operative applicability:
  OPERATIVE | NON_OPERATIVE | CONTESTED
```

Deferral stores trusted Human Investment Decision basis reference, not Governance payload. Re-Deferral appends another lifecycle fact. Withdrawal is not judgment. Need retraction preserves original history.

A supportably superseded unresolved Decision projects `NON_OPERATIVE`; contested Supersession support may project `CONTESTED`, and normal work fails closed.

---

# 8. Relationship persistence

`RENEWED_FROM` and `SUPERSEDES` use many-to-many-capable storage.

- resolved target may be superseded;
- unresolved target becomes non-operative without lifecycle mutation;
- one source may supersede multiple targets;
- multiple sources may supersede one target where supported;
- no one-to-one unique constraint;
- supported lineage acyclic;
- cycle validation fails closed when relevant edge support is contested;
- relationship correction append-only.

R2 does not yet create `PRIOR_DECISION_CONTEXT`, but storage/port shape must permit later target historical knowledge boundary.

---

# 9. Version / compare-and-set

Initiation sets version 1. Each committed Decisions mutation increments version once. Stale expected version commits nothing. Relationship commands touching several Decisions use sufficient guards. Continuity conflict is distinct from expected-version conflict.

---

# 10. Idempotency

1. no receipt -> command may attempt;
2. same operation/same semantic request -> replay prior result;
3. same operation/different request -> idempotency conflict.

Crash after commit/before response is recoverable. Idempotency does not solve different-operation duplicate initiation.

---

# 11. Temporal reconstruction and correction

Every lifecycle/relationship fact/correction carries effective and recorded time; recorded sequence is canonical commit ordering.

`as_known_at(K)` uses only records committed by K and corrections known by K.

`effective_at(T, known_at=K)` uses only knowledge known by K, then applies effective times/corrections at T. Default K=now gives current best supported effective history.

Late correction is append-only and may alter supported projection/effective interpretation without deleting original facts.

External Resolution or unsupported-Need correction discovered after a previously recorded substantive/other disposition is persisted as correction history, not rejected as an impossible ordinary transition.

Competing corrections do not use newest-wins. If typed support cannot establish one interpretation, projection/query is contested with basis references.

---

# 12. Actor Attribution vs provenance

Do not collapse domain Actor Attribution, trigger/source provenance, and technical request/work/model/provider provenance into one generic origin field.

---

# 13. Initial PostgreSQL adapter

May use UUIDs, FKs, checks, unique `(decision_id, recorded_sequence)`, receipt uniqueness, conditional updates/row locks, serializable transactions/predicate protection, advisory/global initiation lock for R2, JSONB for purpose-named non-query-critical payload, recursive CTEs for bounded lineage/cycle checks, and transactional migrations.

These are adapter details.

---

# 14. Expected schema family

```text
decision_needs
investment_decisions
investment_decision_lifecycle_facts
investment_decision_relationships
investment_decision_command_receipts
<optional narrow continuity guard>
```

No R2 workflow/job/agent/report/RAG/Recommendation/Governance/Action Intent/Outcome/Lesson/generic-event tables.

---

# 15. Constraint strategy

Use DB constraints where practical for unique IDs/receipts/recorded sequence, FKs, non-null effective/recorded time, Scope representation, work values, relationship self-reference/type, correction references, and absence of one-to-one Supersession restriction.

History-dependent semantics remain domain/application validated with transactional defense in depth.

---

# 16. Fresh migration lineage

Fresh greenfield root; no legacy revision/table dependency; current migration metadata imports only current greenfield models; empty DB migrates root -> head; legacy data conversion outside R2.

Alembic/ORM/driver choice remains Spec-owned unless it alters inward semantics.

---

# 17. Failure translation

Translate receipt uniqueness -> idempotency evaluation; expected-version miss -> concurrency conflict; initiation serialization/guard failure -> continuity conflict; cycle/support ambiguity -> relationship/operative conflict; FK/correction integrity -> invariant error; transient outage -> retryable persistence unavailable; schema/config defect -> explicit startup/operation failure.

Raw DB exceptions never become application API.

---

# 18. Recovery and reads

After restart, Decision/Need/Scope load; unresolved Scope remains explicit; facts/corrections remain ordered; receipts replay; determinate/contested lifecycle and operative projections rebuild; continuity semantics do not depend on in-memory locks; lineage remains queryable; initiation continuity basis remains reconstructable; no replay engine required.

Support efficient bounded reads for Decision/Need, lifecycle history, operation receipt, unresolved operative candidates, continuity basis, renewal/Supersession adjacency/ancestry, recorded cutoff, effective-time lookup, and correction/support references.

---

# 19. Adapter contract tests

## Atomicity

- lifecycle fact/correction + projection + receipt together;
- initiation continuity basis + revalidation + Need + Decision + fact + receipt together;
- many-target Supersession all-or-nothing;
- injected failure leaves no partial semantic success.

## Scope

- no Scope established;
- partial Scope;
- established Scope;
- revisions reconstruct historically.

## Continuity

- no-candidate creation persists `NO_CANDIDATES` basis;
- explicit create with candidates persists candidate IDs + attributable rationale;
- replay/restart preserves continuity explanation;
- different operation IDs racing cannot silently duplicate one coherent choice.

## Work/operative

- re-Deferral appends fact;
- supportably superseded Decision is non-operative;
- contested Supersession support yields contested operative status and normal work cannot pass through persistence as ordinary success.

## Temporal/correction

- later-recorded earlier-effective fact excluded from earlier `as_known_at`;
- current effective query applies supported correction;
- original fact remains queryable;
- External/unsupported correction may qualify earlier recorded resolution;
- competing corrections -> contested, not newest-wins.

## Relationships

- resolved Decision can be superseded without lifecycle mutation;
- many-to-many Supersession persists;
- direct/indirect mixed lineage cycles blocked;
- ambiguous cycle support fails closed.

## Technology insulation

Same port contract is testable without PostgreSQL-native types inward.

---

# 20. Spec-readiness rule

Specs may choose driver/ORM/migration library, exact tables/indexes, lock/isolation strategy, and reconstruction implementation.

Specs may not weaken atomicity, durable continuity explanation/revalidation, many-to-many relationship semantics, append-only correction, contested lifecycle/operative interpretation, dual temporal queries, or actor/provenance separation.
