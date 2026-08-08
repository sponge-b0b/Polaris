# wiki/_template.md

# [Entity Name] (Entity ID: system-slug)

**Boundary Rationale:** [One or two sentences explaining why this is a distinct entity rather than part of another boundary, or why the boundary sits where it does.]
(source: [docs/... | owner-approved entity boundary determination | owner-approved entity promotion])

Boundary Rationale is required for every entity. It records the reasoning behind the architectural decomposition, not mechanically derivable structure.

Change it only as part of an explicit entity-boundary or topology decision such as creation, promotion, split, merge, or a scope-changing rename. Ordinary code movement or refactoring is not sufficient reason to rewrite it.

### Strict Invariants

* [Invariant] — because [causal reasoning]. (source: docs/...)
* [Cross-entity invariant, when applicable, may link directly to the other entity whose constraint is relevant.] (source: docs/...)

Only claims backed by an accepted ADR or a `docs/current/` document may appear here.

An accepted ADR contributes a Strict Invariant only when either:

* acceptance itself establishes an immediately-effective constraint; or
* a realization-required decision has been verified as implemented.

A realization-required accepted decision that has not yet been verified belongs under `Planned`, marked `accepted, implementation pending`.

Keep the strength of implementation claims proportional to available evidence. A mechanically observable invariant may be positively verified against implementation. An architectural or intent-level invariant may be audited for concrete contradictory evidence, but absence of such evidence does not prove compliance.

If authoritative sources materially disagree, do not choose a winner or rewrite the invariant. Surface a `[source-conflict]` and resolve the source disagreement first.

### Rejected Approaches

* **[Approach]** — rejected because [specific causal reason].
  [Reconsider when: concrete condition that would materially change the original reasoning.]
  (source: docs/... | owner-confirmed session decision, undocumented | session experiment, undocumented)

Record a Rejected Approach only when:

* the owner explicitly rejected it;
* it was actually attempted and failed for a concrete, non-obvious reason worth preserving; or
* an authoritative document records the rejection.

An agent's unsupported judgment is not sufficient to create a durable Rejected Approach.

`Reconsider when:` is optional and should be used only when the rejection depends on a concrete condition that may later change. Rejections do not expire merely because time passes.

When reconsideration becomes appropriate, preserve the history rather than silently deleting the old rejection. Record the subsequent decision through the appropriate authoritative source when warranted.

Omit this section if there are no Rejected Approaches for the entity.

### Open Questions

* **[Unresolved concern or question]** — noted YYYY-MM-DD.
  (source: docs/... | owner-raised session question, undocumented | agent-observed during session, unresolved)

Open Questions preserve unresolved signals, not decisions or current facts. An agent may record a concrete concern it discovers, provided it is clearly represented as unresolved rather than as established truth.

When a question is resolved:

* convert the outcome to a Strict Invariant if it establishes an active constraint;
* move a qualifying failed direction to Rejected Approaches;
* update the relevant Planned entry when it changes future direction; or
* remove the question when the resolution produces no durable entity knowledge.

Omit this section if there are no open questions.

### Planned

* **[Anticipated change or direction]** — proposed, not yet accepted. (source: docs/...)
* **[Accepted decision]** — accepted, implementation pending. (source: docs/...)

`Planned` contains future state that is explicitly not yet established as current implementation.

It may be sourced from:

* `docs/proposed/` documents;
* ADRs with `status: proposed`; or
* accepted ADRs whose realization still requires implementation or other current-state verification.

When an accepted realization-required decision is verified as realized, remove the Planned entry and represent the resulting active constraint under Strict Invariants.

If acceptance itself establishes an immediately-effective constraint, the claim may enter Strict Invariants directly instead of passing through `accepted, implementation pending`.

When a cited proposed source changes, re-evaluate the corresponding Planned entry rather than allowing the derived description to drift.

Omit this section if there is no planned content for the entity.
