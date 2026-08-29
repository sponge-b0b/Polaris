---
name: spec-merge-cleanup
description: Invoked only by `$review-spec` when its Exit Gate authorizes progression. Merges the spec branch into `main` or directly closes branchless Specs, resumes interrupted post-completion cleanup safely, cleans up the branch and any remediation Spec Review, and reconciles completion with every governing Wayfinder map.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Spec Merge & Cleanup

Invoked by `$review-spec` only after its Exit Gate passes: zero Blocking findings, every Root Blocker satisfied, Owner-overridden, or Scope-retired, and no unresolved Candidate new root.

Execution splits depending on whether the Spec used `spec-<spec_issue_number>` and whether authoritative Spec completion has already occurred.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting. Prior-session summaries or remembered conclusions are routing context only and must not substitute for required durable evidence.

If required durable state cannot be recovered, report the missing artifact rather than infer or recreate it from memory.

Never assume an invocation is pre-merge merely because cleanup work remains. Detect whether the authoritative Spec completion transition has already occurred before applying any open-Spec or project-focus precondition.

## Review Exit Authorization

Before closing or merging anything, and before resuming interrupted post-completion cleanup, recover the latest **Spec Review Exit Receipt** from the parent Spec issue. The parent Spec owns workspace metadata, Spec Verification Receipts, and the final review Exit Receipt. A conventional Spec Review issue is optional remediation history and must not be required for a clean first-pass review.

Read the parent Spec's complete durable comment history once:

```bash
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
SPEC_NUMBER=<parent Spec issue number>

SPEC_COMMENT_PAGES=$(
  gh api --paginate --slurp \
    -H "X-GitHub-Api-Version: 2026-03-10" \
    "repos/$REPO/issues/$SPEC_NUMBER/comments?per_page=100"
)

REVIEW_EXIT_RECEIPT_JSON=$(
  printf '%s\n' "$SPEC_COMMENT_PAGES" \
    | jq -c '
        [.[][]
         | select((.body // "") | contains("## Spec Review Exit Receipt"))
         | {id, created_at, html_url, body}]
        | sort_by(.created_at, .id)
        | last // empty'
)
```

That newest parent-Spec receipt is the only review-authorization candidate. Do not use a receipt copied onto a Spec Review issue, an unpaginated comment read, or walk backward to an older receipt when the newest one is malformed or stale.

Resolve an optional conventional Spec Review issue separately for remediation cleanup:

```bash
PARENT_MARKER="**Parent Spec:** #$SPEC_NUMBER"

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
elif [ "$REVIEW_COUNT" -eq 1 ]; then
  SPEC_REVIEW_ISSUE_NUMBER=$(printf '%s\n' "$REVIEW_MATCHES" | jq -r '.[0].number')
else
  SPEC_REVIEW_ISSUE_NUMBER=""
fi
```

Zero conventional Spec Review matches is valid: it means the review passed without entering blocker/remediation state. More than one remains ambiguous durable remediation ownership and fails closed.

The parent-Spec receipt must have been persisted by `$review-spec` only after its Exit Gate passed and must match the current producer schema:

```markdown
## Spec Review Exit Receipt

**Status:** passed
**Reviewed HEAD:** <full SHA>
**Reviewed Baseline:** <full Spec baseline SHA>
**Branch:** spec-<spec_issue_number>
**Spec Body Hash:** <hash>
**Spec Contract Hash:** <hash>
**Blocking findings:** 0
**Root blockers:** satisfied/owner-overridden/scope-retired
**Candidate new roots:** 0
**Review coverage:** complete
**Unchecked coverage cells:** 0
```

Recover the current Spec baseline from its durable workspace metadata and the latest passing Spec Verification Receipt from `SPEC_COMMENT_PAGES` for the same candidate HEAD.

Require:

* `Status` is `passed`;
* `Reviewed Baseline` equals the current Spec baseline;
* `Spec Body Hash` and `Spec Contract Hash` equal the parent Spec's latest passing Spec Verification Receipt for the same `Reviewed HEAD`;
* `Blocking findings` is `0`;
* `Root blockers` is exactly `satisfied/owner-overridden/scope-retired`;
* `Candidate new roots` is `0`;
* `Review coverage` is `complete` and `Unchecked coverage cells` is `0`;
* before merge, when the Spec branch exists, `Branch` matches it and `Reviewed HEAD` exactly equals that branch's current `HEAD`;
* during post-merge recovery, `Reviewed HEAD` exactly equals the matching merged PR's recorded head SHA.

