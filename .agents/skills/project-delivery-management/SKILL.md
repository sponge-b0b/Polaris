---
name: project-delivery-management
description: Coordinate project-level delivery across Polaris Wayfinder efforts by owning durable focus and exact parallel-focus authorization, deriving the Wayfinder frontier from canonical tracker state, and providing fail-closed guard, cross-Wayfinder dependency, and reconciliation operations without becoming a delivery executor or GitHub Project authority.
compatibility: product=codex product=claude-code system=gh network=required
disable-model-invocation: true
---

# Project Delivery Management

Coordinate delivery **at the Polaris project level** across independent Wayfinder efforts.

This skill owns project-level delivery coordination that has no lower authoritative owner. It does not own Wayfinder decisions, Specs, tickets, implementation, verification, review, merge work, or GitHub Project truth.

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
* `dependency ensure <consumer> blocked-by <blocker>` — validate and establish an exact cross-Wayfinder semantic prerequisite;
* `dependency remove <consumer> blocked-by <blocker>` — remove an exact cross-Wayfinder prerequisite only when authoritative evidence says it no longer applies;
* `reconcile` — reduce canonical tracker state after an authoritative transition already succeeded.

Internal composition may never:

* establish focus from an empty set;
* switch focus;
* add a Wayfinder to parallel focus;
* broaden an existing parallel authorization;
* invent a dependency from prose, Project state, similarity, or architectural overlap.

Deterministic removal of completed or directly ineligible focused Wayfinders is reconciliation, not a discretionary focus choice.

If an internal operation returns a **Human Focus Handoff** defined by this skill, the caller must surface that handoff to the human unchanged in meaning. The caller must not execute the suggested focus operation implicitly or replace it with an inferred downstream lifecycle action.

## Authority Model

Keep each fact at its lowest authoritative owner.

| Concern | Authority |
| --- | --- |
| Wayfinder identity, destination, decisions, handoffs | individual Wayfinder artifacts |
| Wayfinder membership | canonical `wayfinder:map` issues |
| same-lineage dependency semantics | existing lifecycle owner for that lineage |
| cross-Wayfinder dependency semantics/writer authority | `$project-delivery-management` |
| native dependency relationship mechanics | `$github-issue-dependencies` |
| focused Wayfinder set | Project Delivery Management singleton |
| exact parallel-focus authorization | Project Delivery Management singleton + authorization comment |
| frontier / eligible / queued / blocked classification | derived here |
| GitHub Project fields | downstream projection only |

Do not maintain a duplicate registry of Wayfinder maps or a persisted dependency/frontier/queue registry.

Native GitHub `blocked by` relationships are the durable dependency truth. This skill decides and reconciles only relationships that cross Wayfinder lineages; it delegates the native relationship mutation to `$github-issue-dependencies`.

## Project Projection Synchronization

The GitHub Project is a downstream view of the canonical state owned here. Every durable focus transition must be projected after authority is already committed.

After an activated-state operation establishes, replaces, broadens, shrinks, or releases focus, invoke `$project-tracking` in **Delivery Overlay Sync** mode for every affected open Wayfinder-managed formal artifact, not only the Wayfinder Map rows.

An **affected delivery scope** is a Wayfinder whose focus membership or map-frontier eligibility changed, including:

* old and new focused maps for `focus`, `switch-focus`, and `parallel-focus`;
* focused maps removed by deterministic reconciliation;
* Wayfinder consumer/blocker maps whose map-level dependency mutation changes eligibility or focus;
* newly resumable direct Wayfinder dependents identified after a focused prerequisite completes.

For each affected delivery scope, recover its open formal artifacts from durable tracker lineage, never from Project fields:

* the canonical Wayfinder Map itself;
* open native Wayfinder Decision children;
* open Specs named by validated `Derived Spec` / `Remediation Spec` handoffs or matching durable `wayfinder-source` / `wayfinder-remediation` provenance;
* open Implementation Ticket children of those Specs;
* the open conventional Spec Review, when present, resolved by its exact parent-Spec contract;
* open Review Remediation Ticket children of that Spec Review.

