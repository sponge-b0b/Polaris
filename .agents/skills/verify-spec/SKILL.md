---
name: verify-spec
description: Perform authorized Spec-wide verification against a deterministic Spec contract, repair Spec-owned failures, and record a passing receipt for the exact final HEAD.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Global Specification Integration & Verification

Verify a completed Spec against its fixed baseline as one integrated acceptance universe. A passing run records a **Spec Verification Receipt** for the exact final `HEAD`; `$review-spec` owns the independent adversarial review that follows.

## Core Invariants

- Recover correctness-critical state from the repository and durable tracker, not prior conversation.
- The `$spec-contract` manifest is the complete acceptance universe.
- Every manifest cell ends `proven`, `not-applicable`, or `unresolved`; any `unresolved` blocks PASS.
- Spec-owned/Mixed surfaces determine repository-standards ownership. Inherited-only unrelated defects are report-only.
- `$verify-spec` owns semantic proof. Do not spawn proof certifiers or shadow reviewers; `$review-spec` is the independent layer.
- Reason about predicates, falsifiers, authoritative domains, Nested Universe closure, assumptions, and evidence, but do **not** serialize that reasoning merely for bookkeeping.

## Deterministic Utility Boundary

Use:

```text
.agents/skills/verify-spec/scripts/verify_spec_artifacts.py
```

It owns only:

- paginated Spec-comment normalization, canonical Workspace Metadata parsing, and latest-receipt extraction;
- compact finalization validation;
- complete manifest-to-proof coverage validation;
- one canonical Verification Hash;
- compact receipt rendering.

Do not recreate those mechanics with ad hoc Python, custom parsers, or multi-stage `jq`. If the utility cannot represent a required invariant, fix it rather than bypassing it.

## 1. Pin the Fixed Point

Read the complete Spec comment history once:

```bash
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
SPEC_NUMBER=<spec_issue_number>
ARTIFACT_TOOL=.agents/skills/verify-spec/scripts/verify_spec_artifacts.py
SPEC_COMMENTS_FILE=$(mktemp)
SPEC_COMMENTS_SUMMARY=$(mktemp)

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

Do not substitute an unpaginated comment read.

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

Invoke `$spec-contract` in `build` mode with the Spec, baseline, branch, and current `HEAD`. Require `SPEC CONTRACT: VALID` and retain exactly its:

- `SPEC_BODY_HASH` and `SPEC_CONTRACT_HASH`;
- ordered manifest;
- source counts/integrity counts;
- ownership classifications;
- immutable default branch/head.

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

Invoke `$wiki-lint` when Living Entity Wiki routing applies. Invoke `$deduplicate-code` only when Spec-owned/Mixed work creates a real duplicate-implementation risk; when invoked, both Arid and JSCPD must be visible. Run other deterministic checks only when their artifact classes apply.

Inherited-only unrelated failures are report-only.

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

## 6. Establish Semantic Proof

After deterministic gates and required tests pass, prove every manifest cell from direct current evidence.

Prefer, in order:

1. exact implementation/config/document/tracker inspection;
2. already-executed gate/test evidence;
3. narrow searches needed to exclude a falsifier;
4. CodeGraph/transitive exploration only when direct evidence cannot establish the required call-path or blast-radius proof cheaply.

For each cell:

- preserve every material clause, quantifier, condition, exception, and named surface;
- identify a real falsifier and authoritative domain;
- establish evidence that excludes the falsifier;
- prove material assumptions or leave the cell unresolved;
- use `not-applicable` only with an exact originating-Spec reason.

For `all`/`every`/`none`/`only`/`complete` or equivalent finite/discoverable domains, establish Nested Universe closure by explicit enumeration or a deterministic exhaustive mechanism. Examples or targeted tests are not exhaustive unless the authoritative domain is exactly that set.

### Compact Proof Map

Group cells only when the same evidence set genuinely proves every mapped claim. Persist only:

```json
{
  "cells": ["US-1", "US-2"],
  "state": "proven",
  "evidence": ["application/x.py:10-40", "test_x::test_behavior"]
}
```

For `not-applicable`, use `reason` instead of `evidence`.

Do **not** create:

- a separate coverage array;
- proof IDs;
- predicate/falsifier/domain/Nested-Universe prose in JSON;
- per-proof hashes;
- a proof-packet hash;
- a second final-state wrapper.

The finalizer derives coverage and rejects missing, unknown, duplicate, or unresolved mappings.

## 7. Failure and Repair

Classify failures as:

- failed Spec obligation;
- Spec-owned repository-standard/tooling failure;
- inherited-only unrelated defect.

Repair only the first two, at the narrowest authoritative point. Use the owning skill where required (`$wiki-sync`, `$to-doc`, `$classify-doc`, `$to-adr-doc`, etc.). A fix that requires choosing/changing a durable architecture invariant routes to `$architecture-remediation`; do not invent the decision locally.

After a repair:

1. rerun only invalidated gates/tests/proof evidence;
2. rebuild only affected proof groups;
3. require every manifest cell resolved at the new candidate `HEAD`;
4. rerun mutable guards invalidated by the change.

If verification changes the repository, verify branch, stage only verification-owned files, invoke `$conventional-commits`, commit, push, then refresh exact-HEAD contract bindings and affected proof groups. Do not preserve proof across uncertain mutation.

## 8. Finalize Once

At stable candidate `HEAD`:

1. rerun `$spec-contract` in `build` mode;
2. require valid body/contract and reconciled ownership;
3. require every applicable gate PASS or NOT APPLICABLE;
4. require every manifest cell proven or not-applicable;
5. require current hierarchy/dependency state valid;
6. require clean worktree.

Create **one compact finalization input** containing only:

```text
spec_issue
head
baseline
branch
mode
prior_checkpoint
spec_body_hash
spec_contract_hash
default_branch
default_head
source_counts
manifest
proofs
gates
repairs
unrelated_inherited_findings
```

Rules:

- copy the ordered manifest rows returned by `$spec-contract` exactly; do not rewrite them;
- do not duplicate manifest cells into coverage;
- proofs contain only `cells`, `state`, and `evidence` or `reason`;
- gates contain only `name`, `status`, and concise native `evidence`; commands are already in the transcript;
- do not build a giant intermediate packet or wrapper object.

Run one deterministic operation:

```bash
FINALIZE_INPUT=$(mktemp)
RECEIPT_FILE=$(mktemp)

uv run python "$ARTIFACT_TOOL" finalize \
  --input "$FINALIZE_INPUT" \
  --receipt-output "$RECEIPT_FILE"
```

`finalize` validates bindings/coverage/gates, rejects unresolved cells, computes one Verification Hash, and renders the receipt. There is no separate packet admission, final-state validation, receipt rendering, or pre-persistence receipt-validation phase.

## 9. Persist the Compact Receipt

The receipt is a checkpoint/binding record, not a transcript of semantic reasoning. It retains the manifest/source counts needed by `$review-spec`, compact derived coverage, gate outcomes, repairs, inherited findings, and one Verification Hash. It omits proof prose, proof hashes, duplicate coverage structures, and commands already visible in the transcript.

Re-run the Project Delivery guard, then persist exactly once:

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

Exact byte equality proves persisted-body integrity because only a successful `finalize` can produce the local receipt.

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
