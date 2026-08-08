---
name: classify-doc
description: Classify, reclassify, relocate, and rename an existing non-ADR document under docs/. Determines the document's correct structural class and filename, updates inbound path references atomically, and invokes wiki-sync when the document's authority change affects derived Living Entity Wiki claims. Use for existing non-ADR documents only; for new documents, use to-doc.
compatibility: product=codex product=claude-code system=git network=none
---

# Classify Doc

`$classify-doc` owns structural classification changes for **existing non-ADR documents** under `docs/`.

Use it when an existing document:

* was never classified;
* sits loose in `docs/` or an unrecognized subdirectory;
* belongs in a different recognized document class;
* needs relocation because its purpose changed;
* needs its entity or `platform-` prefix corrected; or
* is surfaced by `$wiki-lint` as `[unclassified-doc]`.

This includes both:

```text
unclassified → classified
```

and later transitions such as:

```text
research → proposed
proposed → current
current → proposed
current → reference
```

For a newly created document, use `$to-doc`.

For ADRs under `docs/adr/`, use `$to-adr-doc`; ADR lifecycle is status-based and is not handled here.

---

# 1. Confirm Scope

This skill applies only to an **existing non-ADR document**.

If the file is under:

```text
docs/adr/
```

stop and use `$to-adr-doc`.

If the file does not yet exist and new content is being created, stop and use `$to-doc`.

---

# 2. Check External Scaffold Ownership

Before classifying or moving the file, check the External Scaffold Directories registry in `wiki/_schema.md`.

If the file belongs to a registered external scaffold directory:

* do not move it;
* do not rename it;
* do not apply this project's normal prefix rules;
* treat it according to the registry's declared class.

If the registry appears outdated or incorrect, surface that problem rather than modifying externally owned paths.

An unfamiliar directory is not automatically externally owned.

---

# 3. Determine the Current Classification

Determine the document's current structural class from its location according to `wiki/_schema.md`.

Possible current states include:

```text
current
proposed
research
reference
process
unclassified
```

Do not inspect or create an in-file `doc_class` or `Doc-Class:` field.

Non-ADR classification is derived entirely from folder placement.

The current folder describes the document's **current classification**.

It does not determine where the document should remain if its purpose has changed.

---

# 4. Determine the Target Classification

Apply **Determining a Non-ADR Document's Target Class** from `wiki/_schema.md`.

Do not duplicate those rules here.

Classify the document according to its present content and purpose, not merely its existing path.

When the distinction between `current` and `proposed` is genuinely unclear, apply the schema's fail-safe rule:

```text
default to proposed
```

For other unresolved classification ambiguity, surface the uncertainty rather than inventing a confident classification unsupported by the document.

Record:

```text
current class: <class | unclassified>
target class: <class>
```

If the target class equals the current class, the file may still require a filename correction. Continue to the naming check.

---

# 5. Determine the Correct Filename

Apply the Document Naming Convention and Cross-Cutting Documents rules in `wiki/_schema.md`.

Do not restate those rules here.

In summary, determine whether the document:

* primarily belongs to one active entity;
* genuinely requires the `platform-` prefix; or
* is a `process` document exempt from entity/platform prefixing.

Use `wiki/index.md` as the authoritative active-entity registry.

Preserve the existing descriptive slug where reasonable.

This operation should normally correct classification, attribution, or placement — not rewrite an already useful filename without cause.

---

# 6. Determine the Destination

The destination is:

```text
docs/<target-class>/<correct-filename>
```

except for externally scaffolded files, which were already excluded above.

If the required target directory does not exist, create only that directory.

Do not eagerly create all possible document-class folders.

---

# 7. Find Inbound Path References

Before moving or renaming the document, locate references to its current path.

Check at minimum:

* inline `source:` citations under `wiki/entities/`;
* direct links in `wiki/index.md`;
* references in other files under `docs/`;
* `README.md`;
* project instructions or skills that explicitly cite the document path where relevant.

Use exact path/reference discovery for this step.

Do not recreate a `linked_docs` registry.

Inline `source:` citations are the sole entity-to-document relationship representation.

Record every reference that must move with the document.

---

# 8. Identify the Authority Transition

Before changing the path, determine whether the classification transition changes what the document is allowed to support in the entity wiki.

Relevant transitions include:

## No authority change

Examples:

```text
current → current
proposed → proposed
research → research
reference → reference
process → process
```

A path/name correction alone does not change the document's semantic authority.

Existing citations may still need path updates.

---

## Newly eligible for Planned

Examples:

```text
unclassified → proposed
research → proposed
reference → proposed
process → proposed
```

The document may now support `Planned` content.

---

## Newly eligible for Strict Invariants

Examples:

```text
unclassified → current
research → current
reference → current
process → current
```

The document now claims to describe current reality and may support `Strict Invariants`, subject to `$wiki-sync` source-consistency and implementation-evidence checks.

---

## Proposed to current

```text
proposed → current
```

This does **not** automatically convert existing `Planned` claims into `Strict Invariants`.

