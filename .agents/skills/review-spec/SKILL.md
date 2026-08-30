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

The default review requires **one genuinely fresh primary reviewer per applicable axis**. Additional genuinely fresh challengers are conditional and targeted; reviewer count is not a substitute for a complete review universe. If required fresh reviewer execution is unavailable, review fails closed unless the human owner explicitly authorizes the same-agent fallback defined in **Reviewer Execution Integrity** for the current invocation.

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

A **reviewer execution override** is distinct from an `Owner-overridden` finding/root disposition. It waives only the fresh-context execution requirement described below; it does not accept, reject, suppress, or reclassify any review finding.

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

Treat the following baseline and verification-receipt extractions as two prescribed reads over that one snapshot. Execute them separately exactly as written; do not combine their scalar/object outputs into an ad hoc `jq` array/program or reinterpret one extraction's output as the other's input.

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

`$spec-contract` exclusively owns current default-branch head resolution, local object availability/fetch, and Spec Change Ownership comparison. Consume the helper's returned `Default branch`, `Default branch ref`, and ownership classification directly. Do not independently resolve or fetch the default branch, probe its Git object, or run `git diff` / `git rev-list` against a GitHub-pinned default head before or after the helper. If fresh ownership is needed later in the invocation, re-invoke `$spec-contract` rather than reproducing its pin/fetch logic.

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

For operator-facing halt/status reporting only, also distinguish **prior durable review state** from the **current review pass**. Existing review/remediation history remains valid historical state even when the current verified `HEAD` requires a new review pass. Never describe the overall review as `not started` when durable review history exists; `not started` may describe only reviewer dispatch for the current pass.

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

### Reviewer Execution Integrity

Independent reviewer execution is part of review validity, not presentation.

A **fresh reviewer** means a genuinely separate agent/subagent context that did not participate in parent orchestration and receives only the authority, cells, and evidence slice assigned to that reviewer role. The parent must never silently simulate multiple fresh reviewer identities inside one context.

Before the first reviewer dispatch, determine whether the current execution environment can create the required genuinely fresh reviewer contexts.

When fresh contexts are available:

```text
Reviewer execution: independent-subagents
Reviewer execution override: None
```

Use genuine fresh contexts for every primary, targeted challenger, and saturation challenger required by this review.

When fresh contexts are unavailable and the current human invocation does **not** contain an explicit reviewer-execution override, halt before any axis review, Pending Review Remediation persistence, or Exit Receipt persistence:

```text
REVIEW EXECUTION: INDEPENDENCE UNAVAILABLE
Required: genuinely fresh reviewer contexts
Current review pass: reviewer dispatch not started
Prior durable review state: <None | concise recovered review/remediation history>
Verified target: HEAD <SHA>; baseline <SHA>; contract <review-cell count> cells
Persistence: no Pending Review Remediation or Exit Receipt written by this halted invocation
Owner options:
- re-run `$review-spec` in an environment that supports fresh subagents; or
- explicitly authorize same-agent reviewer fallback for this review
```

When prior durable review/remediation state exists, summarize it truthfully here (for example, prior review completed, conventional Spec Review issue, and current root statuses). Do not collapse historical review state into `Current review pass: reviewer dispatch not started` or imply that prior review/remediation never occurred.

Do not substitute the parent agent merely because reviewer spawning is unavailable.

#### Human Owner Reviewer-Execution Override

The human owner may explicitly waive the fresh-context requirement for the **current `$review-spec` invocation**. A canonical authorization is:

```text
OWNER REVIEWER EXECUTION OVERRIDE: authorize same-agent reviewer fallback for this review
```

Equivalent unambiguous current-prompt wording is acceptable, but the override must be explicit. Do not infer it from:

* the human being repository owner;
* a prior invocation or prior-session authorization;
* a finding/root Owner Override;
* issue comments or Project fields;
* inability to spawn subagents;
* a general instruction to continue or use best effort.

