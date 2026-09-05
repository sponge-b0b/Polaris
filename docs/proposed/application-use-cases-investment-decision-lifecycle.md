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

## 3.1 Inputs and one-Need/one-Decision integrity

New initiation includes a **new Decision Need identity**, Need statement/basis, Subject, Scope representation (possibly unresolved/partial), Actor Attribution where material, trigger provenance, operation ID, and an explicit continuity determination when unresolved operative candidates exist.

Every committed Investment Decision references exactly one Decision Need, and one Decision Need may ground at most one Investment Decision. A repeated trigger routed to `CONTINUE_EXISTING` does not create another Need merely to represent the repeated request.

## 3.2 Candidate discovery

Application queries conservative unresolved operative candidates. R2 may treat all unresolved non-superseded Decisions as candidates rather than inventing similarity.

## 3.3 Determination contract

```text
CONTINUE_EXISTING(decision_id)
CREATE_NEW
AMBIGUOUS(candidate_ids)
```

- no candidates: `CREATE_NEW` may be selected automatically, subject to revalidation;
- candidates exist: initiating caller/use case explicitly determines continue or create-new after considering them;
- missing/stale/contradictory determination -> `AMBIGUOUS`, no creation;
- R2 has no hidden ranking/matching heuristic;
- later Attention may automate this contract but must preserve attributable basis.

When `CREATE_NEW` commits, initiation history preserves determination kind, candidate IDs materially considered, actor/basis/rationale for explicit create-new, and the candidate knowledge cutoff/guard used for commit revalidation.

If `CONTINUE_EXISTING`, no duplicate Decision Need/Decision is created merely for the repeated trigger; later Attention/Evidence/Context owners may preserve the trigger contribution under their own semantics.

## 3.4 Atomic revalidation

`CREATE_NEW` commits only if observed candidate basis remains compatible. Changed basis -> `ContinuityConflict` and re-evaluation. PostgreSQL may serialize initiation broadly for R2 correctness.

---

# 4. Scope and Subject

Scope mutation accepts zero-or-more confirmed Portfolio refs + completeness (`UNRESOLVED`/`ESTABLISHED`) and preserves history.

Validation:

- `UNRESOLVED` may contain zero or more confirmed Portfolio refs;
- `ESTABLISHED` requires at least one Portfolio;
- no sentinel/default Portfolio identity stands for unresolved Scope.

Subject refinement preserves identity only while the same coherent choice remains; an independently resolvable choice routes to continuity/new-Decision determination.

Ordinary Subject/Scope work requires lifecycle determinately `UNRESOLVED` and operative applicability determinately operative. Historical correction uses explicit correction path.

---

# 5. Human Deferral seam

Deferral requires typed trusted upstream basis, normally Governance-owned Human Investment Decision with effect `DEFERRING`.

Application validates basis, loads Decision/version + operative state, requires lifecycle `UNRESOLVED`, permits Deferral from `ACTIVE`, `WITHDRAWN`, or already `DEFERRED`, appends `DecisionDeferred`, and stores only Decisions-side consequence + basis reference.

Re-Deferral requires a new attributable Human Investment Decision basis and appends history; posture remains `DEFERRED`.

Awaited Deferral condition is not a Review Condition.

---

# 6. Resume and withdrawal

Resume requires lifecycle determinately `UNRESOLVED`, operative status determinately operative, posture `DEFERRED` or `WITHDRAWN`, expected version, and same-choice resumption basis.

Withdrawal records work-control stop without Human Investment Decision or lifecycle resolution; valid from `ACTIVE` or `DEFERRED` while unresolved/operative.

If Supersession support makes operative status contested, ordinary resume/defer/withdraw/Subject/Scope/substantive-resolution work fails closed with an explicit contested-applicability outcome.

---

# 7. Substantive resolution seam

Requires lifecycle determinately `UNRESOLVED`, Decision determinately operative, and typed trusted upstream basis with semantic effect `SUBSTANTIVELY_RESOLVING`.

Application records Decisions-side resolution consequence only; it does not infer Approval, authority sufficiency, Recommendation acceptance, or Action Intent.

A deliberate hold/no-action Human Investment Decision may have resolving effect. Recommendation rejection alone has no fixed lifecycle effect: rejection that asks for further judgment leaves the Decision unresolved, while a rejection that substantively disposes of the underlying choice may resolve it. The trusted upstream basis explicitly states the effect.

A late-discovered historical Human Investment Decision whose effective ordering changes supported lifecycle interpretation enters through `record_lifecycle_correction`, not an ordinary forward transition.

---

# 8. External Resolution

If current supported lifecycle is determinately `UNRESOLVED`, `apply_external_resolution` records ordinary External Resolution when attributable circumstance eliminated the Need.

If another lifecycle disposition is already recorded and later information establishes earlier External Resolution, Application uses the append-only correction path rather than rejecting the fact or rewriting history.

Changed Evidence/Portfolio State/alternatives alone is insufficient while the same choice exists. No Human Investment Decision is inferred.

