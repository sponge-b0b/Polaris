# Investment Decision Relationship Model

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `investment-decisions`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define typed Investment Decision relationships so lifecycle lineage, supersession, and materially used prior-decision context remain explicit without turning Investment Decision into a graph container or requiring graph-database infrastructure.

## Authority

This design refines:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`investment-decisions-r2-decision-kernel-component-boundaries.md`](investment-decisions-r2-decision-kernel-component-boundaries.md);
- [`investment-decisions-r2-foundation-public-contract.md`](investment-decisions-r2-foundation-public-contract.md);
- [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md);
- [`investment-decisions-lifecycle-model.md`](investment-decisions-lifecycle-model.md);
- [`application-use-cases-investment-decision-lifecycle.md`](application-use-cases-investment-decision-lifecycle.md);
- [`durable-persistence-investment-decision-history.md`](durable-persistence-investment-decision-history.md);
- [`../product/domain-model.md`](../product/domain-model.md) and [`../../CONTEXT.md`](../../CONTEXT.md).

The completed foundation contract and the post-#299 #278 synchronization authority refine the concrete identity/attribution/provenance contracts used by this relationship model.

The owner-approved Independent Spec #278 remediation for Ticket #297 completes the R2 relationship-correction, support, admission, version, and temporal graph-consumption semantics in Sections 4–6 and 9–13 below. Those completed rules supersede older shorthand that treated relationship correction as a generic newest-write-resistant qualification, cycle safety as a current-only check, every relationship append as a version increment, or endpoint lifecycle validity as a continuously re-evaluated relationship-validity invariant.

`legacy/v0_1/` is not relationship-model authority.

---

# 1. Core rule

Decision-to-Decision relationships are separate immutable durable facts.

```text
Application Use Case
        ↓
coordinates establishment
        ↓
Investment Decisions validates semantics
        ↓
Durable Persistence commits typed relationship
        ↓
Decision Memory traverses it later
```

The Investment Decision object does not contain an arbitrary mutable `related_decisions` collection and does not search for its own neighbors.

Every immutable relationship fact has its own opaque domain identity:

```text
DecisionRelationshipFactId -> distinct UUID-backed domain identity
UUID generation             -> UUIDv4
```

`DecisionRelationshipFactId` is allocated independently of source/target Decision IDs, relationship type, effective/recorded time, Operation ID, provenance, basis, or persistence row identity. It is not a composite edge key and is not derived from relationship content.

When common relationship-fact attributes are represented by one exported/public value object, the approved name is `DecisionRelationshipFactMetadata`. Bare `FactMetadata` is not used because it loses lifecycle-vs-relationship context.

---

# 2. Relationship classes

## 2.1 `RENEWED_FROM`

Direction:

```text
new Decision ──RENEWED_FROM──> prior Decision
```

Meaning: a new Decision Need requires deliberate judgment after a prior Decision's supported lifecycle disposition was already substantively or externally resolved, and the new Decision is explicitly causally linked to that prior judgment episode.

Rules:

- source and target differ;
- source is a distinct Decision identity grounded in its own new Decision Need;
- each predecessor must satisfy the historical admission rules in Section 6.8, including supportable substantive/external resolution both when the source's new judgment episode begins and at the relationship claim's effective instant;
- the relationship cannot predate the source's new Decision Need/judgment episode;
- a genuinely omitted renewal relationship may be recorded later against the already-established source/Need when those same historical prerequisites are proven and an explicit renewal basis is supplied;
- the target's identity, Need, lifecycle disposition/work history, and immutable facts are never reopened or rewritten by renewal; its current concurrency `DecisionVersion` may nevertheless advance when the protected incoming renewal interpretation changes under Section 6.10;
- multiple `RENEWED_FROM` predecessors are permitted only when each causal predecessor is independently supportable; R2 does not impose a universal one-predecessor cardinality;
- the temporal mixed lifecycle-lineage graph must satisfy Section 5.

“Resolved at renewal” is an admission predicate, not a relationship-validity invariant that is continuously re-evaluated under later knowledge. Later endpoint lifecycle correction may affect current work/applicability/graph consumers under their own rules, but does not silently rewrite an already-admitted renewal relationship. Relationship-semantic change requires explicit relationship correction.

## 2.2 `SUPERSEDES`

Direction:

```text
source Decision ──SUPERSEDES──> target Decision
```

Meaning: source Decision displaces target Decision's continuing applicability or operative investment basis going forward.

Supersession is orthogonal to lifecycle disposition.

Rules:

- source and target differ;
- positive claim admission follows Section 6.8; at the relationship claim's effective instant both endpoints must exist effectively with determinate lifecycle disposition `UNRESOLVED`, `SUBSTANTIVELY_RESOLVED`, or `EXTERNALLY_RESOLVED`;
- target historical lifecycle/work facts remain unchanged;
- an unresolved target becomes non-operative for ordinary work while an incoming Supersession group is `SUPPORTED`;
- relevant incoming `CONTESTED` Supersession makes operative applicability contested and ordinary work requiring determinate applicability fails closed;
- `WITHDRAWN` and `NOT_EFFECTIVE` relationship groups supply no current Supersession edge/effect;
- one source may supersede multiple targets;
- one target may have multiple superseding sources when that meaning is independently supported;
- no one-to-one uniqueness is part of the inward contract;
- the temporal mixed lifecycle-lineage graph must satisfy Section 5;
- Supersession may be recorded during successor initiation or later between existing Decisions if the business relationship is established later.

A supported Supersession relationship retains its relationship meaning independently of later source/target lifecycle or applicability changes. Those current-time lifecycle states may independently affect whether other work is permitted; they do not erase the relationship edge.

Inverse labels such as `RENEWED_BY` and `SUPERSEDED_BY` are derived navigation, not separately authoritative facts.

## 2.3 `PRIOR_DECISION_CONTEXT`

Direction:

```text
current Decision ──PRIOR_DECISION_CONTEXT──> prior Decision
```

Meaning: the target Decision itself was actually selected and materially used as Decision Context for the source Decision at an attributable point.

This does not mean the target caused the source Decision, was accepted, was correct, or was merely retrieved.

A durable context edge must preserve the historical target boundary actually used, including an equivalent of:

```text
target_decision_id
target_as_known_at
optional target recorded version/fact boundary
```

Later changes to the target Decision must not silently change what the source Decision historically considered.

R2 designs this future edge contract but does not implement it before a real Decision Context use case earns it. Current `RENEWED_FROM` and `SUPERSEDES` facts do not gain speculative optional target-context fields merely for future possibility; the relationship model remains purpose-specific and extensible so the later relationship type can add its required historical boundary without changing existing relationship meanings.

---

# 3. Retrieval is not material use

Candidate discovery may use Subject overlap, Portfolio context, shared Thesis/Assumptions, historical analogs, explicit user reference, deterministic lookup, semantic search, or later AI-assisted ranking.

The progression is:

```text
candidate discovery
        ↓
relevance/materiality selection
        ↓
attributable material use
        ↓
durable PRIOR_DECISION_CONTEXT
```

Therefore:

> **Retrieved prior Decision ≠ materially referenced prior Decision.**

A candidate set can produce zero durable context edges.

---

# 4. Relationship fact, basis, attribution, and temporal contracts

Every base relationship fact preserves at least:

- `DecisionRelationshipFactId`;
- source Decision ID;
- target Decision ID;
- relationship type;
- relationship-claim effective time;
- recorded time;
- `OperationId`;
- Actor Attribution where material;
- one semantic Trigger Provenance;
- optional Technical Provenance;
- a purpose-specific typed relationship basis appropriate to its relationship type.

Actor Attribution, Trigger Provenance, and Technical Provenance use the completed foundation contracts and remain separate. No universal persisted `ActorKind` is required. Technical references remain provenance and cannot become Decision/Need/Portfolio/Actor/relationship-fact identity.

Every required relationship or correction basis contains immutable non-blank typed reference(s). R2 does not silently infer an exactly-one-reference cardinality where no business rule requires it.

Purpose-specific basis roles are distinct:

- a `RENEWED_FROM` base or positive replacement requires renewal relationship basis;
- a `SUPERSEDES` base or positive replacement requires Supersession relationship basis;
- every `QUALIFY` or `DISCONFIRM` correction requires its own relationship-correction basis explaining why that correction act is supported;
- correction basis never substitutes for positive relationship basis, and positive relationship basis never substitutes for correction basis;
- if the same underlying evidence truthfully supports both roles, it remains represented in two typed semantic roles rather than collapsed into one generic basis.

Relationship facts and corrections are immutable. Missing required basis is never synthesized from provenance, another fact/correction, support count, or recorded recency.

A relationship-only committed mutation may advance affected `DecisionVersion` values under Section 6.10 without fabricating a lifecycle fact or advancing `DecisionLifecycleSequence`.

---

# 5. Temporal lifecycle-lineage graph semantics

The Decision relationship set is a typed directed graph. R2 cycle enforcement concerns the mixed lifecycle-lineage subgraph formed by `RENEWED_FROM` and `SUPERSEDES`; Ticket #298 owns the implementation of this enforcement and consumes the interpretation contract frozen here.

