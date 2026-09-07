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
- [`investment-decisions-r2-foundation-public-contract.md`](investment-decisions-r2-foundation-public-contract.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- proposed [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md);
- accepted ADR 0002 and ADR 0003.

The owner-approved foundation public-contract document resolves the foundation blockers that existed when this persistence design was first written. Where historical wording below conflicts with that completion authority, the completed foundation contract controls.

PostgreSQL is the initial/reference adapter, not the persistence architecture.

---

# 1. Persistence objective

R2 persistence must ensure, independently of runtime replay:

1. Decision Need and Investment Decision survive restart;
2. exactly one Decision Need grounds each Decision, and one Need cannot ground multiple Decisions;
3. Scope may remain unresolved/partial and later be established historically;
4. lifecycle facts/corrections remain immutable/reconstructable;
5. current lifecycle/work/operative interpretation is efficiently readable;
6. retry, stale concurrency, and concurrent initiation cannot duplicate/rewrite truth;
7. committed Decision identity remains explainable from its durable continuity determination/candidate basis;
8. renewal and many-to-many Supersession are durable without rewriting predecessor lifecycle disposition;
9. `as_known_at` and `effective_at` remain distinct and correct;
10. late correction does not delete prior facts;
11. contested lifecycle/relationship/operative interpretation remains representable;
12. Actor Attribution remains distinct from Trigger Provenance and Technical Provenance;
13. no persistence-native types leak inward;
14. greenfield schema/migrations remain independent of `legacy/`;
15. the completed opaque UUIDv4-backed domain/application identity contracts survive persistence without conversion to semantic strings or database-generated business identity, including `PortfolioId`, `InvestmentDecisionId`, `DecisionNeedId`, `DecisionLifecycleFactId`, `DecisionRelationshipFactId`, `OperationId`, and `ActorId`.

---

# 2. Inward-owned ports

## Decisions command store

Must support loading current state/version, prior command result, atomic lifecycle mutation/correction, new Decision establishment after continuity revalidation, one/multiple typed relationship facts/corrections, projection update, receipt persistence, and explicit uniqueness/continuity/version/relationship/correction failure.

No SQL/PostgreSQL/session/ORM/table/vendor exception leaks inward.

## Decision Memory reader

Must support current view, immutable history/corrections, `as_known_at`, `effective_at(T, known_at=K)`, determinate vs contested lifecycle/operative interpretation, renewal/Supersession lineage and relationship support, conservative unresolved operative candidates, initiation continuity basis, and observation guard for atomic revalidation.

Optimized projections are never sole historical authority.

---

# 3. No platform-wide Unit of Work yet

R2 owner facts live within Decisions, so a purpose-specific atomic command-store contract is sufficient. A broader UoW is earned later when independently owned stores must commit together, e.g. Governance Human Investment Decision + Decisions consequence.

---

# 4. Logical durable record set

## 4.1 Decision Need

Preserve UUID-backed `DecisionNeedId`, non-empty statement, effective establishment time, recorded time, UUID-backed `OperationId`, Actor Attribution, required Trigger Provenance, optional Technical Provenance, and immutable creation metadata.

One Need may be referenced by **at most one** Investment Decision. The initial PostgreSQL adapter should enforce this mechanically where practical, e.g. a unique FK/reference from Investment Decision to Decision Need.

Later Need correction is append-only lifecycle history.

## 4.2 Investment Decision current projection

Preserve UUID-backed Decision/Need IDs, current `DecisionSubject`, current `DecisionScope` (canonical unordered unique `PortfolioId` membership + completeness), supported lifecycle interpretation summary (determinate or contested), work posture when applicable, supported operative-applicability summary (operative/non-operative/contested), current `DecisionVersion`, `created_at`, and projection/correction marker sufficient to rebuild/verify drift.

Supersession is not a replacement lifecycle status.

## 4.3 Lifecycle fact

Append-only record preserving `DecisionLifecycleFactId`, Decision ID, `DecisionLifecycleSequence`, Decision version associated with the committed mutation, fact kind, effective time, recorded time, UUID-backed `OperationId`, Actor Attribution where applicable, required Trigger Provenance, optional Technical Provenance, purpose-specific typed business basis/reference when required, fact-specific payload, and correction target/reference where applicable.

`DecisionLifecycleSequence` and `DecisionVersion` are separate concepts. Lifecycle initiation starts both at 1; each committed lifecycle/current-state mutation appends the immediately next lifecycle sequence and increments Decision version once. A later relationship-only mutation may increment Decision version without inventing a lifecycle fact or lifecycle-sequence entry.

### `DecisionInitiated` continuity provenance

The initiation fact (or inseparable typed initiation record referenced by it) preserves:

- continuity determination kind (`NO_CANDIDATES` or `EXPLICIT_CREATE_NEW`);
- candidate Decision IDs materially considered when non-empty;
- known Actor Attribution plus non-empty rationale for explicit create-new with candidates;
- candidate knowledge cutoff used for continuity determination and commit revalidation;
- any typed lineage relationship basis established in the same initiation.

Persistence-specific lock IDs, advisory-lock keys, row-version tokens, and equivalent mechanical guard details belong to adapter/receipt evidence rather than lifecycle provenance.

## 4.4 Decision relationship

Many-to-many-capable append-only record preserving `DecisionRelationshipFactId`, source/target Decision IDs, relationship type, effective time, recorded time, UUID-backed `OperationId`, Actor Attribution where material, required Trigger Provenance, optional Technical Provenance, and purpose-specific typed basis/reference when required.

`DecisionRelationshipFactId` is domain fact identity, not persistence row identity and not a hash/key derived from source/type/target values.

Relationship qualification/correction is append-only. A correction fact receives its own `DecisionRelationshipFactId`, explicitly references the prior relationship fact it qualifies/disconfirms, and never rewrites/deletes the original. If typed support cannot reconcile competing facts/corrections, supported relationship interpretation is contested/indeterminate rather than newest-write-wins.

No one-to-one Supersession uniqueness by default.

R2 does not create `PRIOR_DECISION_CONTEXT`. The inward relationship model must remain extensible so that a future purpose-specific context relationship can carry the exact target historical knowledge/version boundary actually used, but current `RENEWED_FROM`/`SUPERSEDES` records do not gain speculative nullable context fields merely for future possibility.

## 4.5 Command receipt

Preserves UUID-backed `OperationId`, command kind, semantic request fingerprint/equivalent, affected Decision IDs, committed result/version(s), stable replay result, committed time.

The UUID value is only the opaque operation identity. Same-operation/same-request replay semantics remain determined by the receipt/request contract, not by interpreting UUID contents.

## 4.6 Continuity arbitration state

Persistence must atomically detect whether the unresolved operative candidate basis observed before `CREATE_NEW` changed before commit.

Physical mechanisms may include serializable predicate protection, global/scoped initiation lock, continuity-generation token, keyed/advisory lock + re-query, or equivalent.

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
+ new Decision Need
+ Investment Decision referencing that Need
+ DecisionInitiated fact
+ optional lineage relationship facts
+ receipt
```

The transaction must enforce both Decision identity uniqueness and one-Need/one-Decision cardinality.

Relationship command:

```text
all relationship facts/corrections
+ affected operative projections/guards
+ Decision version updates where semantically affected
+ receipt
```

No partial semantic success.

---

# 6. Scope persistence

Must distinguish:

```text
[] + UNRESOLVED
[some confirmed PortfolioId values] + UNRESOLVED
[one-or-more confirmed PortfolioId values] + ESTABLISHED
```

Constraints:

- membership is semantically unordered and duplicate-free;
- `ESTABLISHED` with zero confirmed Portfolios is invalid;
- no null/sentinel Portfolio identity overload;
- Scope establishment/revision remains immutable history even if denormalized currently;
- `ESTABLISHED -> UNRESOLVED` is not an ordinary transition;
- semantic no-op does not append history or increment Decision version.

The canonical Portfolio identity and Scope equality/ordering contracts are resolved by the completed foundation: Scope references Portfolio & Risk-owned opaque UUIDv4-backed `PortfolioId` values and preserves set-like equality/uniqueness. Persistence may choose normalized rows, arrays, JSONB, or another adapter representation only if the inward unordered/unique semantics remain unchanged.

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

Deferral stores a purpose-specific reference to an already-valid trusted Human Investment Decision basis, not Governance payload. Analytical/advisory judgment or an unauthorized attempted authority act cannot be persisted as that canonical Human Investment Decision basis. Re-Deferral appends another fact. Withdrawal is not judgment. Need retraction preserves original history.

Supported Supersession of an unresolved Decision projects `NON_OPERATIVE`; contested Supersession support may project `CONTESTED`, and normal work fails closed.

---

# 8. Relationship persistence

`RENEWED_FROM` and `SUPERSEDES` use many-to-many-capable storage.

- every immutable base/correction record carries unique `DecisionRelationshipFactId` domain identity;
- resolved target may be superseded;
- unresolved target becomes non-operative without lifecycle mutation;
- one source may supersede multiple targets;
- multiple sources may supersede one target where supported;
- no one-to-one unique constraint;
- supported lineage acyclic;
- cycle validation fails closed when relevant edge support is contested;
- relationship correction is append-only and explicitly targets prior relationship-fact identity;
- original relationship facts remain queryable after qualification/disconfirmation;
- irreconcilable typed support is contested, not newest-wins;
- a relationship-only committed mutation may advance `DecisionVersion` without advancing `DecisionLifecycleSequence`.

R2 does not yet create `PRIOR_DECISION_CONTEXT`; future storage/port extension must be able to preserve a target historical knowledge/version boundary when that real use case is introduced, without pre-populating current relationship records with speculative context fields.

---

# 9. Version / compare-and-set and idempotency

Initiation sets `DecisionVersion` 1. Each committed mutation of concurrency-protected Decision current state increments version once. Stale expected version commits nothing. Relationship commands touching several Decisions use sufficient guards. Relationship-only mutations may increment affected Decision versions without fabricating lifecycle facts. Continuity conflict is distinct from expected-version conflict.

Idempotency:

1. no receipt -> command may attempt;
2. same operation/same semantic request -> replay prior result;
3. same operation/different semantic request -> conflict.

Crash after commit/before response is recoverable. Idempotency does not solve different-operation duplicate initiation.

---

# 10. Temporal reconstruction and correction

Every lifecycle/relationship fact/correction carries effective and recorded time. Lifecycle facts additionally carry contiguous `DecisionLifecycleSequence`; that sequence is not reused as relationship-history ordering merely to keep counters aligned.

`as_known_at(K)` is the state **effective at K using only records committed by K**. Equivalently:

```text
effective_at(T=K, known_at=K)
```

A fact recorded by K but explicitly effective after K is part of what was known, but it does not alter the lifecycle state effective at K.

`effective_at(T, known_at=K)` uses only knowledge known by K and applies effective times/corrections at T. Default K=now gives current best supported effective history.

Late correction is append-only and may alter supported projection/effective interpretation without deleting original facts. External Resolution or unsupported-Need correction discovered after a previously recorded disposition is persisted as correction history, not rejected as an impossible ordinary transition.

Competing lifecycle or relationship corrections do not use newest-wins. If typed support cannot establish one interpretation, projection/query is contested with basis references.

---

# 11. Actor Attribution vs provenance

Do not collapse Actor Attribution, Trigger Provenance, and Technical Provenance into one generic origin field.

The completed public contracts are:

- Actor Attribution uses canonical `ActorId` and truthful known/unknown/contested states; no universal persisted `ActorKind` is required;
- every new Decisions fact has one constrained semantic Trigger Provenance;
- Technical Provenance is optional, immutable, semantically unordered, and duplicate-free;
- neither attribution nor technical provenance grants investment authority;
- purpose-specific business basis/reference types remain separate from provenance.

Persistence may map these contracts to efficient storage, but it must not redefine the inward types with one generic `(kind, identifier)` representation.

---

# 12. Initial PostgreSQL adapter

For frozen UUID-backed identities, use PostgreSQL native `uuid` representation for `PortfolioId`, `InvestmentDecisionId`, `DecisionNeedId`, `DecisionLifecycleFactId`, `DecisionRelationshipFactId`, `OperationId`, and `ActorId` values where persisted. Do not convert them into semantic text identifiers or database-generated integer business identity.

The adapter may choose FKs, checks, unique `(decision_id, lifecycle_sequence)`, receipt uniqueness, conditional updates/row locks, serializable transactions/predicate protection, advisory/global initiation lock for R2, JSONB for purpose-named non-query-critical payload, recursive CTEs for bounded lineage/cycle checks, and transactional migrations where those choices do not alter inward semantics.

Physical row identity may use adapter-appropriate mechanisms, but it is separate from `DecisionLifecycleFactId` and `DecisionRelationshipFactId` and must not leak inward as domain identity.

These are adapter details.

---

# 13. Expected schema family

```text
decision_needs
investment_decisions
investment_decision_lifecycle_facts
investment_decision_relationships
investment_decision_command_receipts
<optional narrow continuity guard>
```

The relationship table/equivalent may carry both base and correction fact kinds or use another purpose-specific append-only representation; the exact physical split is adapter-owned so long as immutable fact identity/support semantics survive.

No R2 workflow/job/agent/report/RAG/Recommendation/Governance/Action Intent/Outcome/Lesson/generic-event tables.

---

# 14. Constraint strategy

Use DB constraints where practical for unique UUID-backed Decision/Need/lifecycle-fact/relationship-fact identities and receipts/operation IDs, lifecycle sequence, one-Need/one-Decision uniqueness, FKs, non-null effective/recorded times, `ESTABLISHED` Scope requiring at least one Portfolio, work values, relationship self-reference/type, correction target references, and absence of one-to-one Supersession restriction.

History-dependent semantics remain domain/application validated with transactional defense in depth.

---

# 15. Fresh migration lineage and adapter choices

Fresh greenfield root; no legacy revision/table dependency; current migration metadata imports only current greenfield models; empty DB migrates root -> head; legacy data conversion outside R2.

Alembic/ORM/driver choice remains Spec-owned unless it alters inward semantics.

---

# 16. Failure translation

Translate receipt uniqueness -> idempotency evaluation; reused Need reference -> `DecisionNeedAlreadyGrounded`/equivalent; expected-version miss -> concurrency conflict; initiation serialization/guard failure -> continuity conflict; invalid Scope -> semantic/constraint failure; cycle/support ambiguity -> relationship/operative conflict; FK/correction integrity -> invariant error; transient outage -> retryable persistence unavailable; schema/config defect -> explicit startup/operation failure.

Raw DB exceptions never become application API.

---

# 17. Recovery and reads

After restart, Decision/Need/Scope load; unresolved Scope remains explicit; lifecycle and relationship facts/corrections remain inspectable; receipts replay; determinate/contested lifecycle, relationship-support, and operative projections rebuild; continuity semantics do not depend on in-memory locks; lineage remains queryable; initiation continuity basis remains reconstructable; one-Need/one-Decision integrity remains durable; no replay engine is required.

Support efficient bounded reads for Decision/Need, lifecycle history, operation receipt, unresolved operative candidates, continuity basis, renewal/Supersession adjacency/ancestry, relationship support/corrections, recorded cutoff, effective-time lookup, and correction/support references.

---

# 18. Adapter contract tests

## Atomicity and cardinality

- lifecycle fact/correction + projection + receipt together;
- initiation continuity basis + revalidation + Need + Decision + fact + receipt together;
- one Need cannot be referenced by two Decisions, including concurrent attempts;
- many-target Supersession all-or-nothing;
- injected failure leaves no partial semantic success.

## Scope

- no Scope established;
- partial Scope;
- established non-empty Scope;
- empty `ESTABLISHED` Scope rejected;
- unordered membership/duplicate rejection survives adapter round-trip;
- revisions reconstruct historically.

## Continuity

- no-candidate creation persists `NO_CANDIDATES` basis;
- explicit create with candidates persists candidate IDs + attributable rationale;
- replay/restart preserves continuity explanation;
- different operation IDs racing cannot silently duplicate one coherent choice.

## Work/operative

- re-Deferral appends fact;
- supported superseded Decision is non-operative;
- contested Supersession support yields contested operative status and normal work cannot pass through as ordinary success.

## Temporal/correction

- later-recorded earlier-effective fact excluded from earlier `as_known_at`;
- future-effective fact already recorded does not affect `as_known_at` before its effective time;
- current effective query applies supported correction;
- original lifecycle/relationship fact remains queryable after correction;
- External/unsupported correction may qualify earlier recorded resolution;
- competing lifecycle/relationship corrections -> contested, not newest-wins.

## Relationships / insulation

- relationship fact IDs round-trip as domain identity distinct from row identity;
- resolved Decision can be superseded without lifecycle mutation;
- many-to-many Supersession persists;
- relationship correction targets prior fact append-only;
- relationship-only version increment does not fabricate lifecycle sequence;
- direct/indirect mixed lineage cycles blocked;
- ambiguous cycle support fails closed;
- current relationship storage does not require speculative `PRIOR_DECISION_CONTEXT` payload;
- same port contract testable without PostgreSQL-native types inward.

---

# 19. Spec-readiness rule

The foundation public-contract blockers are resolved. Specs may choose driver/ORM/migration library, exact tables/indexes, lock/isolation strategy, and reconstruction implementation only when those choices preserve the completed inward/public contract.

Specs may not weaken one-Need/one-Decision cardinality, UUID-backed identity contracts, Scope validity/equality, lifecycle sequence vs Decision version separation, atomicity, durable continuity explanation/revalidation, many-to-many relationship semantics, relationship fact identity, append-only lifecycle/relationship correction, contested lifecycle/relationship/operative interpretation, dual temporal queries, or Actor/Trigger/Technical Provenance separation.