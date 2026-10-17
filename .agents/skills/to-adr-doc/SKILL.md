---
name: to-adr-doc
description: Create and manage Architectural Decision Records as rationale/history records whose accepted software semantics project an exact CCL transaction when applicable.
compatibility: product=codex product=claude-code network=none
---

# To ADR Doc

`$to-adr-doc` owns ADR format, numbering, lifecycle, historical immutability, and the
ADR-side projection of accepted Canonical Contract Ledger (CCL) semantics.

ADRs live in `docs/adr/`.

An ADR explains **why** a consequential decision was made. When material software semantics
are represented by CCL, the ADR does not independently restate or reinterpret **what** was
decided.

## Qualification

Create an ADR only when all three are true:

1. hard to reverse — later change has meaningful cost;
2. surprising without context — future contributors could reasonably ask why;
3. real trade-off — meaningful alternatives existed and one was deliberately selected.

Routine implementation choices do not need ADRs.

## CCL-backed accepted ADR

Use for an accepted material software decision whose semantics are represented by an
accepted CCL transaction.

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
<why this contract was chosen over material alternatives>
```

`## Considered Options` and `## Consequences` are optional.

Generate the entire `## Decision` section only with:

```bash
python -m scripts.ccl_adr render-decision <accepted-transaction.json>
```

Then require:

```bash
python -m scripts.ccl_adr check-adr <adr-path> <accepted-transaction.json>
```

Do not add prose inside the generated Decision block.

Context/Rationale/Options/Consequences are explanation/history only. They may not introduce
material requirements, cardinality, vocabulary, ownership, lifecycle, failure, or other
semantics absent from the linked CCL transaction. If explanatory prose reveals a missing
semantic requirement, return to the semantic owner.

## Historical and non-CCL ADRs

Accepted historical ADRs remain immutable history. Do not rewrite them solely because the
current workflow uses CCL.

A genuinely non-semantic architecture record may remain unbacked when no material software
contract is created or changed. Do not use that form to bypass CCL for a material semantic
decision.

## Why Decision is generated

```text
CCL typed assertions = frozen semantic contract
ADR Decision section = deterministic human-readable projection
ADR Context/Rationale = explanation/history
```

The generated projection exists for human readability and durable rationale linkage, not
as a second machine authority. If it does not match the transaction, the ADR is invalid.

## Status lifecycle

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

A Wayfinder decision accepted through an exact CCL proposal may create its ADR directly as
`accepted` in the same authority transaction. A proposed ADR remains legal for exploratory
narrative work, but proposed prose is not accepted CCL authority.

## Accepted-content immutability

Once accepted, rejected, deprecated, or superseded, historical decision/rationale content
is immutable except narrow Realization Maintenance.

For a CCL-backed ADR, never manually edit `ccl_proposal`, `ccl_transaction`, or the
generated `## Decision` block. Semantic change requires a new CCL revision and, when
qualified, a successor ADR. Never mutate old history to make it agree with a later
contract.

## Reconsideration

* rejected direction becomes viable → create a new ADR explaining what changed;
* accepted decision replaced → create successor CCL/ADR, then mark old ADR superseded;
* accepted decision retired without replacement → mark ADR deprecated; CCL retirement
  remains owned by `$contract-ledger`.

## Realization Maintenance

Permitted maintenance is limited to explanatory realization/reference wording that does
not alter semantic meaning. For CCL-backed ADRs it must never alter CCL frontmatter or the
generated Decision block. Invoke `$wiki-sync` after allowed maintenance.

## Numbering and naming

Use globally sequential ADR numbers. Apply `wiki/_schema.md` naming rules. Do not invent
entity IDs.

## Wiki synchronization

If the Living Entity Wiki exists, invoke `$wiki-sync` after ADR creation, substantive edit
of a proposed ADR, allowed Realization Maintenance, or status change.

For CCL-backed ADRs pass the linked CCL transaction/contract identities. `$wiki-sync`
never rewrites CCL or historical ADR semantics to force agreement.

## Parent-owned contribution

When an authorized parent already owns an isolated canonical-main authority transaction,
consume the exact accepted CCL transaction, create/update only qualified ADR paths,
generate/check the Decision projection, invoke required wiki synchronization, and return
without committing independently.

## Return

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

`$to-adr-doc` does not make semantic decisions, create/revise CCL semantics, choose between
conflicting authorities, write Specs/tickets, or independently determine implementation
realization.
