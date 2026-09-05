# Application Use Cases for the Investment Decision Lifecycle

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `application-use-cases`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define the R2 application command/query contracts, continuity arbitration, transaction boundaries, idempotency, concurrency, actor/provenance handling, temporal correction, and cross-entity seams for the Investment Decision lifecycle.

## Authority

This design refines:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md);
- [`investment-decisions-lifecycle-model.md`](investment-decisions-lifecycle-model.md);
- [`investment-decisions-decision-relationship-model.md`](investment-decisions-decision-relationship-model.md);
- [`investment-decisions-r2-decision-kernel-component-boundaries.md`](investment-decisions-r2-decision-kernel-component-boundaries.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md);
- accepted ADRs under [`../adr/`](../adr/).

Application use cases coordinate owner behavior and technology-neutral ports. They do not create a second domain model.

---

# 1. R2 application surface

Conceptual command responsibilities:

```text
initiate_decision
establish_decision_scope
revise_decision_subject
revise_decision_scope
record_deferral_consequence
resume_decision_work
withdraw_decision_work
record_substantive_resolution
externally_resolve_decision
retract_unsupported_decision_need
initiate_renewed_decision
record_supersession
correct_decision_lifecycle
```

Conceptual query responsibilities:

```text
get_decision
get_decision_history
get_decision_as_known_at
get_decision_effective_at
find_unresolved_decisions_for_continuity
get_decision_lineage
```

Names are semantic responsibilities, not mandated Python symbols.

R2 does not expose Recommendation, Governance, Attention, Action Intent, or Learning APIs.

---

# 2. Command envelope

Every mutating R2 command carries application-owned metadata independent of database/broker technology:

- operation/idempotency identity;
- command kind;
- Actor Attribution or trusted actor reference where the command establishes an attributable domain act;
- trigger/origin provenance separately from Actor Attribution;
- requested effective time only when caller legitimately knows it, otherwise application clock time;
- expected Decision version(s) for mutations of existing Decisions;
- command-specific payload.

The envelope must not contain:

- ORM session/database transaction;
- SQL expression;
- broker-native message;
- workflow/job identity as business identity;
- model/provider identity as Actor Attribution;
- vendor SDK request type.

Technical request/work identifiers may be carried separately for observability/correlation.

---

# 3. Semantic result model

Commands return success only after required durable commit succeeds.

A successful result contains the minimum useful combination of:

- affected Decision ID(s);
- resulting resolution/work disposition where applicable;
- resulting Decision version(s);
- committed lifecycle/relationship fact IDs where useful;
- whether result is newly committed or idempotent replay.

Queries return application-owned Decision Memory/read models, never persistence rows.

---

# 4. Error/outcome model

R2 callers must distinguish at least:

| Meaning | Caller consequence |
|---|---|
| Decision not found | Target identity absent. |
| Invalid lifecycle operation | Command incompatible with supported disposition/work state. |
| Decision currently superseded/non-operative | Direct mutation is not allowed without correcting supersession. |
| Concurrency conflict | Expected version stale; reload/re-evaluate. |
| Continuity conflict | Candidate set changed between continuity determination and initiation commit. |
| Continuity ambiguous | Same-vs-new Decision cannot be determined reliably; no new Decision committed. |
| Idempotency conflict | Same operation ID reused for materially different request. |
| Scope state invalid | Establish/revise operation inconsistent with current Scope state. |
| Deferral basis invalid/missing | Human Deferral consequence cannot be recorded. |
| Resolution basis invalid/missing | Substantive resolution cannot proceed. |
| External-resolution basis invalid/missing | External Resolution cannot proceed. |
| Need-retraction basis invalid/missing | Unsupported Need correction cannot proceed. |
| Relationship conflict | Invalid renewal/Supersession/cycle semantics. |
| Lifecycle correction conflict | Correction fails to identify the prior interpretation/fact it qualifies. |
| Persistence unavailable/commit failed | No success returned. |

Transport mapping belongs to future interfaces.

---

# 5. Initiation and continuity arbitration

## 5.1 Inputs

- operation ID;
- Decision Need content;
- Decision Subject;
- Decision Scope value **or explicit unresolved Scope**;
- Actor Attribution for Decision Need determination where material;
- trigger/origin provenance;
- explicit continuity determination based on the current candidate set: `CREATE_NEW`, `CONTINUE_EXISTING(<id>)`, or `AMBIGUOUS`;
- continuity observation token/version or equivalent semantic guard supplied by the continuity query/transaction boundary.

`renewed_from` and Supersession are separate relationship semantics and are not overloaded onto ordinary new initiation.

## 5.2 Behavior

If continuity determination is `CONTINUE_EXISTING`, initiation does not create a new Decision; the caller proceeds through the appropriate existing-Decision use case.

