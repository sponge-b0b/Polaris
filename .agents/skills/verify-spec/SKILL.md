---
name: verify-spec
description: Perform authorized Spec-wide integration verification and repairs, then obtain fresh independent semantic certification before persisting a passing receipt for the exact final HEAD.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Global Specification Integration & Verification

Verify a completed Spec as one integrated acceptance universe and record a passing receipt only after a fresh independent `$verify-spec-closure` certifier proves the exact stable HEAD.

This `SKILL.md` is the single authoritative procedure for `$verify-spec`. The preserved integration/gate/repair/finalization procedure later in this file remains normative except where the semantic-certification hardening immediately below explicitly supersedes parent-authored semantic PASS.

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

Follow the procedure below through deterministic/delegated gates, acceptance tests, observed-failure disposition, and all actionable Spec-owned repairs.

At the point where older wording below would establish semantic proof itself:

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
4. repair every actionable Spec-owned finding through the normal procedure and required owner skills;
5. rerun only invalidated gates/tests/failure dispositions;
6. refresh exact-HEAD `$spec-contract` bindings;
7. obtain another fresh semantic certification for the new stable candidate.

Do not drop a prior semantic failure merely because a narrower rerun passes. It remains current until the exact falsifier/claim is re-proven or explicitly superseded by authoritative contract change.

If a finding requires a new durable architecture decision, use the architecture-remediation handoff below; the certifier does not invent that decision.

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

After valid independent PASS, construct the compact `PROOFS_INPUT` required below **from the certifier's returned coverage**, not from parent-authored semantic conclusions.

The parent may mechanically group cells only when the certifier returned the same state and same supporting evidence for those cells. It must not broaden the certifier's entailment claim while compacting the receipt.

`GATES_INPUT` remains parent-owned and follows the procedure below.

Then execute the unchanged finalization and receipt persistence mechanics.

The receipt should identify the semantic certification owner/result concisely, for example in a gate/evidence line:

```text
Independent semantic closure: PASS — $verify-spec-closure at exact HEAD <sha>; manifest <n>; violated 0; unproven 0; unchecked 0; open nested domains 0
```

Do not serialize private reasoning transcripts.

## Exact-HEAD Invalidation

Any repair that changes repository HEAD invalidates prior semantic certification.

A mutable architecture/tracker authority change that affects a certified cell also invalidates that cell/certification.

Reuse is legal only when a prior independent certifier established an explicit invalidation boundary and deterministic fail-closed delta analysis proves the exact proof remains valid. Otherwise recertify.

The exact-HEAD receipt short-circuit below remains legal only when its independent semantic certification is part of the matching receipt and all mutable revalidation requirements still pass.

## Downstream Boundary

A passing `$verify-spec` result means:

> The exact integrated Spec candidate passed deterministic/integration verification and fresh semantic certification against the full Spec contract.

It does not replace `$review-spec`.

The next lifecycle remains the handoff to `$review-spec`, which independently challenges Standards, Spec conformity, architecture, and prior closure confidence.

## Procedure

Verify a completed Spec against its fixed baseline as one integrated acceptance universe. A passing run records a **Spec Verification Receipt** for the exact final `HEAD`; `$review-spec` owns the independent adversarial review that follows.

## Core Invariants

- Recover correctness-critical state from the repository and durable tracker, not prior conversation.
- The `$spec-contract` manifest is the complete acceptance universe.
- Every manifest cell ends `proven`, `not-applicable`, or `unresolved`; any `unresolved` blocks PASS.
- Spec-owned/Mixed surfaces determine repository-standards ownership. Inherited-only unrelated defects are report-only.
- Every observed failure must receive an explicit causal disposition before it can be excluded from PASS.
- A required delegated skill owns its gate procedure and terminal result; the parent may not substitute an ad hoc local implementation.
- Final semantic certification belongs to one fresh `$verify-spec-closure` verifier; the `$verify-spec` parent may prepare evidence but may not self-certify semantic PASS.
- Reason about predicates, falsifiers, authoritative domains, Nested Universe closure, assumptions, and evidence, but do **not** serialize that reasoning merely for bookkeeping.

## Deterministic Utility Boundary

Use:

```text
.agents/skills/verify-spec/scripts/verify_spec_artifacts.py
```

