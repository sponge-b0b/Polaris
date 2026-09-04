# wiki/_template.md

# [Entity Name] (Entity ID: system-slug)

**Boundary Rationale:** [Why this is a distinct architectural boundary and why the boundary sits here.]
(source: [docs/... | owner-approved entity boundary determination | owner-approved entity promotion])

Required for every entity. Change only through an explicit boundary/topology decision, not ordinary code movement or refactoring.

### Strict Invariants

* [Invariant] — because [causal reasoning]. (source: docs/...)
* [Cross-entity invariant, when applicable, may link directly to the relevant entity.] (source: docs/...)

Valid sources are accepted ADRs and `docs/current/`.

An accepted realization-required decision remains under Planned as `accepted, implementation pending` until realization is verified. Immediately effective accepted constraints may appear here directly.

If applicable authorities materially disagree, surface `[source-conflict]` rather than rewriting the invariant.

### Rejected Approaches

* **[Approach]** — rejected because [specific causal reason].
  [Reconsider when: concrete condition that would materially change the reasoning.]
  (source: docs/... | owner-confirmed session decision, undocumented | session experiment, undocumented)

Record only owner-confirmed rejections, concrete failed experiments, or documented rejections. Unsupported agent judgment is insufficient.

`Reconsider when:` is optional and does not expire automatically.

Omit this section when empty.

### Open Questions

* **[Unresolved concern or question]** — noted YYYY-MM-DD.
  (source: docs/... | owner-raised session question, undocumented | agent-observed during session, unresolved)

Open Questions are unresolved signals, not facts or decisions.

When resolved, convert or remove them through the appropriate `$wiki-sync` lifecycle.

Omit this section when empty.

### Planned

* **[Anticipated change or direction]** — proposed, not yet accepted. (source: docs/...)
* **[Accepted decision]** — accepted, implementation pending. (source: docs/...)

Valid sources are:

* `docs/proposed/`;
* proposed ADRs;
* accepted ADRs whose realization remains pending.

Planned describes future state, never current implementation.

Omit this section when empty.
