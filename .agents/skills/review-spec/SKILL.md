---
name: review-spec
description: Review a verified completed Spec against its persisted deterministic Spec contract, using ownership-scoped Standards review, independent Spec/Architecture review, and conditional saturation only when convergence risk is demonstrated.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Review Spec

Review the exact verified Spec state along applicable independent axes:

* **Standards** — deterministic repository standards applied only to Spec-owned/Mixed artifact classes;
* **Spec** — every obligation in the verified Spec Contract Manifest;
* **Architecture** — current applicable architecture governing the Spec's affected boundaries.

This is review-only. `$verify-spec` owns verification/tool execution and produces the contract being reviewed.

The default review uses **one fresh primary reviewer per applicable axis**. Additional fresh challengers are conditional and targeted; reviewer count is not a substitute for a complete review universe.

## Session Independence

Assume no prior conversational or agent-session state.

Recover all correctness-critical state from the invocation, repository, current passing **Spec Verification Receipt**, and durable tracker artifacts.

## Finding Taxonomy

* **Blocking** — must be remediated before review closes.
* **Advisory** — useful but non-blocking.
* **Owner-overridden** — explicitly accepted/rejected by the owner.
* **Scope-retired** — historical Spec Review root/cell proven not owned or required by this Spec under current attribution rules; preserved historically but removed from this Spec's active Blocking state.

Rules:

* exact Spec mismatches are Blocking;
* deterministic Standards violations are Blocking only when the violating surface is Spec-owned/Mixed or Spec-owned tracker state;
* Architecture violations returned by `$review-architecture` are Blocking;
* inherited-only repository defects unrelated to an exact Spec/Architecture obligation are not current-Spec Blocking findings;
* smells remain Advisory unless authority explicitly makes them mandatory.

## 1. Pin Baseline, Branch, and Verified HEAD

Resolve `BASELINE_COMMIT` from the Spec, verify the expected Spec branch, and require a clean worktree.

Capture:

```bash
CURRENT_HEAD=$(git rev-parse HEAD)
```

Recover the latest passing **Spec Verification Receipt** and require:

* `Status: passed`;
* `Verified HEAD == CURRENT_HEAD`;
* `Verified Baseline == BASELINE_COMMIT`;
* branch matches;
* complete Spec Contract Manifest present;
* complete per-cell Spec Contract Coverage present;
* `Spec Body Hash` and `Spec Contract Hash` present.

Any commit after verification requires fresh `$verify-spec`.

## 2. Validate the Shared Spec Contract

Invoke `$spec-contract` in `validate` mode using the manifest/counts/hash from the passing receipt.

Require `SPEC CONTRACT: VALID`.

This proves:

* current Spec body still matches what was verified;
* manifest counts/mappings are complete;
* manifest hash is unchanged;
* the exact verified contract is available;
* current Spec Change Ownership is freshly classified against the current default branch.

If validation fails, halt:

> ⚠️ **Spec review requires a current complete verification contract.**
>
> Please run:
>
> ```
> $verify-spec - <Spec Title> (<Spec URL>)
> ```

Do not repair or independently replace the verification manifest inside review.

### Ownership Boundary

Use the fresh ownership classification as follows:

* Standards universe → Spec-owned/Mixed repository surfaces + Spec-owned tracker surfaces only.
* Spec universe → the complete persisted Spec Contract Manifest; inspect any current surface needed to judge each obligation.
* Architecture universe → Spec Architecture Impact/current authority plus Spec-owned/Mixed and explicitly named/sibling surfaces required by that authority.
* Inherited-only repository drift is not Standards Blocking merely because it exists between the fixed baseline and `HEAD`.
* Inherited-only behavior may still cause a Spec/Architecture blocker when an exact obligation requires that behavior.

## Project Delivery Actionability Guard

Before reviewer dispatch or review-state persistence, perform the current `$project-delivery-management` reconciliation/guard required for a Wayfinder-managed Spec.

Require the Spec open, direct blockers closed, governance unambiguous, and at least one governing Wayfinder allowed.

Re-run immediately before persisting Pending Review Remediation or the final Exit Receipt.

## 3. Recover Durable Review State

