---
name: wayfinder
description: Plan a huge chunk of work — more than one agent session can hold — as a shared map of decision tickets on your issue tracker, and resolve them one at a time until the way to the destination is clear.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# Wayfinder

A loose idea has arrived — too big for one agent session, and wrapped in fog: the way from here to the **destination** isn't visible yet.

Wayfinding finds that route rather than charging at the destination. It charts a shared map of decision tickets, then resolves those decisions one at a time until the route is clear.

The destination may be a Spec, a durable decision, or a change made in place. Naming it is the first act of charting because it determines scope.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting.

Prior-session summaries or remembered conclusions are routing context only and must not substitute for durable evidence.

If required durable state cannot be recovered, report the missing artifact rather than infer it.

## Project Delivery Focus Guard

`$project-delivery-management` owns project-level delivery focus. `$wayfinder` owns Wayfinder planning and must not copy, infer, or persist competing focus state.

The guard applies differently to the two invocation modes:

* **Chart the Map** is capture/planning and is not focus-gated. A new map may be charted while another Wayfinder is focused. Charting must not establish, switch, broaden, or otherwise change focus, and chart-time research needed to form the map remains allowed.
* **Work Through the Map** is substantive advancement and is focus-gated before any durable mutation, including claiming a decision ticket.

Never create a native dependency merely to encode focus or queue preference. Dependency determines eligibility; focus determines intentional project WIP.

### Guard Before Substantive Wayfinder Work

When working through an existing map or decision ticket:

1. resolve the exact governing Wayfinder map from durable tracker relationships/metadata;
2. invoke `$project-delivery-management` `reconcile` so completed or directly ineligible focused maps are reduced before authorization;
3. invoke `$project-delivery-management` `guard <Wayfinder>`;
4. proceed only after the guard returns `PROJECT DELIVERY GUARD: ALLOWED`.

Handle other results without claiming or mutating the decision:

* `PROJECT DELIVERY GUARD: BLOCKED` → report the direct map blockers and stop;
* `PROJECT DELIVERY GUARD: FOCUS REQUIRED` with another focused Wayfinder/set → report the current focus and stop with the explicit human choices to continue current work, run `$project-delivery-management` `switch-focus <Wayfinder>`, or authorize an exact `$project-delivery-management` `parallel-focus <Wayfinder>...` set;
* `PROJECT DELIVERY GUARD: FOCUS REQUIRED` with an empty focused set → ask the human:

  > Establish <Wayfinder Map Title> as the project delivery focus and continue? (yes/no)

  Only an explicit `yes` authorizes invoking `$project-delivery-management` `focus <Wayfinder>` as the human focus decision for this session. Re-run the guard and require `ALLOWED` before continuing. `no` leaves focus empty and ends substantive Wayfinder work.

The empty-focus confirmation is the only focus establishment `$wayfinder` may facilitate. `$wayfinder` must never infer or perform a focus switch, parallel authorization, or broader focus change from its own invocation.

Read-only investigation required to resolve the governing map and project-delivery state is allowed before the guard. Do not claim a decision, post a Decision Analysis, mutate tracker/repository state, or resolve architecture before authorization succeeds.

### Reconcile After Durable Wayfinder Transitions

After a Wayfinder-owned transition that can affect project eligibility, focus validity, or lower-level actionability is durably persisted, invoke `$project-delivery-management` `reconcile` **after** that authoritative mutation succeeds.

Examples include:

* creating/charting a canonical Wayfinder map;
* closing/reopening a Wayfinder decision and updating the map's durable state;
* changing native dependency state owned by the Wayfinder lifecycle;
* any map closure/re-entry performed by the owning lifecycle.

Reconciliation may remove completed/directly ineligible focused maps but must never select a replacement. If reconciliation cannot recover valid project-delivery state, report the failure and do not present a downstream lifecycle handoff that depends on current focus.

A focused map that remains map-eligible but has no currently actionable lower-level decision work because narrower blockers remain is **focused-but-stalled**. Retain focus, surface the blockers, and do not promote them to a synthetic map blocker or silently switch/release focus.

## Mandatory Project Reconciliation

After a Wayfinder-owned tracker/repository transition is durable and after required `$project-delivery-management` reconciliation, invoke `$project-tracking` as prescribed internal composition **before** any Human Handoff or ordinary return.

Derive one reconciliation set from the same post-transition map/frontier state used for the handoff:

