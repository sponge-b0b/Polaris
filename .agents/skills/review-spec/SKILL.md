---
name: review-spec
description: Review a verified completed Spec along applicable Standards, Spec, and Architecture axes, then reconcile independently discovered findings against durable Root Blocker state and route remaining blockers.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Review Spec

Review the exact verified Spec state along independent axes:

* **Standards** — deterministic repository standards applicable to the changed artifact classes;
* **Spec** — originating Spec requirements;
* **Architecture** — resolved architecture and current authorities when architecture is affected.

This is review-only. Do not run `pytest`, Ruff, Mypy, graph updates, duplication scans, `$wiki-lint`, or other verification commands. `$verify-spec` owns verification.

`$review-spec` requires a passing `$verify-spec` receipt for the exact current `HEAD`.

Review discipline is applicability-driven:

> Repository location does not determine review discipline. Derive applicable standards, architecture authority, and adversarial surfaces from the Spec obligations and the actual changed surfaces.

The Spec axis always applies. Standards and Architecture apply only when authoritative material exists for those axes. Mixed work applies the union of relevant surfaces; do not collapse it to one dominant type.

The review protocol is coverage-driven. Optimize for exhaustive blocker discovery inside one review invocation rather than relying on repeated end-to-end lifecycle rounds to reveal omitted findings.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting. Prior-session summaries or remembered conclusions are routing context only and must not substitute for durable evidence.

If required durable state cannot be recovered, report the missing artifact rather than infer or recreate it.

## Finding Taxonomy

* **Blocking** — must be remediated before review closes.
* **Advisory** — useful but non-blocking.
* **Owner-overridden** — explicitly accepted/rejected by the owner; suppress from future blocking counts.

Rules:

* Spec mismatches and deterministic applicable Standards violations are Blocking by default.
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

Verify the expected Spec branch when the Spec uses one:

```bash
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "spec-<spec_issue_number>" ]; then
  echo "❌ Expected spec-<spec_issue_number>; current branch is $CURRENT_BRANCH."
  exit 1
fi

git rev-parse "$BASELINE_COMMIT"
```

Capture repository evidence:

```bash
git diff "$BASELINE_COMMIT"...HEAD
git log "$BASELINE_COMMIT"..HEAD --oneline
```

A non-empty repository diff is required only when the Spec changes repository content. A tracker-only Spec may have an empty diff only when the passing verification receipt and durable Spec/ticket evidence establish that no repository mutation was required.

### 2. Resolve the Spec

Find the originating Spec from:

1. commit references;
2. user-provided issue/path;
3. matching repository Spec;
4. user only if still unresolved.

Capture its **Architecture Impact** and any change-surface classification from the current passing verification receipt.

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
* `Branch` equals the current Spec branch;
* recorded change surfaces/gates, when present, do not contradict current durable evidence.

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

Do not invoke `$verify-spec` implicitly. Any commit after verification makes the receipt stale.

#### Project Delivery Actionability Guard

Before reviewer dispatch or any review-state persistence, determine whether the Spec is Wayfinder-managed from durable `wayfinder-source`, `wayfinder-remediation`, and reconciled `Spec Handoff` evidence.

An intentionally non-Wayfinder Spec keeps the existing review lifecycle. Do not invent a governing Wayfinder merely to enroll it into project focus.

For a Wayfinder-managed Spec:

1. require the Spec issue to be open;
2. read its complete native `blocked by` relationship set and fail closed if blocker data is truncated or unreadable;
3. stop if any direct blocker is open;
4. recover every current governing Wayfinder; ambiguous governance fails closed rather than choosing one;
5. invoke `$project-delivery-management` `reconcile`;
6. invoke `$project-delivery-management` `guard <Wayfinder>` for every governor;
7. require at least one governor to return `PROJECT DELIVERY GUARD: ALLOWED`.

If no governor is allowed, stop before reviewer dispatch and report the governing maps, their guard results, current focus, and the explicit human `$project-delivery-management` focus/switch/parallel choices. `$review-spec` never establishes, switches, or broadens focus.

A legitimately reopened blocker Spec makes this guard fail again through the unchanged native dependency edge. A prior passing verification receipt does not override current dependency/focus state.

`$review-spec-remediation` is an internal continuation of this already-authorized review lifecycle and inherits the parent project-delivery authorization. A later distinct human `$review-spec` invocation performs this guard again.

Re-run this guard immediately before persisting either **Pending Review Remediation** or the final **Spec Review Exit Receipt**. If dependency/focus authorization changed during review, do not persist lifecycle advancement under stale authorization.

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

