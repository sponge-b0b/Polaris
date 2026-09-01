---
name: to-doc
description: Create new Living Entity Wiki-classified non-ADR documents under docs/ using the classification, naming, placement, and Wiki rules defined by the repository schema.
compatibility: product=codex product=claude-code network=none
---

# To Doc

`$to-doc` owns creation-time placement and naming of **new Living Entity Wiki-classified non-ADR documents** under `docs/`.

Its responsibility is:

```text
content
  ↓
classify
  ↓
name
  ↓
write
  ↓
sync when required
```

Classification, naming, and the `docs/.wikiignore` exclusion boundary are owned by `wiki/_schema.md`.

For an existing classified document, use `$classify-doc`.

For an ADR, use `$to-adr-doc`.

## 1. Confirm Scope

Use this skill only for a **new non-ADR document inside the Living Entity Wiki document universe**.

* If the content warrants an ADR, use `$to-adr-doc`.
* If the document already exists, use `$classify-doc`.
* If the requested path is matched by `docs/.wikiignore`, it is outside this skill's ownership; use the workflow or repository owner responsible for that documentation tree.
* Do not recreate an existing document merely to bypass reclassification or reference migration.

## 2. Classify the Document

Apply the non-ADR classification rules in `wiki/_schema.md`.

Possible project-owned classes are:

```text
current
proposed
research
reference
process
```

Classification comes from folder placement.

Do not add:

```text
doc_class:
Doc-Class:
```

to the document.

If `current` vs `proposed` is genuinely unclear, follow the schema fail-safe and use `proposed`.

## 3. Respect the Wiki Exclusion Boundary

Read `docs/.wikiignore` when present and apply only the exclusion grammar defined by `wiki/_schema.md`.

If the requested path is explicitly excluded:

* do not classify it;
* do not apply Living Entity Wiki naming rules;
* do not invoke `$wiki-sync` solely because it was created;
* route creation to the workflow or repository owner responsible for that documentation tree.

Do not infer exclusions for unfamiliar directories and do not invent new `.wikiignore` entries merely to make a requested path legal.

## 4. Name the Document

Apply the naming and cross-cutting-document rules in `wiki/_schema.md`.

When an active `wiki/index.md` exists:

* use the owning Entity ID when the document primarily belongs to one entity;
* use `platform-` only for genuinely cross-cutting documents;
* do not entity/platform-prefix `process` documents.

Use `wiki/index.md` as the source of active Entity IDs.

Do not invent new IDs.

### Before Wiki Bootstrap

If no active entity registry exists yet, use:

```text
<slug>.md
```

Do not invent entity prefixes before bootstrap.

Later normalization belongs to `$classify-doc`.

## 5. Place and Write the Document

Use the canonical folder for its class:

```text
current   → docs/current/
proposed  → docs/proposed/
research  → docs/research/
reference → docs/reference/
process   → docs/process/
```

Create only the required directory if missing.

Write the file directly at its canonical destination.

Do not:

* create it temporarily at the repository root;
* leave it loose under `docs/`;
* duplicate classification or entity-registry metadata inside it.

## 6. Living Entity Wiki Follow-Through

If the Living Entity Wiki has not been bootstrapped, no synchronization is required.

Otherwise:

* new `current` documents → invoke `$wiki-sync`;
* new `proposed` documents → invoke `$wiki-sync`;
* new `research`, `reference`, or `process` documents → do not invoke `$wiki-sync` solely because they were created.

Let `$wiki-sync` determine whether a `current` or `proposed` document contributes durable entity knowledge or exposes `[source-conflict]`.

Do not duplicate that evaluation here.

For genuinely cross-cutting `platform-` documents, maintain any required discovery entry in `wiki/index.md` according to `wiki/_schema.md`.

Do not turn the index into a complete document inventory.

## 7. Commit Ownership

`$to-doc` does not require its own commit when called inside a parent workflow.

If document creation also causes wiki/index changes, keep those changes consistent with the caller's commit strategy and `$wiki-sync`'s semantic logging rules.

Do not create a separate commit merely because `$to-doc` or `$wiki-sync` ran.

## 8. Report

Report:

* created path;
* classification;
* primary entity or `platform` attribution where applicable;
* whether `$wiki-sync` ran;
* whether `wiki/index.md` changed;
* any `[source-conflict]` or unresolved entity-boundary issue.

## Out of Scope

`$to-doc` does not:

* create or manage documentation matched by `docs/.wikiignore`;
* modify or reclassify existing documents — use `$classify-doc`;
* create or manage ADRs — use `$to-adr-doc`;
* own classification, naming, or exclusion policy — see `wiki/_schema.md`;
* decide entity topology — use `$wiki-sync`;
* resolve `[source-conflict]`;
* maintain `linked_docs`;
* perform a full wiki audit — use the `$wiki-lint` skill.

Its job is to ensure a **new classified non-ADR document starts in the correct place, with the correct name, and the correct lifecycle follow-through**.
