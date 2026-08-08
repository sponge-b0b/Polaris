# wiki/_schema.md

## Document classification

Every file under `docs/` has a classification, derived structurally
rather than independently asserted:

- **`docs/adr/`** — via the existing `status` YAML frontmatter field
  (see `/to-adr-doc`). No separate field; `doc_class` is derived from
  it, never stored independently. ADRs keep a flat, sequentially-
  numbered directory regardless of status — status is a lifecycle
  stage on a persistent document, not a category, so it stays a
  field, not a folder.
- **Everywhere else under `docs/`** — via folder location. A file's
  presence in `docs/current/`, `docs/proposed/`, `docs/reference/`,
  `docs/process/`, or `docs/research/` *is* its classification; no
  in-file field is needed or used. This is a category, not a
  lifecycle stage, so it's naturally suited to filing rather than a
  mutable field.

Both mechanisms exist to satisfy the same underlying rule:
classification must be structurally derived and cheap to verify,
never stored as a second, independently-asserted fact that can
silently drift from reality. They differ in mechanism because they
classify different kinds of things — see above — not because one is
more rigorous than the other.

A file sitting outside `docs/adr/`, the five recognized folders, and
the "External scaffold directories" registry below has no derivable
classification. This is a `/wiki-lint` failure (`[unclassified-doc]`).
No exceptions list beyond that registry — every doc gets filed at
creation time, going forward, permanently.

Note: `wiki/entities/` pages use YAML frontmatter — see
`wiki/_template.md`. This is a third, distinct mechanism from either
of the above, used for the wiki's own generated content rather than
for classifying `docs/` at all.

### External scaffold directories

Some directories under `docs/` are owned and maintained by other,
third-party skills — not this project's own naming convention. Files
there are classified `process` and stay exactly where that skill put
them: no entity prefix, no rename, no move. This is a deliberate,
explicit registry, not a name-pattern rule — a folder is only exempt
if it's listed here, verified against what actually owns it.

| Directory | Owned by | Why exempt |
|---|---|---|
| `docs/agents/` | `/setup-matt-pocock-skills` | That skill hardcodes these exact paths in its write step and its `## Agent skills` block; renaming would break re-runs and produce silent duplicates. |

A directory *not* listed here, and not one of `docs/adr/`,
`docs/current/`, `docs/proposed/`, `docs/reference/`, `docs/process/`,
or `docs/research/`, is not automatically exempt — files inside it are
still flagged by `/wiki-lint`'s `[unclassified-doc]` check, same as a
file loose in `docs/` root. An unfamiliar folder name is not
sufficient evidence that it's externally owned; add it here explicitly
once you've confirmed what created it and why moving its contents
would be unsafe, the same reasoning applied to `docs/agents/` above.

| doc_class       | Meaning                                             | Wiki treatment                                                        |
|------------------|--------------------------------------------------------|-------------------------------------------------------------------------|
| accepted         | Settled ADR decision                                    | Feeds entity invariants, cited by ID                                    |
| current          | Describes the system as it exists today                 | Feeds entity content and invariants directly                            |
| proposed         | Forward-looking / exploratory, committed direction       | Never feeds invariants; entity "Planned" section only, explicitly marked not-yet-true |
| research         | Investigation that may or may not lead anywhere          | Never feeds invariants or "Planned"; linked from `wiki/index.md` only    |
| process          | How to work in the repo, not what the system is          | Never enters `wiki/entities/`                                            |
| reference        | Cross-cutting ledger/inventory spanning many entities     | Linked from `wiki/index.md`; never decomposed into one entity            |
| rejected         | An ADR whose proposed decision was not adopted            | Never cited as active authority                                          |
| deprecated       | An ADR whose decision is no longer recommended, without a formal successor | Never cited as active authority                              |
| superseded       | An ADR retired by a later ADR                             | Never cited as active authority                                          |

`accepted`, `proposed`, `rejected`, `deprecated`, and `superseded`
apply specifically to `docs/adr/` and are derived from the ADR's own
`status` field, not independently assigned.

### docs/adr/

`doc_class` mirrors the ADR's own `status` field directly: `proposed`
→ `proposed`, `accepted` → `accepted`, `rejected` → `rejected`,
`deprecated` → `deprecated`, `superseded by ADR-NNNN` → `superseded`.
Content is immutable once `accepted`; the `status` field itself is
the one recognized transition, changed directly by ADR authors as
part of normal ADR lifecycle — never by `/wiki-sync`.

### Citation rule

Only `doc_class: accepted` and `doc_class: current` documents may
back an entity invariant. Anything else reaching a citation
(`proposed`, `research`, `process`, `reference`, `rejected`,
`deprecated`, `superseded`) is a `/wiki-sync` mistake, flagged by
`/wiki-lint` as `[invalid-citation]` or `[stale-citation]`, not a
valid source.

**When placing or classifying a document, and the call between
`docs/current/` and `docs/proposed/` is genuinely unclear, default to
`docs/proposed/`.** This is the fail-safe direction: a mistaken
`proposed` placement only delays the doc from being citable. A
mistaken `current` placement is the dangerous direction — it lets
not-yet-true content get cited as settled fact by an entity page, and
nothing catches that until a `[doc-drift]` finding or manual review
surfaces it later.

### Document naming convention

Every file under `docs/` — ADR and non-ADR alike — is prefixed with
the entity it primarily concerns, so files sort by entity within
their folder without needing a subdirectory per entity. This
convention does not apply inside any "External scaffold directories"
entry (see above), which keep their owning skill's original
filenames, and does not apply to `docs/process/` — see below.

