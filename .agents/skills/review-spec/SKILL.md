---
name: review-spec
description: Review a verified completed Spec against its persisted verification contract using ownership-scoped Standards review, independent Spec/Architecture review, and targeted convergence challenge only when justified.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Review Spec

Review the **exact verified state** of a completed Spec along the applicable independent axes:

- **Standards** — deterministic repository standards over Spec-owned/Mixed surfaces only;
- **Spec** — every cell in the persisted Spec Contract Manifest;
- **Architecture** — current architecture authority governing the affected boundaries.

This skill is review-only. `$verify-spec` owns verification and tool/gate execution. A passing **Spec Verification Receipt** is the immutable contract checkpoint for review; `$review-spec` does not rebuild or re-prove that contract.

## Core Invariants

- Recover durable state; do not rely on prior conversation.
- The newest passing Spec Verification Receipt for the exact current `HEAD` is the review contract.
- Do not rerun Ruff, mypy, pytest, duplicate scanners, wiki lint, or other `$verify-spec` gates merely to strengthen a review finding.
- Fresh current ownership classification is still required because the default branch may advance after verification.
- One genuinely fresh primary reviewer per applicable axis is the default. Challengers are conditional, not ceremonial.
- After primary dispatch, the parent orchestrates; it does not become a fourth semantic reviewer.
- Persist only frozen, provenance-valid findings and compact lifecycle state.

## Finding Taxonomy

- **Blocking** — must be remediated before review closes.
- **Advisory** — useful but non-blocking.
- **Owner-overridden** — explicitly accepted/rejected by the owner.
- **Scope-retired** — historical root/cell proven no longer owned or required by this Spec; history remains durable.

Exact Spec mismatches are Blocking. Deterministic Standards violations are Blocking only on Spec-owned/Mixed or Spec-owned tracker state. Architecture violations returned under current architecture authority are Blocking. Inherited-only unrelated defects are not current-Spec Standards blockers.

## 1. Pin the Verified Checkpoint Once

Read the complete parent-Spec comment history once through the same deterministic comment parser used by `$verify-spec`, then validate the latest receipt mechanically through the review artifact utility:

```bash
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
SPEC_NUMBER=<spec_issue_number>
CURRENT_HEAD=$(git rev-parse HEAD)
CURRENT_BRANCH=$(git branch --show-current)
VERIFY_TOOL=.agents/skills/verify-spec/scripts/verify_spec_artifacts.py
REVIEW_TOOL=.agents/skills/review-spec/scripts/review_spec_artifacts.py
SPEC_COMMENTS_FILE=$(mktemp)
SPEC_COMMENTS_SUMMARY=$(mktemp)
SPEC_BODY_FILE=$(mktemp)
REVIEW_CHECKPOINT=$(mktemp)

gh api --paginate --slurp \
  -H "X-GitHub-Api-Version: 2026-03-10" \
  "repos/$REPO/issues/$SPEC_NUMBER/comments?per_page=100" \
  > "$SPEC_COMMENTS_FILE"

uv run python "$VERIFY_TOOL" comments \
  --input "$SPEC_COMMENTS_FILE" \
  > "$SPEC_COMMENTS_SUMMARY"

gh issue view "$SPEC_NUMBER" --repo "$REPO" --json body --jq .body \
  > "$SPEC_BODY_FILE"

uv run python "$REVIEW_TOOL" checkpoint \
  --comments-summary "$SPEC_COMMENTS_SUMMARY" \
  --spec-body "$SPEC_BODY_FILE" \
  --spec "$SPEC_NUMBER" \
  --head "$CURRENT_HEAD" \
  --branch "$CURRENT_BRANCH" \
  > "$REVIEW_CHECKPOINT"
```

Require the expected `spec-<n>` branch and a clean worktree before review begins.

The checkpoint utility fails closed unless the newest verification receipt is passed, bound to the exact current Spec/HEAD/baseline/branch/body hash, contains one complete manifest, maps every manifest cell exactly once to proven/not-applicable coverage, and has zero unresolved cells.