Any commit after the receipt and before merge makes the authorization stale.

A later commit on a still-existing Spec branch **after** the reviewed HEAD was merged does not retroactively invalidate the completed merge, but it makes that branch unsafe to delete automatically. Post-merge cleanup must fail closed on branch-tip drift rather than deleting unmerged work.

If the parent-Spec receipt is missing, malformed, or cannot be bound either to the current pre-merge branch or to the exact merged PR used for recovery, halt:

> ⚠️ **Spec cleanup requires durable review authorization.**
>
> Please run:
>
> ```
> $review-spec - <Spec Title> (<Spec URL>)
> ```

Do not invoke `$review-spec` implicitly and do not copy/recreate the receipt on a Spec Review issue merely to satisfy cleanup.

### Canonical Lifecycle Reads

Use canonical GitHub REST state for phase detection. Do not probe `gh issue view --json closingIssuesReferences` or other optional/unsupported CLI JSON fields, and do not retry the same fact through alternate interfaces after a prescribed read succeeds.

Read Spec state directly:

```bash
SPEC_STATE=$(gh api \
  -H "X-GitHub-Api-Version: 2026-03-10" \
  "repos/$REPO/issues/$SPEC_NUMBER" \
  --jq '.state')
```

For branch-backed Specs, recover PR candidates from the REST pull-request collection and match by base branch plus exact reviewed head SHA:

```bash
OWNER=${REPO%%/*}
SPEC_BRANCH="spec-$SPEC_NUMBER"

PR_PAGES=$(
  gh api --paginate --slurp \
    -H "X-GitHub-Api-Version: 2026-03-10" \
    "repos/$REPO/pulls?state=all&base=main&per_page=100"
)

MATCHING_MERGED_PRS=$(
  printf '%s\n' "$PR_PAGES" \
    | jq -c --arg owner "$OWNER" --arg branch "$SPEC_BRANCH" --arg head "$REVIEWED_HEAD" '
        [.[][]
         | select(.head.user.login == $owner)
         | select(.head.ref == $branch)
         | select(.head.sha == $head)
         | select(.base.ref == "main")
         | select(.merged_at != null)
         | {number, merge_commit_sha, head_sha: .head.sha, url: .html_url}]'
)
```

Use these prescribed reads for lifecycle routing. A read failure makes the corresponding phase fact unreadable; do not guess it from issue-closing references, Project projection, or prior session state.

## Lifecycle Phase Detection

Determine the lifecycle phase from durable state before invoking the project-delivery actionability guard.

### Pre-completion

The Spec is open and has not yet completed through this skill's authoritative merge/direct-close boundary.

Use the normal actionability guard and then select the standard merge or direct-close path.

### Post-merge recovery

A closed Spec may resume the standard branch cleanup path without being reopened and without re-running the pre-merge project-focus guard only when all of the following are proven:

1. the latest **Spec Review Exit Receipt** passes **Review Exit Authorization**;
2. exactly one merged PR for `spec-<spec_issue_number>` into `main` matches the receipt's `Reviewed HEAD` as its recorded head SHA;
3. the PR is durably `MERGED` and its merge commit is reachable from current `main`;
4. `Reviewed HEAD` is an ancestor of current `main`;
5. the Spec is closed;
6. if the local or remote Spec branch still exists, each existing branch tip still equals `Reviewed HEAD`.

If an existing local or remote branch tip differs from `Reviewed HEAD`, stop before deletion and report branch drift. Never force-delete or silently discard commits added after the reviewed merge.

When these conditions hold, set `PR_NUMBER` from the matching merged PR and resume directly at **Phase B — Cleanup and Finalize**. Do not create another PR, merge again, reopen/reclose the Spec, or require the governing Wayfinder to remain focused. Successful completion may already have released project focus or closed a governing Wayfinder.

### Post-direct-close recovery

