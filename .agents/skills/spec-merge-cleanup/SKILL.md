---
name: spec-merge-cleanup
description: Complete one reviewed Spec by validating the exact v2 review state, merging or directly closing the Spec, cleaning branch/review state idempotently, reconciling governing Wayfinders, and rebuilding Project projection from durable lifecycle authority.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Spec Merge & Cleanup

`$spec-merge-cleanup` is the authoritative completion boundary after `$review-spec` PASS.
It consumes the current structured review ledger directly. Historical remediation compatibility fields/markers are not completion authority.

## 1. Recover durable completion inputs

Assume no prior chat/session state.

Recover:

* parent Spec issue and current state;
* exact current Spec body, branch/baseline metadata, and latest passing Spec Verification Receipt;
* exactly one conventional `Spec Review: ...` issue for the Spec;
* exactly one current `review-spec-finding-ledger:v2` comment on that Spec Review;
* latest Spec Review Exit Receipt on that Spec Review;
* current branch/PR state when the Spec is branch-backed;
* current native Spec blockers/dependents;
* every current governing Wayfinder from Spec-local provenance and canonical Wayfinder handoffs;
* current project-delivery state.

Project fields and prior conversation are never lifecycle authority.

If any required identity is missing, duplicated, contradictory, or stale, fail closed and return the owning lifecycle rather than reconstructing intent from prose.

## 2. Validate current review authorization

Build the deterministic current Spec contract and validate the current v2 finding ledger:

```bash
python -m scripts.ccl_spec check <spec-body-file> contracts/ccl/transactions
python -m scripts.spec_contract build <spec-issue-json> <spec-contract.json>
python -m scripts.review_remediation validate-ledger <spec-contract.json> <review-findings.json>
```

Require `SPEC CONTRACT: VALID` and `REVIEW FINDING LEDGER: VALID`.

Hash the exact managed finding-ledger comment body as persisted by `$review-spec`; do not normalize whitespace or otherwise change bytes.

The Exit Receipt must be current and contain:

```markdown
## Spec Review Exit Receipt

**Status:** passed
**Spec Review:** #<review issue>
**Reviewed HEAD:** <full SHA>
**Reviewed Baseline:** <full Spec baseline SHA>
**Branch:** spec-<spec> | None
**Spec Body Hash:** <hash>
**Spec Contract Hash:** <hash>
**Finding Ledger Hash:** <sha256 of exact managed ledger body>
**Blocking findings:** 0
**Open blocking findings:** 0
**Unaccounted prior findings:** 0
**Unresolved continuity cells:** 0
**Unresolved decomposition defects:** 0
**Review coverage:** complete
**Unchecked coverage cells:** 0
```

Require exact agreement with the current Spec baseline, current deterministic contract, current finding-ledger hash, and latest passing Spec Verification Receipt for the same semantic candidate.

Also validate from the v2 ledger that open Blocking findings, cell-routing defects, contract-authority gaps, and planning-cell gaps are all zero.

Do not require, parse, synthesize, or accept historical remediation compatibility fields or legacy finding-ledger markers as current completion state.

### Semantic anchor vs authorized delivery tip

The Exit Receipt's `Reviewed HEAD` is the semantic anchor. Normally it equals the branch tip. A newer tip is admissible only under the repository-wide Non-Semantic Workflow-Policy Synchronization rule in `AGENTS.md`: Reviewed HEAD is an ancestor of the tip, the complete delta is limited to permitted workflow/process surfaces, no product/test/migration/configuration/architecture/Spec/CCL/coverage/finding semantic state changed, and current deterministic validation reproduces the receipt-bound contract identity.

When proven, call the newer tip `AUTHORIZED_DELIVERY_TIP`. Otherwise review authorization is stale and `$review-spec` must run again.

## 3. Detect lifecycle phase before mutation

Use canonical GitHub issue/PR/branch state, not Project state. Classify exactly one:

```text
pre-completion
    Spec is open; authoritative completion has not occurred

post-merge recovery
    Spec is closed by exactly one merged spec-<n> PR whose recorded head is the AUTHORIZED_DELIVERY_TIP; merge commit is reachable from current main; any remaining local/remote Spec branch still points to that exact tip

post-direct-close recovery
    branchless Spec is closed and carries this workflow's durable direct-close completion evidence; no Spec branch/merge PR exists
```

A closed Spec that cannot prove one recovery mode is ambiguous. Fail closed; never reopen or infer how it completed.

## 4. Project-delivery actionability for a new completion transition

Run this section only for `pre-completion`. Independent Specs remain independent.

For every Wayfinder-managed Spec, require the Spec open and native Spec blockers closed, recover every current governor, invoke `$project-delivery-management reconcile`, invoke `guard <Wayfinder>` for each governor, and require at least one exact `PROJECT DELIVERY GUARD: ALLOWED` result.

This workflow never establishes, switches, or broadens project focus. Do not re-run the pre-completion focus gate merely to finish a proven post-completion recovery.

## 5. Complete the Spec

### Branchless Spec

When neither local nor remote `spec-<n>` exists and no branch-backed completion is present, revalidate Review Exit Authorization, close the Spec exactly once with the canonical direct-close completion comment, re-read and require `CLOSED`, then continue to Review cleanup, Wayfinder reconciliation, project-delivery reconciliation, and Project reconstruction.

A rerun after that transition uses `post-direct-close recovery`; never close again.

### Branch-backed Spec