The **conventional Spec Review issue** is the durable owner of review state for the parent Spec. Pending Review Remediation, Root Blocker ledger/reconciliation state, Scope corrections, and the final **Spec Review Exit Receipt** all belong on that one review issue, not on the parent Spec issue.

Resolve exactly one conventional Spec Review for the parent Spec before any review-state persistence. If none exists yet and this review reaches a persistence point, create/reuse the conventional Spec Review issue first. More than one matching review issue is ambiguous durable state and fails closed.

If a Spec Review exists, recover privately:

* existing `RB-*` IDs and stable invariants;
* current root/cell statuses;
* cumulative acceptance matrix;
* affected semantic surfaces/reference kinds;
* Owner Overrides;
* previous reviewed/satisfied heads.

Do not expose this historical state to axis reviewers.

### Scope Attribution Gate

Using current `$spec-contract` ownership, evaluate active historical roots/cells only for attribution:

A root/cell is eligible for **Scope retirement** only when durable evidence establishes all of:

1. its implicated repository/tracker surface is inherited-only or otherwise not owned by this Spec;
2. no Spec Contract Manifest cell requires the behavior;
3. no applicable Architecture Impact/current authority requires the behavior for this Spec;
4. retiring it does not remove another active Spec-owned obligation.

Do not scope-retire merely because a violation pre-existed the Spec. Pre-existing behavior can still be required by the Spec/Architecture axes.

Record proposed corrections for parent reconciliation only. Reviewers do not receive them.

## 4. Build the Review Universe

The parent builds routing coverage before dispatch. A complete universe is more important than reviewer count.

### Standards Universe

Create `STD-<n>` cells for:

* every Spec-owned/Mixed artifact group governed by deterministic repository standards;
* every applicable deterministic Standards rule/category for those surfaces;
* Spec-owned tracker transitions governed by deterministic workflow policy.

Do not create Standards cells for inherited-only repository surfaces.

### Spec Universe

Use the persisted Spec Contract Manifest **exactly**.

Each manifest cell is one Spec review cell. Do not collapse or substitute cells.

Before dispatch require:

```text
Manifest cells == Spec review cells
Missing manifest cells: 0
Unknown Spec review cells: 0
```

If the manifest says 27 numbered User Stories, the Spec universe necessarily maps all 27 source items.

A Spec reviewer that identifies a real originating-Spec obligation missing from the manifest has discovered a **contract defect**, not permission to silently expand the verified universe. Halt with `SPEC CONTRACT: INCOMPLETE` and require fresh `$verify-spec` after reporting the exact omitted source anchor.

### Architecture Universe

Create `ARCH-<n>` cells covering:

* every affected entity/delivery-process authority in Architecture Impact;
* every governing ADR/current architecture document/Wayfinder decision named by the Spec;
* every canonical owner/path/boundary/lifecycle/source-of-truth implicated by those authorities;
* Spec-owned/Mixed changed surfaces participating in them;
* sibling/alternate/named surfaces explicitly required to obey the same authority.

`$review-architecture` owns architecture evidence procedure.

## 5. Dispatch One Primary Reviewer per Applicable Axis

Spawn exactly one fresh primary reviewer for each applicable axis:

* Standards primary when Standards applies;
* Spec primary always;
* Architecture primary when Architecture applies.

Do not spawn a default challenger.

Give each primary:

* only its axis authority;
* its complete parent-built cells;
* only the evidence slices relevant to those cells;
* no Root Blocker history or prior reviewer findings.

### Primary Strategy

Use a combined coverage strategy:

1. authority-first: trace every supplied cell into all relevant surfaces;
2. adversarial-surface check: for each cell inspect applicable defaults/fallbacks/alternate entries/bypasses/fail-open paths before disposition.

The primary must:

1. disposition every supplied cell;
2. not stop after first blocker;
3. return every supported Blocking finding;
4. not perform Root mapping/remediation;
5. return no `unchecked`, `unknown`, `deferred`, or omitted cells.

Coverage state:

```text
checked-no-finding | blocking | advisory | not-applicable
```

`not-applicable` requires an exact reason.

### Axis Contracts

**Standards**

Every blocker cites an exact deterministic Standards authority and a Spec-owned/Mixed or Spec-owned tracker surface.

**Spec**

