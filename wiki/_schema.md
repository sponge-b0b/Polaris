# wiki/_schema.md

## Purpose

This file defines the structural rules of the Living Entity Wiki:

* how documents under `docs/` are classified;
* how documents are named and attributed to entities;
* which sources may support which kinds of entity knowledge;
* how authoritative-source conflicts are treated;
* how entity boundaries are created and evolved; and
* the required structure and authority of `wiki/index.md`.

Procedures belong in the skills that perform them. Entity-entry wording and provenance formats belong in `wiki/_template.md`.

---

## Document Classification

Every file under `docs/` has a classification that is derived structurally rather than stored as a second independent `doc_class` field.

### ADRs

Files under `docs/adr/` derive `doc_class` from their ADR `status`.

The ADR lifecycle, allowed status values and transitions, content mutability, numbering, and creation rules are owned exclusively by the `$to-adr-doc` skill.

For wiki classification purposes:

| ADR status               | Derived `doc_class` |
| ------------------------ | ------------------- |
| `proposed`               | `proposed`          |
| `accepted`               | `accepted`          |
| `rejected`               | `rejected`          |
| `deprecated`             | `deprecated`        |
| `superseded by ADR-NNNN` | `superseded`        |

No separate `doc_class` field is stored in an ADR.

### Non-ADR documents

Every other project-owned document under `docs/` derives its classification from its folder:

| Location          | `doc_class` |
| ----------------- | ----------- |
| `docs/current/`   | `current`   |
| `docs/proposed/`  | `proposed`  |
| `docs/research/`  | `research`  |
| `docs/reference/` | `reference` |
| `docs/process/`   | `process`   |

No classification field or `Doc-Class:` line is stored inside these files.

A project-owned file under `docs/` that is outside `docs/adr/`, the five recognized folders above, and the External Scaffold Directories registry is unclassified and must be reported by `$wiki-lint` as `[unclassified-doc]`.

Classification and reclassification of an existing non-ADR document are owned by `$classify-doc`. Creation-time classification is owned by `$to-doc`.

---

## Document Classes

| `doc_class`  | Meaning                                                                            | Entity wiki treatment                                                                                                                                                    |
| ------------ | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `accepted`   | An adopted ADR decision                                                            | May support a Strict Invariant when the decision is already effective or has been verified as realized; otherwise may remain Planned as accepted, implementation pending |
| `current`    | Claims to describe the system as it exists now                                     | May support Strict Invariants, subject to source-conflict and implementation checks                                                                                      |
| `proposed`   | A committed future direction that is not yet current                               | May support Planned entries only                                                                                                                                         |
| `research`   | Investigation or evaluation whose outcome remains uncertain                        | Does not establish Planned or Strict Invariant content                                                                                                                   |
| `reference`  | Structured lookup material such as a ledger, inventory, registry, matrix, or table | Does not itself establish Planned or Strict Invariant content                                                                                                            |
| `process`    | Describes how contributors or agents work in the repository                        | Does not enter entity knowledge as architectural authority                                                                                                               |
| `rejected`   | ADR decision that was not adopted                                                  | Never active architectural authority                                                                                                                                     |
| `deprecated` | ADR decision that is no longer recommended                                         | Never active architectural authority                                                                                                                                     |
| `superseded` | ADR decision replaced by a later ADR                                               | Never active architectural authority                                                                                                                                     |

`reference` describes a document's **role**, not its architectural scope. A reference document may concern one entity or may be genuinely cross-cutting.

Likewise, `research` may concern one entity or span the platform.

---

## External Scaffold Directories

Some directories under `docs/` are owned and maintained by external skills whose file paths are part of their own contract.

Files in these directories:

* remain exactly where the owning skill places them;
* are treated as `process`;
* are not renamed using this project's entity-prefix convention; and
* are not moved by `$classify-doc`.

This is an explicit registry, not a naming heuristic.

| Directory      | Owned by                   | Why exempt                                                                                                                                 |
| -------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `docs/agents/` | `setup-matt-pocock-skills` | The owning skill relies on these exact paths; moving or renaming them would break subsequent runs and may create duplicate scaffold files. |

A directory not listed here is not assumed to be externally owned merely because its name is unfamiliar.

If another externally owned scaffold directory is discovered, verify its ownership and path requirements before adding it to this registry.

---

## Determining a Non-ADR Document's Target Class

When `$to-doc` creates a document, or `$classify-doc` determines the correct destination for an existing document, classify the **content**, not its current location.

Apply these rules in order; first match wins:

1. **Externally scaffolded**
   If the file belongs to a registered External Scaffold Directory, keep it in place as `process`.

2. **Reference material**
   If its primary purpose is structured lookup — a ledger, registry, matrix, inventory, catalog, or similar reference-oriented artifact — classify it as `reference`.

