---
name: review-spec
description: Review a verified completed Spec along independent Standards, Spec, and Architecture axes, then reconcile independently discovered findings against durable Root Blocker state and route remaining blockers.
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

Do not invoke `$wiki-lint`.

`$verify-spec` owns verification.

`$review-spec` requires a passing `$verify-spec` receipt for the exact current `HEAD`.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting.

Prior-session summaries or remembered conclusions are routing context only and must not substitute for durable evidence.

If required durable state cannot be recovered, report the missing artifact rather than infer or recreate it.

## Finding Taxonomy

* **Blocking** — must be remediated before review closes.
* **Advisory** — useful but non-blocking.
* **Owner-overridden** — explicitly accepted/rejected by the owner; suppress from future blocking counts.

Rules:

* Spec mismatches and deterministic standards violations are Blocking by default.
* Architecture violations identified by `$review-architecture` are Blocking.
* Blocking Architecture findings must include `Architecture decision required: Yes | No`.
* Smells are Advisory unless explicitly promoted.
* Different axis findings or sibling symptoms of one invariant do not automatically create separate Root Blockers.

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

### 4. Recover Durable Review State

Before reviewer dispatch, determine whether a Spec Review already exists.

If one exists, recover its durable Root Blocker state from the body and subsequent review/remediation updates.

Capture privately in the parent agent:

* existing `RB-*` IDs and stable invariants;
* current root status;
* cumulative acceptance matrix;
* affected semantic surfaces/reference kinds;
* Owner Overrides;
* previous reviewed and satisfied/closed `HEAD` values when available.

#### Cumulative Acceptance State

Acceptance obligations are cumulative for the lifetime of an active root.

Carry forward every established obligation unless durable state explicitly records that it was:

* superseded by a materially equivalent obligation;
* retired because current Spec/architecture no longer requires it; or
* Owner-overridden.

Omission from a later update does not retire a cell.

If durable state silently dropped an active obligation, continue carrying it and report the ledger drift to `$review-spec-remediation`.

#### Root Identity

An existing `RB-*` ID denotes one stable durable invariant.

A later finding maps to that root only when the finding is derivable from the recorded invariant without materially changing what the invariant means.

A shared subsystem, theme, file set, or architectural area is insufficient.

If accommodating a finding would materially broaden the invariant, treat it as a Candidate new root or possible root-definition gap for `$review-spec-remediation`.

Never rewrite, broaden, split, renumber, or assign Root Blocker IDs here.

## Reviewer Isolation Invariant

Durable review state is recovered **for parent reconciliation only**.

Do not provide reviewers with:

* Root Blocker IDs;
* Root Blocker invariants;
* root statuses;
* acceptance matrices;
* historical findings;
* sibling surfaces derived from the Root Blocker Ledger;
* remediation-ticket history;
* prior root mappings.

Reviewers must discover findings independently from their own axis authority.

Do not ask reviewers to:

* evaluate existing Root Blockers;
* map findings to Root Blockers;
* report Root Blocker status;
* preserve prior finding classifications.

The parent performs all root reconciliation only after the three reviewer result sets are complete and frozen.

## 5. Spawn Independent Reviewers

Spawn exactly three parallel sub-agents when all axes apply:

* one Standards;
* one Spec;
* one Architecture.

Never spawn more than one reviewer per axis.

Give every reviewer:

* aggregate diff and commits;
* Finding Taxonomy;
* only the source material authoritative for its axis.

Tell every reviewer:

1. review the complete aggregate Spec change independently;
2. use only its axis authority to decide whether a finding exists;
3. do not stop after the first blocker;
4. return every independently supported Blocking finding;
5. do not infer requirements from another review axis;
6. do not perform Root Blocker mapping;
7. do not perform remediation.

### Standards

Authority:

* `$coding-standards`;
* deterministic repository coding/process standards applicable to the changed code.

Review for deterministic standards violations and relevant non-tooling smells.

Skip issues reliably owned by verification tooling.

Every Blocking Standards finding must return:

```text
Finding: <deterministic violation>
Standard authority: <exact standard file/skill + rule or section>
Evidence: <source evidence>
```

A Blocking Standards finding is invalid unless the cited documented standard independently establishes the violation.

An ADR, architecture document, Spec requirement, Root Blocker invariant, prior finding, or preferred design does not establish a Standards violation.

Apply this boundary test:

> If deciding whether the finding exists requires determining the correct canonical owner, authority source, evidence lifecycle, platform boundary, dependency direction, canonical path, or architectural responsibility, it is not a Standards finding unless a deterministic coding standard independently forbids the concrete construction without relying on that architectural decision.

Examples:

* documented ban on `Any` in governed contracts → potentially Standards;
* duplicated local protocol violating an explicit DRY/interface standard → potentially Standards;
* metadata is the wrong source of governance authority → Architecture, not Standards;
* a materializer rather than a document must own evidence → Architecture, not Standards.

Return invalid-axis concerns neither as Blocking nor Advisory Standards findings.

### Spec

Authority:

* the originating Spec only.

Review for missing, partial, incorrect, or unauthorized behavior required by the Spec.

Every Blocking Spec finding must return:

```text
Finding: <Spec mismatch>
Spec authority: <exact requirement/section>
Evidence: <source evidence>
```

A Blocking Spec finding is invalid unless the cited Spec requirement independently establishes the expected behavior.

Do not import implementation prescriptions from:

* ADRs;
* current architecture docs;
* Root Blocker invariants;
* acceptance matrices;
* prior remediation findings.

If the Spec requires an outcome but does not prescribe the architecture used to achieve it, report the missing outcome without inventing an architectural implementation requirement.

### Architecture

Authority:

* current applicable architecture evaluated through `$review-architecture`.

Invoke `$review-architecture`.

Review the complete aggregate change against applicable architectural authority.

Every Blocking Architecture finding must preserve:

```text
Finding: <architecture violation>
Governing authority: <ADR/doc/invariant>
Evidence: <source evidence>
Architecture decision required: Yes | No
Routing: <existing-authority remediation | architecture resolution>
```

Return all independently supported Architecture findings.

## 6. Freeze and Validate Findings

Wait for all applicable reviewers to complete.

Freeze each axis's returned findings before Root Blocker reconciliation.

The parent may lightly validate citations and axis provenance.

It must not perform a second review.

### Axis-Provenance Gate

Accept a Blocking finding only when its originating axis independently supports it:

* Standards → exact deterministic Standards authority;
* Spec → exact originating Spec requirement;
* Architecture → `$review-architecture` and current architectural authority.

If a finding lacks native axis authority, discard it from Blocking results.

Do **not** move a rejected finding to another axis.

Do **not** repair a Standards finding by supplying Architecture authority.

Do **not** repair a Spec finding by supplying an ADR.

Do **not** create a new Architecture finding because another reviewer raised an architectural concern.

A concern exists in the final review only if the reviewer for the authoritative axis independently returned it.

## 7. Reconcile Findings Against Root State

Only after findings are frozen and validated may the parent expose durable Root Blocker state to the reconciliation step.

For each accepted Blocking finding:

1. compare its independently established invariant against existing stable Root Blockers;
2. map it to an existing root only when the recorded invariant already derives the finding;
3. otherwise classify it as `Candidate new root`;
4. if related to an existing root but accommodation would materially expand that root, mark:
   `Candidate new root — related to RB-<n>; possible root-definition gap`.

Root mapping changes **where remediation is tracked**, not whether a finding exists.

A Root Blocker Ledger can never create an axis finding that the independent reviewer did not establish.

### Root Status

For every previously open or regressed root, and every root receiving a current finding, report:

* **satisfied** — all carried obligations are established by available durable evidence and no accepted current finding violates them;
* **open** — one or more carried/current obligations are violated;
* **regressed** — behavior previously proven satisfied was actually broken later;
* **unproven** — available evidence is insufficient.

Do not infer satisfaction from plausible source alone.

Previously satisfied cumulative cells remain carried even when another cell is open.

### Existing Root Provenance

When a newly accepted violation maps to a previously satisfied/closed root and a prior satisfied/closed `HEAD` exists, inspect only the implicated historical evidence.

Classify:

* defect existed materially unchanged at prior satisfied/closed `HEAD` → **Missed prior finding**; root is `open`;
* defect was introduced or materially changed afterward → **Regression**; root may be `regressed`;
* origin cannot be determined confidently → **Origin uncertain**.

Do not call something a regression merely because it was discovered after closure.

Do not perform broad historical discovery solely for provenance.

### Candidate New Root History

When a previous reviewed `HEAD` exists, classify each Candidate new root as:

* **Missed prior finding**;
* **New/regressed finding**;
* **Origin uncertain**.

This is diagnostic only.

It does not assign a Root Blocker ID.

