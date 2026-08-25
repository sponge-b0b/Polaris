# Polaris Project Board Guide

This guide explains how humans should interpret the Polaris GitHub Project board.

It is **process documentation, not workflow authority**.

Authoritative behavior lives in:

```text
.agents/skills/*/SKILL.md
    executable workflow behavior

.agents/skills/README.md
    cross-skill architecture and governance

docs/process/project-board-guide.md
    human interpretation of the Project board
```

If this guide disagrees with an authoritative skill contract, treat the guide as stale documentation and fix it. Do not change workflow state merely to make the board match this document.

## The Core Mental Model

The Project board is a **projection of durable workflow state**, not the source of that state.

Four fields that can look redundant are intentionally independent:

```text
Delivery State → project-level authorization
Workflow State → lifecycle position
Next Skill     → lifecycle owner for the next human transition
Work Status    → immediate execution condition
```

Read them together.

For example:

```text
Artifact Type:  Wayfinder Decision
Delivery State: Eligible
Workflow State: Architecture Decision
Next Skill:     $wayfinder
Work Status:    Blocked
```

This is valid. The artifact belongs to a delivery scope that is eligible at the project level, `$wayfinder` still owns its lifecycle, but the decision cannot execute yet because an open native prerequisite blocks it.

Likewise:

```text
Artifact Type:  Spec
Delivery State: In Focus
Workflow State: Ready to Implement
Next Skill:     None
Work Status:    Ready
```

This is also valid. The Spec itself remains active, but its implementation-ticket children own the next executable action, so the parent Spec correctly advertises no direct next skill.

## Board Authority Boundary

Do not use Project fields as proof that a workflow transition happened.

Correctness-critical truth comes from durable tracker and repository evidence such as:

* Wayfinder maps and decisions;
* native parent/sub-issue relationships;
* native `blocked by` relationships;
* Wayfinder source/remediation provenance;
* Spec and Ticket baselines;
* Spec Verification Receipts;
* the conventional Spec Review issue and Spec Review Exit Receipt;
* Root Blocker ledgers and remediation evidence;
* the `project-delivery:management` singleton and its focus authorization comments;
* issue state where a lifecycle contract explicitly gives issue closure semantic meaning.

`$project-tracking` projects those facts into the GitHub Project after the authoritative transition has already succeeded.

If the Project disagrees with durable workflow evidence, the Project is drift. Repair the projection; do not rewrite workflow truth to match the board.

## Field Reference

### Artifact Type

**Question:** What kind of workflow object is this?

Formal values:

| Value | Meaning |
| --- | --- |
| `Wayfinder Map` | Canonical planning/delivery scope governed by `$wayfinder`. |
| `Wayfinder Decision` | Decision or planning work decomposed under a Wayfinder Map. |
| `Spec` | Durable implementation specification. |
| `Implementation Ticket` | Executable implementation work decomposed under a Spec. |
| `Spec Review` | The one conventional durable review artifact for a Spec. |
| `Review Remediation Ticket` | Executable remediation work decomposed under a Spec Review. |

`Idea` belongs to the pre-workflow intake layer and is not a formal workflow artifact.

### Delivery State

**Question:** What is this artifact's current relationship to project-level delivery authorization?

| Value | Meaning |
| --- | --- |
| `In Focus` | At least one governing Wayfinder is both focused and frontier-eligible. The delivery scope is currently authorized to advance. |
| `Eligible` | No governing Wayfinder is focused, but at least one governing Wayfinder is frontier-eligible. The work is structurally eligible but is not the current project focus. |
| `Denied` | No governing Wayfinder is currently frontier-eligible. Project-delivery authorization forbids advancement. |
| `Independent` | The formal artifact is durably established as intentionally outside Wayfinder delivery governance. This is explicit classification, never a fallback for missing provenance. |
| `Released` | The artifact's formal lifecycle is complete, so project-delivery coordination no longer applies. |

Important distinctions:

* `Denied` is a **delivery-authorization** state.
* `Blocked` is a **lifecycle/execution** term used by `Workflow State` or `Work Status`.
* A descendant may be `Eligible` and `Blocked` at the same time.
* A focused Wayfinder with lower-level blocked work remains `In Focus`; lower-level stalledness does not create another Delivery State.

### Workflow State

**Question:** Where is this artifact in its own lifecycle?

`Workflow State` is a state machine, not a monotonically increasing stage number. Work may revisit earlier states when review, verification, or implementation reveals additional work or unresolved architecture.

