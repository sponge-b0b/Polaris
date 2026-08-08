---
name: to-doc
description: Create a new non-ADR document under docs/. Determines the correct structural class and filename from the Living Entity Wiki schema, writes the document in its canonical location, and invokes `$wiki-sync` when the new document can affect derived entity knowledge. Use for new non-ADR documents only; use `$classify-doc` for existing documents and `$to-adr-doc` for ADRs.
compatibility: product=codex product=claude-code network=none
---

# To Doc

`$to-doc` owns creation-time placement and naming of **new non-ADR documents** under `docs/`.

Its responsibility is intentionally narrow:

```text
content to create
      ↓
classify
      ↓
name
      ↓
write
      ↓
sync wiki when relevant
```

Document classification and naming rules are defined in `wiki/_schema.md`.

Do not duplicate those rules here.

For an existing document that needs classification, reclassification, relocation, or renaming, use `$classify-doc`.

For an ADR, use `$to-adr-doc`.

---

# 1. Confirm Scope

Use this skill only when creating a **new non-ADR document**.

If the requested document is an architectural decision that should be recorded as an ADR, stop and use `$to-adr-doc`.

If the document already exists, stop and use `$classify-doc`.

Do not convert an existing document into a "new" document merely to avoid its classification or reference-migration lifecycle.

---

# 2. Determine the Target Classification

Apply **Determining a Non-ADR Document's Target Class** from `wiki/_schema.md`.

Classify the proposed document by its intended content and role.

Possible project-owned target classes are:

```text
current
proposed
research
reference
process
```

Do not create or store:

```text
doc_class:
Doc-Class:
```

inside the document.

Classification is derived entirely from folder placement.

---

## Current vs. Proposed Ambiguity

When the distinction between `current` and `proposed` is genuinely unclear, use the schema's fail-safe rule:

```text
default to proposed
```

Do not classify not-yet-true architecture as `current` merely because implementation is expected soon.

---

# 3. Check External Scaffold Ownership

Before choosing the destination, inspect the External Scaffold Directories registry in `wiki/_schema.md`.

If the requested file belongs to a directory owned by another skill:

* do not create it through `$to-doc`;
* do not invent a project naming convention for it;
* use the owning skill or its prescribed workflow instead.

Externally owned scaffold paths are contracts of their owning skills.

An unfamiliar directory is not automatically an external scaffold.

---

# 4. Determine the Filename

Apply **Document Naming Convention** and **Cross-Cutting Documents** from `wiki/_schema.md`.

Do not restate those rules here.

When `wiki/index.md` contains the active entity registry:

* determine whether the document primarily belongs to one active entity;
* use that Entity ID as its prefix when appropriate;
* use `platform-` only when the document is genuinely cross-cutting with no meaningful primary entity;
* do not entity/platform-prefix `process` documents.

Use `wiki/index.md` as the authoritative source for active Entity IDs.

Do not infer a new Entity ID from a directory name or from terminology appearing only in the new document.

---

## Before Wiki Bootstrap

If no active entity registry yet exists in `wiki/index.md`, use:

```text
<slug>.md
```

for project-owned non-ADR documents.

Do not invent entity prefixes before the approved entity decomposition exists.

Later normalization, if needed, is handled through `$classify-doc`.

---

# 5. Determine the Destination

Map the target classification to its canonical folder:

```text
current   → docs/current/
proposed  → docs/proposed/
research  → docs/research/
reference → docs/reference/
process   → docs/process/
```

The destination is:

```text
docs/<target-class>/<filename>
```

If the target directory does not exist, create it lazily.

Create only the required directory.

Do not eagerly create the complete document-folder structure.

---

# 6. Write the Document

Create the new file directly at its canonical destination.

Do not:

* create it temporarily at the repository root;
* create it loose under `docs/` and classify it later;
* add classification metadata to its contents; or
* duplicate entity-registry metadata inside the document.

Write only the content appropriate to the document itself.

---

# 7. Invoke `$wiki-sync` When Relevant

If the Living Entity Wiki has not yet been bootstrapped, no synchronization is required.

Otherwise, synchronization depends on the new document's class.

---

## New `current` Document

Invoke `$wiki-sync`.

The new document may contain architectural knowledge eligible for a `Strict Invariant`.

`$wiki-sync` must:

1. determine the relevant entity;
2. identify any meaningful current architectural constraints;
3. check applicable accepted ADRs and implementation evidence;
4. evaluate `[source-conflict]` before deriving wiki content; and
5. add a Strict Invariant only when the claim is legitimately current and source-consistent.

Creating a `current` document does not automatically make every statement in it an entity invariant.

---

## New `proposed` Document

Invoke `$wiki-sync`.

The document may contain meaningful future direction eligible for `Planned`.

`$wiki-sync` determines:

* whether the proposed direction belongs on an entity page;
* which active entity owns the concern; and
* whether a new boundary question needs to be surfaced.

Creating a `proposed` document does not automatically require a Planned entry if the content contains no durable entity-level architectural direction.

---

## New `research`, `reference`, or `process` Document

Do not invoke `$wiki-sync` solely because the document was created.

These classes do not independently establish:

* `Strict Invariants`; or
* `Planned` content.

A genuinely cross-cutting `platform-` research or reference document may still require its discovery link in `wiki/index.md` according to `wiki/_schema.md`.

That index maintenance is structural discovery metadata, not entity-claim synchronization.

---

# 8. Handle Cross-Cutting Index Discovery

If the new document is genuinely cross-cutting, uses a `platform-` filename, and belongs to an index-listed cross-cutting class defined by `wiki/_schema.md`:

* add the appropriate discovery link to `wiki/index.md`.

Do not add entity-specific research/reference documents to the index merely because they exist.

Do not turn `wiki/index.md` into a complete document inventory.

---

# 9. Report

Report:

* created path;
* document classification;
* primary entity or `platform` attribution where applicable;
* whether `$wiki-sync` ran;
* whether `wiki/index.md` discovery metadata changed;
* any derived wiki claim added or surfaced for review;
* any `[source-conflict]` or unresolved entity-boundary question.

Example:

```text
Created:
docs/proposed/persistence-postgres-cutover.md

Classification:
proposed

Primary entity:
persistence

$wiki-sync:
Added proposed direction to persistence → Planned.

Source conflicts:
none
```

For a non-authoritative document:

```text
Created:
docs/research/persistence-vector-store-evaluation.md

Classification:
research

Primary entity:
persistence

$wiki-sync:
not required
```

---

# Commit Ownership

`$to-doc` does not require a standalone commit when invoked inside another workflow that owns the overall change.

When the creation produces related Living Entity Wiki changes:

* the new document;
* any derived wiki mutation;
* any `wiki/index.md` structural update; and
* the corresponding semantic `wiki/log.md` entry

must land consistently with the calling workflow's commit strategy.

Do not create a separate commit merely because `$to-doc` or `$wiki-sync` ran.

---

# Out of Scope

`$to-doc` does not:

* classify, reclassify, relocate, or rename an existing document — use `$classify-doc`;
* create or manage ADRs — use `$to-adr-doc`;
* own document classification or naming policy — see `wiki/_schema.md`;
* decide entity topology — use `$wiki-sync` with `wiki/_schema.md`;
* resolve `[source-conflict]`;
* maintain `linked_docs`;
* add in-file classification metadata;
* perform a full wiki audit — use `$wiki-lint`.

Its job is to ensure a **new non-ADR document begins life in the correct structural location**, with the correct name, and with the appropriate Living Entity Wiki follow-through.
