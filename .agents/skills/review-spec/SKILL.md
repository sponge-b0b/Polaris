---
name: review-spec
description: Review a verified completed Spec along independent Standards, Spec, and Architecture axes, reconcile findings against any existing Root Blocker Ledger, and route remaining blockers.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

Review the verified diff between `HEAD` and the Spec baseline along three independent axes:

* **Standards** — repository coding standards.
* **Spec** — originating Spec requirements.
* **Architecture** — resolved architecture and current authorities.

This is review-only. Do not run `pytest`, Ruff, Mypy, `$wiki-lint`, graph updates, duplication scans, or other verification commands. `$verify-spec` owns verification.

`$review-spec` requires a passing `$verify-spec` receipt for the exact current `HEAD`.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting. Prior-session summaries or remembered conclusions are routing context only and must not substitute for required durable evidence.

If required durable state cannot be recovered, report the missing artifact rather than infer or recreate it from memory.

## Finding Taxonomy

* **Blocking** — must be remediated before review closes.
* **Advisory** — useful but non-blocking.
* **Owner-overridden** — explicitly accepted/rejected by the owner; suppress from future blocking counts.

Rules:

* Spec mismatches and deterministic standards violations are Blocking by default.
* Architecture violations identified by `$review-architecture` are Blocking.
* Blocking Architecture findings must include `Architecture decision required: Yes | No`.
* Smells are Advisory unless explicitly promoted.
* Different axis views or sibling symptoms of the same invariant are not separate root blockers.

## Process

### 1. Pin the Baseline

Resolve the baseline from the parent Spec comment unless explicitly supplied:

```bash
BASELINE_COMMIT=$(gh issue view <spec_issue_number> --json comments -q '.comments[].body' \
  | grep -oP '(?<=\*\*Baseline Commit Hash:\*\* )\S+' | tail -1)
```

Verify:

```bash
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "spec-<spec_issue_number>" ]; then
  echo "❌ Expected spec-<spec_issue_number>; current branch is $CURRENT_BRANCH."
  exit 1
fi

git rev-parse "$BASELINE_COMMIT"
```

Capture:

```bash
git diff "$BASELINE_COMMIT"...HEAD
git log "$BASELINE_COMMIT"..HEAD --oneline
```

The diff must be non-empty.

### 2. Resolve the Spec

Find the originating Spec from:

1. commit references;
2. user-provided issue/path;
3. matching repository Spec;
4. user only if still unresolved.

Capture its **Architecture Impact**.

### 3. Require Current Spec Verification

Require a clean worktree:

```bash
if [ -n "$(git status --porcelain)" ]; then
  echo "❌ Spec review requires a clean, verified worktree."
  exit 1
fi

CURRENT_HEAD=$(git rev-parse HEAD)
```

Recover the latest passing **Spec Verification Receipt** from the parent Spec.

Require:

* `Status: passed`;
* `Verified HEAD` exactly equals `CURRENT_HEAD`;
* `Verified Baseline` equals the current Spec baseline;
* `Branch` equals the current Spec branch.

If no matching receipt exists, halt:

> ⚠️ **Spec review requires current passing spec verification.**
>
> Current HEAD: `<current HEAD>`
> Verified HEAD: `<latest verified HEAD or none>`
>
> Please run:
>
> ```
> $verify-spec - <Spec Title> (<Spec URL>)
> ```

Do not invoke `$verify-spec` implicitly.

Any commit after verification makes the receipt stale.

### 4. Recover Review State

Before any reviewer is spawned, determine whether a Spec Review already exists for this Spec.

If one exists, recover its **latest persisted Root Blocker state**, including body and later review/remediation updates.

Capture:

* existing `RB-*` IDs and invariants;
* current root status;
* acceptance obligations/matrix;
* affected sibling surfaces;
* Owner Overrides;
* previous reviewed `HEAD` when available.

On re-review:

* every existing open or regressed root MUST receive a status;
* evaluate existing acceptance obligations first;
* map findings to an existing root when they share its invariant;
* another axis, sibling surface, or symptom does not create another root.

**Never create, renumber, or assign a new `RB-*` ID here.**

An unmatched finding is only a **Candidate new root**. `$review-spec-remediation` owns root synthesis and IDs.

### Reviewer Dispatch Invariant

**Review-state recovery is a hard precondition for reviewer dispatch.**

Do not spawn any review sub-agent until:

1. the search for an existing Spec Review is complete; and
2. when one exists, its latest Root Blocker state has been recovered.

Each reviewer's **initial prompt** must contain the applicable recovered root invariants, statuses, acceptance obligations, and sibling surfaces.

Do not intentionally dispatch reviewers without known review state and reconcile it afterward.

If existing review state is discovered only after reviewers were spawned, their incomplete-context results are invalid. Discard those results and restart the affected reviewers with the recovered state rather than layering a second reconciliation pass onto the first.

### 5. Spawn Reviewers

Only after Step 4 and the Reviewer Dispatch Invariant are satisfied, spawn exactly three parallel sub-agents when all axes apply:

* one Standards;
* one Spec;
* one Architecture.

Never spawn more than one reviewer per axis.

After spawning, the main agent only aggregates and lightly validates returned evidence.

Give each reviewer in its initial prompt:

* aggregate diff and commits;
* its authoritative review sources;
* Finding Taxonomy;
* existing roots and applicable acceptance obligations;
* affected sibling surfaces;
* current root status when applicable.

Tell each reviewer:

1. evaluate applicable existing-root obligations first;
2. then complete the **entire independent axis review** across the aggregate Spec change;
3. do not stop after finding a blocker or after evaluating existing roots;
4. return every independent Blocking finding discovered in this pass;
5. map findings to existing roots where applicable;
6. mark unmatched findings `Candidate new root`;
7. never invent an `RB-*` ID.

#### Standards

Use `$coding-standards` and applicable repository standards.

Review the full aggregate change for deterministic standards violations and relevant non-tooling smells.

Return all Blocking/Advisory findings. Skip issues reliably owned by tooling.

#### Spec

Use the originating Spec.

Review the full aggregate implementation for missing, partial, incorrect, or unauthorized behavior and cite the requirement.

Return all findings, not only those related to existing roots.

#### Architecture

Invoke `$review-architecture`.

Review the full aggregate implementation against applicable architectural authority.

Preserve `Architecture decision required: Yes | No` and routing for every Blocking finding.

Return all findings, not only those related to existing roots.

## 6. Aggregate

Lightly validate cited evidence only. Do not perform another review.

Present:

```text
## Standards

## Spec

## Architecture
```

Keep axis findings independent even when several map to one root.

If a Root Blocker Ledger exists, also present:

```text
## Root Blocker Status

RB-1: <satisfied | open | regressed | unproven>
RB-2: <satisfied | open | regressed | unproven>
...

Candidate new roots:
- <unmatched finding>
- or None
```

Every previously open or regressed root must appear.

Use:

* **satisfied** — required obligations are established by available evidence;
* **open** — one or more obligations remain violated;
* **regressed** — previously satisfied behavior is now broken;
* **unproven** — available review evidence is insufficient.

Do not infer satisfaction merely because source code appears plausible.

If multiple findings map to one root, say so explicitly.

### Candidate New Root History

When a previous reviewed `HEAD` is available, determine whether each Candidate new root's implicated defect:

* existed materially unchanged at the previous reviewed `HEAD` → **Missed prior finding**;
* was introduced or materially changed afterward → **New/regressed finding**;
* cannot be determined confidently → **Origin uncertain**.

This classification is diagnostic only. It does not change Blocking severity or root ownership.

Do not perform broad discovery solely for this comparison; inspect only implicated evidence.

### Architecture Human Handoff

If any Blocking Architecture finding has `Architecture decision required: Yes`, collect all independent unresolved architecture blockers and halt.

Use:

> ⚠️ **Spec review is blocked by unresolved architecture.**
>
> Please run:
>
> ```
> $architecture-remediation - <Spec Title> (<Spec URL>) — <concise blocker-set summary>
> ```
>
> **Architecture blockers:**
>
> 1. **<question/conflict>**
>
>    * Evidence: <evidence>
>    * Material consequence: <ownership/path/boundary/dependency/lifecycle/conflict>
>    * Governing context: <entities / ADRs / docs>
>    * Existing root: <RB-n or None>

Do not propose the architectural answer.

Blocking Architecture findings with `Architecture decision required: No` remain ordinary remediation findings.

## 7. Remediation

If Blocking findings remain and none require architecture resolution, invoke `$review-spec-remediation`.

On re-review, pass:

* existing root statuses;
* still-violated/regressed/unproven obligations;
* axis findings mapped to those roots;
* unmatched Candidate new roots and their history classification.

Do not restart root discovery for findings already explained by an existing root.

`$review-spec-remediation` owns:

* root synthesis;
* new `RB-*` IDs;
* ledger updates;
* acceptance matrix updates;
* remediation tracking;
* Owner Overrides.

Advisory-only findings do not trigger remediation.

## Exit Gate

The review passes only when:

* current `HEAD` still matches the passing Spec Verification Receipt;
* all three axes have zero Blocking findings;
* every existing Root Blocker is satisfied or Owner-overridden;
* no Candidate new root remains unresolved.

Advisory findings may remain.

### Persist Exit Receipt

Only after the Exit Gate passes, persist a **Spec Review Exit Receipt** on the parent Spec issue:

```markdown
## Spec Review Exit Receipt

**Status:** passed
**Reviewed HEAD:** <full SHA>
**Reviewed Baseline:** <full Spec baseline SHA>
**Branch:** spec-<spec_issue_number>
**Blocking findings:** 0
**Root blockers:** satisfied-or-owner-overridden
**Candidate new roots:** 0
```

Immediately before persistence:

```bash
REVIEWED_HEAD=$(git rev-parse HEAD)

if [ "$REVIEWED_HEAD" != "$CURRENT_HEAD" ]; then
  echo "❌ HEAD changed during Spec review."
  exit 1
fi
```

`REVIEWED_HEAD` must also equal the `Verified HEAD` from the current passing Spec Verification Receipt.

If receipt persistence fails, review is incomplete.

The receipt authorizes cleanup only for that exact `HEAD`. Any later commit makes it stale.

### Spec Merge Cleanup Human Handoff

`$spec-merge-cleanup` has `allow_implicit_invocation: false`. Do not invoke it implicitly.

After the Exit Receipt is successfully persisted, halt with:

> ✅ **Spec review passed.**
>
> The verified and reviewed `HEAD` is ready for merge and cleanup.
>
> Please run:
>
> ```
> $spec-merge-cleanup - <Spec Title> (<Spec URL>)
> ```

Then stop.

Do not close the Spec or Spec Review here. `$spec-merge-cleanup` owns merge, closure, branch cleanup, and Wayfinder completion reconciliation.