Every blocker cites the exact manifest cell and originating Spec source. Do not import ADR/Root Blocker requirements.

**Architecture**

The reviewer invokes `$review-architecture` and every blocker preserves:

```text
Finding:
Governing authority:
Evidence:
Architecture decision required: Yes | No
Routing: existing-authority remediation | architecture resolution
```

## 6. Conditional Challenge

A fresh targeted challenger is allowed only when a concrete trigger exists.

Challenge triggers:

1. **coverage trigger** — a primary cannot disposition a supplied cell or an applicable Standards/Architecture authority reveals a materially omitted cell;
2. **authority trigger** — source conflict, ambiguous authority, or parent cannot validate the cited native-axis authority;
3. **evidence trigger** — evidence is materially contradictory or insufficient to accept/reject a blocker;
4. **convergence trigger** — after root reconciliation, a newly accepted finding is a Missed prior finding against a previously satisfied root or exposes a root-definition gap.

For triggers 1–3, dispatch one fresh challenger over only the affected cells/question. Do not show it the primary's conclusion. Its job is independent resolution of the trigger, not a second full-axis review.

A valid challenger finding does not require primary agreement.

If targeted challenge cannot resolve the trigger, review is incomplete; do not persist remediation or PASS.

## 7. Freeze Axis Findings and Validate Provenance

Coverage is complete when:

* every parent-supplied cell is dispositioned;
* every targeted challenge cell is dispositioned;
* no Spec manifest cell is missing;
* no applicable Standards/Architecture cell is unchecked;
* every N/A axis/cell has a reason.

Freeze the de-duplicated current findings.

### Axis-Provenance Gate

Accept Blocking only when native axis authority independently establishes it:

* Standards → deterministic repository standard + owned surface;
* Spec → exact manifest cell/originating Spec;
* Architecture → `$review-architecture` + current authority.

Do not move a rejected finding to another axis.

## 8. Reconcile Against Durable Root State

Only after findings are frozen may the parent use Root Blocker history.

Map a finding to an existing root only when the stable invariant already derives it. Otherwise mark `Candidate new root`; if materially related but broader, mark `possible root-definition gap`.

For each newly accepted violation against a previously satisfied/closed root, inspect only implicated historical evidence and classify:

* **Missed prior finding** — defect existed materially unchanged at prior satisfied state;
* **Regression** — introduced/materially changed afterward;
* **Origin uncertain**.

Previously satisfied sibling cells remain satisfied unless directly contradicted.

### Convergence Saturation Gate

A **Missed prior finding** against a previously satisfied root, or a **root-definition gap**, proves that prior closure-domain enumeration was incomplete.

Before Pending Review Remediation:

1. derive a **Root Closure Domain Manifest** from the stable root invariant, current Spec contract, applicable architecture, current semantic surface families, and explicitly required sibling/alternate paths;
2. spawn exactly one fresh **saturation challenger** under the originating axis authority;
3. instruct it to inspect every domain item and to add/check any newly discovered sibling surface before returning;
4. require its final domain coverage to reach `unchecked 0`;
5. validate any additional findings through the normal Axis-Provenance Gate;
6. add supported findings to the current frozen set/root mapping before remediation persistence.

Do not spawn another generic whole-axis reviewer.

The saturation challenger must search to a fixed point within the bounded root invariant. If it returns unresolved domain coverage, review is incomplete.

This gate is the convergence response to demonstrated prior incompleteness; do not defer sibling discovery to another end-to-end review cycle.

## 9. Scope Corrections

After current finding/root reconciliation and saturation, reconcile proposed Scope retirements from Section 3.

For each correction record:

```text
Root/cell:
Action: scope-retire
Ownership evidence:
Spec-contract relationship: none
Architecture relationship: none
Historical finding preserved: yes
External repository follow-up: <optional reference or None>
```

Scope corrections are not Owner Overrides and do not erase historical findings.

If a root has both scope-retired and active Spec-owned cells, retire only the unrelated cells and recompute root status.

## 10. Aggregate Review Results

Present:

```text
## Standards
<Blocking/Advisory/None/N/A>

## Spec
<Blocking/Advisory/None>

## Architecture
<Blocking/Advisory/None/N/A>
```

