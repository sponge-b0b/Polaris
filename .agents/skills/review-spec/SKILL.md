---
name: review-spec
description: Review a completed spec along independent Standards, Spec, and Architecture axes, reconcile findings against any existing Root Blocker Ledger, and route remaining blockers.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

Review the diff between `HEAD` and the Spec baseline along three independent axes:

* **Standards** — repository coding standards.
* **Spec** — originating Spec requirements.
* **Architecture** — resolved architecture and current authorities.

This is review-only. Do not run `pytest`, Ruff, Mypy, `$wiki-lint`, graph updates, duplication scans, or other verification commands. `$verify-spec` owns verification.

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

### 3. Recover Review State

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

### 4. Spawn Reviewers

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

## 5. Aggregate

Lightly validate cited evidence only. Do not perform another review.

Present:

```text
## Standards

## Spec

## Architecture
```

Keep axis findings independent even when multiple findings map to one root.

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

Every previously open/regressed root must appear.

Use:

* **satisfied** — all obligations supported by required evidence;
* **open** — one or more obligations remain violated;
* **regressed** — previously satisfied behavior is now broken;
* **unproven** — required evidence is insufficient.

Do not mark verification-owned obligations satisfied merely because code looks correct.

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

## 6. Remediation

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

* all three axes have zero Blocking findings;
* every existing Root Blocker is satisfied or Owner-overridden;
* no Candidate new root remains unresolved.

Advisory findings may remain.

Do not close the Spec or Spec Review here. `$spec-merge-cleanup` owns closure.