Carry forward every established obligation unless durable state explicitly records that it was superseded by a materially equivalent obligation, retired because current Spec/architecture no longer requires it, or Owner-overridden.

Omission from a later update does not retire a cell. If durable state silently dropped an active obligation, continue carrying it and report the ledger drift to `$review-spec-remediation`.

#### Root Identity

An existing `RB-*` ID denotes one stable durable invariant.

A later finding maps to that root only when the finding is derivable from the recorded invariant without materially changing what the invariant means. A shared subsystem, theme, file set, artifact type, or architectural area is insufficient.

If accommodating a finding would materially broaden the invariant, treat it as a Candidate new root or possible root-definition gap for `$review-spec-remediation`.

Never rewrite, broaden, split, renumber, or assign Root Blocker IDs here.

## Reviewer Isolation Invariant

Durable review state is recovered **for parent reconciliation only**.

Do not provide reviewers with Root Blocker IDs/invariants/statuses, acceptance matrices, historical findings, ledger-derived sibling surfaces, remediation-ticket history, or prior root mappings.

Reviewers must discover findings independently from their own axis authority. The parent performs root reconciliation only after both independent passes for every applicable axis are coverage-complete and their finding sets are frozen.

## 5. Build the Review Universe and Spawn Independent Reviewers

Before reviewer dispatch, build a **Review Universe** from current authoritative inputs. This is coverage routing, not review. Do not use prior Root Blocker findings, acceptance cells, remediation tickets, or previous reviewer conclusions to construct it.

### Change-Surface Inventory

Derive the complete surface set from the originating Spec, passing verification receipt, aggregate repository diff/commits, and durable tracker mutations.

Use these classes as needed:

* **Code**;
* **Tests**;
* **Documentation**;
* **Agent skills / workflow policy**;
* **Repository configuration**;
* **CI / automation**;
* **Data / schema / migrations**;
* **Tracker-only state**.

Group every changed artifact/state transition into at least one class. `Mixed` means the union of relevant classes.

Also capture every boundary, lifecycle, authority, interface, persistence/release/evaluation path, tracker relationship, or sibling/alternate surface explicitly named by the Spec or materially implicated by the aggregate change.

### Axis Applicability

Determine applicability before dispatch:

* **Spec:** always applicable.
* **Standards:** applicable when one or more changed surfaces are governed by deterministic repository standards independent of the Spec/Architecture axes.
* **Architecture:** applicable when Architecture Impact is not `none`, current architecture authority governs a changed surface, or the change materially realizes/changes an architectural owner, boundary, dependency, lifecycle, or source of truth.

An inapplicable Standards or Architecture axis must be recorded as `not-applicable` with a concrete reason. Do not spawn reviewers for an inapplicable axis merely to produce empty output.

### Standards cells

For an applicable Standards axis, create `STD-<n>` cells covering:

* every changed artifact group subject to deterministic repository standards;
* every applicable documented Standards rule/category for those surfaces.

Coding standards apply to code only when code is governed by them. Documentation, skill/workflow, configuration, CI, migration, or tracker standards must come from their own documented authority rather than being inferred from `$coding-standards`.

Do not silently exempt a changed surface. A surface outside Standards scope must be represented as `not-applicable` with a reason when needed for completeness.

### Spec cells

Create `SPEC-<n>` cells for every explicit normative Spec obligation, including:

* every numbered User Story;
* every Implementation Decision bullet;
* every Testing Decision bullet;
* every Out of Scope prohibition;
* every materially unique `must`, `must not`, `only`, `cannot`, fail-closed, unavailable, reconstruction, idempotency, no-fallback, no-bypass, or equivalent normative requirement elsewhere in the Spec.

Do not collapse materially distinct positive and negative obligations merely because they concern the same subsystem or workflow.

Attach every relevant changed/named surface to its cells, including tracker, docs, skill/workflow, configuration, CI, schema, code, tests, and alternate paths as applicable.

### Architecture cells

For an applicable Architecture axis, create `ARCH-<n>` cells covering:

* every affected entity or delivery-process authority in Architecture Impact;
* every governing ADR/current architecture document/Wayfinder decision named by the Spec or current context;
* every named canonical owner/path/boundary/lifecycle/source-of-truth implicated by those authorities;
* changed surfaces participating in those authorities;
* sibling/alternate paths explicitly required to obey the same authority.

`$review-architecture` owns architecture dimensions and evidence procedure; do not duplicate its algorithm here. Feed it the actual architecture surfaces. Do not manufacture runtime/product-code cells for a delivery-process or documentation architecture change.

