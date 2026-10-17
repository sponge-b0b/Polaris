---
name: project-delivery-management
description: Coordinate project-level delivery across current Polaris Wayfinder efforts by owning durable focus, exact parallel-focus authorization, cross-Wayfinder dependency placement, and fail-closed delivery guards.
compatibility: product=codex product=claude-code system=gh network=required
disable-model-invocation: true
---

# Project Delivery Management

Coordinate delivery across independent Wayfinder efforts without replacing lifecycle owners.

This skill owns only:

* the current focused Wayfinder set;
* exact human authorization for parallel focus;
* current Wayfinder-frontier derivation;
* cross-Wayfinder dependency placement/removal;
* deterministic reconciliation after authoritative lifecycle changes;
* delivery guards for Wayfinder-managed work.

It does not own semantic decisions, Specs, tickets, implementation, verification, review,
Project projection, or same-lineage dependencies.

## Session independence

Recover every correctness-critical input from the explicit invocation and durable tracker
state. Conversation state, Project fields, priority, issue ordering, branch activity, and
recent activity are never delivery authority.

## Canonical control artifact

Require exactly one open GitHub issue labeled exactly:

```text
project-delivery:management
```

Discover the singleton by GitHub label metadata across open and closed issues. The label is
the discovery key; issue title/body text is not. Use a label-filtered issue listing/API path
with complete pagination, then verify exact label membership on every returned issue.

Do **not** use GitHub search syntax, body/title matching, Project fields, remembered issue
numbers, or a previously observed singleton as a substitute for canonical discovery. In
particular, do not run ad hoc queries such as `gh search issues ... in:body` to locate the
control artifact. If the available client path cannot prove complete label-filtered
pagination, return invalid control state and fail closed rather than trying another
heuristic discovery method.

Zero, multiple, or closed matching issues are invalid current repository state and fail
closed. Creation or repair of the control artifact is repository administration outside
this runtime skill.

The singleton body contains exactly one current-state block:

```markdown
## Current Delivery State

**Focused Wayfinders:** None
**Parallel authorization:** None
```

`Focused Wayfinders` is `None` or issue references sorted by issue number. `Parallel
authorization` is `None` for cardinality 0..1 and otherwise the URL of the exact durable
human authorization comment for that focused set.

Do not persist frontier, queue order, blocked state, priority, lifecycle stage, Project
fields, or dependency registries in the singleton.

## Invocation boundary

### Human operations

Only an explicit human invocation may make a discretionary focus choice:

```text
focus <Wayfinder>
switch-focus <Wayfinder>
parallel-focus <Wayfinder>...
status
reconcile
```

Every focus-changing operation names exact Wayfinder issue numbers or URLs.

### Internal composition

A lifecycle owner may invoke:

```text
guard <Wayfinder>
dependency ensure <consumer> blocked-by <blocker>
dependency remove <consumer> blocked-by <blocker>
reconcile
```

Internal composition may never establish focus from empty state, switch focus, add a map to
parallel focus, broaden parallel authorization, or invent a dependency.

Deterministic removal of completed or directly ineligible focused maps is reconciliation,
not a discretionary focus choice.

### Caller boundary

Lifecycle callers consume this skill's result; they do not reproduce its control-state or
guard algorithm inline. Singleton discovery, focus validation, Wayfinder-frontier
derivation, and guard classification belong to `$project-delivery-management` while the
invocation is active.

A caller must not compensate for a failed invocation by performing independent `gh search`,
body/title matching, Project queries, or remembered-state checks and then declaring an
ALLOWED result itself. A failed, incomplete, or ambiguous invocation is a blocked guard.

## Canonical Wayfinder frontier

Discover current open `wayfinder:map` issues and read each complete native `blocked by`
relationship set. Truncated blocker data fails closed.

A map is frontier-eligible exactly when it is open and has zero open direct native map
blockers. Lower-level Spec/ticket blockers do not remove a map from the project-level
frontier.

Never derive frontier membership from Project fields, priority, issue order, assignees,
branch state, recency, or activity.

## Validate current focus

Parse the singleton and require:

* every focused issue is a current canonical Wayfinder map;
* every focused map is frontier-eligible;
* cardinality greater than one has one exact matching parallel authorization comment;
* cardinality zero or one has `Parallel authorization: None`.

Invalid current focus fails closed before any substantive guard or focus mutation.

## Human focus operations

Before changing current focus, append:

```markdown
## Project Delivery Focus Authorization

**Operation:** focus | switch-focus | parallel-focus
**Focused Wayfinders:** #<n>[, #<n>...]
**Authorization source:** explicit human invocation
```

If that comment cannot be persisted, do not mutate the singleton.

