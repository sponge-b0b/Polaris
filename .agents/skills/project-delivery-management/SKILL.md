---
name: project-delivery-management
description: Coordinate project-level delivery across Polaris Wayfinder efforts by owning durable focus and exact parallel-focus authorization, deriving the Wayfinder frontier from canonical tracker state, and providing fail-closed guard/reconciliation operations without becoming a delivery executor or GitHub Project authority.
compatibility: product=codex product=claude-code system=gh network=required
disable-model-invocation: true
---

# Project Delivery Management

Coordinate delivery **at the Polaris project level** across independent Wayfinder efforts.

This skill owns the project-level delivery control state that cannot be derived elsewhere. It does not own Wayfinder decisions, Specs, tickets, implementation, verification, review, merge work, or GitHub Project truth.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from explicit invocation arguments and durable GitHub tracker state. Prior-session summaries or remembered conclusions are routing context only.

Never derive delivery truth from GitHub Project fields, Priority, issue age/order, assignees, branch activity, recent activity, or conversation state.

## Invocation Boundary

`$project-delivery-management` supports two invocation modes.

### Human Management Operations

Only an explicit human invocation may make a discretionary focus choice:

* `focus <Wayfinder>` — establish focus when none exists;
* `switch-focus <Wayfinder>` — replace the current focused set with one eligible Wayfinder;
* `parallel-focus <Wayfinder>...` — authorize the exact eligible Wayfinder set for parallel delivery;
* `status` — inspect canonical project-delivery state without mutation;
* `reconcile` — apply only deterministic consequences already forced by canonical state.

Every focus-changing operation must identify exact Wayfinder issue numbers or URLs.

Do not infer a focus change from an invocation of `$wayfinder`, `$to-specs`, `$implement-ticket`, or another lifecycle owner.

### Internal Composition

An already-authorized lifecycle owner may invoke this skill internally for:

* `guard <Wayfinder>` — determine whether substantive work on that exact Wayfinder delivery scope is currently authorized;
* `reconcile` — reduce canonical tracker state after an authoritative transition already succeeded.

Internal composition may never:

* establish focus from an empty set;
* switch focus;
* add a Wayfinder to parallel focus;
* broaden an existing parallel authorization.

Deterministic removal of completed or directly ineligible focused Wayfinders is reconciliation, not a discretionary focus choice.

## Authority Model

Keep each fact at its lowest authoritative owner.

| Concern | Authority |
| --- | --- |
| Wayfinder identity, destination, decisions, handoffs | individual Wayfinder artifacts |
| Wayfinder membership | canonical `wayfinder:map` issues |
| direct dependency truth | native GitHub `blocked by` relationships |
| focused Wayfinder set | Project Delivery Management singleton |
| exact parallel-focus authorization | Project Delivery Management singleton + authorization comment |
| frontier / eligible / queued / blocked classification | derived here |
| GitHub Project fields | downstream projection only |

Do not maintain a duplicate registry of Wayfinder maps or a persisted frontier/queue.

Cross-Wayfinder dependency semantics and mutation are added by the dedicated downstream implementation ticket. Until then, this skill consumes the native relationships that already exist; it does not invent or rewrite them.

## Canonical Singleton

The durable control artifact is exactly one long-lived GitHub issue carrying the label:

```text
project-delivery:management
```

The label is the canonical discovery key. The title `Project Delivery Management` is presentation, not identity.

The singleton:

* is not a `wayfinder:map`;
* is not the native parent of Wayfinder maps;
* must not carry `workflow:tracked`;
* is not workflow truth because of any GitHub Project membership.

Bootstrap/migration owns creating the singleton and required label. After bootstrap, this skill fails closed if discovery returns zero or more than one matching issue.

Discover across open and closed issues so a mistakenly closed singleton cannot be bypassed by creating another:

```bash
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')

gh issue list \
  --repo "$REPO" \
  --state all \
  --label project-delivery:management \
  --limit 100 \
  --json number,title,url,state,labels,body
```

