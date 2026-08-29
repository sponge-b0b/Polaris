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

If the Spec still contains an unresolved material architecture question, halt with a Human Handoff. Do not resolve architecture here.

> ⚠️ **Ticket creation is blocked by unresolved architecture.**
>
> Please run:
>
> ```
> $to-specs - <Spec Title> (<Spec URL>)
> ```

Use the actual Spec title and URL.

A Blocking Architecture finding in a Spec Review issue is not itself unresolved architecture. `$to-remediation-tickets` owns that routing.

#### Project Delivery Actionability Guard

Before ticket drafting, remediation reconciliation, branch setup, or any tracker/repository mutation for a Wayfinder-managed Spec, prove that the underlying Spec is currently in the actionable Spec frontier.

If the invocation source is a `Spec Review: ` issue, first recover its exact `**Parent Spec:** #<n>` and apply this guard to that Spec. Otherwise use the source Spec itself.

A Spec is **Wayfinder-managed** when durable provenance/handoff evidence identifies one or more governing Wayfinders through:

* its canonical `wayfinder-source` marker;
* one or more `wayfinder-remediation` markers; or
* an unambiguous matching `Derived Spec` / `Remediation Spec` entry on a canonical Wayfinder map.

Do not invent a governing Wayfinder. An intentionally non-Wayfinder Spec continues through the existing lifecycle and is not enrolled into project focus merely because `$to-tickets` was invoked.

For a Wayfinder-managed Spec:

1. require the Spec issue to be open;
2. read its complete native `blocked by` relationship set and fail closed if blocker data is truncated/unreadable;
3. if any direct blocker is open, stop before substantive work and report the Spec as dependency-blocked;
4. recover every currently governing Wayfinder from durable provenance/handoff evidence; ambiguity in governance fails closed and routes back to `$to-specs` for reconciliation rather than guessing;
5. invoke `$project-delivery-management` `reconcile`;
6. invoke `$project-delivery-management` `guard <Wayfinder>` for each governing Wayfinder;
7. require at least one governing Wayfinder to return `PROJECT DELIVERY GUARD: ALLOWED`.

If no governing Wayfinder is allowed, stop before substantive work. Surface the exact governing maps, their guard results, current focus, and the explicit human `$project-delivery-management` focus/switch/parallel choices. `$to-tickets` must never establish, switch, or broaden focus itself.

A closed blocker satisfies the Spec dependency only because its authoritative Spec lifecycle is complete. Ticket completion, verification readiness, review passage, `Ready to Merge`, Priority, Project fields, issue order, or handoff order do not satisfy the dependency. If a blocker Spec is reopened, the unchanged native edge makes this guard fail again automatically.

Passing this guard does not create an active-Spec scheduler. Multiple independent open/unblocked Specs governed by the same focused Wayfinder may each be ticketed in separate sessions.

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

If `$to-remediation-tickets` returns one or more **architecture-blocked roots**, halt with a Human Handoff to the parent Spec review lifecycle:

> ⚠️ **Ticket remediation is blocked by unresolved architecture.**
>
> Please run:
>
> ```
> $review-spec - <Parent Spec Title> (<Spec URL>)
> ```
>
> **Architecture blockers:**
>
> 1. **RB-<n> — <question/conflict>**
>    * Governing authority: <authority>
>    * Evidence: <concise evidence>
>    * Material consequence: <ownership/path/boundary/dependency/lifecycle/conflict>

Use the actual parent Spec title and URL. Do not continue ordinary ticket remediation while an architecture-blocked root remains.

If it returns a delta, treat each returned ticket block as the authoritative semantic input for Step 4. You may improve presentation, but do not condense, reclassify, merge, or omit any returned remediation, verification, preservation, root-complete sweep, dependency, or metadata obligation.

Do not discard or collapse Root Blocker preservation obligations merely because they require no new implementation.

If it returns an empty delta, report that the current ticket set already represents the source, identify the applicable open/frontier ticket, and halt with a Human Handoff:

> ✅ **No ticket changes are required.**
>
> Please continue with:
>
> ```
> $implement-ticket - <Frontier Ticket Title> (<Ticket URL>)
> ```

If multiple frontier tickets are available, present one copy-ready `$implement-ticket` line per ticket and let the user choose.

Then stop.

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

For Spec Review remediation tickets, present a **publication-ready proposal**. For each ticket show:

* **Title**;
* **Root Blocker**;
* **Blocked by**;
* **Remediation obligations / What it delivers**;
* **Verification obligations**;
* **Preservation obligations**;
* **Root-complete sweep required for closure**;
* **Ticket branch**;
* **Ticket baseline**;
* **Required label/status**.

Use `None` where a category has no obligations. Do not summarize away, merge, reclassify, or omit any obligation returned by `$to-remediation-tickets`. The proposal must contain everything needed to publish the ticket correctly without additional semantic interpretation after approval.

For remediation, also show any:

* open tickets to update;
* open tickets to close as superseded;
* dependency changes.

Before requesting approval for Spec Review remediation, verify:

