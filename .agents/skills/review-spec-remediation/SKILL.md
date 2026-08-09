---
name: review-spec-remediation
description: Invoked only by `$review-spec` when a review returns one or more Blocking findings — not a standalone command. Synthesizes findings into a Root Blocker Ledger, creates or updates the tracking issue, and halts for the Human Handoff Intercept so `$to-tickets` can slice the blockers into tickets.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Review Spec Remediation

This skill is invoked by `$review-spec` whenever its Aggregate step finds one or more Blocking findings. You are strictly prohibited from performing immediate, "in-flight" file edits to fix code-review errors — this skill's job is to turn Blocking findings into a tracked remediation loop, not to fix them. Once this skill halts for the Human Handoff Intercept (or, on a Recursive Pass, confirms no Blocking findings remain), return to `$review-spec`'s Exit Gate.

If a Blocking Architecture finding with `Architecture decision required: Yes` reaches this skill, halt and return it to `$review-spec`, which owns delegation to `$architecture-remediation`. Unresolved architecture must not be synthesized into remediation tickets.

## Synthesizing Root Blockers

When any Blocking findings remain, synthesize them into root blockers before
creating or updating the tracking issue:

* Group related findings by the durable invariant they violate, not by the file,
  hunk, subsystem, or sub-agent that noticed them.
* Assign stable root IDs (`RB-1`, `RB-2`, ...). Keep existing IDs on later
  passes; never renumber merely because the evidence examples changed.
* For each root, record the invariant, affected surfaces/reference kinds,
  concrete evidence examples, exit checks, owner overrides, and current status.
* For Architecture roots, preserve `Architecture decision required: No`, the
  governing architectural authority, and the remediation routing supplied by
  `$review-architecture`. Do not reinterpret that architecture decision here.
* Classify every new Blocking finding as one of:

  * `new root` — a distinct invariant not already represented;
  * `child symptom` — another manifestation of an existing root; or
  * `regression` — a previously ticketed/closed root or symptom that current
    source truth still violates.
* For cross-cutting specs, maintain a compact acceptance matrix in the parent
  issue. Rows should be the relevant output/evidence families; columns should be
  the obligations that prove the spec through production paths (for example:
  assembly, canonical persistence, reconstruction validation, fail-closed
  readiness, observability, negative tests). Use the spec's own vocabulary rather
  than inventing generic rows.

Use these parseable headings when a parent Spec Review issue has blockers:

```markdown id="b8v6sl"
## Root Blocker Ledger

### RB-1 — <short root name>
Status: open | closed | regressed | owner-overridden
Invariant: <durable invariant being violated>
Architecture decision required: No
Governing authority: <ADR/doc/invariant>
Affected surfaces/reference kinds: <comma-separated list>
Exit checks: <production-path checks/tests required to close the root>
Current evidence: <short bullets or dated finding references>

## Spec Acceptance Matrix

| Root | Surface/reference kind | Production-path obligation | Status | Evidence |
| --- | --- | --- | --- | --- |
```

Omit `Architecture decision required` and `Governing authority` for non-Architecture roots.

Do not let a helper, validator, serializer, or test seam count as root-complete
unless the production path named by the spec is proven by source and tests.

## 1. First-Pass Failure: Parent Issue Creation

* Create a single, dedicated parent GitHub issue titled:
  `Spec Review: <Feature Name>`.
* Populate the description field with the aggregated breakdown of Blocking and
  Advisory findings, clearly separated. Blocking findings must be presented as a
  **Root Blocker Ledger** first, followed by concrete evidence examples. Treat
  individual bullets as evidence for roots, not as an ever-growing independent
  blocker list.
* Link this new tracking issue back to the original project Specification issue
  using a **fixed, parseable format** — the first line of the body must be:
  `**Parent Spec:** #<spec_issue_number>`. This isn't just a human-readable
  cross-reference: `$to-tickets` parses this exact line when it's later handed
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

## 2. The Human Handoff Intercept

Because the `$to-tickets` skill is explicitly locked to
`allow_implicit_invocation: false`, you cannot execute the slicing step yourself.
You MUST halt operations and present a clear **Human Action Block** instructing
the user to run the tool manually.

The handoff must say that `$to-tickets` should slice **Blocking findings only**
unless the user explicitly wants Advisory findings ticketed.

* **Required Terminal Output Template:**

  > ⚠️ **Spec Review Failed with [X] Blocking Findings.**
  > I have created or updated the parent tracking issue:
  > **`Spec Review: <Feature Name> #<Issue_ID>`**.
  >
  > Please run the following command to slice the Blocking findings into tracked
  > child tickets:
  >
  > ```
  > $to-tickets Spec Review: <Feature Name> #<Issue_ID>
  > ```

## 3. Handling Recursive Passes & Secondary Findings

When the user re-runs this `$review-spec` skill after completing child
remediation tickets, perform a bounded re-review:

* **DO NOT** create a brand-new parent issue.
* Verify whether previously recorded Blocking findings are fixed.
* Include regressions introduced by the remediation diff.
* Include newly exposed spec failures only when they are directly connected to a
  prior fix or the remediated behavior.
* Reconcile every finding against the existing Root Blocker Ledger before
  ticketing: update the existing root status/evidence when it is a child symptom,
  mark it as a regression when a closed ticket did not actually satisfy the root,
  and create a new root only when the invariant is genuinely distinct.
* Preserve Architecture routing metadata for existing Architecture roots unless
  `$review-architecture` explicitly changes it on the new review pass.
* Update the acceptance matrix with proven, unproven, or regressed cells. A root
  is not fixed while any required production-path cell for that root remains
  unproven.
* Do not re-mine the full original diff for new Advisory smells.
* Do not add new Blocking Standards findings unless they are deterministic,
  cite a documented standard, and were introduced by the remediation work or
  missed because a previous blocker hid the code path.
* Open the existing parent "Spec Review" issue and append new Blocking or useful
  Advisory findings to the bottom of the body under a fresh, dated header:
  `## Re-review Findings [YYYY-MM-DD HH:MM]`. Read the current body and write
  back the original content plus the new section and any Root Blocker Ledger /
  acceptance-matrix updates — do not replace it with only the new section, or
  the `**Parent Spec:** #<n>` line from Step 1 above is lost, and `$to-tickets`
  will no longer be able to resolve which branch to reuse on the next remediation
  pass.
* Re-trigger the **Human Handoff Intercept** block only when Blocking findings
  remain.

## 4. Owner Overrides

If the user/owner explicitly authorizes or rejects a finding:

* Update the parent issue to record the override and remove the finding from the
  Blocking count.
* Suppress the same finding in future review passes unless the implementation
  materially changes.
* Treat authorized scope creep as Owner-overridden, not as a Spec failure.