- **ADRs:** `000X-<primary-entity-id>-<slug>.md`, preserving the
  existing 4-digit sequential prefix. The number still governs
  ordering and "next number" lookups; the entity prefix is purely
  organizational.
- **Non-ADR docs (`docs/current/`, `docs/proposed/`, `docs/reference/`):**
  `<primary-entity-id>-<slug>.md`, inside whichever folder its
  classification dictates.
- **Optional sub-package qualifier:** `<primary-entity-id>-<qualifier>-<slug>.md`,
  used only when multiple docs cluster under the same entity on
  clearly distinct sub-topics such that the qualifier meaningfully
  aids scanning. When in doubt, omit it.

`<primary-entity-id>` is the entity (top-level or promoted) from
`wiki/index.md` that the document's content most concerns. If a
document genuinely doesn't have one — see "Cross-cutting documents"
below — use `platform-` instead of an entity ID.

**`docs/process/` is exempt from this entire convention.** A process
doc describes how to work in the repo, not which part of the system
it concerns — an entity or `platform-` prefix would be answering a
question the document was never asking. Use a direct, descriptive
`<topic-slug>.md` instead — e.g. `triage-labels.md`,
`issue-tracker.md` — naming the workflow area the document covers, not
a system component.

### Cross-cutting documents

Most `current/` and `proposed/` files are prefixed with the single
entity ID they concern. Some legitimately are not — a doc can span
multiple entities equally, describe a cross-cutting concern no single
entity owns (observability strategy, deployment topology), or simply
predate the entity decomposition. This is a deliberate, named
category, not a leftover bucket for anything ambiguous.

For these, use `platform-<slug>.md` in place of an entity-ID prefix,
inside the folder its content-type would normally dictate (e.g.
`docs/current/platform-observability-strategy.md`). The folder
assignment still follows the normal rules — only the entity
attribution is replaced with this reserved prefix.

A `platform-` doc may still be cited by any entity's `linked_docs` if
it backs a specific invariant there — cross-cutting doesn't mean
uncitable, just not owned by one entity. Whether or not any entity
cites it, list it directly in `wiki/index.md` alongside `reference`
and `research` docs, for the same reason those get that treatment:
content that doesn't decompose into a single entity still needs a
durable, discoverable home.

Reach for `platform-` only when a doc genuinely doesn't have a
primary entity — not as a shortcut to avoid the harder judgment call
of picking one. If a doc mostly concerns one entity with minor
relevance elsewhere, it should still get that entity's prefix.

### Classifying a document

These rules govern both the one-time retrofit of existing docs and
ongoing placement of newly created ones — the same content-based
heuristics apply either way. Apply in order, first match wins:

1. In `docs/adr/` → `doc_class` mirrors the ADR's own `status` field.
2. In `docs/research/` → `docs/research/`. (Path check, deterministic.)
3. In a directory listed under "External scaffold directories" above
   → `process`, in place — do not move or rename.
4. Structured as a table/ledger indexed by component, not prose about
   one subject → `docs/reference/`.
5. Addressed to a contributor about workflow, not the system →
   `docs/process/`.
6. Majority of claims in future/conditional voice ("will," "planned,"
   "target state") → `docs/proposed/`.
7. Otherwise → `docs/current/`.

**Retrofitting existing docs** (a one-time pass, not standing
judgment — see the doc classification/placement/renaming prompt)
touches many files at once and must be proposed as a table — old
path, proposed new path, one-line reasoning — for human review before
any file is moved or renamed.

**Creating a new doc** is a single file with low misclassification
risk — apply these rules and place it directly; no proposal step is
needed. See `/to-doc` for the creation-time procedure this feeds into.

## Entity boundaries

The initial top-level entity decomposition is decided once, up front,
by the entity boundary determination prompt — not re-derived here and
not a standing rule this section enforces going forward.

Once entities exist, the default source for "what entities exist and
what they cover" is `wiki/index.md` itself — already what `/wiki-sync`
step 1 reads. This section's ongoing job is deciding whether a
*newly surfaced* boundary, not yet reflected in `wiki/index.md`,
warrants its own entity.

A sub-package is promoted to its own entity when it meets at least 2
of 3:

1. **Structural boundary** — own top-level directory, distinct from
   siblings.
2. **Independent invariants** — carries constraints that aren't just
   inherited from the parent.
3. **Cross-entity fan-in** — depended on by 2+ entities outside its
   own parent row.

If a concern is ADR-only with no code yet, criterion 1 doesn't apply.
It may still be promoted with `implementation: pending` in
frontmatter if it's the primary subject of 2+ `accepted` ADRs and
doesn't nest under an existing entity's invariants. Flag these to
`/wiki-lint` as unverifiable against code until implementation exists.

### Entity naming and creation

Entity IDs are kebab-case slugs (e.g. `integration-providers`,
`rag-pipeline`) with no numeric prefix — unlike ADRs, entities are not
sequential events, so there is no "next number" to determine. The
filename must exactly match the Entity ID: `wiki/entities/<entity-id>.md`.

Before creating any new entity page, check `wiki/index.md` for an
existing entry covering the same concept — by name and by scope, not
just exact string match, since the same concern can arise under
slightly different phrasing across sessions. Create a new page only if
none exists. If one does, edit it in place rather than creating a
near-duplicate. This check applies equally whether the entity is being
created by `/wiki-sync`'s "No matching entity" branch or by the entity
boundary determination prompt for the initial decomposition — though
for the very first run, no prior entities exist yet, so the check has
nothing to find.

**Category assignment** works the same way, scanned against
`wiki/index.md`: reuse an existing category where the new entity
clearly fits one; introduce a new top-level category only if none
does. Introducing a new top-level category is a judgment call on the
same footing as an entity promotion decision — surface it rather than
deciding it silently.
