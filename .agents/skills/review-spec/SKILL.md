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

This is a **review-only** workflow, not a verification workflow. Do not run
`pytest`, `ruff`, `mypy`, graph updates, duplication scans, or other static/test
verification commands from this skill. If spec-wide verification is needed, stop
and invoke `/verify-spec` as a separate workflow.

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

Use the `/coding-standards` skill as the definitive source for the project's coding standards
and anything in the repo that documents how code should be written, such as `CONTRIBUTING.md`.

### 4. Spawn both sub-agents in parallel

Send a single message with two `Agent` tool calls. Use the `general-purpose`
subagent for both.

**Main-agent orchestration boundary:** after spawning, do not independently
perform the Standards review or the Spec review while the sub-agents run. Waiting
time may be used only for orchestration work that does not discover new review
findings, such as preparing report headings, checking tracker metadata, or
collecting already-identified context. Do not inspect additional hunks, run
verification commands, or duplicate a sub-agent's assigned analysis.

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
issue tracker. Validation is bounded to checking whether a cited finding is
legitimate; it is not permission to perform a fresh review pass or verification
run.

- Confirm Blocking Standards findings cite a documented rule and are not merely a
  smell-baseline judgement call.
- Confirm scope-creep findings have not been explicitly owner-authorized.
- Confirm Owner-overridden findings are not counted or ticketed.
- Inspect only the standards/spec text or diff/source evidence needed to validate
  a sub-agent's cited finding; do not search for additional findings yourself.
- Do not run tests, static checks, format checks, graph updates, or duplication
  scans while aggregating. Those belong to `/verify-spec` or `/verify-code`.
- Do not merge the Standards and Spec axes or pick one overall priority winner.

Present the two reports under `## Standards` and `## Spec` headings. Within each
axis, use `### Blocking` and `### Advisory` subsections when both exist. Mention
Owner-overridden findings only when useful to explain suppression.

End with a one-line summary that counts Blocking and Advisory findings separately
per axis and names the worst Blocking issue within each axis, if any.

If any Blocking findings remain, do not synthesize them into root blockers or
create/update a tracking issue yourself here — that entire process lives in
the `/review-spec-remediation` skill. See "Remediation Loop" below.

## Why two axes

A change can pass one axis and fail the other:

- Code that follows every standard but implements the wrong thing → **Standards
  pass, Spec fail.**
- Code that does exactly what the issue asked but breaks the project's
  conventions → **Spec pass, Standards fail.**

Reporting them separately stops one axis from masking the other.

## Remediation Loop

You are strictly prohibited from performing immediate, "in-flight" file edits to
fix code-review errors. If your verification pass reveals any **Blocking**
specification mismatches or standards violations, do not attempt to resolve them
yourself, and do not draft or publish any tracking issue directly — invoke the 
`/review-spec-remediation` skill in full instead. It covers root-blocker
synthesis, Parent Issue Creation, the Human Handoff Intercept, Recursive Passes,
and Owner Overrides — the complete sequence for turning Blocking findings into a
tracked remediation loop. Advisory-only findings do not trigger this at all
unless the user asks to promote or ticket them.

Once that skill completes — either by creating/updating the tracking issue and
halting for the Human Handoff Intercept, or by confirming Owner Overrides
suppressed every remaining finding — return here to the Exit Gate below.

## The Exit Gate

You are authorized to proceed and invoke the `/spec-merge-cleanup` skill — **not** to close the "Spec" issue directly — when a complete audit run returns exactly zero **Blocking** findings and any Root Blocker Ledger / acceptance matrix maintained for the Spec Review issue has no open or regressed root cells.

Advisory findings may remain documented without preventing progression. Owner-overridden findings must remain suppressed in future review passes.

Do **not** close the "Spec" issue at this gate. It is closed either automatically when the merge PR lands (`/spec-merge-cleanup` skill's Phase A, via `Closes #<spec_issue_number>` in the PR body), or explicitly by that skill's routing step if this spec has no branch — and therefore no PR — to merge at all. Closing it here — before either of those is confirmed — would mark the issue done even if the merge is later halted, fails, or never happens.

Do **not** close the parent "Spec Review" issue here either. That closure happens only once the `/spec-merge-cleanup` skill has fully completed one of its two paths — at the end of its Phase B for the standard PR path, or immediately within its routing step for the no-branch path — **and only if a Spec Review issue exists for this spec** in either case. This keeps both issues' closed state aligned with verified completion, not with the audit decision alone.