The override authorizes the parent agent to execute reviewer roles sequentially in the same context when genuine fresh reviewer contexts are unavailable. Unless the human explicitly narrows the authorization, it covers required primary, targeted challenger, and saturation challenger roles for that one review invocation.

Set:

```text
Reviewer execution: owner-overridden-same-agent
Reviewer execution override: explicit current-invocation owner authorization
```

This override:

* waives **only** genuine fresh-context execution;
* does not make the same-agent roles fresh or independent, and they must never be reported as such;
* does not waive review-universe completeness, per-cell disposition, axis authority, Axis-Provenance Gate, challenge/saturation triggers, Root reconciliation, or Exit Gate requirements;
* does not authorize accepting, rejecting, suppressing, or reclassifying findings merely because the same agent is performing multiple roles;
* does not override any higher-priority system, safety, security, or tool-execution constraint outside this repository workflow.

Under same-agent fallback, preserve reviewer information separation as far as the environment permits: execute one reviewer role at a time from its assigned authority/cells/evidence, do not intentionally consult Root Blocker history or prior axis findings while acting in a primary role, and do not use the primary conclusion as challenger authority. The durable receipt must disclose the reduced execution independence.

## 5. Dispatch One Primary Reviewer per Applicable Axis

Execute exactly one primary reviewer role for each applicable axis:

* Standards primary when Standards applies;
* Spec primary always;
* Architecture primary when Architecture applies.

In `independent-subagents` mode, spawn exactly one genuinely fresh primary reviewer for each applicable axis. In `owner-overridden-same-agent` mode, the parent executes each primary role sequentially under the information-separation discipline above. Do not spawn or simulate a default challenger.

Give each primary role:

* only its axis authority;
* its complete parent-built cells;
* only the evidence slices relevant to those cells;
* no Root Blocker history or prior reviewer findings.

### Reviewer Claim-Proof Integrity

Every primary, targeted challenger, and saturation challenger derives proof from its assigned authoritative claim before treating supplied evidence as a proof plan.

For each material cell, normalize the claim into its **subject, quantifier, domain, predicate, and material conditions/exceptions**, then state the concrete **falsification condition**: a current repository/runtime/tracker state that would make the claim false. Derive the inspection strategy from that claim and falsifier, and actively seek counterexamples within the permitted axis/domain.

A `checked-no-finding` disposition requires evidence that excludes the falsification condition across the required domain. Ask: **Could every inspected/cited check succeed while this cell is still false?** If yes, the cell is not clean and must trigger blocking/advisory/unresolved handling under its axis contract. Any material assumption connecting evidence to conclusion must itself be established by the axis authority or direct evidence.

Known defect patterns, prior implementation choices, changed-file lists, existing tests, and the passing verification receipt are supporting evidence only. They must not define the claim, falsifier, or proof boundary. This reasoning discipline does not require a verbose transcript in the durable review packet.

### Primary Strategy

Use a combined coverage strategy:

1. **claim-first:** apply **Reviewer Claim-Proof Integrity** before accepting supplied evidence as proof;
2. **authority-first:** trace every supplied cell into all relevant surfaces;
3. **adversarial-surface:** inspect applicable defaults/fallbacks/alternate entries/bypasses/fail-open paths as possible counterexample witnesses before disposition.

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

A targeted challenger is allowed only when a concrete trigger exists. In `independent-subagents` mode it must be genuinely fresh; in `owner-overridden-same-agent` mode the parent may execute the challenger role under the explicit current-invocation override and must not report it as fresh or independent.

Challenge triggers:

1. **coverage trigger** — a primary cannot disposition a supplied cell or an applicable Standards/Architecture authority reveals a materially omitted cell;
2. **authority trigger** — source conflict, ambiguous authority, or parent cannot validate the cited native-axis authority;
3. **evidence trigger** — evidence is materially contradictory or insufficient to accept/reject a blocker;
4. **convergence trigger** — after root reconciliation, a newly accepted finding is a Missed prior finding against a previously satisfied root or exposes a root-definition gap.