* an open Wayfinder map with unresolved decision work or in-scope fog → base `Wayfinder Map / Architecture Decision / $wayfinder / Ready`, unless the map itself has an open native blocker, in which case use `Wayfinder Map / Blocked / None / Blocked`;
* a Wayfinder map whose route is clear and whose next destination is specification → base `Wayfinder Map / Ready to Spec / $to-specs / Ready`;
* a newly created, reopened, or otherwise affected open Wayfinder decision with zero open native blockers → base `Wayfinder Decision / Architecture Decision / $wayfinder / Ready`;
* an affected open Wayfinder decision with one or more open native blockers → base `Wayfinder Decision / Blocked / None / Blocked`;
* a decision closed by this invocation → base `Wayfinder Decision / Complete / None / Done` with `Completed On` set to the authoritative closure date;
* a map closed by this invocation only when the Wayfinder lifecycle itself establishes map completion → base `Wayfinder Map / Complete / None / Done` with authoritative `Completed On`;
* any other formal artifact whose lifecycle or open-blocker state this Wayfinder transition changed.

Do not project `Spec Delivery`; `$to-specs` owns that transition after durable Spec handoffs exist. Do not infer map completion from the absence of a frontier when unresolved fog, architectural work, or an unfinished destination remains.

Supply current authoritative Project Delivery State separately from the base lifecycle projection. Preserve `Area` and `Priority` unless this invocation has separate authority to change them.

`$wayfinder` owns the affected-artifact set, decision/frontier reads, and base lifecycle states. `$project-tracking` owns validation, delivery overlay, and Project mutation. Project fields never determine route clarity, decision completion, or focus.

If Project synchronization fails, report `PROJECT TRACKING: DRIFT`. Do not roll back durable map/decision state and do not suppress an otherwise-authorized `$wayfinder` or `$to-specs` handoff.

## Plan, Don't Do

Wayfinder is **planning** by default.

Each ticket resolves a decision. The map is complete when nothing material remains to decide before downstream work can proceed.

The urge to implement is usually evidence that the map has reached its destination and should hand off.

An effort may explicitly carry execution inside its **Notes**, but otherwise produce decisions, not destination deliverables.

## Resolve Architecture Before Handoff

For software work that materially affects architecture, use the Living Entity Wiki and its authoritative sources during distillation rather than leaving architectural questions for specification or implementation.

Classify impact as:

```text
none | conforming | extending | changing | retiring
```

Treat unresolved material architecture questions as decision tickets.

Before the route is clear:

* identify affected entities and applicable invariants, decisions, rejections, and boundaries;
* resolve conflicts or intended architecture changes with the owner;
* route durable decisions through `$to-adr-doc`;
* route new non-ADR architecture documentation through `$to-doc`;
* route reclassification of existing non-ADR documentation through `$classify-doc`;
* invoke `$wiki-sync` when authoritative changes require derived wiki maintenance.

Do not duplicate those skills' lifecycle rules here.

Reconciling architectural records is part of resolving the map, not implementing the destination.

### Architecture Implementability Closure

Architectural consistency alone does not make the route clear.

For every materially affected canonical contract, authority path, dependency boundary, or lifecycle, confirm that accepted architecture determines enough durable semantics to implement it without inventing another architectural choice.

Check where applicable:

* canonical owner;
* required typed authority/input source;
* identity, version, or correlation-key semantics;
* lifecycle ordering;
* persistence and retrieval responsibility;
* dependency direction and boundary ownership;
* authoritative consumers;
* fail-closed/failure semantics.

#### Concrete Contract Validation

When a decision requires an existing domain type, interface, durable record, authority object, or lifecycle component to be produced or consumed, inspect that contract far enough to verify the decision is realizable.

Where applicable, confirm:

* required inputs can exist at the required lifecycle point;
* the designated producer has an authoritative source for them;
* required classifications or authority facts are established or deterministically derivable;
* satisfying the contract does not require inventing new durable meaning, authority, classification, or lifecycle semantics.

Do not require missing implementation wiring to already exist.

A missing factory, method, registration call, repository operation, or DI binding is implementation work when architecture already determines the semantics.

Architecture remains unresolved only when implementation would still have to invent a durable architectural choice.

Do **not** require Wayfinder to decide ordinary implementation details such as:

* class or method names;
* private helper structure;
* repository API shape when responsibility is already established;
* SQL/query mechanics;
* local algorithms;
* ordinary code organization.

Ask:

> Could implementation proceed without inventing a durable architectural choice?

If **No**, architecture remains unresolved.

