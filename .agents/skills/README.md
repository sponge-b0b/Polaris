# Skills

This directory contains the agent skills used to plan, implement, verify, review, and maintain Polaris work.

This README documents **cross-skill architecture and governance**. It explains how skills compose, where human control belongs, how lifecycle ownership moves, how the lifecycle may loop, and which invariants must remain true across skill boundaries.

Individual `SKILL.md` files remain authoritative for their own executable procedure. Do not duplicate detailed commands, templates, or skill-specific algorithms here.

If this README and a `SKILL.md` disagree, treat that as a workflow defect to reconcile rather than guessing which behavior to follow.

## Sources of Authority

Use these layers for different concerns:

```text
.agents/skills/README.md
    cross-skill architecture, lifecycle, conventions, and invariants

.agents/skills/<skill>/SKILL.md
    executable behavior and responsibility of one skill

.agents/skills/<skill>/agents/openai.yaml
    Codex-specific metadata and invocation policy when present

other platform-specific metadata
    platform-specific discovery or invocation controls
```

Invocation metadata controls whether a platform may discover or select a skill automatically. It does **not**, by itself, determine whether a cross-skill transition is a Human Handoff.

## Governing Workflow-Boundary Rule

> **A Human Handoff is required only when the current workflow intentionally ends and the human should choose, authorize, or initiate the next lifecycle stage.**

Classify every cross-skill transition as one of these four cases:

| Transition | Required behavior |
| --- | --- |
| **Internal composition** | Parent invokes the named child directly. |
| **Ordinary return** | Child returns its result and the caller resumes directly. |
| **In-skill HITL** | Current skill asks the user for a decision and then continues itself. |
| **Lifecycle / user-control boundary** | Current skill halts and emits an explicit Human Handoff. |

Do not create Human Handoffs merely because the target skill disables implicit invocation.

## Invocation Semantics

Polaris distinguishes **automatic skill selection** from **delegated workflow composition**.

When a human explicitly authorizes a parent workflow and that workflow explicitly prescribes a named child skill as part of its procedure, the child may be invoked as internal composition.

Example:

```text
Human invokes $to-tickets
    ↓
$to-tickets explicitly invokes $github-issue-dependencies
    ↓
valid internal composition
```

This is different from an agent independently deciding that another skill seems useful.

For Codex, `policy.allow_implicit_invocation: false` is treated as a restriction on model-initiated automatic selection, not as a universal requirement for a new human authorization at every prescribed child edge.

For cross-platform portability, individual skills may also carry platform-specific invocation controls such as `disable-model-invocation: true`. Preserve those controls, but determine Human Handoffs from lifecycle semantics rather than metadata alone.

## Pre-Workflow Intake Boundary

The public Polaris Project may contain **Ideas & Intake** items before formal delivery work begins.

Intake is an operational planning layer, not a skill lifecycle stage and not an architecture authority.

An Intake item means only:

> This concept is ready to be discussed publicly, but Polaris has not yet committed to architecture, scope, specification, or implementation.

Keep rough or private brainstorming outside the public Project until it is ready to be exposed.

Promotion from Intake to formal work is an explicit human decision:

```text
Ideas & Intake
    ↓ HUMAN promotion
$wayfinder
```

`$wayfinder` is the normal formal entry point when the idea requires architectural discovery or durable design decisions.

Do not mutate an informal Intake item into architecture authority merely because it was promoted. The resulting Wayfinder map and decisions become the durable planning artifacts.

## Skill Lifecycle

### Lifecycle Model

The Polaris delivery lifecycle is a **state machine, not a forward-only pipeline**.

The happy path is intentionally simple, but implementation, verification, review, or specification may discover a genuine architecture blocker and route the work back through Wayfinder. Review blockers may create a remediation loop that repeats ticketing, implementation, verification, and review until the review Exit Gate passes.

Important invariants:

* lifecycle state may move backward or revisit an earlier stage;
* a closed GitHub issue does not necessarily mean its parent lifecycle is complete; for example, a closed ticket may still leave its Spec active;
* a closed Wayfinder map is the durable marker that its delivery scope is complete under the current known state; authoritative architecture re-entry or proven open governed Spec work reopens the map before substantive advancement;
* every reviewed Spec has exactly one conventional Spec Review issue as the durable owner of review/remediation state and the final Spec Review Exit Receipt; remediation state itself is conditional;
* internal helper skills do not become separate lifecycle stages merely because they are named skills;
* durable tracker/repository state, not conversational memory or Project-board position, determines correctness-critical workflow state.

### Project Delivery Management

`$project-delivery-management` coordinates intentional delivery WIP across independent Wayfinder lineages without replacing their lifecycle owners.

Keep two questions separate:

> **Dependency determines what may proceed. Focus determines what Polaris will proceed with now.**

Cross-skill invariants:

* canonical Wayfinders are discovered from `wayfinder:map`; there is no duplicate map registry;
* the Wayfinder frontier is the set of open canonical maps with no open direct native blockers;
* project focus is durable, explicit human intent owned by the single `project-delivery:management` control issue; it is never inferred from Project fields, Priority, assignees, issue ordering, activity, branches, or conversation state;
* charting a new Wayfinder is allowed while another map is focused, but substantive advancement of a Wayfinder-managed lineage is guarded before mutation;
* cross-Wayfinder semantic dependencies belong on the narrowest authoritative artifact whose lifecycle completion satisfies the prerequisite; `$project-delivery-management` owns cross-lineage semantics and delegates native relationship mechanics to `$github-issue-dependencies`;
* Wayfinder-to-Wayfinder blockers are reserved for true whole-map prerequisites and must never encode project WIP preference;
* `$to-specs` may publish all currently specifiable Specs. The Spec dependency frontier is open Specs with no open native blockers; a Wayfinder-managed Spec is actionable only when at least one current governing Wayfinder is focused;
* multiple independent actionable Specs inside one focused Wayfinder are allowed; do not create a separate active-Spec queue or WIP state;
* authoritative transitions happen before project-delivery reconciliation. Reconciliation may remove completed or directly ineligible focus but never chooses a replacement;
* a map that remains frontier-eligible but has only lower-level blocked work stays focused-but-stalled rather than acquiring a synthetic map blocker;
* the GitHub Project remains a downstream projection of these facts and never becomes workflow authority.

### Complete Delivery Lifecycle

```text
Ideas & Intake                         public Project only; not formal skill state
    ↓ HUMAN promotion
$wayfinder
    ↺ in-skill HITL / additional Wayfinder decisions as required
    ↓ route clear
    ↓ HUMAN
$to-specs
    ├─ internal → $to-remediation-specs when an existing Spec must be reconciled
    ├─ unresolved architecture → HUMAN → $wayfinder
    └─ Spec ready
           ↓ HUMAN
$to-tickets
    ├─ internal → $to-remediation-tickets when existing tickets or review remediation exist
    ├─ architecture-blocked remediation → HUMAN → owning review/architecture path
    └─ implementation frontier ready
           ↓ HUMAN
$implement-ticket
    ├─ ordinary ticket complete; frontier remains
    │      ↓ HUMAN
    │   $implement-ticket                 next fresh ticket session
    │
    ├─ all implementation tickets complete
    │      ↓ HUMAN
    │   $verify-spec
    │
    ├─ unresolved architecture
    │      ↓ HUMAN
    │   $architecture-remediation
    │      ↓ HUMAN
    │   $wayfinder
    │      ↓ HUMAN after route clear
    │   $to-specs → $to-tickets → $implement-ticket
    │
    └─ Spec Review remediation ticket
           ↓ HUMAN authorization
       fresh verifier subagent executes $verify-root-closure
           ├─ FAIL / invalidated attempt
           │      ↓ ordinary return
           │   $implement-ticket resumes, fixes, reproves
           │      ↓ HUMAN authorization again
           │   fresh $verify-root-closure attempt
           │
           └─ PASS
                  ↓ ordinary return
              $implement-ticket finalizes commit/push/evidence/reconciliation/closure
                  ├─ remediation frontier remains → HUMAN → $implement-ticket
                  └─ remediation complete → HUMAN → $verify-spec

$verify-spec
    ├─ verification-owned failure → repair and rerun inside $verify-spec
    ├─ unresolved architecture → HUMAN → $architecture-remediation → $wayfinder → ...
    └─ passing Spec Verification Receipt
           ↓ HUMAN
$review-spec
    ├─ zero Blocking findings
    │      ├─ create or reuse the one conventional Spec Review issue
    │      ├─ persist Spec Review Exit Receipt on that review issue
    │      └─ HUMAN → $spec-merge-cleanup
    │
    ├─ Blocking findings; no new architecture decision required
    │      ├─ create or reuse the Spec Review issue
    │      ├─ internal → $review-spec-remediation
    │      └─ HUMAN → $to-tickets → $implement-ticket → $verify-spec → $review-spec
    │
    └─ Blocking architecture finding with a new decision required
           ↓ HUMAN
       $architecture-remediation
           ↓ HUMAN
       $wayfinder
           ↓ HUMAN after route clear
       $to-specs → $to-tickets → $implement-ticket → $verify-spec → $review-spec

$spec-merge-cleanup
    ├─ validate current Spec Review Exit Receipt
    ├─ merge or directly close the Spec
    ├─ close the conventional Spec Review issue
    ├─ clean the Spec branch when applicable
    └─ reconcile every governing Wayfinder
           └─ close only when no unresolved decision/fog remains
              and all governed Derived/Remediation Specs are complete
           ↓
       Spec lifecycle complete
```