The valid meaning depends on `Artifact Type`; use the routing matrix later in this guide rather than interpreting a Workflow State in isolation.

Common values:

| Value | Meaning |
| --- | --- |
| `Intake` | Pre-formal-workflow idea/intake state. |
| `Architecture Decision` | Architectural/planning decision work remains active. |
| `Ready to Spec` | Specification creation/reconciliation is the next lifecycle action. |
| `Spec Delivery` | Durable Spec handoffs exist and governed Specs now own downstream execution. |
| `Ready to Ticket` | Ticket decomposition/reconciliation is the next lifecycle action. |
| `Ready to Implement` | Executable child work exists or an executable ticket itself is ready. Meaning depends on Artifact Type. |
| `Ready to Verify` | Implementation work is complete enough for Spec verification. |
| `Ready to Review` | A passing current Spec Verification Receipt authorizes independent review. |
| `Review Remediation` | Review findings/remediation lineage is active. |
| `Awaiting Root Verification` | A review-remediation ticket is waiting for independent root-closure verification. |
| `Architecture Remediation` | The current lifecycle cannot proceed without architecture reconciliation/re-entry. |
| `Ready to Merge` | Review exit conditions have passed and Spec merge/cleanup is next. |
| `Blocked` | The owning lifecycle has established an explicit blocked lifecycle state. |
| `Complete` | The owning lifecycle has completed the formal artifact. |

Do not infer `Workflow State` solely from issue Open/Closed state.

### Next Skill

**Question:** Which human-invocable lifecycle/HITL owner handles this artifact's next transition?

Examples:

```text
$wayfinder
$to-specs
$to-tickets
$implement-ticket
$verify-spec
$review-spec
$architecture-remediation
$verify-root-closure
$spec-merge-cleanup
$project-delivery-management
None
```

`Next Skill` is **not** a list of every helper the workflow may call internally. Internal composition such as `$to-remediation-specs`, `$to-remediation-tickets`, `$review-spec-remediation`, or `$github-issue-dependencies` normally does not become a separate human board stage.

`None` does not necessarily mean complete. It often means a child/downstream artifact currently owns the next executable action.

Delivery authorization does not normally erase a descendant's lifecycle route. An `Eligible` or `Denied` descendant can still advertise `$to-tickets`, `$implement-ticket`, `$wayfinder`, or another lifecycle owner; that owner must enforce project-delivery authorization before substantive work.

The important exception is the **Wayfinder Map itself**:

* eligible-but-unfocused Wayfinder Map → `$project-delivery-management`;
* blocked/denied Wayfinder Map → `None`;
* focused Wayfinder Map → preserve its lifecycle route.

### Work Status

**Question:** What is the artifact's immediate work condition?

| Value | Meaning |
| --- | --- |
| `Ready` | No current lifecycle/dependency condition prevents the artifact's next owned action. |
| `In Progress` | The artifact represents an actively coordinated parent/delivery scope rather than a directly queued unit of work. |
| `Blocked` | Immediate execution is prevented by lifecycle state, an open native blocker, or denied project-delivery authorization where the overlay requires it. |
| `Done` | Formal lifecycle is complete. |

For open artifacts, dependency blocking is independent from lifecycle routing:

```text
open native blocker
    → Work Status = Blocked
    → Workflow State is preserved
    → Next Skill is preserved for descendants
    → Delivery State is derived separately
```

This is why `Eligible / Architecture Decision / $wayfinder / Blocked` can be correct.

### Intake State

**Question:** Where is an informal idea before it becomes formal workflow work?

`Intake State` belongs only to Ideas & Intake. Once an item is promoted into the formal workflow, the formal artifact should not retain Intake State as lifecycle truth.

### Priority

**Question:** How is this work presented/prioritized operationally?

Priority is presentation metadata, not workflow authority.

It does **not** establish:

* focus;
* dependency eligibility;
* lifecycle position;
* the next lifecycle owner.

A lifecycle owner changes Priority only when it independently owns an intentional presentation change; otherwise `$project-tracking` preserves the existing value, including blank.

### Area

**Question:** What project/functional area is useful for grouping this item?

Area is presentation metadata, not workflow authority. It may legitimately be blank.

As with Priority, a lifecycle owner supplies an Area change only when it independently owns that presentation change; otherwise `$project-tracking` preserves the existing value verbatim.

### Root Blocker

**Question:** Which canonical review root blocker does this remediation ticket close?

