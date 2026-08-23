---
name: spec-merge-cleanup
description: Invoked only by `$review-spec` when its Exit Gate authorizes progression. Merges the spec branch into `main` or directly closes branchless Specs, cleans up the branch and Spec Review, and reconciles completion with every governing Wayfinder map.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Spec Merge & Cleanup

Invoked by `$review-spec` only after its Exit Gate passes: zero Blocking findings, every Root Blocker satisfied or Owner-overridden, and no unresolved Candidate new root.

Execution splits depending on whether the Spec used `spec-<spec_issue_number>`.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting. Prior-session summaries or remembered conclusions are routing context only and must not substitute for required durable evidence.

If required durable state cannot be recovered, report the missing artifact rather than infer or recreate it from memory.

## Review Exit Authorization

Before closing or merging anything, recover the latest **Spec Review Exit Receipt** from the parent Spec issue.

The receipt must have been persisted by `$review-spec` only after its Exit Gate passed:

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

Recover the current Spec baseline from its durable workspace metadata.

Require:

* `Status` is `passed`;
* `Reviewed Baseline` equals the current Spec baseline;
* `Blocking findings` is `0`;
* `Root blockers` is `satisfied-or-owner-overridden`;
* `Candidate new roots` is `0`;
* when the Spec branch exists, `Branch` matches it and `Reviewed HEAD` exactly equals that branch's current `HEAD`.

Any commit after the receipt makes the authorization stale.

If the receipt is missing, malformed, or stale, halt:

> ⚠️ **Spec cleanup requires durable review authorization.**
>
> Please run:
>
> ```
> $review-spec - <Spec Title> (<Spec URL>)
> ```

Do not invoke `$review-spec` implicitly.

## Project Delivery Actionability Guard

Before merge, direct close, or any other lifecycle mutation, determine whether the Spec is Wayfinder-managed from durable `wayfinder-source`, `wayfinder-remediation`, and reconciled `Spec Handoff` evidence.

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

This explicit `$spec-merge-cleanup` invocation is a distinct human lifecycle entry and must revalidate authorization even though `$review-spec` was previously authorized.

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

* post one concise completion comment identifying all currently governed Specs considered;
* if the map is still open, close it;
* if it is already closed and the completion invariant is true, leave it closed.

Example completion comment:

```text
All Specs currently governed by this Wayfinder are complete and closed, with no unresolved decision/fog remaining: #<spec>, #<spec>.
```

After all Spec/Wayfinder authoritative transitions are durable, invoke `$project-delivery-management` `reconcile`. A closed or directly map-ineligible focused Wayfinder must be removed from focus; a still-map-eligible Wayfinder with only narrower blocked work remains focused. Reconciliation never auto-selects a replacement.

Failure to determine a governing relationship is not permission to guess and is not a reason to roll back an otherwise successful merge. Report the reconciliation failure, leave ambiguous Wayfinder state untouched, and do not claim Wayfinder completion for that relationship.

## Step 0 — Route: Standard vs. Direct Close

Require a current passing **Spec Review Exit Receipt** and pass the **Project Delivery Actionability Guard** before selecting either path.

If `spec-<spec_issue_number>` does not exist locally or remotely, no PR will auto-close the Spec:

```bash
if ! git show-ref --verify --quiet "refs/heads/spec-<spec_issue_number>" && \
   ! git ls-remote --exit-code --heads origin "spec-<spec_issue_number>" >/dev/null 2>&1; then

  gh issue close <spec_issue_number> \
    --comment "Spec work completed and reviewed directly (no dedicated branch was used). Zero blocking findings on final review."

  if [ -n "$SPEC_REVIEW_ISSUE_NUMBER" ]; then
    gh issue close "$SPEC_REVIEW_ISSUE_NUMBER" \
      --comment "Spec #<spec_issue_number> closed directly. Zero blocking findings on final review."
  else
    echo "No Spec Review issue exists — nothing to close."
  fi

  # Perform Wayfinder Completion Reconciliation here, then project-delivery reconciliation.

  exit 0
fi
```

If the branch exists, continue with the standard merge path.

## Phase A — Merge to Main

1. **Confirm Precondition**

   Do not proceed unless the current **Spec Review Exit Receipt** passes **Review Exit Authorization** and the **Project Delivery Actionability Guard** remains satisfied.

2. **Push Final State**

   ```bash
   git checkout spec-<spec_issue_number>
   git push origin spec-<spec_issue_number>
   ```

3. **Create the PR Idempotently**

   ```bash
   EXISTING_PR=$(gh pr list \
     --head spec-<spec_issue_number> \
     --state open \
     --json number \
     -q '.[0].number')

   if [ -z "$EXISTING_PR" ]; then
     SPEC_TITLE=$(gh issue view <spec_issue_number> --json title -q .title)

     gh pr create \
       --base main \
       --head spec-<spec_issue_number> \
       --title "Spec #<spec_issue_number>: ${SPEC_TITLE}" \
       --body "Closes #<spec_issue_number>"
   fi
   ```

   `Closes #<spec_issue_number>` closes the Spec when the PR merges.

4. **Merge**

   Use a regular merge commit, not squash, so ancestry remains available for safe local branch deletion.

   ```bash
   PR_NUMBER=$(gh pr list \
     --head spec-<spec_issue_number> \
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

Do not continue to cleanup unless the merge succeeded.

## Phase B — Cleanup and Finalize

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
   git pull origin main
   ```

3. **Delete Local Branch**

   ```bash
   git branch -d spec-<spec_issue_number>
   ```

   If this fails, stop and investigate. Do not force-delete with `-D`.

4. **Delete Remote Branch**

   ```bash
   git push origin --delete spec-<spec_issue_number>
   ```

5. **Close Spec Review**

   The Spec itself was closed by the merged PR.

   ```bash
   if [ -n "$SPEC_REVIEW_ISSUE_NUMBER" ]; then
     gh issue close "$SPEC_REVIEW_ISSUE_NUMBER" \
       --comment "Spec merged (PR #$PR_NUMBER) and branch cleaned up. Zero blocking findings on final review."
   else
     echo "No Spec Review issue exists — nothing to close."
   fi
   ```

6. **Reconcile Wayfinder Completion**

   Perform **Wayfinder Completion Reconciliation** only after the Spec is confirmed closed and all required cleanup above succeeded.

   Reconcile every governing Wayfinder against all of its currently governed Derived and Remediation Specs plus unresolved decision/fog state. Then invoke `$project-delivery-management` `reconcile` after any map closure is durable.

## Completion

Cleanup is complete only when the applicable path has:

* validated a current passing Spec Review Exit Receipt from the parent Spec;
* passed the current project-delivery actionability guard when the Spec is Wayfinder-managed;
* successfully closed the Spec;
* closed its Spec Review issue when one exists;
* merged and deleted the Spec branch when applicable;
* reconciled every unambiguously recovered governing Wayfinder against its full Derived+Remediation governed Spec set and decision/fog state;
* invoked project-delivery reconciliation after authoritative completion transitions.

Wayfinder reconciliation must never guess missing lineage or roll back an otherwise successful Spec merge solely because provenance cannot be recovered. Report ambiguity/inconsistency explicitly and leave the affected map untouched rather than manufacturing lifecycle truth.