Create or retain the necessary decision/fog under the same map.

When several missing choices jointly define one contract or lifecycle and materially constrain one another, treat them as one coupled decision rather than artificial separate decisions.

The route is not clear merely because every previously stated question has an answer.

## Repository Persistence

This invariant applies whenever `$wayfinder` creates or modifies repository files.

Before mutation, note pre-existing working-tree changes so they are not absorbed into Wayfinder's commit.

When `$wayfinder` is parent, repository-writing child skills contribute their changes to the Wayfinder commit rather than committing separately.

If repository files change:

1. stage only Wayfinder-owned files;
2. invoke `$conventional-commits`;
3. commit;
4. push and establish upstream when necessary:

```bash
git push -u origin HEAD
```

Do not use `git add .` when unrelated working-tree changes exist.

Tracker-only changes require no repository commit.

If no repository files changed, skip commit and push.

If staging, commit, or push fails:

* do not mark the affected decision or map complete;
* do not close a decision whose repository-side architectural record is unpersisted;
* do not present a downstream Human Handoff;
* report the failure.

A Wayfinder decision that changes repository-side architectural records is incomplete until those records are committed and pushed.

## Refer by Name

Every map and ticket is an issue with a title.

In human-facing narration and **Decisions so far**, refer to it by name rather than bare ID, number, or slug.

The ID and URL still travel inside the named link.

## The Map

The map is a single issue labelled `wayfinder:map` — the canonical artifact. Its tickets are child issues.

The map is an **index**, not a store. It lists decisions and points to the tickets holding their detail. A decision lives in exactly one place.

Tracker-specific storage and relationship mechanics come from the repository's configured issue-tracker documentation.

Run `$setup-matt-pocock-skills` if no tracker has been configured.

### Map Body

```markdown
## Destination

<what reaching the end of this map looks like>

## Notes

<domain; skills every session should consult; standing preferences>

## Decisions so far

- [<closed ticket title>](link) — <one-line gist>

## Not yet specified

<in-scope fog not yet sharp enough to ticket>

## Out of scope

<work ruled beyond the destination>
```

### Tickets

Each ticket is a child issue of the map; the tracker issue ID is its identity.

Its body contains the decision question:

```markdown
## Question

<the decision or investigation this ticket resolves>
```

Each ticket carries one:

```text
wayfinder:research
wayfinder:prototype
wayfinder:grilling
wayfinder:task
```

A session claims a ticket by assigning it to the developer driving the map before work.

An open, unassigned ticket is unclaimed.

Blocking uses the tracker's native dependency relationship.

A ticket is **unblocked** when every blocking ticket is closed. The **frontier** is the open, unblocked, unclaimed children.

Keep the ticket body as the decision question. Persist authored decision analysis and recommendations as issue comments; record the accepted answer in the final resolution comment.

## Ticket Types

Every ticket is either **HITL** — human in the loop — or **AFK**, driven by the agent alone.

A HITL ticket resolves only through the live exchange. **The agent must never infer, assume, or supply the human's decision.**

* **Research** (AFK): read documentation, third-party APIs, or local resources to surface a fact a decision waits on. Resolve through a `$research` subagent.
* **Prototype** (HITL): create a cheap concrete artifact via `$prototype` when reaction to behavior or shape will improve the decision.
* **Grilling** (HITL): use `$grilling` and `$domain-modeling`, one question at a time. Default case. For each decision question, provide the recommended answer, persist the required **Decision Analysis**, then explicitly ask **“Do you agree with this recommendation? (yes/no)”** and wait. `yes` accepts the recommendation. `no` keeps the current decision open and explores the disagreement before advancing. Never infer acceptance or resolve the ticket without an explicit user response.
* **Task** (HITL or AFK): prerequisite work that must happen before a decision can be made.

## Decision Analysis

For every HITL decision ticket, preserve the architectural journey in the ticket before asking the human to accept the recommendation.

After investigation is materially complete and before the explicit yes/no gate, post one authored issue comment beginning with:

```markdown
## Decision Analysis
```

The comment is a durable explanation of how the recommendation follows from repository evidence and architectural constraints. It is **not** a transcript and must not contain raw private scratchpad or chain-of-thought.

Include only sections that carry material information, normally drawn from:

```markdown
### Current State

<relevant implementation and current architecture>

### Future-State Constraints

<accepted-but-not-yet-realized decisions, related Specs/Wayfinders,
dependency chains, and reserved responsibilities that constrain this choice>

### Key Findings

<facts that materially shaped the recommendation>

### Alternatives Considered

<plausible alternatives, why they were plausible, and why they were
rejected or retained>

### Architectural Reasoning

<the concise argument connecting evidence, ownership, lifecycle,
dependency direction, authority, and tradeoffs to the recommendation>

### Recommendation

<the exact recommendation presented to the human>
```

Do not force empty headings or uniform length. A simple decision may need only a few paragraphs; a foundational architectural decision may need substantially more.

Preserve especially:

* evidence or lifecycle facts that were not obvious from the ticket question;
* relevant future-state constraints consulted under **Resolve Architecture Before Handoff**;
* plausible alternatives and why they were rejected;
* assumptions whose later invalidation could justify revisiting the decision;
* first-principles reasoning that prevents a future maintainer from mistaking a deliberate rejection for an overlooked option.

The recommendation in the `Decision Analysis` comment must match the recommendation presented in the live HITL exchange.

### Recommendation Revision

If the human rejects, challenges, or clarifies the recommendation and further analysis materially changes it, preserve history rather than rewriting the earlier comment.

Before presenting the revised yes/no gate, post a new issue comment beginning with:

```markdown
## Recommendation Revision
```

Record concisely:

* the earlier recommendation or assumption being revised;
* the challenge, new evidence, or concrete-contract finding that changed the analysis;
* why the previous approach no longer holds;
* the revised recommendation.

Then present that revised recommendation in the live exchange and ask the exact required yes/no question again.

Do not create a revision comment for mere wording cleanup that does not change the material recommendation.

After acceptance, keep the final resolution comment concise: record the accepted decision and point to the durable ADR/docs/commits as applicable rather than duplicating the full analysis.

## Fog of War

The map is deliberately incomplete.

Beyond live tickets lies **fog of war** — decisions or investigations that are visibly coming but cannot yet be stated precisely because they depend on unresolved questions.

Record this in **Not yet specified**.

### Fog or Ticket?

* **Ticket** when the question can already be stated precisely.
* **Not yet specified** when it cannot.

**Not yet specified** excludes what is already decided, ticketed, or out of scope.

## Out of Scope

Fog gathers only toward the destination.

Work beyond the destination is **out of scope**, not fog.

When an existing ticket proves to sit beyond the destination, close it and leave one linked line in **Out of scope**.

Do not place it in **Decisions so far**.

## Invocation

Two modes.

Either way, **never resolve more than one ticket per session**, except research tickets.

### Execution Lifecycle Guardrails

#### 1. Pre-Flight Metadata Audit

The moment a GitHub issue number or URL is supplied:

```bash
gh issue view <ISSUE_NUMBER> --json labels,title,body
```

#### 2. Workflow Routing

* `wayfinder:grilling` → `$grilling` and `$domain-modeling`;
* otherwise route by ticket type through `$research`, `$prototype`, or AFK execution.

HITL routing always preserves the **Ticket Types** human-decision invariant.

### Chart the Map

User invokes with a loose idea.

1. **Name the destination.** Run `$grilling` and `$domain-modeling`.
2. **Map the frontier.** Surface open decisions breadth-first. For software architecture, include unresolved architectural consequences and apply **Architecture Implementability Closure** before treating the route as clear.
3. If no fog remains, continue the grilling session to completion instead of creating a map.
4. Otherwise create the map with `wayfinder:map`.
5. Create currently specifiable tickets and wire blocking edges.
6. Fire research subagents for research tickets.
7. Persist repository artifacts through **Repository Persistence** when applicable.
8. After the map/ticket/dependency state is durable, invoke `$project-delivery-management` `reconcile`, then perform **Mandatory Project Reconciliation** for every created/affected formal artifact. Do not establish or change focus as part of charting.
9. Stop. Charting does not hand-resolve tickets.

The same persistence rule applies when charting collapses into a single `$grill-with-docs` session. A collapse that creates no Wayfinder map has no Wayfinder focus or formal Wayfinder artifact to reconcile.

### Work Through the Map

User invokes with a map or decision ticket.

If given a ticket, resolve its parent Wayfinder map using the tracker's native relationship or explicit `Parent Wayfinder` metadata, then treat that ticket as the named decision.

