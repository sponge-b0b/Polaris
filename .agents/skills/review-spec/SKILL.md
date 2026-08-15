---
name: review-spec
description: Review a verified completed Spec along independent Standards, Spec, and Architecture axes, reconcile findings against any existing Root Blocker Ledger, and route remaining blockers.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Review Spec

Review the verified diff between `HEAD` and the Spec baseline along three independent axes:

* **Standards** — repository coding standards.
* **Spec** — originating Spec requirements.
* **Architecture** — resolved architecture and current authorities.

This is review-only.

Do not run `pytest`, Ruff, Mypy, graph updates, duplication scans, or other verification commands.

Do not invoke the `$wiki-lint` skill.

`$verify-spec` owns verification.

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

If one exists, recover its **durable Root Blocker state** from the body and subsequent review/remediation updates.

Capture:

* existing `RB-*` IDs and invariants;
* current root status;
* acceptance obligations/matrix;
* affected sibling surfaces;
* Owner Overrides;
* previous reviewed and satisfied/closed `HEAD` values when available.

#### Cumulative Acceptance State

Acceptance obligations are cumulative for the lifetime of an active root.

A later review update may change an obligation's status or evidence, but omission alone does not retire it.

Carry forward every previously established obligation unless durable review state explicitly records that it was:

* superseded by a materially equivalent obligation;
* retired because current Spec/architecture no longer requires it; or
* Owner-overridden.

If a later ledger update silently dropped an active obligation, continue carrying it and pass that ledger drift to `$review-spec-remediation`.

Do not silently shrink a root's closure domain to only the latest failing symptoms.

#### Root Identity

An existing `RB-*` ID denotes one durable invariant.

Map a finding to an existing root only when the finding is derivable from that recorded invariant without materially expanding what the root means.

A shared subsystem, theme, architectural area, or historical association is insufficient.

If a finding appears related to an existing root but would require materially expanding its invariant or closure domain, mark it:

```text
Candidate new root — related to RB-<n>; possible root-definition gap
```

`$review-spec-remediation` owns deciding whether the durable root definition was incomplete or a genuinely distinct root exists.

Never rewrite, broaden, renumber, or assign `RB-*` IDs here.

### Reviewer Dispatch Invariant

**Review-state recovery is a hard precondition for reviewer dispatch.**

Do not spawn any review sub-agent until:

1. the search for an existing Spec Review is complete; and
2. when one exists, its durable cumulative Root Blocker state has been recovered.

Each reviewer's initial prompt must contain enough recovered root state to map findings and report applicable status.

Root Blocker state is **continuity and mapping context only**. It is not review authority.

A reviewer must never derive an axis finding merely because an RB invariant, acceptance obligation, prior finding, or sibling surface says the behavior is required.

If existing review state is discovered only after reviewers were spawned, discard the affected results and restart those reviewers with the recovered state.

### 5. Spawn Reviewers

Only after Step 4 is satisfied, spawn exactly three parallel sub-agents when all axes apply:

* one Standards;
* one Spec;
* one Architecture.

Never spawn more than one reviewer per axis.

After spawning, the main agent only aggregates and lightly validates returned evidence.

Give each reviewer:

* aggregate diff and commits;
* **only its axis authority as review authority**;
* Finding Taxonomy;
* recovered root state for later mapping/status reconciliation.

Tell every reviewer:

1. review the complete aggregate change using only its axis authority;
2. do not use the Root Blocker Ledger, another axis's authority, or previous findings to establish a violation;
3. do not stop after finding a blocker;
4. return every independent Blocking finding discovered by its axis;
5. only after finding an issue, map it to an existing root when the recorded invariant already explains it;
6. mark unmatched or materially root-expanding findings `Candidate new root`;
7. never invent an `RB-*` ID.

For an existing open or regressed root, report status only for obligations independently governed by that reviewer's axis.

#### Standards

Authoritative sources:

* `$coding-standards`;
* applicable repository coding/process standards.

Review the full aggregate change for deterministic standards violations and relevant non-tooling smells.

Every **Blocking Standards** finding must cite the exact documented deterministic standard it violates.

An RB obligation, Spec requirement, ADR, architecture document, or preferred design is not by itself a Standards rule.

When a finding depends on determining canonical architectural ownership, authority source, lifecycle, boundary, or dependency direction rather than a documented coding rule, leave it to the Architecture axis.

Return Blocking/Advisory findings only.

Skip issues reliably owned by tooling.

#### Spec

Authority:

* the originating Spec.

Review the full aggregate implementation for missing, partial, incorrect, or unauthorized behavior.

Every Blocking Spec finding must cite the applicable Spec requirement.

An RB obligation or architectural rule not independently required by the Spec does not establish a Spec finding.

Return all findings, not only those related to existing roots.

#### Architecture

Authority:

* current applicable architecture evaluated through `$review-architecture`.

Invoke `$review-architecture`.

Review the full aggregate implementation against applicable architectural authority.

Preserve `Architecture decision required: Yes | No` and routing for every Blocking finding.

Return all findings, not only those related to existing roots.

## 6. Aggregate

Lightly validate cited evidence only. Do not perform another review.

Validate axis ownership before accepting a finding:

* Blocking Standards → exact deterministic coding/repository standard cited;
* Blocking Spec → originating Spec requirement cited;
* Blocking Architecture → `$review-architecture` evidence/current authority cited.

If a finding is valid but returned under the wrong axis, place it under the axis whose authority actually establishes it. Do not duplicate it merely because another reviewer noticed it.

Present:

```text
## Standards

## Spec

## Architecture
```

Keep genuinely independent axis findings separate even when several map to one root.

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

* **satisfied** — all carried obligations are established by available evidence;
* **open** — one or more carried/current obligations are violated;
* **regressed** — behavior previously established as satisfied was broken by a later change;
* **unproven** — available review evidence is insufficient to establish required status.

Do not infer satisfaction merely because source code appears plausible.

Do not call a root `regressed` merely because a new violation was discovered after it was previously satisfied.

### Existing Root Provenance

When a new violation maps to a previously satisfied/closed root and a prior satisfied/closed `HEAD` is available, inspect only the implicated evidence at that prior `HEAD`.

Classify:

* defect existed materially unchanged at the prior satisfied/closed `HEAD` → **Missed prior finding**; current root status is `open`, not `regressed`;
* defect was introduced or materially changed after that `HEAD` → **Regression**; root may be `regressed`;
* origin cannot be determined confidently → **Origin uncertain**; do not claim regression.

This provenance classification does not change Blocking severity.

Do not perform broad historical discovery solely for provenance.

### Candidate New Root History

When a previous reviewed `HEAD` is available, classify each Candidate new root's implicated defect as:

* **Missed prior finding**;
* **New/regressed finding**;
* **Origin uncertain**.

This classification is diagnostic only. It does not assign a root ID or change Blocking severity.

Inspect only the implicated evidence.

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

Pass:

* durable existing root invariants and statuses;
* the cumulative carried acceptance matrix;
* still-violated/regressed/unproven obligations;
* satisfied obligations that must remain carried;
* axis findings mapped to existing roots;
* Existing Root Provenance classifications;
* unmatched Candidate new roots and their history classifications;
* any possible root-definition gaps;
* any detected acceptance-matrix ledger drift.

Do not restart root discovery for findings already explained by an unchanged existing invariant.

`$review-spec-remediation` owns:

* root synthesis;
* root-definition completeness/expansion decisions;
* new `RB-*` IDs;
* ledger updates;
* cumulative acceptance matrix updates;
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

`$spec-merge-cleanup` has `allow_implicit_invocation: false`.

Do not invoke it implicitly.

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
