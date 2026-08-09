---
name: to-tickets
description: Break a plan, spec, or the current conversation into a set of tracer-bullet tickets, each declaring its blocking edges, published to the configured tracker — edges as text in one file per ticket locally, or native blocking links on a real tracker.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Tickets

Break a plan, spec, or conversation into a set of **tickets** — tracer-bullet vertical slices, each declaring the tickets that **block** it.

The issue tracker and triage label vocabulary should have been provided to you — run `$setup-matt-pocock-skills` if not.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a reference (a spec path, issue number, or URL), fetch it and read its full body and comments.

If the source is a spec, use its **Architecture Impact** as routing context. Carry forward only the affected entities and governing ADR/doc references relevant to each ticket.

If the originating spec still has an unresolved material architecture question, stop and return to `$to-specs`; do not resolve architecture here.

A Blocking Architecture finding in a Spec Review issue is not by itself unresolved architecture. `$to-remediation-tickets` owns that routing.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state.

Use the project's domain glossary vocabulary and respect applicable ADRs.

Look for opportunities to prefactor the code to make implementation easier: make the change easy, then make the easy change.

### 3. Resolve ticket mode

Before drafting tickets, determine whether this is fresh slicing or remediation.

* If the source issue title is prefixed `Spec Review: `, invoke `$to-remediation-tickets`.
* If the source is an existing Spec that already has linked implementation tickets, invoke `$to-remediation-tickets`.
* Otherwise continue with fresh vertical-slice drafting.

`$to-remediation-tickets` owns delta analysis, duplicate prevention, open-ticket updates, superseded-ticket detection, and deciding which new tickets are actually required.

Once it returns a ticket delta, continue at Step 4.

#### Fresh vertical slices

Break the work into **tracer bullet** tickets.

<vertical-slice-rules>

* Each slice cuts a narrow but COMPLETE path through every required layer — vertical, not horizontal.
* A completed slice is demoable or independently verifiable.
* Each slice fits in one fresh context window.
* Any necessary prefactoring comes first.

</vertical-slice-rules>

Give each ticket its **blocking edges** — the tickets that must complete before it can start.

**Wide refactors are the exception.** When one mechanical change fans across the codebase and individual vertical slices cannot stay green, use expand–contract: expand first, migrate callers in independently manageable batches, then contract after all migrations complete.

### 4. Quiz the user

Present the proposed fresh breakdown or remediation delta.

For new tickets, show:

* **Title**
* **Blocked by**
* **What it delivers**

For remediation, also show any:

* open tickets to update;
* open tickets to close as superseded;
* dependency changes.

Ask:

* Does the granularity feel right?
* Are the blocking edges correct?
* Should anything be merged, split, or adjusted?

Iterate until approved.

If the remediation delta is empty, report that the existing ticket set already represents the current source and stop.

### 5. Publish to the configured tracker

Apply only the approved changes.

* **Local files** → write one file per new ticket under `.scratch/<feature-slug>/issues/`, numbered in dependency order. Update or retire existing files when the remediation delta requires it.
* **Real issue tracker** → create new issues in dependency order and apply requested updates or closures to existing open tickets.

For trackers supporting native parent/child and blocking relationships, use them. For GitHub, invoke `$github-issue-dependencies` for exact relationship operations rather than researching them again.

New tickets must:

* link to the same parent Spec;
* use the applicable Architecture context;
* use the shared **Ticket branch**;
* receive correct blocking relationships;
* receive `ready-for-agent` unless instructed otherwise.

Do not reopen or rewrite closed tickets to represent newly required work.

Do not close or modify the parent Spec issue.

<local-ticket-template>

# <NN> — <Ticket title>

**Root blocker:** for Spec Review remediation tickets only, `RB-<n>` and the root invariant this ticket is intended to close. Omit otherwise.

**Architecture context:** affected entities and governing ADR/doc references relevant to this ticket, or "None". Do not copy invariant text.

**What to build:** the end-to-end behaviour this ticket makes work.

