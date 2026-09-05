# Application Use Cases for the Investment Decision Lifecycle

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `application-use-cases`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define R2 command/query contracts, continuity arbitration, transactions, idempotency, concurrency, actor/provenance handling, temporal correction, and cross-owner seams.

## Authority

This design refines:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md);
- [`investment-decisions-lifecycle-model.md`](investment-decisions-lifecycle-model.md);
- [`investment-decisions-decision-relationship-model.md`](investment-decisions-decision-relationship-model.md);
- [`investment-decisions-r2-decision-kernel-component-boundaries.md`](investment-decisions-r2-decision-kernel-component-boundaries.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md);
- accepted ADRs under [`../adr/`](../adr/).

---

# 1. Application surface

Commands:

```text
initiate_decision
establish_or_refine_decision_scope
revise_decision_subject
record_deferral_consequence
resume_decision_work
withdraw_decision_work
record_substantive_resolution
record_external_resolution
retract_unsupported_decision_need
initiate_renewed_decision
record_supersession
correct_decision_lifecycle
```

Queries:

```text
get_decision
get_decision_history
get_decision_as_known_at
get_decision_effective_at
find_unresolved_decisions_for_continuity
get_decision_lineage
```

R2 does not expose Recommendation, Attention, Governance persistence, Action Intent, or Learning APIs.

---

# 2. Command envelope

Every mutation carries:

- operation/idempotency ID;
- command kind;
- Actor Attribution/trusted actor reference where domain act attribution applies;
- trigger/source provenance separately;
- technical request/work provenance separately where useful;
- requested effective time only when semantically legitimate;
- expected Decision version(s) where existing state is mutated;
- command payload.

No ORM/SQL/broker/vendor-native objects cross the inward contract.

---

# 3. Result and error model

Success is returned only after durable commit.

Results may contain affected Decision IDs, supported Need/judgment/work state, versions, committed fact/relationship IDs, and replay-vs-new indicator.

Required distinguishable failures/outcomes:

- Decision not found;
- invalid lifecycle operation;
- Decision currently superseded/non-operative;
- concurrency conflict;
- continuity conflict;
- continuity ambiguous;
- idempotency conflict;
- Scope state invalid;
- Deferral basis invalid/missing;
- substantive-resolution basis invalid/missing;
- External-Resolution basis invalid/missing;
- Need-retraction basis invalid/missing;
- relationship/cycle conflict;
- lifecycle-correction conflict;
- persistence unavailable/commit failed.

---

# 4. Initiation / continuity

## Inputs

- operation ID;
- Decision Need determination;
- Decision Subject;
- Decision Scope with confirmed Portfolio refs + `UNRESOLVED|ESTABLISHED` completeness;
- Actor Attribution for Need determination where material;
- trigger/source provenance;
- explicit continuity outcome: `CREATE_NEW`, `CONTINUE_EXISTING(id)`, or `AMBIGUOUS`;
- continuity observation guard returned by candidate query/transaction boundary.

## R2 candidate policy

To avoid hidden matching heuristics, initial R2 continuity query may return **all currently unresolved, non-superseded Decisions**. Optimization/filtering waits until a later owner earns it.

## Behavior

- `CONTINUE_EXISTING` creates nothing; caller uses existing-Decision path;
- `AMBIGUOUS` creates nothing;
- `CREATE_NEW` revalidates candidate basis atomically before commit.

Commit sequence:

1. check idempotency;
2. validate Need/Subject/Scope;
3. atomically revalidate continuity observation;
4. changed candidate basis -> `ContinuityConflict` and no creation;
5. ambiguous continuity -> `ContinuityAmbiguous` and no creation;
6. establish exactly one Need + one Decision;
7. commit Need, Decision, initial fact, initiation relationships, receipt;
8. return success.

At R2 scale, the PostgreSQL adapter may serialize all Decision initiation globally if that is the smallest correct mechanism. This is an adapter choice, not Decision identity.

---

# 5. Scope refinement

Input Scope carries:

```text
confirmed Portfolio refs
completeness = UNRESOLVED | ESTABLISHED
```

Rules:

- zero-known Portfolio unresolved Scope is valid;
- partial confirmed Scope can remain `UNRESOLVED`;
- transitioning/refining Scope preserves same Decision ID when coherent choice remains same;
- every material change is immutable history;
- empty/default Portfolio ID is never the unresolved marker;
- a different coherent choice uses explicit new/renew/supersession semantics.

---

# 6. Subject revision

Allowed only for unresolved, currently operative Decision when revision still describes same coherent choice.

Append immutable Subject-revision fact; expected-version protected.

---

# 7. Record Deferral consequence

Canonical Deferral is Governance-owned Human Investment Decision.

R2 records only Decisions-side work posture from a trusted Deferral basis.

