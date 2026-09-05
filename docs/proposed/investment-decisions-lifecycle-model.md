# Investment Decision Lifecycle Model

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `investment-decisions`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define the R2 Investment Decision domain model precisely enough that implementation Specs do not need to invent lifecycle identity, state decomposition, temporal correction, actor-attribution, continuity, or cross-entity resolution semantics.

## Authority

This design refines, but does not override:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`investment-decisions-r2-decision-kernel-component-boundaries.md`](investment-decisions-r2-decision-kernel-component-boundaries.md);
- [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md);
- [`investment-decisions-decision-relationship-model.md`](investment-decisions-decision-relationship-model.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md);
- [`../product/domain-model.md`](../product/domain-model.md) and [`../../CONTEXT.md`](../../CONTEXT.md);
- accepted ADRs under [`../adr/`](../adr/).

The relevant requirement families are principally `GF-*`, `DEC-*`, `MEM-*`, `REL-*`, `TMP-*`, and the Decision-kernel portions of `AS-001` through `AS-005` plus `AS-022`.

---

# 1. Design objective

R2 establishes a first-class Investment Decision domain whose identity and history survive:

- unresolved Decision Scope at initiation;
- additional Evidence;
- changed Portfolio State or Portfolio Risk;
- revised analytical judgment;
- changed Recommendation;
- human Deferral and later resumption;
- explicit withdrawal of decision work without investment judgment;
- retries and process restarts;
- concurrent initiation and mutation;
- substantive resolution;
- External Resolution;
- later discovery that an earlier Decision Need was erroneous or unsupported;
- Supersession before or after substantive resolution;
- later renewed judgment;
- late-recorded facts whose effective time precedes their recorded time;
- explicit correction of lifecycle understanding without destructive history rewriting.

The model must not depend on workflow, job, report, model, provider, or database identity.

---

# 2. Canonical R2 concepts

## 2.1 Investment Decision

An **Investment Decision** is one durable identified decision lifecycle established to resolve a Decision Need about one coherent Portfolio-relevant investment choice.

It has:

- a durable `InvestmentDecisionId`;
- one grounding `DecisionNeedId`;
- a current Decision Subject reference;
- a Decision Scope that may be unresolved during early work;
- a current resolution disposition derived from committed lifecycle facts;
- a current work disposition when the Decision remains unresolved;
- zero or more typed Decision-to-Decision relationships;
- a monotonic domain version used for concurrency control;
- immutable creation time.

Investment Decision identity is opaque. It is not a hash of Subject, Scope, Evidence, Recommendation, Portfolio State, text similarity, or runtime metadata.

## 2.2 Decision Need

A **Decision Need** is the attributable determination that an unresolved Portfolio-relevant investment choice warrants deliberate judgment.

R2 preserves:

- durable `DecisionNeedId`;
- concise need statement;
- raised/recognized effective time;
- recorded time;
- Actor Attribution for the determination where material;
- trigger/origin provenance separately from Actor Attribution;
- optional source/context references explaining the triggering matter;
- explicit later retraction/correction when the original determination is established to have been erroneous or unsupported.

A user request, schedule, observation, or system event may trigger Decision Need evaluation without necessarily being the actor that formed the Decision Need determination.

## 2.3 Decision Subject

Decision Subject identifies the investment matter being judged.

It is distinct from Investment Decision identity, Decision Scope, Evidence, trigger, and implementation instrument.

R2 treats Subject as a stable typed representation/reference. Multiple Investment Decisions may concern the same Subject through time.

## 2.4 Decision Scope

Decision Scope identifies the Portfolio or Portfolios whose state, capital consequences, and Mandates are directly implicated.

R2 permits:

```text
Decision exists
Decision Need exists
Decision Subject exists
Decision Scope = unresolved
```

when a genuine coherent choice already warrants deliberate work but Portfolio applicability is not yet established.

Rules:

- unresolved Scope is explicit, never silently invented;
- later Scope establishment is historical fact;
- later Scope refinement may preserve the same Decision ID when the coherent unresolved choice remains the same;
- final Capital-Relevant Recommendation/Human Investment Decision requirements belong to later owners, but the R2 model must be capable of enforcing that unresolved Scope cannot masquerade as established applicability.

## 2.5 Actor Attribution and trigger provenance

R2 preserves two different relationships:

```text
Actor Attribution
Who formed/performed the domain act?

Trigger / technical provenance
What request, observation, schedule, process, model/provider call,
or other event caused work to occur?
```

The two may coincide but must not be collapsed.

Examples:

- a human explicitly establishes a Decision Need -> human Actor Attribution;
- a human asks a question and Polaris determines it creates a Decision Need -> request is trigger, Polaris is the actor for the determination;
- an internal model/provider contributes to a Polaris determination -> model/provider identity remains technical provenance, not Actor Attribution.

---

# 3. Lifecycle is multi-dimensional

The prior five-state model is rejected because it conflated unresolved work posture, judgment/Need disposition, and continuing applicability.

R2 instead models three orthogonal concerns.

## 3.1 Resolution disposition

```text
UNRESOLVED
SUBSTANTIVELY_RESOLVED
EXTERNALLY_RESOLVED
NEED_RETRACTED
```

### UNRESOLVED

The Decision Need still warrants unresolved investment judgment.

### SUBSTANTIVELY_RESOLVED

The investment choice has been substantively answered through an attributable resolution basis. The Decision may still have later Action Continuity, Outcome, Evaluation, or Supersession relationships; this is terminal only for the unresolved investment judgment, not for every lifecycle activity associated with the Decision.

### EXTERNALLY_RESOLVED

Changed circumstances eliminated the Decision Need before substantive human resolution. External Resolution resolves the need for further judgment, not a missing Human Investment Decision.

### NEED_RETRACTED

A later attributable correction establishes that the earlier Decision Need determination was erroneous or unsupported rather than eliminated by changed circumstances. The historical Decision Need remains preserved; its current supported status is retracted.

`NEED_RETRACTED` is an R2 design label for implementation clarity, not a requirement that product UI expose that exact phrase.

## 3.2 Work disposition

While resolution disposition is `UNRESOLVED`, current work posture may be:

```text
ACTIVE
DEFERRED
WITHDRAWN
```

### ACTIVE

Decision work may proceed.

### DEFERRED

The unresolved choice remains real, but an attributable **Human Investment Decision of Deferral** has postponed substantive judgment. A Deferral may carry an awaited condition or reason.

R2 does not fabricate the Governance-owned Human Investment Decision. It records the Decisions-side work consequence only from a trusted attributable Deferral basis.

### WITHDRAWN

Current Polaris work has been explicitly stopped or withdrawn while the underlying Decision Need may still exist.

Withdrawal is not automatically:

- Deferral;
- Human Investment Decision;
- substantive resolution;
- External Resolution;
- Supersession.

If the same coherent unresolved choice later resumes and no later fact requires a new Decision, the same Decision ID may return to `ACTIVE`.

## 3.3 Continuing applicability / Supersession

Supersession is **not** a resolution or work state.

A Decision may be superseded while:

- unresolved;
- deferred;
- withdrawn;
- substantively resolved;
- externally resolved.

Supersession says another Investment Decision has displaced some or all of the earlier Decision's continuing applicability or operative investment basis.

The earlier Decision's resolution/work history remains unchanged.

A currently superseded unresolved Decision is no longer independently operative for normal work unless a later explicit correction changes the supported Supersession relationship.

---

# 4. Canonical R2 lifecycle facts

Current projections are reconstructable from immutable facts. The conceptual fact set is:

```text
DecisionInitiated
DecisionSubjectRevised
DecisionScopeEstablished
DecisionScopeRevised
DecisionDeferred
DecisionWorkResumed
DecisionWorkWithdrawn
DecisionResolved
DecisionExternallyResolved
DecisionNeedRetracted
DecisionLifecycleCorrected
```

Decision-to-Decision relationships such as `RENEWED_FROM` and `SUPERSEDES` are separate durable relationship facts defined in the relationship model.

