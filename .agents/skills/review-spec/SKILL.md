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

Resolve the repository and read the parent Spec's complete durable comment history once:

```bash
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
SPEC_NUMBER=<spec_issue_number>

SPEC_COMMENT_PAGES=$(
  gh api --paginate --slurp \
    -H "X-GitHub-Api-Version: 2026-03-10" \
    "repos/$REPO/issues/$SPEC_NUMBER/comments?per_page=100"
)
```

Resolve `BASELINE_COMMIT` from that complete snapshot:

```bash
BASELINE_COMMIT=$(
  printf '%s\n' "$SPEC_COMMENT_PAGES" \
    | jq -r '
        [.[][]
         | select((.body // "") | contains("**Baseline Commit Hash:**"))
         | {id, created_at, body}]
        | sort_by(.created_at, .id)
        | last
        | .body // ""
        | capture("\\*\\*Baseline Commit Hash:\\*\\*\\s+(?<sha>[0-9a-fA-F]{40})").sha // empty'
)
```

Verify the expected Spec branch and require a clean worktree.

Capture:

```bash
CURRENT_HEAD=$(git rev-parse HEAD)
```

Select exactly the latest durable comment whose body contains `## Spec Verification Receipt`, ordered by `created_at` then comment `id`:

```bash
VERIFICATION_RECEIPT_JSON=$(
  printf '%s\n' "$SPEC_COMMENT_PAGES" \
    | jq -c '
        [.[][]
         | select((.body // "") | contains("## Spec Verification Receipt"))
         | {id, created_at, html_url, body}]
        | sort_by(.created_at, .id)
        | last // empty'
)
```

That newest receipt is the only verification candidate. Do not use `gh issue view --json comments`, an unpaginated comment read, or walk backward to an older receipt when the newest one is malformed or stale.

Require the selected receipt:

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

A **conventional Spec Review issue** is a blocker/remediation artifact, not the owner of a clean review pass. It exists only when review enters blocker/remediation state or when existing durable review state must be reconciled. The parent Spec owns the final **Spec Review Exit Receipt**.

Resolve any existing conventional review issue through one prescribed REST read:

```bash
PARENT_MARKER="**Parent Spec:** #$SPEC_NUMBER"

resolve_spec_review_issue() {
  REVIEW_PAGES=$(
    gh api --paginate --slurp \
      -H "X-GitHub-Api-Version: 2026-03-10" \
      "repos/$REPO/issues?state=all&per_page=100"
  )

  REVIEW_MATCHES=$(
    printf '%s\n' "$REVIEW_PAGES" \
      | jq -c --arg parent "$PARENT_MARKER" '
          [.[][]
           | select(.pull_request == null)
           | select(.title | startswith("Spec Review:"))
           | select((.body // "") | contains($parent))
           | {number, state, url: .html_url}]'
  )

  REVIEW_COUNT=$(printf '%s\n' "$REVIEW_MATCHES" | jq 'length')

  if [ "$REVIEW_COUNT" -gt 1 ]; then
    echo "❌ More than one conventional Spec Review identifies parent Spec #$SPEC_NUMBER."
    exit 1
  fi

  if [ "$REVIEW_COUNT" -eq 1 ]; then
    SPEC_REVIEW_ISSUE_NUMBER=$(printf '%s\n' "$REVIEW_MATCHES" | jq -r '.[0].number')
  else
    SPEC_REVIEW_ISSUE_NUMBER=""
  fi
}

resolve_spec_review_issue
```

Do not infer review ownership from Project fields, labels, prior conversation, title similarity alone, or a receipt copied onto the parent Spec.

If no conventional Spec Review exists, keep `SPEC_REVIEW_ISSUE_NUMBER` empty. A clean first-pass review with zero Blocking findings must not create one.

Create a conventional Spec Review only when Blocking findings require remediation. At that blocker persistence point, create it once and re-resolve only through the same canonical read:

```bash
ensure_spec_review_issue() {
  resolve_spec_review_issue

  if [ -n "$SPEC_REVIEW_ISSUE_NUMBER" ]; then
    return 0
  fi

  SPEC_TITLE=$(gh api "repos/$REPO/issues/$SPEC_NUMBER" --jq .title)
  REVIEW_TITLE_BODY=${SPEC_TITLE#Spec: }

  gh api --method POST "repos/$REPO/issues" \
    -f title="Spec Review: $REVIEW_TITLE_BODY" \
    -f body="$PARENT_MARKER" >/dev/null

  for attempt in 1 2 3 4; do
    resolve_spec_review_issue

    if [ -n "$SPEC_REVIEW_ISSUE_NUMBER" ]; then
      return 0
    fi

    if [ "$attempt" -lt 4 ]; then
      sleep 1
    fi
  done

  echo "❌ Conventional Spec Review creation could not be confirmed after bounded canonical re-resolution."
  exit 1
}
```

The POST is single-shot. A transient read-after-write miss is handled only by bounded retries of `resolve_spec_review_issue`; never POST a second Spec Review merely because the first canonical reread is empty.

Do not call `ensure_spec_review_issue` from a clean PASS path. Re-resolution after blocker-driven creation is mandatory. If a concurrent or historical duplicate makes the result ambiguous, fail closed rather than choosing one.

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

If architecture-conforming Blocking findings remain, call `ensure_spec_review_issue` from Section 3 and persist on that resolved conventional Spec Review issue.

