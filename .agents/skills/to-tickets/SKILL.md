---
name: to-tickets
description: Break a plan, spec, or the current conversation into a set of tracer-bullet tickets, each declaring its blocking edges, published to the configured tracker — edges as text in one file per ticket locally, or native blocking links on a real tracker.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Tickets

Break a plan, spec, or conversation into a set of **tickets** — tracer-bullet vertical slices, each declaring the tickets that **block** it.
The issue tracker and triage label vocabulary should have been provided to you — run `/setup-matt-pocock-skills` if not.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a reference (a spec path, an issue number or URL) as an argument, fetch it and read its full body and comments.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Ticket titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

Look for opportunities to prefactor the code to make the implementation easier. "Make the change easy, then make the easy change."

### 3. Draft vertical slices

Break the work into **tracer bullet** tickets.

<vertical-slice-rules>

- Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests) — vertical, NOT a horizontal slice of one layer
- A completed slice is demoable or verifiable on its own
- Each slice is sized to fit in a single fresh context window
- Any prefactoring should be done first

</vertical-slice-rules>

Give each ticket its **blocking edges** — the other tickets that must complete before it can start. A ticket with no blockers can start immediately.

**If the source issue is a `/review-spec` parent issue** (title prefixed `Spec Review: `), this is a remediation re-invocation, not a fresh breakdown — stop here and invoke `/to-remediation-tickets` before drafting anything. It defines the Root Blocker Ledger process and the strict delta analysis that replace ordinary vertical-slice drafting for this case. Once it hands you a ticket list, return here and continue at Step 4.

**Wide refactors are the exception to vertical slicing.** A **wide refactor** is one mechanical change — rename a column, retype a shared symbol — whose **blast radius** fans across the whole codebase, so a single edit breaks thousands of call sites at once and no vertical slice can land green. Don't force it into a tracer bullet; sequence it as **expand–contract**. First expand: add the new form beside the old so nothing breaks. Then migrate the call sites over in batches sized by blast radius (per package, per directory), each batch its own ticket blocked by the expand, keeping CI green batch to batch because the old form still exists. Finally contract: delete the old form once no caller remains, in a ticket blocked by every migrate batch. When even the batches can't stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify ticket — green is promised only there.

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each ticket, show:

- **Title**: short descriptive name
- **Blocked by**: which other tickets (if any) must complete first
- **What it delivers**: the end-to-end behaviour this ticket makes work

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the blocking edges correct — does each ticket only depend on tickets that genuinely gate it?
- Should any tickets be merged or split further?

Iterate until the user approves the breakdown.

### 5. Publish the tickets to the configured tracker

Publish the approved tickets. **How** depends on the tracker `/setup-matt-pocock-skills` configured — the tickets are the same either way, only the shape of the blocking edges changes:

- **Local files** → write one file per ticket under `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01` in dependency order (blockers first). Each file's "Blocked by" lists the numbers/titles it depends on. Use the per-ticket file template below — one ticket per file, never a single combined file.
- **A real issue tracker (GitHub, Linear, …)** → publish one issue per ticket in dependency order (blockers first) so each ticket's blocking edges can reference real identifiers. Use the platform's native blocking / sub-issue relationship where it has one — for GitHub specifically, invoke `/github-issue-dependencies` for the exact commands rather than researching this from scratch; otherwise set each ticket's "Blocked by" to the blocking issues as text. Apply the `ready-for-agent` triage label unless instructed otherwise — the tickets are agent-grabbable by construction.

Work the **frontier**: any ticket whose blockers are all done. For a purely linear chain that means top to bottom.

Do NOT close or modify any parent issue. (This refers to the ticket-publishing step above — the Spec Branch Rule below separately posts an additive metadata *comment* on first use only; it never edits the issue body or state.)

<local-ticket-template>

# <NN> — <Ticket title>

**Root blocker:** for Spec Review remediation tickets only, `RB-<n>` and the root invariant this ticket is intended to close. Omit this line for ordinary plan/spec tickets. (See `/to-remediation-tickets` for how to derive this.)

**What to build:** the end-to-end behaviour this ticket makes work, from the user's perspective — not a layer-by-layer implementation list.

**Blocked by:** the numbers/titles of the tickets that gate this one, or "None — can start immediately".

**Ticket branch:** the shared branch for this spec, normally `spec-<spec_issue_number>`, an explicitly overridden shared branch name, or "None" when dedicated branch use was explicitly disabled.

**Status:** ready-for-agent

- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2

</local-ticket-template>

<issue-template>

## Parent

A reference to the parent issue on the tracker (if the source was an existing issue, otherwise omit this section).

## Root blocker

For Spec Review remediation tickets only: `RB-<n>` and the root invariant this
ticket is intended to close. Omit this section for ordinary plan/spec tickets.
(See `/to-remediation-tickets` for how to derive this.)

## What to build

The end-to-end behaviour this ticket makes work, from the user's perspective — not layer-by-layer implementation.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] For Spec Review remediation tickets: production-path proof and sibling-surface blast-radius audit for the root blocker are complete, or any remaining unproven cells are explicitly reported.

## Blocked by