### Dual Independent Passes

Spawn exactly **two fresh reviewers per applicable axis**:

* Standards primary + challenger when Standards applies;
* Spec primary + challenger always;
* Architecture primary + challenger when Architecture applies.

Never show one pass another pass's findings, coverage dispositions, reasoning, or historical review state.

Give each pass the aggregate repository/tracker change evidence, Finding Taxonomy, complete axis Review Universe, only source material authoritative for its axis, and one pass strategy.

Use distinct strategies:

**Primary — authority-first**

Start from each rule/requirement/authority cell and trace it into all relevant changed/named surfaces.

**Challenger — adversarial-surface-first**

Start from the actual changed and named surfaces and trace backward to authority. Derive adversarial probes from the surface instead of using a fixed code checklist.

Examples:

* code/runtime → optional dependencies, defaults/fallbacks, direct construction, alternate entry points, persistence/release/evaluation paths;
* skills/workflow/tracker → bypassable guards, duplicated ownership, inferred authority, stale handoffs, non-idempotent writes, re-entry failures, projection becoming authority, partial-mutation recovery;
* documentation/ADR → contradictory normative text, stale lifecycle/realization state, duplicated source-of-truth claims;
* configuration/CI → alternate configuration paths, defaults, disabled/enabled automation contradictions, failure behavior;
* migrations/schema → ordering, reversibility/applicability where required, compatibility and persistence boundaries;
* every surface → negative requirements such as `cannot`, `must not`, `only`, fail closed, and `without fallback`.

The challenger is not a critic of the primary. It is a fully independent second discovery pass.

### Required Reviewer Contract

Tell every reviewer:

1. review the complete assigned Review Universe independently;
2. use only its axis authority to decide whether a finding exists;
3. do not stop after the first blocker;
4. return every independently supported Blocking finding;
5. do not infer requirements from another review axis;
6. do not perform Root Blocker mapping;
7. do not perform remediation;
8. disposition every supplied coverage cell;
9. add a new coverage cell when its own authority reveals a materially relevant omitted requirement/surface rather than silently broadening an existing cell;
10. continue until no supplied or newly discovered cell remains unchecked.

Every coverage cell must end in exactly one state:

```text
checked-no-finding | blocking | advisory | not-applicable
```

`not-applicable` requires a concrete reason. `unknown`, `unchecked`, `deferred`, omitted, or “not reviewed due to time/context” is incomplete review. A finding does not discharge other cells.

### Standards

Authority:

* deterministic repository standards applicable to the assigned changed artifact classes;
* `$coding-standards` only for surfaces it actually governs.

Review for deterministic standards violations and relevant non-tooling smells. Skip issues reliably owned by verification tooling.

For each Standards coverage cell, return:

```text
Coverage: STD-<n>
State: <checked-no-finding | blocking | advisory | not-applicable>
Standard authority: <exact standard file/skill + rule or section>
Surfaces inspected: <files/artifacts/state>
Evidence/reason: <concise evidence or N/A reason>
```

Every Blocking Standards finding must cite a documented standard that independently establishes the violation. An ADR, architecture document, Spec requirement, Root Blocker invariant, prior finding, or preferred design does not establish a Standards violation.

Apply this boundary test:

> If deciding whether the finding exists requires determining a canonical owner, authority source, evidence lifecycle, platform boundary, dependency direction, canonical path, or architectural responsibility, it is not a Standards finding unless a deterministic repository standard independently forbids the concrete construction.

Return invalid-axis concerns neither as Blocking nor Advisory Standards findings.

### Spec

Authority: the originating Spec only.

Review for missing, partial, incorrect, or unauthorized outcomes required by the Spec across every applicable surface.

For each Spec coverage cell, return:

```text
Coverage: SPEC-<n>
State: <checked-no-finding | blocking | advisory | not-applicable>
Spec authority: <exact requirement/section>
Surfaces inspected: <files/artifacts/tracker/boundaries>
Evidence/reason: <concise evidence or N/A reason>
```

For negative requirements, inspect the intended authoritative path/state and relevant sibling/alternate/default/fallback/bypass paths appropriate to the surface. Do not infer compliance only because the intended result exists once.

Every Blocking Spec finding must cite the exact originating Spec requirement that independently establishes the expected outcome. Do not import implementation prescriptions from ADRs, current architecture docs, Root Blocker invariants, acceptance matrices, or prior remediation findings.

### Architecture

Authority: current applicable architecture evaluated through `$review-architecture`.

