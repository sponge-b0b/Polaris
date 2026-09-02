---
name: verify-spec
description: Perform authorized Spec-wide integration verification and repairs, then obtain fresh independent semantic certification before persisting a passing receipt for the exact final HEAD.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Global Specification Integration & Verification

Verify a completed Spec as one integrated acceptance universe and record a passing receipt only after a fresh independent `$verify-spec-closure` certifier proves the exact stable HEAD.

## Base Procedure

Read this file first, then read in full:

```text
.agents/skills/verify-spec/procedure.md
```

The base procedure remains normative for fixed-point recovery, `$spec-contract`, ownership, delivery guards, deterministic/delegated gates, service preflight, acceptance tests, observed-failure disposition, Spec-owned repair, exact-HEAD handling, finalizer mechanics, receipt persistence, Project reconciliation, and handoff.

This file supersedes only the base rule that the `$verify-spec` parent may own its own final semantic proof, plus the portions of **Establish Semantic Proof** and **Finalize Once** that derive semantic PASS from parent-authored proof conclusions.

On conflict, this file wins.

## Separation of Authority

The `$verify-spec` parent owns:

* deterministic Spec Contract construction;
* ownership classification;
* delivery/actionability guards;
* deterministic and delegated gate execution;
* acceptance-test execution and service preflight;
* observed-failure disposition;
* Spec-owned repair;
* stabilizing the exact candidate HEAD;
* deterministic receipt assembly/persistence after certification.

The parent does **not** own final semantic certification of the candidate it has just verified/repaired.

A genuinely fresh non-mutating `$verify-spec-closure` subagent owns:

* per-manifest-cell semantic entailment;
* authoritative/nested domain closure;
* falsifier exclusion;
* production-composition proof where required by the claim;
* negative/fail-closed semantic proof;
* one `SPEC CLOSURE: PASS | FAIL` for the exact stable HEAD.

`$review-spec` remains the later independent adversarial Standards / Spec / Architecture review. Do not duplicate its multi-axis review, root reconciliation, or challenge/saturation procedure here.

## Semantic Candidate Gate

Follow the base procedure through deterministic/delegated gates, acceptance tests, observed-failure disposition, and all actionable Spec-owned repairs.

At the point where the base procedure would establish semantic proof itself:

1. finish all parent-owned gates and failure disposition;
2. require a clean worktree;
3. pin exact `BASELINE_COMMIT`, branch, current `HEAD`, Spec body hash, Spec contract hash, current ownership, architecture impact, and native gate/test evidence;
4. rebuild/refresh the `$spec-contract` handoff if prior repair changed HEAD;
5. treat that exact state as the immutable semantic-certification candidate.

The parent may prepare **evidence pointers** for each manifest cell, but it must not mark the semantic cell proven/not-applicable from its own judgment.

## Fresh Spec Certifier Dispatch

The existing human invocation of `$verify-spec` authorizes semantic certification; no second human handoff is required.

At stable candidate HEAD, the parent enters dispatcher-only mode for semantic certification.

It may only:

1. capture the exact candidate bindings;
2. spawn exactly one genuinely fresh verifier subagent;
3. pass:
   * Spec issue/body identity;
   * exact baseline/branch/HEAD;
   * deterministic `$spec-contract` handoff/manifest and hashes;
   * ownership classifications;
   * applicable current architecture authority/context;
   * native deterministic/delegated gate results;
   * acceptance-test/preflight evidence;
   * observed-failure disposition state;
   * concise evidence pointers collected by the parent;
4. require that subagent to execute `$verify-spec-closure` as a non-mutating leaf;
5. receive one `SPEC CLOSURE: PASS | FAIL`;
6. re-read exact HEAD/worktree and mutable contract-critical state needed to establish the verifier did not mutate the candidate;
7. consume the verdict without semantic override.

While dispatcher-only, the parent must not perform a parallel semantic proof, search for evidence to overturn the verifier, mutate the candidate, repair findings, or dispatch shadow certifiers/reviewers.

