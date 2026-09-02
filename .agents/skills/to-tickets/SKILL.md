---
name: to-tickets
description: Break an explicit plan, Spec, review, or other invocation source into tracer-bullet tickets while proving exhaustive Spec-obligation disposition before fresh Spec ticket publication.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Tickets

Create tracer-bullet tickets using the existing publication workflow, with one added hard boundary for fresh Spec decomposition: **every authoritative Spec contract cell must receive an explicit ticketing disposition before publication.**

## Base Procedure

Read this file first, then read in full:

```text
.agents/skills/to-tickets/procedure.md
```

The base procedure remains normative for session recovery, project-delivery guards, codebase exploration, mode routing, `$to-remediation-tickets`, vertical slicing, user approval, Spec Branch Rule, tracker publication, native hierarchy/dependencies, ticket baseline/branch semantics, Project reconciliation, and handoff.

This file adds the fresh-Spec obligation-coverage gate and extends the ordinary ticket template with exact Spec provenance. On conflict, this file wins.

The remediation path remains owned by `$to-remediation-tickets`; do not replace its Root Blocker delta contract with the fresh-Spec mapping below.

## Fresh Spec Contract Coverage

For a fresh Spec that does not already have linked implementation tickets, the authoritative decomposition universe is the deterministic `$spec-contract` manifest.

Do not define ticket completeness from the obligations noticed during drafting.

### Recover the manifest

Use `$spec-contract` with the exact Spec, branch/baseline/HEAD state required by that skill.

If the Spec Branch Rule has not yet established the durable branch/baseline needed to build the final contract, drafting may begin from the full Spec body, but **publication may not occur** until:

1. the complete Spec Branch Rule has succeeded;
2. `$spec-contract` returns `SPEC CONTRACT: VALID` for the publication state;
3. the proposed ticket breakdown is reconciled against that exact manifest;
4. any semantic change required by that reconciliation is returned to the user approval step rather than silently added during publication.

Retain the exact Spec body hash and contract hash returned by `$spec-contract` for the coverage artifact.

## Spec Obligation Disposition Manifest

Create exactly one row for every Spec contract cell:

```text
Spec obligation: <US-* | ID-* | TD-* | OOS-* | other stable ID>
Requirement: <compact exact requirement>
Disposition: implementation-ticket | verification-only | no-implementation-work | authoritative-exclusion
Tickets: <one or more proposed ticket IDs/titles | None>
Reason/authority: <required for non-ticket dispositions>
```

Rules:

* `implementation-ticket` means one or more tickets carry responsibility to realize the obligation;
* `verification-only` means no new implementation is promised, but later verification must explicitly prove the obligation; state why implementation is unnecessary;
* `no-implementation-work` requires current evidence/authority that the Spec requirement is already realized or needs no repository/tracker mutation; convenience is insufficient;
* `authoritative-exclusion` requires an explicit Spec exclusion/out-of-scope authority and does not mean the requirement was forgotten;
* one Spec cell may map to multiple tickets when the contract genuinely spans slices;
* a ticket may carry multiple Spec cells;
* do not merge distinct Spec cells merely because one implementation change may satisfy them;
* omission is never a disposition.

Before user approval require:

```text
Spec contract cells: <n>
Disposition rows: <n>
Unmapped cells: 0
Ambiguous cells: 0
Unclassified cells: 0
Implementation cells without ticket coverage: 0
Non-ticket dispositions without reason/authority: 0
```

If reconciliation changes ticket scope, acceptance criteria, blocking edges, or disposition semantics, update the proposal and request approval again under the base procedure.

## Ticket Provenance

Every ordinary Implementation Ticket created from a Spec must contain:

```markdown
## Spec obligations

<comma-separated stable Spec contract IDs, or `None` only when the disposition manifest proves this ticket is intentionally supporting/mechanical work with no direct Spec cell>
```

The IDs are exact provenance, not a replacement for good ticket acceptance criteria.

The ticket must still describe the end-to-end behavior it delivers and carry acceptance criteria sufficient to implement its slice.

When a ticket supports another ticket mechanically without directly realizing a Spec cell, `Spec obligations: None` requires an explicit row/reason in the coverage manifest showing why the supporting ticket exists and which covered ticket(s) depend on it.

Do not infer Spec obligation IDs later from changed files or implementation notes.

## Parent Coverage Artifact

After publishing the approved fresh ticket set and native relationships, persist one durable machine-readable-enough coverage record on the parent Spec.

Use one comment headed:

```text
## Ticket Coverage Manifest
```

Include:

```text
Spec Body Hash: <hash>
Spec Contract Hash: <hash>
Spec branch: <branch>

<Cell ID> → <implementation ticket(s) | verification-only | no-implementation-work | authoritative-exclusion> — <reason when required>
...

Spec contract cells: <n>
Mapped: <n>
Unmapped: 0
Ambiguous: 0
```

Persist it once per approved decomposition state. If ticket semantics are later changed through an authorized workflow, that owner must supersede/reconcile the manifest rather than leaving contradictory active coverage records.

The manifest is provenance and coverage authority for decomposition. It is **not** proof that a ticket implementation later passed.

## Publication Integrity

Immediately before Step 5 publication, require all of the following together:

* base Spec Branch Rule passed;
* exact approved ticket proposal still matches planned semantics;
* `$spec-contract` manifest still matches retained body/contract hashes;
* Spec Obligation Disposition Manifest is complete;
* every ticket's `Spec obligations` set equals its approved mapping;
* blocking edges/hierarchy still match the approved proposal.

A changed Spec body/contract invalidates the mapping and returns to drafting/approval.

Do not publish tickets and promise to reconcile the coverage manifest afterward.

## Downstream Contract

The durable chain is:

```text
Spec contract cell
    ↓
Ticket Coverage Manifest
    ↓
Implementation Ticket `Spec obligations`
    ↓
$implement-ticket Proposed Closure Evidence
    ↓
independent $verify-ticket-closure certification
    ↓
$verify-spec integrated semantic certification
```

Ticket certification does not prove the complete Spec; `$verify-spec` remains responsible for integrated closure.

## Base Template Extension

For ordinary Spec tickets, insert `## Spec obligations` after `## Parent` and before Architecture context / What to build.

For remediation tickets, preserve the base remediation template and Root Blocker contract. When exact originating Spec cell IDs are available from the cumulative remediation state, they may be carried as provenance, but the Root Blocker acceptance universe remains authoritative for remediation.