Both Architecture reviewers must independently invoke `$review-architecture` with the aggregate repository/tracker change evidence, originating Spec and Architecture Impact, complete Architecture Review Universe, and their assigned pass strategy.

Every Blocking Architecture finding must preserve:

```text
Finding: <architecture violation>
Governing authority: <ADR/doc/Wayfinder/invariant>
Evidence: <source/tracker evidence>
Architecture decision required: Yes | No
Routing: <existing-authority remediation | architecture resolution>
```

Each Architecture result must also return the complete `$review-architecture` Coverage section.

## 6. Complete Coverage, Freeze, and Validate Findings

Wait for all applicable primary and challenger reviewers to complete.

For each applicable axis, form the union of parent-supplied Review Universe cells and additional cells independently discovered by either pass.

Coverage is complete only when both independent passes have dispositioned every cell in that union. If one pass adds a cell that the sibling pass did not inspect, continue or dispatch a fresh completion pass for only the uncovered cells using the same axis authority/strategy without showing the sibling finding/disposition.

Do not freeze findings, persist Pending Review Remediation, issue a Human Handoff, or pass review while any applicable cell is missing, unchecked, unknown, deferred, or silently omitted.

For an inapplicable Standards/Architecture axis, require its concrete `not-applicable` reason and no reviewer dispatch.

Require final coverage summary in this form:

```text
Standards: <n> cells; primary complete; challenger complete; unchecked 0
# or: Standards: not-applicable — <reason>
Spec: <n> cells; primary complete; challenger complete; unchecked 0
Architecture: <n> cells; primary complete; challenger complete; unchecked 0
# or: Architecture: not-applicable — <reason>
```

### Freeze Findings

After the Review Completeness Gate succeeds, freeze each applicable axis's results. The final axis finding set is the de-duplicated union of independently returned findings from both passes.

A valid finding does not require both passes to discover it. A `checked-no-finding` disposition from one pass does not suppress an independently supported finding from the other.

The parent may lightly validate citations and axis provenance; it must not perform a second review.

### Axis-Provenance Gate

Accept a Blocking finding only when its originating axis independently supports it:

* Standards → exact deterministic applicable Standards authority;
* Spec → exact originating Spec requirement;
* Architecture → `$review-architecture` and current architectural authority.

If a finding lacks native axis authority, discard it from Blocking results. Do not move a rejected finding to another axis or repair its provenance with another axis's authority.

## 7. Reconcile Findings Against Root State

Only after findings are frozen and validated may the parent expose durable Root Blocker state to reconciliation.

For each accepted Blocking finding:

1. compare its independently established invariant against existing stable Root Blockers;
2. map it to an existing root only when the recorded invariant already derives the finding;
3. otherwise classify it as `Candidate new root`;
4. if related to an existing root but accommodation would materially expand that root, mark `Candidate new root — related to RB-<n>; possible root-definition gap`.

Root mapping changes where remediation is tracked, not whether a finding exists. A Root Blocker Ledger can never create an axis finding that an independent reviewer did not establish.

### Root Status

For every previously open or regressed root, and every root receiving a current finding, report:

* **satisfied** — all carried obligations are established by durable evidence and no accepted current finding violates them;
* **open** — one or more carried/current obligations are violated;
* **regressed** — behavior previously proven satisfied was actually broken later;
* **unproven** — available evidence is insufficient.

Do not infer satisfaction from plausible source alone. Previously satisfied cumulative cells remain carried even when another cell is open.

### Existing Root Provenance

When a newly accepted violation maps to a previously satisfied/closed root and a prior satisfied/closed `HEAD` exists, inspect only the implicated historical evidence.

Classify:

* defect existed materially unchanged at prior satisfied/closed `HEAD` → **Missed prior finding**; root is `open`;
* defect was introduced or materially changed afterward → **Regression**; root may be `regressed`;
* origin cannot be determined confidently → **Origin uncertain**.

Do not call something a regression merely because it was discovered after closure. Do not perform broad historical discovery solely for provenance.

### Candidate New Root History

When a previous reviewed `HEAD` exists, classify each Candidate new root as **Missed prior finding**, **New/regressed finding**, or **Origin uncertain**. This is diagnostic only and does not assign a Root Blocker ID.

## 8. Aggregate

Present applicable independent review results first:

```text
## Standards
- <findings/advisories>
- or None
- or Not applicable — <reason>

## Spec
- <findings/advisories>
- or None

## Architecture
- <findings/advisories>
- or None
- or Not applicable — <reason>
```

Immediately after the axes, add one compact coverage line showing each applicable axis's cell/pass counts, explicit N/A axes, and `unchecked 0`.