A non-empty value is valid only for a `Review Remediation Ticket` and has the form:

```text
RB-<n>
```

Examples:

```text
RB-1
RB-17
```

Root Blocker is not a generic free-form blocked-reason field.

### Completed On

**Question:** When did this formal artifact complete its lifecycle?

It is populated only when:

```text
Workflow State = Complete
```

and is stored as an ISO date:

```text
YYYY-MM-DD
```

A non-complete artifact should not carry `Completed On`. Do not infer this date merely from issue closure.

## The Four-Field Interpretation Matrix

When a row looks strange, interpret these fields in this order:

| Field | Interpret as | Do not confuse with |
| --- | --- | --- |
| `Delivery State` | Project-level authorization | Immediate dependency blocking |
| `Workflow State` | Artifact lifecycle position | Issue Open/Closed state |
| `Next Skill` | Human lifecycle owner | Immediate readiness |
| `Work Status` | Immediate execution condition | Lifecycle ownership |

A few common combinations:

| Delivery State | Workflow State | Next Skill | Work Status | Interpretation |
| --- | --- | --- | --- | --- |
| `In Focus` | `Ready to Ticket` | `$to-tickets` | `Ready` | Focused Spec is authorized and ticketing is next. |
| `Eligible` | `Ready to Ticket` | `$to-tickets` | `Ready` | Spec lifecycle says ticketing is next, but its Wayfinder is not focused; `$to-tickets` must stop at the delivery guard. |
| `Eligible` | `Architecture Decision` | `$wayfinder` | `Blocked` | Decision lifecycle belongs to `$wayfinder`, but a native prerequisite currently prevents execution. |
| `In Focus` | `Ready to Implement` | `None` | `Ready` | Parent Spec is active while implementation-ticket children own execution. |
| `Denied` | `Ready to Implement` | `$implement-ticket` | `Blocked` | Ticket still belongs to `$implement-ticket`, but current project-delivery authorization forbids advancement. |
| `Released` | `Complete` | `None` | `Done` | Formal lifecycle and project-delivery coordination are complete. |

## Project Delivery Management

`$project-delivery-management` coordinates delivery WIP across independent Wayfinder lineages. It is **not another lifecycle stage**.

### Wayfinder frontier

The Wayfinder frontier is exactly:

> open canonical `wayfinder:map` issues with zero open direct native map blockers.

Do not use Priority, Project position, issue age, assignee, activity, branch state, or lower-level ticket/Spec blockers to determine the map frontier.

### Focus

Focus answers:

> Which frontier-eligible Wayfinder delivery scope(s) has the human explicitly authorized Polaris to advance now?

Focus is durable state owned by the one `project-delivery:management` singleton issue.

Only explicit human management operations may make discretionary focus choices:

```text
focus
switch-focus
parallel-focus
```

Internal lifecycle composition may guard or reconcile focus, but may never infer a new focus choice.

### Parallel focus

More than one focused Wayfinder requires an exact durable `parallel-focus` authorization covering the exact focused set.

Later eligible Wayfinders do not silently join that set.

### Reconciliation

Reconciliation may remove focus when canonical state forces it, such as when a focused Wayfinder closes or gains an open direct map blocker.

It never chooses a replacement automatically.

A human `reconcile` also provides the universal repair path for delivery-overlay projection: all open Wayfinder-managed formal artifacts under all open canonical Wayfinders are re-synchronized from durable state.

### Focused but stalled

A focused Wayfinder may remain frontier-eligible while lower-level work is blocked.

In that case:

```text
Wayfinder Delivery State = In Focus
lower-level Work Status   = Blocked where appropriate
```

Do not invent a synthetic Wayfinder-to-Wayfinder blocker merely to represent lower-level stalledness.

## Delivery Overlay Matrix

Project-delivery coordination is applied **after** the base lifecycle route is validated.

### Wayfinder Map

| Project Delivery State | Final Work Status | Final Next Skill | Final Delivery State |
| --- | --- | --- | --- |
| `in-focus` | `In Progress` | preserve base lifecycle route | `In Focus` |
| `eligible` | `Ready` | `$project-delivery-management` | `Eligible` |
| `blocked` | `Blocked` | `None` | `Denied` |

An eligible Wayfinder Map therefore advertises `$project-delivery-management`, not `$wayfinder` or `$to-specs`, because the next human decision is project focus.

### Wayfinder-managed descendants

Applies to:

```text
Wayfinder Decision
Spec
Implementation Ticket
Spec Review
Review Remediation Ticket
```

| Project Delivery State | Final Work Status | Final Next Skill | Final Delivery State |
| --- | --- | --- | --- |
| `in-focus` | preserve base | preserve base | `In Focus` |
| `eligible` | preserve base | preserve base | `Eligible` |
| `blocked` | `Blocked` | preserve base | `Denied` |

The key rule is:

> Delivery authorization never suppresses a descendant's lifecycle owner.

### Independent formal artifact

For a non-complete formal artifact durably classified as `independent`:

```text
Delivery State = Independent
Work Status    = preserve base
Next Skill     = preserve base
```

### Complete artifact

Every complete formal artifact projects exactly:

```text
Workflow State = Complete
Delivery State = Released
Work Status    = Done
Next Skill     = None
Completed On   = <ISO date>
```

## Base Lifecycle Routing Matrix

This matrix answers:

> Given an artifact's type and lifecycle position, which human-invocable lifecycle owner is responsible next before project-delivery overlay is applied?

`None` means no direct human lifecycle action belongs to that row at that moment; child/downstream work may still be active.

### Wayfinder Map

| Workflow State | Base Next Skill | What the state means / what normally causes it |
| --- | --- | --- |
| `Architecture Decision` | `$wayfinder` | Decision/fog resolution remains active in the Wayfinder lifecycle. |
| `Ready to Spec` | `$to-specs` | Architecture is sufficiently resolved for specification creation/reconciliation to be the next action. |
| `Spec Delivery` | `None` | Durable Derived/Remediation Spec handoffs exist and at least one governed Spec remains open; those Specs own downstream execution. |
| `Architecture Remediation` | `$wayfinder` | Architecture re-entry is required before the delivery scope can continue. |
| `Blocked` | `None` | The Wayfinder lifecycle itself has established a blocked state. |
| `Complete` | `None` | No unresolved Wayfinder decision/fog remains and all currently governed Derived/Remediation Specs are complete. |

### Wayfinder Decision

| Workflow State | Base Next Skill | What the state means / what normally causes it |
| --- | --- | --- |
| `Architecture Decision` | `$wayfinder` | The decision remains active and belongs to Wayfinder. |
| `Blocked` | `None` | The decision lifecycle itself is blocked. Native dependencies can also make `Work Status=Blocked` without changing this Workflow State. |
| `Complete` | `None` | The decision has been resolved/completed by its owning Wayfinder lifecycle. |

### Spec

| Workflow State | Base Next Skill | What the state means / what normally causes it |
| --- | --- | --- |
| `Ready to Ticket` | `$to-tickets` | The Spec is ready for ticket decomposition or reconciliation. |
| `Ready to Implement` | `None` | Open implementation-ticket children own the next executable work. |
| `Ready to Verify` | `$verify-spec` | Required implementation-ticket work is complete and Spec-level verification is next. |
| `Ready to Review` | `$review-spec` | A current passing Spec Verification Receipt authorizes independent review. |
| `Review Remediation` | `None` | Review/remediation lineage owns the next executable work. |
| `Architecture Remediation` | `$architecture-remediation` | The Spec cannot continue without architecture reconciliation/re-entry. |
| `Ready to Merge` | `$spec-merge-cleanup` | Review exit conditions have passed and the current Spec Review Exit Receipt authorizes cleanup/merge. |
| `Blocked` | `None` | The Spec lifecycle itself has established a blocked state. |
| `Complete` | `None` | Spec merge/direct closure and required cleanup/reconciliation completed. |

### Implementation Ticket

| Workflow State | Base Next Skill | What the state means / what normally causes it |
| --- | --- | --- |
| `Ready to Implement` | `$implement-ticket` | The ticket is executable under its Spec branch/baseline contract. |
| `Architecture Remediation` | `$architecture-remediation` | Implementation discovered unresolved architecture that must be reconciled first. |
| `Blocked` | `None` | The ticket lifecycle itself is blocked. Native blockers can also make `Work Status=Blocked` while leaving `Workflow State=Ready to Implement`. |
| `Complete` | `None` | The implementation ticket completed its authoritative implementation/evidence/reconciliation path. |

### Spec Review

Every reviewed Spec has exactly one conventional Spec Review issue as the durable owner of review/remediation state and the final Spec Review Exit Receipt.

