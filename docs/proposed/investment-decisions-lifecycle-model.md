# Investment Decision Lifecycle Model

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `investment-decisions`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define the R2 Investment Decision domain model precisely enough that Specs do not invent identity, lifecycle dimensions, continuity, actor attribution, temporal correction, or cross-owner semantics.

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

---

# 1. Design objective

R2 establishes a durable Investment Decision identity/history that remains coherent through unresolved Scope, changing context, Deferral, work withdrawal, substantive human judgment, External Resolution, erroneous Need correction, Supersession, renewal, retries, concurrent initiation, process restart, late facts, and explicit non-destructive correction.

The model must not depend on workflow, job, report, model/provider, or database identity.

---

# 2. Identity concepts

## 2.1 Investment Decision

An **Investment Decision** is one durable identified lifecycle established to resolve one coherent Portfolio-relevant investment choice.

It has:

- durable `InvestmentDecisionId`;
- exactly one grounding `DecisionNeedId`;
- current Decision Subject;
- Decision Scope with explicit completeness state;
- current supported Decision Need status;
- current supported judgment-resolution status;
- current work posture when judgment work remains operative;
- typed Decision relationships;
- monotonic recorded domain version;
- immutable creation time.

Identity is opaque and is not derived from Subject, Scope, Evidence, Recommendation, Portfolio State, text similarity, or runtime identity.

## 2.2 Decision Need

A **Decision Need** is the attributable determination that one coherent unresolved Portfolio-relevant choice warrants deliberate judgment.

R2 rules:

- one Investment Decision has exactly one grounding Decision Need;
- one Decision Need grounds at most one Investment Decision;
- if discovery reveals independently resolvable choices, establish distinct Decision Needs/Decisions rather than sharing one Need as identity glue;
- later triggers/observations may contribute to the existing Decision without creating a duplicate Need merely because initiation happens again;
- the original Need determination is durable even if later found unsupported.

Preserve:

- Need ID;
- concise original determination;
- effective recognized time;
- recorded time;
- Actor Attribution for the determination where material;
- trigger/origin provenance separately;
- optional supporting source/context references;
- later explicit correction/retraction facts.

## 2.3 Decision Subject

Decision Subject identifies the investment matter being judged and is distinct from Decision identity, Scope, Evidence, trigger, and implementation instrument.

Subject may be composite when components form one mutually dependent choice. A material Subject refinement may preserve Decision identity when the coherent unresolved choice remains the same.

## 2.4 Decision Scope

Decision Scope identifies the Portfolio or Portfolios directly implicated.

R2 must support **partial knowledge**, not only null-vs-complete Scope.

Conceptually:

```text
DecisionScope
    confirmed_portfolio_refs: zero or more
    completeness: UNRESOLVED | ESTABLISHED
```

Rules:

- `UNRESOLVED` may contain zero or some already-confirmed Portfolios while applicability remains incomplete;
- `ESTABLISHED` means the applicable Portfolio set is sufficiently established for the supported use at that time;
- no default/empty Portfolio ID may masquerade as unresolved Scope;
- Scope establishment/refinement is historical fact;
- later capital-relevant Recommendation/Human Investment Decision must not silently use incomplete Scope.

---

# 3. Actor Attribution vs provenance

R2 uses a small domain-recognized actor reference sufficient for durable attribution, conceptually supporting:

```text
POLARIS
HUMAN(<stable actor reference>)
ORGANIZATION_OR_COLLECTIVE(<stable reference>)
EXTERNAL_ACTOR(<stable reference>)
UNKNOWN_OR_DISPUTED(<preserved status/reference>)
```

Exact class/enum names are implementation details.

Internal model/provider/tool/workflow identities are technical provenance, not Actor Attribution.

Preserve separately:

```text
Actor Attribution
Who formed/performed the domain act?

Trigger/source provenance
What request, observation, schedule, source fact, or event caused work?

Technical provenance
Which model/provider/tool/work attempt contributed technically?
```

---

# 4. Lifecycle uses four independent dimensions

A single status enum is explicitly rejected.

## 4.1 Decision Need status

```text
ACTIVE
EXTERNALLY_ELIMINATED
RETRACTED_UNSUPPORTED
```

### ACTIVE

The Decision Need is currently supported as a real unresolved choice unless judgment has substantively resolved it.

### EXTERNALLY_ELIMINATED

Circumstances external to the unresolved judgment eliminated the underlying choice. This is the Need-side meaning of **External Resolution**.

### RETRACTED_UNSUPPORTED

Later attributable correction establishes that the original Need determination was erroneous or unsupported, rather than a genuine choice eliminated by changed circumstances.

Need status can be corrected after other historical acts. Retraction never erases earlier human/model work that actually occurred.