3. **Process material**
   If it primarily instructs a contributor or agent how to work in the repository rather than describing the system itself, classify it as `process`.

4. **Research material**
   If it investigates, compares, evaluates, or explores a question whose outcome remains genuinely undecided and may lead nowhere, classify it as `research`.

5. **Proposed architecture or behavior**
   If it expresses a committed future direction that is explicitly not yet current — planned, target-state, future, or conditional architecture — classify it as `proposed`.

6. **Current-state material**
   Otherwise, if it claims to describe the system as it exists now, classify it as `current`.

When the distinction between `current` and `proposed` is genuinely unclear, choose `proposed`.

This is the fail-safe direction: incorrectly treating current content as proposed delays its use as active authority, while incorrectly treating future content as current can cause not-yet-true claims to become active invariants.

An existing recognized folder tells you the document's **current classification**. It does not prevent `$classify-doc` from determining that the document now belongs to a different class.

---

## Source Authority and Conflict Handling

The Living Entity Wiki does not use a single global source-precedence ladder.

Authority depends on the kind of claim being evaluated.

### Implementation reality

Current source code, configuration, executable architecture tests, and relevant tests establish evidence about **what Polaris currently implements and does**.

### Architectural decisions

Accepted ADRs establish **active architectural decisions and constraints** until their lifecycle changes through `$to-adr-doc`.

Acceptance does not necessarily mean that a realization-required decision has already been implemented.

### Current architectural documentation

`docs/current/` describes **current architectural state**.

Its claims are usable as active authority only while they remain materially consistent with applicable accepted ADRs and verified implementation evidence.

### Entity wiki

`wiki/entities/` is always a derived synthesis layer.

It never outranks or silently corrects its authoritative sources.

---

## Source Conflicts

A material disagreement between authoritative evidence types is a first-class `[source-conflict]`.

Examples include:

* an accepted ADR conflicts with verified implementation;
* a `docs/current/` claim conflicts with an applicable accepted ADR;
* a `docs/current/` claim materially conflicts with verified implementation evidence.

When a `[source-conflict]` exists:

1. do not choose a winner automatically;
2. do not rewrite an entity claim merely to match one side;
3. surface the conflict for human resolution; and
4. update the derived wiki only after the authoritative-source disagreement has been resolved.

`[source-conflict]` is evaluated before ordinary `[code-drift]` or `[doc-drift]`.

The detailed audit procedure is owned by `$wiki-sync` and `$wiki-lint`.

---

## Entity Citation Rules

Entity-to-document relationships are represented only by inline `source:` citations attached to the specific claim they support.

There is no `linked_docs` registry or frontmatter field.

The inline citation is the single source of truth.

### Strict Invariants

A Strict Invariant must be backed by either:

* an ADR whose derived `doc_class` is `accepted`; or
* a `docs/current/` document.

Citation eligibility alone does not automatically make a claim a current invariant.

For an accepted ADR:

* an **immediately-effective constraint** may become a Strict Invariant upon acceptance; but
* a **realization-required decision** remains under Planned as `accepted, implementation pending` until implementation or other relevant current-state evidence verifies that the decision has been realized.

If authoritative sources materially disagree, apply `[source-conflict]` rather than deriving or rewriting an invariant.

### Planned

Planned entries may be backed by:

* `docs/proposed/`;
* ADRs with `status: proposed`; or
* accepted ADRs whose realization is still pending.

Planned content is explicitly not current implementation reality.

### Other entity sections

Citation and undocumented-session provenance rules for Rejected Approaches, Open Questions, and Boundary Rationale are defined in `wiki/_template.md`.

---

## Implementation Evidence and Drift

The strength of any implementation conclusion must match the strength of the available evidence.

### Mechanically observable invariants

When an invariant is mechanically observable, source inspection, tests, `codegraph`, `codebase-memory-mcp`, or executable architecture checks may positively verify that the implementation satisfies it.

Concrete contradictory evidence may produce `[code-drift]` unless the disagreement is actually a `[source-conflict]`.

### Architectural or intent-level invariants

Some invariants cannot be positively proven from repository structure.

For these:

* actively inspect plausible implementation surfaces for concrete contradictory evidence;
* report a concrete violation when one is found;
* do not treat absence of contradictory evidence as proof of compliance.

A clean search for violations means only:

> no contrary implementation evidence found.

It does not mean:

> invariant mechanically verified.

Where a stable mechanical subset of an architectural rule can be expressed as an executable architecture test or static check, prefer enforcing that subset mechanically rather than repeatedly asking the wiki to infer it.

---

## Document Naming Convention

Document folder and document prefix represent different dimensions:

* **folder** = document role or epistemic state;
* **filename prefix** = architectural subject.