The diagram describes lifecycle ownership only. Each named skill remains authoritative for its detailed gates, mutation rules, receipts, and handoff text.

### Specification Creation and Reconciliation

`$to-specs` owns the transition from decision-complete planning into implementation specification.

When a Wayfinder source already has an in-progress derived or remediation Spec, `$to-specs` invokes `$to-remediation-specs` internally rather than creating a duplicate Spec.

`$to-remediation-specs` preserves the original Spec identity, source provenance, branch/baseline lineage, tickets, and review lineage while applying the decision delta in place.

If accepted architecture does not determine the durable semantics required to amend the Spec, specification stops and returns to Wayfinder rather than inventing architecture inside the Spec.

### Ticket Creation and Reconciliation

`$to-tickets` owns the transition from a Spec or Spec Review remediation source into executable ticket work.

When an existing Spec already has ticket lineage, or the source is a Spec Review, `$to-tickets` invokes `$to-remediation-tickets` internally.

Formal Implementation Tickets and Review Remediation Tickets are created or reconciled only through this ticketing lifecycle. A lifecycle owner that discovers additional executable work must route that work back through `$to-tickets` rather than create an ad-hoc formal ticket. `$to-remediation-tickets` remains internal composition and `$github-issue-dependencies` remains the mechanical owner for native relationship publication.

Remediation ticketing is root-driven rather than symptom-driven. Closed tickets are historical evidence and are not reopened or rewritten to represent newly required work.

All tickets for one Spec share the same Spec branch and fixed Spec baseline. Each ticket owns its own immutable Ticket baseline after `$implement-ticket` replaces `Pending` before first mutation.

### Review and Remediation Loop

`$review-spec` owns independent review and parent reconciliation.

Every reviewed Spec has exactly one conventional **Spec Review issue** as the durable owner of review state. `$review-spec` creates it at the first persistence point when none exists and reuses it across clean review, remediation, and re-review. Do not create one issue per pass.

Clean first review:

```text
$review-spec
    ↓ zero Blocking findings
create or reuse the one conventional Spec Review issue
    ↓
persist Spec Review Exit Receipt on that review issue
    ↓ HUMAN
$spec-merge-cleanup
```

The conventional Spec Review issue remains the durable review owner even when no remediation is required.

When architecture-conforming Blocking findings remain:

```text
$review-spec
    ↓ create or reuse Spec Review issue
    ↓ persist durable review-remediation input
$review-spec-remediation
    ↓ synthesize/update durable Root Blocker remediation state
    ↓ HUMAN
$to-tickets
    ↓
$implement-ticket
    ↓
$verify-spec
    ↓
$review-spec
```

`$review-spec-remediation` is internal composition, not a separate human-authorized lifecycle stage.

The same Spec Review issue is reused across remediation/re-review cycles. Do not create a new review issue for every review pass.

