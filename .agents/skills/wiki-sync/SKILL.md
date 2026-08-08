---
name: wiki-sync
description: Maintains the Living Entity Wiki (wiki/entities/) around three triggers — before any source code change (auditing compliance against stated invariants and previously rejected approaches, updating the entity page afterward if the change alters a structural boundary or invariant, or validates/rejects an approach, or surfaces an open question); around non-ADR docs/ content (checking whether entity pages citing an edited doc_class:current document are now stale, and separately checking whether a newly created or newly-promoted doc_class:current or doc_class:proposed document belongs on an entity page); and after an ADR is created or its status changes (checking whether the new or changed decision belongs on an entity page). Use before modifications to source code, after creating, editing, or reclassifying living docs/ content, and after ADR creation or status changes, triggered by any of these.
compatibility: product=codex product=claude-code system=git network=none
---

# Wiki Sync

## When this runs

Before modifying source code — triggered by any change, with one
mechanical exemption below. Not gated by "could this affect an
invariant," since predicting that answer is the audit's job, not a
precondition for running it — judging significance before loading the
entity page means guessing the audit's conclusion instead of running
it. Steps 1-4 stay cheap by design (a single lazy-loaded entity plus
direct references, or a fast `index.md` miss and exit when nothing
applies) specifically so this doesn't need a significance filter to
be worth running broadly. Step 6, the write-back, has a separate,
non-circular gate — see step 6 below — because by that point the
audit has already produced the real answer, not a prediction of one.

This is a convention, not an enforced gate — nothing prevents a code
change from happening without this skill running. That gap is
expected, not solved here. `[code-drift]` in the `/wiki-lint` check
exists specifically to catch it: an invariant that no longer matches
code is frequently the downstream evidence of a missed `/wiki-sync`
invocation, not just organic staleness. Treat `/wiki-lint` as the
second line of defense for exactly this scenario, and lean on it more
heavily than usual during stretches with a lot of ad hoc, skill-free
edits.

### Trivial-diff exemption

Skip steps 1-4 entirely — no audit, not even the cheap one — only
when the diff is mechanically classifiable as one of:

- Whitespace/formatting-only (e.g., an automated formatter pass).
- Comment or docstring only, with no code change.
- A pure rename/move where the old path is not cited as an anchor
  path in any entity page (a quick path lookup against `wiki/index.md`
  or entity frontmatter — not a full audit).

This is a syntactic check on the diff itself, not a judgment about
downstream impact. If there's any doubt whether a change fits one of
these categories, it doesn't — run the audit.

## Steps

### 1. Map boundaries

Read `wiki/index.md` to identify which entity the change falls under.
If no entity covers it, skip to "No matching entity" below.

### 2. Lazy-load the target entity

Load only the identified entity page from `wiki/entities/`. Do not
scan the full directory.

### 3. Load referenced entities

If the target entity's invariants or "Dependent Entities" section
reference other entities relevant to this change, load those too —
not just the target page. A change can violate an invariant, or repeat
a rejected approach, stated on a *related* entity's page even when the
target entity's own page looks fine. This is the specific gap the
original single-page check missed.

### 4. Compliance audit

Check the intended change against every invariant *and* every
Rejected Approaches entry loaded in steps 2-3.

- **No conflict with an invariant, and no match against a rejected
  approach** → proceed to step 5.
- **Conflict found with an invariant** → stop and surface it before
  writing any code. Do not resolve it unilaterally — flag it and let
  the invoking context (you, or the calling skill) decide whether the
  invariant is outdated or the change needs to adapt. This mirrors
  `/wiki-lint`'s rule: `/wiki-sync` flags, it does not silently
  overwrite a prior claim.
- **The intended approach matches or closely resembles a Rejected Approaches entry** → stop and surface it with the same severity as
  an invariant conflict. Report the matched entry, its reasoning, and
  its source. Do not silently retry a previously rejected approach —
  the invoking context decides whether circumstances have genuinely
  changed enough to revisit it. This is the check that makes Rejected
  Approaches actually prevent repeated failure, rather than just
  recording it after the fact.
- **No entity found at all for this boundary** → see "No matching
  entity" below; proceed with the code change, but note in the
  eventual commit that no entity coverage existed to audit against.

### 5. Modify source code

Standard implementation work, per the invoking skill/task.

### 6. Update the entity page — conditionally

Update if any of the following occurred, even if only one applies:

- The change altered a **structural boundary or invariant**.
- An approach was **validated or rejected** during this change — even
  if no invariant or boundary changed as a result. This is what feeds
  Rejected Approaches: a tried-and-failed approach that leaves the
  invariant landscape unchanged still needs to be recorded, or a
  future session will retry it with no memory of the first attempt.
