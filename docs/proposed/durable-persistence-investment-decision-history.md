# Durable Persistence for Investment Decision History

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `durable-persistence`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define R2 persistence semantics and the initial PostgreSQL adapter precisely enough that Specs can choose concrete libraries/schema details without redefining Decision Need status, judgment resolution, work posture, continuity, temporal correction, idempotency, concurrency, or Decision relationships.

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

1. exactly one Decision Need grounds one Investment Decision and both survive restart;
2. Decision Scope can preserve zero, partial, or fully established Portfolio applicability without inventing defaults;
3. Decision Need status, judgment-resolution status, unresolved work posture, and Supersession remain independent semantics;
4. immutable lifecycle facts and explicit corrections reconstruct both what was known and what is currently supported as effective history;
5. retries do not duplicate business facts;
6. stale mutations cannot silently overwrite newer state;
7. different concurrent initiation operations cannot bypass continuity arbitration merely because their operation IDs differ;
8. renewal and many-to-many Supersession relationships are durable and queryable without rewriting predecessor lifecycle facts;
9. Actor Attribution, trigger/source provenance, and technical provenance remain distinguishable;
10. persistence-native types do not leak inward;
11. greenfield schema/migrations have no dependency on `legacy/`.

---

# 2. Inward-owned persistence contracts

## 2.1 Decision command store

The application needs a semantic write capability that can:

- load current Decision state and version;
- inspect prior command result by operation identity;
- atomically commit one-Decision lifecycle change;
- atomically establish a new Decision after continuity revalidation;
- atomically establish one or more typed Decision relationships;
- atomically combine successor initiation with Supersession relationships when requested;
- persist immutable lifecycle facts and correction facts;
- maintain current supported projections;
- persist command idempotency receipt/result;
- fail explicitly on uniqueness, continuity, relationship, or version conflict.

The port must not expose SQL, PostgreSQL connections/sessions, ORM models, database transaction handles, table names, or vendor-specific exceptions.

## 2.2 Decision memory reader

The application needs a semantic read capability that can:

- return current Decision/Need/Scope inputs;
- return ordered lifecycle and relationship facts;
- reconstruct `as_known_at` state;
- reconstruct `effective_at` state under a stated knowledge cutoff;
- retrieve renewal/Supersession lineage;
- return the R2 continuity candidate universe plus a guard suitable for atomic revalidation.

Optimized projections may exist internally but cannot be the sole historical authority.

---

# 3. No platform-wide Unit of Work yet

R2 still does not need a generic platform Unit of Work.

The Decisions command store may expose purpose-specific atomic semantic commits because R2 durable business changes remain inside one owning domain boundary.

A broader Unit of Work becomes justified only when a later use case atomically coordinates independently owned stores, such as Governance-owned Human Investment Decision plus Decisions-owned Deferral or substantive-resolution consequence.

---

# 4. Logical durable record set

Exact tables/classes are adapter details. Semantically R2 requires the following records.

## 4.1 Decision Need record

Preserves at least:

- Decision Need ID;
- original attributable need statement/determination;
- effective raised/recognized time;
- recorded time;
- current supported Need status:
  - `ACTIVE`;
  - `EXTERNALLY_ELIMINATED`;
  - `RETRACTED_UNSUPPORTED`;
- Actor Attribution for the Need determination where material;
- trigger/source provenance separately;
- immutable creation metadata.

The status values above are design-level representations, not required user-facing vocabulary.

The original Need record is never deleted merely because its current supported status changes.

## 4.2 Investment Decision current record

Provides efficient current access and concurrency protection while preserving semantic separation.

At minimum:

- Investment Decision ID;
- Decision Need ID;
- current Subject representation/reference;
- current Scope representation:
  - zero or more confirmed Portfolio references;
  - completeness `UNRESOLVED | ESTABLISHED`;