The **Pending Review Remediation** packet remains intentionally durable even though the transition into `$review-spec-remediation` is internal. It provides an explicit, recoverable contract between independent review/reconciliation and remediation synthesis.

The review loop ends only when the review Exit Gate passes and `$review-spec` persists a current **Spec Review Exit Receipt** on the one conventional Spec Review issue.

### Architecture Escalation and Re-entry

When a workflow cannot continue without a new or changed durable architectural choice:

```text
active lifecycle owner
    ↓ HUMAN
$architecture-remediation
    ↓ HUMAN
$wayfinder
```

`$architecture-remediation` routes unresolved questions into the **existing Wayfinder effort**. It does not resolve architecture, modify implementation, amend a Spec, or create a replacement Wayfinder map.

Do not treat missing realization of already accepted architecture as a new architecture decision. The owning skill decides whether the blocker is implementation work or genuinely unresolved architecture.

If the governing Wayfinder was previously closed, authoritative re-entry reopens it before unresolved decision work is created or resumed. Reopening restores eligibility evaluation; it does not restore or infer project focus.

After new architecture is resolved, or current authority requires Spec reconciliation, the normal return path is:

```text
$wayfinder
    ↓ HUMAN
$to-specs
    ↓ internal $to-remediation-specs when an existing Spec is affected
    ↓ HUMAN
$to-tickets
    ↓ HUMAN
$implement-ticket
```

Do **not** jump directly back to the previously blocked implementation ticket when the architectural decision changes or invalidates its Spec/remediation obligation. The Spec and ticket contracts must first be reconciled against the new authority.

This architecture re-entry path may originate from `$implement-ticket`, `$verify-spec`, `$review-spec`, `$to-remediation-specs`, or another lifecycle owner that encounters a genuine unresolved durable choice.

### Independent Root Closure Verification

`$verify-root-closure` is a special independent certification path for **Spec Review remediation tickets only**:

```text
$implement-ticket
    ↓ HUMAN authorization
fresh verifier subagent executes $verify-root-closure
    ↓ verifier result
$implement-ticket resumes
```

The human invocation authorizes independent verification. It does not transfer implementation ownership to the verifier and does not authorize the `$implement-ticket` main agent to certify its own work.

`$verify-root-closure` is a non-mutating leaf workflow. `$implement-ticket` fingerprints candidate repository state before dispatch and again after the verifier returns. Any repository-state change during verification invalidates the verifier result; the attempt is neither `PASS` nor `FAIL`.

A valid `FAIL` is **non-terminal**:

```text
$verify-root-closure FAIL
    ↓ ordinary return
$implement-ticket fixes all actionable in-scope findings
    ↓ rebuild proof
    ↓ HUMAN authorization
fresh verifier attempt
```

Every independent verification attempt requires fresh human authorization.

After a valid `PASS`, `$implement-ticket` remains the lifecycle owner. `PASS` alone is not ticket completion. `$implement-ticket` commits and pushes the verified candidate, persists Root Closure Evidence on the remediation ticket, reconciles the verified root state into the parent Spec Review's canonical Root Blocker Ledger and cumulative acceptance state, and only then closes the ticket.

When additional remediation tickets remain, the human selects the next frontier ticket. When remediation is complete, the Spec returns through `$verify-spec` and `$review-spec` again.

### Spec Completion

`$spec-merge-cleanup` is the only normal completion path after `$review-spec` passes its Exit Gate.

It requires the exact current **Spec Review Exit Receipt** and owns:

* merge or direct Spec closure;
* branch cleanup when applicable;
* closure of the conventional Spec Review issue;
* reconciliation of every current Wayfinder governing the completing Spec.

Once review reaches a persistence point, a missing or duplicate conventional Spec Review issue is workflow drift; cleanup must fail closed rather than infer review authority.

A Wayfinder effort is reconciled as complete only when no unresolved Wayfinder decision/fog remains and every currently governed Derived and Remediation Spec is complete. Wayfinder closure is the durable delivery-complete marker. Provenance failure must not be guessed.

## Tracker Relationship Semantics

Use tracker hierarchy for **decomposition**, not for every lifecycle handoff.

Good parent/sub-issue relationships include:

```text
Wayfinder Map
    └─ Wayfinder Decision

Spec
    └─ Implementation Ticket

Spec Review
    └─ Review Remediation Ticket
```

A Wayfinder-to-Spec relationship is normally **planning provenance / lifecycle handoff**, not decomposition. Preserve it through the canonical Wayfinder/Spec provenance metadata rather than forcing it into parent/sub-issue hierarchy.

Likewise, promotion from an Intake item to Wayfinder is a lifecycle/provenance transition, not automatically a parent/sub-issue relationship.

Use blocking/dependency relationships for actual execution dependencies. Same-lineage dependency semantics remain with the existing lifecycle owner. `$project-delivery-management` owns semantics for dependencies crossing Wayfinder lineages and places them at the narrowest authoritative consumer/blocker artifacts; it delegates only native relationship mechanics to `$github-issue-dependencies`.

Do not infer lifecycle authority merely from hierarchy or dependency edges. Do not create dependencies to represent focus, priority, queue order, or WIP preference.

## GitHub Project Tracking

The public Polaris GitHub Project is an **operational projection** of the workflow, not a correctness authority or workflow engine.

The Project may expose fields such as:

* Artifact Type;
* Delivery State;
* Workflow State;
* Next Skill;
* Work Status;
* Intake State;
* Priority;
* Area;
* Root Blocker;
* Completed On.

Cross-skill rules:

* **Workflow State is a state machine, not a stage number.** Items may move backward or revisit a prior state when the skill lifecycle loops.
* **GitHub issue Open/Closed is not generally equivalent to Polaris workflow state.** Ticket closure may still leave its parent Spec active. Wayfinder closure is narrower and intentional: it is the durable delivery-complete marker and must be reversed before authoritative re-entry or proven governed incomplete work advances.
* **Next Skill names the next human lifecycle/HITL entry point.** Internal helpers such as `$to-remediation-specs`, `$to-remediation-tickets`, and `$review-spec-remediation` should not be presented as separate user-controlled board stages.
* **Project-delivery authorization overlays, rather than replaces, lifecycle routing.** Eligible-unfocused Wayfinder Maps use `Next Skill=$project-delivery-management`; Wayfinder-managed descendants preserve the lifecycle `Next Skill` for `In Focus`, `Eligible`, and `Denied`, while lifecycle-owned `None` remains `None`. `Delivery State` carries project-delivery authorization independently of `Workflow State` and `Next Skill`.
* **Durable tracker/repository artifacts remain authoritative.** Project fields must be derived from or reconciled against the same receipts, baselines, provenance, blocker ledgers, issue relationships, focused-set state, and issue state used by the skills.
* **Project drift must not change semantic workflow state.** If Project metadata disagrees with durable workflow evidence, repair the projection rather than changing the underlying lifecycle to match the board.
* **Project synchronization happens after the corresponding durable transition succeeds.** Do not let a board update create authority that the owning skill has not established.
* **Area and Priority are presentation metadata, not workflow authority.** A lifecycle owner supplies either only when it independently owns an intentional presentation change; otherwise `$project-tracking` preserves the current Project value verbatim, including blank.
* **Project synchronization failure is projection drift, not semantic rollback.** Report it and preserve the authoritative tracker/repository result; later workflow entry should reconcile the board from durable state.
* A lightweight auto-add label such as `workflow:tracked` may provide discovery/safety-net behavior, but labels and auto-add rules do not determine lifecycle correctness.

Do not configure generic issue-closed automation to mean `Workflow State = Complete` or `Work Status = Done` for Polaris.

## Skill Roles

Use role classification to reason about composition without maintaining a brittle catalog of every invocation edge.

### Lifecycle Owners

Lifecycle owners control a major phase and own transitions into the next phase. Examples include:

```text
$wayfinder
$to-specs
$to-tickets
$implement-ticket
$verify-spec
$review-spec
$spec-merge-cleanup
$architecture-remediation
```

### Project-Level Coordination Owner

```text
$project-delivery-management
```

This owner is not an additional lifecycle stage. Human invocations make discretionary focus choices; lifecycle owners invoke its guard/reconcile/dependency operations only where their own contracts prescribe internal composition.

### Internal Composition and Helper Skills

