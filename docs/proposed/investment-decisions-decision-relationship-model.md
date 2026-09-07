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
- target must be supportably `SUBSTANTIVELY_RESOLVED` or `EXTERNALLY_RESOLVED` at establishment under the command's knowledge boundary;
- source is a distinct Decision identity;
- target is never reopened/mutated;
- multiple `RENEWED_FROM` predecessors are permitted only when each causal predecessor is independently supportable; R2 does not impose a universal one-predecessor cardinality;
- supported lifecycle-lineage graph must remain acyclic.

## 2.2 `SUPERSEDES`

Direction:

```text
source Decision ──SUPERSEDES──> target Decision
```

Meaning: source Decision displaces target Decision's continuing applicability or operative investment basis going forward.

Supersession is orthogonal to lifecycle disposition.

Rules:

- source and target differ;
- target may be unresolved, substantively resolved, or externally resolved;
- target historical lifecycle/work facts remain unchanged;
- an unresolved target becomes non-operative for automatic continuity selection while the relationship remains supported;
- one source may supersede multiple targets;
- one target may have multiple superseding sources when that meaning is independently supported;
- no one-to-one uniqueness is part of the inward contract;
- supported lifecycle-lineage graph remains acyclic;
- Supersession may be recorded during successor initiation or later between existing Decisions if the business relationship is established later.

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

# 4. Attribution, provenance, identity, and temporal semantics

Every base relationship fact preserves at least:

- `DecisionRelationshipFactId`;
- source Decision ID;
- target Decision ID;
- relationship type;
- effective/use time;
- recorded time;
- `OperationId`;
- Actor Attribution where material;
- one semantic Trigger Provenance;
- optional Technical Provenance;
- purpose-specific typed basis/reference when required.

Actor Attribution, Trigger Provenance, and Technical Provenance use the completed foundation contracts and remain separate. No universal persisted `ActorKind` is required. Technical references remain provenance and cannot become Decision/Need/Portfolio/Actor/relationship-fact identity.

Relationship facts are immutable. Later correction/qualification is append-only.

A relationship-only committed mutation may advance affected `DecisionVersion` values when required by concurrency protection without fabricating a lifecycle fact or advancing `DecisionLifecycleSequence`.

---

# 5. Graph semantics

The Decision relationship set is a typed directed graph.

## 5.1 Lifecycle-lineage subgraph

Supported `RENEWED_FROM` and `SUPERSEDES` edges together must be acyclic.

Reject direct or indirect cycles, including mixed-edge cycles.

```text
A RENEWED_FROM B
B SUPERSEDES A
```

is invalid if it closes a supported causal lineage cycle.

## 5.2 Context subgraph

`PRIOR_DECISION_CONTEXT` need not be globally acyclic. Two simultaneously evolving Decisions may become context for one another at different times.

Temporal provenance keeps that meaning coherent.

## 5.3 Combined graph

Combined graph may contain context cycles. Queries must preserve type, direction, recorded/effective time, and target knowledge boundary where the relationship type owns such a boundary.

This is a semantic/query graph, not a graph-database mandate.

---

# 6. Relationship correction and contested support

A relationship fact remains historical even if later evidence challenges its currently supported interpretation.

Relationship qualification/correction is itself append-only. Each correction fact:

- has its own `DecisionRelationshipFactId`;
- explicitly references the prior relationship fact it qualifies or disconfirms;
- preserves effective time, recorded time, `OperationId`, Actor Attribution where material, one Trigger Provenance, optional Technical Provenance, and purpose-specific typed correction basis;
- never deletes, mutates, or replaces the original fact.

A correction may qualify:

- whether an edge remains currently supported;
- effective time;
- typed basis;
- for a future contextual relationship, its target historical boundary.

Recorded recency is not authority. If competing typed relationship facts/corrections cannot establish one supported interpretation, support is **contested/indeterminate** rather than newest-write-wins.

Lifecycle-cycle checks apply to the **currently supported** lifecycle-lineage graph. A command that cannot determine whether adding an edge would create a cycle because existing support is contested must fail closed.

Supported unresolved Supersession drives non-operative applicability. Contested Supersession support drives contested operative applicability; ordinary work requiring determinate operative status fails closed.

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