- A reference to each blocking ticket, or "None — can start immediately".

## Ticket branch

- The shared branch for this spec, normally `spec-<spec_issue_number>`, an explicitly overridden shared branch name, or "None" when dedicated branch use was explicitly disabled.

</issue-template>

In either form, avoid specific file paths or code snippets — they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

Work the frontier one ticket at a time with `/implement-ticket`, clearing context between tickets.

## Spec Branch Rule

Unless overridden by the user, you MUST create a dedicated branch for all development work tied to this spec, after breaking the provided parent specification issue down into sub-tickets and publishing them to the configured tracker. This keeps the spec's commits grouped under one clearly-named branch, ready for `/review-spec` to diff against and merge later.

**This rule targets one branch per spec, not one per invocation of `/to-tickets`.** `/to-tickets` can legitimately be invoked twice for the same spec: once on the original Spec issue for the initial breakdown, and again later on the **Spec Review** issue that `/review-spec`'s remediation loop hands off to via its Human Handoff Intercept (title prefixed `Spec Review: `). Both invocations must resolve to the *same* branch — remediation tickets get implemented against the same in-progress code, not a fresh branch off `main`. Step 0 below exists to make that resolution explicit rather than assuming the provided issue number is always the spec itself.

0. **Resolve the Spec Issue Number**: Determine which issue number this branch should actually be named after:
   ```bash
   INPUT_ISSUE_NUMBER=<the issue number this invocation of /to-tickets was given>
   INPUT_ISSUE_TITLE=$(gh issue view "$INPUT_ISSUE_NUMBER" --json title -q .title)

   case "$INPUT_ISSUE_TITLE" in
     "Spec Review: "*)
       # Remediation re-invocation, handed a Spec Review issue — resolve the
       # ORIGINAL spec issue instead of using this one, so we reuse the
       # existing branch rather than branching a second one off main.
       spec_issue_number=$(gh issue view "$INPUT_ISSUE_NUMBER" --json body -q .body \
         | grep -oP '(?<=\*\*Parent Spec:\*\* #)\d+')
       if [ -z "$spec_issue_number" ]; then
         echo "❌ Could not resolve the parent Spec issue from #$INPUT_ISSUE_NUMBER's body. Halting — do not create a new branch blind."
         exit 1
       fi
       ;;
     *)
       # Fresh spec breakdown — this issue IS the spec issue.
       spec_issue_number="$INPUT_ISSUE_NUMBER"
       ;;
   esac
   ```
   This depends on `/review-spec` recording the link back to the original Spec issue as a `**Parent Spec:** #<n>` line in the Spec Review issue's body when it's created — confirm that convention is actually in place before relying on this.
1. **Extract Spec ID**: `<spec_issue_number>` is now resolved by Step 0 above, whether directly or via the Spec Review lookup.
2. **Name the Branch**: Construct the branch identity as `spec-<spec_issue_number>`.
3. **Capture Baseline**: Record the current commit hash of `main` so the branch is pinned to a fixed starting point, independent of any commits landing on `main` afterward. On a remediation re-invocation this value goes unused once Step 4 finds the branch already exists — that's expected, not a bug:
   ```bash
   BASELINE_COMMIT=$(git rev-parse main)
   ```
4. **Create or Switch to the Branch**: Check out the dedicated branch for this spec, branching explicitly from the captured baseline commit (not the live tip of `main`) — only if it doesn't already exist:
   ```bash
   if git show-ref --verify --quiet "refs/heads/spec-<spec_issue_number>"; then
     git checkout "spec-<spec_issue_number>"
   else
     git checkout -b "spec-<spec_issue_number>" "$BASELINE_COMMIT"
   fi
   ```
   This check makes the step idempotent — safe to re-run whether the session was interrupted and resumed, or this is a remediation re-invocation correctly routed back to the existing branch by Step 0.

   Since there's no isolated worktree, this switches the branch checked out in your *current* working directory. Make sure any uncommitted changes from whatever you were doing before are committed or stashed first — otherwise this checkout will carry them onto `spec-<spec_issue_number>`, or fail outright if they conflict with it.
5. **Record Baseline Metadata via GitHub CLI**: Use the `gh` CLI tool to record the baseline commit as a **comment** on the parent specification issue — only if it hasn't been posted already, so a remediation re-invocation doesn't leave a duplicate (never overwrite the issue body — `gh issue edit --body` replaces the full description and risks destroying the original spec text):
   ```bash
   ALREADY_POSTED=$(gh issue view <spec_issue_number> --json comments -q '.comments[].body' \
     | grep -c "## Workspace Metadata" || true)

   if [ "$ALREADY_POSTED" -eq 0 ]; then
     gh issue comment <spec_issue_number> --body "$(printf '## Workspace Metadata\n**Baseline Commit Hash:** %s\n**Branch:** spec-%s\n' "$BASELINE_COMMIT" "<spec_issue_number>")"
   fi
   ```
   `/review-spec`'s "Pin the fixed point" step reads this back to resolve the fixed point for its diff — when you patch that file next, double check it's actually reading issue *comments* (not just the body) to find this, since that's where this step posts it.