Helpers perform part of an already-authorized parent workflow and normally return their result to that parent. Examples include remediation helpers, tracker relationship helpers, architecture reviewers, wiki/document helpers, formatting, targeted verification, database migration support, and code-analysis utilities.

Examples:

```text
$to-remediation-specs
$to-remediation-tickets
$github-issue-dependencies
$review-spec-remediation
$review-architecture
$wiki-sync
$wiki-lint
$database-migrations
$format-code
$verify-code
$deduplicate-code
```

A helper should not jump directly into another lifecycle owner unless its contract explicitly owns that transition. Prefer returning structured state to the parent so the lifecycle owner performs any required Human Handoff.

### Independent Verifier

```text
$verify-root-closure
```

Independent verification must remain isolated from implementation/remediation ownership.

### Interactive / HITL Utilities

Interactive utilities may ask the user questions while remaining inside the current workflow. Examples include `$grilling`, `$domain-modeling`, and `$prototype`.

HITL inside a skill is not automatically a lifecycle handoff.

## Human Handoff Convention

Use a Human Handoff only at an intentional lifecycle or fresh-session boundary.

A handoff should:

1. state why the current lifecycle is stopping;
2. identify the next skill;
3. provide a copy-ready invocation using durable titles/URLs when available;
4. stop after the handoff;
5. avoid alternative continuation that bypasses the boundary.

Typical structure:

```text
⚠️ <why the current lifecycle must stop>

Please run:

$next-skill - <Durable Artifact Title> (<URL>)
```

Do not add a Human Handoff solely because the target has `allow_implicit_invocation: false` or another platform-specific invocation gate.

## Return Semantics

Returning from an invoked child to its caller is ordinary workflow continuation and requires no Human Handoff.

Examples:

```text
$to-tickets
    ↓
$to-remediation-tickets
    ↓ result
$to-tickets resumes
```

```text
$review-spec
    ↓
$review-spec-remediation
    ↓ result
$review-spec resumes or propagates the child's terminal lifecycle result
```

Avoid handoff ping-pong such as:

```text
parent → HUMAN → child → HUMAN → parent
```

when the child is only performing internal work for the parent.

## Durable Workflow State

Correctness-critical state must survive fresh sessions and agent context loss.

Prefer durable repository or tracker artifacts over conversational memory whenever later workflow stages depend on exact state.

Examples include:

* Wayfinder source/remediation provenance and Spec handoff metadata;
* Spec baseline metadata;
* Ticket branch and Ticket baseline;
* Spec Verification Receipt;
* Spec Review Exit Receipt;
* Root Blocker Ledger;
* cumulative acceptance matrix;
* Pending Review Remediation packet;
* Root Closure Evidence;
* Root Closure Reconciliation.

A durable intermediate artifact may remain valuable even when both producing and consuming skills are internal composition.

Do not remove durable state merely because a former Human Handoff was removed. First determine whether the artifact also provides recovery, isolation, exact-state binding, auditability, or provenance.

GitHub Project fields are intentionally **not** correctness-critical durable authority. They are a synchronized operational view over the artifacts above.

## Parent / Child Ownership

Use these defaults unless a skill explicitly establishes a different contract:

* **Parent owns lifecycle routing.** A helper reports state upward; the lifecycle owner decides whether to continue, stop, or issue a Human Handoff.
* **Child owns its bounded procedure.** The parent should not duplicate the child's internal algorithm.
* **Return is ordinary control flow.** A child result resumes the parent without new authorization.
* **Parent owns commit scope when declared.** Repository-writing child skills contribute their mutations to the parent's commit when the parent workflow establishes commit ownership.
* **Children do not invent lifecycle transitions.** If a helper detects a condition requiring an upstream or sideways lifecycle change, return that condition to the parent unless the helper explicitly owns the transition.

Example:

```text
$to-remediation-tickets detects architecture-blocked root
    ↓
returns architecture-blocked result
    ↓
$to-tickets owns the Human Handoff to the appropriate review lifecycle
```

## Verification Independence

Independent verification must not collapse into implementation.

For `$verify-root-closure` specifically:

* the verifier is fresh;
* the verifier is non-mutating;
* it does not delegate;
* it does not repair failures;
* it returns a consolidated verdict only after its bounded scan;
* repository state is deterministically fingerprinted before and after dispatch;
* any mutation invalidates the attempt rather than becoming verifier-owned implementation.

A failed verifier result returns implementation ownership to `$implement-ticket`; it does not create a new lifecycle owner or terminate an otherwise actionable remediation ticket.

The exact fingerprint algorithm and dispatch protocol belong in `$implement-ticket` and `$verify-root-closure`; do not duplicate them here.

## Adding or Modifying Skills

Before adding or changing a cross-skill edge, answer these questions in order:

1. **Who owns the current lifecycle stage?**
2. **Is the target performing internal composition or starting a new lifecycle stage?**
3. **Does the human make a meaningful decision, authorization, or selection at this edge?**
4. If **yes**, use a Human Handoff.
5. If **no**, invoke the child directly.
6. **Does the child return to its caller?** If yes, resume the caller directly.
7. **Can this workflow legitimately re-enter an earlier lifecycle state?** Model that loop explicitly rather than assuming forward-only progression.
8. **Does correctness require durable state across sessions?** Persist it before relying on transient context.
9. **Who owns repository/tracker mutations and commits?** Keep ownership explicit.
10. **Who owns lifecycle routing when the child detects a blocker?** Prefer the parent lifecycle owner.
11. **Does the change preserve reviewer/verifier independence?** Never trade independence for convenience.
12. **Does Project tracking need synchronization?** Update it only as a projection of the durable transition and never make it the semantic source of truth.
13. **Does the transition preserve the durable artifact ownership contract?** In particular, reuse the one conventional Spec Review issue across clean review, remediation, and re-review rather than omitting it or creating one issue per pass.

When changing an existing skill, preserve unrelated behavior. Cross-skill governance changes should be lean and surgical.

## Anti-Patterns

Avoid these patterns:

### Linear Pipeline Assumption

```text
wayfinder → specs → tickets → implementation → verification → review
```

is the happy path, not a guarantee that work can only move forward.

Architecture discovery and review remediation may legitimately loop back through earlier lifecycle owners.

### Duplicate or Parent-Owned Spec Review State

Every reviewed Spec uses exactly one conventional `Spec Review:` issue as the durable owner of review/remediation state and the final Exit Receipt.

Do not create one review issue per pass, omit the conventional review issue on a clean review, or persist the final Exit Receipt on the parent Spec.

### Project Board as Workflow Authority

Do not use Project fields, board columns, labels, or generic automation as proof that a receipt, baseline, blocker, approval, verification, or lifecycle transition exists.

Reconcile Project state from durable workflow artifacts instead.

### GitHub Open / Closed as Lifecycle State

Do not infer `Complete`, `Ready to Spec`, `Ready to Verify`, or another workflow state solely from whether an issue is open or closed.

Issue state and Polaris lifecycle state answer different questions. Wayfinder closure is a specific delivery-complete marker established by its owning lifecycle, not a generic substitute for workflow-state derivation.

### Provenance as Hierarchy

Do not force every Wayfinder→Spec or Intake→Wayfinder handoff into parent/sub-issue hierarchy. Use hierarchy for decomposition and preserve lifecycle provenance through its owning durable metadata.

### Metadata-Driven Handoffs

```text
allow_implicit_invocation=false
    ⇒ Human Handoff
```

This is not a valid lifecycle rule by itself.

### Handoff Ping-Pong

```text
parent → HUMAN → helper → HUMAN → parent
```

when the helper is simply part of the parent's work.

### Child-Owned Sideways Routing

```text
helper detects blocker
    ↓
helper independently jumps to unrelated lifecycle owner
```

Prefer returning the blocker to the parent lifecycle owner.

### Conversational State as Durable Authority

Do not rely on prior-session memory for branch identity, baselines, review findings, closure state, or other correctness-critical workflow inputs when durable recovery is possible.

### README Procedure Duplication

Do not copy detailed commands, templates, acceptance algorithms, or skill-specific procedures into this README. Link responsibility to the owning skill instead.

### Automatic Lifecycle Continuation

Do not automatically continue into a stage intentionally designed for user selection, authorization, independent review, certification, merge/cleanup, or another fresh-session boundary.