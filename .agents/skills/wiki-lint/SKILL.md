---
name: wiki-lint
description: Audits the Living Entity Wiki (wiki/entities/) as a whole for contradictions, drift against code and docs, stale or invalid citations, and structural hygiene issues. Run on-demand or at the end of a session that touched multiple entities. Distinct from /wiki-sync, which maintains one entity at a time in the context of a single change; wiki-lint audits the full wiki independently of any specific change.
compatibility: product=codex product=claude-code system=git network=none
---

# Wiki Lint

## When this runs

Run on-demand, or recommended at the end of any session that touched
multiple entities. Never automatic on trivial edits.

Also serves as the backstop for missed `/wiki-sync` invocations — a
source-code or docs change that happened without `/wiki-sync` running
(an ad hoc edit, a skill that didn't call it) has no other detection
path, so `[code-drift]` and `[doc-drift]` findings should be read as
"either genuine drift or a skipped sync" rather than assumed to be
one or the other.

## Checks

- Contradictions between entity pages.
- `[code-drift]` — invariant vs. code, verified against
  codebase-memory-mcp/codegraph, not inferred. Means the wiki failed to
  track a real code change — treat as the higher-severity category.
  Entities with `implementation: pending` are exempt from this check
  by definition — there's no code yet to verify against.
- `[doc-drift]` — invariant vs. the current text of its cited source
  in `docs/` (relevant for `doc_class: current` docs, which are edited
  over time). Often just routine lag behind a deliberate human edit —
  lower severity by default, but still surfaced, not suppressed.
- `[stale-citation]` — an entity invariant cites an ADR whose own
  `status` field has changed away from `accepted` since the citation
  was made — flipped to `deprecated`, `superseded by ADR-NNNN`, or, in
  an edge case, `rejected`. Cheap and deterministic: a YAML
  frontmatter field read, not a content diff.
- `[invalid-citation]` — an entity invariant cites a doc whose
  `doc_class` is not `accepted` or `current`. Only those two classes
  may ever back an invariant; anything else (`proposed`, `research`,
  `process`, `reference`, `rejected`, `deprecated`, `superseded`)
  reaching a citation is a `/wiki-sync` mistake, not a drift condition.
- `[broken-doc-citation]` — an entity's `linked_docs` cites a path
  under `docs/` that no longer resolves to a file. This is not a
  separate pass: resolving the cited path is already the first step
  of `[invalid-citation]`, `[stale-citation]`, and `[doc-drift]`, each
  of which needs to open the cited file before it can check its
  `doc_class`, its ADR `status`, or its content. When that resolution
  fails, report `[broken-doc-citation]` for that citation and skip the
  other three checks for it — there's nothing left to check once the
  file itself can't be found. Distinct from `[doc-drift]` (the file
  exists but its content changed) and `[invalid-citation]` (the file
  exists but its `doc_class` doesn't permit citation) — this is
  specifically the file having moved or been deleted outside of
  `/classify-doc`'s own citation-update step, or `/wiki-sync`'s
  equivalent handling. A dead citation here is not evidence the
  underlying invariant is wrong; it's evidence the citation didn't
  follow the file. Resolving it (updating the path if the file moved
  elsewhere, or reviewing the invariant if the file was genuinely
  removed) is a human call, same as every other citation finding.
- `[unclassified-doc]` — any file under `docs/` that isn't classifiable
  by any of: an ADR `status` field (`docs/adr/`), folder location
  (`docs/current/`, `docs/proposed/`, `docs/reference/`,
  `docs/process/`, `docs/research/`), or the "External scaffold
  directories" registry in `wiki/_schema.md`. In practice, this means
  a file sitting loose in `docs/` root or in an unrecognized
  subfolder — not a missing in-file field, since classification is no
  longer stored as one. Distinct from the checks above: this is a
  `docs/` hygiene check independent of any entity, catching a
  misplaced file before it can produce an `[invalid-citation]` or
  reach an entity page unclassified.
- `[stale-question]` — an Open Questions entry that has sat unresolved
  well past the entity's own pace of activity (a reasonable default is
  60+ days with no related change to the entity, but this is a
  judgment call, not a hard rule — tune it to the project's actual
  pace). Not evidence the question doesn't matter; evidence it's been
  sitting long enough that it's worth a deliberate decision — resolve
  it, or explicitly confirm it's still open — rather than continuing
  to accumulate silently. This is what gives the "what needs to
  change" side of the self-improvement cycle an actual detection path,
  rather than relying on someone remembering to revisit it.