* every unresolved Root Blocker returned by `$to-remediation-tickets` has the required ticket coverage;
* every remediation obligation appears in the proposed ticket;
* every verification obligation is explicitly identified as verification rather than implementation;
* every applicable satisfied same-root cell appears under Preservation obligations;
* the root-complete sweep is explicit;
* blocking edges and dependency changes match the returned delta;
* no closed ticket is being reopened or rewritten;
* `Ticket branch`, `Ticket baseline`, and required label/status are shown;
* architecture-blocked roots, if any, halted ordinary publication instead of appearing as ordinary tickets.

If any check fails, correct the proposal before presenting it to the user. Do not rely on the user to discover omissions or repair the remediation contract during approval.

For any delta that is not metadata-only deterministic normalization, ask:

* Does the granularity feel right?
* Are the blocking edges correct?
* Should anything be merged, split, or adjusted?

Iterate until approved.

An unqualified `yes`, `approved`, or equivalent approves the proposal exactly as presented.

After approval, do not add, remove, merge, split, reinterpret, or reclassify ticket semantics. If a semantic defect is discovered during publishing, return to Step 4 for approval instead of silently repairing it.

### Pre-Publication Spec Branch Guard

After approval and before any mutation in Step 5, execute the complete **Spec Branch Rule** below through Step 4. Treat that rule as a hard precondition to publication even though its procedure is documented later in this file.

Do not create, update, close, label, parent, or change dependencies for any ticket until branch identity, local/remote branch state, upstream tracking, GitHub Development linkage, and Spec baseline metadata have all been verified or persisted as required by that rule.

If any Spec Branch Rule check fails, halt before Step 5 with zero ticket-publication mutations. Do not weaken, bypass, or defer the guard merely because an existing branch is otherwise usable.

After the guard succeeds, continue to Step 5. Do not execute branch setup a second time in the same uninterrupted invocation; reuse the verified branch/baseline state.

### 5. Publish to the Configured Tracker

Apply only the approved changes, or deterministic metadata-only normalization authorized by Step 4.

* **Local files** → create new ticket files and update or retire existing ones as required.
* **Real issue tracker** → create new issues and apply approved updates or closures to existing open tickets.

Use native parent/child and blocking relationships where supported. For GitHub, invoke `$github-issue-dependencies` for relationship operations.

The native parent is the artifact **directly decomposed by this `$to-tickets` invocation**:

* ordinary Spec ticketing → the Spec is the native parent of its Implementation Tickets;
* Spec Review remediation → the Spec Review is the native parent of its Review Remediation Tickets.

Do not use transitive provenance as native hierarchy. In particular, the originating Spec remains the branch/baseline and lifecycle provenance owner for remediation, but it is **not** the native parent of tickets created from a Spec Review. A Spec Review is likewise lifecycle provenance for the Spec, not an implementation child of the Spec.

New tickets must:

* record lineage according to ticket mode:
  * ordinary Spec ticket → `Parent Spec: #<spec_issue_number>`;
  * Spec Review remediation ticket → `Remediation parent: Spec Review #<review_issue_number>` and `Parent Spec: #<spec_issue_number>`;
* use the direct decomposition artifact above as the native GitHub parent;
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

For an ordinary Implementation Ticket:

```text
Parent Spec: #<spec_issue_number>
```

For a Review Remediation Ticket:

```text
Remediation parent: Spec Review #<review_issue_number>
Parent Spec: #<spec_issue_number>
```

The first line identifies immediate decomposition ownership. `Parent Spec` on a remediation ticket is transitive lifecycle provenance and branch/baseline ownership only; do not use it as the native GitHub parent.

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

The **Pre-Publication Spec Branch Guard** executes this complete section before Step 5. When this section is reached later in document order during the same uninterrupted invocation, reuse the already verified branch/baseline state rather than rerunning setup. On a resumed invocation, re-run the guard before any new Step 5 mutation.

All tickets for a Spec — initial, Spec Review remediation, or amended-Spec delta — use the same Spec branch and fixed Spec baseline.

Each ticket has its own `Ticket baseline`.

The Spec branch is a durable GitHub development branch, not a local-only workspace convenience. On first use, `$to-tickets` owns creating it on `origin`, linking it to the originating Spec's GitHub Development section, and establishing the local upstream. Later ticketing/remediation reuses that same linked branch.

The originating Spec's branch/baseline ownership does not make it the native parent of Spec Review remediation tickets. Native hierarchy follows direct decomposition ownership from Step 5.

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

### 3. Create or Reuse the Linked Spec Branch

Require a clean worktree before branch setup. Do not carry unrelated work across this checkout.

Determine local and remote branch existence once:

```bash
LOCAL_BRANCH_EXISTS=false
REMOTE_BRANCH_EXISTS=false

git show-ref --verify --quiet "refs/heads/$SPEC_BRANCH" \
  && LOCAL_BRANCH_EXISTS=true

git ls-remote --exit-code --heads origin "$SPEC_BRANCH" >/dev/null 2>&1 \
  && REMOTE_BRANCH_EXISTS=true
```

