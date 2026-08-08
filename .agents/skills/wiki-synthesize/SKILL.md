---
name: wiki-synthesize
description: Scans across all entity pages in wiki/entities/ for recurring or cumulative patterns in Rejected Approaches and Open Questions — signals that no single entity page states on its own, and that /wiki-lint's direct-contradiction check cannot catch, since nothing directly conflicts. Produces a report only; never writes to wiki/entities/ or docs/. Run on-demand or periodically as entries accumulate, not tied to any single session or code change.
compatibility: product=codex product=claude-code system=git network=none
disable-model-invocation: true
---

# Wiki Synthesize

## When this runs

On-demand, or recommended periodically as Rejected Approaches and Open
Questions entries accumulate across entities — not tied to a single
session, a single code change, or session shape the way `/wiki-lint`
is. Most individual sessions won't add enough new entries for a
cross-entity pattern to be newly visible, so running this every
session mostly produces "nothing new" noise. A reasonable default is
after roughly 10-15 new Rejected Approaches or Open Questions entries
have accumulated since the last run, or whenever you suspect something
is recurring and want it checked deliberately.

This is a full-wiki read, not a lazy-loaded one — unlike `/wiki-sync`,
which loads only the entity relevant to a specific change, this skill
loads every entity page in `wiki/entities/` in full. That cost is
accepted here the same way it's accepted for `/wiki-lint`: this
operation only makes sense evaluated across the whole wiki at once.

## What this is not

`/wiki-lint`'s "Contradictions between entity pages" check catches
*direct* conflicts — entity A states X, entity B states not-X. That's
a clean, deterministic comparison. This skill exists for the opposite
case: nothing directly contradicts, but a pattern recurs often enough
across entities to be worth surfacing on its own — a signal, not a
proof. Do not treat a finding from this skill as equivalent in
certainty to a `/wiki-lint` finding.

This skill performs judgment and inference, not mechanical comparison.
That is exactly why its output is constrained the way it is below —
judgment calls are reported for a human to weigh, never written back
as if they were settled facts.

## Steps

### 1. Load the full wiki
Read every entity page in `wiki/entities/` in full — not lazily, not
by index lookup.

### 2. Scan for cross-entity patterns
Look across all loaded entities for:

- **Recurring rejection themes** — two or more Rejected Approaches
  entries, on the same entity or different ones, that trace back to a
  common underlying cause or assumption even if worded differently.
  Two isolated, unrelated rejections are not a pattern; the same root
  cause showing up more than once is.
- **Reinforced or contradicted open questions** — an Open Questions
  entry on one entity that is implicitly answered, reinforced, or put
  in tension by a Rejected Approaches entry or invariant on a
  *different* entity. This is the case `/wiki-sync`'s step 3
  (load referenced entities) can't catch, because it only looks at
  entities directly linked to the entity being edited, not the whole
  wiki.
- **Invariant tension** — a pattern across multiple Rejected
  Approaches or Open Questions entries, possibly on different
  entities, that suggests an existing Strict Invariant may rest on an
  assumption that no longer holds. This is the most inferential of the
  three checks and should be reported with the most hedged framing —
  it is a "worth reconsidering," never a "this is wrong."

### 3. Cite everything
Every pattern reported must cite the specific entries that support
it — entity name, section, and the entry's own citation (or `session
decision, undocumented`, if that's what the entry itself carries).
A pattern with only one supporting entry is not a pattern; do not
report single-entry "patterns" dressed up as trends.

## Report format

Output a report, not a wiki edit:

    ## Synthesis Report — [YYYY-MM-DD]

    ### Pattern: [one-line description]
    Confidence: [low | medium | high]
    Supporting entries:
    - [entity] › Rejected Approaches: "[entry]" (source: ...)
    - [entity] › Open Questions: "[entry]" (source: ...)
    Suggested next step: [e.g. "consider a new ADR", "revisit invariant X
    on entity Y"] — not applied, for human review only.

If no patterns are found, report that plainly rather than straining to manufacture one — a clean run is a valid and useful outcome, not a failure of the pass.

## Resolution rules

This skill **never** writes to `wiki/entities/` or `docs/`, under any
circumstance — stricter than `/wiki-sync`'s and `/wiki-lint`'s
existing "flags, doesn't resolve" rule, because the judgment involved
here is inference across sources rather than a mechanical comparison,
and a fabricated or overstated pattern presented as fact would be the
most damaging kind of error this whole system could produce. Every
finding is a candidate for human review. If a pattern is confirmed
real, act on it through the normal channels afterward — a new ADR, a
revised invariant via `/wiki-sync`, a new Rejected Approaches entry —
not as an automatic output of this skill.

## Logging

Every run gets one line in `wiki/log.md`, so a run that finds nothing
still leaves a trace, same reasoning as `/wiki-lint`:

    ## [YYYY-MM-DD] synthesize | N patterns found (confidence: low: n, medium: n, high: n)

A fully clean run is written as:

    ## [2026-08-04] synthesize | 0 patterns found

Commit this log.md entry on its own, as its own atomic operation —
unlike `/wiki-sync` and `/wiki-lint`, this skill never produces any
other file diff to pair it with, since it never writes to
`wiki/entities/` or `docs/` under any circumstance. Never leave the
log line uncommitted:

    commit: wiki(synthesize): <date> — N patterns found
    log.md: ## [YYYY-MM-DD] synthesize | N patterns found (...)

## Out of scope

- **Direct contradictions** between entity pages are `/wiki-lint`'s
  job, not this skill's — see "What this is not" above.
- **Drift** against code or docs (`[code-drift]`, `[doc-drift]`,
  citation checks, structural hygiene) is entirely `/wiki-lint`'s
  domain.
- **Per-change auditing and entity maintenance** is `/wiki-sync`'s
  domain. This skill never runs as part of a single code or docs
  change — it operates independently, across the accumulated history
  of the whole wiki.
- **Acting on a finding** — writing a new invariant, creating an ADR,
  resolving an Open Questions entry — is not performed by this skill.
  It produces the report; a human, or a subsequent `/wiki-sync`
  invocation once a decision is made, does the writing.