---

# 9. Unsupported Need retraction

`retract_unsupported_decision_need` is corrective and may apply regardless of previously supported lifecycle disposition when attributable evidence establishes that original Need itself was unsupported.

It appends correction/retraction, preserves all prior acts, and recomputes supported lifecycle interpretation. It never deletes or retroactively converts a prior act.

---

# 10. Lifecycle correction

`record_lifecycle_correction` is internal/privileged. Inputs include target fact/interpretation, correction kind, effective time, trusted basis, Actor Attribution/provenance, expected version, operation ID.

It preserves original fact, appends correction, recomputes supported interpretation, and exposes contested/indeterminate state when typed semantics cannot reconcile competing support. Recorded order alone never gives precedence.

No generic public “set lifecycle status” path is allowed.

---

# 11. Renewal

Creates a new Decision after one/more prior Decisions were supportably substantively or externally resolved and a **new Decision Need** exists.

Performs normal initiation continuity arbitration, persists its continuity basis, creates the new Need/Decision, establishes supported `RENEWED_FROM` edge(s), and rejects lineage cycles. Predecessors remain unchanged.

---

# 12. Supersession

May create successor + one/many edges or establish edges among existing Decisions.

Target may be unresolved/resolved; lifecycle unchanged; unresolved supported target becomes non-operative; many-to-many allowed; one semantic command atomic; cycle check uses currently supported lineage; contested edge support fails closed when cycle/operative safety cannot be established.

---

# 13. Transaction boundaries

```text
ordinary mutation:
  lifecycle fact/correction
  + current projection/version
  + receipt

new initiation:
  continuity determination + durable candidate basis
  + atomic candidate-basis revalidation
  + new Decision Need + Investment Decision + DecisionInitiated
  + optional lineage edges
  + receipt

relationship command:
  all requested relationships
  + operative projections/guards as needed
  + receipt
```

No partial semantic success. Initiation must also enforce one-Need/one-Decision uniqueness atomically.

---

# 14. Concurrency and idempotency

Existing-Decision mutation uses expected version/CAS. Stale version commits nothing.

Same operation + same request replays result. Same operation + different request conflicts. Different operation IDs still require continuity protection.

Relationship commands touching several Decisions require sufficient guards on all semantically affected state.

---

# 15. Query semantics

Current view returns identity/Need/Subject/Scope, determinate lifecycle or contested interpretation, work posture if applicable, version, determinate/contested operative applicability, Supersession summary, and external-owner references.

`as_known_at(K)` means the Decision state **effective at K using only knowledge recorded by K**—equivalent to `effective_at(K, known_at=K)`. A fact known by K but effective later does not prematurely change the state at K.

`effective_at(T, known_at=K)` applies effective times/corrections using only knowledge available by K.

History returns raw immutable facts/corrections + typed support relationships and initiation continuity basis; it never hides disconfirmed historical facts.

Lineage returns typed renewal/Supersession edges with effective/recorded time and correction/support status.

---

# 16. Semantic outcomes

Callers distinguish at least:

```text
NotFound
DecisionNeedAlreadyGrounded
DecisionNonOperative
DecisionOperativeStatusContested
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

- unresolved Scope initiation;
- empty `ESTABLISHED` Scope rejected;
- one Need cannot ground two Decisions;
- repeated continuation creates neither new Decision nor new Need;
- no candidates -> create + persist `NO_CANDIDATES` basis;
- candidates + explicit continue -> no new identity;
- candidates + explicit create -> persist candidate IDs + attributable rationale;
- candidates + missing/contradictory determination -> ambiguity/no creation;
- different-operation race -> no silent duplicate;
- Scope refinement preserves ID;
- Deferral requires trusted deferring basis;
- re-Deferral appends fact;
- awaited condition != Review Condition;
- deliberate hold/no-action may resolve; rejection requesting more judgment remains unresolved;
- withdrawal/resume same identity;
- supportably superseded unresolved Decision rejects ordinary work;
- contested operative applicability also rejects ordinary work;
- substantive resolution requires trusted resolving basis;
- ordinary vs late External Resolution paths distinguished;
- unsupported Need retraction allowed after prior resolution/human acts;
- resolved target superseded without lifecycle mutation;
- many-target Supersession atomic;
- `as_known_at` does not apply later-recorded or future-effective facts prematurely;
- competing corrections -> contested interpretation;
- actor/trigger/technical provenance remain separate.

---

# 18. R2 exclusions / Spec gate

No Attention service, Evidence assembly, model orchestration, Governance implementation, arbitrary trusted-basis injection, Action Continuity, generic event/workflow runtime, generic graph service, or platform-wide UoW framework.

Specs may choose classes/functions, transaction/lock implementation, error types, and tests. They may not redefine command meanings, Need/Decision cardinality, Scope completeness, durable continuity-determination provenance, operative-state guard, trusted Governance seams, correction semantics, actor/provenance separation, or historical query semantics.