- Orphan entities, missing entities.
- Broken or missing reciprocal links.
- Stale frontmatter (`last_updated` far older than the last substantive
  change to an entity's anchor files). Includes the reverse case: an
  `implementation: pending` entity whose anchor paths now resolve to
  real code via codegraph — a sign it should have been promoted to
  `implementation: complete` and was missed.

Every drift or citation finding is reported with its `[code-drift]`,
`[doc-drift]`, `[stale-citation]`, `[invalid-citation]`,
`[unclassified-doc]`, `[stale-question]`, or `[broken-doc-citation]`
prefix so severity is legible without reading each line.

## Resolution rules

Lint flags; it does not silently resolve judgment calls. Mechanical
issues (dead links, missing reciprocal-link stubs) may be auto-fixed.
A stale invariant or citation is not evidence the invariant is wrong;
it's evidence the wiki and its source disagree. Resolving that is a
human call.

## Logging

Every lint run gets one line in `wiki/log.md`, in this exact format,
so a clean run — which produces no git diff and would otherwise be
invisible in history — still leaves a trace:

    ## [YYYY-MM-DD] lint | N issues found ([code-drift]: n, [doc-drift]: n, [stale-citation]: n, [invalid-citation]: n, [unclassified-doc]: n, [stale-question]: n, [broken-doc-citation]: n, [structural]: n)

Orphan/missing entities, broken/missing reciprocal links, and stale
frontmatter (including the pending-but-now-implemented case above)
are counted together under `[structural]` — grouped as general wiki
hygiene rather than given individual severity tags, since that's the
distinction that actually matters for triage. `[unclassified-doc]`
and `[stale-question]` each stay their own category rather than
folding into `[structural]`, since one is a check on `docs/` itself
and the other is central to the self-improvement loop this wiki
supports — both deserve visibility in the summary line rather than
being buried. Omit any category with a zero count from the
parenthetical. A fully clean run is written as:

    ## [2026-08-04] lint | 0 issues found

Commit the `wiki/log.md` entry — together with any mechanical
auto-fixes applied during this run (dead links, missing
reciprocal-link stubs) — as one atomic operation, sharing a label,
same pairing discipline as `/wiki-sync`:

    commit: wiki(lint): <date> — N issues found
    log.md: ## [YYYY-MM-DD] lint | N issues found (...)

Never leave the log line uncommitted. On a fully clean run with no
other changes, the log.md edit itself is still committed on its own —
the commit is what makes the clean run visible in history at all.

## Out of scope

- **Bootstrap** and per-change entity/docs maintenance are handled by
  `/wiki-sync`, not here. `/wiki-lint` audits the wiki as a whole,
  independent of any specific change; it does not create or update
  entity pages itself beyond the mechanical auto-fixes listed above.
- **Cross-entity pattern synthesis** (recurring themes across Rejected
  Approaches or Open Questions entries) is handled by the separate
  `/wiki-synthesize` skill, not attempted here.
- **New-category introduction** is a creation-time compliance check,
  not an ongoing wiki-health one — it's enforced by `/wiki-sync`'s
  "No matching entity" step 2 at the moment a category is introduced,
  not re-litigated here. A category used by exactly one entity is a
  legitimate, permanent shape, not a signal of anything on its own.