It owns only:

- paginated Spec-comment normalization, canonical Workspace Metadata parsing, and latest-receipt extraction;
- contract/proof/gate final-state assembly from the exact `$spec-contract` handoff;
- compact finalization validation;
- complete manifest-to-proof coverage validation;
- one canonical Verification Hash;
- compact receipt rendering.

Do not recreate those mechanics with ad hoc Python, custom parsers, multi-stage `jq`, or a model-authored final-state wrapper. If the utility cannot represent a required invariant, fix it rather than bypassing it.

## 1. Pin the Fixed Point

Read the complete Spec comment history once:

```bash
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
SPEC_NUMBER=<spec_issue_number>
ARTIFACT_TOOL=.agents/skills/verify-spec/scripts/verify_spec_artifacts.py
SPEC_COMMENTS_FILE=$(mktemp)
SPEC_COMMENTS_SUMMARY=$(mktemp)
CONTRACT_HANDOFF=$(mktemp)

gh api --paginate --slurp \
  -H "X-GitHub-Api-Version: 2026-03-10" \
  "repos/$REPO/issues/$SPEC_NUMBER/comments?per_page=100" \
  > "$SPEC_COMMENTS_FILE"

uv run python "$ARTIFACT_TOOL" comments \
  --input "$SPEC_COMMENTS_FILE" \
  > "$SPEC_COMMENTS_SUMMARY"

BASELINE_COMMIT=$(jq -r '.baseline_commit' "$SPEC_COMMENTS_SUMMARY")
```

The utility recognizes exactly one authoritative baseline source: one comment containing the standalone header `## Workspace Metadata` and exactly this field format:

```text
**Baseline Commit Hash:** <40 lowercase hex SHA>
```

The SHA is not backticked, shortened, uppercased, or decorated. A baseline label in any other comment is informational only and never baseline authority. Missing, duplicate, or malformed Workspace Metadata fails closed. Do not parse or recover a baseline independently.

Do not substitute an unpaginated comment read. This is the invocation's one full comment-history read; do not repeat it after receipt persistence merely to rediscover the comment just posted.

Require:

- current branch `spec-<spec_issue_number>`;
- resolvable `BASELINE_COMMIT`;
- clean worktree.

Capture:

```bash
git diff "$BASELINE_COMMIT"...HEAD
git log "$BASELINE_COMMIT"..HEAD --oneline
```

A tracker-only Spec may have an empty diff only when durable evidence proves no repository mutation was required.

## 2. Build the Contract and Guard Delivery

Invoke `$spec-contract` in `build` mode with the Spec, baseline, branch, current `HEAD`, and `handoff-output = CONTRACT_HANDOFF`. Require `SPEC CONTRACT: VALID`, a non-empty `CONTRACT_HANDOFF`, and retain exactly the returned:

- `SPEC_BODY_HASH` and `SPEC_CONTRACT_HASH`;
- ordered manifest;
- source counts/integrity counts;
- ownership classifications;
- immutable default branch/head.

`$spec-contract` owns serialization of the finalizer-facing contract handoff while the canonical manifest is already in context. Do not independently recreate, pretty-print, copy, or re-key the manifest/source-count payload later in this workflow.

Do not independently refresh or reinterpret default-branch ownership.

Capture Architecture Impact. Unresolved material architecture blocks verification and routes to `$architecture-remediation`.

For a Wayfinder-managed Spec, before substantive verification:

1. require the Spec open and all direct native blockers closed;
2. recover every governing Wayfinder; ambiguity fails closed;
3. invoke `$project-delivery-management` `reconcile`;
4. invoke `$project-delivery-management` `guard <Wayfinder>` for every governor;
5. require at least one `PROJECT DELIVERY GUARD: ALLOWED`.

Do not change focus. Re-run the guard only when mutation may change actionability and immediately before persisting a passing receipt.

## 3. Exact-HEAD Checkpoint

Use only `latest_receipt` from the deterministic comment summary.

A passing receipt may short-circuit immutable work only when it matches the exact current:

- `HEAD`;
- branch;
- baseline;
- `SPEC_BODY_HASH`;
- `SPEC_CONTRACT_HASH`.

