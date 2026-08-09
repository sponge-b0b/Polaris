---
name: spec-merge-cleanup
description: Invoked only by `$review-spec` when its Exit Gate authorizes progression (zero Blocking findings) — not a standalone command. Merges the spec branch into `main` via PR (or closes the Spec/Spec Review issues directly if no branch exists), then deletes the branch and closes the Spec Review issue if one exists.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Spec Merge & Cleanup

This skill is invoked by `$review-spec`'s Exit Gate once a review returns exactly zero Blocking findings (and any Root Blocker Ledger / acceptance matrix has no open or regressed cells). Execution splits into two paths depending on whether this spec actually used the standard branch pattern.

## Step 0 — Route: Standard Path vs. Direct-Close Path

The `$to-tickets` skill creates this branch directly, via `git checkout -b spec-<spec_issue_number> ...` off the captured baseline commit. If the user overrode that pattern for this spec — working directly on `main` or some other branch instead — `spec-<spec_issue_number>` never existed, which also means **there is no PR that will ever exist to auto-close the Spec issue**. On this path, closure has to happen explicitly, right here, rather than being deferred to a PR merge that isn't coming:

```bash
if ! git show-ref --verify --quiet "refs/heads/spec-<spec_issue_number>" && \
   ! git ls-remote --exit-code --heads origin "spec-<spec_issue_number>" >/dev/null 2>&1; then

  echo "No spec-<spec_issue_number> branch found locally or on origin — this spec didn't use the standard branch pattern (likely overridden). No PR will ever exist for it, so close both issues explicitly rather than relying on auto-close."

  # No PR exists or ever will for this spec, so the Spec issue must be closed
  # explicitly here rather than relying on a PR's "Closes #<n>" trigger.
  gh issue close <spec_issue_number> --comment "Spec work completed and reviewed directly (no dedicated branch was used for this spec). Zero blocking findings on final review."

  # Same conditional as Phase B Step 5 below — a Spec Review issue only exists if
  # this spec required at least one remediation loop (see the /review-spec-remediation skill's,
  # First-Pass Failure step).
  if [ -n "$SPEC_REVIEW_ISSUE_NUMBER" ]; then
    gh issue close "$SPEC_REVIEW_ISSUE_NUMBER" --comment "Spec #<spec_issue_number> closed directly (no dedicated branch was used for this spec). Zero blocking findings on final review."
  else
    echo "No Spec Review issue was created for this spec (passed on the first review) — nothing to close."
  fi

  exit 0
fi
```

If the branch was found, continue to Phase A below — the standard PR-merge path closes both issues at their respective points instead: the Spec issue via the PR's `Closes #<spec_issue_number>` in Phase A, and the Spec Review issue explicitly in Phase B's Finalize step.

## Phase A — Merge to Main

1. **Confirm Precondition**: Do not proceed unless `$review-spec`'s Exit Gate authorized it for `spec-<spec_issue_number>` — i.e., that review's aggregate audit returned exactly zero Blocking findings. If Blocking findings remain, this skill should not have been invoked at all; return to `$review-spec` and follow its Remediation Loop instead.
2. **Push Final State**: Explicitly checkout the spec branch rather than assuming it's still checked out (this may be running in a fresh session), then ensure everything committed on it is on the remote — defensive, since you should already be committing/pushing as you go per `$implement-ticket`, but this guards against any stragglers:
   ```bash
   git checkout spec-<spec_issue_number>
   git push origin spec-<spec_issue_number>
   ```
3. **Create the PR (idempotent)**: Check for an existing open PR before creating a new one, so this step is safe to re-run:
   ```bash
   EXISTING_PR=$(gh pr list --head spec-<spec_issue_number> --state open --json number -q '.[0].number')

   if [ -z "$EXISTING_PR" ]; then
     SPEC_TITLE=$(gh issue view <spec_issue_number> --json title -q .title)
     gh pr create \
       --base main \
       --head spec-<spec_issue_number> \
       --title "Spec #<spec_issue_number>: ${SPEC_TITLE}" \
       --body "Closes #<spec_issue_number>"
   fi
   ```
   The `Closes #<spec_issue_number>` line auto-closes the parent spec issue the moment this PR merges.
