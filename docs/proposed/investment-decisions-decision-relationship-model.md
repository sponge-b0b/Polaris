# Investment Decision Relationship Model

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `investment-decisions`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define typed relationships among Investment Decisions so renewal, Supersession, materially used prior-decision context, and graph-shaped Decision Memory remain explicit without turning a Decision into a graph container or requiring graph infrastructure.

## Authority

This design refines:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`investment-decisions-r2-decision-kernel-component-boundaries.md`](investment-decisions-r2-decision-kernel-component-boundaries.md);
- [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md);
- [`investment-decisions-lifecycle-model.md`](investment-decisions-lifecycle-model.md);
- [`application-use-cases-investment-decision-lifecycle.md`](application-use-cases-investment-decision-lifecycle.md);
- [`durable-persistence-investment-decision-history.md`](durable-persistence-investment-decision-history.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- [`../product/requirements-0.2.0-amendment-r2-edge-cases.md`](../product/requirements-0.2.0-amendment-r2-edge-cases.md);
- [`../product/domain-model.md`](../product/domain-model.md) and [`../../CONTEXT.md`](../../CONTEXT.md).

---

# 1. Core rule

Decision-to-Decision relationships are immutable typed durable facts coordinated by Application Use Cases and validated by `investment-decisions` semantics.

They are not mutable adjacency owned by the Investment Decision object.

```text
Application
   ↓
explicit relationship operation
   ↓
Decisions validation
   ↓
Durable relationship fact
   ↓
Decision Memory query
```

---

# 2. Relationship types

## 2.1 `RENEWED_FROM`

```text
new Decision ──RENEWED_FROM──> prior Decision
```

Meaning: renewed deliberate judgment is required after the prior Decision no longer has unresolved operative judgment work because either:

- its judgment was substantively resolved; or
- its Decision Need was externally eliminated.

Rules:

- source != target;
- target is not reopened/mutated;
- source has a new Decision Need/Decision identity;
- no fixed one-predecessor cardinality is imposed; each causal predecessor must be independently supportable;
- a Decision whose Need was merely retracted as unsupported is not automatically a renewal predecessor.

## 2.2 `SUPERSEDES`

```text
later/current Decision ──SUPERSEDES──> earlier Decision
```

Meaning: source displaces some or all of target's continuing applicability or operative investment basis.

Rules:

- source != target;
- target may have active/unresolved work or historical substantive resolution; Supersession does not rewrite any Need/judgment/work fact;
- target may also have other later lifecycle correction/history; relationship remains separate from those axes;
- one source may supersede multiple targets;
- one target may be superseded by multiple sources when scoped displacement genuinely requires it;
- relationship preserves basis/scope sufficient to explain what applicability was displaced;
- no one-to-one uniqueness assumption.

A supported Supersession makes an unresolved target non-operative for ordinary direct work while that relationship applies.

## 2.3 `PRIOR_DECISION_CONTEXT`

```text
current Decision ──PRIOR_DECISION_CONTEXT──> materially used prior Decision
```

Meaning: target Decision itself was actually selected and materially used as Decision Context for source at a particular historical point.

It does not mean lifecycle predecessor, causality, Recommendation adoption, Outcome proof, retrieval similarity, or universal use by every judgment under source.

---

# 3. Retrieval is not material context

```text
candidate discovery
   ↓
relevance/materiality determination
   ↓
attributable material use
   ↓
PRIOR_DECISION_CONTEXT
```

> Retrieved prior Decision ≠ materially referenced prior Decision.

Search may return many candidates and create zero durable context edges.

---

# 4. Hindsight-safe context binding

A contextual edge must reconstruct the target Decision state actually available/used.

Preserve at least:

- relationship ID/type;
- source/target Decision IDs;
- effective/use time;
- recorded time;
- operation ID;
- Actor/context-selection provenance where material;
- typed basis;
- **target knowledge cutoff (`target_as_known_at`) or equivalent immutable Decision Memory snapshot/version boundary**.

Later target changes/corrections therefore do not change the source's historical context.

---

# 5. Relationship correction

Relationship facts are immutable.

If an asserted relationship is later shown wrong or overbroad:

- preserve it as recorded history;
- append explicit relationship correction/qualification referencing the prior relationship assertion;
- current/as-known queries apply only corrections visible at their knowledge cutoff.

This correction is not the business `SUPERSEDES` relationship.

---

# 6. Graph semantics

Decision relationships form a typed directed graph.

## Lifecycle-lineage subgraph

Supported `RENEWED_FROM` + `SUPERSEDES` lineage must be acyclic.

No direct or indirect mixed cycle is valid.

## Context subgraph

`PRIOR_DECISION_CONTEXT` need not be globally acyclic. Two concurrently evolving Decisions can use one another at different historical times when each edge is hindsight-safe.

## Combined graph

May contain cycles because context edges may cycle. Every traversal preserves type/direction/effective/recorded time/correction state.

Logical graph semantics do not require a graph database.

---

# 7. Supersession timing

Supersession may be established:

1. atomically with successor initiation; or
2. later between already-existing Decisions.

Late-recorded Supersession preserves effective and recorded time; earlier `as_known_at` views do not contain the relationship.

No predecessor Need/judgment/work facts are rewritten.

---

# 8. Owner-specific influence remains explicit

If Decision B uses only a Lesson, Evidence item, View, Recommendation, or Risk Assessment associated with Decision A, preserve the owner-specific binding.

Create a whole-Decision `PRIOR_DECISION_CONTEXT` edge only when Decision A itself was materially used.

---

# 9. Persistence shape

Semantics equivalent to:

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
  typed_basis/scope
  target_as_known_at      # context edges
  correction_reference
```

R2 PostgreSQL persistence should use a many-to-many-capable typed relationship representation rather than fixed one-predecessor columns as the canonical schema assumption.

---

# 10. Query semantics

Expected semantic capabilities include:

```text
get_renewal_predecessors/successors
get_superseded_decisions
get_superseding_decisions
get_lifecycle_lineage(depth, as_known_at)
get_material_prior_decision_context(as_known_at)
get_related_decision_graph(types, depth, as_known_at)
```

Queries preserve edge type/direction/time and return application-owned models.

---

# 11. R2 implementation boundary

R2 implements:

- `RENEWED_FROM`;
- `SUPERSEDES` many-to-many semantics;
- resolved/unresolved Supersession without lifecycle rewrite;
- lineage-cycle prevention;
- effective/recorded relationship history;
- relationship correction compatibility;
- future-compatible contextual-edge storage shape.

R2 does not implement candidate retrieval, `PRIOR_DECISION_CONTEXT` commands, AI relationship selection, generic graph infrastructure, or visualization.

---

# 12. Validation/tests

R2 tests cover:

- renewal source/target differ;
- renewal target eligibility from substantive resolution or externally eliminated Need;
- renewal does not reopen target;
- Supersession targets unresolved or substantively resolved Decisions without changing historical axes;
- one-to-many/many-to-one Supersession;
- self relationship rejected;
- direct/indirect mixed lineage cycles rejected;
- late relationship excluded from earlier as-known-at;
- relationship correction non-destructive.

Later context tests cover target knowledge cutoff and retrieval-vs-material-use.

---

# 13. Requirements traceability

| Requirement | Consequence |
|---|---|
| `DEC-009` | renewed judgment uses new linked Decision. |
| `DEC-011`, `DEC-016` | Supersession preserves histories and remains orthogonal/no one-to-one default. |
| `DEC-018` | late relationship/correction facts preserve known/effective history. |
| `MEM-005`, `MEM-006` | relationship history/corrections are non-destructive and support-strength bounded. |
| `MEM-011` | contextual edge binds historical target state actually used. |

---

# 14. Spec-readiness gate

Ready only when:

1. renewal eligibility is expressed through Need/judgment dimensions, not stale terminal enum;
2. Supersession never replaces lifecycle axes;
3. no unsupported cardinality remains;
4. lineage acyclicity/context temporal cycles are explicit;
5. historical target binding is explicit;
6. relationship correction is non-destructive;
7. storage remains graph-technology neutral.