A closed branchless Spec may resume finalization without being reopened and without re-running the pre-close project-focus guard only when all of the following are proven:

1. the latest **Spec Review Exit Receipt** passes **Review Exit Authorization**;
2. no local or remote `spec-<spec_issue_number>` branch exists;
3. no merged PR exists for that Spec branch and reviewed HEAD;
4. the Spec contains the durable direct-close completion comment emitted by this skill:

   `Spec work completed and reviewed directly (no dedicated branch was used). Zero blocking findings on final review.`

When these conditions hold, resume with Spec Review cleanup and **Wayfinder Completion Reconciliation**. Do not close the Spec again.

If the Spec is closed but neither recovery mode can be proven exactly, fail closed. Never infer that an arbitrary closed Spec was completed by this workflow.

## Project Delivery Actionability Guard

Apply this guard only in the **Pre-completion** phase, before merge, direct close, or another pre-completion lifecycle mutation. Do not re-run it during proven post-merge or post-direct-close recovery; completion may already have legitimately released focus.

Determine whether the Spec is Wayfinder-managed from durable `wayfinder-source`, `wayfinder-remediation`, and reconciled `Spec Handoff` evidence.

An intentionally non-Wayfinder Spec keeps the existing cleanup lifecycle. Do not invent a Wayfinder merely to enroll it into project focus.

For a Wayfinder-managed Spec:

1. require the Spec to be open;
2. read its complete native `blocked by` relationship set and fail closed if blocker data is truncated or unreadable;
3. stop if any direct blocker is open;
4. recover every current governing Wayfinder; ambiguous governance fails closed rather than choosing one;
5. invoke `$project-delivery-management` `reconcile`;
6. invoke `$project-delivery-management` `guard <Wayfinder>` for every governor;
7. require at least one governor to return `PROJECT DELIVERY GUARD: ALLOWED`.

If none is allowed, stop before merge/close and report the governing maps, their guard results, current focus, and the explicit human `$project-delivery-management` focus/switch/parallel choices. This skill never establishes, switches, or broadens focus.

A legitimately reopened blocker Spec makes this guard fail again through the unchanged native dependency edge. Do not persist a parallel "unblocked" state.

This explicit `$spec-merge-cleanup` invocation is a distinct human lifecycle entry and must revalidate authorization before a new authoritative completion transition. A proven post-completion recovery is continuation of an already-durable completion transition, not authorization for another one.

## Wayfinder Completion Reconciliation

Authoritative Spec closure is the Spec dependency-completion boundary. Once the current Spec is confirmed closed, existing native dependents observe that closure directly; do not write a second satisfaction marker.

Then recover **every current governing Wayfinder** for the completed Spec from:

* its canonical `wayfinder-source` marker;
* every `wayfinder-remediation` marker; and
* matching `Derived Spec` / `Remediation Spec` handoffs on canonical Wayfinder maps.

Preserve the original `wayfinder-source`; remediation governance is additive and never rewrites source provenance.

For each recovered governing Wayfinder:

1. recover its complete currently governed Spec set from both forward `Spec Handoff` metadata and reverse source/remediation provenance;
2. require every recovered relationship to be unambiguous; do not guess or silently convert Derived/Remediation roles;
3. determine whether any governed Spec remains open;
4. determine whether the map still has any open Wayfinder decision ticket or unresolved in-scope `Not yet specified` fog;
5. close the map only when **all** currently governed Derived and Remediation Specs are closed **and** no unresolved decision/fog remains.

If a governed Spec remains open or decision/fog remains, leave an open Wayfinder open. Do not create a synthetic map blocker merely to represent the lower-level work.

If a Wayfinder is already closed while the completion invariant is false, report the inconsistent lifecycle state and do not pretend it is complete or silently reopen it here. Explicit re-entry belongs to the owning re-entry workflow; historical inconsistent state is handled by migration/reconciliation.

When a Wayfinder becomes complete:

* post one concise completion comment identifying all currently governed Specs considered, unless an equivalent completion comment for the same governed set is already present;
* if the map is still open, close it;
* if it is already closed and the completion invariant is true, leave it closed.

Example completion comment:

```text
All Specs currently governed by this Wayfinder are complete and closed, with no unresolved decision/fog remaining: #<spec>, #<spec>.
```

After all Spec/Wayfinder authoritative transitions are durable, invoke `$project-delivery-management` `reconcile`. A closed or directly map-ineligible focused Wayfinder must be removed from focus; a still-map-eligible Wayfinder with only narrower blocked work remains focused. Reconciliation never auto-selects a replacement and must be safe to rerun after an interrupted cleanup.

Failure to determine a governing relationship is not permission to guess and is not a reason to roll back an otherwise successful merge. Report the reconciliation failure, leave ambiguous Wayfinder state untouched, and do not claim Wayfinder completion for that relationship.

## Mandatory Project Reconciliation

After authoritative Spec completion, optional Spec Review cleanup, dependent-Spec actionability recovery, Wayfinder Completion Reconciliation, and required `$project-delivery-management` reconciliation are durable, invoke `$project-tracking` as prescribed internal composition **before** successful return.

First re-read the completed Spec's direct native dependents because Spec closure may change their actionability without removing the dependency relationship. For each open direct dependent, read its complete native `blocked by` set. Do not delete the historical dependency edge.

When an open dependent is durably a Spec whose current `Blocked` lifecycle is dependency-derived:

* one or more open native Spec blockers → keep base `Spec / Blocked / None / Blocked`;
* zero open native Spec blockers → advance to base `Spec / Ready to Ticket / $to-tickets / Ready`.

Do not overwrite a dependent that has another durable lifecycle owner/state; ambiguous restoration fails closed and is reported rather than guessed.

Build one completion reconciliation set containing every affected formal artifact:

* completed parent Spec → base `Spec / Complete / None / Done` with `Completed On` set to the authoritative Spec completion date;
* conventional Spec Review when this skill closes it → base `Spec Review / Complete / None / Done` with authoritative `Completed On`;
* each governing Wayfinder map closed by this skill → base `Wayfinder Map / Complete / None / Done` with authoritative `Completed On`;
* each direct dependent Spec whose dependency-derived base projection changed after this Spec closed;
* any other formal artifact whose lifecycle or open-blocker projection this cleanup durably changed.

A governing Wayfinder that remains open and whose base lifecycle projection did not change need not be rewritten merely because one governed Spec completed. If its lifecycle projection did change, derive that state from its durable Wayfinder lifecycle rather than from Project fields.

For `Complete` artifacts, Project delivery is `Released`; for non-complete affected artifacts, supply current authoritative Project Delivery State separately. Preserve `Area` and `Priority` unless separately authorized.

`$spec-merge-cleanup` owns the completion/dependent/Wayfinder state supplied to `$project-tracking`; `$project-tracking` owns validation, delivery overlay, and Project mutation. Project state never determines whether the merge, close, cleanup, dependency satisfaction, or Wayfinder completion succeeded.

If Project synchronization fails, report `PROJECT TRACKING: DRIFT`. Do not reopen the Spec or Spec Review, restore deleted branches, reopen completed Wayfinders, or otherwise roll back authoritative completion.

## Step 0 — Route: Pre-completion vs. Recovery

Require a current passing **Spec Review Exit Receipt**, then run **Lifecycle Phase Detection**.

If **Post-merge recovery** is proven, skip the pre-completion actionability guard and continue directly to **Phase B — Cleanup and Finalize** with the recovered `PR_NUMBER`.

If **Post-direct-close recovery** is proven, skip the pre-completion actionability guard, finish any still-open Spec Review, perform **Wayfinder Completion Reconciliation**, invoke project-delivery reconciliation, perform **Mandatory Project Reconciliation**, and exit successfully when the completion criteria are satisfied.

If the Spec is open, apply the **Project Delivery Actionability Guard** before selecting either pre-completion path.

If `spec-<spec_issue_number>` does not exist locally or remotely, no PR will auto-close the Spec:

```bash
if ! git show-ref --verify --quiet "refs/heads/spec-<spec_issue_number>" && \
   ! git ls-remote --exit-code --heads origin "spec-<spec_issue_number>" >/dev/null 2>&1; then

  gh issue close <spec_issue_number> \
    --comment "Spec work completed and reviewed directly (no dedicated branch was used). Zero blocking findings on final review."

  if [ -n "$SPEC_REVIEW_ISSUE_NUMBER" ]; then
    REVIEW_STATE=$(gh issue view "$SPEC_REVIEW_ISSUE_NUMBER" --json state -q .state)
    if [ "$REVIEW_STATE" = "OPEN" ]; then
      gh issue close "$SPEC_REVIEW_ISSUE_NUMBER" \
        --comment "Spec #<spec_issue_number> closed directly. Zero blocking findings on final review."
    fi
  else
    echo "No Spec Review issue exists — nothing to close."
  fi

  # Perform Wayfinder Completion Reconciliation, project-delivery reconciliation,
  # and Mandatory Project Reconciliation before successful return.

  exit 0
fi
```

If the branch exists, continue with the standard merge path.

## Phase A — Merge to Main

1. **Confirm Precondition**

   Do not proceed unless the Spec is in **Pre-completion**, the current **Spec Review Exit Receipt** passes **Review Exit Authorization**, and the **Project Delivery Actionability Guard** remains satisfied.

2. **Push Final State**

   ```bash
   git checkout spec-<spec_issue_number>
   git push origin spec-<spec_issue_number>
   ```

3. **Create the PR Idempotently**

   ```bash
   EXISTING_PR=$(gh pr list \
     --head spec-<spec_issue_number> \
     --base main \
     --state open \
     --json number \
     -q '.[0].number')

   if [ -z "$EXISTING_PR" ]; then
     SPEC_TITLE=$(gh issue view <spec_issue_number> --json title -q .title)
     PR_TITLE_BODY=${SPEC_TITLE#Spec: }

     gh pr create \
       --base main \
       --head spec-<spec_issue_number> \
       --title "Spec #<spec_issue_number>: ${PR_TITLE_BODY}" \
       --body "Closes #<spec_issue_number>"
   fi
   ```

   Strip at most one leading `Spec: ` from the issue title when composing the PR title. If the issue title does not use that conventional prefix, preserve it unchanged.

   `Closes #<spec_issue_number>` closes the Spec when the PR merges.

4. **Merge**

   Use a regular merge commit, not squash, so ancestry remains available for safe local branch deletion.

   ```bash
   PR_NUMBER=$(gh pr list \
     --head spec-<spec_issue_number> \
     --base main \
     --state open \
     --json number \
     -q '.[0].number')

   gh pr merge "$PR_NUMBER" --merge
   ```

   Do not use `--delete-branch`; cleanup happens below.

5. **Verify Merge**

   ```bash
   MERGED_STATE=$(gh pr view "$PR_NUMBER" --json state -q .state)

   if [ "$MERGED_STATE" != "MERGED" ]; then
     echo "❌ PR #$PR_NUMBER did not merge (state: $MERGED_STATE)."
     exit 1
   fi
   ```

Do not continue to cleanup unless the merge succeeded. If cleanup later fails, the next invocation must enter **Post-merge recovery** rather than attempting Phase A again.

## Phase B — Cleanup and Finalize

This phase must be idempotent. It may run immediately after Phase A or from proven **Post-merge recovery**.

1. **Check Current Branch**

   ```bash
   CURRENT_BRANCH=$(git branch --show-current)

   if [ "$CURRENT_BRANCH" != "spec-<spec_issue_number>" ]; then
     echo "⚠️ Expected spec-<spec_issue_number>; current branch is $CURRENT_BRANCH. Continuing cleanup."
   fi
   ```

2. **Sync Main**

   ```bash
   git checkout main
   git pull --ff-only origin main
   ```

   Reconfirm that the matching merge commit is reachable from `main` and that `Reviewed HEAD` is an ancestor of `main` before deleting either branch ref.

3. **Delete Local Branch Safely and Idempotently**

   If the local Spec branch is already absent, treat local cleanup as satisfied.

   If it exists, require its current tip to equal `Reviewed HEAD`, then use normal merged-branch deletion only:

   ```bash
   if git show-ref --verify --quiet "refs/heads/spec-<spec_issue_number>"; then
     LOCAL_SPEC_HEAD=$(git rev-parse spec-<spec_issue_number>)

     if [ "$LOCAL_SPEC_HEAD" != "$REVIEWED_HEAD" ]; then
       echo "❌ Local spec branch moved after the reviewed merge; refusing to delete it."
       exit 1
     fi

     git branch -d spec-<spec_issue_number>
   else
     echo "Local spec branch already absent — cleanup satisfied."
   fi
   ```

   If `git branch -d` fails, stop and investigate. Do not force-delete with `-D`.