- current supported judgment-resolution status:
  - `UNRESOLVED`;
  - `SUBSTANTIVELY_RESOLVED`;
- current work posture when Need=`ACTIVE`, judgment=`UNRESOLVED`, and the Decision is operative:
  - `ACTIVE`;
  - `DEFERRED`;
  - `WITHDRAWN`;
- current domain version;
- creation time;
- any narrow correction/projection marker required to derive the currently supported view deterministically.

Supersession is **not** stored as a replacement lifecycle status. Current operability is derived from supported relationship facts or an explicitly derivable cache/projection.

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
- trigger/source provenance where material;
- technical provenance reference where material;
- typed business basis/reference;
- fact-specific content;
- correction target/reference when the fact qualifies a prior lifecycle interpretation.

Stable query-critical dimensions must not be hidden only in opaque generic metadata.

## 4.4 Decision relationship record

R2 requires a many-to-many-capable typed relation rather than fixed single-predecessor columns as the canonical schema assumption.

Preserve at least:

- relationship ID;
- source Decision ID;
- target Decision ID;
- relationship type (`RENEWED_FROM`, `SUPERSEDES`; later `PRIOR_DECISION_CONTEXT`);
- effective time;
- recorded time;
- operation ID;
- typed basis/scope;
- Actor Attribution/context-selection provenance where material;
- correction/reference state when needed;
- future-compatible target knowledge cutoff for contextual edges.

Inverse navigation is derived; reverse duplicate facts are unnecessary unless the adapter independently needs a projection.

## 4.5 Command idempotency receipt

Preserves:

- operation ID;
- command kind;
- canonical semantic request fingerprint or equivalent comparison data;
- affected Decision ID(s);
- committed resulting version(s);
- stable semantic result needed for replay;
- committed time.

Receipt is application durability metadata, not Decision identity.

## 4.6 Continuity arbitration state

R2 continuity deliberately starts with the complete set of currently unresolved, non-superseded Decisions rather than a hidden semantic matching heuristic.

The initial adapter must guarantee that a `CREATE_NEW` initiation commits only if the candidate universe used for that determination remains valid at commit time.

The smallest initial PostgreSQL mechanism MAY serialize Decision initiation globally. Alternatives include serializable predicate protection, a continuity-generation row/token, or another correct mechanism.

The inward semantic contract is:

```text
observe all currently unresolved, non-superseded Decisions
        ↓
explicit CONTINUE / CREATE_NEW / AMBIGUOUS determination
        ↓
commit revalidates observation atomically
        ↓
changed universe -> no creation; re-evaluate
unchanged + CREATE_NEW -> commit exactly one new Need/Decision
```

The concurrency mechanism is replaceable infrastructure; fail-closed continuity is the contract.

---

# 5. One Need / one Decision integrity

R2 persistence must enforce as far as mechanically possible:

- every Investment Decision references exactly one Decision Need;
- one Decision Need grounds at most one Investment Decision;
- deleting a Decision Need that grounds historical Decision truth is not an ordinary store operation.

A unique relationship/foreign-key constraint may enforce one-Need-to-at-most-one-Decision in PostgreSQL.

If semantic discovery later determines one perceived Need contained multiple independently resolvable choices, new distinct Decision Needs/Decisions are established explicitly rather than sharing the original Need as identity glue.

---

# 6. Atomic consistency

A successful ordinary lifecycle mutation commits atomically:

```text
immutable lifecycle fact
+ current supported Decision/Need projection changes
+ Decision version
+ command receipt
```

A successful relationship operation commits atomically:

```text
relationship fact(s)
+ any affected operability projection
+ required version/conflict checks
+ command receipt
```

A successful new initiation commits atomically:

```text
continuity revalidation
+ Decision Need
+ Investment Decision
+ DecisionInitiated fact
+ optional initiation relationship facts
+ command receipt
```

No observer may see partial semantic success.

---

# 7. Version and compare-and-set

