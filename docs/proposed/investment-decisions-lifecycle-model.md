# Investment Decision Lifecycle Model

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `investment-decisions`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define the R2 Investment Decision domain model precisely enough that implementation Specs do not invent lifecycle identity, continuity, temporal, correction, or cross-entity semantics.

## Authority

This design refines, but does not override:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`investment-decisions-r2-decision-kernel-component-boundaries.md`](investment-decisions-r2-decision-kernel-component-boundaries.md);
- [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md);
- [`investment-decisions-decision-relationship-model.md`](investment-decisions-decision-relationship-model.md);
- [`application-use-cases-investment-decision-lifecycle.md`](application-use-cases-investment-decision-lifecycle.md);
- [`durable-persistence-investment-decision-history.md`](durable-persistence-investment-decision-history.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- proposed [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md);
- [`../product/domain-model.md`](../product/domain-model.md) and [`../../CONTEXT.md`](../../CONTEXT.md);
- accepted ADRs under [`../adr/`](../adr/).

`legacy/v0_1/` is not lifecycle authority.

---

# 1. Design objective

R2 establishes one durable Investment Decision identity for one coherent unresolved Portfolio-relevant choice and preserves its history when Scope is unresolved/refined, work is active/deferred/withdrawn/resumed, judgment or circumstances resolve the Need, the Need is later shown unsupported, another Decision supersedes applicability, renewed judgment creates a new Decision, or retry/restart/concurrency/late facts occur.

Investment Decision identity is never derived from workflow/job/report/model/database identity.

---

# 2. Core identities

## Investment Decision and Decision Need

An Investment Decision has opaque durable identity, **exactly one** grounding Decision Need, current Subject/Scope view, supported lifecycle interpretation, unresolved work posture when applicable, monotonic recorded domain version, and immutable creation time. Decision relationships are separate durable facts.

A Decision Need is the attributable determination that one coherent unresolved Portfolio-relevant choice warrants deliberate judgment. Preserve Need identity/statement, effective establishment time, recorded time, Actor Attribution where material, trigger provenance separately, and later correction without deleting original establishment.

Cardinality is deliberate:

```text
one Investment Decision -> exactly one Decision Need
one Decision Need       -> at most one Investment Decision
```

A repeated trigger that continues the same unresolved choice does not create another Decision Need merely to create another Decision identity. A genuinely new or renewed coherent choice requires a distinct Decision Need.

## Decision Subject

Subject identifies the matter being judged. It is required for coherent Decision identity but is not the Decision ID. Refinement preserves history and does not automatically create a new Decision.

## Decision Scope

Scope is:

```text
confirmed portfolio references: zero or more
scope completeness: UNRESOLVED | ESTABLISHED
```

Examples:

```text
[] + UNRESOLVED                 -> none established yet
[Portfolio A] + UNRESOLVED      -> A confirmed, applicability still incomplete
[A, B] + ESTABLISHED            -> applicability sufficiently established
```

Rules:

- `UNRESOLVED` may contain zero or more confirmed Portfolios;
- `ESTABLISHED` MUST contain at least one Portfolio;
- no fake/default Portfolio identity may represent unresolved Scope;
- final Capital-Relevant Recommendation or Human Investment Decision requires sufficiently established Portfolio applicability; initiation does not.

---

# 3. Three orthogonal concerns

## 3.1 Supported lifecycle disposition

When determinable:

```text
UNRESOLVED
SUBSTANTIVELY_RESOLVED
EXTERNALLY_RESOLVED
NEED_RETRACTED_UNSUPPORTED
```

- `UNRESOLVED`: Need remains supported and choice is not substantively or externally resolved.
- `SUBSTANTIVELY_RESOLVED`: choice was substantively disposed of through an attributable resolving basis, normally Governance-owned Human Investment Decision.
- `EXTERNALLY_RESOLVED`: circumstances eliminated the Need before substantive resolution; no Human Investment Decision is inferred.
- `NEED_RETRACTED_UNSUPPORTED`: later attributable correction establishes that the original Need determination itself was erroneous/unsupported.

The original Need/Decision history remains durable in every case.

## 3.2 Work posture

Meaningful only while lifecycle disposition is `UNRESOLVED` and the Decision is **determinately operative**:

```text
ACTIVE
DEFERRED
WITHDRAWN
```

- `ACTIVE`: work may proceed.
- `DEFERRED`: attributable Human Investment Decision postponed substantive judgment. Trusted human-decision basis required; awaited condition is not a Review Condition.
- `WITHDRAWN`: work stopped without investment judgment and without eliminating the Need.

A later human Deferral while already `DEFERRED` is valid when it is a new attributable Human Investment Decision; append another Deferral fact and keep posture `DEFERRED`.

## 3.3 Continuing applicability

`SUPERSEDES` is an orthogonal relationship. It may target unresolved or resolved Decisions and never replaces historical lifecycle disposition.

Operative applicability may itself be determinate or contested when relationship support is contested.

Ordinary resume, defer/re-defer, withdraw, Subject/Scope work, and substantive-resolution consequence commands require the Decision to be **determinately operative**. A supportably superseded or operatively contested Decision cannot receive normal work/judgment consequence mutations. Explicit lifecycle/relationship correction may still target historical Decisions.

---

# 4. Immutable lifecycle facts

Required semantics equivalent to:

```text
DecisionInitiated
DecisionSubjectRevised
DecisionScopeEstablished
DecisionScopeRevised
DecisionDeferred
DecisionWorkWithdrawn
DecisionWorkResumed
DecisionSubstantivelyResolved
DecisionExternallyResolved
DecisionNeedRetractedUnsupported
DecisionLifecycleCorrected
```

Every fact preserves fact/Decision identity, recorded sequence/version, kind, effective time, recorded time, operation ID, Actor Attribution where applicable, trigger/technical provenance separately, typed basis/reference, and correction target/reference where applicable.

### Initiation continuity payload

`DecisionInitiated` additionally preserves enough to reconstruct why a distinct Decision identity was created:

- continuity determination: `NO_CANDIDATES` or `EXPLICIT_CREATE_NEW` (or equivalent);
- unresolved operative candidate Decision IDs materially considered when non-empty;
- attributable continuity actor/basis/rationale when explicit create-new determination was required;
- candidate knowledge cutoff/observation-guard reference used for commit revalidation.

This is lifecycle provenance, not a universal `DecisionThread` entity.

Facts are immutable. Relationship facts (`RENEWED_FROM`, `SUPERSEDES`) are separate.

---

# 5. Normal transition and correction rules

| Current supported interpretation | Work | Operative? | Operation | Result | Required basis |
|---|---|---:|---|---|---|
| none | none | — | initiate | `UNRESOLVED + ACTIVE` | new Need + Subject + durable continuity determination; Scope may be unresolved |
| UNRESOLVED | any | yes | establish/revise Scope or Subject | same Decision/work | explicit revision fact |
| UNRESOLVED | ACTIVE/WITHDRAWN | yes | human defer | `DEFERRED` | trusted Deferral Human Investment Decision |
| UNRESOLVED | DEFERRED | yes | human re-defer | `DEFERRED` | new trusted Deferral Human Investment Decision; append fact |
| UNRESOLVED | DEFERRED/WITHDRAWN | yes | resume | `ACTIVE` | explicit same-choice resumption basis |
| UNRESOLVED | ACTIVE/DEFERRED | yes | withdraw work | `WITHDRAWN` | attributable work-control basis |
| UNRESOLVED | any | yes | substantive resolve | `SUBSTANTIVELY_RESOLVED` | trusted basis explicitly establishing resolving effect |
| UNRESOLVED | any | yes/no | ordinary newly observed External Resolution | `EXTERNALLY_RESOLVED` | attributable circumstance eliminating Need |
| any historical disposition | any | yes/no/contested | late External Resolution correction | supported interpretation may become `EXTERNALLY_RESOLVED` | append-only correction + external basis |
| any historical disposition | any | yes/no/contested | retract unsupported Need | supported interpretation may become `NEED_RETRACTED_UNSUPPORTED` | append-only attributable Need correction |
| any historical disposition | any | any | other lifecycle correction | corrected/contested supported interpretation | typed correction basis |

Once supported lifecycle is not `UNRESOLVED`, ordinary resume/defer/withdraw/re-resolve is invalid. Renewed deliberate judgment creates a new Decision with a new Decision Need.

Late findings use correction semantics rather than pretending they were ordinary forward transitions.

---

# 6. Deferral vs Review Condition

```text
deferred unresolved Decision + awaited condition -> same Decision may resume
resolved Decision + Review Condition -> Attention evaluates possible new Decision Need
```

R2 stores only Decisions-side Deferral consequence + trusted basis reference.

A deliberate hold/no-action may substantively resolve a Decision when the trusted Human Investment Decision basis explicitly has resolving effect. Rejection of a Recommendation does **not** by itself determine lifecycle outcome: a rejection that requests further judgment leaves the Decision unresolved, while a rejection that itself substantively disposes of the underlying choice may resolve it. The upstream Human Investment Decision semantics, not the word “reject,” determine the Decisions-side effect.

---

# 7. Same Decision vs new Decision

Continuity outcomes:

```text
CONTINUE_EXISTING(decision_id)
CREATE_NEW
AMBIGUOUS(candidate_ids)
```

R2 has no Subject/Scope similarity heuristic.

Rules:

1. explicit continuation of a known unresolved operative Decision preserves identity and its existing Decision Need;
2. no unresolved operative candidates -> `CREATE_NEW` may proceed after atomic revalidation;
3. candidates exist -> automatic `CREATE_NEW` requires an explicit continuity determination after considering them;
4. missing/inconsistent determination -> `AMBIGUOUS`, no creation;
5. the determination and material candidate basis are durably preserved in `DecisionInitiated` when a new Decision commits;
6. later Attention may automate determination but must use the same contract and preserve attributable basis;
7. renewed work after substantive/External Resolution creates a new causally linked Decision and a new Decision Need;
8. unsupported Need is never silently reactivated;
9. no universal thread/hash identity abstraction is required.

---

# 8. Concurrent initiation

Different operation IDs can race, so R2 requires conservative candidate discovery, explicit continuity determination, atomic revalidation, `ContinuityConflict` when the basis changed, and fail-closed ambiguity.

PostgreSQL may serialize initiation broadly if simplest. Historical duplicates, if discovered, are never silently merged/deleted.

---

# 9. Governance seams

Governance owns Human Investment Decision/authority acts. Decisions owns resulting Deferral/substantive-resolution consequence.

Trusted basis is typed: upstream owner/business fact plus semantic effect `DEFERRING` or `SUBSTANTIVELY_RESOLVING`. An arbitrary Human Investment Decision reference is not presumed resolving.

R2 tests may use deterministic trusted fixtures. A historical human judgment may exist even when consequential authority was deficient; attribution and authority remain distinct.

---

# 10. External Resolution / unsupported Need

External Resolution requires circumstance eliminating the Need; changed Evidence/Portfolio State/alternatives alone is insufficient while the same choice exists.

Unsupported Need correction applies when original Need determination was erroneous/unsupported. It may be established after any prior lifecycle disposition or human act. Preserve every prior fact and append correction.

Neither path fabricates another owner's judgment/authority fact.

---

# 11. Supersession

- source/target IDs differ;
- unresolved/resolved targets allowed;
- no one-to-one cardinality assumption;
- target lifecycle facts never rewritten;
- unresolved supported target becomes non-operative;
- contested Supersession support yields contested operative applicability and ordinary work fails closed;
- supported `RENEWED_FROM` + `SUPERSEDES` lineage remains acyclic.

---

# 12. Temporal and correction model

Every lifecycle/relationship fact has effective time plus recorded time/monotonic sequence.

`as_known_at(K)` is defined as the lifecycle/operative state **effective at K using only facts and corrections recorded no later than K**. Semantically it is equivalent to:

```text
effective_at(T=K, known_at=K)
```

Therefore a fact already recorded by K but explicitly effective only after K is known historically but does not change the state effective at K.

`effective_at(T, known_at=K)` uses only knowledge recorded by K, then applies effective times/corrections at T. `K=now` yields current best supported effective history.

`DecisionLifecycleCorrected` is append-only. It may qualify/disconfirm prior interpretation, establish another effective disposition, or correct effective time/basis. It never deletes facts, rewrites original Actor Attribution, fabricates another owner's fact, or gains semantic precedence merely by being newer.

If typed support cannot reconcile competing interpretations, Decision Memory exposes **contested/indeterminate** lifecycle interpretation rather than last-writer-wins.

Example:

```text
10:00 circumstance eliminates choice
10:05 human judgment recorded without that knowledge
10:10 authoritative fact arrives showing elimination effective 10:00
```

Preserve human act + originally recorded Decisions fact; append correction supporting `EXTERNALLY_RESOLVED` effective 10:00; earlier `as_known_at` remains stable.

---

# 13. Version/idempotency and invalid outcomes

- initiation version 1;
- each committed Decisions mutation increments version once;
- existing-Decision mutation uses expected version;
- same operation/same request replays result;
- same operation/different request conflicts;
- different operations still require continuity protection.

Callers distinguish not-found, invalid/reused Decision Need, non-operative/operative-contested, non-unresolved, invalid trusted basis, invalid Scope, invalid work transition, stale version, idempotency conflict, continuity conflict/ambiguity, relationship/cycle conflict, and contested lifecycle interpretation when deterministic state is required.

---

# 14. R2 test fixtures

1. no Scope at initiation;
2. partial Scope later completed;
3. `ESTABLISHED` empty Scope rejected;
4. one Decision Need cannot ground two Decision identities;
5. repeated continuation does not create a second Need;
6. human Deferral + awaited condition + same-Decision resume;
7. re-Deferral appends another Deferral fact;
8. deliberate hold/no-action resolving basis resolves; Recommendation rejection requesting more judgment does not;
9. withdrawal + same-Decision resume;
10. supportably superseded unresolved Decision rejects ordinary work;
11. contested Supersession/operative state also rejects ordinary work;
12. substantive resolution requires typed resolving basis;
13. ordinary External Resolution without human-decision inference;
14. late External Resolution after recorded substantive resolution uses correction;
15. unsupported Need retraction after substantive/External resolution or human acts preserves history;
16. resolved Decision later superseded without losing disposition;
17. one-to-many and many-to-one Supersession;
18. no candidates -> create after revalidation and preserve `NO_CANDIDATES` continuity basis;
19. candidates + explicit create -> preserve candidate IDs and attributable continuity rationale;
20. candidates + missing/contradictory determination -> ambiguity/no creation;
21. different-operation race -> no silent duplicate;
22. competing corrections -> contested interpretation, not newest-wins;
23. `as_known_at` excludes later-recorded facts and does not prematurely apply future-effective known facts;
24. `effective_at` applies currently supported correction;
25. runtime/job/model/report IDs never determine Decision identity.

---

# 15. R2 implementation scope / Spec gate

R2 implements Decision/Need/Subject/Scope semantics, lifecycle/work posture, immutable facts/corrections, explicit and durable continuity arbitration, trusted human-judgment seams, External/unsupported correction, renewal/Supersession, dual-time queries, and contested interpretation.

R2 excludes Attention, Evidence/full Decision Context, Intelligence/Recommendation, Governance implementation, Action Continuity, Learning, contextual prior-Decision retrieval, and generic graph infrastructure.

Specs may choose code organization, algorithms, libraries, schema details, and test mechanics. They may not redefine the semantics above.