## 4.2 Judgment-resolution status

```text
UNRESOLVED
SUBSTANTIVELY_RESOLVED
```

This axis answers whether an attributable substantive investment judgment resolved the choice.

A Human Investment Decision can exist without causing `SUBSTANTIVELY_RESOLVED` (for example Deferral or rejection requesting more analysis).

If later correction establishes that the Need had already been externally eliminated or unsupported before a recorded Decisions-side resolution consequence, the historical Human Investment Decision remains, while an explicit lifecycle correction may qualify/reverse the supported Decisions-side `SUBSTANTIVELY_RESOLVED` interpretation.

## 4.3 Work posture

When Need status is `ACTIVE`, judgment status is `UNRESOLVED`, and the Decision is currently operative, work posture may be:

```text
ACTIVE
DEFERRED
WITHDRAWN
```

### ACTIVE

Decision work may proceed.

### DEFERRED

An attributable **Human Investment Decision of Deferral** postpones substantive judgment while Need remains active/unresolved.

### WITHDRAWN

Current Polaris work is explicitly stopped without itself making an investment judgment. Need may remain active.

## 4.4 Continuing applicability / Supersession

Supersession is a typed graph relationship, not any of the three axes above.

A Decision may be superseded while unresolved, deferred, withdrawn, substantively resolved, externally eliminated, or later corrected.

Supersession changes continuing applicability/operative basis without rewriting Need status, historical work posture, or judgment history.

A currently superseded unresolved Decision is non-operative for ordinary direct work while the relationship remains supported.

---

# 5. External Resolution is a compound semantic outcome

External Resolution means:

```text
Decision Need status = EXTERNALLY_ELIMINATED
and
no supported substantive judgment was required to eliminate that Need
```

Canonical invariant:

> External Resolution resolves the Decision Need, not the judgment.

No Human Investment Decision is inferred.

If a human judgment was nevertheless recorded because the eliminating circumstance was not yet known, preserve the human act and use explicit correction to qualify the Decisions-side lifecycle interpretation.

---

# 6. Canonical R2 facts

Conceptual immutable facts:

```text
DecisionInitiated
DecisionSubjectRevised
DecisionScopeEstablishedOrRefined
DecisionDeferred
DecisionWorkResumed
DecisionWorkWithdrawn
DecisionSubstantivelyResolved
DecisionNeedExternallyEliminated
DecisionNeedRetracted
DecisionLifecycleCorrected
```

Decision relationships (`RENEWED_FROM`, `SUPERSEDES`) are separate durable relationship facts.

Every fact preserves at least:

- fact ID;
- Decision ID;
- recorded sequence/version;
- kind;
- effective time;
- recorded/committed time;
- operation ID;
- Actor Attribution where applicable;
- trigger/technical provenance separately where material;
- typed basis/reference;
- correction target/reference when applicable;
- typed payload.

Facts are immutable after commit.

---

# 7. Operation matrix

| Need | Judgment | Work | Operation | Result | Durable fact |
|---|---|---|---|---|---|
| none | none | none | initiate | `ACTIVE / UNRESOLVED / ACTIVE` | `DecisionInitiated` |
| `ACTIVE` | `UNRESOLVED` | any | establish/refine Scope | axes unchanged | `DecisionScopeEstablishedOrRefined` |
| `ACTIVE` | `UNRESOLVED` | any | revise Subject | axes unchanged | `DecisionSubjectRevised` |
| `ACTIVE` | `UNRESOLVED` | `ACTIVE` or `WITHDRAWN` | trusted Human Deferral | work=`DEFERRED` | `DecisionDeferred` |
| `ACTIVE` | `UNRESOLVED` | `DEFERRED` | new Human Deferral | remains `DEFERRED` | new `DecisionDeferred` |
| `ACTIVE` | `UNRESOLVED` | `DEFERRED`/`WITHDRAWN` | resume | work=`ACTIVE` | `DecisionWorkResumed` |
| `ACTIVE` | `UNRESOLVED` | `ACTIVE`/`DEFERRED` | withdraw work | work=`WITHDRAWN` | `DecisionWorkWithdrawn` |
| `ACTIVE` | `UNRESOLVED` | any operative posture | substantive resolution basis | judgment=`SUBSTANTIVELY_RESOLVED`; work n/a | `DecisionSubstantivelyResolved` |
| `ACTIVE` | `UNRESOLVED` | any | external circumstance eliminates Need | need=`EXTERNALLY_ELIMINATED`; work n/a | `DecisionNeedExternallyEliminated` |
| `ACTIVE` | any | any/n/a | later correction shows Need was unsupported | need=`RETRACTED_UNSUPPORTED`; other historical facts preserved/qualified as needed | `DecisionNeedRetracted` + correction if required |
| any | any | any | record Supersession | axes unchanged; applicability edge added | `SUPERSEDES` relationship |
| any | any | any | late lifecycle correction | supported projection changes non-destructively | `DecisionLifecycleCorrected` |