Do **not** independently parse receipt Markdown, walk backward to an older receipt, or rebuild the source-unit/manifest proof inside review. Any checkpoint failure routes back to fresh `$verify-spec`.

The checkpoint JSON is the immutable review contract for this invocation. Retain exactly its baseline, body/contract hashes, manifest, verification hash, and receipt identity.

## 2. Refresh Ownership Only

The verification receipt proves the immutable contract; review needs only fresh ownership attribution against the **current** default branch.

Use the canonical `$spec-contract` ownership helper:

```bash
OWNERSHIP_FILE=$(mktemp)

uv run python \
  .agents/skills/spec-contract/scripts/classify_ownership.py \
  --baseline "$(jq -r .baseline "$REVIEW_CHECKPOINT")" \
  --branch "$CURRENT_BRANCH" \
  --head "$CURRENT_HEAD" \
  > "$OWNERSHIP_FILE"
```

This is an ownership refresh, not contract validation. It owns GitHub-pinned default-head resolution/fetch and current Spec-change ownership classification. Do not independently resolve/fetch the default branch or reproduce its diff algorithm in the parent.

Use the resulting ownership as follows:

- Standards universe → Spec-owned/Mixed repository surfaces + Spec-owned tracker surfaces only.
- Spec universe → the persisted manifest exactly.
- Architecture universe → current authority plus all owned/Mixed and explicitly required sibling/alternate surfaces.
- Inherited-only behavior can still violate an exact Spec/Architecture obligation, but it is not a Standards blocker merely because it exists.

## 3. Project Delivery Guard

For a Wayfinder-managed Spec, before reviewer dispatch:

1. require the Spec open and all direct blockers closed;
2. recover governing Wayfinder(s) from durable lineage;
3. invoke `$project-delivery-management` `reconcile` once when required by that skill;
4. invoke `$project-delivery-management` `guard <Wayfinder>` for each governor;
5. require at least one `PROJECT DELIVERY GUARD: ALLOWED`.

Do not reproduce the guard with custom `sed`, `awk`, regex parsing, Project-field logic, or a parallel frontier implementation.

Immediately before Pending or Exit persistence, invoke `guard <Wayfinder>` again for the already-resolved governor(s). That is mutable-state **revalidation**, not a second delivery-analysis phase. Do not rediscover lineage or explicitly rerun broader reconciliation unless intervening durable mutation invalidated those inputs.

## 4. Recover Durable Review State

A conventional **Spec Review** issue exists only for blocker/remediation history. A clean first-pass review does not create one; the parent Spec owns the final Exit Receipt.

Resolve an existing conventional Spec Review from one paginated issues read and the exact body marker:

```text
**Parent Spec:** #<n>
```

There must be zero or one matching issue titled `Spec Review: ...`; multiple matches fail closed. Do not infer review identity from Project fields, labels, title similarity alone, or prior conversation.

When Blocking findings require first-time remediation, create the conventional Spec Review **once**, then boundedly re-resolve the same canonical query. Never POST a second review issue because of read-after-write delay.

If a conventional Spec Review exists, recover privately:

- existing `RB-*` IDs/stable invariants;
- active/satisfied/owner-overridden/scope-retired cells;
- cumulative acceptance matrix and semantic surfaces;
- prior reviewed/satisfied heads and Owner Overrides.

Do not expose root history to primary reviewers.

### Scope Attribution Gate

An historical root/cell may scope-retire only when all are proven:

1. implicated surface is inherited-only or otherwise outside this Spec ownership;
2. no manifest cell requires the behavior;
3. no current architecture authority requires the behavior for this Spec;
4. retirement does not remove another active Spec-owned obligation.

Pre-existing behavior is not automatically out of scope.

## 5. Build the Review Universes

Build routing coverage before dispatch.

### Standards

