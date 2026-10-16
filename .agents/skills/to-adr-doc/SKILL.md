---
name: to-adr-doc
description: Create and manage Architectural Decision Records as rationale/history records whose accepted software semantics project an exact CCL transaction when applicable.
compatibility: product=codex product=claude-code network=none
---

# To ADR Doc

`$to-adr-doc` owns ADR format, numbering, lifecycle, historical immutability, and the ADR-side projection of accepted Canonical Contract Ledger (CCL) semantics.

ADRs live in:

```text
docs/adr/
```

An ADR explains **why** a consequential decision was made. For new material software semantics backed by CCL, it does not independently restate or reinterpret **what** was decided.

## When to Create an ADR

Create an ADR only when all three are true:

1. **Hard to reverse** — later change has meaningful migration/cost;
2. **Surprising without context** — a future contributor could reasonably ask why;
3. **Real trade-off** — meaningful alternatives existed and one was deliberately selected.

Routine implementation choices do not need ADRs.

## Two ADR Forms

### CCL-backed accepted ADR

Use for a newly accepted material software decision whose semantics are represented by an accepted CCL transaction.

Required frontmatter:

```yaml
---
status: accepted
ccl_proposal: sha256:<64-hex>
ccl_transaction: contracts/ccl/transactions/<proposal-hash-without-prefix>.json
---
```

Required body:

```markdown
# <Short decision title>

## Context

<why this decision was necessary>

## Decision

<exact machine-managed CCL projection>

## Rationale

<why this semantic contract was chosen over material alternatives>
```

Optional:

```markdown
## Considered Options

## Consequences
```

For a CCL-backed ADR, the entire `## Decision` section is machine-managed. Generate it only with:

```bash
python scripts/ccl_adr.py render-decision <accepted-transaction.json>
```

After writing the ADR, require:

```bash
python scripts/ccl_adr.py check-adr <adr-path> <accepted-transaction.json>
```

Do not add prose before, after, or inside the generated Decision block.

`Context`, `Rationale`, `Considered Options`, and `Consequences` are explanatory/history surfaces. They may describe implications and trade-offs but must not introduce a material requirement, cardinality, vocabulary, ownership rule, lifecycle, failure mode, or other semantic contract absent from the linked CCL transaction.

If explanatory prose reveals a missing semantic requirement, stop and return to the semantic decision owner. Do not silently add it to the ADR.

### Legacy / non-CCL ADR

Existing ADRs created before CCL retain their historical form and lifecycle. Do not rewrite them solely to look modern.

A genuinely non-semantic architecture record may also remain unbacked when no material software contract is being created or changed.

Do not use the legacy form as an escape hatch for a new material software decision that should be CCL-backed.

## Why the Decision Projection Is Generated

The CCL transaction is the exact accepted semantic payload. The ADR Decision section is a deterministic human-readable projection so humans and not-yet-migrated downstream workflows can still inspect the contract without creating a second independently authored version.

For CCL-backed ADRs:

```text
CCL typed assertions = frozen semantic contract
ADR Decision section = deterministic projection
ADR Context/Rationale = explanation/history
```

If the generated projection does not match the transaction, the ADR is invalid.

## Status

Allowed statuses:

```text
proposed
accepted
rejected
deprecated
superseded by ADR-NNNN
```

Allowed transitions:

```text
proposed -> accepted
proposed -> rejected
accepted -> deprecated
accepted -> superseded by ADR-NNNN
deprecated -> superseded by ADR-NNNN
```

`rejected` and `superseded` are terminal.

A Wayfinder decision already accepted through an exact CCL proposal may create its ADR directly as `accepted` in the same atomic authority transaction. It does not need a temporary proposed ADR merely to replay an already-completed human semantic gate.

A proposed ADR is still legal for exploratory narrative work, but proposed prose is not accepted CCL authority.

## Accepted Content Immutability

