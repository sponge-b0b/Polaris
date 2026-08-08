---
name: wiki-lint
description: Audit the Living Entity Wiki as a whole for structural integrity, citation validity, authoritative-source conflicts, derived-document drift, implementation contradictions, stale questions, and classification hygiene.
compatibility: product=codex product=claude-code system=git network=none
---

# Wiki Lint

`$wiki-lint` performs an independent whole-wiki audit.

It is the backstop for:

* missed `$wiki-sync` runs;
* stale derived claims;
* source disagreements;
* broken citations;
* structural corruption;
* missed lifecycle transitions.

`$wiki-sync` maintains one change.

`$wiki-lint` audits accumulated state.

A clean run reports only. It does not mutate the wiki, append `wiki/log.md`, or create a commit.

## When to Run

Run `$wiki-lint`:

* on demand;
* after work spanning multiple entities;
* after large architecture/document changes;
* when wiki drift is suspected;
* before relying heavily on the wiki after extended ad hoc work.

Do not run automatically for trivial edits.

## Audit Order

Run checks in this order:

1. structural integrity;
2. citation resolution and eligibility;
3. authoritative-source consistency;
4. derived-document drift;
5. implementation drift;
6. Open Question review;
7. cross-entity contradictions;
8. document classification hygiene.

Order matters.

Do not repair or classify downstream drift before determining whether the authoritative sources themselves conflict.

# 1. Structural Integrity

`wiki/index.md` is the authoritative active-entity registry.

Report `[structural]` for issues such as:

* entity page missing from the index;
* index entry with no entity page;
* duplicate Entity IDs;
* duplicate active scope;
* invalid `Implementation` value;
* more than two Routing Anchors;
* broken or meaningless Routing Anchors;
* `pending` when implementation clearly exists;
* `present` when implementation cannot reasonably be located;
* retired/tombstone pages under `wiki/entities/`;
* registry metadata duplicated into entity pages;
* YAML frontmatter reintroduced;
* structural dependency lists reintroduced.

Allowed `Implementation` values:

```text id="g8y1oy"
present
pending
```

A `pending` entity normally has no implementation Routing Anchor.

## Entity Page Structure

Each page must conform to `wiki/_template.md`.

Required where applicable:

* heading with stable Entity ID;
* Boundary Rationale with valid provenance;
* Strict Invariants section when invariants exist.

Optional sections may be absent when empty:

* Rejected Approaches;
* Open Questions;
* Planned.

Report `[structural]` if obsolete entity metadata reappears, including:

```text id="sgx7ow"
category:
last_updated:
linked_docs:
implementation:
```

## Boundary Rationale

Every entity needs a Boundary Rationale with provenance allowed by `wiki/_template.md`, such as:

```text id="1kvfnh"
source: docs/...
source: owner-approved entity boundary determination
source: owner-approved entity promotion
```

Report `[structural]` when rationale is:

* missing;
* missing provenance;
* merely a directory description;
* apparently rewritten to follow ordinary code movement rather than an explicit topology decision.

Do not invent missing rationale.

# 2. Citation Resolution and Eligibility

Entity-document relationships exist only through inline `source:` citations.

Do not reconstruct `linked_docs`.

Audit citations in the context of the section they support.

## Broken Citation

Report:

```text id="05bnhs"
[broken-doc-citation]
```

when a cited `docs/...` path no longer resolves.

Include:

* entity;
* section;
* claim;
* missing path.

Do not automatically delete the claim; determine whether the source moved, was removed, or was replaced.

## Invalid or Stale Citation

Report:

```text id="v1rz9a"
[invalid-citation]
```

when the cited source type was never eligible for that section.

Report:

```text id="mtzmmf"
[stale-citation]
```

when it was once eligible but lifecycle/classification changed.

Use the eligibility rules in `wiki/_schema.md` and `wiki/_template.md`.

Core rules:

### Strict Invariants

Eligible sources:

* accepted ADR;
* `docs/current/`.

### Planned

Eligible sources:

* proposed ADR;
* `docs/proposed/`;
* accepted ADR with implementation still pending.

### Rejected Approaches

Use provenance defined by `wiki/_template.md`, including:

```text id="oh7e28"
source: docs/...
source: owner-confirmed session decision, undocumented
source: session experiment, undocumented
```

### Open Questions

Valid provenance includes:

```text id="xyxvdz"
source: docs/...
source: owner-raised session question, undocumented
source: agent-observed during session, unresolved
```

### Boundary Rationale

Use `wiki/_template.md`.

`[stale-citation]` is about authority lifecycle.

`[doc-drift]` is about changed meaning.

# 3. Authoritative-Source Consistency

Before ordinary drift checks, compare materially relevant authorities.

Authority is claim-specific:

* implementation evidence → what currently exists or behaves;
* accepted ADRs → active architectural decisions;
* `docs/current/` → current architectural description;
* entity pages → derived knowledge only.

Report:

```text id="7eqt6t"
[source-conflict]
```

when those authorities materially disagree about architecture, ownership, constraints, or current behavior.

For each finding include:

* affected entity/claim;
* conflicting sources;
* what each source says;
* relevant implementation evidence;
* why the disagreement matters.

Do not:

* select a winner;
* rewrite the entity to one source;
* edit current docs automatically;
* change ADR lifecycle;
* infer which authority is wrong.

Skip ordinary drift repair for the disputed claim until the underlying conflict is resolved.

# 4. Derived Document Drift

Report:

```text id="4x9nrb"
[doc-drift]
```

when a valid source still has appropriate authority but the derived entity claim no longer reflects its current meaning.

Do not report drift merely because a document changed.

The meaning must actually have diverged.

## Strict Invariants

For claims sourced from `docs/current/`:

* confirm the source is still current;
* ensure no `[source-conflict]`;
* compare the invariant with the document's present meaning.

## Planned

For claims sourced from `docs/proposed/` or proposed ADRs:

* compare against the current proposal;
* report drift when the proposal changed, disappeared, or was substantively rewritten while the wiki retained the old direction.

## Accepted Implementation-Pending Decisions

For Planned entries backed by accepted ADRs, check whether:

* the ADR remains accepted;
* `accepted, implementation pending` is still accurate;
* implementation has already realized the decision.

If realization is clear and the wiki did not transition, report the appropriate structural/drift finding.

Do not manufacture realization from weak evidence.

# 5. Implementation Drift

Report:

```text id="t1asap"
[code-drift]
```

when implementation evidence materially contradicts an active Strict Invariant and the authoritative sources behind that invariant are otherwise consistent.

Do not use `[code-drift]` to mean:

> I could not prove this from code.

## Mechanically Observable Invariants

Use appropriate evidence such as:

* source inspection;
* tests;
* executable architecture checks;
* `$codegraph`;
* `$codebase-memory-mcp`;
* configuration.

If evidence directly proves or disproves the rule, a positive or negative conclusion is valid.

## Architectural / Intent-Level Invariants

For rules that cannot be mechanically proven:

1. identify plausible concrete violations;
2. inspect relevant implementation surfaces;
3. report `[code-drift]` only when contradictory evidence exists.

If none is found, the strongest valid conclusion is:

```text id="c16f20"
no contrary implementation evidence found
```

not:

```text id="jf12gi"
verified
```

Prefer deterministic architecture tests/static rules for mechanically enforceable subsets.

# 6. Open Question Review

Report:

```text id="n6mevy"
[stale-question]
```

when an Open Question has remained unresolved long enough to deserve deliberate review.

Approximately 60 days is a useful default, not an expiry rule.

Consider:

* entity activity;
* related architecture changes;
* continued relevance;
* whether later evidence appears to have answered it.

A stale question may be:

* resolved;
* confirmed still open;
* converted into another durable section;
* removed as no longer meaningful.

Do not fabricate a resolution to clear lint.

# 7. Cross-Entity Contradictions

Scan active entity claims for material architectural contradictions.

Report the conflicting claims and their sources.

