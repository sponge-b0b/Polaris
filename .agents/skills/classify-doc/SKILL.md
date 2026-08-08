---
name: classify-doc
description: Classify, relocate, and rename an existing document under docs/ that was created without doc_class placement — typically in response to /wiki-lint's [unclassified-doc] finding, or a doc discovered sitting outside the recognized folder scheme. Updates any existing citations to the file's old path. Use for existing files only; for new documents, use /to-doc instead.
compatibility: product=codex product=claude-code system=git network=none
---

# Classify Doc

This skill handles a document that already exists but was never
placed under the folder-based classification scheme — most commonly
surfaced by `/wiki-lint`'s `[unclassified-doc]` check, but also usable
directly on any file you find sitting loose in `docs/` or in an
unrecognized subfolder.

This is distinct from `/to-doc`, which places brand-new content.
`/to-doc`'s classification and naming logic (steps 1-2 below) is
reused here — but a new file has no history and no existing
references to it, while an existing file may already be linked from
other documents or cited in an entity's `linked_docs`. That difference
is why this is a separate skill, not a mode of `/to-doc`.

## 1. Determine the folder

Apply "Classifying a document" in `wiki/_schema.md` (six rules,
first-match-wins) to determine the destination folder. Do not
re-derive or restate those rules here.

One exception check specific to *existing* files, not covered by
`/to-doc`: if the file currently sits under a directory listed in
"External scaffold directories" in `wiki/_schema.md`, stop — do not
reclassify or move it. That directory is owned by its listed skill; if
a file under it is flagged as unclassified, the registry itself is
probably out of date, not the file. Report this rather than acting on
it.

When the call between `docs/current/` and `docs/proposed/` is
genuinely unclear, apply the fail-safe default in "Citation rule" in
`wiki/_schema.md`.

## 2. Determine the filename

Apply "Document naming convention" (including the `docs/process/`
exemption) and, where no single entity applies, "Cross-cutting
documents" in `wiki/_schema.md` to determine the filename. Do not
restate those rules here.

Preserve the document's existing slug where reasonable rather than
inventing a new one — this step is about adding the correct prefix and
folder, not rewriting a working name from scratch.

## 3. Check for and update inbound references

Before moving the file, check whether anything already points to its
current path:

- `grep` other files under `docs/` for the current filename or
  relative path.
- Check every entity's `linked_docs` in `wiki/entities/` (if
  `wiki/entities/` exists) for a citation matching the current path.
- Check `wiki/index.md` for a direct link, if the file was already
  linked there as `reference`/`research`/cross-cutting content.
- Check `README.md`.

If any are found, note them — they'll need updating to the new path
as part of the same operation, not left dangling. A citation left
pointing at a pre-move path is a broken reference `/wiki-lint`'s
existing checks may not catch, since none of its current checks are
scoped to detecting a moved (rather than edited or newly-stale)
`docs/` file.

## 4. Move and update

`git mv` (or equivalent) the file from its current path to
`docs/<folder>/<filename>` determined in steps 1-2, preserving
history. Update every reference found in step 3 to the new path in
the same pass — do not leave any of them pointing at the old location.

Do not insert any classification line or field into the file's
content — classification is derived entirely from folder location.

## 5. Living Entity Wiki sync

If `wiki/entities/` exists, and the file landed in `docs/current/` or
`docs/proposed/`:

- If step 3 found an existing citation to this file in some entity's
  `linked_docs`, that citation's path was already corrected in step 4
  — no further wiki-sync trigger needed for it specifically, since the
  underlying invariant or Planned entry is unchanged, only its
  citation path is.
- If no prior citation existed, invoke `/wiki-sync`'s docs-change
  trigger, "New or promoted doc" branch, the same as `/to-doc` step 4
  — this file is new to the wiki's awareness even though it isn't new
  to the filesystem.

A document landing in `docs/reference/`, `docs/process/`, or
`docs/research/` never triggers this, same as `/to-doc`.

## 6. Report

State the old path, the new path, every reference updated, and
whether a `/wiki-sync` trigger fired.
