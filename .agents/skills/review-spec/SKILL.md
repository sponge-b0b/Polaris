---
name: review-spec
description: Review the changes of the provided spec since a fixed point (commit, branch, tag, or merge-base). Review the spec along two axes — Standards (does the code follow this repo's documented coding standards?) and Spec (does the code match what the originating issue/spec asked for?). Run both reviews in parallel sub-agents and report them side by side.
compatibility: product=codex product=claude-code system=git system=python network=none
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

Whatever the user said is the fixed point — a commit SHA, branch name, tag,
`main`, `HEAD~5`, etc. If they didn't specify one, ask for it.

Capture the diff command once: `git diff <fixed-point>...HEAD` (three-dot, so
the comparison is against the merge-base). Also note the list of commits via
`git log <fixed-point>..HEAD --oneline`.

Before going further, confirm the fixed point resolves (`git rev-parse
<fixed-point>`) and the diff is non-empty. A bad ref or empty diff should fail
here — not inside two parallel sub-agents.

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
- Natively link or cross-reference this new tracking issue to the original
  project Specification issue.

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
  `## Re-review Findings [YYYY-MM-DD HH:MM]`.
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

You are authorized to log a closing comment and **Close** the parent "Spec
Review" issue when a complete audit run returns exactly zero **Blocking**
findings.

Advisory findings may remain documented without preventing closure. Owner-
overridden findings must remain suppressed in future review passes.