Even then, revalidate mutable hierarchy/dependency/focus state, mutable/time-dependent gates, clean worktree, and Project projection. An ancestor receipt never carries proof forward across a changed `HEAD`.

## 4. Classify and Run Fail-Fast Gates

Use `$spec-contract` ownership to classify applicable Code, Tests, Documentation, Agent-skill/workflow, Configuration, CI/automation, Data/schema/migrations, and Tracker-only surfaces.

Every candidate gate is `required`, `not-applicable`, or `unresolved`. Do not run a gate solely because an Inherited-only surface appears in integration history.

Run cheap deterministic gates before semantic proof. When repository content changed:

```bash
git diff --check "$BASELINE_COMMIT"
```

When code quality applies:

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff format --check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> \
  uv run mypy . --explicit-package-bases
```

Never use Ruff `--add-noqa`.

Run the deterministic verifier self-test when this workflow utility is in scope:

```bash
uv run python "$ARTIFACT_TOOL" self-test
```

Invoke the `$wiki-lint` skill when Living Entity Wiki routing applies. Invoke the `$deduplicate-code` skill only when Spec-owned/Mixed work creates a real duplicate-implementation risk; when invoked, both Arid and JSCPD must be visible. Run other deterministic checks only when their artifact classes apply.

Inherited-only unrelated failures are report-only only after **Observed Failure Disposition** below proves that causal classification. Surface ownership alone is not causal evidence.

### Delegated Gate Ownership

When this workflow requires another skill to decide or execute a gate, that child skill owns the procedure and terminal result. The parent must not search for a same-named script, recreate a subset of the child procedure with shell commands, or substitute its own ad hoc audit and then report the delegated gate as passed.

Maintain a working delegated-gate inventory:

```text
Delegated gate: DG-<n>
Owner skill: $<skill>
Applicability: <required | not-applicable>
Execution: <executed | unavailable>
Terminal result: <valid child result | unresolved | not-applicable>
Evidence/reason: <native child-skill result/reference or exact N/A reason>
```

Rules:

- `required` means the exact owner skill must be invoked and its current contract followed;
- `unavailable` leaves the gate `unresolved`; it does not authorize parent substitution;
- `not-applicable` requires the same concrete applicability reason the parent uses for the gate;
- a gate may enter final `GATES_INPUT` as PASS only when the owning skill produced a valid terminal result supporting PASS;
- a delegated gate may not disappear because local commands appeared equivalent or because the parent believes it can reproduce the child skill's checks more cheaply.

Before finalization require:

```text
Delegated gate candidates: <n>
Delegated gate rows: <n>
Unclassified delegated gates: 0
Required delegated gates without valid terminal result: 0
```

### Transcript Discipline

The native command/skill transcript is the execution record. Do **not** echo separate `GATE`, `COMMAND`, `RESULT`, `EXIT`, or `SUMMARY` blocks after commands run.

Successful native output may remain visible. For very large output, capture it to `/tmp` and surface only the useful tail/summary while preserving the real command and exit status in the native transcript.

## 5. Acceptance Tests and Service Preflight

Derive the smallest complete pytest scope that directly exercises the Spec acceptance behavior. Every pytest command must set:

```text
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number>
```

Before pytest, perform the exact-scope service preflight from `AGENTS.md` and `docs/process/testing-guide.md`. A timeout, connection failure, or skip is not a preflight. Missing prerequisites leave the check unresolved.

Group test files that share the same service classification/prerequisites into one cohesive invocation. Never expose secrets or authenticated connection strings.

## 6. Prepare Semantic Evidence

After deterministic gates and required tests pass, prepare concise current evidence pointers for every manifest cell for the fresh `$verify-spec-closure` certifier.

Prefer, in order:

1. exact implementation/config/document/tracker inspection;
2. already-executed gate/test evidence;
3. narrow searches needed to expose relevant domain members;
4. CodeGraph/transitive exploration only when direct evidence cannot establish the required call-path or blast-radius evidence cheaply.

For each cell preserve every material clause, quantifier, condition, exception, and named surface in the handoff. The parent must not turn these pointers into its own semantic `proven`/`not-applicable` verdict. The fresh certifier independently derives falsifiers, closes authoritative and nested domains, evaluates assumptions, and decides semantic state.

Parent-prepared evidence may be grouped only when the same evidence genuinely applies to every mapped claim. Passing tests, examples, or targeted searches remain evidence pointers, not semantic certification.

## 7. Failure and Repair

Every failure observed from a required deterministic gate, delegated gate, service preflight, acceptance-test invocation, or independent semantic certification enters the working **Observed Failure Disposition** universe immediately. A later narrower rerun does not erase the earlier observation.

For every observed failure record:

```text
Failure: VF-<n>
Origin: <gate/test/preflight/delegated-skill/certifier identity>
Observed failure: <concise exact failure>
Affected contract/behavior: <boundary or obligation implicated>
Disposition: <spec-owned | inherited-unrelated | unresolved>
Witness: <independently checkable causal evidence>
```

Disposition rules:

- `spec-owned` covers a failed Spec obligation or Spec-owned/Mixed repository-standard/tooling failure and requires repair;
- `inherited-unrelated` is report-only, but requires evidence that the failure is causally independent of the Spec change; ownership classification alone is insufficient;
- valid independence witnesses include deterministic reproduction at the immutable baseline, deterministic delta analysis excluding interaction with the Spec change, or fresh non-mutating semantic certification when causal independence is not mechanically decidable;
- `unresolved` blocks PASS;
- a failure may not disappear because the verifier narrows a later command, removes a failing file from a selected test set, calls the surface inherited, or obtains a passing rerun over a smaller universe.

Before finalization require:

```text
Observed failures: <n>
Failure disposition rows: <n>
Undispositioned failures: 0
Unresolved failures: 0
Spec-owned failures remaining: 0
Inherited exclusions without sufficient witness: 0
```

When no failure was observed, record `Observed failures: 0`; do not manufacture rows.

Repair only Spec-owned failures, at the narrowest authoritative point. Use the owning skill where required (`$wiki-sync`, `$to-doc`, `$classify-doc`, `$to-adr-doc`, etc.). A fix that requires choosing/changing a durable architecture invariant routes to `$architecture-remediation`; do not invent the decision locally.

After a repair:

1. rerun only invalidated gates/tests/evidence;
2. update the affected failure dispositions rather than deleting prior observed-failure rows;
3. refresh only affected evidence pointers;
4. require a fresh `$verify-spec-closure` certification for the new stable candidate unless an independently certified invalidation boundary proves reuse safe;
5. rerun mutable guards invalidated by the change.

If verification changes the repository, verify branch, stage only verification-owned files, invoke `$conventional-commits`, commit, push, then refresh exact-HEAD contract bindings and affected evidence. Do not preserve proof across uncertain mutation.

## 8. Finalize Once

At stable candidate `HEAD`, after valid `SPEC CLOSURE: PASS`:

1. rerun `$spec-contract` in `build` mode with the same `handoff-output = CONTRACT_HANDOFF`, replacing the handoff only after the refreshed contract is valid;
2. require valid body/contract and reconciled ownership;
3. require every applicable gate PASS or NOT APPLICABLE;
4. require Delegated Gate Ownership closure complete;
5. require Observed Failure Disposition closure complete;
6. require the certifier coverage to map every manifest cell to `proven` or valid originating-Spec `not-applicable` with `violated=0`, `unproven=0`, and `unchecked=0`;
7. require current hierarchy/dependency state valid;
8. require clean worktree.

Create only the two genuinely verification-owned compact arrays:

```text
PROOFS_INPUT = [<proof groups derived from certifier-returned coverage>]
GATES_INPUT = [<gate outcomes>]
```

Rules:

- do not copy the manifest, source counts, hashes, baseline, branch, `HEAD`, or default ownership point into another wrapper; those already exist in `CONTRACT_HANDOFF`;
- proofs contain only `cells`, `state`, and `evidence` or `reason`, preserving the certifier's actual entailment result;
- gates contain only `name`, `status`, and concise native `evidence`; commands are already in the transcript;
- include closure outcomes for delegated-gate ownership, observed-failure disposition, and independent semantic closure when applicable, with their required counts in concise gate evidence;
- serialize the two arrays compactly; do not pretty-print them merely for bookkeeping;
- do not create `FINALIZE_INPUT`, a giant intermediate packet, or a second final-state object.

Run one deterministic assembly/finalization operation:

```bash
PROOFS_INPUT=$(mktemp)
GATES_INPUT=$(mktemp)
RECEIPT_FILE=$(mktemp)