Deduplicate artifacts shared by multiple governing Wayfinders. Ambiguous provenance, conflicting parentage, or multiple conventional review candidates fails Project synchronization closed; do not guess lineage to make the Project agree.

For each recovered open formal artifact, derive its current authoritative `Project Delivery State` from **all** governing Wayfinders:

* at least one governor focused and frontier-eligible → `in-focus`;
* otherwise at least one governor frontier-eligible → `eligible`;
* otherwise every governor currently map-ineligible → `blocked`.

For a Wayfinder Map, the artifact governs itself and the same mapping applies.

A focused Wayfinder with narrower stalled work remains `in-focus`; stalledness is an execution condition reported by the owning lifecycle, not a distinct project-delivery authorization state.

`$project-tracking` preserves each artifact's current projected lifecycle state and reconstructs only the base route needed to re-apply the delivery overlay. This skill must not derive or rewrite `Workflow State` merely to synchronize focus.

Projection synchronization happens **after** authoritative focus/dependency persistence and verification. A Project sync failure is `PROJECT TRACKING: DRIFT`; never roll back or rewrite canonical focus/dependency state to make the Project agree.

When a human `reconcile` is invoked explicitly, recover and synchronize every open Wayfinder-managed formal artifact under every open canonical Wayfinder in one batched `$project-tracking` invocation after canonical reconciliation, even when canonical focus did not change. This is the idempotent repair path for stale universal `Delivery State`, `Work Status`, and `Next Skill` overlay without making the Project authoritative.

## Cross-Wayfinder Dependency Reconciliation

A **cross-Wayfinder dependency** is an exact semantic prerequisite between artifacts governed by different Wayfinder lineages.

Dependency means:

> The consumer artifact may not advance until the blocker artifact completes through its own authoritative lifecycle.

The blocker artifact's lifecycle completion supplies the satisfaction boundary. Do not introduce a second dependency type such as planning-vs-delivery.

### Recover and Validate Lineage

Before deciding ownership, recover the exact governing Wayfinder for both consumer and blocker from durable tracker relationships/provenance.

Use the artifact's existing lifecycle lineage:

* Wayfinder map → itself;
* Wayfinder decision → its native Wayfinder parent;
* Spec → its durable Wayfinder source/remediation governance applicable to the requested relationship;
* implementation/review artifacts → their parent Spec/Spec Review lineage and that artifact's governing Wayfinder.

The caller may supply the expected lineage as routing context, but this skill must validate it against durable tracker evidence.

If an artifact currently has multiple plausible governing Wayfinders and the relationship context does not establish exactly one, fail closed. Do not choose a lineage heuristically.

If consumer and blocker resolve to the same Wayfinder lineage, do not mutate the edge here. Return the relationship to the existing same-lineage lifecycle owner.

### Lowest Accurate Semantic Boundary

For `dependency ensure`, require durable semantic evidence for this exact prerequisite. A title similarity, broad architectural reference, Project field, label, or prose such as “Map B depends on Map A” is candidate evidence only.

Choose the **narrowest authoritative consumer and blocker artifacts whose lifecycle boundaries make the prerequisite true**.

Normal shapes include:

* decision blocked by decision;
* Spec blocked by Spec;
* implementation ticket blocked by implementation ticket.

Same-level symmetry is not mandatory. Use a cross-level relationship when it is genuinely the narrower accurate completion boundary.

Before accepting the pair, ask both:

1. Does completion of this blocker fully satisfy the prerequisite represented by this edge?
2. Is there a narrower authoritative consumer or blocker artifact that expresses the prerequisite without blocking unrelated work?

If either answer is unresolved, fail closed with `AMBIGUOUS DEPENDENCY PLACEMENT` and do not mutate.

### Whole-Map Dependency Gate

