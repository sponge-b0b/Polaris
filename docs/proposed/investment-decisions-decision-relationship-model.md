# Investment Decision Relationship Model

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `investment-decisions`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define typed relationships among Investment Decisions so lifecycle lineage, Supersession, materially used prior-decision context, and graph-shaped Decision Memory remain explicit without turning an Investment Decision into a graph container or requiring graph-database infrastructure.

## Authority

This design refines, but does not override:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`investment-decisions-r2-decision-kernel-component-boundaries.md`](investment-decisions-r2-decision-kernel-component-boundaries.md);
- [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md);
- [`investment-decisions-lifecycle-model.md`](investment-decisions-lifecycle-model.md);
- [`application-use-cases-investment-decision-lifecycle.md`](application-use-cases-investment-decision-lifecycle.md);
- [`durable-persistence-investment-decision-history.md`](durable-persistence-investment-decision-history.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md);
- [`../product/domain-model.md`](../product/domain-model.md) and [`../../CONTEXT.md`](../../CONTEXT.md);
- accepted ADRs under [`../adr/`](../adr/).

`legacy/v0_1/` is not a relationship-model authority.

---

# 1. Design objective

Polaris must distinguish:

1. a prior Decision that is a renewal predecessor;
2. a Decision whose continuing applicability/operative basis is displaced by another Decision;
3. a prior Decision materially used as context for a later Decision;
4. a Decision merely retrieved as a candidate but never materially used;
5. a Lesson, Evidence item, View, Recommendation, Risk Assessment, or other owner-specific fact that influences later work without flattening that influence into a generic whole-Decision edge.

Relationships must remain historically reconstructable without:

- embedding mutable adjacency lists inside the Investment Decision aggregate;
- treating retrieval similarity as durable truth;
- forcing every relationship into one untyped edge;
- assuming one-to-one lineage/cardinality without domain authority;
- requiring a graph database;
- allowing relationships to redefine Decision identity.

---

# 2. Core rule: relationships are separate durable facts

An Investment Decision does not discover or mutate arbitrary graph neighbors itself.

```text
Application Use Case
        ↓
coordinates explicit relationship establishment
        ↓
Investment Decisions validates relationship semantics
        ↓
Durable Persistence commits typed relationship fact
        ↓
Decision Memory may traverse it later
```

Relationship facts reference independently durable Decision identities.

The Decision lifecycle root therefore remains small: relationship truth is adjacent to Decision identity, not stored as an ever-growing mutable collection inside it.

---

# 3. Relationship classes

## 3.1 Renewal lineage: `RENEWED_FROM`

Direction:

```text
new Decision ──RENEWED_FROM──> prior Decision
```

Meaning:

A new Decision Need requires renewed deliberate judgment after the prior Decision's unresolved judgment was already substantively or externally resolved.

Rules:

- source and target differ;
- target's supported disposition at relationship effective time is `SUBSTANTIVELY_RESOLVED` or `EXTERNALLY_RESOLVED`;
- relationship never reopens/mutates target;
- source is a distinct Decision identity;
- no fixed one-predecessor cardinality is imposed by the inward model; one or more prior Decisions may be causal predecessors only when each relationship is independently supportable;
- materially relevant additional prior Decisions that are not causal renewal predecessors use owner-specific/context relationships instead.

## 3.2 Supersession: `SUPERSEDES`

Direction:

```text
later/current Decision ──SUPERSEDES──> earlier Decision
```

Meaning:

The source Decision displaces some or all of the target Decision's continuing applicability or operative investment basis going forward.

Supersession is **orthogonal** to the target's historical resolution/work disposition.

Rules:

- source and target differ;
- target may be unresolved, deferred, withdrawn, substantively resolved, or externally resolved;
- target's historical disposition is not changed to `SUPERSEDED`;
- unresolved superseded target is no longer independently operative for ordinary decision work while the relationship remains currently supported;
- one source may supersede multiple prior Decisions when a broader Decision displaces several operative bases;
- one target may be superseded by multiple later Decisions when the earlier basis is deliberately decomposed/displaced across several later Decisions;
- no one-to-one cardinality is assumed;
- relationship preserves explicit scope/basis sufficient to understand what applicability was displaced;
- Supersession does not copy predecessor facts into successor ownership.

