# wiki/_schema.md

## Purpose

Defines the structural rules of the Living Entity Wiki:

* document classification and naming;
* source eligibility and authority;
* `wiki/index.md` structure;
* entity boundaries and topology;
* entity-page structure;
* wiki-log semantics.

Procedures belong to the skills that perform them. Entry formatting and provenance belong to `wiki/_template.md`.

## Document Classification

Classification is structural. Do not store `doc_class` or `Doc-Class:` metadata.

### ADRs

Files under `docs/adr/` derive class from ADR `status`:

| Status                   | Class        |
| ------------------------ | ------------ |
| `proposed`               | `proposed`   |
| `accepted`               | `accepted`   |
| `rejected`               | `rejected`   |
| `deprecated`             | `deprecated` |
| `superseded by ADR-NNNN` | `superseded` |

ADR lifecycle is owned by `$to-adr-doc`.

### Non-ADR documents

| Location          | Class       |
| ----------------- | ----------- |
| `docs/current/`   | `current`   |
| `docs/proposed/`  | `proposed`  |
| `docs/research/`  | `research`  |
| `docs/reference/` | `reference` |
| `docs/process/`   | `process`   |

Apply the `docs/.wikiignore` exclusion boundary before classification. Anything project-owned remaining under `docs/` outside these locations or `docs/adr/` is unclassified.

New classified documents use `$to-doc`; existing classified documents use `$classify-doc`.

### Class semantics

| Class                                    | Meaning                      | Wiki authority                                                                                  |
| ---------------------------------------- | ---------------------------- | ----------------------------------------------------------------------------------------------- |
| `accepted`                               | Adopted ADR                  | Strict Invariant if effective/realized; otherwise Planned as `accepted, implementation pending` |
| `current`                                | Current architecture         | May support Strict Invariants                                                                   |
| `proposed`                               | Future direction             | May support Planned                                                                             |
| `research`                               | Unresolved investigation     | No active authority                                                                             |
| `reference`                              | Structured lookup material   | No active authority                                                                             |
| `process`                                | Repository working procedure | No architectural authority                                                                      |
| `rejected` / `deprecated` / `superseded` | Inactive ADR                 | No active authority                                                                             |

`research` and `reference` describe document role, not architectural scope.

## Living Entity Wiki Exclusion Boundary

`docs/.wikiignore` is the canonical boundary for documentation paths that are intentionally outside the Living Entity Wiki document universe.

Ignored paths are ordinary repository documentation, but the Living Entity Wiki does not classify, name, audit, synchronize, or treat them as architectural source material. An ignored document is not `process`, `unclassified`, or another hidden Wiki class. If its content should become Wiki source material, move or promote that content into a normal classified document or ADR through the applicable workflow.

The exclusion boundary is explicit and fail-closed:

* paths are relative to `docs/` and use `/` separators;
* surrounding whitespace is ignored;
* blank lines are ignored;
* a line whose first non-whitespace character is `#` is a comment;
* a path ending in `/` excludes that directory and all descendants;
* a path not ending in `/` excludes exactly that file;
* absolute paths, `.` or `..` path components, backslashes, globbing, and negation/re-inclusion syntax are unsupported and invalid;
* an entry does not need to exist yet; it may reserve an explicit future exclusion;
* `docs/.wikiignore` itself is outside document classification and cannot be excluded by one of its own entries.

Do not infer exclusions. An unfamiliar directory that is not explicitly matched by `docs/.wikiignore` remains inside the Wiki document universe and is unclassified unless normal classification rules apply.

Skills that construct a complete `docs/` classification universe must validate `docs/.wikiignore` before applying it. Invalid exclusion syntax is a structural error, not permission to omit a path from the universe.

## Target Class Rules

For non-ADR documents inside the Living Entity Wiki document universe, classify current content/purpose in this order:

1. structured lookup material → `reference`;
2. contributor/agent workflow instructions → `process`;
3. unresolved investigation/evaluation → `research`;
4. committed future state → `proposed`;
5. description of current system → `current`.

If `current` vs `proposed` is genuinely unclear, choose `proposed`.

Existing location determines current classification, not necessarily correct classification.

## Source Authority

There is no global precedence ladder.

Authority is claim-specific:

* code, configuration, tests, executable checks → implementation reality;
* accepted ADRs → active architectural decisions;
* `docs/current/` → current architectural description;
* entity pages → derived knowledge only.

Accepted ADRs may require future implementation.

`docs/current/` is usable as active authority only when materially consistent with applicable accepted ADRs and verified implementation evidence.

### Source conflicts

Material disagreement among applicable authorities is `[source-conflict]`.

Do not automatically choose a winner or rewrite derived wiki content to one side.

Resolve `[source-conflict]` before ordinary `[code-drift]` or `[doc-drift]`.

Detailed handling belongs to the `$wiki-sync` skill and the `$wiki-lint` skill.

## Entity Citations

Entity-document relationships exist only through inline `source:` citations.

There is no `linked_docs` registry.

### Strict Invariants

Eligible sources:

* accepted ADR;
* `docs/current/`.

An accepted ADR becomes a Strict Invariant only when:

* acceptance itself establishes the constraint; or
* a realization-required decision is verified as implemented.

Otherwise it remains Planned as:

`accepted, implementation pending`

### Planned

Eligible sources:

* proposed ADR;
* `docs/proposed/`;
* accepted ADR with implementation pending.

Rejected Approaches, Open Questions, and Boundary Rationale use provenance defined in `wiki/_template.md`.

## Implementation Evidence

Conclusion strength must match evidence.

Mechanically observable invariants may be positively verified from code, tests, configuration, executable checks, `$codegraph`, `$codebase-memory-mcp`, or equivalent evidence.

Intent-level invariants cannot be positively proven by absence of contradiction.

For those, the strongest clean conclusion is:

> no contrary implementation evidence found

Prefer deterministic checks for stable mechanically enforceable subsets.

## Document Naming

Folder = document role/state.
Filename prefix = architectural subject.

### ADR

With an active entity registry:

`000X-<entity-id>-<slug>.md`

Cross-cutting:

`000X-platform-<slug>.md`

ADR numbering and pre-bootstrap naming are owned by `$to-adr-doc`.

### Current / Proposed / Research / Reference

Entity-specific:

`<entity-id>-<slug>.md`

Optional qualifier:

`<entity-id>-<qualifier>-<slug>.md`

Cross-cutting:

`platform-<slug>.md`

Use `platform-` only when no meaningful primary entity exists.

### Process

`<topic-slug>.md`

No entity/platform prefix.

## Cross-Cutting Documents

A document is cross-cutting only when no meaningful primary entity owns it.

Genuinely cross-cutting `platform-` documents may be linked from `wiki/index.md` for discovery.

Do not duplicate entity-specific research/reference documents in the index.

## Entity Registry

`wiki/index.md` is the authoritative registry of active entities and sole owner of:

* Entity;
* Category;
* Implementation;
* Routing Anchors;
* Summary.

Required table:

```md
| Entity | Category | Implementation | Routing Anchors | Summary |
|---|---|---|---|---|
```

### Entity

Links to `wiki/entities/<entity-id>.md`.

Entity IDs are stable kebab-case slugs.

### Category

Exists only in the index.

Reuse existing categories where possible. New top-level categories require explicit approval.

### Implementation

Allowed values:

* `present` — some implementation exists;
* `pending` — architectural entity exists before implementation.

`present` does not mean feature-complete.

### Routing Anchors

A `present` entity may have at most 1–2 coarse anchors.

Anchors are starting hints, not ownership declarations or file inventories.

A `pending` entity normally has none.

### Summary

One concise scope sentence.

Do not include invariants, rationale, dependencies, rejected approaches, Planned work, or file inventories.

## Entity Boundaries

Initial decomposition comes from the owner-approved Entity Wiki Boundaries bootstrap process.

No single signal determines a boundary.

### Promotion test

After bootstrap, a new sub-boundary normally requires at least 2 of 3:

1. meaningful structural boundary;
2. independent invariants;
3. material fan-in from at least two entities outside its parent boundary.

Structural boundary is architectural evidence, not a directory-name test.

### ADR-only pending exception

An unimplemented concern may become `pending` when:

* it is the primary subject of at least two accepted ADRs;
* it forms a coherent boundary;
* it does not fit cleanly inside an existing entity.

Before creating an entity, check for existing scope, apply these rules, reuse an existing Category where possible, and create the page/index entry atomically.

Do not create near-duplicate entities because terminology changed.

## Boundary Rationale

Every entity page has Boundary Rationale with provenance from `wiki/_template.md`.

It explains why the architectural boundary exists.

Change it only through an explicit boundary/topology decision, not ordinary code movement.

## Entity Topology

After bootstrap, `$wiki-sync` owns:

* creation/promotion;
* rename;
* split;
* merge;
* removal;
* material scope change;
* Boundary Rationale change.

Topology changes must atomically keep the index, entity pages, explicit links, and semantic log consistent.

`wiki/entities/` contains active entities only. Do not keep tombstones.

## Entity Page Structure

Entity pages follow `wiki/_template.md` and have no YAML frontmatter.

They do not store:

* Category;
* Implementation;
* Routing Anchors;
* `last_updated`;
* `linked_docs`;
* structural dependency lists.

Cross-entity relationships appear only inside claims where the relationship itself is meaningful.

Do not maintain a hand-authored dependency graph.

## Wiki Log

`wiki/log.md` records substantive semantic wiki mutations, not tool executions.

Log changes such as:

* entity topology changes;
* material entity-content changes;
* `pending → present`;
* Planned → Strict Invariant;
* Routing Anchor changes;
* Boundary Rationale changes.

Do not log:

* clean `$wiki-lint`;
* `$wiki-synthesize` execution;
* `$wiki-sync` with no semantic mutation.

A semantic log entry lands atomically with the wiki mutation it describes.

Git remains byte-level history; `wiki/log.md` is semantic history.