Require exactly one result and require it to be open.

### Current-State Contract

The singleton body contains exactly one current-state block:

```markdown
## Current Delivery State

**Focused Wayfinders:** None
**Parallel authorization:** None
```

Canonical focused-set representation:

* `None` for the empty set;
* otherwise issue references sorted by issue number, comma-separated: `#53, #188`.

`Parallel authorization` is:

* `None` when the focused set has cardinality `0..1`;
* the URL of the durable authorization comment when the focused set has cardinality greater than one.

Do not persist frontier, queue order, blocked state, Priority, lifecycle stage, or Project fields in this block.

Preserve historical focus decisions as issue comments rather than accumulating history in the current-state block.

### Focus Authorization Comment

Before a human focus-changing operation updates the current-state block, append:

```markdown
## Project Delivery Focus Authorization

**Operation:** focus | switch-focus | parallel-focus
**Focused Wayfinders:** #<n>[, #<n>...]
**Authorization source:** explicit human invocation
```

The GitHub comment author and timestamp provide durable attribution. For `parallel-focus`, store that comment URL in `Parallel authorization`.

If the comment cannot be persisted, do not mutate current focus.

## Recover Canonical Wayfinders

Wayfinder membership is discovered, never registered here.

```bash
gh issue list \
  --repo "$REPO" \
  --state open \
  --label wayfinder:map \
  --limit 1000 \
  --json number,title,url,state,blockedBy
```

For every returned map:

1. require `blockedBy.nodes` count to equal `blockedBy.totalCount`; otherwise fail closed because blocker data is truncated;
2. inspect blocker state from the native relationship;
3. classify the map as frontier-eligible only when it is open and has zero open direct blockers.

The **Wayfinder frontier** is exactly the set of open canonical Wayfinder maps with no open direct native blockers.

Do not consult Priority, Project fields, issue ordering, issue age, assignee state, branch state, recency, or lower-level Spec/ticket blockers when determining the map frontier.

Lower-level blockers remain lower-level.

## Validate Current Focus

Parse the singleton current-state block and validate it against canonical tracker state.

Require:

1. every focused issue is a canonical Wayfinder map;
2. every focused Wayfinder is currently in the Wayfinder frontier;
3. focused-set cardinality `0..1` has `Parallel authorization: None`;
4. focused-set cardinality `>1` has a valid authorization comment whose exact sorted Wayfinder set matches the current focused set.

If cardinality is greater than one without matching durable authorization, return invalid control state. Do not choose which Wayfinder to keep.

If current state is malformed or ambiguous, fail closed.

## Deterministic Reconciliation

`reconcile` may change focus only when canonical state forces the consequence.

1. Re-read the singleton.
2. Re-read canonical `wayfinder:map` issues and their direct blockers.
3. Derive the current Wayfinder frontier.
4. Remove from the focused set any Wayfinder that:
   * is closed; or
   * has an open direct map blocker; or
   * is no longer a canonical `wayfinder:map`.
5. Never add a replacement.
6. If a previously parallel set shrinks to one or zero, set `Parallel authorization: None`. Historical authorization remains in comments.
7. Persist the new current-state block only when its value changed.
8. Re-read and verify the exact persisted state.

A newly eligible Wayfinder never joins the focused set automatically.

### Focused-but-Stalled

Lack of lower-level actionable work does **not** remove an otherwise frontier-eligible focused Wayfinder.

When a downstream lifecycle owner has authoritatively established that a focused, map-eligible Wayfinder currently has no actionable lower-level work because narrower decision/Spec/ticket blockers remain, report:

```text
PROJECT DELIVERY: FOCUSED-BUT-STALLED
```

Retain focus and surface the lower-level blockers supplied/recovered by their owning lifecycle.

Do not promote those blockers to the map and do not silently switch or release focus.

This ticket establishes the retention rule. Later lifecycle-integration tickets own the exact lower-level frontier recovery at their respective boundaries.

## Human Focus Operations