The document now claims to describe current reality.

`$wiki-sync` must first evaluate:

* applicable accepted ADRs;
* relevant implementation evidence; and
* `[source-conflict]`.

Only legitimately current claims are promoted.

---

## Current to proposed

```text
current → proposed
```

The document can no longer independently support an active `Strict Invariant`.

`$wiki-sync` must re-evaluate every affected invariant:

* retain it only if another valid active source independently supports it;
* move appropriate future-state content to `Planned`;
* otherwise remove the unsupported active claim.

---

## Losing active wiki authority

Examples:

```text
current → research
current → reference
current → process

proposed → research
proposed → reference
proposed → process
```

The document can no longer perform its previous active wiki role.

`$wiki-sync` must re-evaluate any derived claims sourced from it.

---

# 9. Move and Rename Atomically

Move the file using:

```text
git mv
```

or an equivalent history-preserving operation.

Move from the current path to the destination determined above.

In the same operation:

* update every inbound path reference found earlier;
* update inline entity `source:` citations to the new path;
* update any direct `wiki/index.md` platform-document link;
* update other document links;
* update repository instructions that explicitly depend on the path.

Do not leave known references pointing at the old location.

Do not insert any classification metadata into the document body.

---

# 10. Invoke `$wiki-sync`

If `wiki/entities/` does not exist, skip Living Entity Wiki synchronization.

Otherwise, invoke `$wiki-sync` whenever:

* classification authority changed;
* an existing derived claim cites the moved document;
* the document became newly eligible to support `Planned` or `Strict Invariants`; or
* substantive content changes were made as part of the same operation.

Pass the relevant transition context:

```text
<old-class | unclassified> → <new-class>
```

and the old/new document paths.

---

## Path-Only Move With Existing Derived Claims

If classification did not change and only the path/name changed:

* update the inline citation path atomically;
* the underlying derived claim does not need semantic reevaluation solely because of the move.

If other evidence suggests the claim itself may now be stale, invoke the normal `$wiki-sync` source reevaluation rather than assuming path-only equivalence.

---

## Newly Eligible Document With No Existing Citation

If the document becomes `current` or `proposed` and no entity currently cites it, `$wiki-sync` must still inspect whether its content introduces:

* a current architectural constraint; or
* meaningful Planned direction.

A document does not need an existing citation before newly authoritative content can enter the wiki.

---

## Transition Away From Active Authority

If the document leaves `current` or `proposed`, `$wiki-sync` must search for affected derived claims even if all path references were mechanically updated.

Changing the citation path is not enough when the document's authority changed.

---

# 11. Handle Source Conflicts

Reclassification can expose disagreement between:

* the document;
* accepted ADRs;
* implementation evidence.

If `$wiki-sync` identifies a material disagreement, surface:

```text
[source-conflict]
```

Do not:

* alter the document to match another source;
* alter an ADR;
* force the entity wiki to follow the newly classified document; or
* choose which source is correct.

Finish the safe mechanical relocation/reference update if appropriate, but leave judgment-bearing derived wiki changes unresolved until the source conflict is resolved.

---

# 12. Preserve Historical ADR Paths

This skill does not rename or relocate ADRs.

If an entity rename or other topology change suggests that historical ADR filenames no longer match current entity terminology, leave those historical filenames unchanged unless an explicit ADR/document migration operation separately requires otherwise.

Historical provenance is more important than forcing every old filename to mirror current topology.

---

# 13. Report

Report:

* old path;
* new path;
* current classification;
* target classification;
* whether classification changed;
* every inbound reference updated;
* whether `$wiki-sync` ran;
* any wiki claims added, updated, removed, or left for human review;
* any `[source-conflict]` or other unresolved condition.

Example:

```text
Classified document:
docs/persistence-plan.md
→ docs/proposed/persistence-postgres-migration.md

Transition:
unclassified → proposed

References updated:
- README.md

$wiki-sync:
Added Planned entry to persistence entity.

Source conflicts:
none
```

---

# Commit Ownership

`$classify-doc` does not require a standalone commit when invoked inside another workflow that owns the overall change.

Whether committed standalone or through a calling skill:

* the document move;
* path-reference updates; and
* any resulting `$wiki-sync` mutation and semantic `wiki/log.md` entry

must land consistently and atomically enough that no committed state contains knowingly broken paths or half-applied wiki authority transitions.

---

# Out of Scope

`$classify-doc` does not:

* create brand-new documents — use `$to-doc`;
* manage ADR lifecycle or ADR status — use `$to-adr-doc`;
* decide new entity topology — use `$wiki-sync` plus `wiki/_schema.md`;
* resolve `[source-conflict]`;
* rewrite document content merely to justify a preferred classification;
* maintain `linked_docs`;
* add in-file classification fields;
* perform a full wiki audit — use `$wiki-lint`.

Its responsibility is the structural classification lifecycle of an **existing non-ADR document** and the safe propagation of that change into references and derived wiki knowledge.