**Blocked by:** ticket numbers/titles, or "None — can start immediately".

**Ticket branch:** the shared branch for this spec, normally `spec-<spec_issue_number>`, an explicitly overridden shared branch, or "None".

**Status:** ready-for-agent

* [ ] Acceptance criterion 1
* [ ] Acceptance criterion 2

</local-ticket-template>

<issue-template>

## Parent

Reference the parent Spec.

## Root blocker

For Spec Review remediation tickets only: `RB-<n>` and the root invariant this ticket is intended to close. Omit otherwise.

## Architecture context

Affected entities and governing ADR/doc references relevant to this ticket, or "None". Do not copy invariant text.

## What to build

The end-to-end behaviour this ticket makes work.

## Acceptance criteria

* [ ] Criterion 1
* [ ] Criterion 2
* [ ] For Spec Review remediation tickets: production-path proof and sibling-surface blast-radius audit for the root blocker are complete, or remaining unproven cells are explicitly reported.

## Blocked by

References to blocking tickets, or "None — can start immediately".

## Ticket branch

The shared branch for this spec, normally `spec-<spec_issue_number>`, an explicitly overridden shared branch, or "None".

</issue-template>

Avoid specific file paths or code snippets unless a prototype produced a decision-rich snippet that is materially clearer than prose.

Work the frontier one ticket at a time with `$implement-ticket`, clearing context between tickets.

## Spec Branch Rule

All tickets for a Spec — initial, Spec Review remediation, or amended-Spec delta — use the same Spec branch and baseline.

### 0. Resolve the Spec Issue Number

If the source is a `Spec Review: ` issue, recover the original Spec from its exact body line:

```text
**Parent Spec:** #<n>
```

Otherwise the source Spec issue is the Spec issue.

```bash
INPUT_ISSUE_NUMBER=<input issue number>
INPUT_ISSUE_TITLE=$(gh issue view "$INPUT_ISSUE_NUMBER" --json title -q .title)

case "$INPUT_ISSUE_TITLE" in
  "Spec Review: "*)
    spec_issue_number=$(gh issue view "$INPUT_ISSUE_NUMBER" --json body -q .body \
      | grep -oP '(?<=\*\*Parent Spec:\*\* #)\d+')

    if [ -z "$spec_issue_number" ]; then
      echo "❌ Could not resolve the parent Spec issue. Halting."
      exit 1
    fi
    ;;
  *)
    spec_issue_number="$INPUT_ISSUE_NUMBER"
    ;;
esac
```

### 1. Resolve Branch Identity

```bash
SPEC_BRANCH="spec-$spec_issue_number"
```

### 2. Capture Baseline for First Use

```bash
BASELINE_COMMIT=$(git rev-parse main)
```

This value is used only if the Spec branch does not already exist.

### 3. Create or Reuse the Spec Branch

```bash
if git show-ref --verify --quiet "refs/heads/$SPEC_BRANCH"; then
  git checkout "$SPEC_BRANCH"
else
  git checkout -b "$SPEC_BRANCH" "$BASELINE_COMMIT"
fi
```

Do not create another branch for remediation or amended-Spec ticket deltas.

Ensure unrelated uncommitted work is not carried across the checkout.

### 4. Record Baseline Metadata Once

Record the baseline on the parent Spec issue only if it has not already been recorded:

```bash
ALREADY_POSTED=$(gh issue view "$spec_issue_number" --json comments -q '.comments[].body' \
  | grep -c "## Workspace Metadata" || true)

if [ "$ALREADY_POSTED" -eq 0 ]; then
  gh issue comment "$spec_issue_number" --body "$(printf \
'## Workspace Metadata\n**Baseline Commit Hash:** %s\n**Branch:** %s\n' \
"$BASELINE_COMMIT" "$SPEC_BRANCH")"
fi
```

Never overwrite the Spec body to store workspace metadata.

The original baseline remains the fixed point for the entire Spec lifecycle.
