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

## Investment Decision

An Investment Decision has:

- opaque durable `InvestmentDecisionId`;
- one grounding `DecisionNeedId`;
- current Decision Subject reference;
- current Decision Scope representation;
- supported lifecycle disposition derived from immutable facts/corrections;
- current work posture when unresolved and operative;
- monotonic recorded domain version;
- immutable creation time.

Decision relationships are separate durable facts.

## Decision Need

A Decision Need is the attributable determination that one coherent unresolved Portfolio-relevant choice warrants deliberate judgment. R2 preserves Need identity/statement, effective establishment time, recorded time, Actor Attribution where material, trigger provenance separately, and later correction without deleting original establishment.

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

No fake/default Portfolio identity may represent unresolved Scope. Final Capital-Relevant Recommendation or Human Investment Decision requires sufficiently established Portfolio applicability; initiation does not.

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

Meaningful only while lifecycle disposition is `UNRESOLVED` **and the Decision remains operative**:

```text
ACTIVE
DEFERRED
WITHDRAWN
```

- `ACTIVE`: work may proceed.
- `DEFERRED`: attributable Human Investment Decision postponed substantive judgment. A trusted human-decision basis is required; awaited condition is not a Review Condition.
- `WITHDRAWN`: work was explicitly stopped without investment judgment and without eliminating the Need.

A later human Deferral while already `DEFERRED` is valid when it is a new attributable Human Investment Decision (for example changing the awaited condition). It appends a new Deferral fact and leaves posture `DEFERRED`; it never overwrites the earlier Deferral.

## 3.3 Continuing applicability

`SUPERSEDES` is an orthogonal Decision-to-Decision relationship indicating that a source Decision displaces a target Decision's continuing applicability/operative basis.

A target may be unresolved, substantively resolved, or externally resolved. Supersession never replaces its historical lifecycle disposition.

### Operative rule

Ordinary unresolved-work and judgment-consequence commands—resume, defer/re-defer, withdraw, and substantive resolution—require the Decision to remain operative (not currently supportably superseded). A superseded historical Decision may still receive explicit correction/relationship facts, but normal decision work does not continue through it.

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

Facts are immutable. Relationship facts (`RENEWED_FROM`, `SUPERSEDES`) are separate.

---

# 5. Normal transition rules

| Lifecycle | Work | Operative? | Operation | Result | Required basis |
|---|---|---:|---|---|---|
| none | none | — | initiate | `UNRESOLVED + ACTIVE` | Need + Subject; Scope may be unresolved |
| UNRESOLVED | any | yes | establish/revise Scope or Subject | same Decision/work | explicit revision fact |
| UNRESOLVED | ACTIVE/WITHDRAWN | yes | human defer | `DEFERRED` | trusted Deferral Human Investment Decision |
| UNRESOLVED | DEFERRED | yes | human re-defer | `DEFERRED` | new trusted Deferral Human Investment Decision; append fact |
| UNRESOLVED | DEFERRED/WITHDRAWN | yes | resume | `ACTIVE` | explicit same-choice resumption basis |
| UNRESOLVED | ACTIVE/DEFERRED | yes | withdraw work | `WITHDRAWN` | attributable work-control basis |
| UNRESOLVED | any | yes | substantive resolve | `SUBSTANTIVELY_RESOLVED` | trusted basis explicitly establishing resolving effect |
| UNRESOLVED | any | yes or no | externally resolve | `EXTERNALLY_RESOLVED` | attributable circumstance eliminating Need |
| UNRESOLVED | any | yes or no | retract unsupported Need | `NEED_RETRACTED_UNSUPPORTED` | attributable correction basis |

Once lifecycle disposition is not `UNRESOLVED`, ordinary resume/defer/withdraw/re-resolve is invalid. Renewed deliberate judgment creates a new Decision identity.

External/unsupported correction may target a non-operative historical Decision because it corrects lifecycle understanding rather than continuing work.

---

# 6. Deferral vs Review Condition

```text
deferred unresolved Decision
    + awaited condition
    -> same Decision may resume

substantively resolved Decision
    + Review Condition
    -> Attention evaluates possible new Decision Need
```

R2 stores only Decisions-side Deferral consequence + trusted basis reference; Governance owns the Human Investment Decision payload.

---

# 7. Same Decision vs new Decision

Continuity outcomes are:

```text
CONTINUE_EXISTING(decision_id)
CREATE_NEW
AMBIGUOUS(candidate_ids)
```

R2 does **not** invent a Subject/Scope similarity heuristic to select among candidates.

Rules:

1. explicit continuation of a known unresolved operative Decision preserves identity;
2. if no unresolved operative candidates exist, `CREATE_NEW` may proceed subject to atomic revalidation;
3. if one or more candidates exist, automatic `CREATE_NEW` requires an **explicit continuity determination** from the initiating use case/caller after considering the candidate set; absence/inconsistency yields `AMBIGUOUS`;
4. a later Attention implementation may automate that determination, but it must use this same contract and preserve its attributable basis;
5. renewed work after substantive/External Resolution creates a new causally linked Decision;
6. unsupported Need is never silently reactivated;
7. no universal `DecisionThread` or hash-derived continuity key is required.

---

# 8. Concurrent initiation

Operation idempotency does not prevent different operation IDs from racing.

R2 requires:

1. conservative discovery of unresolved, non-superseded candidates;
2. explicit continuity determination as above;
3. atomic revalidation of candidate basis before `CREATE_NEW` commits;
4. `ContinuityConflict` when concurrent work changes that basis;
5. ambiguity to fail closed.

PostgreSQL may serialize initiation broadly in R2 if simplest. Inward semantics remain technology-neutral.

Historical duplicates, if discovered, are never silently merged/deleted.

---

# 9. Governance seams

Governance owns Human Investment Decision/authority acts. Decisions owns the resulting Deferral/substantive-resolution consequence.

A trusted Deferral/resolution basis is typed: it identifies the upstream owner/business fact and explicitly states the semantic effect established by that owner (`DEFERRING` or `SUBSTANTIVELY_RESOLVING`). Decisions does not treat any arbitrary Human Investment Decision reference as resolving by default.

R2 tests may use deterministic trusted fixtures. No generic public path lets arbitrary callers self-assert authority facts.

A substantive Human Investment Decision may historically exist even when consequential authority was deficient; attribution and authority remain distinct.

---

# 10. External Resolution and unsupported Need

External Resolution requires a basis showing circumstances eliminated the Need. Changing Evidence/Portfolio State/alternatives alone is insufficient while the same coherent choice exists.

Unsupported Need correction applies when the Need determination itself was erroneous/unsupported. Original Need/Decision and all prior acts remain historical; later genuine need follows normal identity rules.

Neither path fabricates Recommendation, Human Investment Decision, Approval, Action Intent, or Outcome.

---

# 11. Supersession

- source/target IDs differ;
- unresolved or resolved targets allowed;
- no one-to-one cardinality assumption;
- target lifecycle facts never rewritten;
- unresolved superseded target is non-operative for ordinary continuation/work;
- supported `RENEWED_FROM` + `SUPERSEDES` lineage remains acyclic.

---

# 12. Temporal and correction model

Every lifecycle/relationship fact has effective time plus recorded time/monotonic recorded sequence.

`as_known_at(K)` uses only facts/corrections recorded by K.

`effective_at(T, known_at=K)` uses only knowledge recorded by K, then applies effective times/corrections at T. `K=now` yields current best supported effective history.

Late facts never leak into earlier `as_known_at` views.

`DecisionLifecycleCorrected` is append-only and may qualify/disconfirm a prior interpretation, establish another effective disposition, or correct effective time/basis. It never deletes facts, rewrites original Actor Attribution, fabricates another owner's fact, or gains precedence merely by being newer.

If currently available attributable facts support incompatible interpretations and typed correction/basis semantics cannot resolve them, Decision Memory exposes **contested/indeterminate** lifecycle interpretation. This is a query condition, not another business lifecycle state.

Example:

```text
10:00 circumstance eliminates choice
10:05 human judgment recorded without that knowledge
10:10 authoritative fact arrives showing elimination effective 10:00
```

Preserve the human act and recorded Decisions fact, append correction supporting `EXTERNALLY_RESOLVED` effective 10:00, keep `as_known_at(10:06)` unchanged, and let current `effective_at(10:02)` reflect the later supported understanding.

---

# 13. Version, idempotency, invalid outcomes

- initiation version 1;
- each committed Decisions mutation increments version once;
- existing-Decision mutations use expected version;
- same operation/same request replays result;
- same operation/different request -> idempotency conflict;
- different operations still require continuity protection.

Callers must distinguish not-found, non-operative Decision, non-unresolved Decision, invalid trusted basis, invalid resume/defer/withdraw transition, stale version, idempotency conflict, continuity conflict/ambiguity, relationship/cycle conflict, and contested lifecycle interpretation when deterministic state is required.

---

# 14. R2 test fixtures

Required fixtures include:

1. no Scope at initiation;
2. partial Scope later completed;
3. human Deferral + awaited condition + same-Decision resume;
4. re-Deferral appends another Deferral fact;
5. withdrawal + same-Decision resume;
6. superseded unresolved Decision rejects ordinary resume/defer/resolve;
7. substantive resolution requires typed resolving basis;
8. External Resolution without human-decision inference;
9. erroneous Need retracted after work/human acts occurred;
10. resolved Decision later superseded without losing resolution;
11. one-to-many and many-to-one Supersession;
12. initiation with no candidates may create after revalidation;
13. candidates present + no explicit continuity determination -> ambiguity/no creation;
14. different-operation initiation race cannot silently duplicate identity;
15. late External Resolution predating recorded substantive resolution;
16. competing corrections -> contested interpretation, not newest-wins;
17. `as_known_at` excludes later correction;
18. `effective_at` applies currently supported correction;
19. runtime/job/model/report IDs never determine Decision identity.

---

# 15. R2 implementation scope / Spec gate

R2 implements Decision/Need/Subject/Scope semantics, lifecycle/work posture, immutable facts/corrections, explicit continuity arbitration, trusted human-judgment seams, External/unsupported correction, renewal/Supersession, dual-time queries, and contested interpretation.

R2 excludes Attention, Evidence/full Decision Context, Intelligence/Recommendation, Governance implementation, Action Continuity, Learning, contextual prior-Decision retrieval, and generic graph infrastructure.

Specs may choose code organization, concrete algorithms, libraries, schema details, and test mechanics. They may not redefine the semantics above.