If a Root Blocker Ledger exists or Candidate roots were discovered, also present Root Blocker Status and Candidate new roots.

## Architecture Human Handoff

If any independently returned Blocking Architecture finding has `Architecture decision required: Yes`, collect all such unresolved architecture blockers and halt:

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
>    * Governing context: <entities / ADRs / docs / Wayfinder decisions>
>    * Existing root: <RB-n or None>

Do not propose the architectural answer. Blocking Architecture findings with `Architecture decision required: No` are ordinary remediation findings.

## 9. Pending Remediation

If Blocking findings remain and none require architecture resolution, re-run the **Project Delivery Actionability Guard** before persisting review-remediation state.

Persist a durable **Pending Review Remediation** section on the existing Spec Review issue, or create the conventional `Spec Review: <Feature Name>` issue with first body line `**Parent Spec:** #<spec_issue_number>` when none exists.

Persist:

```markdown
## Pending Review Remediation [YYYY-MM-DD HH:MM]

**Status:** pending
**Reviewed HEAD:** <full SHA>
**Reviewed Baseline:** <full Spec baseline SHA>
**Branch:** spec-<spec_issue_number>
**Change surfaces:** <classified surfaces>

### Standards
<accepted Blocking findings, None, or Not applicable — reason>

### Spec
<accepted Blocking findings or None>

### Architecture
<accepted Blocking findings with Architecture decision required: No, None, or Not applicable — reason>

### Review coverage
- Standards: <coverage or N/A reason>
- Spec: <n> cells; primary complete; challenger complete; unchecked 0
- Architecture: <coverage or N/A reason>

### Root mappings
- <finding> → <RB-n | Candidate new root>

### Root state
- <relevant root statuses/stable invariants/cumulative obligations>

### Provenance
- <finding/root>: <Missed prior finding | Regression | Origin uncertain>

### Root-definition / ledger notes
- <gaps/drift or None>
```

The pending packet is the durable input to `$review-spec-remediation`. Persist only already accepted review findings, completed coverage summary, and parent reconciliation state. Do not perform remediation synthesis or assign/update Root Blocker definitions here.

Immediately before persistence require `HEAD` still equals the `Verified HEAD` from the passing verification receipt. Persistence failure means review remediation is incomplete.

After persistence, invoke `$review-spec-remediation` with the Spec Review issue and wait for its result. The child inherits this review invocation's project-delivery authorization.

If it returns a genuine architecture blocker, apply the Architecture Human Handoff. If it returns its `$to-tickets` Human Handoff, first present Section 8 results then append that handoff exactly. If it reports no Blocking findings remain, continue to the Exit Gate.

## Exit Gate

The review passes only when:

* current `HEAD` still matches the passing Spec Verification Receipt;
* the Review Completeness Gate passed for every applicable axis;
* both independent passes are complete for every applicable axis;
* every inapplicable axis has a concrete N/A reason;
* zero applicable Review Universe cells remain unchecked;
* every applicable axis has zero Blocking findings;
* every existing Root Blocker is satisfied or Owner-overridden;
* no Candidate new root remains unresolved.

Advisory findings may remain.

### Persist Exit Receipt

Only after the Exit Gate passes, re-run the **Project Delivery Actionability Guard** when the Spec is Wayfinder-managed. If current dependency/focus authorization no longer permits advancement, do not persist an exit receipt or hand off cleanup under stale authorization.

Persist on the parent Spec:

```markdown
## Spec Review Exit Receipt

**Status:** passed
**Reviewed HEAD:** <full SHA>
**Reviewed Baseline:** <full Spec baseline SHA>
**Branch:** spec-<spec_issue_number>
**Change surfaces:** <classified surfaces>
**Blocking findings:** 0
**Root blockers:** satisfied-or-owner-overridden
**Candidate new roots:** 0
**Review coverage:** complete
**Independent passes:** Standards <2/2 | N/A>; Spec 2/2; Architecture <2/2 | N/A>
**Unchecked coverage cells:** 0
```

Immediately before persistence, require current `HEAD` still equals the captured review `CURRENT_HEAD` and the passing verification receipt's `Verified HEAD`.

Receipt persistence failure means review is incomplete. Any later commit makes the receipt stale.

### Spec Merge Cleanup Human Handoff

`$spec-merge-cleanup` has `allow_implicit_invocation: false`.

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

Do not close the Spec or Spec Review here. `$spec-merge-cleanup` owns merge, closure, branch cleanup, and Wayfinder completion reconciliation.
