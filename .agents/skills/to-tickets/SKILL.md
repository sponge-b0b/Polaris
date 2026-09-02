---
name: to-tickets
description: Break an explicit plan, Spec, review, or other invocation source into tracer-bullet tickets while proving exhaustive Spec-obligation disposition and independently certifying proposal readiness before human approval.
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

This file adds the fresh-Spec obligation-coverage gate, independently certified proposal readiness before human approval, and exact Spec provenance on ordinary tickets. On conflict, this file wins.

The remediation path remains owned by `$to-remediation-tickets`; do not replace its Root Blocker delta contract with the fresh-Spec mapping below.

## Human Approval Is Not Verification

The human approval step exists to approve or reject the **substantive decomposition**: ticket granularity, meaningful scope, and product/architecture choices that genuinely require owner judgment.

It is **not** a correctness backstop for `$to-tickets`.

Before the user ever sees a publication proposal, `$to-tickets` owns proving that the proposal already complies with repository ticketing authority, including as applicable:

* authoritative source/root obligation coverage;
* required ticket fields and template semantics;
* direct native parent and durable lineage;
* `Ticket branch` semantics;
* `Ticket baseline` semantics;
* required label/status;
* preservation and verification classification;
* blocking relationships/dependency direction;
* closed-ticket preservation and duplicate prevention;
* publication-state consistency with the exact source contract.

Do not ask the user to validate, repair, or reconstruct those mechanics.

An unqualified `approve`, `approved`, `yes`, or equivalent after a certified proposal is presented authorizes publication of that exact proposal. The user does not need to restate its metadata, prove its coverage, or independently verify repository policy.

If a genuine unresolved product, architecture, or decomposition choice remains, surface that specific choice. Do not disguise an internal ticket-construction or policy-validation failure as a human design decision.

## Proposal Readiness Certification

Before the base procedure's Step 4 approval prompt for any non-metadata-only proposal, freeze the exact proposed ticket set and obtain one **fresh, non-mutating proposal-readiness certification**.

The drafting parent may construct and revise the proposal, but it may not certify its own proposal readiness.

### Freeze the candidate

Render the exact proposal that would be shown to the user, including every proposed new/update/close action, ticket body semantics, hierarchy, dependencies, branch/baseline metadata, labels/status, and mode-specific coverage summary.

Bind the candidate to:

```text
Source artifact: <durable identity>
Ticket mode: fresh | remediation
Source contract/root state: <durable identity/hash where available>
Proposal identity: <SHA-256 of the exact rendered proposal candidate>
```

Any semantic or metadata change after certification invalidates the readiness result and requires certification of the new candidate before it is shown for approval.

### Fresh certifier

Dispatch exactly one genuinely fresh subagent that did not draft, reconcile, or transform the proposal.

The certifier is:

* non-mutating;
* non-delegating for semantic proposal certification;
* proposal-bound;
* source-bound;
* independent of the drafting parent's readiness conclusions.

Give it the exact frozen proposal plus authoritative durable inputs. Do not give it a parent-authored claim that the proposal is complete as authority.

The certifier independently validates the proposal against the current `$to-tickets` base procedure, this overlay, and the mode-specific authority below.

### Authoritative proposal universe

For a **fresh Spec** proposal, independently validate against:

* the exact deterministic `$spec-contract` manifest;
* the Spec Obligation Disposition Manifest;
* the proposed ticket `Spec obligations` mappings;
* the applicable parent Spec, branch, and workspace metadata.

For a **Spec Review remediation** proposal, independently validate against:

* the exact remediation parent Spec Review;
* the parent Spec provenance;
* every current unresolved/regressed Root Blocker and active cumulative acceptance cell;
* the complete remediation / verification / preservation partition;
* current existing-ticket lineage and closed/open state;
* the Root Delta Coverage returned under `$to-remediation-tickets` authority.

The certifier must not define completeness from what the proposal happened to mention.

### Required readiness checks

A proposal may PASS only when all applicable checks are independently established:

```text
Source obligations/root cells complete: yes
Proposal coverage complete: yes
Missing obligations/cells: 0
Ambiguous dispositions: 0
Unclassified dispositions: 0
Required remediation without ticket coverage: 0
Required preservation omitted: 0
Required verification omitted/misclassified: 0
Template/required fields valid: yes
Native parent/lineage valid: yes
Ticket branch semantics valid: yes
Ticket baseline semantics valid: yes
Label/status semantics valid: yes
Dependencies/blocking edges internally valid: yes
Closed tickets reopened/rewritten: 0
Duplicate/conflicting active ticket coverage: 0
Unresolved repository-policy conflicts: 0
```

For new tickets, explicitly enforce the repository baseline distinction:

* `Ticket baseline: Pending` is the required **per-ticket implementation anchor** at publication;
* `$implement-ticket` later pins that ticket baseline to the exact pre-mutation HEAD;
* the fixed parent **Spec baseline is separate provenance** and must never replace a new ticket's `Ticket baseline: Pending` field.

Do not treat `Pending` as proposal shorthand.

### Verdict

Return exactly one result for the frozen proposal.

PASS:

```text
TICKET PROPOSAL READINESS: PASS
Source: <identity>
Mode: fresh | remediation
Proposal identity: <sha256>
Coverage: <n>/<n>; missing 0; ambiguous 0; unclassified 0
Mechanics: template/lineage/branch/baseline/status/dependencies valid
Repository-policy conflicts: 0
Human verification required: no
```

FAIL:

```text
TICKET PROPOSAL READINESS: FAIL
Source: <identity>
Mode: fresh | remediation
Proposal identity: <sha256>
Findings:
1. <exact violated authority / affected proposal element / required correction>
...
```

The certifier does not repair the proposal.

### Parent handling

On FAIL, the drafting parent corrects every resolvable ticket-construction defect and certifies the revised frozen proposal again **before showing it to the user**.

Do not expose intermediate invalid proposals merely to ask the user to act as `$to-tickets` verifier.

Only surface a blocker to the user when authoritative sources genuinely leave a substantive owner decision unresolved. Mechanical/template/lifecycle errors are `$to-tickets` responsibilities.

After PASS, present the certified proposal and include one compact line:

```text
Proposal readiness: independently certified; repository-policy verification is complete.
```

Then request substantive approval. Prefer the minimal close:

> **Reply `approve` to publish exactly as proposed.** Otherwise, tell me any substantive change you want.

Do not require the user to answer separate questions about branch/baseline correctness, template compliance, root-cell accounting, labels/status, hierarchy, or dependency mechanics.

If the user requests a substantive proposal change, freeze and certify the revised candidate before requesting approval again.

If the user requests a purely mechanical change that conflicts with authoritative repository policy, preserve the authoritative repository semantics and explain the conflict. Do not ask the user to reconstruct the correct mechanical value. Request renewed approval only when the resulting proposal changes substantive ticket scope, acceptance obligations, preservation obligations, or blocking/dependency semantics.

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
* the latest `TICKET PROPOSAL READINESS: PASS` binds to the exact approved proposal identity and current source state;
* `$spec-contract` manifest still matches retained body/contract hashes when applicable;
* Spec Obligation Disposition Manifest is complete when applicable;
* every ticket's `Spec obligations` set equals its approved mapping when applicable;
* blocking edges/hierarchy still match the approved proposal.

A changed proposal, source contract/root state, branch/baseline authority, or Spec body/contract invalidates readiness and returns to drafting/certification/approval as applicable.

Do not publish tickets and promise to reconcile the coverage manifest or proposal correctness afterward.

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