uv run python "$ARTIFACT_TOOL" finalize-parts \
  --contract-input "$CONTRACT_HANDOFF" \
  --proofs-input "$PROOFS_INPUT" \
  --gates-input "$GATES_INPUT" \
  --mode <full|checkpoint> \
  --receipt-output "$RECEIPT_FILE" \
  [--prior-checkpoint <checkpoint>] \
  [--repair <repair>]... \
  [--inherited-finding <finding>]...
```

`finalize-parts` assembles the already-owned contract/proof/gate pieces, validates bindings/coverage/gates through the same canonical finalizer, rejects unresolved cells, computes one Verification Hash, and renders the receipt. There is no model-authored wrapper, separate packet admission, final-state validation, receipt rendering, or pre-persistence receipt-validation phase.

## 9. Persist the Compact Receipt

The receipt is a checkpoint/binding record, not a transcript of semantic reasoning. It retains the manifest/source counts needed by `$review-spec`, compact derived coverage, gate outcomes, repairs, inherited findings, and one Verification Hash. It omits proof prose, proof hashes, duplicate coverage structures, and commands already visible in the transcript.

Immediately before persistence, invoke `$project-delivery-management` `guard <Wayfinder>` again for the already-resolved governing Wayfinders. This is revalidation, not a second delivery-analysis phase: do not explicitly invoke another `reconcile`, rediscover lineage, inspect Project schema, or repeat broader frontier analysis before the guard unless repository/tracker mutation since the prior guard invalidated those inputs. The guard remains authoritative for its own canonical reads and any reconciliation it requires.

Then persist exactly once:

```bash
RECEIPT_JSON=$(mktemp)
COMMENT_JSON=$(mktemp)
READBACK_FILE=$(mktemp)

