---
name: to-adr-doc
description: Create and manage Architectural Decision Records (ADRs) in docs/adr/. Owns ADR format, required status metadata, numbering, naming, lifecycle transitions, content mutability, supersession, and Living Entity Wiki synchronization. Use whenever an ADR is created, a proposed ADR is edited, or an existing ADR changes lifecycle status.
compatibility: product=codex product=claude-code network=none
---

# To ADR Doc

This skill is the single source of truth for ADR creation and lifecycle management in this repository.

ADRs live in `docs/adr/` and use globally sequential numbering.

Create `docs/adr/` lazily when the first ADR is needed.

## ADR Format

Use this minimal structure:

```md
---
status: proposed
---

# [Short decision title]

## Context

[What problem, constraint, or architectural question requires a decision?]

## Decision

[What was decided?]

## Rationale

[Why was this option chosen over the meaningful alternatives?]
```

Keep ADRs concise. Preserve enough causal reasoning that a future contributor can understand why the decision was made without reconstructing the original discussion.

Optional sections may be added only when they provide durable value:

```md
## Considered Options

[Meaningful alternatives and why they were not chosen.]

## Consequences

[Non-obvious downstream costs, constraints, or trade-offs created by the decision.]
```

Do not add sections merely to fill out a template.

---

## Status Is Mandatory

Every ADR in a repository with the Living Entity Wiki must have a `status` YAML frontmatter field at the very top of the file.

Allowed values are:

```text
proposed
accepted
rejected
deprecated
superseded by ADR-NNNN
```

The wiki derives the ADR's `doc_class` from this field. No separate `doc_class` is stored.

If this skill is used in a repository without a Living Entity Wiki, mandatory status is not required by this project-specific rule.

---

## ADR Lifecycle

The allowed lifecycle is:

```text
proposed
   ├──→ accepted
   └──→ rejected

accepted
   ├──→ deprecated
   └──→ superseded by ADR-NNNN

deprecated
   └──→ superseded by ADR-NNNN

rejected
   └── terminal

superseded
   └── terminal
```

Do not invent additional transitions.

### `proposed`

The decision is still being developed or evaluated.

The ADR body may be edited while status remains `proposed`.

Because proposed ADR content may feed an entity's `Planned` section, substantive edits to a proposed ADR must invoke the `$wiki-sync` ADR/docs-source reevaluation path even when the `status` field itself does not change.

### `accepted`

The architectural decision has been adopted.

Acceptance means:

> this is the active architectural decision.

It does **not** necessarily mean:

> the repository has already finished implementing the decision.

Once accepted, the ADR's decision content becomes historical and immutable.

Only lifecycle status may subsequently change.

### `rejected`

The proposed decision was deliberately not adopted.

The ADR body is historical and immutable.

`rejected` is terminal.

If changed circumstances later make the rejected direction worth reconsidering, create a new ADR that references the earlier rejection and explains what changed. Do not rewrite or reactivate the rejected ADR.

### `deprecated`

The accepted decision is no longer recommended or active, but no formal replacement decision necessarily exists yet.

The ADR body remains historical and immutable.

A deprecated ADR may later become:

```text
superseded by ADR-NNNN
```

when a formal successor exists.

### `superseded by ADR-NNNN`

A later ADR has replaced this decision.

The successor ADR must already exist.

The old ADR remains unchanged except for its lifecycle status.

`superseded` is terminal.

---

## Content Immutability

ADR content is editable only while status is `proposed`.

Once an ADR leaves `proposed`, its decision content is historical and must not be rewritten to reflect later understanding.

Do not modify an accepted, rejected, deprecated, or superseded ADR's Context, Decision, Rationale, Considered Options, or Consequences.

When a historical decision needs to be changed:

1. create a new ADR describing the new decision;
2. reference the prior ADR where relevant; and
3. transition the prior accepted or deprecated ADR to `superseded by ADR-NNNN` when the new ADR formally replaces it.

Preserve history rather than rewriting it.

---

## Acceptance vs. Implementation

An accepted ADR can affect the entity wiki in one of two ways.

### Immediately-effective constraint

Some decisions become active constraints simply because they have been adopted.

Examples include:

* product-scope restrictions;
* governance constraints;
* ownership boundaries;
* prohibited architectural directions;
* compliance constraints.

When acceptance itself makes the constraint effective, `$wiki-sync` may represent it immediately as a `Strict Invariant`.

### Realization-required decision

Some accepted decisions describe architecture or behavior that still has to be implemented.

Examples include:

* migrating canonical persistence;
* replacing an orchestration boundary;
* introducing a new projection architecture;
* moving responsibility between components.

These remain in the relevant entity's `Planned` section as:

```text
accepted, implementation pending
```

until current-state evidence confirms that the decision has actually been realized.

Once realization is verified, `$wiki-sync` removes the Planned entry and represents the resulting active constraint under `Strict Invariants`.

Do not change the ADR status when implementation finishes. The ADR remains `accepted`; implementation realization is wiki/current-state lifecycle, not ADR lifecycle.

If it is unclear whether acceptance itself establishes the constraint or implementation is still required, surface the question rather than guessing.

---

## Numbering

Before creating a new ADR, inspect `docs/adr/` for the highest existing numeric prefix and increment it by one.

Numbering is global across `docs/adr/`.

Example:

```text
0007-...
0008-...
0009-...
```

The number records ADR sequence. It does not indicate entity ownership.

---

## Entity-Prefixed Naming

If `wiki/index.md` exists and contains the active entity registry, determine the ADR's primary architectural subject from that registry.

For an ADR primarily concerning one entity:

```text
000X-<primary-entity-id>-<slug>.md
```

Example:

```text
0012-persistence-postgres-source-of-record.md
```

For a genuinely cross-cutting decision with no meaningful primary entity:

```text
000X-platform-<slug>.md
```

Use `platform-` only when no single active entity meaningfully owns the decision.

Do not use it merely to avoid choosing a primary entity.

If the Living Entity Wiki has not yet been bootstrapped, use:

```text
000X-<slug>.md
```

Entity prefixes may be introduced later through the approved document classification/renaming process.

---

## Living Entity Wiki Synchronization

If `wiki/entities/` exists, invoke `$wiki-sync` after any ADR event that may change derived entity knowledge.

### New ADR

After creating an ADR, invoke `$wiki-sync`.

Behavior depends on its status:

* `proposed` → evaluate whether the decision belongs under `Planned`;
* `accepted` → determine whether it is immediately effective or realization-required;
* `rejected`, `deprecated`, or `superseded` → verify that no active derived wiki claim incorrectly treats it as current authority.

### Proposed ADR body edit

After substantively editing an ADR whose status remains `proposed`, invoke `$wiki-sync`.

Re-evaluate any `Planned` entry sourced from that ADR.

The fact that its status did not change does not exempt it from synchronization; its meaning may have changed.

### Status change

After changing an ADR's lifecycle status, invoke `$wiki-sync`.

Examples:

```text
proposed → accepted
proposed → rejected
accepted → deprecated
accepted → superseded by ADR-NNNN
deprecated → superseded by ADR-NNNN
```

`$wiki-sync` owns the resulting entity-wiki transition.

### Source conflicts

If the ADR conflicts materially with verified implementation evidence or applicable `docs/current/` authority, do not silently alter the ADR or derived wiki to force agreement.

Surface `[source-conflict]` according to `wiki/_schema.md`.

The entity wiki never chooses between conflicting authorities by itself.

---

## When to Create an ADR

Create or offer an ADR only when all three conditions are true:

1. **Hard to reverse**
   Changing the decision later would carry meaningful cost or migration effort.

2. **Surprising without context**
   A future contributor could reasonably question why the architecture was designed this way.

3. **Result of a real trade-off**
   Meaningful alternatives existed and one was selected for specific reasons.

If a decision is easy to reverse, obvious from context, or has no meaningful alternative, an ADR is usually unnecessary.

### Typical ADR subjects

Good ADR candidates include:

* architectural shape;
* integration patterns between contexts;
* technology choices with meaningful lock-in;
* ownership and boundary decisions;
* deliberate deviations from the obvious approach;
* constraints not visible in source code;
* consequential governance or product-scope boundaries;
* non-obvious rejected alternatives.

Do not create ADRs for routine implementation choices or ordinary library usage that can be changed cheaply.

---

## Reconsidering Earlier Decisions

Do not modify historical ADR content merely because circumstances changed.

### Previously rejected direction becomes viable

Create a new ADR that:

* references the rejected ADR;
* explains what changed;
* evaluates the decision under the new conditions.

The old rejected ADR remains rejected.

### Accepted decision is replaced

Create the successor ADR first.

Once the successor formally replaces the prior decision, update the old ADR's status to:

```text
superseded by ADR-NNNN
```

### Accepted decision is retired without replacement

Change its status to:

```text
deprecated
```

A later successor may then transition it from `deprecated` to `superseded by ADR-NNNN`.

---

## Out of Scope

This skill does not:

* decide entity topology;
* update entity pages directly;
* determine whether implementation has realized an accepted decision;
* resolve `[source-conflict]`;
* classify or move non-ADR documents.

Those responsibilities belong respectively to `wiki/_schema.md`, `$wiki-sync`, and `$classify-doc`.
