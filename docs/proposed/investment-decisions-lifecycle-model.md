# Investment Decision Lifecycle Model

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `investment-decisions`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define the R2 Investment Decision domain model precisely enough that implementation Specs do not need to invent lifecycle identity, transition, temporal, or cross-entity resolution semantics.

## Authority

This design refines, but does not override:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`investment-decisions-r2-decision-kernel-component-boundaries.md`](investment-decisions-r2-decision-kernel-component-boundaries.md);
- [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- [`../product/domain-model.md`](../product/domain-model.md) and [`../../CONTEXT.md`](../../CONTEXT.md);
- accepted ADRs under [`../adr/`](../adr/).

The relevant requirement families are principally `GF-*`, `DEC-*`, `MEM-*`, `TMP-*`, and the R2 acceptance scenarios `AS-001` through `AS-005` plus `AS-022`.

---

# 1. Design objective

R2 must establish a first-class Investment Decision domain whose identity and history survive:

- additional Evidence;
- changed Portfolio State or Portfolio Risk;
- revised analytical judgment;
- changed Recommendation;
- Deferral and later resumption;
- retries and process restarts;
- concurrent commands;
- substantive resolution;
- External Resolution;
- Supersession;
- later renewed judgment.

The model must not depend on workflow/job/report/model/database identity.

---

# 2. Canonical R2 concepts

## 2.1 Investment Decision

An **Investment Decision** represents one coherent unresolved portfolio-relevant choice.

It has:

- a durable `InvestmentDecisionId`;
- one grounding `DecisionNeedId`;
- a current Decision Subject reference;
- a current Decision Scope value;
- a lifecycle state derived from committed lifecycle facts;
- a monotonic domain version used for concurrency control;
- immutable creation time;
- optional causal relationship to an earlier resolved Investment Decision;
- optional Supersession relationship when one decision replaces another.

Investment Decision identity is opaque. It is not a hash of Subject, Scope, Evidence, Recommendation, Portfolio State, or runtime metadata.

## 2.2 Decision Need

A **Decision Need** is the attributable reason deliberate investment judgment is required.

R2 makes Decision Need durable because `DEC-002` requires every Investment Decision to be grounded in one and later history must explain why the decision existed.

The R2 semantic shape includes:

- durable `DecisionNeedId`;
- concise need statement;
- time the need was raised/recognized;
- attributable origin reference;
- optional source/context references that explain the triggering matter.

R2 does not implement the full future Attention engine. The origin representation must be able to preserve user, scheduled, or system-detected provenance later without forcing a new Decision Need model.

## 2.3 Decision Subject

Decision Subject identifies what the judgment is about.

It is distinct from Investment Decision identity and Decision Scope.

R2 treats Subject as a stable typed reference, not as the primary key of the Decision. Multiple Investment Decisions may concern the same Subject over time.

## 2.4 Decision Scope

Decision Scope describes the boundaries of the coherent choice under consideration.

It may include portfolio/instrument/horizon or other canonical scope dimensions as applicable, but it is not itself the Investment Decision identity.

A Scope revision during unresolved work does not automatically create a new Investment Decision. If the coherent choice remains the same, the Decision keeps its ID and the change is preserved historically.

R2 therefore treats material Subject/Scope changes as explicit lifecycle-supporting facts rather than silently overwriting earlier values.

## 2.5 Causal relationships

R2 distinguishes at least these relationships:

- **renewed from** — a new Investment Decision created after a prior Decision was already substantively or externally resolved because deliberate judgment is needed again;
- **supersedes** — a new Investment Decision intentionally replaces another Investment Decision before the predecessor would otherwise continue as the active choice.

These relationships never merge histories or reuse the predecessor Decision ID.

---

# 3. Lifecycle state model

R2 uses five externally meaningful lifecycle states:

```text
ACTIVE
DEFERRED
RESOLVED
EXTERNALLY_RESOLVED
SUPERSEDED
```

`ACTIVE` and `DEFERRED` are unresolved states.

`RESOLVED`, `EXTERNALLY_RESOLVED`, and `SUPERSEDED` are terminal for that Investment Decision identity.

A terminal Investment Decision never returns to `ACTIVE` or `DEFERRED`.

## 3.1 State semantics

### ACTIVE

The coherent choice remains unresolved and decision work may proceed.

### DEFERRED

The coherent choice remains unresolved, but deliberate work is intentionally paused. Deferral is not a negative Recommendation, Human Investment Decision, no-action resolution, or External Resolution.

### RESOLVED

The coherent choice has been substantively answered through an attributable resolution basis.

R2 owns this lifecycle state but does **not** own the future Governance fact—such as Human Investment Decision—that may justify it.

### EXTERNALLY_RESOLVED

Circumstances eliminated the Decision Need before substantive human resolution.

No Human Investment Decision may be inferred merely because the Decision became externally resolved.

### SUPERSEDED

Another explicit Investment Decision replaces this Decision as the active unresolved choice. The predecessor remains permanently inspectable and links to the successor.

---

# 4. Lifecycle facts

Current state is reconstructable from immutable lifecycle facts. The canonical R2 fact set is conceptually:

```text
DecisionInitiated
DecisionSubjectRevised
DecisionScopeRevised
DecisionDeferred
DecisionResumed
DecisionResolved
DecisionExternallyResolved
DecisionSuperseded
```

A renewed Decision is represented by a new `DecisionInitiated` fact on a new Decision with a `renewed_from` relationship. It is not a reopening fact on the old Decision.

The names above describe semantics, not mandatory Python class names.

## 4.1 Fact requirements

Every lifecycle fact preserves at least:

- unique fact identity;
- Investment Decision identity;
- per-decision monotonic sequence/version;
- fact kind;
- effective/occurred time supplied or established by the use case;
- durable recorded/committed time;
- operation/idempotency identity;
- attributable initiating context appropriate to the fact;
- related Decision identity when the fact represents renewal or Supersession;
- typed fact-specific content.

Facts are immutable after commit.

Later correction, if eventually required, must be represented explicitly rather than editing an older fact in place.

---

# 5. Transition table

| Current state | Operation | Result state | Same Decision ID? | Required durable fact | Notes |
|---|---|---:|---:|---|---|
| none | initiate | ACTIVE | new | DecisionInitiated | Establishes Decision Need, Subject, Scope, version 1. |
| ACTIVE | revise Subject | ACTIVE | yes | DecisionSubjectRevised | Must not manufacture a new Decision when coherent choice remains same. |
| DEFERRED | revise Subject | DEFERRED | yes | DecisionSubjectRevised | Revision alone does not resume work. |
| ACTIVE | revise Scope | ACTIVE | yes | DecisionScopeRevised | Same-choice rule applies. |
| DEFERRED | revise Scope | DEFERRED | yes | DecisionScopeRevised | Same-choice rule applies. |
| ACTIVE | defer | DEFERRED | yes | DecisionDeferred | Remains unresolved. |
| DEFERRED | resume | ACTIVE | yes | DecisionResumed | Resumes same identity. |
| ACTIVE | resolve substantively | RESOLVED | yes | DecisionResolved | Requires attributable resolution basis; does not fabricate Governance fact. |
| DEFERRED | resolve substantively | RESOLVED | yes | DecisionResolved | Explicit resolution may terminate deferred work without a ceremonial resume. |
| ACTIVE | externally resolve | EXTERNALLY_RESOLVED | yes | DecisionExternallyResolved | Must record external-resolution basis; no Human Investment Decision inferred. |
| DEFERRED | externally resolve | EXTERNALLY_RESOLVED | yes | DecisionExternallyResolved | Same rule. |
| ACTIVE | supersede | SUPERSEDED | predecessor no; successor new | DecisionSuperseded + successor DecisionInitiated | Must be one semantic atomic operation. |
| DEFERRED | supersede | SUPERSEDED | predecessor no; successor new | DecisionSuperseded + successor DecisionInitiated | Must be one semantic atomic operation. |
| RESOLVED | renewed judgment | RESOLVED + new ACTIVE | old no; new yes | successor DecisionInitiated with renewed_from | Old Decision remains untouched. |
| EXTERNALLY_RESOLVED | renewed judgment | EXTERNALLY_RESOLVED + new ACTIVE | old no; new yes | successor DecisionInitiated with renewed_from | Same rule. |
| SUPERSEDED | any reopen/resume/defer | invalid | — | none | Terminal Decisions never reopen. |
| RESOLVED | resume/defer/re-resolve | invalid | — | none | Renewed work uses a new Decision. |
| EXTERNALLY_RESOLVED | resume/defer/re-resolve | invalid | — | none | Renewed work uses a new Decision. |

---

# 6. Same Decision vs new Decision

Polaris must not infer Decision identity mechanically from Subject/Scope or from a change in Evidence/Recommendation.

R2 therefore uses an explicit continuity model:

1. **Resume existing** — caller/use case identifies the existing unresolved Investment Decision being continued.
2. **Create new** — caller/use case explicitly establishes a new coherent unresolved choice.
3. **Renew after terminal resolution** — new Decision explicitly references the prior terminal Decision through `renewed_from`.
4. **Supersede** — one atomic use case terminates the predecessor as `SUPERSEDED` and creates the successor with an explicit relationship.

R2 does not introduce a new universal `DecisionThread`, `ContinuityKey`, or hash-derived identity abstraction merely to automate this judgment.

Later Attention logic may search Decision Memory for candidate unresolved Decisions and determine whether material change resumes one or creates another. That later decision must still obey these identity rules.

---

# 7. Resolution seam with Governance

This is the most important cross-entity R2 seam.

## 7.1 Ownership split

- `investment-decisions` owns the lifecycle fact that a Decision is substantively resolved.
- `governance-authority` owns Human Investment Decision and other power-specific authority acts.

R2 must not collapse those into one object.

## 7.2 Resolution basis

A substantive resolution transition requires an attributable **resolution basis reference** supplied through Application Use Cases.

The Decisions domain only needs to know enough to preserve:

- that the basis is a valid business fact/reference from an allowed source category;
- the referenced fact identity;
- the time the substantive resolution became effective;
- optional human-readable resolution summary appropriate to Decision lifecycle history.

The Decisions domain does not duplicate the Human Investment Decision payload or authority evaluation.

## 7.3 R2 behavior before Governance exists

R2 may implement the domain/application contract for substantive resolution and test it with a deterministic trusted fixture representing an external resolution-basis owner.

R2 must **not** expose a user-facing or generic public API that lets an arbitrary caller self-assert a Human Investment Decision or authority act.

When Governance is implemented later, its application path will produce the authoritative Human Investment Decision fact/reference and then coordinate the Decisions resolution transition atomically where required.

---

# 8. External Resolution seam

External Resolution requires a basis describing the circumstance that eliminated the Decision Need.

The R2 semantic record preserves:

- source/basis reference where one exists;
- attributable explanation;
- effective time;
- recorded time.

The External Resolution transition must not create:

- Human Investment Decision;
- Recommendation;
- Action Intent;
- implied approval or denial.

Later external-fact integration may provide richer typed source references without redefining the Decisions lifecycle.

---

# 9. Supersession semantics

Supersession is a two-Decision operation.

The operation must atomically establish:

1. predecessor remains durably identifiable;
2. predecessor gains terminal `SUPERSEDED` state;
3. successor gets a new Investment Decision identity;
4. successor is grounded in a Decision Need;
5. explicit predecessor/successor relationship is preserved;
6. no history is copied or rewritten as though it belonged to the successor.

The successor may reference inherited context in future use cases, but inherited context does not transfer ownership of predecessor facts.

---

# 10. Temporal model

R2 preserves two time concepts on lifecycle facts:

- **effective/occurred time** — when the business lifecycle event is understood to have occurred;
- **recorded/committed time** — when Polaris durably knew/recorded the fact.

This dual-time preservation is required so later historical reasoning can distinguish late-recorded facts from facts actually known at an earlier point.

## 10.1 Historical query default

The safe historical default is **as-known-at** reconstruction:

> Return only facts committed no later than the requested knowledge cutoff, then derive the lifecycle state from that fact set.

A later-recorded fact with an earlier effective time must not silently appear in an earlier as-known-at view.

R2 may also expose effective-time information for analysis, but it must not confuse effective time with Judgment-Time Availability.

Full Evidence Judgment-Time Availability belongs to the Evidence owner and later milestones.

---

# 11. Version and concurrency semantics

Each Investment Decision has a monotonic domain version.

Rules:

- initiation establishes version 1;
- each committed lifecycle mutation increments the version exactly once;
- every mutating command against an existing Decision supplies an expected version;
- stale expected version produces an explicit concurrency conflict rather than overwriting newer truth;
- retry of the same successfully committed operation returns the original semantic result rather than creating another lifecycle fact;
- two different commands using the same idempotency identity with different semantic payloads produce an idempotency conflict.

The version is business concurrency metadata, not database row identity.

---

# 12. Invalid-transition behavior

Invalid transitions are domain outcomes, not generic infrastructure errors.

The R2 domain/application contract must distinguish at least:

- Decision not found;
- Decision already terminal;
- resume attempted when not deferred;
- defer attempted when already deferred under a different operation;
- stale expected version;
- idempotency key reused for a different command payload;
- invalid/missing substantive resolution basis;
- invalid/missing External Resolution basis;
- invalid Supersession relationship such as self-supersession;
- causal relationship to a non-terminal predecessor where `renewed_from` requires terminal history.

Error names are implementation details, but callers must be able to distinguish these meanings deterministically.

---

# 13. Domain construction and mutation rules

The domain model should expose behavior rather than allow arbitrary state mutation.

A practical R2 shape is:

```text
InvestmentDecision
  - current immutable identity values
  - current lifecycle state
  - current version
  - behavior methods that return typed lifecycle changes/facts

DecisionLifecycleFact
  - immutable typed history
```

The implementation must not expose public setters that allow callers to assign `status = RESOLVED` or rewrite version/history directly.

Persistence reconstruction may use an internal rehydration path, but that path must not become a general application mutation bypass.

---

# 14. R2 domain test matrix

Pure domain tests must cover at least:

## Identity

- same Subject can have multiple Decisions over time;
- same Scope can have multiple Decisions over time;
- changed Evidence/Portfolio/Risk/Recommendation does not change Decision ID;
- workflow/job/report/model IDs do not participate in Decision ID.

## Deferral/resumption

- ACTIVE → DEFERRED keeps ID;
- DEFERRED → ACTIVE keeps ID;
- repeated retry does not duplicate fact;
- terminal Decision cannot resume.

## Resolution

- ACTIVE/DEFERRED may resolve with valid attributable basis;
- resolution basis is referenced, not copied into Decisions ownership;
- terminal Decision cannot reopen;
- new judgment after resolution creates a new Decision with `renewed_from`.

## External Resolution

- ACTIVE/DEFERRED may become EXTERNALLY_RESOLVED;
- no Human Investment Decision is created or implied;
- renewed judgment creates a new linked Decision.

## Supersession

- predecessor and successor IDs differ;
- predecessor becomes terminal SUPERSEDED;
- both histories remain queryable;
- self-supersession and cycles are rejected;
- predecessor history is not copied as successor-owned facts.

## Temporal/version behavior

- fact sequence/version is monotonic;
- stale expected version is rejected;
- as-known-at reconstruction excludes later-recorded facts;
- historical states remain stable after later lifecycle changes.

---

# 15. Requirements traceability

| Requirement | Design consequence |
|---|---|
| `GF-001`, `GF-005` | Decision ID is first-class and independent of runtime/persistence identity. |
| `DEC-001` | Opaque durable Decision ID plus explicit lifecycle root. |
| `DEC-002` | Durable attributable Decision Need. |
| `DEC-003`, `DEC-004` | Subject/Scope/context changes do not automatically create new Decision identity. |
| `DEC-005` | Unresolved lifecycle supports iterative work without identity replacement. |
| `DEC-006` | DEFERRED remains unresolved and resumable. |
| `DEC-008` | EXTERNALLY_RESOLVED is distinct and does not invent Human Investment Decision. |
| `DEC-009`, `DEC-010` | Terminal Decisions never reopen; renewed work creates linked new identity. |
| `DEC-011` | Supersession preserves both histories and explicit relationship. |
| `DEC-012` | Immutable lifecycle facts + effective/recorded times support reconstruction. |
| `MEM-*` | Decision history remains direct business truth independent of runtime replay. |
| `TMP-*` | Dual-time preservation leaves judgment-time faithful reconstruction possible. |
| `AS-001`–`AS-005` | Transition/test matrix supplies objective R2 evidence. |
| `AS-022` | Domain model contains no legacy dependency. |

---

# 16. Out of scope for this design

This design does not define:

- Evidence data structures or binding model beyond references;
- Recommendation/View schemas;
- Human Investment Decision payload or authority evaluation;
- Action Intent;
- Outcome/Evaluation/Lesson;
- Attention heuristics for deciding same-vs-new Decision automatically;
- PostgreSQL tables or ORM classes;
- interface protocol;
- worker/event/outbox architecture;
- generic correction framework;
- legacy data migration.

---

# 17. Spec-readiness gate

This design is ready to feed Specs only after review confirms:

1. the five lifecycle states are sufficient and semantically non-overlapping;
2. substantive resolution ownership is correctly split from Governance;
3. Supersession and renewal relationships are unambiguous;
4. dual-time history is sufficient for R2 without pretending full Evidence temporality is implemented;
5. idempotency/version rules are precise enough for the application and persistence designs;
6. no implementation agent must invent same-vs-new Decision semantics or terminal transition rules.