Expected-version semantics are enforced durably.

On a normal lifecycle mutation:

- one new recorded Decision version is committed;
- current version increments once;
- lifecycle fact carries the corresponding recorded sequence/version.

On stale conflict:

- no new fact/relationship/projection from the stale command remains;
- no command receipt claims success;
- adapter translates the failure into technology-neutral concurrency semantics.

Relationship operations spanning multiple Decisions use sufficient expected-version/conflict protection to prevent stale operability/lineage decisions.

---

# 8. Idempotency

Idempotency survives process restart.

Atomic distinctions:

1. no receipt exists -> command may execute;
2. receipt exists with same semantic request -> replay stable result;
3. receipt exists with materially different request -> idempotency conflict.

A crash after commit but before response is recoverable through the same operation ID.

Idempotency does not replace continuity arbitration for different operation IDs.

---

# 9. Scope persistence

Decision Scope is not a nullable scalar.

The physical model must preserve:

```text
confirmed Portfolio refs: zero or more
completeness: UNRESOLVED | ESTABLISHED
```

Therefore these meanings remain distinct:

```text
no Portfolio known yet, Scope unresolved
some Portfolios confirmed, Scope still unresolved/incomplete
Portfolio applicability established
later established Scope refined while same choice remains
```

Do not use empty strings, sentinel Portfolio IDs, or accidental null semantics to mean unresolved Scope.

Every material establishment/refinement remains immutable lifecycle history even when the latest Scope is denormalized in the current Decision projection.

The Spec may choose a normalized child relation or another constrained relational representation for multi-Portfolio Scope; a single array/JSON field must not become the inward contract merely for convenience.

---

# 10. Need, judgment, work, and applicability persistence

The current projection must keep these dimensions independently reconstructable:

```text
Decision Need status
  ACTIVE | EXTERNALLY_ELIMINATED | RETRACTED_UNSUPPORTED

Judgment-resolution status
  UNRESOLVED | SUBSTANTIVELY_RESOLVED

Work posture when applicable
  ACTIVE | DEFERRED | WITHDRAWN

Continuing applicability
  derived from supported SUPERSEDES relationships
```

Mechanical consistency rules should reject impossible current combinations such as a non-null work posture for a currently non-operative externally eliminated Need, while historical facts remain preserved.

A late correction may change the **supported current projection** without mutating historical facts.

---

# 11. Deferral and re-Deferral persistence

Every `DecisionDeferred` fact preserves the trusted Human Investment Decision/Deferral basis reference and its own effective/recorded time.

Rules:

- Governance-owned Human Investment Decision payload is not copied into the Decisions store;
- Deferral may move work `ACTIVE -> DEFERRED` or `WITHDRAWN -> DEFERRED`;
- another attributable Deferral while already `DEFERRED` appends a new fact rather than overwriting the earlier Deferral reason/awaited condition;
- a later resume appends its own fact;
- Review Condition is not persisted as the awaited-condition meaning of Deferral unless a later owner explicitly establishes a separate applicable Review Condition.

---

# 12. Work withdrawal persistence

`DecisionWorkWithdrawn` preserves the actor/basis and time that Polaris work stopped while the Need may remain active and judgment unresolved.

It must not be physically encoded as:

- Deferral;
- substantive resolution;
- External Resolution;
- Supersession;
- deletion of the Decision.

Same-choice resumption later appends a new resume fact.

---

# 13. External Resolution persistence

External Resolution is persisted principally as a **Decision Need status transition**:

```text
Need ACTIVE -> EXTERNALLY_ELIMINATED
```

with immutable `DecisionNeedExternallyEliminated` fact/basis.

It does not mechanically set judgment status to `SUBSTANTIVELY_RESOLVED` and does not create a Human Investment Decision.

If discovered late after human/Decisions-side judgment history already exists, use explicit lifecycle correction rather than deleting that history.

---

# 14. Unsupported Decision Need retraction persistence