Create `STD-*` cells for every Spec-owned/Mixed artifact group and each applicable deterministic Standards rule/category. Include Spec-owned tracker transitions governed by workflow policy. Do not create Standards cells for inherited-only surfaces.

### Spec

Use the checkpoint manifest **exactly**. Each persisted manifest cell is one Spec review cell. Require no missing/unknown cells before dispatch.

A reviewer-discovered originating-Spec obligation absent from the manifest is a **contract defect**. Halt and require fresh `$verify-spec`; do not silently expand the universe.

### Architecture

Create `ARCH-*` cells covering current affected architecture authorities, canonical owner/path/boundary/lifecycle/source-of-truth, owned/Mixed participants, and any sibling/alternate/named surface that the authority requires to obey the same rule. `$review-architecture` owns architecture evidence procedure.

## 6. Reviewer Execution Integrity

A fresh reviewer is a genuinely separate context that did not participate in parent orchestration and receives only its axis authority, complete cells, and relevant evidence pointers.

Default mode:

```text
Reviewer execution: independent-subagents
Reviewer execution override: None
```

If genuinely fresh contexts are unavailable, halt before review/persistence unless the human explicitly authorizes same-agent fallback for the current invocation. The override waives independence only; it never accepts or suppresses findings.

Canonical authorization:

```text
OWNER REVIEWER EXECUTION OVERRIDE: authorize same-agent reviewer fallback for this review
```

Under fallback, execute roles sequentially and disclose reduced independence. Never describe same-context roles as fresh.

## 7. Dispatch Primaries

Execute exactly one primary per applicable axis:

- Standards primary when applicable;
- Spec primary always;
- Architecture primary when applicable.

Give each primary only:

- axis authority;
- complete cells;
- relevant evidence pointers/owned surfaces;
- no Root Blocker history or prior reviewer conclusions.

Each primary must disposition every supplied cell and continue after discovering a blocker.

Coverage states:

```text
checked-no-finding | blocking | advisory | not-applicable
```

`not-applicable` requires exact authority/reason.

### Claim-Proof Integrity

For every material cell, the reviewer must internally establish claim/predicate/domain/falsifier/evidence and exclude the falsifier before `checked-no-finding`. Material assumptions must themselves be proven.

Do **not** serialize full predicate/falsifier prose for clean cells merely for bookkeeping. Return compact coverage groups plus full findings. A useful primary result is:

```text
Coverage: <cell IDs grouped by disposition>; missing 0; unchecked 0
Blocking: <full finding records>
Advisory: <records>
N/A: <cells + reasons>
Challenge triggers: <None | exact cell/question>
```

This keeps reviewer reasoning rigorous without spending output budget reproducing internal proof records.

Axis blocker authority:

- Standards → exact deterministic standard + owned/Mixed surface.
- Spec → exact manifest cell + originating Spec source.
- Architecture → current authority with `Architecture decision required: Yes|No` and routing.

## 8. Parent Orchestration Boundary

After primary dispatch, the parent is an **orchestrator**, not another reviewer.

While reviewers run, the parent may:

- wait/collect results;
- recover tracker/remediation state not exposed to reviewers;
- prepare compact persistence metadata;
- deduplicate returned records mechanically.

The parent must **not**:

- independently re-review assigned semantic cells;
- explore implementation to search for additional findings in parallel;
- rerun pytest/Ruff/mypy/Arid/JSCPD/wiki lint or other verification gates;
- use a passing/failing test as substitute review authority;
- preempt a reviewer by reaching its own semantic disposition.

After results return, parent inspection is allowed only at these narrow boundaries:

1. **Axis-Provenance validation** — confirm that the cited native authority exists and applies to the cited surface/cell;
2. **concrete challenge trigger** — resolve ambiguity/contradiction through a targeted challenger, not an open-ended parent review;
3. **root reconciliation** — inspect only historical root evidence implicated by frozen findings.

If accepting/rejecting a finding would require broad semantic exploration, dispatch the targeted challenger instead.