The names above describe semantics, not mandatory Python class names.

## 4.1 Fact requirements

Every lifecycle fact preserves at least:

- unique fact identity;
- Investment Decision identity;
- monotonic recorded sequence/version;
- fact kind;
- effective/occurred time;
- durable recorded/committed time;
- operation/idempotency identity;
- Actor Attribution where the fact is an attributable domain act;
- trigger/technical provenance separately where material;
- typed business basis/reference;
- typed fact-specific content.

Facts are immutable after commit.

---

# 5. Transition and operation matrix

| Current resolution | Current work | Operation | Result | Durable fact / relationship | Notes |
|---|---|---|---|---|---|
| none | none | initiate | `UNRESOLVED` + `ACTIVE` | `DecisionInitiated` | Scope may be unresolved. |
| `UNRESOLVED` | `ACTIVE`/`DEFERRED`/`WITHDRAWN` | revise Subject | unchanged dispositions | `DecisionSubjectRevised` | Same-choice rule applies. |
| `UNRESOLVED` | any | establish previously unresolved Scope | unchanged dispositions | `DecisionScopeEstablished` | Explicit historical establishment. |
| `UNRESOLVED` | any | revise established Scope | unchanged dispositions | `DecisionScopeRevised` | Same-choice rule applies. |
| `UNRESOLVED` | `ACTIVE` | human Deferral basis | `DEFERRED` | `DecisionDeferred` | Requires trusted Human Investment Decision/Deferral basis. |
| `UNRESOLVED` | `DEFERRED` | resume | `ACTIVE` | `DecisionWorkResumed` | Awaited condition may motivate resume; no Review Condition required. |
| `UNRESOLVED` | `ACTIVE`/`DEFERRED` | withdraw current work | `WITHDRAWN` | `DecisionWorkWithdrawn` | No investment judgment implied. |
| `UNRESOLVED` | `WITHDRAWN` | resume same choice | `ACTIVE` | `DecisionWorkResumed` | Same identity only if Need remains supported. |
| `UNRESOLVED` | any operative work state | substantive resolution basis | `SUBSTANTIVELY_RESOLVED` | `DecisionResolved` | Requires trusted attributable basis. |
| `UNRESOLVED` | any operative work state | External Resolution | `EXTERNALLY_RESOLVED` | `DecisionExternallyResolved` | Must preserve cause; no Human Investment Decision inferred. |
| `UNRESOLVED` | any | retract unsupported Need | `NEED_RETRACTED` | `DecisionNeedRetracted` | Correction of earlier determination, not changed circumstances. |
| `SUBSTANTIVELY_RESOLVED` | n/a | renewed judgment | old unchanged + new Decision | `RENEWED_FROM` + new `DecisionInitiated` | New ID; predecessor remains historical. |
| `EXTERNALLY_RESOLVED` | n/a | renewed judgment | old unchanged + new Decision | `RENEWED_FROM` + new `DecisionInitiated` | New ID. |
| any eligible disposition | any | record Supersession | disposition unchanged | `SUPERSEDES` | May target unresolved or resolved Decision; relationship is orthogonal. |
| any | any | late correction | append correction; recompute supported projection | `DecisionLifecycleCorrected` | Never mutates/deletes prior fact. |

## 5.1 Invalid operations

At minimum:

- resume a substantively/external-resolved/retracted Decision -> invalid;
- defer without a trusted Deferral/Human Investment Decision basis -> invalid;
- classify withdrawal as External Resolution when the choice still exists -> invalid;
- classify unsupported original Decision Need as External Resolution merely because work should stop -> invalid;
- reopen a substantively or externally resolved Decision -> invalid; renewed judgment uses a new Decision;
- mutate an unresolved Decision that is currently superseded as though it remained operative -> invalid unless an explicit correction first changes the supported Supersession relationship.

---

# 6. Same Decision vs new Decision

Polaris must not infer Decision identity mechanically from Subject/Scope or from a change in Evidence/Recommendation.

The continuity outcomes are:

1. **continue existing** — an unresolved Decision already represents the same coherent choice;
2. **create new independent Decision** — a different coherent unresolved choice exists;
3. **renew after substantive/External Resolution** — create a new Decision with explicit `RENEWED_FROM`;
4. **supersede** — preserve both Decisions and add explicit `SUPERSEDES` relationship;
5. **ambiguous continuity** — do not automatically create another Decision until continuity can be determined reliably.

No universal `DecisionThread`, hash-derived ID, or Subject/Scope uniqueness rule is introduced.

## 6.1 Concurrent initiation

Operation-id idempotency alone does not prevent two different operations from creating duplicate Decision identities.

Before a distinct new Decision is committed, the application/persistence boundary must support an **atomic continuity arbitration** against the bounded unresolved candidate set used for the initiation decision.

Required semantics:

```text
observe candidate unresolved Decisions
        ↓
make explicit continuity determination
        ↓
before commit, ensure candidate continuity basis did not change
        ↓
changed / ambiguous -> ContinuityConflict or ContinuityAmbiguous
unchanged + explicitly new -> commit new Decision
```

The persistence mechanism may use serializable transactions, predicate/row locking, a bounded continuity generation/version, or another correct technique. The inward contract owns the semantic guarantee, not the mechanism.

Because semantic equivalence cannot always be proven mechanically, candidate selection must be conservative and ambiguity must fail closed rather than creating another Decision automatically.

---

# 7. Deferral seam with Governance

Canonical Deferral is a Human Investment Decision.

Ownership split:

- `governance-authority` owns the Human Investment Decision of Deferral;
- `investment-decisions` owns the resulting unresolved work posture (`DEFERRED`).

R2 may implement and test the Decisions-side transition using a trusted deterministic fixture/reference.

R2 must not expose a generic public command that allows an arbitrary caller to manufacture human Deferral authority.

An **awaited condition** attached to Deferral is not a Review Condition. When it becomes available/due, Attention may resume the same unresolved Decision.

A **Review Condition** belongs to a substantively resolved Decision and later causes Attention to evaluate whether a new Decision Need exists.

---

# 8. Substantive resolution seam with Governance

A substantive resolution transition requires an attributable **resolution basis reference** from an allowed owner/category.

The Decisions domain preserves enough to establish:

- referenced business fact identity;
- basis category;
- effective time;
- optional lifecycle summary;
- Actor Attribution/reference as appropriate.

It does not duplicate the Human Investment Decision payload or authority evaluation.

R2 may exercise the seam with trusted fixtures; later Governance implementation will coordinate the real owner facts in one application transaction when required.

---

# 9. External Resolution

External Resolution is valid only when changed circumstances eliminate the underlying Decision Need itself.

It is not triggered merely by:

- changed price;
- changed Evidence;
- changed Portfolio State;
- a changed Recommendation;
- user cancellation/withdrawal;
- another Investment Decision displacing the earlier one.

The fact preserves:

- attributable cause/basis;
- source reference where available;
- effective time;
- recorded time.

No Human Investment Decision, Recommendation, Action Intent, Approval, or authority act is inferred.

---

# 10. Decision Need retraction

A Decision Need may later be established as erroneous or unsupported.

Example:

```text
Decision Need established from believed Portfolio concentration
        ↓
later authoritative correction shows concentration never existed
        ↓
original Need remains historical
current support for that Need is retracted
```

This is not External Resolution because changed circumstances did not eliminate a genuine choice.

R2 records a non-destructive `DecisionNeedRetracted` fact with:

- correction basis;
- Actor Attribution;
- effective scope of the correction;
- recorded time;
- references to the Need/observations being corrected where available.

A later genuine need normally creates a new Investment Decision rather than silently reactivating the Decision grounded in the unsupported Need.

---

# 11. Withdrawal of decision work

Withdrawal records that current Polaris work is intentionally stopped while the unresolved choice may still exist.

Examples include:

- user says “stop evaluating this” without making the investment choice;
- operating policy suppresses further current work without determining the economic answer;
- resource/attention decision stops work without a Human Investment Decision of Deferral.

