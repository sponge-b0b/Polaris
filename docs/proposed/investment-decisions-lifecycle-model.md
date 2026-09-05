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

R2 establishes one durable Investment Decision identity for one coherent unresolved Portfolio-relevant choice and preserves its history when:

- Decision Scope is initially unresolved or only partially established;
- Subject/Scope are refined;
- work is actively pursued, human-deferred, withdrawn, or resumed;
- a substantive human judgment resolves the choice;
- circumstances externally eliminate the Decision Need;
- the original Decision Need is later established to have been unsupported;
- another Decision supersedes continuing applicability;
- later judgment creates a new causally linked Decision;
- retries, restarts, concurrent initiation, or late-recorded facts occur.

Investment Decision identity is never derived from workflow/job/report/model/database identity.

---

# 2. Core identities

## 2.1 Investment Decision

An Investment Decision has:

- opaque durable `InvestmentDecisionId`;
- one grounding `DecisionNeedId`;
- current Decision Subject reference;
- current Decision Scope representation;
- supported lifecycle disposition derived from immutable facts/corrections;
- current work posture when lifecycle disposition remains unresolved and operative;
- monotonic recorded domain version;
- immutable creation time.

Decision-to-Decision relationships are separate durable facts. They are not mutable adjacency inside the Decision object.

## 2.2 Decision Need

A Decision Need is the attributable determination that one coherent unresolved Portfolio-relevant choice warrants deliberate judgment.

R2 preserves:

- durable identity;
- need statement;
- effective establishment time;
- recorded time;
- Actor Attribution where material;
- trigger/origin provenance separately;
- later lifecycle disposition/correction without deleting original establishment.

## 2.3 Decision Subject

Subject identifies the investment matter being judged. It is required for coherent Decision identity but is not the Decision ID. Material refinement preserves history and does not automatically create a new Decision.

## 2.4 Decision Scope

Scope identifies affected Portfolio applicability. It is represented as:

```text
confirmed portfolio references: zero or more
scope completeness: UNRESOLVED | ESTABLISHED
```

Examples:

```text
[] + UNRESOLVED
= no Portfolio applicability established yet

[Portfolio A] + UNRESOLVED
= A is known to be implicated, but additional applicability remains unresolved

[Portfolio A, Portfolio B] + ESTABLISHED
= applicable Portfolio scope is sufficiently established for the current decision use
```

R2 MUST NOT fabricate empty/default Portfolio identity to mean unresolved Scope.

A final Capital-Relevant Investment Recommendation or Human Investment Decision requires sufficiently established Portfolio applicability, but initiation does not.

---

# 3. Lifecycle model: three orthogonal concerns

Polaris must not collapse these concerns into one status enum.

## 3.1 Supported lifecycle disposition

Exactly one supported lifecycle interpretation is exposed when determinable:

```text
UNRESOLVED
SUBSTANTIVELY_RESOLVED
EXTERNALLY_RESOLVED
NEED_RETRACTED_UNSUPPORTED
```

### UNRESOLVED

The Decision Need remains supported and the coherent investment choice has not been substantively resolved or eliminated.

### SUBSTANTIVELY_RESOLVED

The investment choice was substantively disposed of through an attributable resolution basis, normally a Governance-owned Human Investment Decision.

The Decisions boundary records the lifecycle consequence; it does not own or fabricate the Human Investment Decision.

### EXTERNALLY_RESOLVED

Circumstances eliminated the Decision Need before substantive resolution of the choice. No Human Investment Decision is inferred.

### NEED_RETRACTED_UNSUPPORTED

Later attributable correction establishes that the Decision Need determination itself was erroneous or unsupported rather than eliminated by changed circumstances.

The original Need/Decision history remains durable. This disposition is not External Resolution.

## 3.2 Work posture

Work posture is meaningful only while the supported lifecycle disposition is `UNRESOLVED` and the Decision remains operative.

```text
ACTIVE
DEFERRED
WITHDRAWN
```

### ACTIVE

Decision work may proceed.

### DEFERRED

Work is intentionally paused because an attributable Human Investment Decision deferred substantive judgment. Deferral requires a trusted human-decision basis; Decisions may not manufacture it.

A Deferral may preserve an awaited condition. That awaited condition is **not** a Review Condition.

### WITHDRAWN

