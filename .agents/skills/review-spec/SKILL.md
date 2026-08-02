---
name: review-spec
description: Review the changes of the provided spec since a fixed point (commit, branch, tag, or merge-base). Review the spec along two axes — Standards (does the code follow this repo's documented coding standards?) and Spec (does the code match what the originating issue/spec asked for?). Run both reviews in parallel sub-agents and report them side by side. On a clean pass (zero Blocking findings), also merges the spec branch into `main` via PR and deletes the spec branch (local and remote).
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

Two-axis review of the diff between `HEAD` and a fixed point the user supplies:

- **Standards** — does the code conform to this repo's documented coding standards?
- **Spec** — does the code faithfully implement the originating issue / spec?

Both axes run as **parallel sub-agents** so they don't pollute each other's context,
then this skill aggregates their findings. The review loop is bounded: it closes
when there are zero **Blocking** findings, even if Advisory notes remain.

The issue tracker should have been provided to you — run `/setup-matt-pocock-skills`
if `docs/agents/issue-tracker.md` is missing.

## Finding Taxonomy

Every finding must be classified before it is counted or ticketed:

- **Blocking** — must be remediated before the spec review can close. Includes
  spec mismatches, implemented-wrong behavior, missing required acceptance tests
  or docs, and hard violations of documented repo standards.
- **Advisory** — useful but non-blocking observations. Includes Fowler smells,
  design-smell heuristics, duplication suggestions, maintainability concerns, and
  speculative cleanup. Advisory findings are not included in the blocking count
  and are not sliced into tickets unless the user explicitly asks.
- **Owner-overridden** — findings explicitly accepted, authorized, or rejected by
  the owner. Do not include these in the blocking count, do not ticket them, and
  do not re-raise them as blockers on later review passes. Record the override in
  the parent review issue when relevant so future agents can suppress it.

Classification rules:

- Spec-axis mismatches are Blocking by default.
- Documented-standard violations are Blocking by default when the cited standard
  is specific and the violation is deterministic.
- Smell-baseline findings are always Advisory by default. They become Blocking
  only if the user/owner explicitly promotes them.
- Scope-creep findings are suppressed as Owner-overridden when the user/owner has
  explicitly authorized the work.
- Tool-enforced issues should be skipped unless the tooling cannot reasonably
  catch them in this diff.

## Process

### 1. Pin the fixed point

The fixed point is automatically stored in the parent specification issue on GitHub, unless explicitly overridden or provided by the user. Follow these steps to resolve and validate it:

1. **Extract Baseline Metadata**: `/to-tickets` posts the baseline as a **comment** on the parent spec issue (it never edits the issue body — see the Spec Branch Rule in `/to-tickets`), so fetch comments specifically, not just the body, to find and parse the **Baseline Commit Hash**:
   ```bash
   BASELINE_COMMIT=$(gh issue view <spec_issue_number> --json comments -q '.comments[].body' \
     | grep -oP '(?<=\*\*Baseline Commit Hash:\*\* )\S+' | tail -1)
   ```
2. **Fallback**: If the metadata is missing (checked across the issue's comments) and the user did not explicitly specify a commit SHA, branch name, tag, or relative ref (e.g., `main`, `HEAD~5`), ask the user for it directly.
3. **Verify Branch Checked Out**: Ensure `spec-<spec_issue_number>` is actually the currently checked-out branch before running the diff commands below — there's no isolated worktree here to make this automatic, so it's easy to accidentally review against the wrong branch if something switched branches earlier in the session:
   ```bash
   CURRENT_BRANCH=$(git branch --show-current)
   if [ "$CURRENT_BRANCH" != "spec-<spec_issue_number>" ]; then
     echo "❌ Expected spec-<spec_issue_number> to be checked out, but current branch is $CURRENT_BRANCH. Checkout the spec branch before continuing."
     exit 1
   fi
   ```
4. **Validate the Ref**: Confirm the extracted or provided fixed point resolves locally by running:
   ```bash
   git rev-parse <fixed-point>
   ```
   *If the ref is bad or fails to resolve, halt execution immediately with a clear error message.*
5. **Capture Diff and Log**: Once validated, capture the targeted differential context since development started:
   * **The Diff**: Run `git diff <fixed-point>...HEAD` (three-dot comparison to evaluate strictly against the merge-base).
   * **The Commit Log**: Run `git log <fixed-point>..HEAD --oneline` to note the exact list of commits authored on this spec branch.
6. **Pre-Flight Check**: Verify that the generated diff is non-empty. An empty diff or unresolved ref must fail immediately here—never inside down-stream parallel sub-agents. Use this comprehensive diff as the primary source of truth to review if the aggregate changes accurately satisfy the parent specification goals.

### 2. Identify the spec source

Look for the originating spec, in this order:

1. Issue references in the commit messages (`#123`, `Closes #45`, GitLab `!67`,
   etc.) — fetch via the workflow in `docs/agents/issue-tracker.md`.
2. A path the user passed as an argument.
3. A spec file under `docs/`, `specs/`, or `.scratch/` matching the branch name
   or feature.
4. If nothing is found, ask the user where the spec is. If they say there isn't
   one, the **Spec** sub-agent will skip and report "no spec available".

### 3. Identify the standards sources

Anything in the repo that documents how code should be written, such as
`CODING_STANDARDS.md` or `CONTRIBUTING.md`.

### 4. Spawn both sub-agents in parallel

Send a single message with two `Agent` tool calls. Use the `general-purpose`
subagent for both.

**Standards sub-agent prompt** — include:

- The full diff command and commit list.
- The list of standards-source files you found in step 3, **plus the smell
  baseline from step 3** pasted in full — the sub-agent has no other access to
  it.
- The Finding Taxonomy from this skill.
- The brief: "Report — per file/hunk where relevant — (a) every place the diff
  violates a documented standard: cite the standard (file + the rule); and (b)
  any baseline smell you spot: name it and quote the hunk. Label each finding as
  Blocking or Advisory. Documented-standard breaches can be Blocking when they
  cite a specific deterministic rule; baseline smells are Advisory by default,
  and a documented repo standard overrides the baseline. Skip anything tooling
  enforces. Under 400 words. If no findings, say `No findings.`"

**Spec sub-agent prompt** — include:

- The diff command and commit list.
- The path or fetched contents of the spec.
- The Finding Taxonomy from this skill.
- The brief: "Report: (a) requirements the spec asked for that are missing or
  partial; (b) behaviour in the diff that wasn't asked for and was not explicitly
  owner-authorized; (c) requirements that look implemented but where the
  implementation looks wrong. Quote the spec line for each finding. Label each
  finding as Blocking, Advisory, or Owner-overridden. Suppress scope-creep
  findings when the owner explicitly authorized the work. Under 400 words. If no
  findings, say `No findings.`"

If the spec is missing, skip the Spec sub-agent and note this in the final
report.

### 5. Aggregate

Lightly validate sub-agent findings before adding them to the final report or the
issue tracker:

- Confirm Blocking Standards findings cite a documented rule and are not merely a
  smell-baseline judgement call.
- Confirm scope-creep findings have not been explicitly owner-authorized.
- Confirm Owner-overridden findings are not counted or ticketed.
- Do not merge the Standards and Spec axes or pick one overall priority winner.

Present the two reports under `## Standards` and `## Spec` headings. Within each
axis, use `### Blocking` and `### Advisory` subsections when both exist. Mention
Owner-overridden findings only when useful to explain suppression.

End with a one-line summary that counts Blocking and Advisory findings separately
per axis and names the worst Blocking issue within each axis, if any.

## Why two axes

A change can pass one axis and fail the other:

- Code that follows every standard but implements the wrong thing → **Standards
  pass, Spec fail.**
- Code that does exactly what the issue asked but breaks the project's
  conventions → **Spec pass, Standards fail.**

Reporting them separately stops one axis from masking the other.

## Remediation Loop & Human Handoff Rules

You are strictly prohibited from performing immediate, "in-flight" file edits to
fix code-review errors. If your verification pass reveals any **Blocking**
specification mismatches or standards violations, follow this exact sequence.
Advisory-only findings do not trigger the handoff block unless the user asks to
promote or ticket them.

### 1. First-Pass Failure: Parent Issue Creation

- Create a single, dedicated parent GitHub issue titled:
  `Spec Review: <Feature Name>`.
- Populate the description field with the aggregated breakdown of Blocking and
  Advisory findings, clearly separated.
- Link this new tracking issue back to the original project Specification issue
  using a **fixed, parseable format** — the first line of the body must be:
  `**Parent Spec:** #<spec_issue_number>`. This isn't just a human-readable
  cross-reference: `/to-tickets` parses this exact line when it's later handed
  this Spec Review issue during a remediation re-invocation, to resolve which
  spec's branch to reuse rather than accidentally branching a new one off
  `main`. Do not substitute a differently-worded reference, a GitHub "Tracked
  by" relationship, or a plain `#<n>` mention elsewhere in the body — none of
  those are what the parser looks for.
  ```bash
  gh issue create \
    --title "Spec Review: <Feature Name>" \
    --body "$(printf '**Parent Spec:** #%s\n\n%s' "<spec_issue_number>" "$AGGREGATED_FINDINGS_BODY")"
  ```

### 2. The Human Handoff Intercept

Because the `/to-tickets` skill is explicitly locked to
`allow_implicit_invocation: false`, you cannot execute the slicing step yourself.
You MUST halt operations and present a clear **Human Action Block** instructing
the user to run the tool manually.

The handoff must say that `/to-tickets` should slice **Blocking findings only**
unless the user explicitly wants Advisory findings ticketed.

- **Required Terminal Output Template:**
  > ⚠️ **Spec Review Failed with [X] Blocking Findings.**
  > I have created or updated the parent tracking issue:
  > **`Spec Review: <Feature Name> #<Issue_ID>`**.
  >
  > Please run the following command to slice the Blocking findings into tracked
  > child tickets:
  > ```
  > $to-tickets Spec Review: <Feature Name> #<Issue_ID>
  > ```

### 3. Handling Recursive Passes & Secondary Findings

When the user re-runs this `/review-spec` skill after completing child
remediation tickets, perform a bounded re-review:

- **DO NOT** create a brand-new parent issue.
- Verify whether previously recorded Blocking findings are fixed.
- Include regressions introduced by the remediation diff.
- Include newly exposed spec failures only when they are directly connected to a
  prior fix or the remediated behavior.
- Do not re-mine the full original diff for new Advisory smells.
- Do not add new Blocking Standards findings unless they are deterministic,
  cite a documented standard, and were introduced by the remediation work or
  missed because a previous blocker hid the code path.
- Open the existing parent "Spec Review" issue and append new Blocking or useful
  Advisory findings to the bottom of the body under a fresh, dated header:
  `## Re-review Findings [YYYY-MM-DD HH:MM]`. Read the current body and write
  back the original content plus the new section — do not replace it with only
  the new section, or the `**Parent Spec:** #<n>` line from Step 1 above is
  lost, and `/to-tickets` will no longer be able to resolve which branch to
  reuse on the next remediation pass.
- Re-trigger the **Human Handoff Intercept** block only when Blocking findings
  remain.

### 4. Owner Overrides

If the user/owner explicitly authorizes or rejects a finding:

- Update the parent issue to record the override and remove the finding from the
  Blocking count.
- Suppress the same finding in future review passes unless the implementation
  materially changes.
- Treat authorized scope creep as Owner-overridden, not as a Spec failure.

### 5. The Exit Gate

You are authorized to proceed to the Merge & Cleanup workflow — **not** to close the "Spec" issue directly — when a complete audit run returns exactly zero **Blocking** findings.

Advisory findings may remain documented without preventing progression. Owner-overridden findings must remain suppressed in future review passes.

Do **not** close the "Spec" issue at this gate. It is closed either automatically when the merge PR lands (Phase A, via `Closes #<spec_issue_number>` in the PR body), or explicitly by the routing step at the start of the next section if this spec has no branch — and therefore no PR — to merge at all. Closing it here — before either of those is confirmed — would mark the issue done even if the merge is later halted, fails, or never happens.

Do **not** close the parent "Spec Review" issue here either. That closure happens only once one of the two paths below has fully completed — at the end of Phase B for the standard PR path, or immediately within the routing step for the no-branch path — **and only if a Spec Review issue exists for this spec** in either case. This keeps both issues' closed state aligned with verified completion, not with the audit decision alone.

## Spec Merge & Branch Cleanup Rule

This runs only once the Exit Gate above has authorized it — i.e., this review's own aggregate audit returned exactly zero **Blocking** findings. From here, execution splits into two paths depending on whether this spec actually used the standard branch pattern.

### Step 0 — Route: Standard Path vs. Direct-Close Path

The `/to-tickets` skill creates this branch directly, via `git checkout -b spec-<spec_issue_number> ...` off the captured baseline commit. If the user overrode that pattern for this spec — working directly on `main` or some other branch instead — `spec-<spec_issue_number>` never existed, which also means **there is no PR that will ever exist to auto-close the Spec issue**. On this path, closure has to happen explicitly, right here, rather than being deferred to a PR merge that isn't coming:

```bash
if ! git show-ref --verify --quiet "refs/heads/spec-<spec_issue_number>" && \
   ! git ls-remote --exit-code --heads origin "spec-<spec_issue_number>" >/dev/null 2>&1; then

  echo "No spec-<spec_issue_number> branch found locally or on origin — this spec didn't use the standard branch pattern (likely overridden). No PR will ever exist for it, so close both issues explicitly rather than relying on auto-close."

  # No PR exists or ever will for this spec, so the Spec issue must be closed
  # explicitly here rather than relying on a PR's "Closes #<n>" trigger.
  gh issue close <spec_issue_number> --comment "Spec work completed and reviewed directly (no dedicated branch was used for this spec). Zero blocking findings on final review."

  # Same conditional as Phase B Step 5 below — a Spec Review issue only exists if
  # this spec required at least one remediation loop (see Remediation Loop, Step 1).
  if [ -n "$SPEC_REVIEW_ISSUE_NUMBER" ]; then
    gh issue close "$SPEC_REVIEW_ISSUE_NUMBER" --comment "Spec #<spec_issue_number> closed directly (no dedicated branch was used for this spec). Zero blocking findings on final review."
  else
    echo "No Spec Review issue was created for this spec (passed on the first review) — nothing to close."
  fi

  exit 0
fi
```

If the branch was found, continue to Phase A below — the standard PR-merge path closes both issues at their respective points instead: the Spec issue via the PR's `Closes #<spec_issue_number>` in Phase A, and the Spec Review issue explicitly in Phase B's Finalize step.

### Phase A — Merge to Main

1. **Confirm Precondition**: Do not proceed unless the Exit Gate above authorized it for `spec-<spec_issue_number>` — i.e., this review's aggregate audit returned exactly zero Blocking findings. If Blocking findings remain, do not run this phase; follow the Human Handoff Intercept instead.
2. **Push Final State**: Explicitly checkout the spec branch rather than assuming it's still checked out from Section 1 (this may be running in a fresh session), then ensure everything committed on it is on the remote — defensive, since you should already be committing/pushing as you go per `/implement-ticket`, but this guards against any stragglers:
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

### Phase B — Branch Cleanup

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
5. **Finalize: Close the Spec Review Issue (if one exists)**: Only reached if every step above succeeded. A "Spec Review" issue only exists if this spec required at least one remediation loop — created in the *First-Pass Failure* step (Remediation Loop, Step 1), or reused across *Recursive Passes* (Step 3). If the audit returned zero Blocking findings on the very first pass, no such issue was ever created, and this step should be skipped entirely — there's nothing to close. The Spec issue itself is already closed automatically via the PR's `Closes #<spec_issue_number>`; the Spec Review issue has no equivalent automatic trigger, so it must be closed explicitly when it exists. (For specs with no branch, this same closure already happened in Step 0's routing check above, and this step is never reached.):
   ```bash
   if [ -n "$SPEC_REVIEW_ISSUE_NUMBER" ]; then
     gh issue close "$SPEC_REVIEW_ISSUE_NUMBER" --comment "Spec merged (PR #$PR_NUMBER) and branch cleaned up. Zero blocking findings on final review."
   else
     echo "No Spec Review issue was created for this spec (passed on the first review) — nothing to close."
   fi
   ```