4. **Delete Remote Branch Safely and Idempotently**

   If the remote Spec branch is already absent, treat remote cleanup as satisfied.

   If it exists, require its current tip to equal `Reviewed HEAD` before deletion:

   ```bash
   REMOTE_SPEC_HEAD=$(git ls-remote --heads origin "refs/heads/spec-<spec_issue_number>" | awk '{print $1}')

   if [ -n "$REMOTE_SPEC_HEAD" ]; then
     if [ "$REMOTE_SPEC_HEAD" != "$REVIEWED_HEAD" ]; then
       echo "❌ Remote spec branch moved after the reviewed merge; refusing to delete it."
       exit 1
     fi

     git push origin --delete spec-<spec_issue_number>
   else
     echo "Remote spec branch already absent — cleanup satisfied."
   fi
   ```

5. **Close Spec Review Idempotently**

   The Spec itself was closed by the merged PR. Never reopen or reclose it during post-merge recovery.

   ```bash
   if [ -n "$SPEC_REVIEW_ISSUE_NUMBER" ]; then
     REVIEW_STATE=$(gh issue view "$SPEC_REVIEW_ISSUE_NUMBER" --json state -q .state)

     if [ "$REVIEW_STATE" = "OPEN" ]; then
       gh issue close "$SPEC_REVIEW_ISSUE_NUMBER" \
         --comment "Spec merged (PR #$PR_NUMBER) and branch cleaned up. Zero blocking findings on final review."
     else
       echo "Spec Review already closed — cleanup satisfied."
     fi
   else
     echo "No Spec Review issue exists — nothing to close."
   fi
   ```

6. **Reconcile Wayfinder Completion**

   Perform **Wayfinder Completion Reconciliation** only after the Spec is confirmed closed and required branch cleanup above is satisfied.

   Reconcile every governing Wayfinder against all of its currently governed Derived and Remediation Specs plus unresolved decision/fog state. Then invoke `$project-delivery-management` `reconcile` after any map closure is durable.

   Recovery must tolerate already-correct completion state: an already-closed Wayfinder whose invariant still holds and an already-released project focus are successful no-op reconciliation results, not errors.

7. **Reconcile Project Projection**

   Perform **Mandatory Project Reconciliation** from the final durable completion/dependency/Wayfinder state before returning success.

## Completion

Cleanup is complete only when the applicable path has:

* validated a current passing Spec Review Exit Receipt from the parent Spec and bound it to the current Spec verification/branch state;
* either passed the current project-delivery actionability guard before a new authoritative completion transition **or** proven an exact post-completion recovery path from durable evidence;
* successfully closed the Spec exactly once through the applicable authoritative path;
* closed its Spec Review issue when one exists, or confirmed it was already closed;
* for a branch-backed Spec, confirmed the exact reviewed HEAD was merged to `main` and removed any still-existing local/remote Spec branch without deleting drifted post-merge work;
* reconciled every unambiguously recovered governing Wayfinder against its full Derived+Remediation governed Spec set and decision/fog state;
* invoked project-delivery reconciliation after authoritative completion transitions, with already-correct reconciled state accepted as a no-op;
* invoked `$project-tracking` for the completed Spec and every other formal artifact whose lifecycle/open-blocker projection changed, with Project drift reported but never treated as workflow authority.

A failed cleanup step after successful Spec completion does not invalidate the completed merge/direct close. A later invocation must recover from durable completion evidence and resume the remaining idempotent cleanup instead of requiring the Spec to be open, re-establishing focus, or repeating the completion transition.

Wayfinder reconciliation must never guess missing lineage or roll back an otherwise successful Spec merge solely because provenance cannot be recovered. Report ambiguity/inconsistency explicitly and leave the affected map untouched rather than manufacturing lifecycle truth.
