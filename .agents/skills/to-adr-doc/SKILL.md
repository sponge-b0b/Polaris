---
name: to-adr-doc
description: Create and manage Architectural Decision Records (ADRs) in docs/adr/. Owns ADR format, numbering, naming, lifecycle transitions, content mutability, realization maintenance, supersession, and Living Entity Wiki synchronization triggers.
compatibility: product=codex product=claude-code network=none
---

# To ADR Doc

`$to-adr-doc` is the single source of truth for ADR creation and lifecycle management.

ADRs live in:

```text
docs/adr/
```

and use globally sequential numbering.

Create the directory lazily when the first ADR is needed.

## ADR Format

Use the smallest structure that preserves the decision and its causal reasoning:

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

[Why was this option chosen over meaningful alternatives?]
```

Optional sections:

```md
## Considered Options

## Consequences
```

Add them only when they preserve useful information.

Keep ADRs concise.

## Status

Every ADR uses a `status` frontmatter field.

Allowed values:

```text
proposed
accepted
rejected
deprecated
superseded by ADR-NNNN
```

No separate `doc_class` is stored; ADR classification is derived from status according to `wiki/_schema.md`.

## Lifecycle

Allowed transitions are:

```text
proposed → accepted
proposed → rejected

accepted → deprecated
accepted → superseded by ADR-NNNN