- A concern surfaced that may warrant future change, without yet being
  resolved into a decision — recorded as an Open Questions entry
  rather than a structural update.

A rename, a new function, an internal refactor with no behavioral,
contractual, validated, rejected, or open-question outcome: no update.

When updating:
- Never write structural facts (file paths, module membership, call
  chains) — those come from codebase-memory-mcp/codegraph at query
  time, per `wiki/_template.md`. Only invariants, rationale,
  `linked_docs`, Rejected Approaches, and Open Questions change here.
- Any new or changed invariant must cite a source per the citation
  rule in `wiki/_schema.md` (`accepted` or `current` docs only).
- A new Rejected Approaches or Open Questions entry may cite either a
  `docs/` source or `(source: session decision, undocumented)`, per
  `wiki/_template.md` — these are exempt from the invariant citation
  rule, since they aren't backing an active invariant.
- If a session resolves an existing Open Questions entry — into a new
  invariant, a Rejected Approaches entry, or a decision to leave
  things as-is — remove or update that entry rather than leaving a
  stale, already-resolved question sitting on the page.
- If the change adds or changes a link to another entity, add the
  reciprocal link on that entity's own page in the same pass — don't
  leave it for the next `/wiki-lint` run to catch.
- Bump `last_updated`.
- Commit the entity-page change and append the matching `wiki/log.md`
  line as one atomic step, sharing a label:

      commit: wiki(entity-update): <entity> — <what changed>
      log.md: ## [YYYY-MM-DD] entity-update | <entity> — <what changed>

  Never write one without the other.

  When invoked from within another skill's workflow that performs its
  own single commit for the overall change (e.g. `/implement-ticket`),
  the entity-page diff and `wiki/log.md` line may instead be staged
  and included in that skill's commit rather than committed here
  directly. The pairing invariant is satisfied as long as both land
  in the same commit together — it does not require the commit to be
  `/wiki-sync`'s own.

### No matching entity

If the boundary being touched has no entity page:

1. Check it against the promotion test in `wiki/_schema.md` (2 of 3:
   structural boundary, independent invariants, cross-entity fan-in;
   or the ADR-only exception with `implementation: pending`).
2. **Passes** → apply the "Entity naming and creation" rules in
   `wiki/_schema.md`: check `wiki/index.md` for an existing entity
   covering the same concept before assuming this is new, then assign
   a kebab-case Entity ID and matching filename, and a category per
   the same section's category-assignment rule — reuse an existing
   category from `wiki/index.md` where the new entity clearly fits
   one, and flag it explicitly if none does and a new top-level
   category is being introduced. Create the page using
   `wiki/_template.md`, add it to `wiki/index.md`, commit and log as
   in step 6.
3. **Doesn't pass** → this boundary belongs under an existing parent
   entity's invariants, not its own page. Update the parent instead.
4. **Unclear** → proceed with the code change without wiki coverage,
   and say so explicitly rather than silently skipping the audit. Do
   not guess at entity boundaries to force a fit.

## Docs-change trigger

`/wiki-sync` also runs around non-ADR content under `docs/` — edited,
newly created, or reclassified. This branches by what actually
happened, the same way the ADR-change trigger branches by the ADR's
new `status`:

### Existing doc edited (staleness check)

An edit to an already-existing `doc_class: current` document. Docs
are the authoritative source entity invariants are derived from, so
there's no "conflict to block" the way a code change can violate a
stated invariant; the doc's new content is simply correct by
definition. What can go stale is the *wiki's copy* of a claim from
that doc, so this check looks forward from the edit, not backward.

1. After the edit is saved, check `linked_docs` across
   `wiki/entities/` for any entity citing the edited doc's path — a
   targeted grep, not a full-wiki scan.
2. **No entity cites it** → nothing to do.
3. **One or more entities cite it** → for each, compare the doc's new
   content against the specific invariant(s) that cite it.
   - **Invariant still holds** → no update needed.
   - **Invariant is now stale** → this is a live catch of what would
     otherwise surface later as `[doc-drift]` at the next
     `/wiki-lint` run. Update the entity page following step 6's
     rules above.
   - **Unclear whether it's stale** → flag it for human review rather
     than guessing.

### New or promoted doc (invariant/Planned check)

A new file created under `docs/` (outside `docs/adr/`) with
`doc_class: current` or `doc_class: proposed`, or an existing
document whose `Doc-Class:` line changes to `current` (most commonly
a promotion from `proposed`). Unlike the staleness check above, this
looks forward: a brand-new or newly-promoted doc has no existing
citation to check for drift, but may describe something that belongs
on an entity page immediately, rather than waiting for an unrelated
future code change to organically surface it.