Example:

```text
D-610
historical Human Investment Decision: Hold AAPL
supported disposition: SUBSTANTIVELY_RESOLVED

later D-611
Exit all individual equities

D-611 SUPERSEDES D-610

D-610 remains SUBSTANTIVELY_RESOLVED historically
and is additionally superseded as an operative basis.
```

## 3.3 Material prior-decision context: `PRIOR_DECISION_CONTEXT`

Direction:

```text
current Decision ──PRIOR_DECISION_CONTEXT──> materially used prior Decision
```

Meaning:

The target Decision itself was actually selected and materially used as Decision Context for the source Decision at an attributable point in time.

This relationship does **not** mean:

- target caused source to exist;
- target is a lifecycle predecessor;
- target Recommendation was accepted;
- target Outcome proves current action;
- target merely appeared in retrieval/search;
- every judgment within source used target.

---

# 4. Retrieval is not relationship creation

Candidate discovery may use:

- same/related Subject;
- overlapping Portfolio/Exposure;
- shared Thesis/Assumption;
- similar Scope/Horizon;
- historical analog retrieval;
- Lessons;
- explicit human reference;
- deterministic lookup;
- semantic/AI ranking.

Required progression:

```text
candidate discovery
        ↓
relevance/materiality selection
        ↓
attributable material use in current Decision Context
        ↓
durable PRIOR_DECISION_CONTEXT binding
```

> **Retrieved prior Decision ≠ materially referenced prior Decision.**

A query returning many candidates may produce zero durable context bindings.

---

# 5. Hindsight-safe contextual binding

A `PRIOR_DECISION_CONTEXT` edge must identify not only **which** Decision was used but enough temporal boundary to reconstruct **which state of that Decision was actually available/used**.

At minimum the durable relationship preserves or references:

- source Decision ID;
- target Decision ID;
- relationship identity/type;
- effective/use time;
- recorded/committed time;
- operation/idempotency identity;
- Actor Attribution/context-selection provenance where applicable;
- typed material-use basis;
- **target knowledge cutoff** (`target_as_known_at`) or an equivalent immutable Decision Memory snapshot/version boundary.

Optional implementation metadata may include a stable assembled-view digest/reference, but that cannot replace the semantic target knowledge cutoff.

Therefore later mutations/corrections to the target Decision do not alter what the source historically used.

Example:

```text
Decision B at 2026-09-10 11:00
uses Decision A as it was knowable at 2026-09-10 10:55

Decision A later receives a late-recorded lifecycle correction

B's historical context still points to A-as-known-at-10:55.
```

---

# 6. Who establishes relationships

Application Use Cases coordinates relationship creation.

For contextual relationships a future use case may:

1. query candidate prior Decisions;
2. assemble candidate historical states using explicit knowledge cutoffs;
3. determine relevance/materiality or preserve ambiguity;
4. preserve attributable selection provenance;
5. ask Decisions domain to validate proposed relationship semantics;
6. persist relationship only when target was actually materially used;
7. expose it through Decision Memory later.

The Decision aggregate does not call search/model/repository services to discover its own neighbors.

---

# 7. Immutability and correction

Relationship facts are immutable once committed.

If a relationship was recorded incorrectly or later knowledge changes its supported interpretation:

- do not delete/mutate the earlier relationship fact;
- append an explicit relationship correction/supersession-of-assertion fact or equivalent non-destructive correction record;
- preserve what was known and asserted before correction;
- current graph queries apply supported corrections according to knowledge cutoff.

A relationship correction is not the same as the `SUPERSEDES` business relationship between Investment Decisions.

---

# 8. Graph semantics

Decision-to-Decision relationships form a typed directed graph.

## 8.1 Lifecycle/continuity lineage graph

The subgraph containing `RENEWED_FROM` and `SUPERSEDES` must be acyclic with respect to supported effective lineage.