### ADRs

When an active entity registry exists, use:

`000X-<primary-entity-id>-<slug>.md`

For a genuinely cross-cutting ADR with no primary entity:

`000X-platform-<slug>.md`

ADR numbering and pre-bootstrap naming behavior are owned by `$to-adr-doc`.

### Current, proposed, reference, and research documents

When a document primarily concerns one active entity:

`<primary-entity-id>-<slug>.md`

Optional qualifier:

`<primary-entity-id>-<qualifier>-<slug>.md`

Use a qualifier only when it materially improves scanning among several distinct documents for the same entity.

When a document genuinely has no primary entity:

`platform-<slug>.md`

This applies equally to:

* `docs/current/`;
* `docs/proposed/`;
* `docs/reference/`; and
* `docs/research/`.

Do not use `platform-` merely to avoid deciding which entity primarily owns a document.

### Process documents

`docs/process/` does not use entity or `platform-` prefixes.

Use:

`<topic-slug>.md`

A process document describes how work happens, not which architectural entity owns it.

### External scaffold directories

Files under registered External Scaffold Directories keep the names required by their owning skill.

---

## Cross-Cutting Documents

A cross-cutting document:

* spans multiple entities without a meaningful primary owner; or
* describes a platform-wide concern no single entity owns.

Use `platform-` only in those cases.

Cross-cutting documents retain their ordinary document class. For example:

* `docs/current/platform-observability-strategy.md`
* `docs/proposed/platform-deployment-topology.md`
* `docs/reference/platform-service-port-registry.md`
* `docs/research/platform-graph-retrieval.md`

Genuinely cross-cutting `platform-` documents are linked directly from `wiki/index.md` because no primary entity can be relied upon as their discovery path.

Entity-specific `reference` and `research` documents do not receive duplicate index entries merely because they exist.

---

# Entity Registry

## `wiki/index.md` Authority

`wiki/index.md` is the authoritative registry of **active entities**.

It is also the single source of truth for:

* entity category;
* entity implementation state;
* entity routing anchors; and
* the entity's short scope summary.

Entity pages do not duplicate this metadata.

The required active-entity table is:

```md
## Entities

| Entity | Category | Implementation | Routing Anchors | Summary |
|---|---|---|---|---|
| [Runtime](entities/runtime.md) | Runtime | present | `src/polaris/runtime/` | Canonical workflow execution and runtime contracts. |
| [Approval](entities/approval.md) | Governance | pending | — | Approval and human-decision boundary. |
```

### Entity

The link points to:

`wiki/entities/<entity-id>.md`

The filename is the canonical Entity ID and uses kebab-case.

### Category

Category exists only in `wiki/index.md`.

Reuse an existing category when an entity clearly belongs to it.

Introducing a new top-level category is an architectural classification judgment and must be surfaced for explicit approval rather than silently created.

### Implementation

Allowed values:

* `present` — an implementation exists; this does not imply feature completeness or that all Planned work is finished.
* `pending` — the entity exists architecturally but no implementation has yet been established.

A `pending` entity whose implementation now exists must be reviewed and promoted to `present`.

### Routing Anchors

Each `present` entity may have no more than 1–2 coarse routing anchors.

Routing anchors are:

* starting hints for identifying which entity to inspect first;
* intentionally non-exhaustive; and
* not ownership declarations or substitutes for the code graph.

Prefer stable directory-level anchors where possible.

Good:

`src/polaris/runtime/`

Avoid detailed file inventories.

If a touched path clearly matches one entity's routing anchors, `$wiki-sync` loads that entity first.

If routing is ambiguous, crosses boundaries, or matches no anchor, use current repository analysis through `codegraph`, `codebase-memory-mcp`, or other appropriate project discovery tooling rather than guessing.

A `pending` entity normally has no source routing anchor because no implementation yet exists.

### Summary

The Summary is one concise sentence describing entity scope.

It must not contain:

* invariants;
* architectural rationale;
* dependency graphs;
* rejected approaches;
* planned work; or
* detailed file inventories.

Those belong elsewhere.

---

## Index Structural Integrity

`$wiki-lint` treats the following as structural failures:

* an entity page exists but is absent from `wiki/index.md`;
* an index entry points to a missing entity page;
* duplicate Entity IDs;
* an invalid Implementation value;
* more than two Routing Anchors for an entity;
* routing anchors that no longer resolve without an intentional topology update;
* an entity marked `pending` even though implementation now clearly exists;
* duplicate or conflicting Category ownership outside the index; or
* other metadata that should be index-owned being reintroduced into entity pages.

`wiki/entities/` contains active entities only.

Retired or obsolete entities are not kept as tombstone pages.

Git and authoritative ADR/document history preserve the historical record.