Polaris/user work on the unresolved choice is explicitly stopped without making an investment judgment and without eliminating the Decision Need.

Withdrawal is not Deferral, substantive resolution, External Resolution, or Supersession. Later explicit continuation may resume the same Decision if the coherent unresolved choice remains the same.

## 3.3 Continuing applicability / operative basis

Supersession is not a lifecycle disposition or work posture.

`SUPERSEDES` is a typed Decision-to-Decision relationship indicating that a source Decision displaces a target Decision's continuing applicability or operative investment basis.

A Decision may be superseded while unresolved, substantively resolved, or externally resolved. Supersession never replaces or erases the target's historical lifecycle disposition.

---

# 4. Immutable lifecycle facts

R2 requires immutable fact semantics equivalent to:

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

Decision relationship facts (`RENEWED_FROM`, `SUPERSEDES`) are defined separately.

Every fact preserves at least:

- fact identity;
- Decision identity;
- recorded sequence/domain version;
- fact kind;
- effective/occurred time;
- durable recorded/committed time;
- operation/idempotency identity;
- Actor Attribution where applicable;
- trigger/technical provenance separately where material;
- typed business basis/reference;
- correction target/reference when applicable.

Facts are immutable after commit.

---

# 5. Normal transitions

| Supported disposition | Work posture | Operation | Result | Required basis |
|---|---|---|---|---|
| none | none | initiate | `UNRESOLVED + ACTIVE` | Decision Need + Subject; Scope may be unresolved |
| UNRESOLVED | ACTIVE | establish/revise Scope | same Decision | explicit Scope fact |
| UNRESOLVED | DEFERRED | establish/revise Scope | same Decision, still deferred | explicit Scope fact |
| UNRESOLVED | WITHDRAWN | establish/revise Scope | same Decision, still withdrawn | explicit Scope fact |
| UNRESOLVED | ACTIVE | human defer | `UNRESOLVED + DEFERRED` | trusted Human Investment Decision basis |
| UNRESOLVED | WITHDRAWN | resume work | `UNRESOLVED + ACTIVE` | explicit continuity decision |
| UNRESOLVED | DEFERRED | resume work | `UNRESOLVED + ACTIVE` | awaited/material resumption condition or explicit human continuation |
| UNRESOLVED | ACTIVE | withdraw work | `UNRESOLVED + WITHDRAWN` | attributable work-control basis |
| UNRESOLVED | DEFERRED | withdraw work | `UNRESOLVED + WITHDRAWN` | attributable work-control basis; Deferral fact remains historical |
| UNRESOLVED | any | substantive resolve | `SUBSTANTIVELY_RESOLVED` | trusted resolution basis |
| UNRESOLVED | any | external resolve | `EXTERNALLY_RESOLVED` | attributable external-resolution basis |
| UNRESOLVED | any | retract unsupported Need | `NEED_RETRACTED_UNSUPPORTED` | attributable correction basis |

Once supported disposition is not `UNRESOLVED`, ordinary resume/defer/withdraw/re-resolve operations are invalid. Renewed deliberate judgment creates a new Decision identity.

Supersession may be established independently of this table because it is an orthogonal relationship.

---

# 6. Deferral and Review Condition

Canonical distinction:

```text
deferred unresolved Decision
    + awaited condition
    -> same Decision may resume

substantively resolved Decision
    + Review Condition
    -> Attention evaluates whether a renewed Decision Need exists
```

R2 stores only the Decisions-side Deferral consequence and trusted basis reference. It does not create Governance-owned Human Investment Decision payloads.

---

# 7. Same Decision vs new Decision

Identity follows one coherent unresolved choice, not Subject/Scope equality or hash matching.

Application continuity outcomes are:

```text
CONTINUE_EXISTING(decision_id)
CREATE_NEW
AMBIGUOUS
```

Rules:

1. explicit continuation of a known unresolved Decision preserves identity;
2. new work after substantive or External Resolution creates a new causally linked Decision when it is genuinely renewed judgment;
3. a corrected unsupported Need is never silently reactivated;
4. ambiguity fails closed—no automatic duplicate Decision is created;
5. R2 need not invent a universal `DecisionThread` or hash-derived continuity key.

---

# 8. Concurrent initiation

Operation idempotency alone does not prevent two distinct operation IDs from creating duplicate Decisions.

R2 therefore requires:

1. conservative discovery of unresolved, non-superseded candidate Decisions;
2. explicit same/new/ambiguous continuity determination;
3. atomic revalidation that the relevant candidate basis has not changed before `CREATE_NEW` commits;
4. a `ContinuityConflict`/equivalent result when concurrent work invalidates the basis;
5. ambiguity to remain explicit rather than guessing.

For R2 scale, the persistence adapter MAY serialize initiation broadly if that is the smallest correct mechanism. The inward contract remains technology-neutral.

If historical duplicates are discovered after commit, R2 does not silently merge/delete them. Duplicate-identity remediation requires explicit correction/relationship semantics and remains inspectable.

---

# 9. Resolution seam with Governance

Ownership split:

- Governance owns Human Investment Decision and authority acts;
- Decisions owns the lifecycle consequence that the investment choice became substantively resolved or human-deferred.

A trusted reference supplied by Application must identify the authoritative business basis. R2 tests may use deterministic trusted fixtures, but no generic public path may allow arbitrary callers to self-assert a Human Investment Decision.

A substantive resolution may exist even if authority for consequential action was deficient; attribution and authority remain distinct. Decisions records resolution semantics, not inferred authority.

---

# 10. External Resolution

External Resolution means circumstances eliminated the underlying Decision Need before substantive resolution.

The basis preserves:

- source/business reference where available;
- attributable explanation;
- effective time;
- recorded time.

External Resolution must not create or imply Recommendation, Human Investment Decision, Approval, Action Intent, or favorable Outcome.

A change that only modifies Evidence, Portfolio State, alternatives, or expected consequence is not External Resolution if the same coherent choice still exists.

---

# 11. Unsupported Decision Need correction

`NEED_RETRACTED_UNSUPPORTED` is used when later attributable understanding shows the original Decision Need determination was not supportable in the first place.

Examples include materially erroneous Portfolio facts or an incorrectly inferred choice.

Rules:

- original `DecisionInitiated` and Need remain historical;
- prior human/Polaris acts remain historical;
- correction may change current supported lifecycle interpretation;
- no prior act is deleted or retroactively converted into another act;
- later genuine need uses normal identity rules.

---

# 12. Supersession

Supersession is defined in the relationship model but lifecycle constraints include:

- source and target identities differ;
- resolved or unresolved targets are allowed;
- no one-to-one cardinality assumption;
- no lifecycle fact on the target is rewritten;
- unresolved superseded Decisions are no longer considered operative candidates for continuation;
- supported `RENEWED_FROM` + `SUPERSEDES` lineage remains acyclic.

---

# 13. Temporal model

Every lifecycle/relationship fact has:

- **effective time** — when the business fact is understood to apply;
- **recorded time** plus monotonic recorded sequence — when Polaris durably knew/recorded it.

Recorded sequence is the deterministic commit ordering primitive; timestamps alone are insufficient.

## 13.1 As-known-at

`as_known_at(K)`:

- includes only facts/corrections recorded by cutoff `K`;
- reconstructs the supported lifecycle understanding from that knowledge set;
- never leaks later-recorded facts backward.

## 13.2 Effective-at under knowledge cutoff

`effective_at(T, known_at=K)`:

- uses only facts/corrections recorded by `K`;
- evaluates their effective times relative to `T`;
- returns the supported effective lifecycle interpretation at `T` under that knowledge boundary.

With `K=now`, this expresses current best supported historical interpretation.

## 13.3 Late correction

Example:

```text
10:00 external circumstance eliminates choice
10:05 Human Investment Decision is formed without that knowledge
10:10 authoritative information is recorded showing elimination effective 10:00
```

Polaris must preserve:

- the Human Investment Decision as an actual historical act;
- the Decisions resolution fact actually recorded at/after 10:05 if one was recorded;
- a later correction supporting `EXTERNALLY_RESOLVED` effective 10:00;
- `as_known_at(10:06)` as the knowledge state then;
- current `effective_at(10:02)` as externally resolved if the later correction is currently supported.

## 13.4 Contested interpretation

If currently available attributable facts support incompatible lifecycle interpretations and no governing correction/basis resolves them, Decision Memory MUST expose the lifecycle interpretation as **contested/indeterminate** rather than choosing the last writer.

This is a query/interpretation condition, not a new Investment Decision business lifecycle state.

---

# 14. Correction semantics

`DecisionLifecycleCorrected` is append-only and references the fact/interpretation it qualifies.

