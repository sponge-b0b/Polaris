# Application Use Cases for Investment Decision Lifecycle

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `application-use-cases`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define the R2 application command/query contracts, continuity arbitration, transaction boundaries, idempotency, concurrency behavior, actor/provenance handling, temporal correction, and cross-entity seams for Investment Decision lifecycle truth.

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

Names are not prescribed APIs. Semantics are.

---

# 2. Command envelope

Every mutating use case receives semantic input equivalent to:

```text
operation_id
actor_context / actor_attribution input where applicable
trigger_provenance
technical_correlation metadata
business effective time or clock-derived effective time
expected version(s) when mutating existing Decisions
command-specific payload
```

The application must keep these meanings separate:

- Actor Attribution = who formed/performed a material domain act;
- trigger provenance = what caused work to begin;
- technical provenance = request/model/work/provider correlation.

A user request can trigger a Polaris-attributed Decision Need determination. Model/provider/work IDs are never Actor Attribution by convenience.

---

# 3. Initiation and continuity arbitration

## 3.1 Initiation inputs

A new Decision requires:

- Decision Need statement/basis;
- Decision Subject;
- Scope representation that may be unresolved/partial;
- Actor Attribution for the Decision Need determination where material;
- trigger provenance;
- operation ID.

## 3.2 Continuity preflight

Before automatic creation, Application asks the Decision Memory/persistence port for conservative unresolved, operative candidate Decisions.

For R2, the conservative set MAY be all unresolved, non-superseded Decisions rather than an unproven semantic matching heuristic.

Application derives one explicit outcome:

```text
CONTINUE_EXISTING(decision_id)
CREATE_NEW
AMBIGUOUS(candidate_ids)
```

`AMBIGUOUS` creates no new Decision automatically.

## 3.3 Atomic revalidation

If outcome is `CREATE_NEW`, commit must atomically verify that the continuity candidate basis observed by the use case has not changed incompatibly.

If it changed, return `ContinuityConflict` and require re-evaluation. Do not commit a second Decision and repair later by default.

The initial PostgreSQL adapter may serialize initiation broadly if that is the smallest correct mechanism.

## 3.4 Explicit continuation

A caller/use case that already knows the unresolved Decision being continued uses explicit identity and expected-version semantics rather than rediscovering identity from Subject/Scope.

---

# 4. Scope and Subject changes

`establish_or_revise_scope`:

- accepts zero-or-more confirmed Portfolio references + completeness state;
- preserves unresolved/partial state explicitly;
- requires expected version;
- emits immutable Scope fact;
- does not change Decision identity merely because Scope changes.

`revise_subject` similarly preserves history and applies the same-choice invariant. If a proposed Subject change would actually describe an independently resolvable choice, application must reject/route to new-Decision determination rather than silently mutate identity.

---

# 5. Human Deferral seam

Deferral is not a generic Decisions command that any caller may self-assert.

`apply_human_deferral` requires a trusted reference to an attributable Human Investment Decision owned by Governance (or deterministic trusted fixture in R2 tests).

Application:

1. validates trusted basis category/reference shape;
2. loads current Decision/version;
3. verifies lifecycle disposition is unresolved and operation is semantically valid;
4. invokes Decisions behavior producing `DecisionDeferred`;
5. persists only the Decisions-side consequence + basis reference;
6. does not copy Governance payload or infer authority.

An awaited condition associated with Deferral is stored as a Deferral/resumption basis. It is not a Review Condition.

---

# 6. Resume and withdrawal

## 6.1 Resume

`resume_decision_work` is valid for unresolved `DEFERRED` or `WITHDRAWN` work when the same coherent choice remains applicable and operative.

Inputs include:

- Decision ID;
- expected version;
- resumption basis (awaited condition satisfied, explicit human continuation, material event, or another allowed basis);
- Actor Attribution/provenance as applicable.

If the Decision is supportably superseded, resolved, externally resolved, or Need-retracted, ordinary resume fails.

## 6.2 Withdraw

`withdraw_decision_work` records that current work is stopped while the Decision Need remains unresolved.

It must not require or fabricate a Human Investment Decision. It must not become Deferral or resolution.

A later explicit continuation can resume the same Decision if continuity still holds.

---

# 7. Substantive resolution seam

`apply_substantive_resolution` requires a trusted resolution-basis reference, normally Governance-owned Human Investment Decision.

Application:

1. loads Decision/version;
2. checks supported lifecycle interpretation is determinately unresolved;
3. validates trusted basis category/reference;
4. records Decisions-side `DecisionSubstantivelyResolved` consequence;
5. does not infer Approval, authority sufficiency, Action Intent, or Recommendation acceptance;
6. returns committed Decision lifecycle result.

When Governance exists, a cross-owner use case may need a broader Unit of Work to atomically persist Governance-owned judgment and Decisions-owned consequence. R2 designs the seam but does not pre-build a platform-wide UoW without that owner present.

---

# 8. External Resolution

`apply_external_resolution` requires an attributable circumstance/basis that eliminated the Decision Need.

Application must distinguish:

- choice eliminated -> External Resolution;
- facts changed but same choice remains -> no External Resolution;
- original Need was unsupported -> Need retraction/correction instead.

If applicable prior lifecycle interpretation is contested, command fails closed unless the supplied basis/correction semantics resolve the ambiguity.

No Human Investment Decision is inferred.

---

# 9. Unsupported Decision Need retraction

`retract_unsupported_decision_need` records a correction that the Need determination itself was unsupported/erroneous.

It may occur after substantial work, including after a historical Human Investment Decision exists. Application must preserve all prior acts and append the correction.