4. **Merge the PR**: Use a regular merge commit — **not squash** — so commit ancestry is preserved. This matters because Phase B's `git branch -d` (Step 3 below) relies on ancestry to verify the branch is safely mergeable before deleting it; a squash merge would break that check permanently.
   ```bash
   PR_NUMBER=$(gh pr list --head spec-<spec_issue_number> --state open --json number -q '.[0].number')
   gh pr merge "$PR_NUMBER" --merge
   ```
   Deliberately **not** using `--delete-branch` here — you're still sitting on `spec-<spec_issue_number>` at this point (per Step 2 above), and Git won't let you delete the branch you're currently checked out on. Local branch deletion is handled explicitly in Phase B instead, right after switching to `main`.
5. **Verify Merge Succeeded**: Do not proceed to cleanup on a failed or unmerged PR:
   ```bash
   MERGED_STATE=$(gh pr view "$PR_NUMBER" --json state -q .state)
   if [ "$MERGED_STATE" != "MERGED" ]; then
     echo "❌ PR #$PR_NUMBER did not merge (state: $MERGED_STATE). Halting before cleanup — resolve manually."
     exit 1
   fi
   ```

## Phase B — Branch Cleanup

Only reached if Phase A confirmed a successful merge.

1. **Confirm Current Branch**: Non-fatal sanity check before switching away from the spec branch — if something switched branches mid-session, worth knowing about, but Step 0 already confirmed the branch itself exists, so this doesn't block cleanup either way:
   ```bash
   CURRENT_BRANCH=$(git branch --show-current)
   if [ "$CURRENT_BRANCH" != "spec-<spec_issue_number>" ]; then
     echo "⚠️ Expected to be on spec-<spec_issue_number> but current branch is $CURRENT_BRANCH. Continuing cleanup anyway."
   fi
   ```
2. **Sync Local Main**: Make sure `main` is actually checked out before pulling — don't assume the current branch — then pull down the merge you just made so it's reflected before branch deletion is evaluated against it:
   ```bash
   git checkout main
   git pull origin main
   ```
3. **Delete Local Branch**: This should now succeed cleanly — the merge commit in Step 4 of Phase A preserved ancestry, so Git can verify it:
   ```bash
   git branch -d spec-<spec_issue_number>
   ```
   If this fails, treat it as a signal to stop and investigate — do not force it with `-D`.
4. **Delete Remote Branch**: Safe to do unconditionally here, since Phase A already confirmed the PR merged:
   ```bash
   git push origin --delete spec-<spec_issue_number>
   ```
5. **Finalize: Close the Spec Review Issue (if one exists)**: Only reached if every step above succeeded. A "Spec Review" issue only exists if this spec required at least one remediation loop — created in the `$review-spec-remediation` skill's *First-Pass Failure* step, or reused across its *Recursive Passes* step. If the audit returned zero Blocking findings on the very first pass, no such issue was ever created, and this step should be skipped entirely — there's nothing to close. The Spec issue itself is already closed automatically via the PR's `Closes #<spec_issue_number>`; the Spec Review issue has no equivalent automatic trigger, so it must be closed explicitly when it exists. (For specs with no branch, this same closure already happened in Step 0's routing check above, and this step is never reached.):
   ```bash
   if [ -n "$SPEC_REVIEW_ISSUE_NUMBER" ]; then
     gh issue close "$SPEC_REVIEW_ISSUE_NUMBER" --comment "Spec merged (PR #$PR_NUMBER) and branch cleaned up. Zero blocking findings on final review."
   else
     echo "No Spec Review issue was created for this spec (passed on the first review) — nothing to close."
   fi
   ```
