---
name: to-doc
description: Create a new document in docs/ outside docs/adr/ — determines the correct doc_class (folder placement), the entity-prefixed or platform- filename, and triggers the Living Entity Wiki when relevant. Use whenever a new architecture, reference, process, or research document is being written. For docs/adr/, use /to-adr-doc instead.
compatibility: product=codex product=claude-code network=none
---

# To Doc

Every file under `docs/`, outside `docs/adr/`, is classified by folder
location — no in-file classification field is used. This skill
determines that folder, the filename, and whether the Living Entity
Wiki needs to know about the new file.

This skill is for **creating new content**. If a file already exists
and needs to be classified, relocated, or renamed after the fact, use
`/classify-doc` instead — that's a distinct operation with its own
judgment-recovery concerns, not a mode of this skill.

## 1. Determine the folder

Apply "Classifying a document" in `wiki/_schema.md` (six rules,
first-match-wins) to determine the destination folder. Do not
re-derive or restate those rules here — `wiki/_schema.md` is the
single source of truth for them.

When the call between `docs/current/` and `docs/proposed/` is
genuinely unclear, apply the fail-safe default in "Citation rule" in
`wiki/_schema.md`.

## 2. Determine the filename

Apply "Document naming convention" (including the `docs/process/`
exemption) and, where no single entity applies, "Cross-cutting
documents" in `wiki/_schema.md` to determine the filename. Do not
restate those rules here.

If `wiki/entities/` does not exist, use `<slug>.md` with no prefix —
the naming convention only applies once entities exist to prefix
against.

## 3. Write the file

Create the file at `docs/<folder>/<filename>` determined above. Do
not insert any classification line or field into the file's
content — classification is derived entirely from folder location.

## 4. Living Entity Wiki sync

If `wiki/entities/` exists in this repository, and the new document
was placed in `docs/current/` or `docs/proposed/` (the only two
classes that can ever back an entity invariant or Planned entry),
invoke the `/wiki-sync` skill's docs-change trigger, "New or promoted
doc" branch, immediately after writing the file. See `/wiki-sync`'s
"Docs-change trigger" section for the full branch logic.

A document placed in `docs/reference/`, `docs/process/`, or
`docs/research/` never triggers this — none of those classes can back
an invariant or Planned entry.

If `wiki/entities/` does not exist, this does not apply.