A later finding that the original Need determination was erroneous/unsupported appends `DecisionNeedRetracted` and changes current supported Need status to `RETRACTED_UNSUPPORTED`.

This may occur before or after other historical acts.

If a prior Decisions-side substantive-resolution interpretation becomes unsupported as effective lifecycle truth, append `DecisionLifecycleCorrected` referencing that interpretation. Do **not** delete:

- original Need;
- Human Investment Decision;
- Recommendation or other historical facts;
- originally recorded Decisions-side lifecycle fact.

This is not External Resolution.

---

# 15. Supersession persistence

Supersession lives in `investment_decision_relationships` or an equivalent many-to-many relation.

Rules:

- target Need/judgment/work history remains unchanged;
- unresolved or historically substantively resolved targets may be superseded;
- supported Supersession makes unresolved target non-operative without creating a fake terminal lifecycle state;
- one source may supersede multiple targets;
- one target may be superseded by multiple sources when scoped displacement supports it;
- no one-to-one unique constraint is allowed by this design;
- lineage-cycle prevention applies across supported `RENEWED_FROM` + `SUPERSEDES` graph.

An initiation+Supersession command may create successor and several relationship rows in one transaction. Later-recorded Supersession between already-existing Decisions is also supported.

---

# 16. Renewal persistence

`RENEWED_FROM` is a typed relationship from a new Decision to one or more independently supported causal predecessors.

A predecessor is eligible when the prior Decision no longer has unresolved operative judgment because:

- judgment status is `SUBSTANTIVELY_RESOLVED`; or
- Need status is `EXTERNALLY_ELIMINATED`.

`RETRACTED_UNSUPPORTED` is not automatically renewal-eligible because the earlier Need may never have been supportable in the first place.

Predecessor rows/history are never reopened.

---

# 17. Temporal persistence and correction

Every lifecycle/relationship fact preserves:

- effective time;
- recorded/committed time;
- recorded sequence/version.

Recorded sequence/version is canonical ordering of committed knowledge. Timestamps alone are not the ordering primitive.

## 17.1 `as_known_at(K)`

For knowledge cutoff `K`:

- exclude facts/relationships/corrections recorded after `K`;
- apply only correction knowledge already recorded by `K`;
- reconstruct what Polaris durably knew then.

A later-recorded fact with earlier effective time never leaks into an earlier as-known-at result.

## 17.2 `effective_at(T, knowledge_cutoff=K)`

Using only facts recorded by `K`, reconstruct the supported Need/judgment/work/applicability state effective at `T`.

Default `K=now` gives current best supported effective history.

This is Decision lifecycle temporality, not Evidence Judgment-Time Availability.

## 17.3 Lifecycle correction

A correction is append-only and references the exact prior fact/interpretation it qualifies.

It may change current/effective projections without deleting original records.

The adapter must prevent ambiguous correction chains from producing two unqualified competing current interpretations. A practical implementation may require every correction to identify its target fact/interpretation and current supported replacement/qualification explicitly.

Example:

```text
10:00 external circumstance eliminates Need
10:05 Human Investment Decision + Decisions-side resolution fact recorded
10:10 10:00 fact learned
```

Persistence keeps all recorded history and appends correction so:

- `as_known_at(10:06)` remains unchanged;
- current effective history shows Need externally eliminated at 10:00;
- Human Investment Decision remains historical;
- prior Decisions-side resolution interpretation is explicitly qualified rather than erased.

---

# 18. Actor Attribution vs provenance storage

Do not collapse actor and provenance into one generic `created_by` field.

Where material, preserve separate representations for:

- domain Actor Attribution/reference;
- trigger/source provenance;
- technical request/work/model/provider provenance.

The Actor representation must support at least the semantic categories established by the lifecycle design, including Polaris, human, collective/organization, external actor, and unknown/disputed attribution.