Cycles such as these are invalid:

```text
A RENEWED_FROM B
B RENEWED_FROM A
```

```text
A SUPERSEDES B
B SUPERSEDES A
```

or longer mixed lineage cycles.

No fixed one-to-one cardinality is required to enforce acyclicity.

## 8.2 Context graph

`PRIOR_DECISION_CONTEXT` is directed but need not be globally acyclic.

Two concurrently evolving Decisions may legitimately use one another at different times if each material use was historically possible and bound to the correct target knowledge cutoff.

The temporal edge data makes such a static cycle coherent.

## 8.3 Combined graph

The combined Decision graph may contain cycles because context edges may cycle while lifecycle lineage may not.

Queries must preserve:

- relationship type;
- direction;
- effective time;
- recorded time;
- supported/corrected status;
- target knowledge cutoff for contextual use.

---

# 9. Supersession semantics in detail

Supersession may be known at successor initiation or established later after both Decisions already exist.

R2 therefore supports two semantic patterns:

## 9.1 Initiate with Supersession

One application transaction may:

- create successor Decision/Need;
- establish one or more `SUPERSEDES` edges to existing Decisions;
- make the successor immediately operative where applicable.

No predecessor resolution state is rewritten.

## 9.2 Record later Supersession

When the displacement relationship is established after both Decisions exist:

- append the relationship with effective and recorded time;
- apply graph/cycle/continuity validation;
- preserve predecessor history unchanged;
- if the relationship is recorded late, as-known-at queries before recorded time must not show it.

This supports historically resolved Decisions later becoming superseded as operative bases.

---

# 10. Lesson-mediated and owner-specific influence remains explicit

If a later Decision uses a Lesson derived from an earlier Decision, preserve:

```text
Decision A
  ↓
Outcome / Evaluation
  ↓
Lesson L
  ↓
Decision B
```

Do not automatically flatten this to `B PRIOR_DECISION_CONTEXT A` unless Decision A itself was materially used.

Similarly, reuse of only a View, Recommendation, Evidence item, or Risk Assessment from another Decision should use the appropriate owner-specific binding rather than fabricating whole-Decision influence.

---

# 11. Decision graph vs Durable Decision Memory graph

Decision-to-Decision relationships are one portion of broader graph-shaped Decision Memory:

```text
Investment Decision
    ├── Investment Decisions
    ├── Evidence
    ├── Views / Recommendations
    ├── Portfolio/Risk facts
    ├── Governance acts / Human Investment Decisions
    ├── Action Intents / external activity
    ├── Outcomes / Evaluations
    └── Lessons
```

Each edge remains owned by its semantic owner.

No generic graph entity/table becomes the semantic owner of all cross-lifecycle relationships.

A graph-shaped query projection is allowed; a graph-shaped universal aggregate is not required.

---

# 12. Persistence contract

A durable Decision relationship must support semantics equivalent to:

```text
DecisionRelationship
    relationship_id
    source_decision_id
    target_decision_id
    relationship_type
    effective_time
    recorded_time
    operation_id
    actor/context provenance
    typed_basis/reference
    target_as_known_at      # required for PRIOR_DECISION_CONTEXT
    correction_status/reference
```

Exact physical representation is adapter-owned.

For R2, PostgreSQL should prefer a dedicated typed relationship relation/table because R2 now requires many-to-many Supersession compatibility and later many-to-many contextual edges. Fixed single foreign-key columns must not become the inward contract.

No graph database is required.

---

# 13. Query semantics

Semantic query capabilities may include:

```text
get_renewal_predecessors(decision_id)
get_renewal_successors(decision_id)
get_superseded_decisions(decision_id)
get_superseding_decisions(decision_id)
get_lifecycle_lineage(decision_id, depth=..., as_known_at=...)
get_material_prior_decision_context(decision_id, as_known_at=...)
get_related_decision_graph(decision_id, relationship_types=..., depth=..., as_known_at=...)
```

Queries must:

- preserve type/direction;
- support bounded depth;
- apply recorded-time/correction filtering for `as_known_at`;
- avoid traversing unrequested edge types;
- preserve target knowledge cutoff for context edges;
- return application-owned read models rather than persistence-native rows/graph objects.

---

# 14. R2 implementation boundary

## R2 implements

- `RENEWED_FROM` durable relationship semantics;
- `SUPERSEDES` durable many-to-many semantics;
- Supersession of unresolved or already resolved Decisions without rewriting disposition;
- lifecycle-lineage cycle prevention;
- relationship effective/recorded time;
- relationship correction compatibility;
- persistence/query support required by renewal, Supersession, and historical reconstruction;
- schema/contracts compatible with later `PRIOR_DECISION_CONTEXT` many-to-many edges.

## R2 does not implement

- prior-Decision candidate retrieval;
- historical analog ranking;
- `PRIOR_DECISION_CONTEXT` creation commands;
- AI-assisted context selection;
- Attention-based memory search;
- generic graph framework/database;
- user-facing graph visualization.

The contextual relationship is designed now to prevent R2 schema/contract lock-in, but first implementation waits until Decision Context materially uses prior Decisions.

---

# 15. Validation rules

All relationships require:

- valid source/target Decision identities;
- source != target;
- recognized relationship type;
- durable operation/idempotency identity;
- immutable relationship identity;
- effective and recorded time;
- relationship-specific basis;
- no supported lineage cycle for `RENEWED_FROM`/`SUPERSEDES`.

Additional renewal rules:

- target was substantively or externally resolved at applicable effective/knowledge boundary;
- relationship does not mutate/reopen target.

Additional Supersession rules:

- target may be unresolved or resolved;
- relationship states what applicability/operative basis is displaced sufficiently for later interpretation;
- no one-to-one cardinality assumption;
- unresolved superseded target becomes non-operative without changing its historical resolution/work facts.

Additional contextual rules when later implemented:

- target existed and was knowable by the preserved `target_as_known_at` cutoff;
- retrieval alone is insufficient;
- material-use basis/provenance is required;
- retry is idempotent;
- later target changes cannot alter historical binding meaning.

---

# 16. Test model

R2 tests must cover:

- renewal source/target differ;
- renewal target eligibility by historical disposition;
- renewal does not reopen predecessor;
- Supersession can target unresolved Decision;
- Supersession can target substantively resolved Decision without changing its resolution fact;
- one successor can supersede multiple predecessors;
- one predecessor can have multiple supported superseding successors when scoped semantics justify it;
- self relationship rejected;
- direct/indirect mixed lineage cycles rejected;
- late-recorded Supersession excluded from earlier as-known-at query;
- relationship correction is non-destructive;
- relational persistence does not assume one predecessor column as inward contract.

Later contextual tests must cover target knowledge cutoff and retrieval-vs-material-use distinction.

---

# 17. Requirements traceability

| Requirement | Relationship consequence |
|---|---|
| `DEC-009` | renewed judgment creates new linked Decision. |
| `DEC-011` | Supersession preserves both histories. |
| `DEC-016` | Supersession is orthogonal to historical disposition and not one-to-one by default. |
| `DEC-018` | late relationship/correction facts preserve effective vs known history. |
| `MEM-005` | relationship correction is non-destructive. |
| `MEM-006` | relationships are recorded only to supported strength. |
| `MEM-007` | Decision Memory can use durable relationships as future active context. |
| `MEM-011` | contextual edges preserve target historical state actually used. |

---

# 18. Spec-readiness gate

This relationship design is Spec-ready only when review confirms:

1. Supersession is a relationship, never a replacement lifecycle state;
2. unresolved and resolved Decisions may both be superseded;
3. no unsupported one-to-one Supersession cardinality remains;
4. lifecycle lineage stays acyclic while context graph may cycle temporally;
5. `PRIOR_DECISION_CONTEXT` binds a target historical knowledge boundary;
6. relationship correction is non-destructive;
7. persistence remains graph-technology neutral;
8. R2 implementation scope remains limited to renewal/Supersession mechanics while preserving later context compatibility.