## 5.1 Complete known effective timeline

At command admission knowledge `K=R`, graph safety is certified against the complete proposed post-command relationship history for every materially distinct effective interval that is known at `R`, including historical/backdated intervals and all known future intervals. There is no arbitrary lookahead horizon.

The finite topology-change boundaries are relationship-claim effective instants, correction-activation instants, and `QUALIFY` replacement-claim effective instants. Equivalent algorithms may prove the same predicate without iterating every clock instant.

A future-only assertion cannot bypass graph validation merely because it has no current protected relationship entry or does not advance `DecisionVersion`.

## 5.2 Edge projection from relationship interpretation

At each effective boundary `T`, consume the combined relationship interpretation defined in Section 6 at `(effective_at=T, known_at=R)`:

- `SUPPORTED` contributes its surviving effective positive edge;
- `CONTESTED` contributes every surviving effective positive edge possibility to the conservative cycle-safety predicate, but is not promoted to a supported edge;
- `WITHDRAWN` contributes no positive edge;
- `NOT_EFFECTIVE` contributes no positive edge, even when it has explanatory support.

Do not infer an edge from the presence of support IDs alone. Incomplete/invalid required ancestry is an explicit history failure and fails before graph certification.

## 5.3 Admission under uncertainty

For every evaluated interval, the union of supported edges and surviving positive possibilities from relevant contested groups across `RENEWED_FROM` and `SUPERSEDES` must remain acyclic.

- definite supported cycle -> typed cycle rejection;
- cycle possible only under one or more contested positive possibilities -> typed indeterminate-cycle-safety rejection;
- contested relationship evidence may otherwise be admitted when every surviving positive possibility is acyclic.

Contest is therefore not a blanket graph prohibition, but uncertainty must never permit a possible cycle to commit.

## 5.4 Corrections and atomic repair

The same final-result predicate applies to base establishment, `QUALIFY`, `DISCONFIRM`, recursive restoration, and an explicitly supplied atomic relationship-correction set. Withdrawing a correction can restore an earlier edge, so correction is not a graph-safety bypass.

An atomic correction set may repair several relationships together when the command's complete final history passes the predicate across all known intervals. Intermediate validation order, serialization order, or temporarily unsafe tentative states are not public graph-admission boundaries. The entire semantic command commits or nothing does.

## 5.5 Current-time consumers remain separate

Current supported traversal uses `SUPPORTED` relationships only. A consumer requiring determinate traversal through relevant `CONTESTED` support fails closed rather than treating contest as absence.

Endpoint lifecycle/applicability changes do not delete relationship edges from cycle analysis. Ordinary work and continuity eligibility independently consume their current lifecycle and operative-applicability rules. A valid relationship never authorizes work on an otherwise ineligible Decision.

The future `PRIOR_DECISION_CONTEXT` subgraph is not subject to this lifecycle-lineage acyclicity rule; its temporal provenance owns its separate meaning.

This is a semantic/query graph, not a graph-database mandate.

---

# 6. Relationship correction and complete interpretation

Relationship interpretation is purpose-specific and append-only. It does not copy lifecycle-correction sequence rules and introduces no relationship sequence.

For one exact relationship group, interpret immutable history at explicit:

```text
effective_at = T
known_at     = K
```

The group key is exactly `(source Decision, relationship type, target Decision)`. Grouping does not replace fact identity: each base assertion and correction retains its own opaque `DecisionRelationshipFactId`.

## 6.1 Correction target and effect

A relationship correction:

- has a fresh `DecisionRelationshipFactId`;
- targets exactly one base relationship fact or earlier correction in the **same relationship-fact lineage**;
- preserves the lineage's source Decision, target Decision, and relationship type;
- carries its own correction effective instant, recorded time, `OperationId`, attribution/provenance, and required correction basis;
- has effect `QUALIFY` or `DISCONFIRM`.

Changing source, target, or relationship type requires a separate base relationship assertion; correction cannot mutate lineage identity.

`QUALIFY` supplies a complete replacement positive relationship claim. It carries both its required correction basis and a separately required purpose-specific relationship basis for the replacement claim. The preceding positive basis remains immutable historical evidence and is not inherited.

`DISCONFIRM` supplies no replacement positive relationship claim or replacement relationship basis. It still requires its own correction basis and may contribute explanatory support when its surviving effect is needed to establish `WITHDRAWN`, restoration, `NOT_EFFECTIVE`, or contest.

## 6.2 Recursive Undo and Replace

Resolve each base fact's correction lineage recursively:

1. a base with no applicable surviving correction contributes its native positive claim;
2. applicable `QUALIFY` replaces the targeted branch with its complete replacement claim;
3. `DISCONFIRM` of a base withdraws that base assertion;
4. `DISCONFIRM` of a correction defeats that correction and restores the branch interpretation immediately preceding it, which may be a positive claim, a qualification, or a withdrawal;
5. a correction may itself later be qualified or disconfirmed;
6. sibling correction branches remain independent; defeating one sibling never erases competing sibling support.

All facts remain inspectable in immutable raw history. Recorded recency is never semantic authority.

## 6.3 Independent temporal activation

Knowledge is a hard prerequisite: a correction and its complete target ancestry must be known by `K` before it can participate.

Each known correction activates independently when its own correction `effective_at <= T`; it does not wait for its target or ancestor correction to become effective. Thus a correction can preempt a known future-effective correction. A defeated correction does not reactivate later merely when its own effective instant arrives.

Restored positive claims retain their own relationship-claim effective instants. Future-only positive claims and future-only correction effects create no present positive support or contest merely because they are already known.

Unknown required ancestry is an explicit incomplete/invalid-history condition, never a determinate relationship state.

## 6.4 Two effective instants for `QUALIFY`

Every `QUALIFY` has two distinct temporal meanings:

1. **correction effective instant** — when the prior branch interpretation ceases to govern;
2. **replacement relationship-claim effective instant** — when the replacement positive relationship becomes effective.

The replacement instant may precede, equal, or follow the correction instant. Once qualification activates, the prior interpretation is suppressed even when the replacement claim is still future-effective. That creates a legitimate `NOT_EFFECTIVE` gap rather than resurrecting the preceding claim.

Recording time controls knowledge, never precedence. Do not collapse these two instants.

## 6.5 Independent base-lineage reconciliation

Resolve every base assertion and its recursive correction lineage independently, then combine them only by the exact `(source, type, target)` group.

Within one surviving lineage or across independent lineages:

- effective positive claims are materially equivalent only when source, relationship type, target, and relationship-claim effective instant all match;
- equivalent positive claims coalesce while retaining the union of all surviving support IDs and valid relationship/correction bases with their semantic roles and contributor associations;
- positive claims with different effective instants are irreconcilable and yield contest;
- surviving positive support versus a surviving explicit withdrawal in the same participating lineage is irreconcilable;
- a determinately withdrawn independent lineage does not conflict with an otherwise clean supported sibling lineage;
- if every known independent base lineage is determinately withdrawn, the group is `WITHDRAWN`;
- a contested lineage keeps the combined group `CONTESTED` even beside clean positive support.

Supporter count, basis count, fact count, larger UUID, and recorded recency establish no precedence.

`A SUPERSEDES B` and `C SUPERSEDES B` are distinct relationship groups; differing effective instants between those groups do not themselves constitute conflict.

## 6.6 Complete-result support membership

`support_fact_ids` and associated basis membership explain the complete interpreted result at `(T,K)`. They are not an arbitrary or minimal witness set and are not equivalent to graph edges.

Rules:

- equivalent surviving branches union every current contributor required for the complete result;
- contested results retain every surviving positive/withdrawal conflict participant;
- defeated ancestry is excluded from current interpreted support but remains in immutable raw history;
- a surviving `QUALIFY` contributes its own fact ID as positive replacement support;
- a surviving base `DISCONFIRM` contributes withdrawal support;
- restoring a correction includes the restored positive/withdrawal support plus the restoration correction only when that correction is currently necessary to suppress an otherwise-effective competing effect;
- an effective correction whose only current role is suppressing a still-future target is excluded until the target would otherwise participate;
- support membership can change as `T` advances without a new fact and without a synthetic `DecisionVersion`.

For example, if base `F` is effective September 1, `C1` disconfirms `F` effective September 20, and `C2` disconfirms `C1` effective September 10, then with all facts known `F` remains supported. September 10–19 support is `{F}`; from September 20 support is `{F, C2}` because only then is `C2` necessary to suppress an otherwise-effective `C1`.

## 6.7 Public relationship result universe

For a known exact relationship group with valid complete history, public interpretation is exactly one of:

```text
SUPPORTED
CONTESTED
WITHDRAWN
NOT_EFFECTIVE
```

- `SUPPORTED`: at least one effective positive survives, all effective positives agree under Section 6.5, and no participating lineage is contested;
- `CONTESTED`: a participating lineage is contested or surviving effective positives disagree;
- `WITHDRAWN`: every known independent base lineage is determinately withdrawn;
- `NOT_EFFECTIVE`: no effective positive or contested claim remains at `T`, but not every known lineage is withdrawn.