On first use, neither branch exists. Require local `main` to match `origin/main`, then create the remote branch through GitHub's issue-development boundary so branch creation and Spec linkage happen together:

```bash
if [ "$LOCAL_BRANCH_EXISTS" = false ] && [ "$REMOTE_BRANCH_EXISTS" = false ]; then
  git fetch origin main
  REMOTE_MAIN=$(git rev-parse origin/main)

  if [ "$BASELINE_COMMIT" != "$REMOTE_MAIN" ]; then
    echo "❌ Local main does not match origin/main. Synchronize main before creating the Spec branch."
    exit 1
  fi

  gh issue develop "$spec_issue_number" \
    --name "$SPEC_BRANCH" \
    --base main \
    --checkout

  git push -u origin "$SPEC_BRANCH"
elif [ "$LOCAL_BRANCH_EXISTS" = true ] && [ "$REMOTE_BRANCH_EXISTS" = true ]; then
  git checkout "$SPEC_BRANCH"
  git branch --set-upstream-to="origin/$SPEC_BRANCH" "$SPEC_BRANCH"
elif [ "$LOCAL_BRANCH_EXISTS" = false ] && [ "$REMOTE_BRANCH_EXISTS" = true ]; then
  git fetch origin "$SPEC_BRANCH"
  git checkout -b "$SPEC_BRANCH" --track "origin/$SPEC_BRANCH"
else
  echo "❌ Local Spec branch exists without its required remote linked branch. Reconcile branch publication/linkage before continuing."
  exit 1
fi
```

Do not create another branch for remediation or amended-Spec ticket deltas. Do not silently fall back to a local-only branch if `gh issue develop`, the remote push, or Development linkage is unavailable.

Verify branch identity, upstream, and GitHub Development linkage before continuing:

```bash
if [ "$(git branch --show-current)" != "$SPEC_BRANCH" ]; then
  echo "❌ Expected Spec branch $SPEC_BRANCH is not checked out."
  exit 1
fi

if [ "$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null)" != "origin/$SPEC_BRANCH" ]; then
  echo "❌ Spec branch is not tracking origin/$SPEC_BRANCH."
  exit 1
fi

if ! gh issue develop --list "$spec_issue_number" | grep -Fq "$SPEC_BRANCH"; then
  echo "❌ Spec branch is not linked to the parent Spec's GitHub Development section."
  exit 1
fi

if [ "$LOCAL_BRANCH_EXISTS" = false ] && [ "$REMOTE_BRANCH_EXISTS" = false ] \
  && [ "$(git rev-parse HEAD)" != "$BASELINE_COMMIT" ]; then
  echo "❌ Newly created Spec branch does not match the captured Spec baseline."
  exit 1
fi
```

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

## Mandatory Project Reconciliation

After ticket publication/reconciliation and Spec branch metadata are durable, derive the complete ticket frontier and invoke `$project-tracking` as prescribed internal composition **before** the Implementation Human Handoff.

Use one post-transition reconciliation set:

* ordinary ticketing parent Spec → base `Spec / Ready to Implement / None / Ready`;
* Spec Review remediation parent Spec Review → base `Spec Review / Review Remediation / None / Ready` once executable remediation-ticket children exist; before such children exist its route remains `$to-tickets`;
* the originating parent Spec in remediation remains `Spec / Review Remediation / None / Ready` when that lifecycle state is already established, and must be included when this invocation changes or re-establishes it;
* every open frontier Implementation Ticket or Review Remediation Ticket with zero open native blockers → base `Ready to Implement / $implement-ticket / Ready` for its artifact type;
* every open ticket with one or more open native blockers → base `Blocked / None / Blocked` for its artifact type;
* every updated/superseded formal ticket or other formal artifact whose lifecycle state or open-blocker set changed during this invocation.

For Review Remediation Tickets, supply the durable `Root Blocker` value. For all non-complete artifacts, `Completed On = None`.

Supply current Project Delivery State separately from these base lifecycle values. Preserve `Area` and `Priority` unless this invocation has separate authority to change them.

`$to-tickets` owns the affected-artifact set, blocker/frontier reads, and base states. `$project-tracking` owns only projection validation, delivery overlay, and Project mutation.

If Project synchronization fails, report `PROJECT TRACKING: DRIFT`. Do not roll back durable ticket/branch state and do not suppress an otherwise-authorized `$implement-ticket` handoff.

## Implementation Human Handoff

After ticket publication/reconciliation, Spec branch metadata, and mandatory Project reconciliation are complete, identify every open, unblocked frontier ticket for the Spec.

If one frontier ticket is available, halt with:

> ✅ **Tickets are ready for implementation.**
>
> Please run:
>
> ```
> $implement-ticket - <Frontier Ticket Title> (<Ticket URL>)
> ```

If multiple frontier tickets are available, output one copy-ready `$implement-ticket` line per ticket and let the user choose which fresh implementation session to start.

Do not invoke `$implement-ticket` implicitly.