Wayfinder → Wayfinder is valid only when **the downstream destination as a whole** cannot safely advance until the upstream Wayfinder is delivery-complete and no narrower authoritative prerequisite is sufficient.

If any legitimate portion of the downstream map can proceed independently, do not create the map-level edge. Place the prerequisite lower or reject the proposal as unresolved.

The #188/#194 relationship is the standing counterexample: broad prose says the background-ingestion worker consumes incremental-ingestion semantics, but #195 can proceed independently while #196 depends narrowly on #189/#190 and #198 depends narrowly on #193. Never translate that evidence into `#194 blocked by #188`.

### Cycle Guard

Before adding `consumer blocked-by blocker`:

1. reject consumer = blocker;
2. recover the complete native `blocked by` graph reachable from the blocker;
3. require blocker data to be complete at every visited artifact;
4. reject the edge if the consumer is reachable from the blocker.

That reachability means the new edge would create a dependency cycle.

Do not interpret an unreadable/truncated graph as acyclic. Fail closed.

### Ensure an Edge

For `dependency ensure <consumer> blocked-by <blocker>`:

1. recover/validate both lineages;
2. require they are different;
3. validate durable semantic evidence and lowest accurate placement;
4. pass the Whole-Map Dependency Gate when both artifacts are Wayfinder maps;
5. run the Cycle Guard;
6. re-read the consumer's native blockers immediately before mutation;
7. if the exact edge already exists, verify it and return idempotent success;
8. when both artifacts are Wayfinder maps, capture the current focused set before adding the edge;
9. invoke `$github-issue-dependencies` to add only that native `blocked by` relationship;
10. re-read the consumer and require the exact blocker relationship to exist;
11. run deterministic focus reconciliation because a newly added direct map blocker may invalidate current focus;
12. synchronize the affected delivery scopes through **Project Projection Synchronization**;
13. if this new open map-level blocker caused a previously focused consumer to be removed from focus, emit the **Dependency Focus Handoff** below.

Do not create parent/sub-issue hierarchy here.

#### Dependency Focus Handoff

This handoff reports a forced loss of focus; it never chooses the replacement.

If the newly established open blocker caused the consumer to leave focus, report:

```text
PROJECT DELIVERY: FOCUS RELEASED BY DEPENDENCY
Previously focused: #<consumer>
Now blocked by: #<blocker>
Current focus: <None | exact focused set>
```

Then re-read the blocker as a Wayfinder map and its complete direct blocker set.

If current focus is `None` and the blocker is frontier-eligible, append exactly:

```text
Next human action:
$project-delivery-management focus #<blocker>
```

If the blocker is not frontier-eligible, list its open direct map blockers and state that no focus command for the blocker is currently valid. Do not traverse the dependency graph to select another Wayfinder.

If another Wayfinder remains focused, report the blocker as frontier-eligible or blocked and list only the valid explicit human choices (`switch-focus` or an exact `parallel-focus` set when eligible). Do not mutate the remaining focus.

### Remove an Edge

Absence of prose or a closed blocker is not evidence that a dependency should be deleted. A closed blocker satisfies the existing edge; reopening it must make the edge blocking again.

For `dependency remove <consumer> blocked-by <blocker>` require authoritative evidence that the semantic prerequisite itself no longer applies or was established in error.

Then:

1. recover/validate both lineages and confirm this skill owns the cross-lineage relationship;
2. re-read the exact current edge;
3. if absent, return idempotent success;
4. invoke `$github-issue-dependencies` to remove only that native relationship;
5. re-read and require the relationship to be absent;
6. run deterministic focus reconciliation. Newly eligible maps are never auto-focused;
7. synchronize affected delivery scopes through **Project Projection Synchronization**.

### Dependency Failure Result

On cycle, ambiguous placement/lineage, unsupported inference, incomplete graph data, mutation failure, or post-mutation verification failure, return:

```text
PROJECT DELIVERY DEPENDENCY: INVALID
Consumer: <issue>
Blocker: <issue>
Reason: <cycle | ambiguous placement | ambiguous lineage | unsupported inference | incomplete graph | mutation/verification failure>
```