For `pre-completion`, require the branch tip equals `AUTHORIZED_DELIVERY_TIP`, push without force, reuse the one open PR from `spec-<n>` to `main` or create it idempotently with `Closes #<spec>`, require the PR head SHA equals the authorized tip, merge with a regular merge commit rather than squash, and require PR state `MERGED`, Spec state closed, and the merge commit reachable from `main`.

Do not delete the branch as part of the merge operation. Any failure after the merge transition is cleanup drift; the next invocation must prove `post-merge recovery` and resume.

## 6. Branch cleanup is idempotent and fail-closed

For branch-backed completion or post-merge recovery, sync `main` with fast-forward-only semantics, require the matching merge commit reachable from `main`, require `Reviewed HEAD` to be an ancestor of `main`, and delete local/remote Spec branches only when their current tips equal `AUTHORIZED_DELIVERY_TIP`. Never force-delete a drifted branch.

A branch tip that moved after the reviewed merge is a Hard Blocker for cleanup only. It does not roll back the already completed Spec.

## 7. Close the conventional Spec Review

After authoritative Spec completion is proven, close the conventional Spec Review if it is still open. If already closed, treat it as an idempotent no-op.

The v2 finding ledger and Exit Receipt remain historical completion evidence on the closed review issue. Do not rewrite them during cleanup.

### Best-effort Workflow Invocation Journal GC

After authoritative Spec completion is proven, perform best-effort cleanup of disposable
Workflow Invocation Journals whose exact immutable `lifecycle_scope` is this Spec. The
canonical WIJ contract is `.agents/skills/WORKFLOW_INVOCATION_JOURNAL.md`.

Run:

```bash
python -m scripts.workflow_journal gc \
  --lifecycle-scope-url <canonical Spec issue URL>
```

`WORKFLOW JOURNAL GC: COMPLETE` is the ordinary result. `WORKFLOW JOURNAL GC: DEGRADED`, a
missing helper, unreadable journal storage, or any other WIJ cleanup failure is report-only
cleanup degradation: continue the authoritative Spec-completion workflow without rollback,
without reopening any lifecycle artifact, and without restoring a deleted Spec branch.

GC may remove terminal or nonterminal journals for the completed Spec. It matches exact
`lifecycle_scope` identity, never branch-name inference. Independent clones outside the
repository's Git common directory remain outside this cleanup boundary and disappear with
their clone.

## 8. Reconcile every governing Wayfinder

Spec closure is the native dependency-completion boundary; do not write a second synthetic satisfaction marker.

For every current governing Wayfinder build one working completion record with the complete governed Spec set, open Wayfinder decisions, unresolved in-scope fog, governance ambiguity, and a disposition of `complete | remain-open | ambiguous`.

`complete` requires all currently governed Derived/Remediation Specs closed, zero open Wayfinder decisions, zero unresolved in-scope fog, and no governance ambiguity. Persist one idempotent completion comment and close the Wayfinder if still open. `remain-open` leaves it open. `ambiguous` leaves it untouched and reports reconciliation drift.

After all unambiguous map transitions, invoke `$project-delivery-management reconcile`. A completed/ineligible map must leave focus; reconciliation never auto-selects a replacement.

## 9. Reconstruct Project projection once

Project is an eventually consistent projection, not lifecycle authority.

After Spec completion, Review cleanup, Wayfinder reconciliation, dependent actionability, and project-delivery reconciliation are durable, reconstruct one complete Project manifest from authoritative tracker/repository state containing the completed parent Spec, all native Implementation Ticket children, the conventional Spec Review, all native Review Remediation Ticket children, all current governing Wayfinders, required Wayfinder Decision children needed for complete lineage, direct dependent Specs whose actionability changed, and any additional formal artifact required for internal consistency.

For each artifact derive current lifecycle projection from owning durable authority: issue hierarchy/dependencies, deterministic contract/coverage state, ticket closure receipts, Spec Verification/Review receipts, Wayfinder state, project-delivery state, and explicit supersession/retirement authority.

Do not use historical remediation compatibility state or current Project rows to derive lifecycle truth. Recover terminal completion dates from lifecycle-authoritative completion evidence, not merely issue `closed_at`.

Invoke `$project-tracking` exactly once with the complete reconstructed projection set and preserve Area/Priority unless separately authorized.

If projection fails after lifecycle completion, report `PROJECT TRACKING: DRIFT`. Do not reopen lifecycle artifacts or restore branches.

## 10. Completion criteria

Success requires the current v2 finding ledger to validate against the current deterministic Spec contract; the Exit Receipt to bind the current semantic candidate and ledger hash; zero open Blocking findings/routing defects/contract-planning gaps; exactly one authoritative Spec completion transition or an exact post-completion recovery; closed conventional Spec Review; safe branch cleanup for branch-backed work; an explicit completion disposition for every unambiguously recovered governor; project-delivery reconciliation after completion transitions; and one complete Project reconstruction/projection attempt.

WIJ garbage collection is best-effort housekeeping and is deliberately not a success criterion.
A cleanup failure after authoritative Spec completion never invalidates the completion transition. Resume from durable state and perform only remaining idempotent work.

## Non-goals

`$spec-merge-cleanup` does not interpret review prose into findings, parse historical remediation compatibility receipt fields, consume legacy finding-ledger markers as current state, reopen a completed Spec because cleanup/project projection failed, guess Wayfinder governance, use Project projection as lifecycle authority, force-delete a drifted branch, create semantic requirements, or make WIJ cleanup a prerequisite for completion.