Once accepted, rejected, deprecated, or superseded, historical decision/rationale content is immutable except for narrow Realization Maintenance below.

For a CCL-backed accepted ADR, never manually edit:

* `ccl_proposal`;
* `ccl_transaction`;
* the generated `## Decision` block.

Changing semantic meaning requires a new CCL revision. If that later decision deserves an ADR, create a successor ADR and supersede/deprecate the earlier ADR as appropriate.

Never mutate an old ADR to make history agree with a later contract.

## Reconsidering Decisions

### Rejected direction becomes viable

Create a new ADR referencing the rejection and explain what changed. The rejected ADR remains historical.

### Accepted decision is replaced

Create the successor decision/CCL revision first. Create the successor ADR when qualified, then transition the old ADR to:

```text
superseded by ADR-NNNN
```

### Accepted decision is retired without replacement

Use:

```text
deprecated
```

Retiring CCL semantics remains owned by `$contract-ledger`; ADR status alone does not rewrite CCL history.

## Realization Maintenance

An accepted realization-required ADR may receive narrow maintenance after current-state evidence establishes implementation realization.

Permitted maintenance is limited to explanatory realization/reference wording that does not alter semantic meaning.

For a CCL-backed ADR, Realization Maintenance must never alter its CCL frontmatter or generated Decision block.

Do not use Realization Maintenance to:

* change Context/Rationale trade-offs;
* add or remove semantic requirements;
* reinterpret the historical contract through later implementation;
* mark ambiguous/partial realization complete;
* change ADR status except through the normal lifecycle.

After Realization Maintenance, invoke `$wiki-sync`.

## Numbering

Use globally sequential ADR numbers. Inspect `docs/adr/` and increment the highest numeric prefix.

## Naming

Apply `wiki/_schema.md` naming rules.

With an active entity registry:

```text
000X-<entity-id>-<slug>.md
```

For genuinely cross-cutting architecture:

```text
000X-platform-<slug>.md
```

Before wiki bootstrap:

```text
000X-<slug>.md
```

Do not invent entity IDs.

## Living Entity Wiki Synchronization

If the Living Entity Wiki exists, invoke `$wiki-sync` after:

* creating an ADR;
* substantively editing a proposed ADR;
* applying allowed Realization Maintenance;
* changing ADR status.

For CCL-backed ADRs, pass both the ADR path and linked CCL transaction/contract identities so derived knowledge can preserve exact semantic provenance.

`$wiki-sync` owns derived entity consequences and source-conflict reporting. It must not rewrite CCL or historical ADR semantics to force agreement.

## Parent-owned Atomic Contribution

When invoked by `$wayfinder` or another authorized parent that already owns an isolated canonical-main authority transaction:

1. consume the exact accepted CCL transaction contributed by `$contract-ledger`;
2. create/update only the qualified ADR paths;
3. generate the Decision section through `scripts/ccl_adr.py`;
4. run `check-adr` before returning;
5. invoke required `$wiki-sync` composition as prescribed;
6. do not commit or push independently.

Return the exact ADR paths and projection-check result to the parent.

## Standalone Commit Ownership

When not inside another workflow, follow the repository's ordinary persistence policy. `$to-adr-doc` does not require a standalone commit merely because it ran.

## Return Contract

For a CCL-backed ADR:

```text
ADR: CREATED | UPDATED | UNCHANGED
Path: <docs/adr/...>
Status: accepted
CCL proposal: <sha256:...>
CCL transaction: <contracts/ccl/transactions/...>
CCL projection check: PASS
Wiki sync: <result | not-applicable>
```

For legacy lifecycle maintenance, report the ordinary ADR path/status transition and any wiki-sync result.

## Out of Scope

`$to-adr-doc` does not:

* make the semantic decision;
* create/revise CCL semantics;
* choose between conflicting authorities;
* write Specs or tickets;
* independently determine implementation realization;
* classify/move non-ADR documents.

Those responsibilities remain with their owning workflows.
