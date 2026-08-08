# wiki/_template.md

# [Entity Name] (Entity ID: system-slug)

---
category: [Top-level architectural grouping this entity maps to.
  Reuse an existing category already in use across wiki/index.md
  where this entity clearly fits one — introduce a new top-level
  category only if none does, and flag that as a judgment call rather
  than deciding it silently. If promoted as a sub-entity of an
  existing entity, reflect the parent's category with a qualifier —
  e.g. "Application (RAG)".]
last_updated: YYYY-MM-DD
linked_docs: [docs/adr/0004-persistence-postgres-source-of-record.md, docs/current/platform-rag-pipeline.md]
implementation: complete | pending
---

> **Agent Boundary Instruction:** This is a live machine-readable twin
> of the active repository. Update immediately if code drift occurs.
> Never edit `docs/` to match this page — direction of truth is
> one-way, from `docs/` to here.

**Boundary Rationale:** [One or two sentences — why this is a
distinct entity rather than folded under a parent, or why the
boundary sits where it does. Required for every entity — sourced from
the boundary or promotion-test reasoning applied when the entity was
created. There is no exempt/self-evident case — every entity's
existence traces back to an explicit decision somewhere in this
system, and that decision should be recoverable from the page itself.]

### Anchor Paths
*   **Primary entry point:** `path/to/file.py`
*   (1-2 max. Full module membership, call chains, and file listings
    come from codebase-memory-mcp/codegraph at query time — never
    enumerated here.)

### Dependent Entities
*   **Upstream:** [Link](parent-entity.md)
*   **Downstream:** [Link](child-entity.md)
*   (Every link here must have a matching reciprocal link on the
    linked entity's own page. `/wiki-sync`'s step 6 adds this inline
    when a link changes; the bootstrap prompt's closure pass and
    `/wiki-lint`'s reciprocal-link check both catch anything that
    slips through.)

### Strict Invariants
*   [Invariant] — because [reasoning] (source: docs/adr/000X-....md)
*   Only invariants sourced from `doc_class: accepted` or `doc_class:
    current` documents may appear here. Citing anything else is an
    `[invalid-citation]` finding from `/wiki-lint`.

### Rejected Approaches
*   [Approach] — rejected because [reason] (source: docs/adr/000X-....md)
*   Citation here may be a `docs/` path, or `(source: session
    decision, undocumented)` when the rejection happened in-session
    and was never written up formally. The latter is exempt from
    `/wiki-lint`'s citation checks — those apply to backing an active
    invariant, not to recording a rejected approach — but should be
    upgraded to a real citation if the reasoning later gets captured
    in an ADR or doc.
*   `/wiki-sync` step 4 checks intended changes against this section,
    not just against Strict Invariants — this is what prevents a
    future session from silently retrying a previously rejected
    approach.

### Open Questions
*   [Concern or signal that something may need to change] — noted
    [YYYY-MM-DD] (source: session decision, undocumented | docs/....md)
*   For unresolved signals only — not yet a decision, not yet an
    invariant or a rejected approach. Same citation flexibility as
    Rejected Approaches. When a session resolves an entry (into a new
    invariant, a Rejected Approaches entry, or a decision to leave
    things as-is), `/wiki-sync` removes or updates it rather than
    leaving it stale. Omit this section entirely if there are no open
    questions for this entity.

### Planned
*   [Anticipated change or direction] — explicitly not yet true,
    sourced only from `doc_class: proposed` documents (source:
    docs/....md). Never phrased as a current invariant. Omit this
    section entirely if no proposed docs touch this entity.
