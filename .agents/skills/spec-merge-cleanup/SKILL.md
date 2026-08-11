---
name: spec-merge-cleanup
description: Invoked only by `$review-spec` when its Exit Gate authorizes progression. Merges the spec branch into `main` or directly closes branchless Specs, cleans up the branch and Spec Review, and reconciles completion with the originating Wayfinder map.
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

## Wayfinder Completion Reconciliation

After the current Spec is successfully closed, recover its originating Wayfinder map from the Spec provenance marker when present:

```html
<!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision> -->
```

Determine every Spec derived from that map using explicit Wayfinder/Spec handoff metadata or the same provenance marker.

If any derived Spec remains open, make no Wayfinder lifecycle change.

If all derived Specs are closed:

* post one concise completion comment on the Wayfinder map identifying the completed derived Specs;
* if the map is still open, close it;
* if it is already closed, leave it closed.

Do not reopen a closed Wayfinder map merely to close it again.

Example completion comment:

```text
All implementation Specs derived from this Wayfinder effort are complete and closed: #<spec>, #<spec>.
```

Failure to determine Wayfinder provenance is not a merge failure; report it and skip Wayfinder reconciliation rather than guessing.

## Step 0 — Route: Standard vs. Direct Close

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

  # Perform Wayfinder Completion Reconciliation here.

  exit 0
fi
```

If the branch exists, continue with the standard merge path.

## Phase A — Merge to Main

1. **Confirm Precondition**

   Do not proceed unless `$review-spec`'s Exit Gate authorized cleanup.

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

   If another derived Spec remains open, leave the Wayfinder map unchanged.

   If this was the final derived Spec, comment on the map and close it only if it is still open.

## Completion

Cleanup is complete only when the applicable path has:

* successfully closed the Spec;
* closed its Spec Review issue when one exists;
* merged and deleted the Spec branch when applicable;
* reconciled the originating Wayfinder map when provenance is available.

Wayfinder reconciliation must never guess missing lineage or block an otherwise successful Spec merge solely because provenance cannot be recovered.
