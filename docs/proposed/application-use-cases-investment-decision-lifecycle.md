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
- [`investment-decisions-r2-foundation-public-contract.md`](investment-decisions-r2-foundation-public-contract.md);
- [`durable-persistence-investment-decision-history.md`](durable-persistence-investment-decision-history.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- proposed [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md).

The owner-approved foundation public-contract document explicitly resolves the foundation blockers that existed when this application design was first written. Where historical wording below conflicts with that completion authority, the completed foundation contract controls.

Application coordinates owner behavior; it does not create a second domain model.

The later owner-approved [R2 lifecycle correction support contract](investment-decisions-r2-lifecycle-correction-support-contract.md) controls lifecycle-disposition correction and temporal interpretation. Application supplies current observation time and trusted command recording time; every public lifecycle interpretation exposes `(effective_at=T, known_at=K)`. Unknown-at-K is not found, while a known Decision with zero effective positive claims is `NOT_YET_EFFECTIVE`, with no effective support or work posture. Commands reconstruct at their recording boundary and consume the domain's append-time validation, branch-local compatibility, and exact surviving support rules.

Every distinct valid attributable lifecycle correction act appends, even when its claim is equivalent; exact operation/request replay is the only correction append no-op, and changed-request reuse conflicts through Application/persistence receipts. Compare preceding and appended history at the same recording boundary to determine the version consequence, including support-only changes. Future-only append may retain version, and clock/query execution creates no version. These rules supersede older two-state temporal-result and unconditional correction-version shorthand below. Corrections bypass the ordinary work gate but retain correction-specific eligibility; #296 does not implement Subject/Scope/work-posture correction or a domain receipt framework.

The owner-approved [Investment Decision Relationship Model](investment-decisions-decision-relationship-model.md) now controls R2 renewal/Supersession relationship correction, four-state support interpretation, historical admission, same-command correction ancestry, relationship-driven `DecisionVersion`, distinct attributable acts versus replay, and temporal graph-admission semantics. Application consumes that authority; it does not implement another reducer. In particular, relationship validity established at admission is not silently rewritten by later endpoint lifecycle change, while current work/applicability consumers still evaluate current lifecycle independently. Relationship version checks are necessary but not sufficient: Application must transactionally revalidate every material history, ancestry, graph path, future-effective fact, and absence predicate relied upon through commit.

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
record_relationship_correction
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
actor_context / known actor attribution for a new attributable act
trigger_provenance
optional technical_provenance
business effective time or clock-derived effective time
expected version(s) when mutating existing Decisions
command-specific payload
```

Actor Attribution, Trigger Provenance, and Technical Provenance remain separate. Every committed Decisions fact has one semantic Trigger Provenance. Technical Provenance is optional and may be empty. Ordinary live commands establishing a new attributable act require known Actor Attribution; historical reconstruction/correction may preserve unknown or contested attribution when that is the truthful supported state.

## 2.1 Opaque identity allocation

Application consumes the completed foundation identity contract:

```text
InvestmentDecisionId       -> distinct UUID-backed domain identity, UUIDv4
DecisionNeedId             -> distinct UUID-backed domain identity, UUIDv4
DecisionLifecycleFactId    -> distinct UUID-backed domain identity, UUIDv4
DecisionRelationshipFactId -> distinct UUID-backed domain identity, UUIDv4
OperationId                -> distinct UUID-backed application-operation identity, UUIDv4
PortfolioId                -> distinct UUID-backed Portfolio identity, UUIDv4
ActorId                    -> distinct UUID-backed actor identity, UUIDv4
```

For `CREATE_NEW`, the application initiation boundary allocates fresh Decision Need and Investment Decision UUIDv4 values independently of Subject, Scope, Portfolio State, continuity candidates, workflow/job/model/report identity, persistence row identity, or any other business/technical content. Those typed values are supplied to the domain transition; the domain does not derive them.

`OperationId` is an opaque idempotency/correlation identity for one semantic application operation. Its UUID value carries no business meaning. A retry/replay of the **same semantic operation** reuses the same `OperationId`; a distinct operation uses a distinct value. Same-operation request equivalence remains determined by the semantic request fingerprint/contract, not by interpreting UUID contents.

Identity generation does not replace transactional uniqueness, continuity, or idempotency enforcement.

---

# 3. Initiation and continuity arbitration

## 3.1 Inputs and one-Need/one-Decision integrity

New initiation includes a **new Decision Need identity**, non-empty Need statement, Subject, Scope representation (possibly unresolved/partial), known Actor Attribution, one Trigger Provenance, optional Technical Provenance, Operation ID, and an explicit continuity determination when unresolved operative candidates exist.

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

When `CREATE_NEW` commits, initiation history preserves determination kind, candidate IDs materially considered, actor/rationale for explicit create-new, and the candidate knowledge cutoff used for commit revalidation. Persistence-specific lock/guard tokens remain adapter/receipt mechanics rather than domain lifecycle provenance.

If `CONTINUE_EXISTING`, no duplicate Decision Need/Decision is created merely for the repeated trigger; later Attention/Evidence/Context owners may preserve the trigger contribution under their own semantics.

## 3.4 Atomic revalidation

`CREATE_NEW` commits only if observed candidate basis remains compatible. Changed basis -> `ContinuityConflict` and re-evaluation. PostgreSQL may serialize initiation broadly for R2 correctness.

---

# 4. Scope and Subject

Scope mutation accepts zero-or-more canonical `PortfolioId` values + completeness (`UNRESOLVED`/`ESTABLISHED`) and preserves history.

Validation:

- membership is unique and semantically unordered;
- `UNRESOLVED` may contain zero or more confirmed `PortfolioId` values;
- `ESTABLISHED` requires at least one `PortfolioId`;
- no sentinel/default Portfolio identity stands for unresolved Scope;
- `UNRESOLVED -> UNRESOLVED` changed membership is Scope revision;
- `UNRESOLVED -> ESTABLISHED` is Scope establishment;
- `ESTABLISHED -> ESTABLISHED` changed membership is Scope revision;
- `ESTABLISHED -> UNRESOLVED` is invalid ordinary mutation and requires correction if prior establishment was erroneous;
- semantically identical Scope is a no-op.

`DecisionSubject` is the completed immutable non-empty statement contract. Subject revision preserves identity only while the same coherent choice remains; an independently resolvable choice routes to continuity/new-Decision determination. Semantically identical Subject is a no-op.

Ordinary Subject/Scope work requires lifecycle determinately `UNRESOLVED` and operative applicability determinately operative. Historical correction uses explicit correction path.

The former foundation blockers are resolved by `investment-decisions-r2-foundation-public-contract.md` and certified #299 implementation. Application must consume the frozen Subject, `PortfolioId`, unordered Scope, Actor Attribution, Trigger/Technical Provenance, purpose-specific basis/reference, lifecycle sequence/version/time, error, and construction/reconstruction contracts rather than redefining them.

---

# 5. Human Deferral seam

Deferral requires a purpose-specific trusted upstream basis, normally a Governance-owned canonical Human Investment Decision with semantic effect `DEFERRING`.

When the basis is a Human Investment Decision, Application treats it as an already-valid authority-bearing upstream fact: Governance established it only after the applicable Investment Authority Regime confirmed the attributable actor possessed the required power for the act's subject, Portfolio scope, conditions, and authority-effective time. Analytical/advisory judgment and unauthorized attempted authority acts cannot satisfy this seam. Application/Decisions does not infer or manufacture that authority fact.

Application validates the typed basis contract, loads Decision/version + operative state, requires lifecycle `UNRESOLVED`, permits Deferral from `ACTIVE`, `WITHDRAWN`, or already `DEFERRED`, appends `DecisionDeferred`, and stores only Decisions-side consequence + basis reference.

Re-Deferral requires a new valid trusted deferring basis and appends history; posture remains `DEFERRED`.

Awaited Deferral condition is not a Review Condition.

---

# 6. Resume and withdrawal

Resume requires lifecycle determinately `UNRESOLVED`, operative status determinately operative, posture `DEFERRED` or `WITHDRAWN`, expected version, and same-choice resumption basis.

Withdrawal records work-control stop without Human Investment Decision or lifecycle resolution; valid from `ACTIVE` or `DEFERRED` while unresolved/operative.

If Supersession support makes operative status contested, ordinary resume/defer/withdraw/Subject/Scope/substantive-resolution work fails closed with an explicit contested-applicability outcome.

---

# 7. Substantive resolution seam

Requires lifecycle determinately `UNRESOLVED`, Decision determinately operative, and purpose-specific trusted upstream basis with semantic effect `SUBSTANTIVELY_RESOLVING`.

When the resolving basis is a Human Investment Decision, it must be the already-valid canonical Governance authority fact described in Section 5. Application records the Decisions-side resolution consequence only; it does not infer Approval, authority sufficiency, Recommendation acceptance, or Action Intent.

A deliberate hold/no-action Human Investment Decision may have resolving effect. Recommendation rejection alone has no fixed lifecycle effect: rejection that asks for further judgment leaves the Decision unresolved, while a rejection that substantively disposes of the underlying choice may resolve it. The trusted upstream basis explicitly states the effect.

A late-discovered historical Human Investment Decision whose effective ordering changes supported lifecycle interpretation enters through `record_lifecycle_correction`, not an ordinary forward transition. Historical validity is evaluated using the authority regime that actually applied when the upstream authority fact occurred; later revocation does not retroactively invalidate a then-valid Human Investment Decision.

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

`record_lifecycle_correction` is internal/privileged. Inputs include target fact/interpretation, correction kind, effective time, typed trusted basis, truthful Actor Attribution, Trigger Provenance, optional Technical Provenance, expected version, and Operation ID.

It preserves original fact and appends a correction with a new `DecisionLifecycleFactId` and next `DecisionLifecycleSequence`. `DecisionVersion` advances only when the frozen lifecycle current-interpretation comparison at the command's trusted recording boundary requires it; a distinct valid correction may therefore append while leaving the version unchanged when it affects only historical/future interpretation. Recorded order alone never gives precedence, and typed semantic conflict yields contested interpretation rather than newest-write-wins.

No generic public “set lifecycle status” path is allowed.

---

# 11. Renewal

Ordinary renewal creates a new Decision after one/more prior Decisions were supportably substantively or externally resolved and a **new Decision Need** exists.

Application performs normal initiation continuity arbitration, persists its continuity basis, creates the new Need/Decision, and proposes one/more `RENEWED_FROM` relationship facts with explicit renewal bases.

For each predecessor, admission must establish substantive/external resolution under command knowledge both when the source's new judgment episode begins and at the relationship claim's effective instant. The relationship cannot predate the new episode. Each predecessor is checked independently.

A later attributable assertion of genuinely omitted renewal lineage may target the already-established source Decision/Need without recreating or reopening either identity when those same historical predicates and an explicit renewal basis are proven.

Predecessor identity, Need, lifecycle disposition/work history, and immutable facts remain unchanged. Its `DecisionVersion` may nevertheless advance when the protected incoming renewal interpretation changes.

Later endpoint lifecycle correction does not silently invalidate or rewrite the admitted renewal relationship. If later knowledge requires relationship-semantic change, use explicit relationship correction. Current lifecycle/applicability may independently affect downstream work under its current-time rules.

---

# 12. Supersession and relationship correction

Supersession may create successor + one/many edges or establish edges among existing Decisions. Positive relationship claims are admitted using the historical endpoint eligibility contract in the relationship model rather than ordinary current unresolved/operative work gates.

For incoming Supersession groups:

- `SUPPORTED` contributes its effective edge; an unresolved target is non-operative for ordinary work;
- relevant `CONTESTED` support makes applicability contested even alongside clean support;
- `WITHDRAWN` and `NOT_EFFECTIVE` contribute no positive current edge;
- renewal alone has no Supersession effect.

`record_relationship_correction` preserves immutable history and accepts purpose-specific `QUALIFY`/`DISCONFIRM` correction acts. A correction targets exactly one committed or valid same-command base/correction fact in the same lineage. Same-command target ancestry is an explicit acyclic dependency chain; request-list, insertion, UUID, and timestamp order grant no semantic precedence.

`QUALIFY` supplies a complete replacement positive claim with its own relationship basis plus a separate correction basis and distinct correction/replacement effective instants. `DISCONFIRM` supplies no replacement positive and carries its correction basis. Recursive disconfirmation can restore the immediately preceding positive/qualification/withdrawal interpretation; sibling branches remain independent.

Application consumes the domain's exact `SUPPORTED | CONTESTED | WITHDRAWN | NOT_EFFECTIVE` combined interpretation, complete support-ID membership, and role-associated bases. It does not reduce raw facts independently or infer positive edges from explanatory support.

Every distinct valid attributable relationship assertion/correction appends a fresh fact even when equivalent to existing support. Exact same-operation/same-request replay is the only append no-op; same-operation/different-request reuse conflicts.

Temporal graph admission is evaluated against the complete proposed post-command relationship history across every materially distinct historical and known-future topology interval. Supported edges plus all surviving positive possibilities under contest must be acyclic for the mixed `RENEWED_FROM`/`SUPERSEDES` graph. Definite cycles and cycles possible only under contest have distinct typed rejection semantics. An atomic correction batch may repair relationships together when its complete final history passes; no intermediate insertion order is a public graph state. Ticket #298 owns enforcement implementation; Application coordinates the command/transaction around the frozen predicate.

---

# 13. Transaction boundaries

```text
ordinary mutation:
  lifecycle fact/correction
  + current projection/version when required by current-interpretation comparison
  + receipt

new initiation:
  continuity determination + durable candidate basis
  + atomic candidate-basis revalidation
  + new Decision Need + Investment Decision + DecisionInitiated
  + optional lineage edges
  + relationship graph/admission validation when edges exist
  + receipt

relationship command:
  complete atomic set of requested relationship facts/corrections
  + same-command target-ancestry validation
  + historical endpoint/relationship admission validation
  + complete known-timeline graph certification
  + protected endpoint version updates when current relationship interpretation changes
  + transactional protection/revalidation of all materially read histories, ancestry, paths, future facts, and absence predicates
  + receipt
```

No partial semantic success. Initiation must also enforce one-Need/one-Decision uniqueness atomically.

Tentative same-command validation stages are never public/durable. A command either commits its complete semantic result or commits nothing.

---

# 14. Concurrency and idempotency

Existing directly touched pre-existing Decisions require expected-version checks even when the proposed relationship act would not itself advance their versions. Stale version commits nothing.

Relationship-driven version comparison protects both source and target current incident relationship interpretation: group state, surviving effective claims/effective instants, complete support IDs, and role-associated bases. Support/basis-only current changes count; raw append count does not. A Decision touched by several lifecycle/relationship changes advances at most once for the atomic command. New Decisions start at version 1 including same-command initial relationships. Relationship mutation never advances `DecisionLifecycleSequence`.

Version equality is necessary but insufficient. Before commit, Application/persistence must establish against authoritative committed knowledge that every material endpoint/admission history, relationship fact/correction ancestry, potential return path, and absence predicate relied on remains valid. This includes same-group/cross-group changes, non-endpoint path changes, and future/history-only facts that may not advance any endpoint version. Failed predicate revalidation commits nothing and returns explicit semantic concurrency/relationship conflict.

Physical locking, snapshot/isolation, serialization, or equivalent coordination is adapter-owned; observable correctness must equal validation against the complete applicable committed predecessor state at the final trusted recording boundary followed by atomic commit.

Same operation + same semantic request replays the stored result without append/version. Same operation + different semantic request conflicts. A different operation is a distinct act and still passes every admission/concurrency rule.

Both-endpoint support-sensitive versioning intentionally accepts higher optimistic-concurrency contention to preserve complete relationship meaning. If contention becomes significant, optimize coordination/transaction mechanics rather than weakening protected endpoint/support/basis semantics.

---

# 15. Query semantics

Current view returns identity/Need/Subject/Scope, determinate lifecycle or contested interpretation, work posture if applicable, version, determinate/contested operative applicability, Supersession summary, and external-owner references.

`as_known_at(K)` means the Decision state **effective at K using only knowledge recorded by K**—equivalent to `effective_at(K, known_at=K)`. A fact known by K but effective later does not prematurely change the state at K.

`effective_at(T, known_at=K)` applies effective times/corrections using only knowledge available by K.

History returns raw immutable facts/corrections + typed support relationships and initiation continuity basis; it never hides disconfirmed historical facts.

Lineage/relationship reads preserve exact `(T,K)`, relationship group identity, `SUPPORTED | CONTESTED | WITHDRAWN | NOT_EFFECTIVE`, surviving positive claims/effective instants, complete support IDs, role-associated bases, and not-found/invalid-history distinctions. Explanatory support is not silently converted into a graph edge. Traversal uses supported edges unless a consumer explicitly performs the conservative contested-possibility graph-safety projection.

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
RelationshipCycleSafetyIndeterminate
RelationshipHistoryInvalidOrIncomplete
RelationshipInterpretationContested
LifecycleInterpretationContested
PersistenceUnavailable
```

Concrete application outcome names are optional. Domain failures use the completed `InvestmentDecisionError` hierarchy; Application translates domain/persistence/concurrency outcomes at its boundary rather than exposing persistence exceptions.

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
- Scope revision preserves ID and obeys establishment/revision/no-op transitions;
- Deferral requires valid trusted deferring basis;
- analytical/advisory judgment or unauthorized authority attempt cannot masquerade as Human Investment Decision basis;
- re-Deferral appends fact;
- awaited condition != Review Condition;
- deliberate hold/no-action may resolve; rejection requesting more judgment remains unresolved;
- withdrawal/resume same identity;
- supportably superseded unresolved Decision rejects ordinary work;
- contested operative applicability also rejects ordinary work;
- substantive resolution requires valid trusted resolving basis;
- ordinary vs late External Resolution paths distinguished;
- unsupported Need retraction allowed after prior resolution/human acts;
- resolved target superseded without lifecycle mutation;
- many-target Supersession atomic;
- relationship correction preserves original fact, supports recursive correction/restoration, and can yield contested support;
- renewal admission proves predecessor resolution at new-episode start and relationship effective instant; late omitted lineage is historical attachment rather than identity recreation;
- later endpoint lifecycle correction does not silently rewrite an admitted relationship while current work/applicability may change independently;
- same-command relationship correction ancestry is explicit/acyclic and independent of request-list/insertion/timestamp order;
- `QUALIFY` preserves distinct correction and replacement effective instants and distinct correction/relationship bases;
- exact four-state relationship interpretation and complete support/basis association are consumed without an application-side reducer;
- distinct equivalent relationship acts append; exact replay appends nothing; changed-request OperationId reuse conflicts;
- support/basis-only current relationship changes can advance both endpoint versions; future-only unchanged-current facts may not;
- complete historical/known-future graph validation rejects definite or possible cycles and permits acyclic contest;
- atomic correction batch can repair several relationships with no visible intermediate graph state;
- concurrent path/future/absence change is rejected even if expected endpoint versions still match;
- `as_known_at` does not apply later-recorded or future-effective facts prematurely;
- competing lifecycle corrections -> contested interpretation;
- Actor Attribution, Trigger Provenance, and Technical Provenance remain separate.

---

# 18. R2 exclusions / Spec gate

No Attention service, Evidence assembly, model orchestration, Governance implementation, arbitrary trusted-basis injection, Action Continuity, generic event/workflow runtime, generic graph service, or platform-wide UoW framework.

The foundation, lifecycle-correction, and #297 relationship architecture blockers are resolved. Specs may choose classes/functions, transaction/lock implementation, private realization helpers, and test mechanics only when those choices preserve the completed foundation/lifecycle/relationship/application contracts. They may not redefine command meanings, Need/Decision cardinality, identity representation/generation, Scope semantics, durable continuity provenance, operative-state guards, trusted Governance seams, append-only lifecycle/relationship correction/support semantics, relationship admission/version/graph predicates, Actor/Trigger/Technical Provenance separation, historical query semantics, or public/domain contracts by implementation convenience.