deprecated → superseded by ADR-NNNN
```

`rejected` and `superseded` are terminal.

Do not invent additional transitions.

### Proposed

The decision is still being developed.

Its body may be edited while status remains `proposed`.

A substantive proposed-ADR edit must trigger `$wiki-sync`, because derived `Planned` knowledge may have changed even though status did not.

### Accepted

The decision is active architecture.

Acceptance does **not** necessarily mean implementation is complete.

Once accepted, decision content becomes historical and immutable except for the narrow **Realization Maintenance** exception below.

### Rejected

The decision was deliberately not adopted.

The body is immutable and the status is terminal.

If changed circumstances later make the direction viable, create a new ADR referencing the rejection rather than reopening it.

### Deprecated

The accepted decision is no longer active, but no formal replacement necessarily exists.

Its body remains immutable.

It may later become `superseded by ADR-NNNN`.

### Superseded

A later ADR formally replaced the decision.

The successor ADR must already exist.

The old ADR changes only its lifecycle status and then becomes terminal.

## Content Immutability

ADR body content is editable only while status is `proposed`, except for permitted **Realization Maintenance** on an accepted ADR.

Once an ADR leaves `proposed`, do not rewrite its:

* Context;
* Decision;
* Rationale;
* Considered Options;
* decision-bearing Consequences.

If the architecture changes, preserve history:

1. create a new ADR;
2. reference the earlier decision where useful;
3. supersede or deprecate the older accepted decision when appropriate.

Realization Maintenance must never be used to change what was decided, why it was decided, or the trade-offs originally accepted.

## Acceptance vs. Implementation

`accepted` means:

> this is the active architectural decision.

It does not necessarily mean:

> the repository already realizes it.

An accepted ADR may represent either:

* an **immediately effective constraint**, where acceptance itself establishes the rule; or
* a **realization-required decision**, where implementation must still change.

`$wiki-sync` owns that determination.

A realization-required accepted decision may remain under `Planned` as:

```text
accepted, implementation pending
```

until implementation evidence confirms realization.

Do not change ADR status merely because implementation finishes. It remains `accepted`.

If immediate effectiveness vs. implementation-pending is unclear, surface the ambiguity rather than guessing.

## Realization Maintenance

An accepted realization-required ADR may receive a narrow maintenance edit after current-state evidence clearly establishes that its decision has been fully realized.

`$to-adr-doc` does not independently determine realization. Apply this exception only when realization has already been established by the invoking workflow or `$wiki-sync`.

Permitted maintenance is limited to:

* changing stale realization wording from pending/future tense to implemented/current tense;
* updating a stale ADR reference when a later ADR formally carries forward or supersedes that referenced authority and the reference update does not change the decision's meaning.

For example:

```text
implementation must ...
accepted but implementation pending
```

may become:

```text
implementation has ...
this realization-required decision is implemented
```

Do not use Realization Maintenance to:

* alter Context, Decision, Rationale, or Considered Options;
* change a decision-bearing consequence or architectural requirement;
* introduce a new requirement, owner, boundary, trade-off, or rationale;
* reinterpret the historical decision using later implementation details;
* mark partial or ambiguous realization as complete;
* change ADR status.

If the required edit would change the architectural decision rather than only its realization/reference annotation, create a new ADR instead.

After Realization Maintenance, invoke `$wiki-sync` so derived current-state knowledge is re-evaluated.

## Numbering

Before creating an ADR, inspect `docs/adr/` for the highest numeric prefix and increment it.

Example:

```text
0007-...
0008-...
0009-...
```

Numbering is global and does not imply entity ownership.

## Naming

Apply the ADR naming rules in `wiki/_schema.md`.

When an active entity registry exists:

```text
000X-<entity-id>-<slug>.md
```

For a genuinely cross-cutting decision:

```text
000X-platform-<slug>.md
```

Use `platform-` only when there is no meaningful primary entity.

Before wiki bootstrap:

```text
000X-<slug>.md
```

Do not invent entity IDs before the approved registry exists.

## Living Entity Wiki Synchronization

If the Living Entity Wiki exists, invoke `$wiki-sync` after:

* creating an ADR;
* substantively editing a proposed ADR;
* applying Realization Maintenance;
* changing ADR status.

Pass the ADR path and relevant old/new status where applicable.

Let `$wiki-sync` determine all derived entity consequences, including:

* `Planned`;
* `Strict Invariants`;
* implementation-pending realization;
* retirement of inactive authority;
* `[source-conflict]`.

Do not duplicate those transition rules here.

If `$wiki-sync` identifies material disagreement among active authorities or implementation evidence, surface `[source-conflict]`.

Do not rewrite historical ADR content merely to force agreement.

## When to Create an ADR

Create or offer an ADR only when all three conditions are true:

1. **Hard to reverse** — changing the decision later carries meaningful cost or migration effort.
2. **Surprising without context** — a future contributor could reasonably ask why the system was designed this way.
3. **Real trade-off** — meaningful alternatives existed and one was chosen for specific reasons.

If a choice is easy to reverse, obvious, or lacks a meaningful alternative, an ADR is usually unnecessary.

Typical ADR subjects include:

* architectural shape;
* integration patterns;
* technology choices with meaningful lock-in;
* ownership or architectural boundaries;
* deliberate deviations from the obvious approach;
* consequential governance/product constraints;
* non-obvious rejected alternatives.

Do not create ADRs for routine implementation choices.

## Reconsidering Decisions

### Rejected direction becomes viable

Create a new ADR that:

* references the rejected ADR;
* explains what changed;
* evaluates the decision under the new conditions.

The old ADR remains rejected.

### Accepted decision is replaced

Create the successor ADR first, then transition the old ADR to:

```text
superseded by ADR-NNNN
```

### Accepted decision is retired without replacement

Change its status to:

```text
deprecated
```

A later successor may supersede it.

## Commit Ownership

`$to-adr-doc` does not require a standalone commit when invoked inside another workflow.

Any ADR change and resulting `$wiki-sync` mutation should follow the parent workflow's commit strategy.

Do not create a commit merely because `$to-adr-doc` or `$wiki-sync` ran.

## Out of Scope

`$to-adr-doc` does not:

* decide entity topology;
* update entity pages directly;
* independently determine whether implementation has realized an accepted decision;
* resolve `[source-conflict]`;
* classify or move non-ADR documents.

Those responsibilities belong to `wiki/_schema.md`, `$wiki-sync`, and `$classify-doc`.