This use case never deletes the Decision or pretends the prior human act did not occur.

---

# 10. Lifecycle correction

`record_lifecycle_correction` is an internal/privileged semantic use case for attributable correction of supported lifecycle interpretation.

It accepts:

- target Decision/fact/interpretation reference;
- correction kind;
- business effective time;
- correction basis/reference;
- Actor Attribution/provenance;
- expected version;
- operation ID.

Application must:

- preserve original fact;
- append correction;
- recompute supported current/effective interpretation;
- expose contested/indeterminate interpretation when competing supported facts cannot be reconciled deterministically;
- never use recorded order alone as semantic precedence.

Arbitrary interfaces must not gain a generic “rewrite lifecycle” endpoint.

---

# 11. Renewal

`renew_decision` creates a new Decision identity after one or more prior Decisions were supportably substantively or externally resolved and a new Decision Need now exists.

The operation atomically:

- performs normal new-Decision continuity arbitration;
- creates new Decision Need/Decision;
- establishes supported `RENEWED_FROM` edge(s);
- preserves all predecessors unchanged;
- prevents lifecycle-lineage cycles.

A corrected unsupported Need is not an eligible renewal predecessor merely because it once had work attached; any later genuine Need follows normal causality rules.

---

# 12. Supersession

`establish_supersession` may:

- create a new successor and one/many `SUPERSEDES` edges in one command; or
- establish one/many supported Supersession edges among existing Decisions when the relationship is learned/authorized later.

Rules:

- target may be unresolved or resolved;
- target lifecycle disposition is not changed;
- unresolved supported target becomes non-operative for automatic continuity selection;
- many-to-many is allowed;
- all requested edge creation for one semantic command is atomic;
- cycle check uses supported lifecycle-lineage graph;
- contested graph support causes fail-closed behavior if cycle safety cannot be determined.

---

# 13. Transaction boundaries

A command reports success only after all business facts/receipts required for that command durably commit.

Examples:

```text
ordinary mutation:
  lifecycle fact/correction
  + current projection/version
  + idempotency receipt

new initiation:
  continuity revalidation
  + Decision Need
  + Investment Decision
  + DecisionInitiated
  + optional lineage relationships
  + receipt

multi-target supersession:
  all relationship facts
  + operative projections/guards as needed
  + receipt
```

No partial semantic success is visible.

Long external/model calls are not part of R2; future use cases follow R1 rule to run them outside durable-store transactions and revalidate before commit.

---

# 14. Expected-version concurrency

Every existing-Decision mutation supplies expected version or equivalent compare-and-set guard.

Stale version -> explicit concurrency conflict; no partial fact is committed.

Relationship commands touching multiple Decisions require sufficient guards to prevent stale semantic decisions.

Expected version does not replace initiation continuity arbitration.

---

# 15. Idempotency

Each retryable command has operation-specific idempotency identity.

Rules:

- same operation + same semantic request -> original semantic result;
- same operation + different semantic request -> `IdempotencyConflict`;
- crash after durable commit before response -> replay returns committed result;
- different operation IDs can still race and are handled by continuity/concurrency semantics.

Decision ID is not a universal idempotency key.

---

# 16. Query semantics

## 16.1 Current Decision view

Returns:

- identity/Need/Subject/Scope;
- determinate supported lifecycle disposition or contested interpretation;
- work posture when applicable;
- current version;
- supported operative/Supersession summary;
- references, not duplicated payloads, for external owner facts.

## 16.2 `as_known_at`

Returns the lifecycle/history supported using only facts/corrections recorded by cutoff K.

## 16.3 `effective_at`

Returns the lifecycle interpretation effective at business time T under a specified knowledge cutoff K, defaulting to current knowledge when omitted.

## 16.4 History

Returns raw immutable facts/corrections in recorded order plus enough typed relationships to explain supported interpretation. It must not hide disconfirmed historical facts merely because the current projection changed.

## 16.5 Lineage

Returns typed renewal/Supersession relationships with recorded/effective time and correction/support status.

---

# 17. Semantic outcomes/errors

Application callers must be able to distinguish:

```text
NotFound
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

Concrete names are optional; semantic distinctions are not.

---

# 18. R2 application tests

Required deterministic-fake tests include:

- initiate with unresolved Scope;
- candidate continuity returns continue/new/ambiguous;
- two different operation IDs racing cannot silently create duplicate choice;
- Scope establishment/revision preserves ID;
- Deferral rejected without trusted Human Investment Decision basis;
- awaited Deferral condition is not a Review Condition;
- withdrawn work can resume same unresolved Decision;
- substantive resolution uses trusted basis but does not infer authority;
- External Resolution vs unsupported Need correction distinguished;
- unsupported Need correction preserves prior human act references;
- resolved target may be superseded without lifecycle mutation;
- many-target Supersession atomic;
- late lifecycle correction preserves as-known-at history;
- competing corrections expose contested interpretation;
- idempotent retry returns original result;
- stale expected version creates no partial state;
- actor, trigger, and technical provenance remain separate.

---

# 19. R2 exclusions

Application R2 does not introduce:

- Attention service;
- Evidence assembly;
- model orchestration;
- Governance implementation;
- human-facing arbitrary trusted-basis injection;
- Action Continuity;
- generic event bus/workflow runtime;
- generic graph service;
- platform-wide repository/UoW framework.

---

# 20. Spec-readiness rule

Specs may choose class/function names, transaction implementation, error types, concrete continuity-lock algorithm, and test organization.

Specs may not redefine the command meanings, trusted Governance seams, continuation fail-closed rule, lifecycle correction behavior, actor/provenance separation, or historical query semantics established here.