1. Load the **map**, not every ticket body.
2. Apply **Project Delivery Focus Guard** and require `PROJECT DELIVERY GUARD: ALLOWED` before claiming or mutating the decision.
3. Choose the named ticket or first frontier ticket and **claim it** before work.
4. Resolve it. Fetch related detail only as needed. Use `$grilling` and `$domain-modeling` when appropriate. For architecture, apply **Resolve Architecture Before Handoff** and **Architecture Implementability Closure**.
5. For a HITL decision, after investigation is materially complete, persist the required **Decision Analysis** comment before presenting the recommendation and explicit yes/no gate. If further exchange materially changes the recommendation, persist a **Recommendation Revision** before asking again.
6. Do not treat the recommendation as the user's decision. Obtain the explicit human response required by **Ticket Types** before resolution.
7. **Persist the resolution**:

   * reconcile required authoritative architecture records;
   * if repository files changed, complete **Repository Persistence**;
   * only after persistence succeeds, post the concise resolution comment, close the ticket, and append its context pointer to **Decisions so far**.
8. Add newly surfaced decisions, wire dependencies, graduate newly specifiable fog, and move newly out-of-scope work. If the decision invalidates other map state, update or delete affected tickets.
9. After all Wayfinder-owned tracker/repository mutations from this decision are durable, invoke `$project-delivery-management` `reconcile`, then perform **Mandatory Project Reconciliation** before the Post-Resolution Gate.

## Post-Resolution Gate

After every resolved decision, **re-evaluate the parent map before ending the session**, including re-entry into an already-closed map.

Confirm:

* no open decision tickets remain;
* **Not yet specified** contains no unresolved in-scope fog;
* no material architecture question remains unresolved;
* **Architecture Implementability Closure** passes for materially affected architecture;
* required authoritative architecture records are reconciled;
* required Decision Analysis and any material Recommendation Revision are durably recorded on the decision ticket;
* the new decision has not left stale or contradictory map state or affected prior decisions unreconciled;
* all Wayfinder-owned repository changes are committed and pushed;
* required project-delivery reconciliation completed successfully.

When a new decision supersedes or invalidates an earlier decision, preserve the historical resolution but update affected map/ticket state enough to make the supersession explicit.

A closed map or existing derived Spec does **not** waive this gate.

If another unresolved decision, missing implementability choice, or newly specifiable fog remains, the route is not clear.

Except for additional research tickets permitted by **Invocation**, do not resolve another ticket in the same session.

After updating the map, identify the current frontier and require **Mandatory Project Reconciliation** to reflect that same post-resolution state before emitting any handoff or returning:

* If one open, unblocked, unclaimed frontier ticket is available, halt with:

  > ✅ **Wayfinder decision resolved.**
  >
  > Please continue with:
  >
  > ```
  > $wayfinder - <Next Decision Ticket Title> (<Ticket URL>)
  > ```

* If multiple frontier tickets are available, output one copy-ready `$wayfinder` line per frontier ticket and let the user choose the next session. The user may run independent frontier tickets in parallel because they remain inside the same focused Wayfinder delivery scope.
* If open decision tickets remain but every one is blocked, keep the map focused when it remains map-frontier eligible, report `PROJECT DELIVERY: FOCUSED-BUT-STALLED`, surface the exact decision blockers, and stop. Do not create a map blocker or release/switch focus.
* If unresolved in-scope fog remains but no frontier ticket can yet be stated, report the remaining fog and stop. Do not present a downstream handoff.

Then stop.

The route is not clear while:

* decision tickets or in-scope fog remain;
* a material architecture question remains unresolved;
* implementation of an affected canonical contract/path/lifecycle would still require inventing a durable architectural choice;
* authoritative records remain unreconciled;
* affected prior map state remains contradictory or stale;
* Wayfinder-owned repository changes remain uncommitted or unpushed;
* project-delivery reconciliation required by the current transition remains unresolved.

When the Post-Resolution Gate passes and the destination is an implementation specification, require **Mandatory Project Reconciliation** to project the map as `Ready to Spec` from this same clear-route state, then halt with a Human Handoff Intercept:

> ✅ **Wayfinder route is clear.**
>
> Please run:
>
> ```
> $to-specs - <Wayfinder Map Title> (<Map URL>)
> ```

Always hand `$to-specs` the **Wayfinder map**, never an individual decision ticket or derived Spec.

`$to-specs` owns deciding whether this creates a new Spec or delegates an existing-Spec update to `$to-remediation-specs`.

The project-delivery focus remains on the governing Wayfinder across this handoff; route clarity does not release or switch focus.

The user may run unblocked tickets in parallel, so expect other sessions to edit the tracker concurrently.
