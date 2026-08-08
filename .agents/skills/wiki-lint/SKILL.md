---
name: wiki-lint
description: Audits the Living Entity Wiki as a whole for authoritative-source conflicts, drift between derived claims and their sources, implementation contradictions, invalid or broken citations, stale open questions, unclassified documents, and structural registry/entity integrity. Use on-demand or after work spanning multiple entities. Distinct from wiki-sync, which maintains the wiki around one specific change.
compatibility: product=codex product=claude-code system=git network=none
---

# Wiki Lint

`$wiki-lint` performs an independent whole-wiki audit.

It is the backstop for:

* missed `$wiki-sync` invocations;
* stale derived claims;
* source disagreements;
* structural wiki corruption; and
* lifecycle transitions that were not reflected in the Living Entity Wiki.

`$wiki-sync` maintains the wiki around a specific change.

`$wiki-lint` audits the accumulated state independently of any one change.

---

# When This Runs

Run `$wiki-lint`:

* on demand;
* after a session that materially touched multiple entities;
* after large architectural or documentation changes;
* when wiki drift is suspected; or
* before relying heavily on the wiki after an extended period of ad hoc work.

Do not run automatically for trivial edits.

A clean lint run reports its result but creates no wiki mutation, log entry, or commit.

---

# Audit Order

Run checks in this order:

1. structural integrity;
2. citation resolution and eligibility;
3. authoritative-source consistency;
4. derived-document drift;
5. implementation drift;
6. Open Question age/review;
7. cross-entity contradictions.

This ordering matters.

Do not recommend repairing a derived entity claim before determining whether its authoritative sources already disagree.

---

# 1. Structural Integrity

## Active Entity Registry

`wiki/index.md` is the authoritative registry of active entities.

Report `[structural]` for:

* an entity page under `wiki/entities/` that has no corresponding index entry;
* an index entry whose entity page does not exist;
* duplicate Entity IDs;
* duplicate active entries for the same architectural scope;
* an invalid `Implementation` value;
* more than two Routing Anchors for one entity;
* Routing Anchors that no longer resolve or no longer provide a meaningful routing start;
* a `pending` entity whose implementation now clearly exists;
* an entity marked `present` whose supposed implementation cannot be located and whose state is not otherwise explainable;
* registry metadata duplicated back into entity pages;
* YAML frontmatter reintroduced into entity pages;
* structural upstream/downstream dependency lists reintroduced into entity pages; or
* retired/tombstone pages remaining under `wiki/entities/`.

Allowed Implementation values are:

```text id="kqs1z4"
present
pending
```

A `pending` entity normally has no implementation Routing Anchor.

---

## Entity Page Structure

Each entity page must follow `wiki/_template.md`.

Required:

* entity heading with stable Entity ID;
* Boundary Rationale with valid provenance;
* Strict Invariants section where invariants exist.

Optional sections may be omitted when empty:

* Rejected Approaches;
* Open Questions;
* Planned.

Report `[structural]` if obsolete metadata appears, including:

```text id="spukv6"
category:
last_updated:
linked_docs:
implementation:
```

These belong nowhere in entity frontmatter because entity pages no longer use frontmatter.

---

## Boundary Rationale

Every entity must contain a Boundary Rationale.

Its provenance must be either:

```text id="9gcld0"
source: docs/...
source: owner-approved entity boundary determination
source: owner-approved entity promotion
```

or another explicitly approved topology-decision source defined by `wiki/_template.md`.

Report `[structural]` when Boundary Rationale:

* is missing;
* lacks required provenance;
* merely describes directory structure rather than architectural reasoning; or
* appears to have been casually rewritten to follow code movement rather than an explicit topology decision.

Do not attempt to reconstruct or invent the missing rationale automatically.

---

# 2. Citation Resolution and Eligibility

Entity-document relationships exist only through inline `source:` citations.

Do not look for or reconstruct a `linked_docs` registry.

Audit each inline citation in context of the section containing it.

---

## `[broken-doc-citation]`

Report:

```text id="ag6ns7"
[broken-doc-citation]
```

when an inline `docs/...` citation no longer resolves.

Include:

* entity;
* section;
* claim;
* missing path.

A missing citation does not prove the claim itself is wrong.

Do not automatically delete the claim.

Determine whether:

* the document moved;
* the document was intentionally removed;
* another active source now supports the claim; or
* the derived claim should be retired.

---

## `[invalid-citation]`