1. **New doc with `doc_class: current`, or a doc just promoted to
   `current`** → check whether it establishes or changes an
   invariant that belongs on an entity page, using the same logic as
   step 6 and the "No matching entity" flow above. If a Planned entry
   already exists on some entity citing this doc from when it was
   `proposed`, replace it with the now-settled invariant — same rule
   as the ADR-change trigger's `accepted` branch.
2. **New doc with `doc_class: proposed`** → check whether it belongs
   in some entity's Planned section, citing the doc.
3. If it's unclear whether the doc belongs on any entity page, flag
   it for human review rather than silently guessing — same as the
   ADR-change trigger.

`doc_class: research`, `process`, and `reference` documents are
excluded from this entire trigger, both branches — per the citation
rule in `wiki/_schema.md`, none of those classes may ever back an
invariant or a Planned entry, so there's nothing for either check to
do when one is created or edited.

Both branches apply independently of whether the change happened
inside a ticket workflow or as an ad hoc edit. Same caveat as every
other trigger: this is a convention, not an enforced gate, and a
missed invocation is still caught eventually by `/wiki-lint`'s
`[doc-drift]` or `[unclassified-doc]` checks.

This does not apply to `docs/adr/` — ADRs have their own trigger
below, since ADR lifecycle (`status`) is a distinct mechanism from
`doc_class`.

## ADR-change trigger

`/wiki-sync` also runs after `/domain-modeling` creates a new ADR or
changes an existing ADR's `status` field. This trigger only applies if
`wiki/entities/` exists in this repository — `/domain-modeling` may be
used in repos without a Living Entity Wiki, per `/to-adr-doc`'s own
carve-out, in which case there is nothing for this trigger to do.

Unlike the docs-change trigger, which only ever checks for staleness,
this trigger branches on the ADR's new `status`:

- **New status is `proposed`** → check whether this decision, if
  adopted, would belong in some entity's Planned section (per
  `wiki/_template.md`, sourced from `doc_class: proposed` content).
  If so, add it there, citing the ADR.
- **New status is `accepted`** → check whether this establishes or
  changes an invariant that belongs on an entity page, using the same
  logic as step 6 and the "No matching entity" flow above. If a
  Planned entry already exists on some entity citing this ADR from
  when it was `proposed`, replace it with the now-settled invariant
  rather than leaving both a stale Planned entry and a new invariant
  describing the same decision.
- **New status is `rejected`, `deprecated`, or `superseded by
  ADR-NNNN`** → check whether any entity currently cites this ADR in
  an active invariant. If so, this is a live catch of what
  `/wiki-lint`'s `[stale-citation]` check would otherwise surface
  later. Flag it — do not resolve it unilaterally, per the same rule
  as step 4's compliance audit; deciding what the invariant becomes
  (removed, replaced, left as historical note) is a human call.

### Steps

1. Confirm `wiki/entities/` exists. If not, this trigger does not
   apply — stop here.
2. Based on the ADR's new `status`, apply the corresponding check
   above.
3. If a wiki update is warranted, apply it following step 6's rules:
   citation must be `accepted` or `current` only for an active
   invariant (a newly `accepted` ADR now qualifies), preserve causal
   reasoning, bump `last_updated`, and pair the commit with its
   `wiki/log.md` line atomically — or stage both for inclusion in a
   calling skill's single commit, same as step 6.
4. If it's unclear whether the ADR belongs on any entity page, flag
   it for human review rather than silently guessing. Do not force an
   ADR onto an entity it doesn't clearly belong to just to close the
   loop.

## Out of scope

- **Bootstrap** (initial creation of all entities from `docs/`) is a
  separate, one-time operation — not something `/wiki-sync` performs
  incrementally.
- **Lint** (contradiction/drift/citation checks across the whole
  wiki) is handled by the separate `/wiki-lint` skill, not run as
  part of every `/wiki-sync` invocation. `/wiki-sync` maintains one
  entity at a time, in the context of one change; `/wiki-lint` audits
  the wiki as a whole.
- **Cross-entity pattern synthesis** (recurring themes across Rejected
  Approaches or Open Questions entries on different entities) is
  handled by the separate `/wiki-synthesize` skill, not attempted
  here. `/wiki-sync`'s step 3 only loads entities directly referenced
  by the one being edited — it does not scan the full wiki for
  patterns the way `/wiki-synthesize` does.
- **`docs/` is never edited by this skill.** Direction of truth is
  one-way, `docs/` → `wiki/entities/`. If a change reveals that a
  `docs/` file is now wrong, that's a signal to raise to the human,
  not something `/wiki-sync` corrects itself.