---

# Entity Boundaries

## Initial Decomposition

The initial entity decomposition is established through the owner-approved Entity Wiki Boundaries process.

No single signal determines an entity boundary.

The decomposition should cross-reference architecture structure, dependency evidence, accepted decisions, current architecture documentation, domain boundaries, and other relevant evidence rather than treating directory structure alone as architecture.

The approved result becomes the initial `wiki/index.md` registry and entity set.

---

## Promotion Test

After bootstrap, a newly surfaced sub-boundary may be promoted to its own entity when it meets at least **2 of 3**:

1. **Structural boundary**
   It has a meaningful implementation boundary distinct from siblings.

2. **Independent invariants**
   It carries constraints that are not merely inherited from its parent.

3. **Cross-entity fan-in**
   It is materially depended upon by at least two entities outside its own parent boundary.

The structural-boundary criterion is evidence, not a directory-name test. Use current repository analysis when necessary.

### ADR-only exception

A concern with no implementation yet may still become an entity with `Implementation: pending` when:

* it is the primary subject of at least two accepted ADRs;
* it carries a coherent architectural boundary of its own; and
* it does not fit cleanly inside an existing entity's invariants.

Such an entity cannot be positively checked against implementation until implementation exists.

---

## Entity Naming and Creation

Entity IDs are stable kebab-case slugs.

Example:

`rag-pipeline`

Entity path:

`wiki/entities/rag-pipeline.md`

Before creating an entity:

1. search `wiki/index.md` for an existing entity covering the same concept, by scope as well as name;
2. apply the promotion rules where this is a newly surfaced sub-boundary;
3. reuse an existing Category where appropriate;
4. surface creation of a new top-level Category for explicit approval;
5. create the entity using `wiki/_template.md`;
6. add the corresponding `wiki/index.md` entry in the same operation.

A near-duplicate entity must never be created merely because a later session uses different terminology for an existing boundary.

---

## Boundary Rationale

Every entity page must contain a Boundary Rationale using the provenance rules in `wiki/_template.md`.

A Boundary Rationale explains **why the architectural boundary exists**, not what files happen to be located inside it.

It may change only as part of an explicit entity-boundary or topology decision.

Ordinary refactoring, file movement, or package reorganization does not by itself justify rewriting Boundary Rationale.

---

## Entity Topology Changes

`$wiki-sync` owns living changes to entity topology after bootstrap.

Supported topology changes include:

* rename;
* split;
* merge;
* removal/retirement;
* promotion of a new sub-boundary; and
* a material scope change to an existing boundary.

These operations must keep:

* `wiki/index.md`;
* affected entity pages;
* explicit entity links; and
* the semantic `wiki/log.md` mutation record

consistent in the same atomic change.

### Rename

Rename the entity and update its index entry and explicit entity links atomically.

Do not create a replacement entity while leaving the old one active.

### Split

Apply the promotion/boundary rules to the resulting entities.

Redistribute only the knowledge that actually belongs to each resulting scope.

Remove the old entity if it no longer describes an active boundary.

### Merge

Choose or create the surviving entity.

Combine only still-valid knowledge, deduplicate overlapping claims, update the index, and remove obsolete entity pages.

### Removal

When an architectural boundary genuinely ceases to exist, remove it from the active registry and delete its entity page.

Do not retain a tombstone entity.

Historical information remains available through ADRs, other authoritative documents, Git history, and the semantic wiki log.

---

# Entity Page Structure

Entity pages contain architectural knowledge, not registry metadata.

They use the structure defined by `wiki/_template.md`.

Entity pages have **no YAML frontmatter**.

In particular, they do not independently store:

* Category;
* Implementation state;
* Routing Anchors;
* `last_updated`;
* `linked_docs`; or
* structural upstream/downstream dependency lists.

Cross-entity relationships appear only when they are meaningful parts of a specific invariant, rejected approach, open question, planned decision, or boundary rationale.

Do not reconstruct a hand-maintained dependency graph inside the wiki.

---

# Wiki Log Semantics

`wiki/log.md` records substantive mutations to the Living Entity Wiki.

Examples:

* entity created;
* entity updated;
* entity promoted;
* entity renamed;
* entity split or merged;
* entity removed;
* pending implementation promoted to present;
* Planned decision promoted to Strict Invariant;
* boundary rationale changed through an approved topology decision.

It does **not** record tool execution merely because a tool ran.

A clean `$wiki-lint` run creates no log entry and no commit.

A `$wiki-synthesize` run creates no log entry merely to record that synthesis was performed.

When a substantive wiki mutation occurs, its semantic log entry must land atomically with the corresponding wiki change.

Git remains the byte-level history; `wiki/log.md` is the concise semantic history of meaningful wiki evolution.