## 9. Conditional Challenge

Dispatch one targeted challenger only for a concrete trigger:

1. coverage gap/materially omitted applicable cell;
2. authority conflict/ambiguity;
3. contradictory or materially insufficient finding evidence;
4. convergence trigger after root reconciliation.

Challenge only the affected cell/question. Do not intentionally give the challenger the primary conclusion. It applies the same Claim-Proof Integrity. If a required challenge remains unresolved, review is incomplete and nothing is persisted as PASS/remediation-ready.

## 10. Freeze Findings and Validate Provenance

Coverage is complete only when every supplied cell is dispositioned, no manifest cell is missing, no applicable Standards/Architecture cell is unchecked, and every N/A has a reason.

Freeze and deduplicate the current findings. Accept Blocking only when its own axis authority establishes it; do not move a rejected finding to another axis.

## 11. Reconcile Durable Roots

Only after findings are frozen may the parent use Root Blocker history.

Map a finding to an existing root only when the stable invariant already derives it. Otherwise mark `Candidate new root`; if materially related but broader, mark `possible root-definition gap`.

For a newly accepted violation against a previously satisfied/closed root, classify only from implicated history:

- **Missed prior finding**;
- **Regression**;
- **Origin uncertain**.

Previously satisfied sibling cells remain satisfied unless directly contradicted.

### Convergence Saturation

A Missed prior finding against a satisfied root or a root-definition gap proves incomplete prior closure enumeration. Before persistence:

1. derive the bounded Root Closure Domain Manifest;
2. execute exactly one saturation challenger under the originating axis;
3. require every domain item checked and `unchecked 0`;
4. provenance-validate new findings and merge them before persistence.

Do not run another generic full-axis review.

## 12. Aggregate

Report the three axes and compact coverage/effectiveness:

```text
Reviewer execution: <mode>
Standards: <coverage>; unchecked 0
Spec: <manifest count>; unchecked 0
Architecture: <coverage>; unchecked 0
Targeted challengers: <n>
Saturation challengers: <n>
Primary validated findings: <n>
Targeted-only validated findings: <n>
Saturation-only validated findings: <n>
```

If any Blocking Architecture finding requires an architecture decision, halt with `$architecture-remediation`; do not invent the decision.

## 13. Pending Review Remediation

If architecture-conforming Blocking findings remain, or Scope corrections must update existing durable review state:

1. revalidate Project Delivery guard for the already-resolved governor(s);
2. require `HEAD` still equals the verification checkpoint;
3. create/re-resolve the conventional Spec Review only when Blocking remediation requires one;
4. render the Pending packet through the deterministic review utility;
5. POST once, GET that exact comment, and require byte-for-byte equality;
6. invoke `$review-spec-remediation` only after persistence succeeds.

Build one compact JSON input containing checkpoint bindings, reviewer execution metadata, accepted findings by axis, compact coverage/effectiveness, root mappings/state, provenance, scope corrections, and saturation result. Then:

```bash
PENDING_INPUT=$(mktemp)
PENDING_FILE=$(mktemp)
PENDING_JSON=$(mktemp)
COMMENT_JSON=$(mktemp)
READBACK_FILE=$(mktemp)

uv run python "$REVIEW_TOOL" render-pending \
  --input "$PENDING_INPUT" \
  --output "$PENDING_FILE"

jq -Rs '{body: .}' "$PENDING_FILE" > "$PENDING_JSON"
gh api --method POST \
  "repos/$REPO/issues/$SPEC_REVIEW_ISSUE_NUMBER/comments" \
  --input "$PENDING_JSON" > "$COMMENT_JSON"

COMMENT_ID=$(jq -r .id "$COMMENT_JSON")
COMMENT_URL=$(jq -r .html_url "$COMMENT_JSON")
[ -n "$COMMENT_ID" ] && [ "$COMMENT_ID" != "null" ]
gh api "repos/$REPO/issues/comments/$COMMENT_ID" \
  | jq -j .body > "$READBACK_FILE"
cmp -s "$PENDING_FILE" "$READBACK_FILE"
```