Inputs:

- operation ID;
- Decision ID/version;
- trusted typed Human Investment Decision/Deferral reference;
- effective time;
- optional awaited-condition description/reference.

Valid when Need=`ACTIVE`, judgment=`UNRESOLVED`, Decision operative, and work is `ACTIVE`, `WITHDRAWN`, or already `DEFERRED`.

Behavior:

- result work=`DEFERRED`;
- append new `DecisionDeferred` fact even for re-Deferral;
- preserve all prior Deferral facts;
- no Review Condition is created;
- no Governance fact is fabricated.

---

# 8. Resume work

Valid when:

- Need=`ACTIVE`;
- judgment=`UNRESOLVED`;
- Decision not currently superseded;
- work=`DEFERRED` or `WITHDRAWN`.

Result work=`ACTIVE` + immutable resume fact.

If already `ACTIVE`, return explicit no-transition/already-active outcome.

An awaited condition may motivate resume. A Review Condition on a resolved Decision never resumes the old Decision.

---

# 9. Withdraw work

Valid while Need=`ACTIVE`, judgment=`UNRESOLVED`, Decision operative, work=`ACTIVE|DEFERRED`.

Append `DecisionWorkWithdrawn`; result work=`WITHDRAWN`.

No Human Investment Decision, Deferral, substantive resolution, External Resolution, or Supersession is implied.

---

# 10. Record substantive resolution

Inputs:

- operation ID;
- Decision ID/version;
- trusted typed resolution-basis reference;
- effective time;
- optional lifecycle summary.

Ordinary path requires Need=`ACTIVE` and judgment=`UNRESOLVED` at supported effective point.

Behavior:

- validate basis category;
- set judgment=`SUBSTANTIVELY_RESOLVED`;
- work becomes not applicable;
- append Decisions-side resolution fact + receipt.

R2 tests use trusted fixtures. Later Governance implementation coordinates real Human Investment Decision fact + Decisions consequence atomically when required.

If later knowledge proves Need was already eliminated/unsupported at the resolution effective time, use lifecycle correction; do not delete the human act or prior recorded fact.

---

# 11. External Resolution

Inputs:

- operation ID;
- Decision ID/version;
- basis showing changed circumstance eliminated Decision Need;
- source/external fact reference where available;
- effective time.

Ordinary path requires supported Need=`ACTIVE`, judgment=`UNRESOLVED`.

Behavior:

- Need -> `EXTERNALLY_ELIMINATED`;
- work becomes not applicable;
- append `DecisionNeedExternallyEliminated`;
- judgment axis remains `UNRESOLVED` unless separate historical/corrected facts say otherwise;
- create no Human Investment Decision/Recommendation/Action Intent.

Changed Evidence/Portfolio attractiveness alone is insufficient.

If discovered after conflicting history was recorded, use correction path.

---

# 12. Retract unsupported Decision Need

May occur while unresolved or after other historical acts.

Inputs:

- operation ID;
- Decision/Need ID + expected version;
- attributable correction basis;
- effective interpretation time if meaningful;
- Actor/provenance.

Behavior:

- Need -> `RETRACTED_UNSUPPORTED`;
- preserve original Need and all historical acts;
- if a prior Decisions-side resolution interpretation is no longer supported, append lifecycle correction referencing it;
- never classify this as External Resolution merely because further work stops.

A later genuine Need creates a new Need/Decision under normal continuity rules.

---

# 13. Renewed Decision

Inputs:

- operation ID;
- one or more causal predecessor IDs;
- new Need/Subject/Scope;
- Actor/trigger provenance;
- continuity observation/outcome.

Each predecessor must currently support either:

- substantive judgment resolution; or
- externally eliminated Decision Need.

Successor gets new ID + `RENEWED_FROM` relationship(s). Predecessors remain unchanged.

A retracted-unsupported Need is not automatically a renewal predecessor.

---

# 14. Supersession

Supersession never rewrites Need/judgment/work axes.

## Initiate with Supersession

One transaction may create successor + one or more `SUPERSEDES` edges.

## Record later Supersession

May connect already-existing Decisions.

Targets may be unresolved or historically substantively resolved. Scope/basis explains what continuing applicability is displaced.

No one-to-one cardinality.

An unresolved superseded target becomes non-operative while supported relationship applies.

---

# 15. Lifecycle correction

Inputs:

- operation ID;
- Decision ID/version;
- correction basis;
- prior fact/interpretation being corrected;
- corrected Need/judgment/work interpretation + effective time;
- Actor/provenance.

Behavior:

- append immutable correction fact/reference;
- never update/delete corrected fact;
- recompute supported current/effective projection;
- preserve recorded sequence and prior as-known-at history;
- retry-safe/idempotent.

Late External Resolution example:

- 10:05 Human Investment Decision + Decisions-side resolution recorded;
- 10:10 learn Need was externally eliminated effective 10:00;
- preserve human act and original resolution record;
- append correction making Need=`EXTERNALLY_ELIMINATED` effective 10:00 and qualifying Decisions-side substantive-resolution interpretation as unsupported for effective lifecycle;
- `as_known_at(10:06)` still shows what Polaris knew then.

---

# 16. Queries

## Current Decision

Returns:

- Decision/Need IDs;
- Subject;
- Scope confirmed refs + completeness;
- supported Need status;
- supported judgment status;
- work posture if applicable;
- current operability/Supersession summary;
- version;
- no persistence-native types.

## History

Immutable lifecycle + relationship facts in recorded order with effective/recorded times/corrections.

## `as_known_at(K)`

Only facts/relationships/corrections recorded by `K`.

## `effective_at(T, knowledge_cutoff=K)`

Using only knowledge recorded by `K`, return supported Need/judgment/work/applicability state effective at `T`. Default K=current knowledge.

## Continuity candidates

Initial R2 returns all unresolved non-superseded Decisions plus an observation guard suitable for atomic revalidation.

## Lineage

Typed renewal/Supersession edges with bounded traversal/time filters.

---

# 17. Transactions

Single mutation:

```text
load/version/idempotency
-> domain change
-> atomic current projection + immutable fact + receipt
```

Initiation:

```text
candidate observation
-> explicit continuity outcome
-> atomic revalidation
-> Need + Decision + initial fact + relationships + receipt
```

Supersession:

```text
load source/targets
-> validate cycle/basis
-> atomic relationships (+ successor creation if combined)
```

Future cross-owner human judgment:

```text
Governance fact + Decisions consequence
-> one application transaction when required
```

---

# 18. Idempotency / concurrency

- same operation/same request -> stable replay;
- same operation/different request -> conflict;
- expected-version stale -> conflict, no partial fact/receipt;
- continuity arbitration separately protects distinct operation IDs;
- relationship commands use required multi-Decision conflict detection.

---

# 19. Persistence ports

`DecisionCommandStore` semantics:

- current load;
- idempotency replay;
- atomic single mutation;
- atomic continuity-safe initiation;
- atomic relationship establishment;
- lifecycle correction.

`DecisionMemoryReader` semantics:

- current;
- history;
- as-known-at;
- effective-at;
- all unresolved non-superseded continuity candidates for R2;
- typed lineage.

No generic CRUD repository/UoW yet.

---

# 20. Required application tests

- zero/partial Scope initiation;
- Scope refinement preserves ID;
- actor differs from trigger; model/provider remains provenance;
- exact Need -> one Decision relationship;
- same-operation replay/conflict;
- distinct concurrent initiation re-evaluates after first commit;
- ambiguity creates no Decision;
- Deferral from ACTIVE/WITHDRAWN and re-Deferral from DEFERRED;
- withdrawal distinct from Deferral/resolution;
- External Resolution changes Need axis only;
- Need retraction after prior human/resolution history preserves those facts and uses correction as needed;
- renewal eligibility from substantive resolution or external elimination;
- resolved Decision later superseded without resolution rewrite;
- many-target Supersession;
- as-known-at/effective-at diverge correctly after late correction;
- persistence failure never returns success.

---

# 21. Requirements traceability

| Requirement | Consequence |
|---|---|
| `DEC-001`–`DEC-004` | explicit identity/continuity. |
| `DEC-006` | trusted Human Deferral basis + work posture. |
| `DEC-008` | Need-side External Resolution. |
| `DEC-009`–`DEC-011` | renewal/Supersession preserve histories. |
| `DEC-013` | partial/unresolved Scope. |
| `DEC-014` | withdrawal distinct. |
| `DEC-015` | Need retraction after any historical stage is non-destructive. |
| `DEC-016` | Supersession orthogonal/no cardinality default. |
| `DEC-017` | continuity-safe initiation. |
| `DEC-018` | correction + dual temporal queries. |
| `DEC-019` | actor vs provenance. |
| `MEM-011` | future context target historical boundary. |

---

# 22. Out of scope

Transport APIs, auth provider, Governance persistence, full Review/Awaited Condition models, Recommendation/Evidence/Portfolio internals, async follow-up unless earned, generic workflow/CQRS/event sourcing, and contextual prior-Decision binding implementation.

---

# 23. Spec-readiness gate

Ready only when no Spec must decide:

- Need vs judgment vs work vs Supersession semantics;
- partial Scope meaning;
- Deferral/re-Deferral rules;
- continuity candidate behavior/concurrent initiation;
- late Need retraction/External Resolution correction;
- actor/provenance distinction;
- dual temporal queries;
- transaction/idempotency guarantees.