## 7.1 Re-Deferral

A new Human Investment Decision may defer an already deferred unresolved Decision again, for example to replace/extend an awaited condition. Append a new `DecisionDeferred` fact; do not overwrite the earlier Deferral or require a ceremonial resume.

## 7.2 Deferral from withdrawn work

A human may form a Deferral judgment while work is withdrawn; the trusted human basis may move the unresolved Decision directly to `DEFERRED` without an artificial `ACTIVE` transition.

---

# 8. Same Decision vs new Decision

Continuity outcomes:

1. continue existing unresolved Decision;
2. create new independent Decision;
3. renew after prior substantive resolution/External Resolution using new Decision + `RENEWED_FROM`;
4. supersede one or more earlier Decisions using explicit relationships;
5. ambiguity -> create nothing automatically.

No universal DecisionThread/hash identity is introduced.

## 8.1 R2 continuity candidate policy

To avoid a Spec inventing a hidden matching heuristic, **R2 may initially return all currently unresolved, non-superseded Decisions as the continuity candidate set**. The expected R2 scale makes correctness more important than optimization.

The application/caller makes an explicit continue/new/ambiguous determination.

Later Attention may introduce owner-approved narrowing/ranking without changing Decision identity semantics.

## 8.2 Concurrent initiation

A new Decision commit must atomically revalidate that the unresolved candidate set used for the continuity determination has not changed materially.

At R2 scale, the initial adapter may serialize Decision initiation globally if that is the smallest correct implementation. That is an adapter/concurrency choice, not business identity.

If another initiation commits first, the later operation re-queries/re-evaluates rather than silently creating another Decision.

---

# 9. Deferral / Governance seam

Canonical Deferral is Governance-owned Human Investment Decision.

Decisions records only the work-posture consequence from a trusted typed basis.

An awaited condition for a deferred unresolved Decision is not a Review Condition.

R2 uses trusted deterministic fixture references in tests and exposes no public authority bypass.

---

# 10. Substantive resolution / Governance seam

A Decisions-side substantive resolution requires an allowed attributable resolution-basis reference.

Preserve:

- basis fact identity/category;
- effective time;
- optional summary;
- actor/reference provenance as appropriate.

Do not duplicate Governance payload/authority evaluation.

---

# 11. Decision Need retraction

Retraction may occur while unresolved or after other historical acts.

Example after human judgment:

```text
09:00 Decision Need established
10:00 Human Investment Decision recorded
11:00 authoritative correction proves initiating Portfolio fact was wrong
```

Required behavior:

- original Need remains historical;
- Human Investment Decision remains historical;
- Need status may become `RETRACTED_UNSUPPORTED`;
- any Decisions-side lifecycle interpretation made invalid by that correction is qualified through explicit `DecisionLifecycleCorrected` rather than deletion;
- this is not External Resolution.

A later genuine supported choice establishes a new Need/Decision rather than silently treating the erroneous Need as always valid.

---

# 12. Work withdrawal

Withdrawal may be attributable to human, Polaris operating logic, or another permitted actor/process and means only that current work stops.

It does not imply Human Investment Decision, Deferral, External Resolution, substantive resolution, or Supersession.

Same-choice work may resume under the same Decision if Need remains active, judgment unresolved, and Decision operative.

---

# 13. Supersession

Defined in the relationship model.

Key lifecycle consequence:

- it never changes Need/judgment/work historical facts merely to represent displacement;
- resolved Decisions remain resolved historically;
- unresolved superseded Decisions become non-operative through the relationship, not through a fake terminal status.

---

# 14. Temporal model and correction

Preserve:

- effective time;
- recorded/committed time;
- monotonic recorded sequence/version.

## 14.1 `as_known_at(K)`

Use only facts/relationships/corrections recorded by knowledge cutoff `K`.

Answers what Polaris durably knew then.

## 14.2 `effective_at(T, knowledge_cutoff=K)`

Using only knowledge recorded by `K`, answer what Need/judgment/work/applicability state is supported as having been effective at time `T`.

Default `K=now` gives current best supported effective history.

This is Decision lifecycle reconstruction, not Evidence Judgment-Time Availability.

## 14.3 Late conflicting facts

Example:

```text
10:00 circumstance actually eliminates Need
10:05 Human Investment Decision recorded; Polaris does not know 10:00 fact
10:10 10:00 fact becomes known
```

Preserve:

- the Human Investment Decision;
- any earlier Decisions-side resolution fact as recorded history;
- a later correction showing Need status `EXTERNALLY_ELIMINATED` effective 10:00;
- correction/qualification of the Decisions-side substantive-resolution interpretation if it is no longer supported;
- `as_known_at(10:06)` as what Polaris knew then;
- current effective history using the correction.

Correction identifies exactly which prior fact/interpretation it qualifies so competing current truth is not ambiguous.

---

# 15. Version / concurrency semantics

- initiation establishes recorded Decision version 1;
- each lifecycle mutation/correction increments version once;
- expected-version checks prevent stale overwrite;
- idempotent replay returns prior semantic result;
- same operation/different semantic request conflicts;
- continuity arbitration separately protects different operation IDs;
- relationship operations use expected versions/conflict detection when they change operability.

Version orders recorded knowledge; it is not effective time.

---

# 16. Domain construction shape

Conceptually:

```text
InvestmentDecision
  identity
  DecisionNeed identity + supported Need status
  Subject
  Scope { confirmed Portfolios, completeness }
  judgment-resolution status
  work posture when applicable
  version

DecisionLifecycleFact
  immutable fact/correction history

DecisionRelationship
  immutable typed graph relationship
```

No public arbitrary status setters.

---

# 17. Required domain tests

## Identity / Need

- one Decision -> exactly one Need;
- one Need cannot silently ground multiple Decisions;
- multiple independently resolvable choices require distinct Needs;
- runtime IDs do not influence Decision identity.

## Scope

- zero-known-Portfolio unresolved Scope valid;
- partially known Scope valid with `UNRESOLVED` completeness;
- establishment/refinement preserves Decision ID/history;
- empty/default Portfolio is not used as unresolved marker.

## Actor/provenance

- trigger and actor can differ;
- Polaris can be actor;
- model/provider/workflow cannot become actor by technical participation;
- unknown/disputed historical attribution can remain explicit.

## Deferral / work

- Deferral requires trusted human basis;
- ACTIVE -> DEFERRED;
- WITHDRAWN -> DEFERRED with human basis;
- DEFERRED -> DEFERRED re-deferral appends fact;
- awaited condition may resume same Decision;
- Review Condition does not resume resolved Decision;
- withdrawal creates no Human Investment Decision/resolution.

## Need / judgment

- substantive resolution changes judgment axis only;
- External Resolution changes Need axis, not judgment axis;
- Need retraction can occur after recorded human judgment without erasing it;
- corrected unsupported Need is not External Resolution.

## Supersession / renewal

- resolved predecessor may be superseded without resolution rewrite;
- unresolved predecessor may be superseded and become non-operative;
- renewed judgment creates new ID/relationship.

## Continuity

- different concurrent initiation operations cannot silently both create new Decisions after candidate set changes;
- ambiguity creates no Decision.

## Temporal correction

- as-known-at excludes later facts/corrections;
- effective-at may change under later knowledge;
- correction is append-only and identifies corrected interpretation;
- late External Resolution preserves later human act.

---

# 18. Requirements traceability

| Requirement | Consequence |
|---|---|
| `DEC-001`–`DEC-004` | explicit Need/Decision identity and same-choice continuity. |
| `DEC-006` | Deferral is human basis + unresolved work posture. |
| `DEC-008` | External Resolution changes Need status without inventing human judgment. |
| `DEC-009`–`DEC-012` | renewal/non-reopening/historical reconstruction. |
| `DEC-013` | partial/unresolved Scope. |
| `DEC-014` | work withdrawal distinct from judgment. |
| `DEC-015` | Need retraction non-destructive even after other acts. |
| `DEC-016` | Supersession orthogonal. |
| `DEC-017` | concurrent initiation revalidates continuity. |
| `DEC-018` | late facts + dual temporal history + correction. |
| `DEC-019` | actor distinct from provenance. |
| `MEM-*` | direct immutable Decision Memory basis. |
| `REL-*` | retry/concurrency/recovery. |

---

# 19. Out of scope

R2 does not implement full Attention, Evidence, Recommendation, Governance/Human Decision persistence, Review Conditions, Action Continuity, Learning, generic event sourcing, or generic cross-domain correction framework.

---

# 20. Spec-readiness gate

This design is ready for Specs only when review confirms:

1. Need status, judgment resolution, work posture, and Supersession are independent;
2. External Resolution literally changes Need status rather than pretending to be substantive judgment;
3. Need retraction may qualify history even after human judgment without deleting it;
4. Scope supports partial knowledge/completeness;
5. actor categories/provenance separation are sufficient;
6. re-Deferral and withdrawal edge cases are deterministic;
7. R2 continuity candidate policy no longer requires a Spec to invent matching heuristics;
8. late corrections and dual temporal queries are deterministic;
9. no Spec must invent remaining lifecycle semantics.
