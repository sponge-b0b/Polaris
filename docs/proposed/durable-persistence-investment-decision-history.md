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

The later owner-approved [R2 lifecycle correction support contract](investment-decisions-r2-lifecycle-correction-support-contract.md) controls lifecycle-disposition correction and temporal interpretation. Preserve each public result's explicit `(effective_at=T, known_at=K)` boundary and exact surviving support. Unknown-at-K is not found; known zero-effective-positive history is `NOT_YET_EFFECTIVE`, without effective support or posture. This supersedes older two-state summaries and implicit-current-time shorthand below; Application supplies observation time rather than the domain reading a clock or deriving now from the latest fact.

Preserve non-decreasing `recorded_at` in lifecycle sequence, including timestamp ties, so ordinary acts can be validated against their strictly earlier sequence prefix at recording and proposed effective time. Retain known future-effective target ancestry for independently active lifecycle-correction descendants. Reconstruct branch-local restoration, semantic cross-root compatibility, and minimal surviving lifecycle support without latest-write selection or retroactive invalidation of admitted ordinary acts.

Exact operation/request replay returns the receipt without append; changed-request reuse conflicts. Every distinct valid lifecycle correction act appends even if equivalent. Compare preceding and appended histories at the same command recording boundary for the version consequence, including support-only changes. A future-only lifecycle correction may advance lifecycle sequence without advancing version; clock passage and queries create neither facts nor versions. Existing receipt/transaction ownership remains here and in Application; #296 introduces no domain receipt framework or generic Subject/Scope/work-posture correction. These rules control any less precise lifecycle-correction/version wording below.

The owner-approved [Investment Decision Relationship Model](investment-decisions-decision-relationship-model.md) controls relationship correction/interpretation, purpose-specific basis roles, historical admission, same-command correction ancestry, relationship-driven both-endpoint `DecisionVersion`, distinct attributable relationship acts versus replay, and the complete known-timeline conservative graph-admission predicate. Persistence must retain enough immutable history and transactionally protect enough read/absence state to reproduce those semantics exactly. Matching endpoint versions alone are insufficient because future/history-only and non-endpoint graph changes may alter admission safety without advancing a touched Decision's version.

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
15. the completed opaque UUIDv4-backed domain/application identity contracts survive persistence without conversion to semantic strings or database-generated business identity, including `PortfolioId`, `InvestmentDecisionId`, `DecisionNeedId`, `DecisionLifecycleFactId`, `DecisionRelationshipFactId`, `OperationId`, and `ActorId`;
16. relationship history can reconstruct recursive qualification/disconfirmation, exact four-state interpretation, complete support/basis membership, historical admission, and same-command target ancestry without relying on physical insertion order;
17. relationship transaction protection detects stale graph/history/absence predicates even when endpoint versions remain equal.

---

# 2. Inward-owned ports

## Decisions command store

Must support loading current state/version, prior command result, atomic lifecycle mutation/correction, new Decision establishment after continuity revalidation, one/multiple typed relationship facts/corrections, projection update, receipt persistence, and explicit uniqueness/continuity/version/relationship/correction failure.

Relationship commands additionally require a transaction boundary capable of validating/revalidating complete relevant endpoint history, relationship ancestry, historical/known-future graph predicates, path reachability, and absence assumptions before atomic commit. The port expresses the semantic guarantee; it does not expose SQL/PostgreSQL/session/ORM/table/vendor mechanisms inward.

## Decision Memory reader

Must support current view, immutable history/corrections, `as_known_at`, `effective_at(T, known_at=K)`, determinate vs contested lifecycle/operative interpretation, renewal/Supersession lineage and exact relationship support/basis interpretation, conservative unresolved operative candidates, initiation continuity basis, and observation guards for atomic revalidation.

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

`DecisionLifecycleSequence` and `DecisionVersion` are separate concepts. Lifecycle initiation starts both at 1. Every distinct valid lifecycle correction appends the next lifecycle sequence, while `DecisionVersion` advances only when the frozen current-interpretation comparison requires it. A later relationship-only mutation may increment Decision version without inventing a lifecycle fact or lifecycle-sequence entry.

### `DecisionInitiated` continuity provenance

The initiation fact (or inseparable typed initiation record referenced by it) preserves:

- continuity determination kind (`NO_CANDIDATES` or `EXPLICIT_CREATE_NEW`);
- candidate Decision IDs materially considered when non-empty;
- known Actor Attribution plus non-empty rationale for explicit create-new with candidates;
- candidate knowledge cutoff used for continuity determination and commit revalidation;
- any typed lineage relationship basis established in the same initiation.

Persistence-specific lock IDs, advisory-lock keys, row-version tokens, and equivalent mechanical guard details belong to adapter/receipt evidence rather than lifecycle provenance.

## 4.4 Decision relationship

Use a many-to-many-capable append-only representation whose semantic records preserve at least:

### Base relationship assertion

```text
DecisionRelationshipFactId
source_decision_id
target_decision_id
relationship_type
relationship_effective_at
recorded_at
OperationId
Actor Attribution where material
Trigger Provenance
optional Technical Provenance
purpose-specific typed relationship basis
```

### Relationship correction

```text
DecisionRelationshipFactId
target_relationship_fact_id
effect: QUALIFY | DISCONFIRM
correction_effective_at
replacement_relationship_effective_at   # QUALIFY only
replacement typed relationship basis    # QUALIFY only
recorded_at
OperationId
Actor Attribution where material
Trigger Provenance
optional Technical Provenance
typed correction basis
```

Every base/correction fact has a unique opaque `DecisionRelationshipFactId` that is distinct from persistence row identity and is never a hash/composite derived from source/type/target content.

Purpose-specific relationship basis and correction basis are separate semantic roles. A base or `QUALIFY` replacement positive requires its relationship-type basis; every `QUALIFY`/`DISCONFIRM` separately requires correction basis. Missing bases are not inherited from the target, inferred from provenance, or synthesized from recency/support count.

A correction targets exactly one base relationship fact or earlier correction in the same immutable source/type/target lineage. Same-command target ancestry may reference another fact in the same atomic command, but the complete explicit target-reference graph must be acyclic and rooted in an independently valid base. Request-list, insert, UUID, or timestamp order must not be persisted/used as semantic precedence. No relationship sequence is introduced.

Persistence must preserve the immutable target ancestry and the trusted recording/admission boundary needed to distinguish “valid when admitted under knowledge R” from later interpretation. A later endpoint lifecycle correction never causes persistence to rewrite/delete/revalidate the historical relationship record as if it had been invalid then.

For reconstructable combined interpretation, preserve enough to emit the exact group `(source, type, target)`, four-state result `SUPPORTED | CONTESTED | WITHDRAWN | NOT_EFFECTIVE`, every surviving effective positive claim/effective instant, complete interpreted support IDs, and role-associated surviving relationship/correction bases with contributor associations. Defeated facts remain raw history even when excluded from current interpreted support. Not-found-at-cutoff and incomplete/invalid-history are distinct from the four valid states.

`QUALIFY`'s correction effective instant and replacement relationship effective instant are distinct persisted semantics and may not be collapsed.

No one-to-one Supersession uniqueness by default.

R2 does not create `PRIOR_DECISION_CONTEXT`. The inward relationship model must remain extensible so that a future purpose-specific context relationship can carry the exact target historical knowledge/version boundary actually used, but current `RENEWED_FROM`/`SUPERSEDES` records do not gain speculative nullable context fields merely for future possibility.

## 4.5 Command receipt

Preserves UUID-backed `OperationId`, command kind, semantic request fingerprint/equivalent, affected Decision IDs, committed result/version(s), stable replay result, committed time.

The UUID value is only the opaque operation identity. Same-operation/same-request replay semantics remain determined by the receipt/request contract, not by interpreting UUID contents.