If the contradiction comes from underlying authoritative sources, classify the root issue as `[source-conflict]`.

If authorities agree and one entity is stale, use the appropriate drift finding.

Do not auto-resolve semantic contradictions.

# 8. Document Classification Hygiene

Report:

```text id="p74vci"
[unclassified-doc]
```

for project-owned files under `docs/` whose classification cannot be derived from:

* `docs/adr/` plus ADR status;
* `docs/current/`;
* `docs/proposed/`;
* `docs/research/`;
* `docs/reference/`;
* `docs/process/`;
* the External Scaffold Directories registry in `wiki/_schema.md`.

Do not assume unfamiliar folders are externally owned.

Use `$classify-doc` for existing non-ADR documents.

# Finding Priority

When several findings apply to the same claim, prefer the root cause:

```text id="mqon3j"
[source-conflict]
      ↓
[broken-doc-citation]
      ↓
[stale-citation] / [invalid-citation]
      ↓
[doc-drift]
      ↓
[code-drift]
```

This is root-cause ordering, not a universal severity ranking.

Avoid duplicate downstream findings when an upstream issue already explains them.

# Resolution Rules

`$wiki-lint` reports judgment-bearing issues; it does not silently decide architecture.

Never auto-resolve:

* `[source-conflict]`;
* `[code-drift]`;
* `[doc-drift]`;
* ambiguous `[stale-citation]`;
* judgment-bearing `[invalid-citation]`;
* `[stale-question]`;
* cross-entity semantic contradictions;
* entity topology;
* Boundary Rationale.

## Mechanical Fixes

A fix may be applied only when exactly one correction is unambiguous and no architectural judgment is required.

Examples:

* stale link after a known rename;
* formatting damage;
* duplicate registry row;
* Routing Anchor affected only by an established path rename.

Do not treat claim removal, promotion, source selection, or topology changes as mechanical merely because the edit is small.

When uncertain, report instead of fixing.

# Reporting

Use these prefixes:

```text id="3pcjrz"
[source-conflict]
[code-drift]
[doc-drift]
[stale-citation]
[invalid-citation]
[broken-doc-citation]
[unclassified-doc]
[stale-question]
[structural]
```

Each finding should include enough context to act on it:

* entity;
* claim/section;
* evidence or sources;
* why it is a problem;
* required next action or owner judgment.

End with a count by finding type.

Example:

```text id="mxwxsj"
Wiki lint: 3 issues found
- [source-conflict]&#58; 1
- [doc-drift]&#58; 1
- [structural]&#58; 1
```

For a clean run:

```text id="31j0q1"
Wiki lint: 0 issues found
```

Omit zero-count categories.

# Logging and Commits

`wiki/log.md` records semantic wiki mutations, not lint executions.

If `$wiki-lint` only reports findings or finds nothing:

* do not edit `wiki/log.md`;
* do not create a lint-only commit.

If it applies an allowed mechanical fix:

* append one semantic log entry describing the actual mutation;
* land the fix and log atomically;
* defer commit ownership to a calling workflow when one exists.

Do not log issue counts or clean lint runs.

# Relationship to Other Skills

Use:

* `$wiki-sync` — per-change synchronization;
* `$to-adr-doc` — ADR lifecycle;
* `$to-doc` — new non-ADR documents;
* `$classify-doc` — existing non-ADR classification;
* `$wiki-synthesize` — higher-inference cross-entity synthesis.

`$wiki-lint` is for direct integrity/conflict/drift auditing, not synthesis.

# Out of Scope

`$wiki-lint` does not:

* bootstrap the wiki;
* decide new entity boundaries;
* settle source conflicts;
* rewrite architectural decisions;
* create ADRs merely to clear findings;
* infer intent-level compliance from absence of evidence;
* maintain `linked_docs`, timestamps, reciprocal dependency lists, or entity frontmatter;
* log clean runs;
* perform cross-entity synthesis.

Its job is to determine whether the Living Entity Wiki can still be trusted, why not when it cannot, and where normal lifecycle or owner judgment is required.