If `AMBIGUOUS`, no Decision is created.

For `CREATE_NEW`:

1. check operation idempotency;
2. validate Need/Subject/Scope representation;
3. revalidate continuity basis atomically against current unresolved candidates;
4. if the candidate basis changed or now creates material ambiguity, fail with `ContinuityConflict`/`ContinuityAmbiguous`;
5. ask Decisions domain to establish Decision Need + Investment Decision;
6. atomically persist Need, current state, initial fact, any initiation relationships, and command receipt;
7. return success after durable commit.

## 5.3 Why operation idempotency is insufficient

Two different operation IDs can race to represent the same coherent unresolved choice. R2 therefore requires continuity arbitration in addition to idempotency.

The persistence adapter may implement this with serializable semantics, locks, bounded generation/version guards, or another correct mechanism; the application contract is only the fail-closed behavior.

---

# 6. Scope establishment/revision

## Establish unresolved Scope

Inputs:

- operation ID;
- Decision ID;
- expected version;
- established Scope;
- attributable basis/provenance.

Valid only when Scope is explicitly unresolved.

Produces `DecisionScopeEstablished`; preserves Decision ID.

## Revise established Scope

Valid for unresolved, currently operative Decision work when the coherent choice remains the same.

Produces `DecisionScopeRevised`; does not manufacture new identity.

If changing Scope reveals that a different coherent choice is now required, caller must use explicit new/renew/supersession semantics.

---

# 7. Subject revision

Explicit Subject revision is allowed only while the Decision remains unresolved and currently operative.

Rules:

- same Decision ID;
- append immutable `DecisionSubjectRevised` fact;
- expected-version protection;
- terminal judgment dispositions are immutable except through explicit correction semantics;
- changing Subject must not be used to hide a genuinely different investment choice.

---

# 8. Record Deferral consequence

Canonical Deferral is a Human Investment Decision owned by Governance.

R2 command records only the **Decisions-side work consequence**.

Inputs:

- operation ID;
- Decision ID;
- expected version;
- trusted typed Deferral/Human Investment Decision basis reference;
- effective time;
- optional awaited-condition description/reference when an owner/type exists.

Behavior:

- requires `UNRESOLVED + ACTIVE` and currently operative Decision;
- moves work disposition to `DEFERRED`;
- appends `DecisionDeferred`;
- does not create a Human Investment Decision record;
- does not create a Review Condition.

R2 tests may use deterministic trusted fixture references only.

---

# 9. Resume decision work

Inputs:

- operation ID;
- Decision ID;
- expected version;
- resumption basis/reason.

Behavior:

- `UNRESOLVED + DEFERRED` -> `ACTIVE` + `DecisionWorkResumed`;
- `UNRESOLVED + WITHDRAWN` -> `ACTIVE` only when Decision Need remains supported and same coherent choice is being resumed;
- already `ACTIVE` returns explicit no-transition/already-active outcome rather than manufacturing history;
- substantively/external-resolved/retracted Decisions cannot resume;
- currently superseded unresolved Decision cannot resume until relationship support is corrected.

An awaited condition may motivate resumption. A Review Condition on a resolved Decision does not resume the old Decision.

---

# 10. Withdraw current decision work

Inputs:

- operation ID;
- Decision ID;
- expected version;
- Actor Attribution/basis for withdrawal;
- effective time.

Behavior:

- valid only while unresolved and currently operative;
- moves work disposition to `WITHDRAWN`;
- appends `DecisionWorkWithdrawn`;
- does not create Deferral, Human Investment Decision, External Resolution, or Supersession;
- later same-choice resumption may return the same ID to `ACTIVE`.

---

# 11. Record substantive resolution

Inputs:

- operation ID;
- Decision ID;
- expected version;
- trusted typed resolution-basis reference;
- effective time;
- optional lifecycle summary.

Behavior:

1. load current Decision/version/relationship applicability;
2. validate resolution-basis category;
3. reject if current supported effective state already precludes substantive resolution;
4. ask domain to establish `SUBSTANTIVELY_RESOLVED`;
5. atomically persist lifecycle change + receipt;
6. later Governance implementation coordinates Human Investment Decision + Decisions consequence in one application transaction when required.

R2 does not expose a public path allowing arbitrary self-asserted Human Investment Decision/authority.

---

# 12. External Resolution

Inputs:

- operation ID;
- Decision ID;
- expected version;
- attributable basis explaining how circumstances eliminated the Decision Need;
- external/source fact reference where available;
- effective time.

Behavior:

- ordinary command applies to currently unresolved Decision whose choice is eliminated;
- produces `EXTERNALLY_RESOLVED` + `DecisionExternallyResolved`;
- creates no Human Investment Decision, Recommendation, or Action Intent;
- changed attractiveness/state alone is insufficient;
- if the decisive circumstance is discovered only after a conflicting lifecycle fact was already recorded, use lifecycle correction rather than silently overwriting/rejecting history.

---

# 13. Retract unsupported Decision Need

Inputs:

- operation ID;
- Decision ID/Need ID;
- expected version;
- attributable correction basis;
- effective interpretation time if meaningful;
- recorded time from application clock.

Behavior:

- establishes current supported disposition `NEED_RETRACTED`;
- appends `DecisionNeedRetracted`;
- preserves original Need and why it was created;
- does not classify the case as External Resolution;
- later genuine supported Need uses normal new identity rules.

This is a correction of the Need determination, not a generic delete/cancel API.

---

# 14. Renewed Decision

Inputs:

- operation ID;
- one or more predecessor Decision IDs whose supported dispositions are substantively/external-resolved;
- new Decision Need;
- Subject;
- Scope or explicit unresolved Scope;
- Actor/trigger provenance;
- continuity basis.

Behavior:

- predecessors remain unchanged;
- successor gets new Decision ID;
- establish `RENEWED_FROM` edge(s) to each independently supported causal predecessor;
- ordinary initiation continuity safeguards still apply;
- if predecessor is still unresolved, caller must continue/supersede as appropriate.

---

# 15. Supersession use cases

Supersession does not terminalize the predecessor's resolution disposition.

## 15.1 Initiate successor with Supersession

One transaction may:

- establish new successor Decision/Need;
- add one or more `SUPERSEDES` relationships to existing Decisions;
- validate no lineage cycle;
- commit relationship scope/basis/effective time;
- preserve every predecessor lifecycle fact unchanged.

## 15.2 Record Supersession between existing Decisions

Inputs:

- operation ID;
- source successor ID + expected version as required;
- one or more target predecessor IDs + expected versions as required;
- scope/basis of displacement;
- effective time.

Targets may be unresolved or already substantively/external-resolved.

A resolved target remains historically resolved while becoming superseded as an operative basis.

A currently unresolved target becomes non-operative for ordinary direct work while the supported Supersession edge remains in force.

No one-to-one cardinality is assumed.

---

# 16. Lifecycle correction

Late information may change the supported understanding of an earlier lifecycle disposition.

Inputs:

- operation ID;
- Decision ID;
- expected version;
- correction basis/reference;
- fact(s)/interpretation being corrected;
- corrected effective disposition/time;
- Actor Attribution/provenance where material.

Behavior:

- append `DecisionLifecycleCorrected` or equivalent explicit correction fact;
- never update/delete corrected historical fact;
- recompute current supported effective projection;
- preserve recorded sequence/what-was-known timeline;
- correction itself is idempotent/retry-safe.

Example late External Resolution:

- prior `DecisionResolved` remains recorded history;
- correction may establish `EXTERNALLY_RESOLVED` as the supported effective disposition at an earlier effective time;
- Human Investment Decision history remains untouched.

---

# 17. Query contracts

## 17.1 Get current Decision

Returns:

- Decision ID / Need ID;
- Subject;
- Scope including explicit unresolved state;
- supported current resolution disposition;
- work disposition when unresolved;
- current version;
- currently supported renewal/Supersession relationships;
- creation/recorded timestamps;
- no persistence-native types.

## 17.2 Get Decision history

Returns immutable lifecycle facts and relationship facts in deterministic recorded order, preserving effective and recorded time plus correction references.

## 17.3 As-known-at

Input: Decision ID + knowledge cutoff.

Include only facts/relationships/corrections recorded by cutoff. Reconstruct the state Polaris durably knew then.

## 17.4 Effective-at

Input:

- Decision ID;
- effective time;
- optional knowledge cutoff (default current knowledge).

Returns supported effective lifecycle state using only facts known by the knowledge cutoff.

This is distinct from Evidence Judgment-Time Availability.

## 17.5 Find unresolved Decisions for continuity

Returns a deliberately conservative bounded candidate set plus an application-owned continuity observation token/version or equivalent guard.

The query does not decide same-vs-new identity. It supplies candidates and a basis that must be revalidated atomically before a distinct new Decision commits.

## 17.6 Decision lineage

Returns typed renewal/Supersession edges with effective/recorded times and bounded traversal semantics.

---

# 18. Transaction patterns

## Single-Decision mutation

```text
load Decision + version
check idempotency
apply domain change
atomic commit:
  current projection
  + immutable fact
  + receipt
return committed result
```

## Initiation with continuity arbitration

