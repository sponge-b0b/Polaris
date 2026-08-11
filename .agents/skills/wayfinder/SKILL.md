---
name: wayfinder
description: Plan a huge chunk of work — more than one agent session can hold — as a shared map of decision tickets on your issue tracker, and resolve them one at a time until the way to the destination is clear.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# Wayfinder

A loose idea has arrived — too big for one agent session, and wrapped in fog: the way from here to the **destination** isn't visible yet. Wayfinding is about finding that way, not charging at the destination. This skill charts the way as a **shared map** on the repo's issue tracker, then works its **decision tickets** — questions whose resolution is a decision, not slices of a build to execute — one at a time until the route is clear.

The destination varies per effort, and naming it is the first act of charting — it shapes every ticket. It might be a spec to hand off and iterate on, a decision to lock before planning starts, or a change made in place like a data-structure migration. The map is domain-agnostic — engineering work, course content, whatever fits the shape.

## Plan, don't do

Wayfinder is **planning** by default: each ticket resolves a decision, and the map is done when the way is clear — nothing left to decide before someone goes and does the thing.

The pull to just do the work is usually the signal you've reached the edge of the map and it's time to hand off.

An effort can override this in its **Notes** by carrying execution into the map itself, but absent that, produce decisions, not deliverables.

## Resolve Architecture Before Handoff

For software work that materially affects architecture, use the Living Entity Wiki and its authoritative sources during distillation rather than leaving architectural questions for specification or implementation.

Classify the impact as:

```text
none | conforming | extending | changing | retiring
```

Treat unresolved material architecture questions as decision tickets.

Before the route is considered clear:

* identify affected entities and applicable invariants, decisions, rejections, and boundaries;
* resolve conflicts or intended architecture changes with the owner;
* route durable decisions through `$to-adr-doc`;
* route new non-ADR architecture documentation through `$to-doc`;
* route reclassification of existing non-ADR documentation through `$classify-doc`;
* invoke `$wiki-sync` when the resulting authoritative change requires derived wiki maintenance.

Do not duplicate those skills' lifecycle rules here.

Reconciling architectural decision records is part of resolving the map, not implementing the destination.

### Architecture Implementability Closure

Architectural consistency alone does not make the route clear.

For every materially affected canonical contract, authority path, dependency boundary, or lifecycle, confirm that accepted architecture determines enough durable semantics to implement it without inventing another architectural choice.

Check, where applicable:

* canonical owner;
* required typed authority/input source;
* identity, version, or correlation key semantics;
* lifecycle ordering;
* persistence and retrieval responsibility;
* dependency direction and boundary ownership;
* authoritative consumers;
* fail-closed or failure semantics.

#### Concrete Contract Validation

When an architectural decision requires an **existing domain type, interface, durable record, authority object, or lifecycle component** to be produced or consumed, inspect that concrete contract far enough to verify the decision is realizable.

Where applicable, confirm:

* required inputs can exist at the lifecycle point where the architecture requires the artifact;
* the designated producer has an authoritative source for those inputs;
* required classifications or authority facts are determined or deterministically derivable from accepted authority;
* satisfying the existing contract does not require inventing a new durable meaning, input, authority source, classification, or lifecycle rule.

Do not require missing implementation wiring to already exist.

A missing factory, method, registration call, repository operation, or DI binding is implementation work when accepted architecture already determines the required semantics.

If the required artifact **cannot be validly produced or consumed at the specified boundary without inventing durable semantics**, architecture remains unresolved.

These are architectural questions only when their answers establish durable ownership, contracts, paths, boundaries, dependency direction, or lifecycle semantics.

Do **not** require Wayfinder to decide implementation details such as:

* class or method names;
* private helper structure;
* repository API shape when authority already determines its responsibility;
* SQL/query mechanics;
* local algorithms;
* ordinary code organization.

Ask:

> Could implementation proceed without inventing a durable architectural choice?

If **No**, architecture remains unresolved.

