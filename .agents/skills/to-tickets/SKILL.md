---
name: to-tickets
description: Break an explicit plan, spec, review, or other invocation source into tracer-bullet tickets, each declaring its blocking edges, and publish them to the configured tracker.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Tickets

Break an explicit plan, spec, review, or other invocation source into **tickets** — tracer-bullet vertical slices, each declaring the tickets that **block** it.

The issue tracker and triage label vocabulary should have been provided — run `$setup-matt-pocock-skills` if not.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting.

Prior-session summaries or remembered conclusions are routing context only.

If required durable state cannot be recovered, report the missing artifact rather than infer or recreate it.

## Process

### 1. Gather Context

Work from the explicit invocation source and recover its durable tracker/repository state.

If the user passes a spec path, issue number, or URL, fetch and read its full body and comments.

If the source is a Spec, use its **Architecture Impact** as routing context. Carry forward only the affected entities and governing ADR/doc references relevant to each ticket.

If the Spec still contains an unresolved material architecture question, stop and return to `$to-specs`. Do not resolve architecture here.

A Blocking Architecture finding in a Spec Review issue is not itself unresolved architecture. `$to-remediation-tickets` owns that routing.

### 2. Explore the Codebase

If needed, inspect the current codebase before slicing.

Use project domain vocabulary and respect applicable ADRs.

Look for useful prefactoring: make the change easy, then make the easy change.

### 3. Resolve Ticket Mode

Before drafting:

* source title prefixed `Spec Review: ` → invoke `$to-remediation-tickets`;
* existing Spec with linked implementation tickets → invoke `$to-remediation-tickets`;
* otherwise → fresh vertical-slice drafting.

`$to-remediation-tickets` owns:

* remediation delta analysis;
* duplicate prevention;
* open-ticket updates;
* superseded-ticket detection;
* Root Blocker reconciliation;
* remediation, verification, and preservation obligations;
* determining which new tickets are required.

If it returns a delta, preserve that delta semantically and continue at Step 4.

Do not discard or collapse Root Blocker preservation obligations merely because they require no new implementation.

If it returns an empty delta, report that the current ticket set already represents the source and direct the user to resume the applicable open/frontier ticket with `$implement-ticket`. Then stop.

#### Fresh Vertical Slices

Break the work into **tracer-bullet** tickets.

<vertical-slice-rules>

* Each slice cuts a narrow but complete path through the required layers.
* A completed slice is independently demoable or verifiable.
* Each slice fits in one fresh context window.
* Necessary prefactoring comes first.

</vertical-slice-rules>

Give each ticket its **blocking edges**.

**Wide refactors are the exception.** When one mechanical change fans across the codebase and individual vertical slices cannot stay green, use expand–contract: expand first, migrate callers in manageable batches, then contract after all migrations complete.

### 4. Quiz the User

Present the proposed fresh breakdown or remediation delta.

If the delta contains **only deterministic required ticket-metadata normalization** and does not change ticket scope, acceptance criteria, preservation obligations, blocking edges, dependencies, labels, or lifecycle state, skip user approval and continue directly to Step 5.

For new tickets, show:

* **Title**
* **Blocked by**
* **What it delivers**

For Spec Review remediation tickets, also summarize:

* Root Blocker;
* remediation obligations;
* verification obligations when applicable;
* preservation obligations;
* root-complete sweep required for closure.

For remediation, also show any:

* open tickets to update;
* open tickets to close as superseded;
* dependency changes.

For any delta that is not metadata-only deterministic normalization, ask:

* Does the granularity feel right?
* Are the blocking edges correct?
* Should anything be merged, split, or adjusted?

Iterate until approved.

### 5. Publish to the Configured Tracker

Apply only the approved changes, or deterministic metadata-only normalization authorized by Step 4.

* **Local files** → create new ticket files and update or retire existing ones as required.
* **Real issue tracker** → create new issues and apply approved updates or closures to existing open tickets.

Use native parent/child and blocking relationships where supported. For GitHub, invoke `$github-issue-dependencies` for relationship operations.

New tickets must:

* link to the same parent Spec;
* carry applicable Architecture context;
* use the shared **Ticket branch**;
* declare **Ticket baseline** as `Pending`;
* receive correct blocking relationships;
* receive `ready-for-agent` unless instructed otherwise.

For Spec Review remediation, publish the Root Blocker contract returned by `$to-remediation-tickets` without weakening it:

* open/regressed implementation obligations → acceptance criteria;
* verification-only obligations → explicit verification criteria when applicable;
* satisfied same-root cells → preservation obligations;
* root-complete invariant sweep → closure criterion.