Citation validity is section-specific.

### Strict Invariants

Valid sources:

* accepted ADR;
* `docs/current/`.

Anything else is invalid.

Examples of invalid Strict Invariant sources:

```text id="zzr5b9"
proposed ADR
docs/proposed/
docs/research/
docs/reference/
docs/process/
rejected ADR
deprecated ADR
superseded ADR
```

### Planned

Valid sources:

* proposed ADR;
* `docs/proposed/`;
* accepted ADR whose realization remains pending.

A rejected, deprecated, or superseded ADR cannot continue backing active Planned content.

### Rejected Approaches

Valid provenance is defined by `wiki/_template.md`, including:

```text id="ge42dh"
source: docs/...
source: owner-confirmed session decision, undocumented
source: session experiment, undocumented
```

An undocumented agent judgment that does not meet those provenance rules is invalid.

### Open Questions

Valid provenance includes:

```text id="d1e761"
source: docs/...
source: owner-raised session question, undocumented
source: agent-observed during session, unresolved
```

### Boundary Rationale

Use the provenance rules in `wiki/_template.md`.

Report `[invalid-citation]` with the entity, section, claim, and invalid source.

---

## `[stale-citation]`

Report:

```text id="ypx8am"
[stale-citation]
```

when the cited document still exists but its lifecycle/class can no longer support the section in which it is used.

Common examples:

* Strict Invariant cites an ADR that changed from `accepted` to `deprecated`;
* Strict Invariant cites an ADR now superseded;
* Planned cites an ADR now rejected;
* a document moved from `current` to `research` but remains the sole source of an active invariant.

`[stale-citation]` concerns authority lifecycle.

`[doc-drift]` concerns meaning/content.

---

# 3. Authoritative-Source Consistency

Evaluate relevant authoritative sources before ordinary drift.

Report:

```text id="pxae88"
[source-conflict]
```

when materially relevant authorities disagree.

Authority is claim-specific:

* implementation evidence establishes what currently exists or behaves;
* accepted ADRs establish active architectural decisions;
* `docs/current/` claims to describe current architecture;
* entity pages are derived and never resolve conflicts among those sources themselves.

---

## Common Source Conflicts

Examples include:

### Accepted ADR vs implementation

```text id="rzzuj5"
accepted ADR → architecture A
verified implementation → architecture B
```

### Accepted ADR vs current documentation

```text id="hwe0ud"
accepted ADR → PostgreSQL canonical
docs/current/ → Qdrant canonical
```

### Current documentation vs implementation

```text id="sq5g8w"
docs/current/ → interface routes through application service
verified code → interface bypasses application service
```

Not every wording difference is a conflict.

Report only material disagreement affecting architecture, ownership, constraints, or derived entity knowledge.

---

## Source Conflict Behavior

For each `[source-conflict]`, report:

* affected entity and claim;
* conflicting sources;
* what each source currently says;
* relevant implementation evidence;
* why the disagreement is material.

Do not:

* rewrite the entity to match one source;
* automatically edit a current document;
* change ADR lifecycle;
* infer which authority is wrong.

Resolve the underlying sources first.

Skip ordinary drift repair for the disputed derived claim until the conflict is resolved.

---

# 4. `[doc-drift]`

`[doc-drift]` means a derived entity claim no longer accurately reflects the meaning of the valid document source it cites.

This check is section-aware.

---

## Strict Invariants

For invariants sourced from `docs/current/`:

1. resolve the source;
2. confirm it remains `current`;
3. ensure there is no `[source-conflict]`;
4. compare the entity claim with the document's current meaning.

Report `[doc-drift]` when:

* the source changed materially;
* the entity still expresses the old constraint; and
* the underlying authorities are otherwise consistent.

Do not report `[doc-drift]` merely because the source document was edited.

The derived meaning must actually have become stale.

---

## Planned

For Planned entries sourced from:

* `docs/proposed/`; or
* proposed ADRs,

compare the entry with the current proposed direction.

Report `[doc-drift]` when:

* the proposal changed materially;
* the Planned entry still reflects the old proposal;
* the proposal was removed but the Planned entry remains; or
* a proposed ADR was substantively rewritten while its old Planned synthesis remained unchanged.

The fact that classification/status stayed `proposed` does not prevent drift.

---

## Accepted, Implementation-Pending Planned Entries

For Planned entries sourced from accepted ADRs:

verify that:

* the ADR remains accepted;
* the entry is still correctly marked `accepted, implementation pending`; and
* implementation has not already clearly realized the decision.

If implementation is now realized, this is a missed lifecycle transition.

Report it as `[structural]` or `[doc-drift]` according to the concrete failure:

* state transition metadata/placement problem → `[structural]`;
* derived description itself is stale → `[doc-drift]`.

Do not automatically promote it unless the realization evidence is clear and the mechanical-fix policy below allows the change.

---

# 5. `[code-drift]`

`[code-drift]` means implementation evidence materially contradicts an active Strict Invariant while the authoritative sources behind the invariant are not themselves in conflict.

Do not use `[code-drift]` as shorthand for:

> I could not prove this invariant from the code.

---

## Mechanically Observable Invariants

Examples may include:

* forbidden dependency directions;
* ownership of a concrete execution path;
* use of one canonical composition root;
* absence/presence of a specific transport bypass;
* architectural tests;
* configuration-level ownership rules.

Use appropriate evidence:

* source inspection;
* tests;
* executable architecture checks;
* `$codegraph`;
* `$codebase-memory-mcp`;
* configuration;
* other project discovery tooling.

When mechanically observable evidence contradicts the invariant, report `[code-drift]`.

When mechanically observable evidence confirms it, the invariant may be positively verified.

---

## Architectural or Intent-Level Invariants

Some invariants cannot be positively proven mechanically.

Examples:

* product-scope restrictions;
* "must not become autonomous trading";
* intent-level governance boundaries;
* constraints whose full meaning cannot be reconstructed from imports or call graphs.

For these:

1. identify plausible concrete manifestations of a violation;
2. inspect relevant implementation surfaces;
3. report `[code-drift]` only when concrete contradictory evidence exists.

If no contradictory evidence is found, the strongest valid result is:

```text id="yhzipx"
no contrary implementation evidence found
```

Do not report:

```text id="mwd3io"
verified
```

unless the invariant is actually mechanically observable.

Absence of evidence is not positive proof of an intent-level constraint.

---

## Prefer Mechanical Enforcement Where Possible

If a stable subset of an invariant can be encoded as:

* an architecture test;
* dependency rule;
* static check;
* schema constraint; or
* deterministic configuration test,

prefer that enforcement for the mechanically testable subset.

The wiki should preserve the reason and broader architectural meaning, not substitute for deterministic enforcement that can cheaply exist.

---

# 6. `[stale-question]`

Open Questions exist to preserve unresolved concerns, not accumulate indefinitely.

Report:

```text id="m7ukus"
[stale-question]
```

when an Open Question has remained unresolved long enough to warrant deliberate review.

A reasonable default is approximately 60 days, but this is a judgment threshold, not a hard expiry rule.

Consider:

* entity activity level;
* whether related architecture has changed;
* whether the question remains relevant;
* whether later evidence has implicitly answered it.

A stale question is not automatically invalid.

The correct response may be:

* resolve it;
* confirm it remains open;
* convert its outcome into another entity section; or
* remove it if it is no longer meaningful.

Do not fabricate a resolution merely to clear the lint finding.

---

# 7. Cross-Entity Contradictions

Scan active entity pages for direct architectural conflicts.

Examples:

```text id="5jflg2"
Entity A:
Persistence owns canonical record creation.

Entity B:
RAG owns canonical record creation.
```

or:

```text id="ko4bu2"
Entity A:
All workflow execution passes through RuntimeEngine.

Entity B:
This subsystem intentionally bypasses RuntimeEngine.
```

A contradiction check is lower-inference than `$wiki-synthesize`, but it is still semantic judgment rather than a mathematically deterministic comparison.

Report the conflicting claims and sources.

If the contradiction reflects disagreement among authoritative sources, classify the root issue as `[source-conflict]`.

If the authoritative sources agree and one entity is simply stale, use the appropriate drift finding.

Do not resolve contradictions automatically unless the correction is purely mechanical and unambiguous.

---

# 8. Document Classification Hygiene

Report:

```text id="plm4jw"
[unclassified-doc]
```

for a project-owned file under `docs/` whose classification cannot be structurally derived from:

* `docs/adr/` plus ADR `status`;
* `docs/current/`;
* `docs/proposed/`;
* `docs/research/`;
* `docs/reference/`;
* `docs/process/`; or
* the External Scaffold Directories registry in `wiki/_schema.md`.

Examples:

```text id="hwb0iz"
docs/random-architecture-notes.md
docs/designs/foo.md
```

Do not assume an unfamiliar folder is externally owned.

Use `$classify-doc` to classify or reclassify an existing non-ADR document.

---

# Finding Priority

When multiple findings apply to the same derived claim, prefer the root cause.

General priority:

```text id="a4pkwr"
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

This is not a universal severity scale.

It prevents duplicate findings where one upstream problem already explains the downstream mismatch.

For example:

* if an ADR is deprecated, report `[stale-citation]` rather than also claiming its entity wording drifted;
* if accepted ADR and current doc conflict, report `[source-conflict]` before suggesting either the entity or implementation is stale.

---

# Resolution Rules

`$wiki-lint` reports judgment-bearing problems; it does not silently decide architecture.

Never auto-resolve:

* `[source-conflict]`;
* `[code-drift]`;
* `[doc-drift]`;
* `[stale-citation]` where the correct replacement authority is unclear;
* `[invalid-citation]` requiring architectural judgment;
* `[stale-question]`;
* contradictory entity claims;
* entity promotion/topology decisions;
* Boundary Rationale.

---

## Mechanical Fixes

Mechanical fixes may be applied when there is exactly one unambiguous correction and no architectural judgment is required.

Examples may include:

* an explicit entity link still uses an old path after a known atomic rename;
* formatting damage;
* a clearly duplicated registry row;
* a Routing Anchor with an obvious path-only rename already established by Git history.

Do not treat claim removal, claim promotion, source selection, or boundary changes as mechanical merely because the edit itself is small.

When uncertain, report rather than fix.

---

# Reporting Format

Report findings with explicit prefixes:

```text id="rz6o95"
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

```text id="w8lf1s"
[source-conflict] persistence

Claim:
PostgreSQL is the canonical durable authority.

Sources:
- ADR-0012: PostgreSQL is canonical.
- docs/current/persistence-storage.md: Qdrant is canonical.
- implementation: PostgreSQL repositories remain the canonical writer.

Action:
Resolve the authoritative-source disagreement before changing the entity wiki.
```

---

# Summary

End every run with a compact count by finding type.

Example:

```text id="qvkbq8"
Wiki lint: 4 issues found
- [source-conflict]&#58; 1
- [doc-drift]&#58; 1
- [stale-question]&#58; 1
- [structural]&#58; 1
```

Omit zero-count categories.

For a clean run:

```text id="82b9qi"
Wiki lint: 0 issues found
```

A clean run is a report only.

Do not edit `wiki/log.md`.

Do not create a commit.

---

# Logging and Commits

`wiki/log.md` records substantive Living Entity Wiki mutations, not lint executions.

Therefore:

### No mutation

If `$wiki-lint` only reports findings or finds nothing:

* do not edit `wiki/log.md`;
* do not create a lint-only commit.

### Mechanical mutation

If `$wiki-lint` applies a permitted mechanical fix:

* append one semantic `wiki/log.md` entry describing the actual wiki mutation, not "lint ran";
* commit the fix and matching log entry atomically, unless a calling workflow already owns the commit.

Example:

```text id="dskxv9"
## [YYYY-MM-DD] registry-update | runtime — corrected renamed routing anchor
```

Do not log zero findings or issue counts as wiki history.

---

# Relationship to Other Skills

`$wiki-lint` does not perform ordinary per-change synchronization.

Use:

* `$wiki-sync` — maintain the wiki around a specific code/docs/ADR/topology change;
* `$to-adr-doc` — ADR creation and lifecycle;
* `$to-doc` — new non-ADR documents;
* `$classify-doc` — classification or reclassification of existing non-ADR documents;
* `$wiki-synthesize` — inferential cross-entity pattern synthesis.

`$wiki-synthesize` remains distinct because recurring themes and latent patterns require more inference than direct conflict/drift auditing.

---

# Out of Scope

`$wiki-lint` does not:

* bootstrap the initial entity wiki;
* decide new entity boundaries;
* automatically settle source conflicts;
* rewrite architectural decisions;
* create ADRs merely to eliminate lint findings;
* infer intent-level compliance from absence of code evidence;
* maintain `linked_docs`, timestamps, reciprocal dependency lists, or entity frontmatter;
* log clean audit runs;
* perform cross-entity synthesis of recurring themes.

Its job is to tell you whether the current Living Entity Wiki can still be trusted, why not when it cannot, and where human or normal lifecycle action is required.
