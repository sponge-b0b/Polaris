---
name: to-adr-doc
description: Create or modify an Architectural Decision Record (ADR) in docs/adr/ — required frontmatter, sequential numbering, entity-prefixed naming when a Living Entity Wiki exists, and when creating an ADR is actually warranted. Use whenever a decision needs to be recorded as an ADR, or when another skill (e.g. /domain-modeling) needs to write one.
compatibility: product=codex product=claude-code network=none
---

# To ADR Doc

ADRs live in `docs/adr/` and use sequential numbering. Create the
`docs/adr/` directory lazily — only when the first ADR is needed.

## Template

```md
---
status: "{proposed | rejected | accepted | deprecated | superseded by ADR-NNNN}"
---

# {Short title of the decision}

{1-3 sentences: what's the context, what did we decide, and why.}
```

`status` must appear as a YAML frontmatter field, delimited by `---`
at the very top of the file, before the title — not as a plain text
line in the body. This is a required deviation from base MADR (which
treats status as optional metadata) — see "Project-specific
requirement" below for why.

## Project-specific requirement: status is mandatory

Base MADR treats `status` as optional metadata, useful mainly when a
decision gets revisited. In this repository, `status` is **required on
every ADR, not optional**, because the Living Entity Wiki (`wiki/`)
derives each ADR's `doc_class` directly from this field — see
`wiki/_schema.md`. An ADR with no `status` field cannot be classified,
which breaks citation and drift-checking for anything that would
reference it.

If this skill is used in a repository without a Living Entity Wiki,
this requirement does not apply — treat `status` as optional, per base
MADR, in that context.

## Numbering

Before creating a new ADR, list `docs/adr/` to find the highest
existing numeric prefix, and increment by one. Numbering is global
across `docs/adr/` regardless of which entity an ADR concerns — it
governs chronological order and "next number" lookups, not
organization by topic; that's the entity prefix's job (below).

## Entity-prefixed naming

If `wiki/entities/` exists in this repository, the filename is
`000X-<primary-entity-id>-<slug>.md`, per "Document naming
convention" in `wiki/_schema.md` — the sequential prefix from
Numbering above, followed by the entity this ADR primarily concerns.

Determine `<primary-entity-id>` by checking `wiki/index.md` for the
entity the decision most concerns. If the ADR genuinely spans
multiple entities equally, or concerns a cross-cutting decision no
single entity owns, use `platform-` in place of an entity ID instead
— per "Cross-cutting documents" in `wiki/_schema.md`. Reach for
`platform-` only when there's genuinely no primary entity, not as a
shortcut to avoid picking one.

If `wiki/entities/` does not exist, this does not apply — use
`000X-<slug>.md`, the base convention, with no entity prefix.

## Living Entity Wiki sync

If `wiki/entities/` exists in this repository, invoke the
`/wiki-sync` skill's ADR-change trigger immediately after:

- Creating a new ADR, or
- Changing an existing ADR's `status` field.

This lets the wiki pick up a new or changed decision — whether it
belongs on an entity page as an invariant, a Planned entry, or a
signal that an existing citation is now stale — without waiting for
an unrelated code or docs change to surface it later. See
`/wiki-sync`'s "ADR-change trigger" section for what it checks and
how it branches on the new `status` value.

If `wiki/entities/` does not exist, this does not apply — proceed
without invoking `/wiki-sync`.

## Optional sections

Only include these when they add genuine value. Most ADRs won't need
them.

- **Considered Options** — only when the rejected alternatives are
  worth remembering.
- **Consequences** — only when non-obvious downstream effects need to
  be called out.

## When to offer an ADR

All three of these must be true:

1. **Hard to reverse** — the cost of changing your mind later is
   meaningful.
2. **Surprising without context** — a future reader will look at the
   code and wonder "why on earth did they do it this way?"
3. **The result of a real trade-off** — there were genuine
   alternatives and you picked one for specific reasons.

If a decision is easy to reverse, skip it — you'll just reverse it. If
it's not surprising, nobody will wonder why. If there was no real
alternative, there's nothing to record beyond "we did the obvious
thing."

### What qualifies

- **Architectural shape.** "We're using a monorepo." "The write model
  is event-sourced, the read model is projected into Postgres."
- **Integration patterns between contexts.** "Ordering and Billing
  communicate via domain events, not synchronous HTTP."
- **Technology choices that carry lock-in.** Database, message bus,
  auth provider, deployment target. Not every library — just the ones
  that would take a quarter to swap out.
- **Boundary and scope decisions.** "Customer data is owned by the
  Customer context; other contexts reference it by ID only." The
  explicit no-s are as valuable as the yes-s.
- **Deliberate deviations from the obvious path.** "We're using manual
  SQL instead of an ORM because X." Anything where a reasonable reader
  would assume the opposite. These stop the next engineer from
  "fixing" something that was deliberate.
- **Constraints not visible in the code.** "We can't use AWS because
  of compliance requirements." "Response times must be under 200ms
  because of the partner API contract."
- **Rejected alternatives when the rejection is non-obvious.** If you
  considered GraphQL and picked REST for subtle reasons, record it —
  otherwise someone will suggest GraphQL again in six months.