The renderer owns packet shape and validation. Do not hand-build the Markdown with shell substitution, `sed`, regex patching, or a second wrapper object. Exact readback of the deterministic renderer output is sufficient persistence integrity; do not reparse/rewrite the persisted packet merely for ceremony.

If remediation remains active and `$review-spec-remediation` returns `$to-tickets`, reconcile Project state before presenting that handoff.

## 14. Exit Gate

PASS requires:

- current `HEAD` and Spec body still match the checkpoint;
- reviewer execution integrity satisfied;
- every Spec/Standards/Architecture review cell dispositioned;
- no unresolved targeted/saturation coverage;
- zero current Blocking findings;
- all existing roots `satisfied`, `owner-overridden`, or `scope-retired`;
- zero Candidate new roots.

The immutable contract itself does not need to be rebuilt again at Exit. Re-read current `HEAD`, clean worktree, Spec body hash, and mutable delivery guard; if any checkpoint binding changed, require fresh `$verify-spec`.

### Persist Exit Receipt

Revalidate Project Delivery guard, render the Exit Receipt through the same deterministic utility, POST it to the **parent Spec**, GET the exact comment, and require byte equality.

```bash
EXIT_INPUT=$(mktemp)
EXIT_FILE=$(mktemp)
EXIT_JSON=$(mktemp)
COMMENT_JSON=$(mktemp)
READBACK_FILE=$(mktemp)

uv run python "$REVIEW_TOOL" render-exit \
  --input "$EXIT_INPUT" \
  --output "$EXIT_FILE"

jq -Rs '{body: .}' "$EXIT_FILE" > "$EXIT_JSON"
gh api --method POST \
  "repos/$REPO/issues/$SPEC_NUMBER/comments" \
  --input "$EXIT_JSON" > "$COMMENT_JSON"

COMMENT_ID=$(jq -r .id "$COMMENT_JSON")
COMMENT_URL=$(jq -r .html_url "$COMMENT_JSON")
[ -n "$COMMENT_ID" ] && [ "$COMMENT_ID" != "null" ]
gh api "repos/$REPO/issues/comments/$COMMENT_ID" \
  | jq -j .body > "$READBACK_FILE"
cmp -s "$EXIT_FILE" "$READBACK_FILE"
```

Do not create a conventional Spec Review on a clean PASS path.

A persisted Exit Receipt establishes the parent Spec base lifecycle:

```text
Artifact Type: Spec
Workflow State: Ready to Merge
Work Status: Ready
Next Skill: $spec-merge-cleanup
Root Blocker: None
Completed On: None
```

Invoke `$project-tracking` after Exit persistence. Project drift does not invalidate the durable review receipt.

## 15. Human Handoff

On PASS:

> ✅ **Spec review passed.**
>
> The verified and reviewed `HEAD` is ready for merge and cleanup.
>
> Please run:
>
> ```
> $spec-merge-cleanup - <Spec Title> (<Spec URL>)
> ```

Do not close the Spec or Spec Review here; `$spec-merge-cleanup` owns merge/closure/branch cleanup.

## Transition-Bound Review Proof State

Every reviewer role must maintain enough working proof to justify each disposition:

```text
Cell
Claim/predicate/domain
Falsifier
Evidence
Survivability: excluded | survives
Material assumptions
Disposition
```

`checked-no-finding` requires excluded falsifier and no unproven material assumption. The parent must require complete universe coverage, no unknown/missing/unresolved cells, and no incomplete clean dispositions before PASS.

These records are **working reasoning state**, not mandatory serialized output. Primaries/challengers should return compact grouped coverage and full findings rather than dumping one verbose proof object per clean cell. Fresh reviewer independence remains mandatory unless explicitly owner-overridden for the current invocation.