A model/provider/workflow identifier cannot satisfy Actor Attribution merely because it technically participated.

---

# 19. PostgreSQL initial adapter

PostgreSQL fits R2 because of transaction, relational integrity, indexing, and concurrency capabilities.

Adapter may use internally:

- UUID identities;
- foreign keys;
- constrained enum/text values;
- unique operation receipts;
- unique `(decision_id, recorded_sequence)`;
- unique one-Decision-per-Decision-Need relationship;
- row/transaction locks;
- serializable initiation if selected;
- JSONB for purpose-named non-query-critical payload detail;
- recursive CTEs or application-side bounded ancestry checks for lineage cycles;
- transactional migrations.

These mechanisms are adapter details and must not leak inward.

---

# 20. Expected logical schema

Approximately:

```text
decision_needs
investment_decisions
investment_decision_scope_members       # or equivalent multi-Portfolio representation
investment_decision_lifecycle_facts
investment_decision_relationships
investment_decision_command_receipts
<optional narrow initiation/continuity serialization structure>
```

Exact table names are not mandated.

Do not add R2 tables for workflow/job/runtime, agents/models, reports, RAG, Recommendation, Governance, Action Intent, Outcome/Lesson, universal event sourcing, or a global persistence taxonomy.

---

# 21. Constraint strategy

Good candidates for mechanical enforcement:

- unique Decision/Need/fact/relationship IDs;
- each Need grounds at most one Decision;
- unique operation receipts;
- unique recorded sequence per Decision;
- valid foreign keys;
- non-null required effective/recorded times;
- valid current Need/judgment/work combinations;
- explicit Scope completeness semantics;
- unique Scope membership per Decision/Portfolio at a current projection level as appropriate;
- no relationship self-reference;
- relationship-type checks;
- correction references valid prior fact/relationship;
- no one-to-one Supersession uniqueness restriction.

History-dependent semantic rules remain domain/application validation with transactional defense in depth.

---

# 22. Fresh migration lineage

- fresh greenfield root;
- no dependency on legacy migration revisions/tables;
- current migration metadata imports current greenfield definitions only;
- empty database migrates root -> head;
- legacy data conversion is out of R2 scope.

The Spec may choose Alembic if it remains the smallest suitable migration tool.

---

# 23. ORM / driver choice

No ORM/driver is mandated.

Spec selects the smallest maintained stack satisfying:

- explicit transaction control;
- expected-version concurrency;
- continuity-safe initiation;
- migration support;
- chosen sync/async execution style;
- testability;
- clean inward contract separation.

Legacy SQLAlchemy/Alembic mechanics may be mined after the Spec selects the stack; legacy schema taxonomy must not be transplanted.

---

# 24. Failure translation

Database-native failures map to semantic outcomes, e.g.:

- operation uniqueness collision -> idempotency replay/conflict evaluation;
- expected-version miss -> concurrency conflict;
- initiation serialization/guard conflict -> continuity conflict/re-evaluation;
- relationship/cycle integrity failure -> relationship semantic error;
- Scope/Need uniqueness/correction integrity failure -> semantic persistence/invariant error;
- transient database outage -> retryable persistence unavailable;
- schema/configuration defect -> explicit startup/operation failure.

Raw database exceptions are not application API.

---

# 25. Recovery behavior

After ordinary restart:

- Decision/Need/current Scope load;
- partial/unresolved Scope remains explicit;
- lifecycle and relationship facts remain complete/ordered;
- receipts replay committed results;
- supported current projection can be reconstructed/verified from immutable facts/corrections;
- initiation continuity does not depend solely on in-memory locks;
- no generic replay engine is required.

---

# 26. Read/index expectations

Support efficient bounded reads for:

- Decision/Need by ID;
- lifecycle history by Decision + sequence;
- receipt by operation ID;
- all currently unresolved, non-superseded Decisions for initial R2 continuity;
- renewal/Supersession adjacency and bounded ancestry;
- recorded-time cutoff;
- effective-time lookup under knowledge cutoff;
- correction references;
- current Scope membership/completeness.