A verifier-integrity failure invalidates the attempt and must be resolved before certification can continue.

## Certifier Proof Contract

`$verify-spec-closure` independently certifies every manifest cell from the exact authoritative claim.

The following are hard PASS requirements:

* exact evidence entailment per cell;
* no broad proof object silently certifies materially heterogeneous claims;
* every finite/discoverable nested quantified domain is closed;
* production-path claims reach canonical composition, not merely component capability;
* negative/fail-closed claims receive meaningful adversarial falsifier proof;
* every material assumption bridging evidence to conclusion is proven;
* `violated=0`, `unproven=0`, `unchecked=0`;
* no open nested-domain candidate remains.

Passing parent tests/gates remain evidence of what they actually establish. They are not semantic proof of unrelated or stronger claims.

## FAIL Loop

`SPEC CLOSURE: FAIL` is non-terminal and does not authorize a Spec Verification Receipt.

After the verifier returns:

1. exit dispatcher-only mode;
2. retain every returned finding as current verification state;
3. classify whether each finding is Spec-owned repair, unresolved architecture, external/environmental blocker, or a deterministic contract defect requiring the owning workflow;
4. repair every actionable Spec-owned finding through the normal base procedure and required owner skills;
5. rerun only invalidated gates/tests/failure dispositions;
6. refresh exact-HEAD `$spec-contract` bindings;
7. obtain another fresh semantic certification for the new stable candidate.

Do not drop a prior semantic failure merely because a narrower rerun passes. It remains current until the exact falsifier/claim is re-proven or explicitly superseded by authoritative contract change.

If a finding requires a new durable architecture decision, use the base architecture-remediation handoff; the certifier does not invent that decision.

## PASS Consumption

Accept `SPEC CLOSURE: PASS` only when:

* Spec/baseline/branch/HEAD/body hash/contract hash match dispatch exactly;
* candidate and required mutable authority did not change unexpectedly during certification;
* certifier was genuinely fresh, non-mutating, and non-delegating;
* every manifest cell is `proven` or valid originating-Spec `not-applicable`;
* no violated/unproven/unchecked cell remains;
* all required nested domains are closed.

The parent may validate identities/counts/hashes mechanically. It may not reinterpret a semantic FAIL into PASS.

## Finalizer Integration

After valid independent PASS, construct the base procedure's compact `PROOFS_INPUT` **from the certifier's returned coverage**, not from parent-authored semantic conclusions.

The parent may mechanically group cells only when the certifier returned the same state and same supporting evidence for those cells. It must not broaden the certifier's entailment claim while compacting the receipt.

`GATES_INPUT` remains parent-owned and follows the base procedure.

Then execute the unchanged base finalization and receipt persistence mechanics.

The receipt should identify the semantic certification owner/result concisely, for example in a gate/evidence line:

```text
Independent semantic closure: PASS — $verify-spec-closure at exact HEAD <sha>; manifest <n>; violated 0; unproven 0; unchecked 0; open nested domains 0
```

Do not serialize private reasoning transcripts.

## Exact-HEAD Invalidation

Any repair that changes repository HEAD invalidates prior semantic certification.

A mutable architecture/tracker authority change that affects a certified cell also invalidates that cell/certification.

Reuse is legal only when a prior independent certifier established an explicit invalidation boundary and deterministic fail-closed delta analysis proves the exact proof remains valid. Otherwise recertify.

The base exact-HEAD receipt short-circuit remains legal only when its independent semantic certification is part of the matching receipt and all base mutable revalidation requirements still pass.

## Downstream Boundary

A passing `$verify-spec` result means:

> The exact integrated Spec candidate passed deterministic/integration verification and fresh semantic certification against the full Spec contract.

It does not replace `$review-spec`.

The next lifecycle remains the base handoff to `$review-spec`, which independently challenges Standards, Spec conformity, architecture, and prior closure confidence.