`NOT_EFFECTIVE` covers a future base assertion, an active qualification gap before its replacement becomes effective, and mixtures of withdrawn plus not-yet-effective independent lineages. Absence of positive support never fabricates withdrawal.

Examples:

- future base alone -> `NOT_EFFECTIVE`, support `{}`;
- active `QUALIFY` suppresses an effective base while replacement is future -> `NOT_EFFECTIVE`, with the qualification retained as explanatory support when needed for that result;
- `WITHDRAWN`/`NOT_EFFECTIVE` support IDs remain explanatory facts, not positive graph edges.

Outside this four-state result:

- no base relationship fact known by `K` -> relationship not-found-at-cutoff;
- a known correction whose required ancestry is unavailable/malformed -> explicit incomplete/invalid-history failure and fail closed.

The name is `NOT_EFFECTIVE`, not `NOT_YET_EFFECTIVE`, because a qualification may create a non-effective interval after the relationship was previously effective.

## 6.8 Positive-claim admission and preserved historical validity

Admission and later interpretation are distinct.

Validate each new base relationship claim and every `QUALIFY` replacement positive using authoritative endpoint lifecycle histories known at the command's trusted recording boundary `R`, including valid same-command prerequisites under Section 6.9.

At the positive relationship claim's effective instant:

- both endpoint identities must already exist effectively;
- each endpoint lifecycle interpretation must be determinate in `UNRESOLVED`, `SUBSTANTIVELY_RESOLVED`, or `EXTERNALLY_RESOLVED`;
- missing/not-yet-effective, contested, or `NEED_RETRACTED_UNSUPPORTED` endpoint interpretation cannot establish positive claim eligibility.

`RENEWED_FROM` additionally requires each predecessor to be supportably substantively/externally resolved both when the source's new Decision Need/judgment episode begins and at the relationship claim's effective instant. The relationship cannot predate that new episode. Each predecessor is validated independently. Equal effective instants are valid when the predecessor resolution is already a valid prerequisite in the admission prefix rather than being established retroactively by a descendant.

Current endpoint state at recording time is not a generic positive-relationship gate. A valid later assertion of genuinely omitted renewal lineage may be admitted when its historical prerequisites and explicit renewal basis are proven without recreating or reopening either Decision/Need.

`QUALIFY` validates its replacement positive claim under these rules plus its separate correction/relationship bases and two effective instants. `DISCONFIRM` supplies no positive replacement, so it does not require positive claim-time endpoint eligibility; it still requires valid target ancestry, identity, attribution/provenance, correction basis, and graph admission.

Corrections bypass ordinary current work/lifecycle/applicability gates because they operate on historical relationship truth.

Once a relationship fact is validly admitted, later endpoint lifecycle correction or applicability change does not retroactively invalidate, withdraw, restore, or otherwise rewrite that relationship. Relationship-semantic change requires explicit relationship correction. Current lifecycle/applicability consumers remain free to change their own derived outcomes under their current-time rules.

This separation is deliberate Decision Memory behavior: Polaris must be able to explain both why a relationship was validly admitted under the authoritative knowledge then available and why later evidence caused an explicit relationship qualification/disconfirmation, without rewriting admission truth.

## 6.9 Same-command correction ancestry

A correction target may already be committed or may be proposed by the same indivisible semantic command.

Same-command targeting is valid only when:

1. the immutable target `DecisionRelationshipFactId` resolves exactly to the committed/same-command fact; equal timestamp or `OperationId` alone is insufficient;
2. the complete target ancestry forms an explicit acyclic target-reference chain rooted in an independently valid base relationship fact;
3. every prerequisite fact/correction is itself valid to record before its descendant is admitted; a descendant cannot retroactively validate an invalid target;
4. “earlier” means prerequisite in that explicit dependency chain, never request-list, UUID, insertion, timestamp, or arbitrary processing order;
5. prerequisites need be valid to record, not currently effective/supported, preserving approved future-target preemption;
6. missing targets, self-reference, or correction-target cycles are invalid;
7. sibling processing order grants no precedence;
8. tentative validation stages are not public or durable. The whole command, endpoint/version effects, and receipt commit atomically or none do.

A serialized batch may list a dependent before its prerequisite when explicit target references still form a valid acyclic graph. Relationship correction introduces no public relationship sequence or commit-step counter.

## 6.10 `DecisionVersion` protection

Relationship-driven `DecisionVersion` protects the complete **current interpreted relationship meaning**, not raw fact count and not only operative applicability.

### Affected Decisions