Exact same-operation/same-request replay returns the stored result without allocating/appending another lifecycle or relationship fact and without version change. Same Operation ID with a different semantic request conflicts and commits nothing. A different valid relationship operation remains a distinct attributable act and appends a fresh fact even when equivalent to existing support.

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
+ current projection/version when required by current-interpretation comparison
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
+ relationship admission/graph validation when lineage facts exist
+ receipt
```

The transaction must enforce both Decision identity uniqueness and one-Need/one-Decision cardinality.

Relationship command:

```text
complete atomic set of relationship facts/corrections
+ same-command target ancestry validation
+ historical endpoint/relationship admission validation
+ complete historical/known-future graph predicate
+ protected endpoint DecisionVersion updates when required
+ authoritative revalidation/protection of every material history/path/absence dependency
+ receipt
```

No partial semantic success. Tentative validation stages never become public/durable state. An explicitly supplied atomic correction set may repair multiple relationships together when the complete final history passes all predicates.

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

Supported incoming Supersession of an unresolved Decision projects `NON_OPERATIVE`; relevant contested incoming Supersession projects `CONTESTED`, including beside otherwise clean support, and normal work fails closed. Relationship truth itself is not erased when endpoint lifecycle/applicability later changes.

---

# 8. Relationship persistence and reconstruction

`RENEWED_FROM` and `SUPERSEDES` use many-to-many-capable storage and consume the relationship model as the only relationship reducer.

Required persistence semantics include:

- every distinct valid base/correction act carries a fresh unique `DecisionRelationshipFactId`; equivalent claims are not deduplicated into one fact;
- resolved target may be superseded; unresolved supported target becomes non-operative without lifecycle mutation;
- no one-to-one unique constraint;
- correction is append-only and may recursively target an earlier correction in the same lineage;
- `QUALIFY` and `DISCONFIRM` remain distinct effects; correction-of-correction may restore the preceding positive/qualification/withdrawal branch;
- sibling branches remain independently reconstructable;
- same-command target references form explicit acyclic causal ancestry and are not ordered by physical persistence order;
- `QUALIFY` preserves separate correction and replacement relationship effective instants;
- current combined interpretation uses exact claim equivalence/conflict rules and four valid states rather than newest-wins;
- equivalent surviving support unions every distinct support fact and valid typed basis; defeated ancestry remains raw history;
- explanatory `WITHDRAWN`/`NOT_EFFECTIVE` support is never persisted/projected as a positive graph edge;
- positive relationship admission preserves the authoritative lifecycle knowledge boundary used at admission; unsupported-Need/not-yet-effective/contested endpoint state cannot establish a positive claim at its effective instant;
- renewal additionally preserves proof that each predecessor was substantively/externally resolved when the new source episode began and at the relationship effective instant;
- late omitted renewal lineage is appended to the existing source/Need only when those historical predicates and explicit basis are proven;
- later endpoint lifecycle correction never mutates the relationship record; explicit relationship correction owns relationship-semantic change;
- a relationship-only commit may advance source and target `DecisionVersion` without advancing `DecisionLifecycleSequence`.

R2 does not yet create `PRIOR_DECISION_CONTEXT`; future storage/port extension must be able to preserve a target historical knowledge/version boundary when that real use case is introduced, without pre-populating current relationship records with speculative context fields.

---

# 9. Version / compare-and-set, graph guards, and idempotency

Initiation sets `DecisionVersion` 1.

For relationship changes, compare complete pre-command and complete post-command relationship interpretation at the same trusted recording boundary `(T=R, K=R)`. Both source and target are candidates. Protected current meaning includes group identity/type/direction, state, surviving effective claims/effective instants, complete support IDs, and role-associated bases. Support/basis-only current changes therefore count; a future/history-only append that leaves protected current meaning unchanged may not.

An already-existing Decision advances at most once for an atomic command even if lifecycle and several relationship groups change. A newly created Decision remains version 1 including same-command initial relationships. Relationship commits never fabricate lifecycle sequence entries. Clock/query passage never creates a version.

Expected-version checks remain required for every pre-existing directly touched source/target even when the proposed relationship act would not increment the version. They are not sufficient protection.

Within the same atomic commit, persistence must ensure that every material endpoint/admission history, relationship fact/correction ancestry, reachable return path, graph path, and absence predicate used by validation remains valid against authoritative committed knowledge. Include same-group/cross-group changes, non-endpoint path changes, and future/history-only changes that may not advance endpoint versions. A stale version or failed predicate/snapshot revalidation commits nothing and maps to explicit semantic concurrency/relationship conflict.

Physical protection may use serializable isolation, predicate/range locking, advisory/scoped locks, explicit graph/history generation guards, re-query plus row locks, or another equivalent strategy. The inward guarantee is validation against the complete applicable committed predecessor state at the final trusted `R` boundary followed by atomic commit; endpoint CAS alone is not graph-safety proof.

The intentionally support-sensitive both-endpoint version contract may create more optimistic-concurrency conflicts than applicability-only versioning. This is an accepted correctness tradeoff; optimize coordination if necessary without weakening protected relationship meaning.

Idempotency:

1. no receipt -> command may attempt;
2. same operation/same semantic request -> replay prior result without append/version;
3. same operation/different semantic request -> conflict;
4. different valid relationship operation -> new attributable fact even when equivalent, subject to all admission/concurrency rules.

Crash after commit/before response is recoverable. Idempotency does not solve different-operation duplicate initiation or graph races.

---

# 10. Temporal reconstruction and correction

Every lifecycle/relationship fact/correction carries effective and recorded time. Lifecycle facts additionally carry contiguous `DecisionLifecycleSequence`; that sequence is **not** reused as relationship-history ordering. Relationship correction ordering comes only from explicit target ancestry plus effective/knowledge semantics; request-list/insertion/UUID/timestamp-tie order grants no precedence.

`as_known_at(K)` is the state **effective at K using only records committed by K**. Equivalently:

```text
effective_at(T=K, known_at=K)
```

A fact recorded by K but explicitly effective after K is part of what was known, but it does not alter the state effective at K.

`effective_at(T, known_at=K)` uses only knowledge known by K and applies effective times/corrections at T. Default K=now gives current best supported effective history.

Lifecycle and relationship correction are both append-only but use separate purpose-specific interpretation contracts. Competing corrections never use newest-wins.

Relationship reconstruction must distinguish:

- no base relationship known at `K` -> not-found-at-cutoff;
- known valid relationship history -> exactly `SUPPORTED | CONTESTED | WITHDRAWN | NOT_EFFECTIVE`;
- missing/malformed required correction ancestry -> explicit invalid/incomplete-history failure.

A known future-only base can therefore be `NOT_EFFECTIVE` with empty support rather than not-found; active qualification can create a `NOT_EFFECTIVE` gap with explanatory qualification support. Time passage may change interpretation/support without generating a fact or version.

Late lifecycle correction may alter supported lifecycle projection/effective interpretation without deleting original facts. Later endpoint lifecycle change does not retroactively rewrite relationship admission validity.

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

The adapter may choose FKs, checks, unique `(decision_id, lifecycle_sequence)`, receipt uniqueness, conditional updates/row locks, serializable transactions/predicate protection, advisory/global initiation lock for R2, JSONB for purpose-named non-query-critical payload, recursive CTEs or equivalent algorithms for finite relationship ancestry/lineage checks, and transactional migrations where those choices do not alter inward semantics.

Physical row identity may use adapter-appropriate mechanisms, but it is separate from `DecisionLifecycleFactId` and `DecisionRelationshipFactId` and must not leak inward as domain identity.

No physical mechanism may turn insertion order or an adapter-generated relationship sequence into semantic relationship authority.

These are adapter details.

---

# 13. Expected schema family

```text
decision_needs
investment_decisions
investment_decision_lifecycle_facts
investment_decision_relationships
investment_decision_command_receipts
<optional narrow continuity/relationship guard state>
```

The relationship table/equivalent may carry both base and correction fact kinds or use another purpose-specific append-only representation; the exact physical split is adapter-owned so long as immutable fact identity, explicit target ancestry, basis roles, dual effective instants, admission boundary, and exact support semantics survive.

No R2 workflow/job/agent/report/RAG/Recommendation/Governance/Action Intent/Outcome/Lesson/generic-event tables.

---

# 14. Constraint strategy

Use DB constraints where practical for unique UUID-backed Decision/Need/lifecycle-fact/relationship-fact identities and receipts/operation IDs, lifecycle sequence, one-Need/one-Decision uniqueness, FKs, non-null effective/recorded times, `ESTABLISHED` Scope requiring at least one Portfolio, work values, relationship self-reference/type, correction target references, and absence of one-to-one Supersession restriction.

History-dependent relationship semantics remain domain/application validated with transactional defense in depth. In particular, DB uniqueness alone does not prove recursive correction ancestry, historical endpoint eligibility, complete support interpretation, temporal mixed-lineage acyclicity, or stale absence/path safety.

---

# 15. Fresh migration lineage and adapter choices

Fresh greenfield root; no legacy revision/table dependency; current migration metadata imports only current greenfield models; empty DB migrates root -> head; legacy data conversion outside R2.

Alembic/ORM/driver choice remains Spec-owned unless it alters inward semantics.

---

# 16. Failure translation

Translate receipt uniqueness -> idempotency evaluation; reused Need reference -> `DecisionNeedAlreadyGrounded`/equivalent; expected-version miss or failed protected predicate -> concurrency conflict; initiation serialization/guard failure -> continuity conflict; invalid Scope -> semantic/constraint failure; definite cycle -> relationship cycle; possible cycle under contested positive support -> indeterminate cycle-safety failure; invalid/missing correction ancestry -> relationship-history invariant failure; FK/correction integrity -> invariant error; transient outage -> retryable persistence unavailable; schema/config defect -> explicit startup/operation failure.

Raw DB exceptions never become application API.

---

# 17. Recovery and reads

After restart, Decision/Need/Scope load; unresolved Scope remains explicit; lifecycle and relationship facts/corrections remain inspectable; receipts replay; determinate/contested lifecycle, exact four-state relationship support, and operative projections rebuild; continuity semantics do not depend on in-memory locks; lineage remains queryable; initiation continuity basis remains reconstructable; one-Need/one-Decision integrity remains durable; no replay engine is required.

Support efficient bounded reads for Decision/Need, lifecycle history, operation receipt, unresolved operative candidates, continuity basis, renewal/Supersession adjacency/ancestry, relationship support/corrections, recorded cutoff, effective-time lookup, correction/support references, graph reachability/predicate revalidation, and admission-history boundaries.

---

# 18. Adapter contract tests

## Atomicity and cardinality

- lifecycle fact/correction + projection + receipt together;
- initiation continuity basis + revalidation + Need + Decision + fact + receipt together;
- one Need cannot be referenced by two Decisions, including concurrent attempts;
- many-target Supersession all-or-nothing;
- atomic multi-correction relationship repair exposes no intermediate committed graph;
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

- later-recorded earlier-effective lifecycle fact excluded from earlier `as_known_at`;
- future-effective fact already recorded does not affect `as_known_at` before its effective time;
- current effective query applies supported lifecycle correction;
- original lifecycle/relationship fact remains queryable after correction;
- External/unsupported correction may qualify earlier recorded resolution;
- competing lifecycle corrections -> contested, not newest-wins;
- recursive relationship `QUALIFY`/`DISCONFIRM` and correction-of-correction restore positive/withdrawal/gap branches exactly;
- distinct correction and replacement relationship effective instants round-trip and reconstruct correctly;
- same-command correction target ancestry survives persistence independently of insertion order;
- future relationship assertion and qualification-gap histories rebuild as `NOT_EFFECTIVE`, not false withdrawal/not-found.

## Relationships / insulation

- relationship fact IDs round-trip as domain identity distinct from row identity;
- distinct equivalent relationship acts retain distinct support IDs/bases while exact replay adds nothing;
- base/replacement relationship basis and correction basis remain separately typed/associated;
- resolved Decision can be superseded without lifecycle mutation;
- many-to-many Supersession persists;
- relationship correction targets prior base/correction fact append-only and same-lineage only;
- late renewal relationship records against existing source/Need without recreating identity when historical admission proof is valid;
- later endpoint lifecycle correction never silently deletes/requalifies relationship persistence;
- relationship-only version update does not fabricate lifecycle sequence;
- support/basis-only current relationship change can update both endpoint versions once;
- future-only append can leave endpoint versions unchanged while remaining visible historically;
- direct/indirect mixed lineage cycles blocked across every known historical/future topology interval;
- contested positive possibilities reject only when a cycle is possible; acyclic contest remains representable;
- concurrent non-endpoint path/future/absence change invalidates stale graph admission even when endpoint versions still match;
- current relationship storage does not require speculative `PRIOR_DECISION_CONTEXT` payload;
- same port contract testable without PostgreSQL-native types inward.

---

# 19. Spec-readiness rule

The foundation, lifecycle-correction, and #297 relationship architecture blockers are resolved. Specs may choose driver/ORM/migration library, exact tables/indexes, lock/isolation strategy, graph/correction traversal algorithm, and reconstruction implementation only when those choices preserve the completed inward/public contract.

Specs may not weaken one-Need/one-Decision cardinality, UUID-backed identity contracts, Scope validity/equality, lifecycle sequence vs Decision version separation, atomicity, durable continuity explanation/revalidation, many-to-many relationship semantics, relationship fact identity, purpose-specific basis roles, recursive append-only relationship correction, historical admission validity, exact four-state relationship interpretation/support, both-endpoint version semantics, temporal graph admission/predicate protection, dual temporal queries, contested lifecycle/relationship/operative interpretation, or Actor/Trigger/Technical Provenance separation.