Then coverage:

```text
Standards: <n cells | N/A>; primary complete; targeted challengers <n>; unchecked 0
Spec: <manifest n> cells; primary complete; targeted challengers <n>; unchecked 0
Architecture: <n cells | N/A>; primary complete; targeted challengers <n>; unchecked 0
Saturation challengers: <n>
```

Also report reviewer effectiveness:

```text
Primary validated findings: <n>
Targeted challenger-only validated findings: <n>
Saturation-only validated findings: <n>
```

This telemetry is diagnostic; it does not change finding validity.

## Architecture Human Handoff

If any Blocking Architecture finding has `Architecture decision required: Yes`, collect all such blockers and halt with:

> ⚠️ **Spec review is blocked by unresolved architecture.**
>
> Please run:
>
> ```
> $architecture-remediation - <Spec Title> (<Spec URL>) — <concise blocker-set summary>
> ```

Do not propose the architectural answer.

## 11. Pending Remediation

If architecture-conforming Blocking findings remain **or Scope corrections must update existing durable review state**, re-run the Project Delivery Actionability Guard.

Create/reuse the conventional Spec Review issue and persist:

```markdown
## Pending Review Remediation [YYYY-MM-DD HH:MM]

**Status:** pending
**Reviewed HEAD:** <SHA>
**Reviewed Baseline:** <SHA>
**Branch:** spec-<n>
**Spec Body Hash:** <hash>
**Spec Contract Hash:** <hash>

### Standards
<accepted current Blocking findings / None / N/A>

### Spec
<accepted current Blocking findings / None>

### Architecture
<accepted Architecture decision required: No findings / None / N/A>

### Review Coverage
- Standards: <coverage>
- Spec: <manifest count>; primary complete; targeted challengers <n>; unchecked 0
- Architecture: <coverage>
- Saturation challengers: <n>

### Reviewer Effectiveness
- Primary validated findings: <n>
- Targeted challenger-only validated findings: <n>
- Saturation-only validated findings: <n>

### Root Mappings
<current mappings>

### Root State
<relevant stable roots/cells>

### Provenance
<Missed prior | Regression | Origin uncertain>

### Scope Corrections
<scope-retire entries or None>

### Saturation
<triggered root/domain/result or None>
```

Immediately before persistence require `HEAD` still equals the passing receipt.

Invoke `$review-spec-remediation` internally and wait.

If it returns a `$to-tickets` handoff, present the aggregate review first and append the handoff exactly. If no active Blocking remains after corrections, continue to Exit Gate.

## Exit Gate

PASS requires:

* current `HEAD` still matches current verification receipt;
* `$spec-contract` remains valid;
* every manifest cell reviewed;
* every applicable Standards/Architecture cell reviewed;
* no unresolved challenge/saturation coverage;
* zero current Blocking findings;
* every existing Root Blocker is `satisfied`, `owner-overridden`, or `scope-retired`;
* no unresolved Candidate root remains.

Advisories and unrelated inherited findings may remain.

### Persist Exit Receipt

Re-run Project Delivery Actionability Guard and persist the Exit Receipt on the **conventional Spec Review issue** resolved in Section 3. Do not persist the review Exit Receipt on the parent Spec issue.

Require the review issue to durably identify the current parent Spec before writing. The receipt is review-owned authorization consumed later by `$spec-merge-cleanup`; the parent Spec continues to own its Spec Verification Receipt and workspace metadata.

Persist:

```markdown
## Spec Review Exit Receipt

**Status:** passed
**Reviewed HEAD:** <SHA>
**Reviewed Baseline:** <SHA>
**Branch:** spec-<n>
**Spec Body Hash:** <hash>
**Spec Contract Hash:** <hash>
**Blocking findings:** 0
**Root blockers:** satisfied/owner-overridden/scope-retired
**Candidate new roots:** 0
**Review coverage:** complete
**Primary reviewers:** Standards <1|N/A>; Spec 1; Architecture <1|N/A>
**Targeted challengers:** <n>
**Saturation challengers:** <n>
**Unchecked coverage cells:** 0
```

Any later commit or Spec-body change makes the receipt stale.

### Spec Merge Cleanup Human Handoff

After receipt persistence, halt with:

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