For each changed exact `(source Decision, relationship type, target Decision)` group, both source and target are candidates for both `RENEWED_FROM` and `SUPERSEDES`. Increment each already-existing endpoint whose protected incident relationship interpretation changes. A Decision touched by several changed groups increments exactly once for the whole atomic command. Do not propagate versions transitively merely because another Decision is graph-reachable.

### Protected interpretation

Compare:

- relationship group identity/direction/type;
- current `SUPPORTED | CONTESTED | WITHDRAWN | NOT_EFFECTIVE` result when it contributes protected current meaning;
- every surviving effective positive claim and its effective instant;
- complete interpreted support-ID set;
- associated surviving relationship/correction bases, semantic roles, and contributor associations.

Support-only, basis-only, or contested-claim changes therefore count even when operative applicability or the coarse result enum is unchanged. Order is not semantic meaning. Do not compare all immutable raw history as the version token.

### Common observation boundary

Let `R` be the trusted command recording/commit boundary.

- before = complete committed pre-command history interpreted at `(effective_at=R, known_at=R)`;
- after = complete proposed post-command history interpreted at the same `(R,R)`.

Pre-history includes earlier committed acts even when their `recorded_at` equals `R`; it excludes every fact proposed by the current atomic command. Post-history adds the entire command. Never compare a stale caller view, different boundaries, or an intermediate tentative state. Invalid/incomplete history is a failure, not a comparison state.

### Future/history-only facts

An append that leaves protected current relationship interpretation unchanged does not advance `DecisionVersion`.

For version comparison only, no relationship entry before a first future-only assertion and `NOT_EFFECTIVE` with empty explanatory support after it both contribute no protected current relationship entry, even though public queries distinguish not-found from known `NOT_EFFECTIVE`. Learning a future-only assertion therefore need not bump a version.

`NOT_EFFECTIVE` with non-empty explanatory support is protected. A future-effective append may still change current complete meaning—for example, turning a fully `WITHDRAWN` group into `NOT_EFFECTIVE` because a new independent future lineage is not withdrawn—and then it advances affected versions.

Time passage and queries never synthesize a fact or version.

### Atomic cardinality and lifecycle separation

An existing Decision increments once when either the frozen lifecycle-version contract or this relationship comparison requires it, not once per changed fact/group/dimension. A Decision first established by the command starts at version 1 including same-command initial relationships.

Relationship facts/corrections never fabricate lifecycle facts or advance `DecisionLifecycleSequence`.

### Concurrency consequence

Both-endpoint, support-sensitive versioning intentionally accepts more optimistic-concurrency conflicts than applicability-only versioning in exchange for protecting complete interpreted relationship meaning. If contention later becomes operationally significant, optimize coordination/transaction mechanics without weakening endpoint/support/basis protection.

Matching versions are not proof that time, future-known history, ancestry, graph paths, or absence predicates remain unchanged. Section 5 and the Application/persistence contracts therefore require authoritative command-time transactional revalidation of every material dependency, including dependencies whose DecisionVersion does not advance. Endpoint CAS alone is never graph-safety proof.

## 6.11 Distinct attributable acts versus replay

Append semantics and idempotent retry suppression are separate:

- every distinct valid attributable `RENEWED_FROM`/`SUPERSEDES` assertion or `QUALIFY`/`DISCONFIRM` correction receives a fresh immutable `DecisionRelationshipFactId` and appends, even when its complete claim and bases match existing support;
- equivalent surviving claims retain all distinct support IDs and valid bases under Section 6.5;
- duplicate/colliding relationship fact identity is invalid history, never a silent merge;
- same `OperationId` + same semantic request replays the already-committed receipt/result without allocating/appending another fact or advancing versions;
- same `OperationId` + different semantic request conflicts and commits nothing;
- a distinct operation must still satisfy every admission, basis, identity, graph, and concurrency rule.

Receipt/idempotency ownership remains Application/persistence; #297 introduces no domain receipt framework.

---

# 7. Supersession examples

## 7.1 Resolved then superseded

```text
D-610
supported lifecycle: SUBSTANTIVELY_RESOLVED
Human judgment: Hold AAPL

D-611
Human judgment: Exit all individual equities

D-611 SUPERSEDES D-610
```

D-610 remains historically substantively resolved. Supersession changes continuing applicability, not its historical disposition.

## 7.2 One Decision supersedes several

```text
D-900 SUPERSEDES D-610
D-900 SUPERSEDES D-702
D-900 SUPERSEDES D-811
```

This is valid when one broader Decision becomes the new operative basis for several prior decisions.