Withdrawal preserves:

- reason/basis;
- Actor Attribution where applicable;
- effective and recorded time.

It does not invent Deferral, Human Investment Decision, External Resolution, or Supersession.

---

# 12. Temporal model and correction

R2 preserves:

- **effective/occurred time** — when the domain fact is currently understood to have applied;
- **recorded/committed time** — when Polaris durably recorded/knew the fact;
- monotonic recorded sequence/version — deterministic ordering of committed knowledge for one Decision.

## 12.1 As-known-at

`as_known_at(T)`:

- uses only facts recorded no later than knowledge cutoff `T`;
- applies corrections only if those corrections were themselves recorded by `T`;
- reconstructs what Polaris could durably know about lifecycle at that time;
- never leaks a later-recorded fact backward merely because its effective time is earlier.

## 12.2 Effective-as-understood

R2 also needs a distinct effective reconstruction capability:

```text
state_effective_at(effective_time=T, knowledge_cutoff=K)
```

Meaning:

> Using only knowledge recorded by `K`, what lifecycle disposition is supported as having been effective at `T`?

When `K` is omitted, current durable knowledge is used.

This query is not Judgment-Time Availability for Evidence; it is Decision lifecycle temporal reconstruction.

## 12.3 Late-discovered conflicting lifecycle fact

If a later-recorded fact shows that the supported effective lifecycle differs from an earlier recorded lifecycle interpretation, Polaris appends an explicit `DecisionLifecycleCorrected` fact/reference.

Example:

```text
10:00 actual circumstance eliminates Decision Need
10:05 Human Investment Decision is recorded while Polaris does not know that
10:10 Polaris learns the 10:00 circumstance
```

Required result:

- the 10:05 Human Investment Decision remains historical and attributable;
- the earlier `DecisionResolved` lifecycle fact, if one was recorded, is not deleted;
- a later correction establishes that the supported effective Decision disposition became External Resolution at 10:00;
- `as_known_at(10:06)` still shows the state Polaris knew then;
- current effective reconstruction can show External Resolution effective at 10:00;
- no history is rewritten to pretend the human judgment never occurred.

A correction must reference the corrected/superseded interpretation or fact set sufficiently to avoid ambiguous competing “current truth” facts.

---

# 13. Version and concurrency semantics

Each Investment Decision has a monotonic recorded domain version.

Rules:

- initiation establishes version 1;
- each committed lifecycle mutation/correction increments the Decision version once;
- relationship facts may have their own identity/version semantics and must participate in expected-version checks when they affect operative behavior;
- every mutating command against an existing Decision supplies expected version(s) as required;
- stale expected version produces explicit concurrency conflict;
- same successfully committed operation replay returns original semantic result;
- same operation ID with materially different request produces idempotency conflict;
- continuity arbitration protects concurrent initiation separately from command idempotency.

Version orders recorded business knowledge; it does not replace effective time.

---

# 14. Domain construction rules

The domain model exposes behavior, not public setters.

A practical shape is conceptually:

```text
InvestmentDecision
  - identity
  - DecisionNeed identity/status
  - Subject
  - Scope (possibly unresolved)
  - resolution disposition
  - work disposition when unresolved
  - current version
  - behavior returning typed changes

DecisionLifecycleFact
  - immutable recorded history

DecisionRelationship
  - immutable typed cross-Decision relationship
```

Persistence reconstruction may use internal rehydration, but application callers cannot assign status/version/history arbitrarily.

---

# 15. Required domain test matrix

## Scope

- initiation with unresolved Scope is valid;
- Scope establishment preserves Decision ID and history;
- Scope revision while same choice remains unresolved preserves Decision ID.

## Actor/provenance

- actor and trigger can differ;
- model/provider identity cannot be substituted for Actor Attribution.

## Deferral/work posture

- Deferral requires trusted Human Investment Decision/Deferral basis;
- `ACTIVE -> DEFERRED` preserves Decision ID;
- awaited condition may resume same deferred Decision;
- Review Condition is not used to resume deferred Decision;
- withdrawal does not create Deferral or resolution;
- withdrawn same choice may resume with same ID.