If no Blocking findings remain and only Scope corrections must update existing durable review state, require an already-existing conventional Spec Review issue and persist there. Do not create a Spec Review issue solely for Scope corrections.

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

### Atomic Pending Packet Persistence

Before any Pending Review Remediation comment mutation, render the **complete** packet into `PENDING_REVIEW_FILE=$(mktemp)`. Treat Markdown as data: use Python or `printf`; never use an unquoted heredoc. If a heredoc contains literal Markdown, quote its delimiter (`<<'EOF'`) and write dynamic values separately. Ensure the file ends with exactly one newline.

Pre-validate the rendered file before POST. Require the exact pending header/status, reviewed HEAD/baseline/branch, Spec body/contract hashes, all packet sections exactly once, and no unresolved template placeholders. Immediately before POST require `HEAD` still equals the passing verification receipt.

POST the validated packet exactly once to the resolved conventional Spec Review issue using file-based JSON encoding, then read back that exact comment and compare bytes before invoking `$review-spec-remediation`:

```bash
PENDING_JSON=$(mktemp)
COMMENT_JSON=$(mktemp)
READBACK_FILE=$(mktemp)

jq -Rs '{body: .}' "$PENDING_REVIEW_FILE" > "$PENDING_JSON"
gh api --method POST \
  "repos/$REPO/issues/$SPEC_REVIEW_ISSUE_NUMBER/comments" \
  --input "$PENDING_JSON" > "$COMMENT_JSON"

COMMENT_ID=$(jq -r .id "$COMMENT_JSON")
COMMENT_URL=$(jq -r .html_url "$COMMENT_JSON")
[ -n "$COMMENT_ID" ] && [ "$COMMENT_ID" != "null" ]

gh api "repos/$REPO/issues/comments/$COMMENT_ID" \
  | jq -j '.body' > "$READBACK_FILE"

cmp -s "$PENDING_REVIEW_FILE" "$READBACK_FILE"
```

Run the same deterministic packet validation against `READBACK_FILE`. Only exact readback plus post-validation completes persistence. If POST succeeds but readback or validation fails, stop, report `COMMENT_URL`, and do not invoke `$review-spec-remediation`, create a corrective second packet, or patch the malformed comment in the same invocation.

Invoke `$review-spec-remediation` internally only after Pending packet persistence is complete, and wait.

### Mandatory Project Reconciliation — Review Remediation

When `$review-spec-remediation` durably leaves one or more architecture-conforming Blocking roots active and returns a `$to-tickets` handoff, derive the remediation lifecycle from that persisted state and invoke `$project-tracking` as prescribed internal composition **before** presenting the handoff.

Use one reconciliation set:

* parent Spec → base `Spec / Review Remediation / None / Ready`;
* conventional Spec Review → base `Spec Review / Review Remediation / $to-tickets / Ready` while no executable remediation-ticket children exist;
* any other formal review artifact whose lifecycle state was durably changed by `$review-spec-remediation`.

Do not create a Spec Review merely for projection. The review issue must already exist because Blocking remediation state required it. Supply current Project Delivery State separately; preserve `Area` and `Priority` unless separately authorized.

`$review-spec` owns these post-review base states; `$project-tracking` owns validation, delivery overlay, and Project mutation. `PROJECT TRACKING: DRIFT` does not roll back the Root Blocker ledger or suppress an otherwise-authorized `$to-tickets` handoff.

If `$review-spec-remediation` returns a `$to-tickets` handoff, present the aggregate review first and append the handoff exactly after mandatory Project reconciliation. If no active Blocking remains after corrections, continue to Exit Gate.

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

Re-run Project Delivery Actionability Guard and persist the Exit Receipt on the **parent Spec issue**. Do not call `ensure_spec_review_issue` from the PASS path and do not create a conventional Spec Review issue merely to store successful review authorization.

The parent Spec owns workspace metadata, the Spec Verification Receipt, and the final review Exit Receipt consumed later by `$spec-merge-cleanup`. If a conventional Spec Review exists from an earlier blocker/remediation cycle, preserve it as remediation history; it does not own the Exit Receipt.

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

### Mandatory Project Reconciliation — Ready to Merge

A successfully persisted Exit Receipt is the authoritative clean-review transition. From that exact receipt and reviewed `HEAD`, establish the parent Spec's base lifecycle as:

```text
Artifact Type: Spec
Workflow State: Ready to Merge
Work Status: Ready
Next Skill: $spec-merge-cleanup
Root Blocker: None
Completed On: None
```

Invoke `$project-tracking` as prescribed internal composition for the parent Spec **after** Exit Receipt persistence and **before** the Spec Merge Cleanup Human Handoff. Supply current Project Delivery State separately; preserve `Area` and `Priority` unless separately authorized.

If a conventional Spec Review exists from earlier remediation, include it only when this invocation durably changed its own lifecycle state. Do not manufacture `Spec Review / Complete` merely because the parent Spec passed review; `$spec-merge-cleanup` owns review-issue closure/finalization.

The Project projection and `$spec-merge-cleanup` handoff must derive from the same persisted Exit Receipt. `PROJECT TRACKING: DRIFT` does not invalidate the receipt, roll back `Ready to Merge`, or suppress the otherwise-authorized handoff.

### Spec Merge Cleanup Human Handoff

After receipt persistence and mandatory Project reconciliation, halt with:

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
