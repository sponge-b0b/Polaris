# Application Use Cases for Investment Decision Lifecycle

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `application-use-cases`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define the R2 application command/query contracts, explicit continuity arbitration, transaction boundaries, idempotency, concurrency behavior, actor/provenance handling, temporal correction, and cross-entity seams for Investment Decision lifecycle truth.

## Authority

This design refines:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md);
- [`investment-decisions-lifecycle-model.md`](investment-decisions-lifecycle-model.md);
- [`investment-decisions-decision-relationship-model.md`](investment-decisions-decision-relationship-model.md);
- [`investment-decisions-r2-decision-kernel-component-boundaries.md`](investment-decisions-r2-decision-kernel-component-boundaries.md);
- [`durable-persistence-investment-decision-history.md`](durable-persistence-investment-decision-history.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- proposed [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md).

Application coordinates owner behavior; it does not create a second domain model.

---

# 1. R2 application surface

Conceptual commands:

```text
initiate_decision
establish_or_revise_scope
revise_subject
apply_human_deferral
resume_decision_work
withdraw_decision_work
apply_substantive_resolution
apply_external_resolution
retract_unsupported_decision_need
record_lifecycle_correction
renew_decision
establish_supersession
```

Conceptual queries:

```text
get_decision
get_decision_history
get_decision_as_known_at
get_decision_effective_at
get_decision_lineage
find_unresolved_continuity_candidates
```

Names are not prescribed APIs; semantics are.

---

# 2. Command envelope

Every mutation carries semantic input equivalent to:

```text
operation_id
actor_context / actor_attribution input where applicable
trigger_provenance
technical_correlation metadata
business effective time or clock-derived effective time
expected version(s) when mutating existing Decisions
command-specific payload
```

Actor Attribution, trigger provenance, and technical provenance remain separate.

---

# 3. Initiation and continuity arbitration

## 3.1 Inputs

New Decision initiation includes:

- Decision Need statement/basis;
- Decision Subject;
- Scope representation that may be unresolved/partial;
- Actor Attribution for Need determination where material;
- trigger provenance;
- operation ID;
- **explicit continuity determination** when unresolved operative candidates exist.

## 3.2 Candidate discovery

Application queries conservative unresolved, operative candidates. R2 may treat all unresolved non-superseded Decisions as candidates rather than inventing semantic similarity.

## 3.3 Continuity determination contract

Allowed semantic outcomes:

```text
CONTINUE_EXISTING(decision_id)
CREATE_NEW
AMBIGUOUS(candidate_ids)
```

Rules:

- no candidates: `CREATE_NEW` may be selected automatically, subject to revalidation;
- candidates exist: caller/use case must explicitly determine `CONTINUE_EXISTING` or `CREATE_NEW` after considering them;
- missing, stale, contradictory, or insufficient determination -> `AMBIGUOUS` and no creation;
- R2 contains no hidden similarity/ranking algorithm;
- later Attention may automate determination, but must use this contract and preserve attributable basis.

If `CONTINUE_EXISTING`, initiation returns/routes to the existing Decision rather than creating another identity.

## 3.4 Atomic revalidation

`CREATE_NEW` commits only if the observed candidate basis remains compatible. Changed basis -> `ContinuityConflict` and re-evaluation.

The PostgreSQL adapter may serialize initiation broadly for R2 correctness.

---

# 4. Scope and Subject

`establish_or_revise_scope` accepts zero-or-more confirmed Portfolio references + completeness (`UNRESOLVED`/`ESTABLISHED`), preserves history, and never changes Decision ID merely because Scope changes.

`revise_subject` similarly preserves identity only while the coherent unresolved choice remains the same. If the change actually describes an independently resolvable choice, application routes to continuity/new-Decision determination rather than silently mutating identity.

Ordinary Scope/Subject work requires the Decision to remain unresolved and operative unless the operation is explicitly a historical correction.

---

# 5. Human Deferral seam

Deferral requires a typed trusted upstream basis, normally Governance-owned Human Investment Decision with semantic effect `DEFERRING`.

Application:

1. validates trusted owner/fact reference and deferring effect;
2. loads Decision/version + operative state;
3. requires supported lifecycle disposition `UNRESOLVED`;
4. permits Deferral from `ACTIVE`, `WITHDRAWN`, or already `DEFERRED` work;
5. invokes Decisions behavior producing a new immutable `DecisionDeferred` fact;
6. persists only Decisions-side consequence + basis reference;
7. does not infer authority or copy Governance payload.

Re-Deferral while already deferred is valid only with a new attributable Human Investment Decision basis. It appends history and leaves work posture `DEFERRED`.

Awaited Deferral condition is not a Review Condition.

---

# 6. Resume and withdrawal

`resume_decision_work` requires:

- lifecycle determinately `UNRESOLVED`;
- Decision operative/not supportably superseded;
- posture `DEFERRED` or `WITHDRAWN`;
- expected version;
- same-choice resumption basis.

`withdraw_decision_work` records work-control withdrawal without Human Investment Decision or lifecycle resolution. It is valid from `ACTIVE` or `DEFERRED` while unresolved/operative and preserves prior Deferral history.

---

# 7. Substantive resolution seam

`apply_substantive_resolution` requires:

- lifecycle determinately `UNRESOLVED`;
- Decision operative;
- typed trusted upstream basis with semantic effect `SUBSTANTIVELY_RESOLVING`;
- expected version.

Application records only Decisions-side `DecisionSubstantivelyResolved` consequence. It does not infer Approval, authority sufficiency, Recommendation acceptance, or Action Intent.

When Governance exists, cross-owner atomicity may earn a broader Application Unit of Work. R2 does not pre-build one.

---

# 8. External Resolution

`apply_external_resolution` requires attributable circumstance/basis that eliminated the Need.

Application distinguishes:

- choice eliminated -> External Resolution;
- facts changed but same choice remains -> no lifecycle resolution;
- original Need unsupported -> Need retraction/correction.

External Resolution is a lifecycle correction/observation path and may target a superseded historical Decision when new facts establish what happened; it is not ordinary continuation of decision work.

No Human Investment Decision is inferred.

---

# 9. Unsupported Need retraction

`retract_unsupported_decision_need` appends an attributable correction that original Need determination was unsupported/erroneous.

It may occur after substantial work, Supersession, or historical Human Investment Decision. All prior acts remain history. No deletion or retroactive conversion is allowed.

---

# 10. Lifecycle correction

`record_lifecycle_correction` is internal/privileged and accepts target fact/interpretation, correction kind, effective time, trusted basis/reference, Actor Attribution/provenance, expected version, and operation ID.

It must preserve the original fact, append correction, recompute supported interpretation, and expose contested/indeterminate state when typed semantics cannot reconcile competing support. Recorded order alone never gives semantic precedence.

No generic public “set lifecycle status” interface is allowed.

---

# 11. Renewal

`renew_decision` creates a new Decision after one/more prior Decisions were supportably substantively or externally resolved and a new Need exists.

It performs normal initiation continuity arbitration and atomically creates the new Need/Decision plus supported `RENEWED_FROM` edges. Predecessors remain unchanged; lifecycle-lineage cycles are rejected.

Unsupported/retracted Need is not automatically a renewal predecessor merely because historical work existed.

---

# 12. Supersession

`establish_supersession` may create a new successor + one/many edges or establish one/many edges among existing Decisions.

Rules:

- target may be unresolved/resolved;
- target lifecycle disposition is unchanged;
- unresolved supported target becomes non-operative for ordinary work/continuity selection;
- many-to-many allowed;
- all edges in one semantic command commit atomically;
- cycle check uses currently supported lifecycle-lineage graph;
- contested support fails closed when cycle safety cannot be established.

---

# 13. Transaction boundaries

Success only after required durable commit.

```text
ordinary mutation:
  lifecycle fact/correction
  + current projection/version
  + receipt

new initiation:
  candidate-basis revalidation
  + Need
  + Decision
  + DecisionInitiated
  + optional lineage edges
  + receipt

relationship command:
  all requested relationships
  + operative projections/guards as needed
  + receipt
```

No partial semantic success.

---

# 14. Expected-version concurrency and idempotency

Existing-Decision mutation uses expected version or equivalent CAS. Stale version commits nothing.

Same operation + same semantic request replays original result. Same operation + different request conflicts. Different operation IDs still require continuity/concurrency protection.

Relationship commands touching multiple Decisions require sufficient guards on all semantically affected state.

---

# 15. Query semantics

Current Decision view returns identity/Need/Subject/Scope, determinate supported lifecycle disposition or contested interpretation, work posture if applicable, version, operative/Supersession summary, and references to other-owner facts.

`as_known_at(K)` uses only records known by K.

`effective_at(T, known_at=K)` applies effective times/corrections using only knowledge available by K.

History returns raw immutable facts/corrections plus typed support relationships; it never hides disconfirmed historical facts.

Lineage returns typed renewal/Supersession edges with effective/recorded time and correction/support status.

---

# 16. Semantic outcomes

Callers must distinguish at least:

```text
NotFound
DecisionNonOperative
InvalidLifecycleTransition
InvalidTrustedBasis
ScopeValidationFailure
ConcurrencyConflict
IdempotencyConflict
ContinuityConflict
ContinuityAmbiguous
RelationshipConflict
RelationshipCycle
LifecycleInterpretationContested
PersistenceUnavailable
```

Concrete names are optional.

---

# 17. R2 application tests

Required fake-port tests include:

- initiate with unresolved Scope;
- no candidates -> create after revalidation;
- candidates + explicit continue -> no new identity;
- candidates + explicit create -> create only after revalidation;
- candidates + missing/contradictory determination -> ambiguity/no creation;
- different-operation race -> no silent duplicate;
- Scope refinement preserves ID;
- Deferral rejected without trusted deferring basis;
- re-Deferral appends another Deferral fact;
- awaited Deferral condition != Review Condition;
- withdrawn Decision resumes same identity;
- superseded unresolved Decision rejects ordinary resume/defer/resolve;
- substantive resolution requires trusted resolving basis;
- External Resolution vs unsupported Need distinguished;
- unsupported correction preserves prior human acts;
- resolved target superseded without lifecycle mutation;
- many-target Supersession atomic;
- late correction preserves earlier `as_known_at`;
- competing corrections -> contested interpretation;
- idempotent retry and stale-version behavior;
- actor/trigger/technical provenance remain separate.

---

# 18. R2 exclusions / Spec gate

No Attention service, Evidence assembly, model orchestration, Governance implementation, arbitrary trusted-basis injection, Action Continuity, generic event/workflow runtime, generic graph service, or platform-wide UoW framework is introduced.

Specs may choose classes/functions, transaction/lock implementation, error types, and tests. They may not redefine command meanings, trusted Governance seams, explicit continuity-determination rules, operative-state requirement, correction semantics, actor/provenance separation, or historical queries.
