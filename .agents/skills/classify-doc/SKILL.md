---
name: classify-doc
description: Classify, reclassify, relocate, or rename an existing non-ADR document under docs/, updating inbound references and Living Entity Wiki consequences when required.
compatibility: product=codex product=claude-code system=git network=none
---

# Classify Doc

`$classify-doc` owns the structural lifecycle of **existing non-ADR documents** under `docs/`.

Use it when a document:

* is unclassified or misplaced;
* belongs in a different document class;
* needs relocation because its purpose changed;
* needs its entity or `platform-` prefix corrected;
* is surfaced by `$wiki-lint` as structurally misclassified.

For a new document, use `$to-doc`.

For an ADR, use `$to-adr-doc`.

## 1. Confirm Scope

The file must already exist and must not be an ADR.

If it is under `docs/adr/`, use `$to-adr-doc`.

If new content is being created, use `$to-doc`.

## 2. Respect External Scaffold Ownership

Check the External Scaffold Directories registry in `wiki/_schema.md`.

If another skill owns the path:

* do not move or rename it;
* do not apply normal project prefix rules;
* follow the owning workflow.

If the registry appears wrong, surface that rather than altering the externally owned path.

## 3. Determine Current and Target Classification

Derive the current class from the document's location.

Apply the target-class rules in `wiki/_schema.md` to the document's **current content and purpose**, not merely its existing folder.

Possible project-owned classes are:

```text id="gf2lwx"
current
proposed
research
reference
process
```

An existing loose or unrecognized document may be `unclassified`.

Do not use or introduce:

```text id="rw6zdz"
doc_class:
Doc-Class:
```

If `current` vs `proposed` is genuinely ambiguous, follow the schema fail-safe and use `proposed`.

Record:

```text id="8p8i8m"
current: <class | unclassified>
target:  <class>
```

## 4. Determine the Correct Filename and Destination

Apply the naming and cross-cutting-document rules in `wiki/_schema.md`.

When the active entity registry exists:

* use the primary Entity ID when the document belongs to one entity;
* use `platform-` only for genuinely cross-cutting documents;
* do not entity/platform-prefix `process` documents.

Use `wiki/index.md` for active Entity IDs. Do not invent one.

Preserve the existing descriptive slug where reasonable.

The destination is:

```text id="2hmjqt"
docs/<target-class>/<correct-filename>
```

Create only the required target directory if missing.

If classification and filename are already correct, no move is required.

## 5. Find Inbound References

Before moving or renaming the file, find references to its existing path.

Check at minimum:

* inline `source:` citations under `wiki/entities/`;
* cross-cutting links in `wiki/index.md`;
* other documents under `docs/`;
* `README.md`;
* repository instructions, skills, scripts, or configuration that explicitly reference the path.

Use exact path discovery.

Do not recreate `linked_docs`; inline `source:` citations remain the entity-document relationship mechanism.

## 6. Move Atomically

Use `git mv` or an equivalent history-preserving operation.

In the same change, update every known inbound reference to the new path.

This includes applicable:

* inline `source:` citations;
* `wiki/index.md` links;
* documentation links;
* repository instructions.

After the move, search for the old path again and resolve any remaining valid references.

Do not add classification metadata to the document body.

## 7. Apply Living Entity Wiki Follow-Through

If the Living Entity Wiki has not been bootstrapped, skip this step.

Otherwise invoke `$wiki-sync` when:

* the document's classification authority changed;
* an entity claim cites the moved document;
* the document became `current` or `proposed`;
* the document left `current` or `proposed`;
* substantive content changed as part of the operation.

Pass the old/new class and old/new path.

Let `$wiki-sync` determine the semantic consequence.

In particular, do not locally assume that:

```text id="fh23jr"
proposed → current
```

automatically means:

```text id="13lb23"
Planned → Strict Invariant
```

or that leaving `current` automatically deletes an invariant.

Those decisions require `$wiki-sync`'s normal authority, implementation-evidence, and `[source-conflict]` evaluation.

### Path-only move

If classification did not change and the operation is purely structural:

* update citations and references mechanically;
* do not semantically rewrite wiki claims solely because their source path changed.

Invoke full source reevaluation only if there is separate evidence that the claim itself may be stale.

## 8. Source Conflicts

If `$wiki-sync` surfaces `[source-conflict]`, do not resolve it by:

* rewriting the document;
* altering an ADR;
* forcing the entity wiki to follow the reclassified document;
* choosing one authority unilaterally.

Complete safe mechanical path updates where appropriate, but leave judgment-bearing wiki changes unresolved until the conflict is resolved.

## 9. Commit Ownership

`$classify-doc` does not require a standalone commit when called by a parent workflow.

The document move, inbound-reference updates, and any resulting wiki mutation must land consistently with the caller's commit strategy.

If `$wiki-sync` makes a substantive wiki mutation, its semantic `wiki/log.md` entry must land with that mutation.

Do not create a commit merely because `$classify-doc` or `$wiki-sync` ran.

## 10. Report

Report:

* old path;
* new path;
* current classification;
* target classification;
* inbound references updated;
* whether `$wiki-sync` ran;
* resulting wiki changes or unresolved review;
* any `[source-conflict]`.

## Out of Scope

`$classify-doc` does not:

* create new documents — use `$to-doc`;
* manage ADR lifecycle — use `$to-adr-doc`;
* own classification or naming policy — see `wiki/_schema.md`;
* decide entity topology — use `$wiki-sync`;
* resolve `[source-conflict]`;
* rewrite content merely to justify a preferred classification;
* maintain `linked_docs`;
* perform a full wiki audit — use `$wiki-lint`.

Its responsibility is to put an **existing non-ADR document in the correct structural location without breaking references or derived architectural knowledge**.