## 8. Aggregate

Present the independent review results first:

```text
## Standards
- <Blocking findings>
- <Advisories>
- or None

## Spec
- <Blocking findings>
- <Advisories>
- or None

## Architecture
- <Blocking findings>
- <Advisories>
- or None
```

Do not display discarded wrong-axis findings as blockers.

If a Root Blocker Ledger exists or Candidate roots were discovered, also present:

```text
## Root Blocker Status

RB-1: <satisfied | open | regressed | unproven>
RB-2: <satisfied | open | regressed | unproven>
...

Candidate new roots:
- <finding>
- or None
```

If several independently valid findings map to one root, say so explicitly without collapsing their axis identities.

## Architecture Human Handoff

If any independently returned Blocking Architecture finding has:

```text
Architecture decision required: Yes
```

collect all such unresolved architecture blockers and halt:

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
>    * Evidence: <evidence>
>    * Material consequence: <ownership/path/boundary/dependency/lifecycle/conflict>
>    * Governing context: <entities / ADRs / docs>
>    * Existing root: <RB-n or None>

Do not propose the architectural answer.

Blocking Architecture findings with `Architecture decision required: No` are ordinary remediation findings.

## 9. Pending Remediation

If Blocking findings remain and none require architecture resolution, persist a durable **Pending Review Remediation** section on the existing Spec Review issue.

If no Spec Review issue exists yet, create the parent tracking issue first using the existing Spec Review convention:

```text
Spec Review: <Feature Name>
```

Its first body line must be:

```markdown
**Parent Spec:** #<spec_issue_number>
```

Then persist:

```markdown
## Pending Review Remediation [YYYY-MM-DD HH:MM]

**Status:** pending
**Reviewed HEAD:** <full SHA>
**Reviewed Baseline:** <full Spec baseline SHA>
**Branch:** spec-<spec_issue_number>

### Standards
<accepted independently validated Blocking findings or None>

### Spec
<accepted independently validated Blocking findings or None>

### Architecture
<accepted independently validated Blocking findings with `Architecture decision required: No`, or None>

### Root mappings
- <finding> → <RB-n | Candidate new root>

### Root state
- <existing root statuses and stable invariants relevant to the findings>
- <cumulative carried acceptance obligations relevant to remediation>
- <satisfied obligations that remain preservation obligations>

### Provenance
- <finding/root>: <Missed prior finding | Regression | Origin uncertain>

### Root-definition / ledger notes
- <possible root-definition gaps or cumulative-ledger drift>
- or None
```

The pending packet is the durable input to `$review-spec-remediation`.

Persist only the already accepted review findings and parent reconciliation state.

Do not perform remediation synthesis, assign new Root Blocker IDs, or update acceptance obligations here.

Immediately before persistence require:

```bash
PENDING_HEAD=$(git rev-parse HEAD)

if [ "$PENDING_HEAD" != "$CURRENT_HEAD" ]; then
  echo "❌ HEAD changed during Spec review."
  exit 1
fi
```

`PENDING_HEAD` must equal the `Verified HEAD` from the current passing Spec Verification Receipt.

If persistence fails, review remediation is incomplete.

After persistence, invoke `$review-spec-remediation` with:

```text
Spec Review: <Feature Name> (<Issue URL>)
```

Wait for its result.

If `$review-spec-remediation` returns a genuine architecture blocker, apply the **Architecture Human Handoff** above and stop.

If it returns its `$to-tickets` Human Handoff, first present the Section 8 aggregate review results and Root Blocker Status required above, then append the returned Human Handoff exactly and stop.

If it reports that no Blocking findings remain, continue to the Exit Gate.

## Exit Gate

The review passes only when:

* current `HEAD` still matches the passing Spec Verification Receipt;
* all three independent axes have zero Blocking findings;
* every existing Root Blocker is satisfied or Owner-overridden;
* no Candidate new root remains unresolved.

Advisory findings may remain.

### Persist Exit Receipt

Only after the Exit Gate passes, persist on the parent Spec:

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

Any later commit makes the receipt stale.

### Spec Merge Cleanup Human Handoff

`$spec-merge-cleanup` has `allow_implicit_invocation: false`.

Do not invoke it implicitly.

After the Exit Receipt is persisted, halt with:

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

Do not close the Spec or Spec Review here.

`$spec-merge-cleanup` owns merge, closure, branch cleanup, and Wayfinder completion reconciliation.