Create or retain the required Wayfinder decision/fog under the same map. When several missing questions jointly define one contract or lifecycle and materially constrain one another, treat them as one coupled decision rather than artificial separate decisions.

The route is not clear merely because every previously stated question has an answer.

## Repository Persistence

This invariant applies whenever `$wayfinder` creates or modifies repository files, whether during initial Wayfinding or later decision/re-entry work.

Before repository mutation, note any pre-existing working-tree changes so they are not absorbed into Wayfinder's commit.

When `$wayfinder` is the parent workflow, repository-writing child skills contribute their changes to the Wayfinder commit rather than creating separate commits.

If the current Wayfinder session creates or modifies repository files:

1. stage only files created or modified by the current Wayfinder work;
2. invoke `$conventional-commits`;
3. commit the Wayfinder-owned changes;
4. push and establish upstream if necessary:

   ```bash
   git push -u origin HEAD
   ```

Do not use `git add .` or otherwise stage unrelated working-tree changes.

Tracker-only changes do not require a repository commit.

If no repository files changed, skip commit and push.

If staging, commit, or push fails:

* do not mark the affected Wayfinder decision or map complete;
* do not close a decision whose repository-side architecture record has not been persisted;
* do not present a downstream Human Handoff;
* report the failure.

A Wayfinder decision that changes repository-side architectural records is not complete until those records are committed and pushed.

## Refer by Name

Every map and ticket is an issue, so it has a **name** — its title.

In everything the human reads — narration, the map's Decisions-so-far — refer to it by that name, never by a bare id, number, or slug.

The id and URL still travel inside the named link.

## The Map

The map is a single issue on this repo's issue tracker, labelled `wayfinder:map` — the canonical artifact. Its tickets are child issues of the map.

The map is an **index**, not a store. It lists decisions made and points at the tickets that hold their detail; a decision lives in exactly one place.

**Where the map, child tickets, blocking, and frontier queries physically live is tracker-specific.** The issue tracker should have been provided — run `$setup-matt-pocock-skills` if not.

Consult the tracker doc's "Wayfinding operations" section. If no tracker has been provided, default to the local-markdown tracker.

### The Map Body

The map is the low-resolution view loaded once per session. Open tickets are found by query.

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

Each ticket is a **child issue** of the map; the tracker's issue id is its identity.

Its body contains the question, sized to one agent session:

```markdown
## Question

<the decision or investigation this ticket resolves>
```

Each ticket carries a `wayfinder:<type>` label — one of `research`, `prototype`, `grilling`, `task`.

A session **claims** a ticket by assigning it to the dev driving the map before any work. An open, unassigned ticket is unclaimed.

Blocking uses the tracker's native dependency relationship. A ticket is **unblocked** when every ticket blocking it is closed; the **frontier** is the open, unblocked, unclaimed children.

The answer is recorded on resolution, not in the question body.

## Ticket Types

Every ticket is either **HITL** — human in the loop — or **AFK**, driven by the agent alone.

* **Research** (AFK): read documentation, third-party APIs, or local resources to surface a fact a decision waits on. Resolve through a `$research` subagent.
* **Prototype** (HITL): create a cheap concrete artifact via `$prototype` when reaction to behavior or shape will improve the decision.
* **Grilling** (HITL): use `$grilling` and `$domain-modeling`, one question at a time. Default case.
* **Task** (HITL or AFK): prerequisite work that must happen before a decision can be made.

## Fog of War

The map is deliberately incomplete.

Beyond live tickets lies **fog of war** — decisions or investigations that are visibly coming but cannot yet be stated precisely because they depend on unresolved questions.

Record this in **Not yet specified**.

**Fog or ticket?**

* **Ticket** when the question can already be stated precisely.
* **Not yet specified** when it cannot.

**Not yet specified** excludes what is already decided, already ticketed, or out of scope.

## Out of Scope

Fog gathers only toward the destination.

Work beyond the destination is **out of scope**, not fog.

When an existing ticket proves to sit beyond the destination, close it and leave one linked line in **Out of scope**. Do not place it in **Decisions so far**.

## Invocation