| Workflow State | Base Next Skill | What the state means / what normally causes it |
| --- | --- | --- |
| `Review Remediation` | `$to-tickets` or `None` | Before executable remediation children exist, ticketing is next; once remediation-ticket children exist, they own the next action and the review parent shows `None`. |
| `Architecture Remediation` | `$architecture-remediation` | A Blocking architecture finding requires architecture re-entry. |
| `Blocked` | `None` | Review lifecycle is explicitly blocked. |
| `Complete` | `None` | Review lifecycle has completed and cleanup has closed the conventional review artifact. |

A clean review still uses the conventional Spec Review issue; it is not omitted merely because no remediation tickets were required.

### Review Remediation Ticket

| Workflow State | Base Next Skill | What the state means / what normally causes it |
| --- | --- | --- |
| `Ready to Implement` | `$implement-ticket` | The remediation root has executable implementation work. |
| `Awaiting Root Verification` | `$verify-root-closure` | Candidate remediation is ready for fresh independent root-closure verification. |
| `Architecture Remediation` | `$architecture-remediation` | Root remediation cannot proceed without new/reconciled architecture. |
| `Blocked` | `None` | The remediation ticket lifecycle itself is blocked. |
| `Complete` | `None` | Root verification/evidence/reconciliation and ticket completion are finished. |

## Lifecycle Transition Guide

The tables above describe valid row states. This section explains the main human lifecycle flow that produces those states.

The happy path is:

```text
Wayfinder Map
    Architecture Decision
        ↓ decisions clear
    Ready to Spec
        ↓ $to-specs
    Spec Delivery

Spec
    Ready to Ticket
        ↓ $to-tickets
    Ready to Implement
        ↓ child Implementation Tickets complete
    Ready to Verify
        ↓ $verify-spec passes
    Ready to Review
        ↓ $review-spec passes
    Ready to Merge
        ↓ $spec-merge-cleanup
    Complete
```

Ticket execution appears beneath the Spec:

```text
Implementation Ticket
    Ready to Implement
        ↓ $implement-ticket
    Complete
```

Review remediation introduces a loop rather than a one-way stage progression:

```text
Spec
    Ready to Review
        ↓ $review-spec finds Blocking findings
    Review Remediation

Spec Review
    Review Remediation
        ↓ $to-tickets when remediation tickets do not yet exist
        ↓ child remediation tickets own execution once created

Review Remediation Ticket
    Ready to Implement
        ↓ $implement-ticket
    Awaiting Root Verification
        ↓ fresh $verify-root-closure attempt
    Complete

Spec
    ↓ remediation frontier complete
    Ready to Verify
        ↓ $verify-spec
    Ready to Review
        ↓ $review-spec again
```

Architecture discovery can route an active lifecycle backward through architecture remediation:

```text
active lifecycle owner
    ↓ unresolved durable architecture
Architecture Remediation
    ↓ $architecture-remediation
$wayfinder
    ↓ architecture resolved
$to-specs
    ↓ reconcile affected Specs
$to-tickets
    ↓ reconcile affected tickets
$implement-ticket
```

Do not jump directly back to stale implementation work when architecture changed the governing Spec/remediation obligation.

## What Causes `Work Status = Blocked`?

`Blocked` Work Status is deliberately broader than `Workflow State = Blocked`.

For open formal artifacts, base Work Status is derived in this order:

```text
Workflow State = Blocked
    → Blocked

otherwise, one or more open native blockers
    → Blocked

otherwise, Wayfinder Map / Spec Delivery
    → In Progress

otherwise
    → Ready
```

Then project-delivery overlay is applied.

For a Wayfinder-managed descendant with delivery state `blocked`/`Denied`, final Work Status becomes `Blocked` while its lifecycle `Next Skill` remains visible.

For a Wayfinder Map, the delivery overlay directly controls the final Work Status:

```text
In Focus → In Progress
Eligible → Ready
Denied   → Blocked
```

## Native Dependencies

Native GitHub `blocked by` relationships represent actual execution prerequisites, not priority or focus preference.

Same-lineage dependency semantics belong to the relevant lifecycle owner.

Cross-Wayfinder dependency semantics belong to `$project-delivery-management`, which places a dependency at the narrowest authoritative consumer/blocker boundary and delegates only native relationship mechanics to `$github-issue-dependencies`.

A Wayfinder-to-Wayfinder dependency is appropriate only when the downstream delivery scope as a whole cannot advance until the upstream Wayfinder completes. Narrower decision/Spec/ticket dependencies should be preferred when they express the real prerequisite without blocking unrelated work.