A correction may:

- disconfirm or qualify a prior supported lifecycle interpretation;
- establish a different effective lifecycle disposition;
- correct materially wrong effective time or business basis;
- leave earlier as-known-at views intact.

It must not:

- delete the original fact;
- rewrite Actor Attribution of the original act;
- fabricate a Human Investment Decision or external fact;
- silently select among contested corrections.

Correction ordering by itself does not imply semantic precedence. Precedence comes from typed correction/basis semantics.

---

# 15. Version and idempotency

- initiation establishes version 1;
- each committed Decisions mutation increments recorded domain version exactly once;
- expected-version checks protect mutation of an existing Decision;
- same operation + same semantic request returns original committed semantic result;
- same operation + different request is an idempotency conflict;
- different operation IDs still require continuity/concurrency protection.

Version is business concurrency metadata, not database row identity.

---

# 16. Invalid outcomes

Application callers must distinguish at least:

- Decision not found;
- Decision no longer unresolved for requested ordinary work transition;
- invalid Deferral basis;
- invalid substantive-resolution basis;
- invalid External Resolution basis;
- invalid Need-retraction basis;
- resume when not deferred/withdrawn as required by operation semantics;
- stale expected version;
- idempotency conflict;
- continuity conflict;
- continuity ambiguity;
- invalid relationship/self-reference/cycle;
- contested lifecycle interpretation when requested operation requires a deterministic prior disposition.

Concrete exception/result names remain implementation details.

---

# 17. Domain construction

The domain exposes behavior, not public status setters.

A practical shape is:

```text
InvestmentDecision
  identity
  DecisionNeed reference
  Subject
  Scope
  supported lifecycle view
  work posture
  version
  behavior -> typed facts

DecisionLifecycleFact
  immutable fact

DecisionLifecycleInterpretation
  determinate(disposition)
  or contested(candidate interpretations + basis references)
```

Rehydration may have an internal persistence path but must not become an application mutation bypass.

---

# 18. R2 test fixtures

Pure domain/application tests must include:

1. initiation with no established Portfolio Scope;
2. partially known Scope later completed;
3. human Deferral with awaited condition, then same-Decision resumption;
4. withdrawal and later same-Decision resumption;
5. substantive resolution from active/deferred/withdrawn work posture with trusted basis;
6. External Resolution without Human Investment Decision inference;
7. erroneous Need retracted after work has occurred;
8. erroneous Need discovered after a Human Investment Decision fact exists—the act remains historical;
9. resolved Decision later superseded without losing resolved disposition;
10. one Decision superseding multiple prior Decisions;
11. multiple superseding Decisions where domain basis supports it;
12. concurrent different-operation initiations cannot silently duplicate one coherent unresolved choice;
13. late External Resolution effective before a previously recorded substantive resolution;
14. competing late corrections produce contested/indeterminate effective interpretation rather than last-writer-wins;
15. as-known-at excludes later-recorded correction;
16. effective-at with current knowledge applies supported correction;
17. runtime/job/model/report IDs never determine Decision identity.

---

# 19. R2 implementation scope

R2 implements:

- Decision/Need/Subject/Scope identity semantics;
- supported lifecycle disposition + work posture;
- immutable facts and explicit correction semantics;
- continuation/concurrent-initiation arbitration;
- trusted Deferral/substantive-resolution seams;
- External Resolution and unsupported-Need correction;
- renewal/Supersession lineage support;
- dual-time historical query semantics;
- deterministic contested-interpretation reporting.

R2 does not implement:

- Attention engine;
- Evidence acquisition/full Decision Context;
- Investment Intelligence/Recommendation;
- Governance domain implementation;
- Action Continuity;
- Learning;
- contextual prior-Decision retrieval/selection;
- generic graph infrastructure.

---

# 20. Spec-readiness rule

A Spec derived from this design may choose class/function organization, concrete algorithms, libraries, PostgreSQL schema details, and test mechanics.

It may **not** redefine:

- Decision identity;
- Scope unresolved/partial semantics;
- lifecycle disposition/work-posture separation;
- Deferral ownership;
- withdrawal meaning;
- unsupported Need correction;
- Supersession as an orthogonal relationship;
- continuity ambiguity/concurrency behavior;
- effective vs recorded time;
- append-only correction and contested interpretation semantics.