jq -Rs '{body: .}' "$RECEIPT_FILE" > "$RECEIPT_JSON"

gh api --method POST \
  "repos/$REPO/issues/$SPEC_NUMBER/comments" \
  --input "$RECEIPT_JSON" \
  > "$COMMENT_JSON"

COMMENT_ID=$(jq -r .id "$COMMENT_JSON")
COMMENT_URL=$(jq -r .html_url "$COMMENT_JSON")
[ -n "$COMMENT_ID" ] && [ "$COMMENT_ID" != "null" ]

gh api "repos/$REPO/issues/comments/$COMMENT_ID" \
  | jq -j '.body' > "$READBACK_FILE"

cmp -s "$RECEIPT_FILE" "$READBACK_FILE"
```

Exact byte equality proves persisted-body integrity because only a successful canonical finalization can produce the local receipt. `COMMENT_ID` plus successful exact readback is also sufficient proof that this invocation's receipt is durably persisted; do not reread the full paginated Spec comment history or rerun the comment-summary utility afterward merely to prove the newly posted receipt is latest.

Never patch a malformed persisted receipt or create a second corrective receipt in the same invocation. If POST succeeds but readback differs, report `COMMENT_URL` and stop. Any later Spec-body change or candidate commit makes the receipt stale.

## 10. Lifecycle Transition and Project Reconciliation

A successfully persisted receipt establishes:

```text
Artifact Type: Spec
Workflow State: Ready to Review
Work Status: Ready
Next Skill: $review-spec
Root Blocker: None
Completed On: None
```

Immediately invoke `$project-tracking` with that base projection. Recover Project Delivery State after receipt persistence; preserve `Area` and `Priority` unless separately authorized. `PROJECT TRACKING: DRIFT` does not invalidate the receipt or roll back `Ready to Review`.

## 11. Human Handoff

Report concisely:

- baseline/final `HEAD` and verification mode;
- Spec contract count/hash;
- applicable gate results;
- coverage summary;
- proof-group count and Verification Hash;
- repairs and unrelated inherited findings;
- commit/push/final worktree;
- receipt URL;
- Project reconciliation result.

On success:

> ✅ **Spec verification passed.**
>
> Please run:
>
> ```
> $review-spec - <Spec Title> (<Spec URL>)
> ```

Then stop. Do not invoke `$review-spec` implicitly.