Dependency edges must not be invented to represent:

* focus;
* Priority;
* queue order;
* WIP preference;
* issue age;
* Project-board position.

## Common Misreadings

### `Eligible` means ready to execute

No. `Eligible` means the governing delivery scope is frontier-eligible but not currently focused.

A lifecycle skill may still be shown in `Next Skill`, but it must enforce the delivery guard before substantive work.

### `Blocked` Work Status means Delivery State should be `Denied`

No. A native lower-level prerequisite can block immediate execution while the governing Wayfinder remains frontier-eligible.

Valid example:

```text
Delivery State = Eligible
Work Status    = Blocked
```

### `Next Skill = None` means the artifact is complete

No. It may mean child work owns the next action.

Typical examples:

```text
Spec / Ready to Implement
Spec / Review Remediation
Wayfinder Map / Spec Delivery
Spec Review / Review Remediation with open remediation-ticket children
```

### A closed implementation ticket means its Spec is complete

No. Ticket closure may merely advance the parent Spec toward `Ready to Verify`.

### A closed issue always means `Workflow State = Complete`

No. GitHub issue state and Polaris lifecycle state are distinct except where the owning lifecycle explicitly binds them.

### Priority determines focus

No. Focus is explicit durable human authorization in the `project-delivery:management` singleton.

### Project-board position determines lifecycle state

No. Views, grouping, sorting, columns, and saved filters are presentation only.

### A focused Wayfinder must always have immediately executable child work

No. A map can remain focused and frontier-eligible while narrower work is stalled. That is focused-but-stalled, not a reason to synthesize a map blocker or silently switch focus.

## Reading a Row: A Practical Checklist

When reviewing an item on the Project board:

1. **Identify Artifact Type.** This tells you which lifecycle contract applies.
2. **Read Delivery State.** Determine whether project-level delivery authorization is focused, merely eligible, denied, independent, or released.
3. **Read Workflow State.** Locate the artifact in its own lifecycle using the routing matrix above.
4. **Read Next Skill.** Identify the human lifecycle owner for the next transition. Remember that `None` can mean child-owned execution.
5. **Read Work Status.** Determine whether immediate execution is Ready, In Progress, Blocked, or Done.
6. **If blocked unexpectedly, inspect native blockers.** Do not infer the blocker from Delivery State alone.
7. **Treat Priority and Area as presentation metadata.** They help organize the board but establish no workflow authority.
8. **If the row contradicts durable evidence, treat it as Project drift.** Reconcile the projection rather than editing semantic workflow state to match the board.

## When to Use `$project-delivery-management`

Use the project-delivery management skill when the human needs to inspect or change project-level focus rather than advance an artifact lifecycle.

Typical human operations are:

```text
$project-delivery-management status
$project-delivery-management reconcile
$project-delivery-management focus <Wayfinder>
$project-delivery-management switch-focus <Wayfinder>
$project-delivery-management parallel-focus <Wayfinder>...
```

An eligible Wayfinder Map advertises `$project-delivery-management` because the missing transition is a human focus decision.

Do not invoke project-delivery management merely because a descendant is dependency-blocked. Its lifecycle owner and native dependency state remain the relevant interpretation unless the dependency crosses Wayfinder lineages or canonical focus itself must change.

## Reconciliation and Board Drift

`$project-tracking` is the internal projection helper. Humans normally should not invoke it directly.

Lifecycle owners call it after durable transitions. `$project-delivery-management` calls it to apply delivery overlays.

A human `$project-delivery-management reconcile` is the deterministic broad repair path for open Wayfinder-managed artifacts. It recovers authority from GitHub tracker lineage, focus, and blocker state, then reprojects the delivery overlay without making Project fields authoritative.

Project synchronization failure means:

```text
projection drift
```

It does **not** mean the authoritative lifecycle transition should be rolled back.

## Document Maintenance

This guide should remain a human interpretation layer, not a duplicate workflow engine.

When workflow semantics change:

1. update the authoritative `SKILL.md` contract first;
2. update `.agents/skills/README.md` when cross-skill architecture changed;
3. update this guide when the human interpretation of fields, routing, or board transitions changed;
4. use the deterministic workflow audit to detect contract/projection drift rather than trusting visual inspection alone.

Do not add skill-specific command algorithms, mutation implementations, API details, or receipt schemas here unless they are necessary to explain how a human should interpret the Project board.