# 9. Persistence contract

A base relationship semantic record is equivalent to:

```text
DecisionRelationshipFact
    relationship_fact_id
    source_decision_id
    target_decision_id
    relationship_type
    effective_time
    recorded_time
    operation_id
    actor_attribution
    trigger_provenance
    technical_provenance
    typed_basis
```

A correction semantic record is equivalent to:

```text
DecisionRelationshipCorrected
    relationship_fact_id
    target_relationship_fact_id
    effective_time
    recorded_time
    operation_id
    actor_attribution
    trigger_provenance
    technical_provenance
    typed_correction_basis
```

A future `PRIOR_DECISION_CONTEXT` relationship adds its purpose-specific `target_as_known_at` / optional target version/fact boundary when that use case is implemented; those fields are not universal base-edge metadata.

Exact PostgreSQL representation is adapter-owned.

R2 should use a many-to-many-capable relation/table or equivalent so future context edges and many-to-many Supersession do not require redefining the inward model.

---

# 10. Query semantics

Decision Memory should support semantic capabilities equivalent to:

```text
get_renewal_predecessors(decision_id, as_known_at=...)
get_renewal_successors(decision_id, as_known_at=...)
get_superseded_targets(decision_id, as_known_at=...)
get_superseding_sources(decision_id, as_known_at=...)
get_lifecycle_lineage(decision_id, depth=..., as_known_at=...)
get_material_prior_decision_context(decision_id, as_known_at=...)
get_related_decision_graph(decision_id, relationship_types=..., depth=..., as_known_at=...)
```

Queries must:

- preserve relationship fact identity, type, and direction;
- apply recorded-time cutoff;
- expose correction/contested support where material;
- bound traversal depth;
- not silently traverse unrequested edge types;
- preserve a contextual relationship's target historical boundary when that relationship type is implemented;
- return application-owned read models, not DB-native graph/row objects.

---

# 11. R2 implementation boundary

R2 implements:

- `DecisionRelationshipFactId` and purpose-specific relationship-fact metadata semantics;
- `RENEWED_FROM`;
- `SUPERSEDES`;
- append-only relationship qualification/correction and contested-support interpretation;
- many-to-many-capable persistence;
- lifecycle-lineage cycle prevention;
- correction-aware/as-known-at lineage queries;
- operative-candidate exclusion for supported unresolved superseded Decisions.

R2 does not implement:

- prior-Decision candidate retrieval;
- `PRIOR_DECISION_CONTEXT` command creation;
- speculative universal context fields on current relationship facts;
- historical analog ranking;
- AI relationship selection;
- generic graph engine/database;
- graph UI.

---

# 12. Required R2 tests

- relationship fact IDs are UUIDv4-backed, type-distinct, and not derived from edge content;
- relationship correction has a new fact ID, explicitly targets the prior fact, and preserves the original;
- incompatible typed relationship support/corrections yield contested support rather than newest-wins;
- self-reference rejected;
- direct and indirect lifecycle cycles rejected;
- mixed `RENEWED_FROM`/`SUPERSEDES` cycle rejected;
- cycle validation fails closed when relevant existing edge support is contested;
- resolved target may be superseded without lifecycle mutation;
- unresolved superseded target becomes non-operative for automatic continuation;
- one source may supersede several targets atomically;
- several sources may supersede one target when independently supported;
- renewal never reopens target;
- relationship retry is idempotent;
- as-known-at excludes later-recorded relationship/correction;
- relationship-only version mutation does not fabricate lifecycle sequence;
- future `PRIOR_DECISION_CONTEXT` contract carries target historical boundary without adding speculative fields to current relationship types;
- graph persistence does not require graph-database types inward.

---

# 13. Spec-readiness rule

Specs may choose schema/index/cycle-check algorithms, private realization helpers, and query implementation details.

Specs may not redefine relationship fact identity, relationship type meaning, cardinality, Supersession orthogonality, append-only correction/support semantics, contested-support behavior, lifecycle-lineage acyclicity, contextual historical binding, retrieval-vs-material-use semantics, Actor/Trigger/Technical Provenance separation, or lifecycle-sequence-vs-Decision-version separation.