Do not partially rewrite another dependency, focus state, hierarchy, or Project projection to compensate.

## Canonical Singleton

The durable control artifact is exactly one long-lived GitHub issue carrying the label:

```text
project-delivery:management
```

The label is the canonical discovery and **bootstrap activation** key. The title `Project Delivery Management` is presentation, not identity.

The singleton:

* is not a `wayfinder:map`;
* is not the native parent of Wayfinder maps;
* must not carry `workflow:tracked`;
* is not workflow truth because of any GitHub Project membership.

Bootstrap/migration owns creating the label and singleton.

### Bootstrap Activation Boundary

Project-delivery focus enforcement has two durable phases so the workflow can implement its own cutover without a circular dependency.

**Pre-bootstrap** means the repository does not yet contain the canonical `project-delivery:management` label.

In pre-bootstrap mode:

* no singleton is expected and no focused-set state exists;
* `guard <Wayfinder>` still validates that the target is a canonical open Wayfinder with no open direct map blocker;
* an eligible target returns `PROJECT DELIVERY GUARD: ALLOWED` with `Mode: pre-bootstrap`;
* a directly blocked target still returns `PROJECT DELIVERY GUARD: BLOCKED`;
* `reconcile` performs no focus mutation because focus authority is not activated yet;
* `status` reports `PROJECT DELIVERY MANAGEMENT: NOT BOOTSTRAPPED` plus the derivable Wayfinder frontier;
* human `focus`, `switch-focus`, and `parallel-focus` operations are unavailable because there is no durable focus owner yet;
* cross-Wayfinder dependency validation/mutation may still operate because native dependency semantics do not depend on the singleton focused set.

This is a temporary cutover compatibility mode, not an alternate scheduler. Do not infer or persist focus while pre-bootstrap.

**Activation begins when the canonical label exists.** From that point forward, require exactly one matching open singleton. Zero, multiple, or closed matching control issues fail closed. A partially applied migration that created the label but not a valid singleton is therefore invalid rather than silently treated as pre-bootstrap.

Migration should create the label and singleton in one audited cutover sequence and initialize:

```text
Focused Wayfinders: None
Parallel authorization: None
```

An already-running lifecycle that entered with `PROJECT DELIVERY GUARD: ALLOWED` in `Mode: pre-bootstrap` may finish **only that current atomic bootstrap/cutover lifecycle** if it is the operation activating project delivery. Activation during that invocation does not retroactively invalidate the authorization that was required to perform the cutover itself.

That inherited pre-bootstrap authorization:

* may not authorize a new human lifecycle after cutover;
* may not establish, switch, or broaden focus;
* may not be used to emit a downstream lifecycle handoff that requires focused delivery after activation.

Every later human lifecycle observes the activated singleton and normal focus rules.

When activation is in effect, discover across open and closed issues so a mistakenly closed singleton cannot be bypassed by creating another:

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

When bootstrap activation is in effect, parse the singleton current-state block and validate it against canonical tracker state.

Require:

1. every focused issue is a canonical Wayfinder map;
2. every focused Wayfinder is currently in the Wayfinder frontier;
3. focused-set cardinality `0..1` has `Parallel authorization: None`;
4. focused-set cardinality `>1` has a valid authorization comment whose exact sorted Wayfinder set matches the current focused set.

If cardinality is greater than one without matching durable authorization, return invalid control state. Do not choose which Wayfinder to keep.

If current state is malformed or ambiguous, fail closed.

## Deterministic Reconciliation

In pre-bootstrap mode, `reconcile` reports the derivable Wayfinder frontier and performs no focus mutation or Project delivery projection.

After activation, `reconcile` may change focus only when canonical state forces the consequence.

1. Re-read the singleton.
2. Re-read canonical `wayfinder:map` issues and their direct blockers.
3. Derive the current Wayfinder frontier.
4. Remove from the focused set any Wayfinder that:
   * is closed; or
   * has an open direct map blocker; or
   * is no longer a canonical `wayfinder:map`.