Do not convert preservation obligations into new implementation requirements.

Do not omit them because prior tickets are closed or the cells are currently satisfied.

When updating an existing open ticket, preserve valid execution metadata and add `Ticket baseline: Pending` when the field is missing. Never replace an existing pinned baseline SHA.

Do not reopen or rewrite closed tickets to represent newly required work.

Do not close or modify the parent Spec issue.

### Architecture Readiness Language

Scope ticket readiness claims to what the current Spec, review state, and accepted decisions actually establish.

When architecture dependencies for a ticket are resolved, prefer language such as:

> All architecture decisions currently required by this ticket are accepted; no known architecture blocker remains unresolved.

Do not write absolute claims such as:

* `no architecture decision remains unresolved`;
* `architecture is fully resolved`;
* `all architecture is settled`;
* equivalent language implying implementation cannot expose another material blocker.

Ticket readiness means **no known architecture blocker currently prevents this ticket from starting**.

It does not waive `$implement-ticket`'s obligation to halt on a newly discovered material architecture blocker.

More generally, state only what the workflow has established. Do not turn current evidence into broader or final claims.

<local-ticket-template>

# <NN> — <Ticket title>

**Root blocker:** for Spec Review remediation tickets only, `RB-<n>` and the stable root invariant this ticket closes. Omit otherwise.

**Architecture context:** affected entities and governing ADR/doc references relevant to this ticket, or "None". Do not copy invariant text. Scope any readiness statement according to **Architecture Readiness Language**.

**What to build:** the end-to-end behaviour this ticket makes work.

**Blocked by:** ticket numbers/titles, or "None — can start immediately".

**Ticket branch:** the shared branch for this Spec, normally `spec-<spec_issue_number>`, an explicitly overridden shared branch, or "None".

**Ticket baseline:** Pending

**Status:** ready-for-agent

* [ ] Acceptance criterion 1
* [ ] Acceptance criterion 2
* [ ] For Spec Review remediation: the required production-path, negative/fail-closed, and root-complete invariant proof is established.

**Preservation obligations:** for Spec Review remediation only, list the satisfied same-root acceptance obligations that must remain satisfied while this ticket changes shared root surfaces. Omit otherwise.

</local-ticket-template>

<issue-template>

## Parent

Reference the parent Spec.

## Root blocker

For Spec Review remediation tickets only: `RB-<n>` and the stable root invariant this ticket closes. Omit otherwise.

## Architecture context

Affected entities and governing ADR/doc references relevant to this ticket, or "None". Do not copy invariant text. Scope any readiness statement according to **Architecture Readiness Language**.

## What to build

The end-to-end behaviour this ticket makes work.

## Acceptance criteria

* [ ] Criterion 1
* [ ] Criterion 2
* [ ] For Spec Review remediation: required production-path and negative/fail-closed proof is complete, and the root-complete invariant sweep establishes every active non-satisfied obligation or explicitly reports remaining `unproven` verification work.

## Preservation obligations

For Spec Review remediation only, list the currently satisfied same-root acceptance obligations returned by `$to-remediation-tickets` that must remain satisfied.

These are not new implementation work. They define established behavior that remediation must not regress.

Omit this section for ordinary tickets.

## Blocked by

References to blocking tickets, or "None — can start immediately".

## Ticket branch

The shared branch for this Spec, normally `spec-<spec_issue_number>`, an explicitly overridden shared branch, or "None".

## Ticket baseline

Pending

</issue-template>

Avoid specific file paths or code snippets unless a prototype produced a decision-rich snippet materially clearer than prose.

For Spec Review remediation, semantic Root Blocker surface/reference families and acceptance obligations are durable ticket context and should be preserved even when concrete implementation files may change.

### Ticket Baseline

`Ticket baseline` is a per-ticket verification anchor, not the Spec baseline.

Publish every new ticket with `Ticket baseline: Pending`.

`$implement-ticket` replaces `Pending` exactly once with the full current `HEAD` before the ticket's first file mutation, then reuses that persisted SHA across resumed sessions.

Never initialize a ticket baseline from the fixed Spec baseline or another ticket's baseline.

Work the frontier one ticket at a time with `$implement-ticket`, clearing context between tickets.

## Spec Branch Rule

All tickets for a Spec — initial, Spec Review remediation, or amended-Spec delta — use the same Spec branch and fixed Spec baseline.

Each ticket has its own `Ticket baseline`.

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

### 2. Capture Spec Baseline for First Use

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

### 4. Record Spec Baseline Metadata Once

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