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

```bash id="iewafb"
BASELINE_COMMIT=$(gh issue view <spec_issue_number> --json comments -q '.comments[].body' \
  | grep -oP '(?<=\*\*Baseline Commit Hash:\*\* )\S+' | tail -1)
```

Verify:

```bash id="6xsps6"
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "spec-<spec_issue_number>" ]; then
  echo "❌ Expected spec-<spec_issue_number>; current branch is $CURRENT_BRANCH."
  exit 1
fi

git rev-parse "$BASELINE_COMMIT"
```

Capture:

```bash id="djpber"
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

Before recovering review state or spawning reviewers, require a clean worktree:

```bash id="pytpxi"
if [ -n "$(git status --porcelain)" ]; then
  echo "❌ Spec review requires a clean, verified worktree."
  exit 1
fi
```

Capture current `HEAD`:

```bash id="kczocg"
CURRENT_HEAD=$(git rev-parse HEAD)
```

Read the parent Spec comments and recover the **latest passing Spec Verification Receipt**.

The receipt must contain:

```text id="9zrts2"
## Spec Verification Receipt
**Status:** passed
**Verified HEAD:** <full SHA>
**Verified Baseline:** <baseline>
**Branch:** spec-<spec_issue_number>
```

Require:

* `Status` is `passed`;
* `Verified HEAD` exactly equals `CURRENT_HEAD`;
* `Verified Baseline` equals the current Spec baseline;
* `Branch` equals the current Spec branch.

If no matching receipt exists, verification is missing or stale. Do not review.

Halt with:

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

Then stop.

Do not invoke `$verify-spec` implicitly.

Any commit after a passing verification invalidates that receipt for review eligibility until `$verify-spec` passes again.

### 4. Recover Review State

If a Spec Review already exists, recover the **latest persisted Root Blocker state**, considering its body and subsequent remediation/review updates.

Capture:

* existing `RB-*` IDs and invariants;
* current root status;
* acceptance obligations/matrix;
* affected sibling surfaces;
* Owner Overrides.

On re-review:

* every existing open or regressed root MUST receive a status this pass;
* evaluate its acceptance obligations before looking for new roots;
* map findings to an existing root when they share its invariant;
* another axis, sibling surface, or symptom does not create another root.

**Never create, renumber, or assign a new `RB-*` ID here.**

An unmatched finding is only a **Candidate new root**. `$review-spec-remediation` owns root synthesis and IDs.

### 5. Spawn Reviewers

Spawn exactly three parallel sub-agents when all axes apply:

* one Standards;
* one Spec;
* one Architecture.

Never spawn more than one reviewer per axis.

After spawning, the main agent only aggregates and lightly validates returned evidence.

Give each reviewer:

* aggregate diff and commits;
* its authoritative review sources;
* Finding Taxonomy;
* existing roots and applicable acceptance obligations.

Tell each reviewer:

1. evaluate applicable existing-root obligations first;
2. perform its independent axis review;
3. map findings to existing roots where applicable;
4. mark unmatched findings `Candidate new root`;
5. never invent an `RB-*` ID.

#### Standards

Use `$coding-standards` and applicable repository standards.

Return Blocking/Advisory findings only. Skip issues reliably owned by tooling.

#### Spec

Use the originating Spec.

Find missing, partial, incorrect, or unauthorized behavior and cite the requirement.

#### Architecture

Invoke `$review-architecture`.

Preserve `Architecture decision required: Yes | No` and routing for every Blocking finding.

## 6. Aggregate

Lightly validate cited evidence only. Do not perform another review.

Present:

```text id="44d6jf"
## Standards

## Spec

## Architecture
```

Keep axis findings independent even when multiple findings map to one root.

If a Root Blocker Ledger exists, also present:

```text id="2n41xu"
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

* **satisfied** — all required obligations are established by available evidence;
* **open** — one or more obligations remain violated;
* **regressed** — previously satisfied behavior is now broken;
* **unproven** — available review evidence is insufficient.

Do not infer satisfaction merely because source code appears plausible.

If multiple findings map to one root, say so explicitly.

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
* unmatched Candidate new roots.

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

Proceed to `$spec-merge-cleanup` only when:

* the current `HEAD` still matches the passing Spec Verification Receipt;
* all three axes have zero Blocking findings;
* every existing Root Blocker is satisfied or Owner-overridden;
* no Candidate new root remains unresolved.

Advisory findings may remain.

Do not close the Spec or Spec Review here. `$spec-merge-cleanup` owns closure.