5. Record which focused Wayfinders were removed because they are closed.
6. Never add a replacement.
7. If a previously parallel set shrinks to one or zero, set `Parallel authorization: None`. Historical authorization remains in comments.
8. Persist the new current-state block only when its value changed.
9. Re-read and verify the exact persisted state.
10. Synchronize affected delivery scopes through **Project Projection Synchronization**. For an explicit human `reconcile`, synchronize every open Wayfinder-managed formal artifact under every open canonical Wayfinder in one batch even when canonical focus did not change.
11. For each closed focused Wayfinder removed in step 5, derive open canonical Wayfinders that directly list it in `blocked by` and are now frontier-eligible. If any exist, synchronize those delivery scopes and emit the **Prerequisite Completion Handoff** below.

A newly eligible Wayfinder never joins the focused set automatically.

### Prerequisite Completion Handoff

This handoff identifies downstream work that became eligible because a focused prerequisite completed. It never chooses among multiple successors.

When one or more downstream Wayfinders become frontier-eligible through a closed focused prerequisite, report:

```text
PROJECT DELIVERY: PREREQUISITE COMPLETE
Completed prerequisite: #<closed Wayfinder>
Resumable Wayfinders: #<n>[, #<n>...]
Current focus: <None | exact focused set>
```

Sort resumable Wayfinders by issue number only for stable presentation, not priority.

If current focus is `None` and exactly one resumable Wayfinder exists, append exactly:

```text
Next human action:
$project-delivery-management focus #<Wayfinder>
```

If current focus is `None` and multiple resumable Wayfinders exist, list the exact valid `focus` command for each and, when all are frontier-eligible, the exact `parallel-focus` command for the full sorted set. State that no successor was selected.

If another Wayfinder remains focused, list the resumable Wayfinders and only the exact valid `switch-focus` / `parallel-focus` choices. Do not alter the remaining focus.

An internal caller that triggered reconciliation after authoritative completion must surface this handoff to the human rather than auto-running a resumed Wayfinder lifecycle.

### Focused-but-Stalled

Lack of lower-level actionable work does **not** remove an otherwise frontier-eligible focused Wayfinder.

When a downstream lifecycle owner has authoritatively established that a focused, map-eligible Wayfinder currently has no actionable lower-level work because narrower decision/Spec/ticket blockers remain, report:

```text
PROJECT DELIVERY: FOCUSED-BUT-STALLED
```

Retain focus, synchronize `Delivery State = In Focus`, surface the lower-level blockers, and do not promote those blockers to a synthetic map blocker or silently switch/release focus.

Lower-level lifecycle owners recover their exact decision/Spec/ticket frontiers at their own boundaries and supply the resulting blockers here.

## Human Focus Operations

Human focus operations are unavailable in pre-bootstrap mode. Bootstrap/cutover activates the singleton with empty focus; a later explicit human invocation may then choose focus.

After activation, always re-read canonical state immediately before mutation.

### `focus <Wayfinder>`

Require:

* current focused set is empty;
* target is a canonical Wayfinder;
* target is in the current Wayfinder frontier.

If any check fails, do not mutate focus.

Persist an authorization comment, then set and verify:

```text
Focused Wayfinders: #<target>
Parallel authorization: None
```

Then synchronize the target delivery scope through **Project Projection Synchronization**.

### `switch-focus <Wayfinder>`

Require the target is a canonical frontier-eligible Wayfinder.

This is an explicit replacement operation. The previously focused Wayfinder remains open and simply becomes eligible-but-unfocused when still in the frontier. Do not create a blocker between the two maps.

Persist an authorization comment, replace and verify the focused set with the target, clear current parallel authorization, then synchronize the old and new focused delivery scopes through **Project Projection Synchronization**.

### `parallel-focus <Wayfinder>...`

Require:

* at least two distinct exact Wayfinder identities;
* every target is canonical;
* every target is currently frontier-eligible.

Do not implicitly include an existing focus that the human omitted.

Persist one authorization comment naming the exact sorted set, then set and verify:

```text
Focused Wayfinders: #<n>, #<n>...
Parallel authorization: <authorization comment URL>
```

Synchronize the union of the prior and new focused delivery scopes through **Project Projection Synchronization**.

Later eligible maps are not members unless a new explicit `parallel-focus` invocation authorizes a new exact set.

## Internal `guard <Wayfinder>`

The caller must supply or durably resolve the exact governing Wayfinder before calling this operation.

Re-read canonical map state first.

If pre-bootstrap, return:

```text
PROJECT DELIVERY GUARD: ALLOWED
Mode: pre-bootstrap
```

only when the target is a canonical open Wayfinder with zero open direct map blockers. A directly blocked target returns `PROJECT DELIVERY GUARD: BLOCKED` even before focus activation.

After activation, re-read and reconcile current singleton state first.

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

In pre-bootstrap mode, report:

* `PROJECT DELIVERY MANAGEMENT: NOT BOOTSTRAPPED`;
* current Wayfinder frontier;
* directly blocked open Wayfinders and their open direct blockers;
* that no focused-set authority exists yet.

After activation, report:

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

* bootstrap activation exists but the singleton is missing;
* more than one singleton exists;
* the singleton is closed;
* the current-state block is missing, duplicated, malformed, or references non-Wayfinder issues;
* focused-set cardinality is greater than one without matching durable parallel authorization;
* native blocker data is truncated or cannot be read;
* a requested focus target is not frontier-eligible;
* cross-Wayfinder dependency lineage or placement is ambiguous;
* a proposed dependency would create a cycle or is supported only by inference;
* required dependency/focus persistence cannot be verified.

Use:

```text
PROJECT DELIVERY MANAGEMENT: INVALID STATE
Reason: <exact durable-state, dependency, or eligibility failure>
```

The absence of the canonical activation label is the one valid pre-bootstrap condition; once the label exists, a missing singleton is invalid.

Project drift is never a reason to rewrite canonical focus or dependency state. When `$project-tracking` fails after authoritative state is durable, report that drift separately and preserve canonical state.

## Scope Boundary

This skill may:

* identify pre-bootstrap versus activated project-delivery state from the canonical label boundary;
* discover the singleton and canonical Wayfinder maps;
* derive the Wayfinder frontier from direct native blockers;
* own and persist the focused Wayfinder set after activation;
* own and persist exact human parallel-focus authorization after activation;
* guard map-level substantive delivery authorization;
* own semantic validation/write reconciliation for cross-Wayfinder dependencies;
* delegate native cross-Wayfinder dependency mechanics to `$github-issue-dependencies`;
* deterministically shrink invalid/completed focus membership;
* recover open Wayfinder-managed formal descendants from durable lineage for Project overlay synchronization;
* invoke `$project-tracking` after authoritative delivery changes so universal Project delivery state and lifecycle routing remain visibly synchronized;
* report deterministic human focus handoffs after dependency-driven focus release or focused prerequisite completion;
* report canonical status and focused-but-stalled state.

This skill must not:

* create/bootstrap or migrate the live singleton during steady-state operation;
* infer or persist focus in pre-bootstrap mode;
* own same-lineage dependency semantics;
* create parent/sub-issue hierarchy while reconciling cross-Wayfinder dependencies;
* infer dependencies from broad prose, Project state, labels, priority, similarity, or architectural overlap;
* write Wayfinder decisions, Specs, tickets, implementation, verification, review, or merge artifacts;
* own detailed Spec/ticket frontier semantics;
* directly mutate GitHub Project schema or use Project fields as authority;
* auto-run downstream lifecycle skills;
* auto-select a successor Wayfinder.

Those responsibilities remain with their existing lifecycle owners; `$project-tracking` owns GitHub Project projection mechanics.