```text
query bounded unresolved candidates
explicit continuity determination
        ↓
commit transaction revalidates candidate basis
        ↓
changed/ambiguous -> no creation
unchanged + CREATE_NEW ->
  Need + Decision + initial fact + receipt
```

## Supersession

```text
load source/targets + versions
validate relationship semantics/cycle
atomic commit relationship facts
(and successor creation when combined initiation)
```

No predecessor resolution fact is overwritten.

## Future cross-owner human judgment

```text
Governance owner fact
        +
Decisions work/resolution consequence
        ↓
ONE application transaction when use-case atomicity requires it
```

---

# 19. Idempotency

For each retryable command:

1. unseen operation -> execute;
2. prior committed same semantic request -> return stable prior result;
3. prior committed different request -> `IdempotencyConflict`.

Operation identity is not Investment Decision identity.

Continuity arbitration remains a separate safeguard for different operation IDs.

---

# 20. Optimistic concurrency

Mutations use expected version(s) as appropriate.

Adapter semantics must ensure stale commands leave:

- no partial current-state change;
- no lifecycle/relationship fact;
- no false receipt.

Caller reloads/re-evaluates rather than application silently applying stale intent.

---

# 21. Persistence ports required by R2

## Decision command store

Must support semantic operations for:

- current state/version load;
- idempotency inspection/replay;
- atomic single-Decision change;
- atomic initiation with continuity revalidation;
- atomic relationship establishment, including many-target Supersession;
- lifecycle correction;
- stable replay result.

## Decision memory reader

Must support:

- current view inputs;
- ordered lifecycle/relationship history;
- as-known-at reconstruction;
- effective-at reconstruction;
- conservative unresolved continuity candidates;
- typed renewal/Supersession lineage.

No generic CRUD repository/platform Unit of Work is introduced merely by convention.

---

# 22. Required application tests

- initiation with unresolved Scope succeeds;
- Scope later establishes without changing Decision ID;
- actor differs from trigger provenance;
- initiation same operation replay returns same Decision;
- same operation/different payload conflicts;
- two different concurrent initiations cannot silently create duplicate Decisions when continuity basis overlaps;
- continuity ambiguity creates no Decision;
- Deferral requires trusted human-decision basis;
- awaited condition resumes same deferred ID;
- withdrawal does not create Deferral/resolution;
- substantive resolution requires trusted basis;
- External Resolution does not create human judgment;
- unsupported Need retraction is distinct from External Resolution;
- resolved Decision cannot reopen; renewal creates linked new ID;
- resolved Decision may later be superseded without losing resolution history;
- one successor may supersede multiple predecessors atomically when requested;
- late lifecycle correction preserves earlier as-known-at view;
- effective-at current knowledge can differ from earlier as-known-at;
- persistence failure never returns successful result.

---

# 23. Requirements traceability

| Requirement | Application consequence |
|---|---|
| `DEC-001`–`DEC-004` | explicit continuity arbitration and identity-safe mutation. |
| `DEC-006` | Deferral consequence requires Human Investment Decision basis. |
| `DEC-008` | External Resolution has dedicated non-human path. |
| `DEC-009`–`DEC-011` | renewal and Supersession preserve identities/histories. |
| `DEC-013` | initiation accepts unresolved Scope. |
| `DEC-014` | explicit work-withdrawal behavior. |
| `DEC-015` | explicit Need-retraction correction. |
| `DEC-016` | Supersession relationship does not replace resolution state/cardinality. |
| `DEC-017` | continuity arbitration beyond operation idempotency. |
| `DEC-018` | lifecycle correction + dual temporal queries. |
| `DEC-019` | actor and trigger provenance separated. |
| `MEM-011` | later context relationship design preserves historical target boundary. |
| `REL-*` | atomicity/idempotency/concurrency/failure visibility. |

---

# 24. Out of scope

- web/CLI/MCP transport mapping;
- authentication provider;
- Governance/Human Investment Decision persistence;
- full Review Condition/Awaited Condition entity models;
- Recommendation/Evidence/Portfolio internals;
- asynchronous follow-up for R2 unless a concrete command earns it;
- generic mediator/CQRS/workflow/event-sourcing framework;
- prior-Decision contextual binding implementation.

---

# 25. Spec-readiness gate

This design is Spec-ready only when:

1. initiation continuity, concurrency, and ambiguity behavior are deterministic;
2. Scope-unresolved initiation is supported;
3. Deferral requires the proper cross-owner human basis;
4. withdrawal and Need retraction cannot be confused with resolution;
5. Supersession works independently of historical resolution and without one-to-one assumptions;
6. lifecycle correction and dual temporal queries are explicit;
7. Actor Attribution is distinct from trigger/technical provenance;
8. ports remain technology-neutral;
9. no Spec must invent these application semantics.