## Resolution

- valid basis moves unresolved Decision to `SUBSTANTIVELY_RESOLVED`;
- resolution basis is referenced, not copied into Decisions ownership;
- resolved judgment never reopens;
- renewed judgment creates new ID + `RENEWED_FROM`.

## External Resolution

- changed circumstances must eliminate the Need;
- changed Evidence/state alone is insufficient;
- no Human Investment Decision is inferred;
- renewed judgment uses new ID.

## Need retraction

- erroneous/unsupported Need remains historical;
- current supported status becomes retracted;
- it is not classified as External Resolution;
- later genuine Need does not silently reactivate old Decision.

## Supersession

- Supersession does not replace historical resolution disposition;
- resolved predecessor can be superseded;
- unresolved predecessor can be superseded;
- superseded unresolved Decision is not treated as independently operative;
- relationship graph rules are tested in the relationship model.

## Continuity/concurrency

- same operation retry is idempotent;
- two distinct initiations racing against same candidate continuity basis cannot both silently commit as independent new Decisions;
- ambiguity returns explicit non-success rather than duplicate identity.

## Temporal correction

- as-known-at excludes later-recorded facts/corrections;
- effective-as-understood can incorporate late facts at their effective time;
- late External Resolution does not erase later-recorded Human Investment Decision history;
- correction does not mutate/delete the earlier lifecycle fact.

---

# 16. Requirements traceability

| Requirement | Design consequence |
|---|---|
| `GF-001`, `GF-005` | Decision identity is first-class and independent of runtime/persistence identity. |
| `DEC-001`–`DEC-004` | Explicit identity/continuity and Scope/Subject separation. |
| `DEC-006` | Deferral preserves unresolved identity but requires Human Investment Decision basis. |
| `DEC-008` | External Resolution preserves no inferred Human Investment Decision. |
| `DEC-009`–`DEC-012` | Resolution never reopens; historical lifecycle remains reconstructable. |
| `DEC-013` | Scope may be unresolved at initiation. |
| `DEC-014` | Work withdrawal is distinct from investment resolution/Deferral. |
| `DEC-015` | Unsupported Need is corrected non-destructively. |
| `DEC-016` | Supersession is orthogonal to historical resolution. |
| `DEC-017` | Concurrent initiation fails closed on continuity ambiguity. |
| `DEC-018` | Late lifecycle facts preserve effective truth and prior knowledge. |
| `DEC-019` | Actor Attribution remains separate from trigger provenance. |
| `MEM-*` | Immutable facts and distinct historical reconstructions support Decision Memory. |
| `REL-*` | Retry, concurrency, and recovery never silently duplicate/rewrite business truth. |
| `TMP-*` | Effective and recorded time remain distinct. |

---

# 17. Out of scope

This design does not implement:

- Attention candidate reasoning;
- Evidence internals;
- Recommendation/Investment Intelligence internals;
- Governance/Human Investment Decision persistence;
- Review Condition domain implementation;
- Action Continuity;
- Outcome/Evaluation/Lesson;
- generic event sourcing;
- generic correction framework for every future domain entity;
- a generic workflow/state-machine framework.

R2 implements only the Decisions-side seams needed to avoid later redesign.

---

# 18. Spec-readiness gate

This lifecycle design is Spec-ready only when review confirms:

1. Scope may be unresolved without inventing applicability;
2. Deferral, withdrawal, substantive resolution, External Resolution, Need retraction, and Supersession remain semantically distinct;
3. Supersession is orthogonal to resolution/work disposition and may apply after resolution;
4. Actor Attribution is distinct from trigger/technical provenance;
5. concurrent initiation has an explicit fail-closed continuity contract beyond operation-id idempotency;
6. late-recorded lifecycle facts use explicit non-destructive correction;
7. as-known-at and effective-as-understood queries have different semantics;
8. no Spec must invent how these lifecycle cases behave.