Two modes.

Either way, **never resolve more than one ticket per session**, except research tickets.

### Execution Lifecycle Guardrails

1. **Pre-Flight Metadata Audit**

   The moment a GitHub issue number or URL is supplied:

   ```bash
   gh issue view <ISSUE_NUMBER> --json labels,title,body
   ```

2. **Workflow Routing**

   * label `wayfinder:grilling` → `$grilling` and `$domain-modeling`;
   * otherwise route by Ticket Type through `$research`, `$prototype`, or AFK execution.

### Chart the Map

User invokes with a loose idea.

1. **Name the destination.** Run `$grilling` and `$domain-modeling`.
2. **Map the frontier.** Surface open decisions breadth-first. For software architecture, include unresolved architectural consequences and apply **Architecture Implementability Closure** before treating the route as clear. If no fog remains, continue the grilling session to completion instead of creating a map.
3. **Create the map** with `wayfinder:map`.
4. **Create currently specifiable tickets**, then wire blocking edges.
5. **Fire research subagents** for research tickets.
6. **Persist repository artifacts** through **Repository Persistence** when applicable.
7. Stop. Charting does not hand-resolve tickets.

The same persistence rule applies when charting collapses into a single `$grill-with-docs` session.

### Work Through the Map

User invokes with a map or decision ticket.

If given a ticket, resolve its parent Wayfinder map using the tracker's native relationship or explicit `Parent Wayfinder` metadata, then treat that ticket as the named decision.

1. Load the **map**, not every ticket body.
2. Choose the named ticket or first frontier ticket and **claim it** before work.
3. Resolve it. Fetch related ticket detail only as needed. Use `$grilling` and `$domain-modeling` when appropriate. For architectural decisions, apply **Resolve Architecture Before Handoff** and **Architecture Implementability Closure**.
4. **Persist the resolution**:

   * reconcile required authoritative architecture records;
   * if repository files changed, complete **Repository Persistence**;
   * only after persistence succeeds, post the resolution comment, close the ticket, and append its context pointer to **Decisions so far**.
5. Add newly surfaced decisions, wire dependencies, graduate newly specifiable fog, and move newly out-of-scope work. If the decision invalidates other map state, update or delete affected tickets.

### Post-Resolution Gate

After every resolved decision, **re-evaluate the parent map before ending the session**, including re-entry into an already-closed map.

Confirm:

* no open decision tickets remain;
* **Not yet specified** contains no unresolved in-scope fog;
* no material architecture question remains unresolved;
* **Architecture Implementability Closure passes for materially affected architecture**;
* required authoritative architecture records are reconciled;
* the new decision has not left stale or contradictory map state or affected prior decisions unreconciled;
* all Wayfinder-owned repository changes are committed and pushed.

When a new decision supersedes or invalidates an earlier decision, preserve the historical resolution but update affected map/ticket state enough to make the supersession explicit. Do not leave stale guidance looking current.

A closed map or existing derived Spec does **not** waive this gate.

If another unresolved decision, missing implementability choice, or newly specifiable fog remains, continue routing through the map rather than presenting a downstream handoff.

The route is not clear while:

* decision tickets or in-scope fog remain;
* a material architecture question remains unresolved;
* implementation of an affected canonical contract/path/lifecycle would still require inventing a durable architectural choice;
* authoritative records remain unreconciled;
* affected prior map state remains contradictory or stale;
* Wayfinder-owned repository changes remain uncommitted or unpushed.

When the Post-Resolution Gate passes and the destination is an implementation specification, halt with a Human Handoff Intercept:

> ✅ **Wayfinder route is clear.**
>
> Please run:
>
> ```
> $to-specs - <Wayfinder Map Title> (<Map URL>)
> ```

Always hand `$to-specs` the **Wayfinder map**, never an individual decision ticket or derived spec.

`$to-specs` owns deciding whether this creates a new spec or delegates an existing-spec update to `$to-remediation-specs`.

The user may run unblocked tickets in parallel, so expect other sessions to edit the tracker concurrently.