## 7.3 Several later Decisions supersede one prior basis

This may be valid when a prior broad decision is deliberately decomposed into several independently meaningful successor decisions. No universal one-successor restriction is imposed.

---

# 8. Lesson-mediated and owner-specific influence

Do not flatten every historical influence into Decision-to-Decision context.

If the actual path is:

```text
Decision A
  ↓
Evaluation
  ↓
Lesson L
  ↓
Decision B
```

preserve the Lesson relationship. Add `PRIOR_DECISION_CONTEXT` only if Decision A itself was materially used.

Likewise reuse of one Evidence item, View, Recommendation, or Risk Assessment should retain that owner's semantic binding rather than fabricate whole-Decision influence.

---

# 9. Persistence-facing semantic record contract

A base relationship semantic record is equivalent to:

```text
DecisionRelationshipFact
    relationship_fact_id
    source_decision_id
    target_decision_id
    relationship_type
    relationship_effective_at
    recorded_at
    operation_id
    actor_attribution
    trigger_provenance
    technical_provenance
    typed_relationship_basis
```

A correction semantic record is equivalent to:

```text
DecisionRelationshipCorrected
    relationship_fact_id
    target_relationship_fact_id
    effect: QUALIFY | DISCONFIRM
    correction_effective_at
    replacement_relationship_effective_at   # QUALIFY only
    replacement_typed_relationship_basis    # QUALIFY only
    recorded_at
    operation_id
    actor_attribution
    trigger_provenance
    technical_provenance
    typed_correction_basis
```

Persistence must preserve enough immutable target ancestry and admission/recording knowledge to reconstruct Sections 6.2–6.9 exactly. There is no relationship sequence. Request-list/insertion order is not semantic ordering.

A relationship interpretation/read model must be able to preserve:

- exact `(T,K)` observation boundary;
- exact group identity;
- four-state result;
- every surviving effective positive claim and its effective instant where applicable;
- complete interpreted `support_fact_ids`;
- role-associated surviving relationship/correction bases and contributor associations;
- explicit not-found-at-cutoff versus invalid/incomplete-history outcomes outside the four valid states.

A future `PRIOR_DECISION_CONTEXT` relationship adds its purpose-specific `target_as_known_at` / optional target version/fact boundary when that use case is implemented; those fields are not universal base-edge metadata.

Exact PostgreSQL representation is adapter-owned. R2 should use a many-to-many-capable relation/table or equivalent so future context edges and many-to-many Supersession do not require redefining the inward model.

---

# 10. Query semantics

Decision Memory should support semantic capabilities equivalent to:

```text
get_renewal_predecessors(decision_id, effective_at=..., known_at=...)
get_renewal_successors(decision_id, effective_at=..., known_at=...)
get_superseded_targets(decision_id, effective_at=..., known_at=...)
get_superseding_sources(decision_id, effective_at=..., known_at=...)
get_lifecycle_lineage(decision_id, depth=..., effective_at=..., known_at=...)
get_material_prior_decision_context(decision_id, as_known_at=...)
get_related_decision_graph(decision_id, relationship_types=..., depth=..., effective_at=..., known_at=...)
```

Queries must:

- preserve relationship fact identity, type, and direction;
- apply explicit recorded-time/knowledge cutoff and effective-time interpretation;
- distinguish not-found-at-cutoff, valid four-state interpretation, and invalid/incomplete history;
- expose complete surviving support/basis associations and contested possibilities where material;
- never treat explanatory support as a positive graph edge;
- bound traversal depth;
- not silently traverse unrequested edge types;
- preserve a contextual relationship's target historical boundary when that relationship type is implemented;
- return application-owned read models, not DB-native graph/row objects.

`as_known_at(K)` shorthand, when offered, means relationship state effective at `K` using knowledge recorded by `K`, equivalent to `(T=K,K)`.

---

# 11. R2 implementation boundary

R2 implements:

- `DecisionRelationshipFactId` and purpose-specific relationship-fact metadata semantics;
- `RENEWED_FROM`;
- `SUPERSEDES`;
- append-only recursive relationship qualification/disconfirmation and four-state combined interpretation;
- purpose-specific relationship/correction basis roles;
- historical admission and same-command correction ancestry;
- relationship-driven both-endpoint `DecisionVersion` semantics;
- many-to-many-capable persistence;
- temporal lifecycle-lineage cycle-admission contract consumed by #298;
- correction-aware temporal lineage queries;
- operative-candidate exclusion/fail-closed applicability for supported/contested incoming Supersession.

R2 does not implement:

- prior-Decision candidate retrieval;
- `PRIOR_DECISION_CONTEXT` command creation;
- speculative universal context fields on current relationship facts;
- historical analog ranking;
- AI relationship selection;
- generic graph engine/database;
- graph UI;
- a generic cross-domain correction framework;
- a domain idempotency/receipt subsystem.

Ticket #297 owns the relationship interpretation/admission/version semantics above. Ticket #298 owns concrete mixed-lineage cycle enforcement while consuming this contract. Application/persistence own transactional coordination/protection mechanisms without redefining the predicate.

---

# 12. Required R2 tests

At minimum cover:

- relationship fact IDs are UUIDv4-backed, type-distinct, fresh per distinct valid act, and not derived from edge content;
- base renewal/Supersession and every `QUALIFY` replacement require their correct relationship basis; every correction separately requires correction basis;
- missing/inferred/inherited relationship/correction basis rejected;
- recursive `QUALIFY`/`DISCONFIRM`, correction-of-correction, and restoration of positive/withdrawal/gap interpretations;
- sibling correction branches remain independent;
- correction with unknown/malformed ancestry fails explicitly;
- same-command target dependency may be serialized out of order but must form an explicit acyclic same-lineage chain rooted in a valid base fact;
- request-list/UUID/timestamp/insertion order never becomes correction precedence;
- two `QUALIFY` effective instants remain distinct, including replacement before/equal/after correction activation;
- equivalent same-instant positive assertions coalesce and union all surviving support/bases;
- different effective instants or surviving positive-vs-withdrawal conflict yields contest;
- future base, qualification gap, withdrawn+future mixtures, and all-withdrawn histories distinguish `NOT_EFFECTIVE` from `WITHDRAWN`;
- no known base is not-found, not `NOT_EFFECTIVE`; invalid ancestry is a failure, not a four-state result;
- support membership changes with `T` only when contributors become necessary; defeated/unrelated/future-only support is excluded appropriately;
- historical positive admission rejects missing/not-yet-effective, contested, and unsupported-Need endpoints;
- renewal predecessor is resolved at new-episode start and relationship effective instant; late omitted lineage can be recorded only when those historical predicates remain provable;
- later endpoint lifecycle correction does not silently rewrite admitted relationship truth;
- resolved target may be superseded without lifecycle mutation;
- supported incoming Supersession makes unresolved target non-operative; relevant contest makes applicability contested;
- first future-only assertion may append without current version bump; support/basis-only current changes advance both affected endpoint versions;
- multiple changed relationship groups/lifecycle effects increment each existing Decision at most once per atomic command;
- predecessor identity/lifecycle history stays immutable even when incoming renewal changes its concurrency version;
- exact same-operation/request replay appends nothing; distinct equivalent acts append distinct support; changed-request OperationId reuse conflicts;
- graph certification checks historical and every known future topology interval;
- contested positive possibilities may be admitted when all possibilities are acyclic, but definite or possible cycles fail with distinct typed semantics;
- atomic correction batches may repair multiple relationships without exposing intermediate graph states;
- future-only/non-endpoint/path/absence changes are transactionally protected even when endpoint versions match;
- relationship-only version mutation does not fabricate lifecycle sequence;
- future `PRIOR_DECISION_CONTEXT` contract carries target historical boundary without adding speculative fields to current relationship types;
- graph persistence does not require graph-database types inward.

---

# 13. Spec-readiness rule

Specs may choose schema/index/cycle-check algorithms, physical locking/serialization, private realization helpers, collection layouts, and query implementation details only when those choices are semantically equivalent under this completed contract.

Specs may not redefine:

- relationship fact identity or relationship type meaning;
- source/target/type lineage identity;
- many-to-many cardinality;
- purpose-specific basis roles;
- recursive correction/Undo/Replace semantics;
- correction activation or the two `QUALIFY` effective instants;
- exact claim equivalence/conflict predicates;
- the four-state result universe and complete support membership;
- admission-time endpoint/renewal validity or preserved historical admission truth;
- same-command target ancestry;
- distinct attributable append versus idempotent replay;
- both-endpoint protected `DecisionVersion` meaning;
- temporal conservative graph-admission semantics;
- the requirement to protect graph/history/absence dependencies beyond endpoint versions;
- Supersession orthogonality/current applicability consumption;
- contextual historical binding or retrieval-vs-material-use semantics;
- Actor/Trigger/Technical Provenance separation;
- lifecycle-sequence-vs-Decision-version separation.

Could two implementations satisfying this document produce materially different domain/public/persistence/temporal/concurrency/downstream behavior for those dimensions? If yes, the implementation has found an architecture gap and must fail closed rather than choose by convenience.