For triggers 1–3, dispatch or execute one targeted challenger over only the affected cells/question. Do not intentionally provide it the primary's conclusion. Its job is resolution of the trigger, not a second full-axis review. The challenger applies **Reviewer Claim-Proof Integrity** independently to its assigned cells/question.

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
2. execute exactly one **saturation challenger** under the originating axis authority using the current Reviewer Execution mode;
3. instruct it to inspect every domain item, apply **Reviewer Claim-Proof Integrity**, and add/check any newly discovered sibling surface before returning;
4. require its final domain coverage to reach `unchecked 0`;
5. validate any additional findings through the normal Axis-Provenance Gate;
6. add supported findings to the current frozen set/root mapping before remediation persistence.

In `independent-subagents` mode the saturation challenger must be genuinely fresh. In `owner-overridden-same-agent` mode the parent may execute the role under the explicit current-invocation override and must disclose that reduced independence in durable review provenance.

Do not spawn or simulate another generic whole-axis reviewer.

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
Reviewer execution: <independent-subagents | owner-overridden-same-agent>
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
**Reviewer execution:** <independent-subagents | owner-overridden-same-agent>
**Reviewer execution override:** <None | explicit current-invocation owner authorization>

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

Pre-validate the rendered file before POST. Require the exact pending header/status, reviewed HEAD/baseline/branch, Spec body/contract hashes, reviewer execution mode/override provenance, all packet sections exactly once, and no unresolved template placeholders. Immediately before POST require `HEAD` still equals the passing verification receipt.

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
* reviewer execution integrity is satisfied by genuine fresh reviewer contexts or an explicit current-invocation human owner reviewer-execution override;
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
**Reviewer execution:** <independent-subagents | owner-overridden-same-agent>
**Reviewer execution override:** <None | explicit current-invocation owner authorization>
```

`Primary reviewers`, `Targeted challengers`, and `Saturation challengers` count logical reviewer roles. When `Reviewer execution = owner-overridden-same-agent`, those counts must not be interpreted or described as fresh-subagent counts.

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

## Transition-Bound Review Proof State

Reviewer Claim-Proof Integrity is an enforceable state transition. A reviewer may not return `checked-no-finding` merely after acknowledging falsification-first reasoning.

For every primary, targeted-challenger, and saturation-challenger cell actually dispositioned, maintain a working record:

```text
Cell: <STD-* | Spec manifest ID | ARCH-*>
Claim: <assigned authoritative claim>
Predicate: <subject + quantifier + domain + required predicate + material conditions/exceptions>
Falsifier: <concrete current state that would make the claim false>
Evidence: <direct inspected evidence>
Survivability: <excluded | survives>
Assumptions: <None | material assumption + authority/direct proof>
Disposition: <checked-no-finding | Blocking | Advisory | not-applicable | unresolved>
```

`checked-no-finding` requires concrete Predicate/Falsifier/Evidence, `Survivability: excluded`, and no unproven material assumption. If every cited inspection could succeed while the claim remains false, the reviewer must not return `checked-no-finding`; use the axis-appropriate finding or `unresolved` result. `not-applicable` must cite the exact condition/authority that removes the cell from applicability.

The parent must require, across the complete review universes before the Exit Gate:

```text
Review universe cells: <n>
Disposition rows: <n>
Missing cells: 0
Unknown cells: 0
Unchecked/unresolved cells: 0
Incomplete checked-no-finding proof records: 0
Survivability not excluded for checked-no-finding cells: 0
Unproven material assumptions: 0
```

Fresh reviewer independence remains mandatory exactly as defined above. These records strengthen each reviewer role; they do not permit the parent to substitute its own reasoning for a required fresh reviewer or to expose historical Root Blocker state to primaries.

The durable Exit Receipt may remain concise. The working proof state must nevertheless exist before the parent may persist a passing Exit Receipt or invoke `$spec-merge-cleanup`.