Always re-read canonical state immediately before mutation.

### `focus <Wayfinder>`

Require:

* current focused set is empty;
* target is a canonical Wayfinder;
* target is in the current Wayfinder frontier.

If any check fails, do not mutate focus.

Persist an authorization comment, then set:

```text
Focused Wayfinders: #<target>
Parallel authorization: None
```

### `switch-focus <Wayfinder>`

Require the target is a canonical frontier-eligible Wayfinder.

This is an explicit replacement operation. The previously focused Wayfinder remains open and simply becomes eligible-but-unfocused when still in the frontier. Do not create a blocker between the two maps.

Persist an authorization comment, then replace the focused set with the target and clear current parallel authorization.

### `parallel-focus <Wayfinder>...`

Require:

* at least two distinct exact Wayfinder identities;
* every target is canonical;
* every target is currently frontier-eligible.

Do not implicitly include an existing focus that the human omitted.

Persist one authorization comment naming the exact sorted set, then set:

```text
Focused Wayfinders: #<n>, #<n>...
Parallel authorization: <authorization comment URL>
```

Later eligible maps are not members unless a new explicit `parallel-focus` invocation authorizes a new exact set.

## Internal `guard <Wayfinder>`

The caller must supply or durably resolve the exact governing Wayfinder before calling this operation.

Re-read and reconcile current state first.

Return:

```text
PROJECT DELIVERY GUARD: ALLOWED
```

only when the target is both:

* in the current Wayfinder frontier; and
* in the current focused set.

If the target has an open direct map blocker, return:

```text
PROJECT DELIVERY GUARD: BLOCKED
```

and list the open direct blockers.

If the target is frontier-eligible but not focused, return:

```text
PROJECT DELIVERY GUARD: FOCUS REQUIRED
```

and report:

* current focused Wayfinder set;
* target Wayfinder;
* allowed human management choices: establish focus when empty, switch focus, or authorize an exact parallel set.

Do not mutate focus from an internal guard.

## `status`

`status` is read-only.

Report:

* singleton identity;
* current focused Wayfinder set;
* current parallel authorization state;
* current Wayfinder frontier;
* eligible-but-unfocused Wayfinders;
* directly blocked open Wayfinders and their open direct blockers;
* invalid control-state findings, if any.

Do not order eligible-but-unfocused Wayfinders by Priority, age, number, Project position, or recency.

## Failure Semantics

Fail closed without semantic mutation when:

* the singleton is missing after bootstrap;
* more than one singleton exists;
* the singleton is closed;
* the current-state block is missing, duplicated, malformed, or references non-Wayfinder issues;
* focused-set cardinality is greater than one without matching durable parallel authorization;
* native blocker data is truncated or cannot be read;
* a requested focus target is not frontier-eligible;
* required authorization/current-state persistence cannot be verified.

Use:

```text
PROJECT DELIVERY MANAGEMENT: INVALID STATE
Reason: <exact durable-state or eligibility failure>
```

Project drift is never a reason to rewrite canonical focus or dependency state.

## Scope Boundary

This skill may:

* discover the singleton and canonical Wayfinder maps;
* derive the Wayfinder frontier from direct native blockers;
* own and persist the focused Wayfinder set;
* own and persist exact human parallel-focus authorization;
* guard map-level substantive delivery authorization;
* deterministically shrink invalid/completed focus membership;
* report canonical status and focused-but-stalled state.

This skill must not, under this ticket:

* create/bootstrap or migrate the live singleton;
* invent, add, remove, or relocate cross-Wayfinder dependency edges;
* decide same-lineage dependency semantics;
* write Wayfinder decisions, Specs, tickets, implementation, verification, review, or merge artifacts;
* derive detailed Spec/ticket frontiers;
* mutate GitHub Project schema or use Project fields as authority;
* auto-run downstream lifecycle skills;
* auto-select a successor Wayfinder.

Those responsibilities remain with existing lifecycle owners or the downstream Spec #219 tickets that explicitly implement their integration.