Rules:

* `focus` requires current focus empty and target frontier-eligible;
* `switch-focus` requires target frontier-eligible and replaces the current set;
* `parallel-focus` requires every exact target frontier-eligible and records that exact set;
* no operation infers a target from ordering, priority, Project fields, or recommendation.

After mutation, re-read the singleton and require exact intended state.

## Guard

`guard <Wayfinder>` requires:

1. a valid canonical singleton/current focus;
2. target is a current canonical Wayfinder map;
3. complete direct blocker state is readable;
4. target is frontier-eligible;
5. target belongs to the current focused set.

Return exactly:

```text
PROJECT DELIVERY GUARD: ALLOWED
Wayfinder: #<n>
Focused set: <exact set>
```

or:

```text
PROJECT DELIVERY GUARD: BLOCKED
Wayfinder: #<n>
Reason: <not frontier-eligible | not focused | invalid control state | unreadable blockers>
```

A blocked guard never changes focus.

## Cross-Wayfinder dependencies

A cross-Wayfinder dependency is an exact semantic prerequisite between artifacts governed
by different Wayfinder lineages. Native GitHub `blocked by` relationships are durable
dependency truth; this skill owns only the semantic placement decision for cross-lineage
edges and delegates mechanics to `$github-issue-dependencies`.

### Recover lineage

Resolve each endpoint to its exact governing Wayfinder from durable tracker provenance:

* map -> itself;
* decision -> native Wayfinder parent;
* Spec -> current Wayfinder source/remediation governance applicable to the relationship;
* implementation/review artifact -> parent lineage.

Ambiguous lineage fails closed. Same-lineage relationships return to the owning lifecycle
rather than being mutated here.

### Lowest accurate boundary

For `dependency ensure`, require durable semantic evidence for the exact prerequisite and
choose the narrowest authoritative consumer/blocker pair whose completion boundary makes
the prerequisite true.

Ask:

1. does completion of this blocker fully satisfy this prerequisite?
2. is there a narrower authoritative endpoint that avoids blocking unrelated work?

An unresolved answer returns `AMBIGUOUS DEPENDENCY PLACEMENT` without mutation.

Wayfinder -> Wayfinder is valid only when the downstream destination as a whole cannot
advance safely until the upstream Wayfinder is complete and no narrower edge is sufficient.

### Cycle guard

Before adding `consumer blocked-by blocker`:

* reject self-dependency;
* traverse the complete native blocker graph reachable from the proposed blocker;
* fail closed on unreadable/truncated graph data;
* reject when the consumer is reachable from the blocker.

### Ensure/remove

`dependency ensure` re-reads the current edge immediately before mutation, treats an exact
existing edge as idempotent success, delegates one exact add to
`$github-issue-dependencies`, verifies it, then runs deterministic focus reconciliation.

`dependency remove` requires durable authority that the prerequisite no longer applies or
was established in error. Closed blocker state alone is not removal authority. Re-read the
edge, treat absence as idempotent success, delegate one exact removal, verify it, then run
focus reconciliation.

A newly added map-level blocker may force a focused map out of focus. Report that release
and valid explicit human focus choices; never auto-select a replacement.

## Reconcile

`reconcile` applies only consequences forced by current canonical state:

* remove closed Wayfinders from focus;
* remove focused Wayfinders with an open direct map blocker;
* preserve still-open frontier-eligible focused maps;
* if the resulting set has cardinality 0..1, clear parallel authorization;
* if cardinality remains >1, require the existing authorization to match the exact set.

Reconciliation never adds focus, chooses a replacement, or changes dependencies merely to
preserve focus.

Re-read and verify the singleton after mutation.

## Deferred Project projection

This skill never invokes `$project-tracking` as a side effect. Project projection occurs
only at the permanent authorized boundaries defined by `$project-tracking`: completed-Spec
reconstruction or an explicit human board-refresh request.

Project lag never changes focus, dependency truth, frontier eligibility, or lifecycle
authorization.

## Results

Human/status operations report the exact focused set and frontier. Dependency failures use:

```text
PROJECT DELIVERY DEPENDENCY: INVALID
Consumer: <issue>
Blocker: <issue>
Reason: <cycle | ambiguous placement | ambiguous lineage | unsupported inference | incomplete graph | mutation/verification failure>
```

Do not compensate for a failure by rewriting another dependency, hierarchy, focus state, or
Project projection.

## Non-goals

`$project-delivery-management` does not create/repair its control artifact, choose semantic
requirements, create lifecycle artifacts, execute delivery work, maintain a duplicate
Wayfinder registry, persist a queue, infer focus from Project state, or provision Project
schema.