Do not add speculative analytics/reporting indexes.

---

# 27. Adapter contract tests

## Atomicity

- single mutation commits projection + fact + receipt together;
- initiation continuity revalidation + Need + Decision + fact + receipt together;
- many-target Supersession all-or-nothing;
- injected failure leaves no partial semantic success.

## Identity / continuity

- one Need cannot ground two Decisions;
- two different initiation operations serialized/racing cannot both silently create a new Decision after candidate universe changes;
- continuity conflict forces re-query/re-evaluation.

## Scope

- zero-known Scope with `UNRESOLVED` completeness persists;
- partially known Scope persists without becoming `ESTABLISHED` accidentally;
- establishment/refinement is historical;
- sentinel/default Portfolio values are not used.

## Idempotency / concurrency

- replay returns prior result;
- same operation/different request conflicts;
- stale expected version leaves no false fact/receipt;
- restart preserves receipt.

## Lifecycle axes

- Need status, judgment status, and work posture can be reconstructed independently;
- External Resolution changes Need status without manufacturing substantive judgment;
- Deferral/re-Deferral facts are append-only;
- withdrawal remains distinct;
- Need retraction after prior human/resolution history preserves those records and applies correction when necessary.

## Relationships

- renewal eligibility uses substantive judgment resolution or external Need elimination;
- resolved target can be superseded without resolution rewrite;
- one-to-many/many-to-one Supersession works;
- self/mixed lineage cycles rejected;
- late relationship excluded from earlier as-known-at.

## Temporal correction

- corrected facts cannot be updated/deleted through ordinary API;
- as-known-at before correction remains stable;
- effective-at current knowledge reflects late correction;
- current projection agrees with supported corrected history.

## Fresh lineage

- empty DB migrates greenfield root -> head;
- no legacy metadata/schema dependency.

---

# 28. Requirements traceability

| Requirement | Persistence consequence |
|---|---|
| `GF-003`–`GF-005` | fresh schema; business identity independent of rows/runtime. |
| `DEC-001`–`DEC-004` | one Need/Decision identity and immutable continuity history. |
| `DEC-013` | zero/partial/established Scope states. |
| `DEC-014` | withdrawal represented distinctly. |
| `DEC-015` | Need retraction can qualify history non-destructively. |
| `DEC-016` | Supersession is many-to-many relationship, not lifecycle status. |
| `DEC-017` | continuity-safe initiation across different operation IDs. |
| `DEC-018` | dual time + explicit correction. |
| `DEC-019` | actor/source/technical provenance stored distinctly. |
| `MEM-005`, `MEM-009` | non-destructive direct business truth. |
| `MEM-011` | future context edge can bind target knowledge cutoff. |
| `REL-*` | durable retry, atomicity, concurrency, recovery. |

---

# 29. Out of scope

R2 persistence does not implement full Evidence, Recommendation, Portfolio/Risk, Governance/Human Decision, Action Continuity, Learning stores; generic outbox/event bus/UoW; warehouse/vector/graph database; contextual prior-Decision binding; or legacy data conversion.

---

# 30. Spec-readiness gate

Persistence design is Spec-ready only when:

1. four lifecycle dimensions remain separable in physical representation;
2. Scope supports zero/partial/established Portfolio applicability;
3. one Need cannot silently ground multiple Decisions;
4. continuity-safe initiation requires no hidden matching heuristic in the Spec;
5. re-Deferral/withdrawal/Need retraction remain distinct durable facts;
6. relationship storage is many-to-many and cycle-safe;
7. correction is append-only and dual temporal queries are deterministic;
8. actor/provenance cannot collapse into one field semantically;
9. PostgreSQL mechanisms stay adapter-internal;
10. no persistence Spec must invent these guarantees.
