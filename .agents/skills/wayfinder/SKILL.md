---
name: wayfinder
description: Plan a huge chunk of work — more than one agent session can hold — as a shared map of decision tickets on your issue tracker, and resolve them one at a time until the way to the destination is clear.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

A loose idea has arrived — too big for one agent session, and wrapped in fog: the way from here to the **destination** isn't visible yet. Wayfinding is about finding that way, not charging at the destination. This skill charts the way as a **shared map** on the repo's issue tracker, then works its **decision tickets** — questions whose resolution is a decision, not slices of a build to execute — one at a time until the route is clear.

The destination varies per effort, and naming it is the first act of charting — it shapes every ticket. It might be a spec to hand off and iterate on, a decision to lock before planning starts, or a change made in place like a data-structure migration. The map is domain-agnostic — engineering work, course content, whatever fits the shape.

## Plan, don't do

Wayfinder is **planning** by default: each ticket resolves a decision, and the map is done when the way is clear — nothing left to decide before someone goes and does the thing. The pull to just do the work is usually the signal you've reached the edge of the map and it's time to hand off. An effort can override this in its **Notes** — carrying execution into the map itself — but absent that, produce decisions, not deliverables.

## Resolve architecture before handoff

For software work that materially affects architecture, use the Living Entity Wiki and its authoritative sources during distillation rather than leaving architectural questions for specification or implementation.

Classify the impact as:

```text
none | conforming | extending | changing | retiring
```

Treat unresolved material architecture questions as decision tickets. Before the route is considered clear:

* identify affected entities and applicable invariants, decisions, rejections, and boundaries;
* resolve conflicts or intended architecture changes with the owner;
* route durable decisions through `$to-adr-doc`;
* route new non-ADR architecture documentation through `$to-doc`;
* route reclassification of existing non-ADR documentation through `$classify-doc`;
* invoke `$wiki-sync` when the resulting authoritative change requires derived wiki maintenance.

Do not duplicate those skills' lifecycle rules here. Reconciling architectural decision records is part of resolving the map, not implementing the destination.

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

## Refer by name

Every map and ticket is an issue, so it has a **name** — its title. In everything the human reads — narration, the map's Decisions-so-far — refer to it by that name, never by a bare id, number, or slug. A wall of `#42, #43, #44` is illegible; names read at a glance. The id and URL don't vanish — a name wraps its link — but they ride *inside* the name, never stand in for it.

## The Map

The map is a single issue on this repo's issue tracker, labelled `wayfinder:map` — the canonical artifact. Its tickets are child issues of the map.

The map is an **index**, not a store. It lists the decisions made and points at the tickets that hold their detail; a decision lives in exactly one place — its ticket — so the map never restates it, only gists it and links.

**Where the map, its child tickets, blocking, and frontier queries physically live is tracker-specific.** The issue tracker should have been provided to you — run `$setup-matt-pocock-skills` if not. Consult the tracker doc's "Wayfinding operations" section for how *this* repo expresses them. If no tracker has been provided, default to the local-markdown tracker.

### The map body

The whole map at low resolution, loaded once per session. Open tickets are **not** listed — they are open child issues, found by query.

```markdown
## Destination

<what reaching the end of this map looks like — the spec, decision, or change this effort is finding its way to. One or two lines; every session orients to it before choosing a ticket.>

## Notes

<domain; skills every session should consult; standing preferences for this effort>

## Decisions so far

<!-- the index — one line per closed ticket: enough to judge relevance, then zoom the link for the detail the ticket holds -->

- [<closed ticket title>](link) — <one-line gist of the answer>

## Not yet specified

<!-- see "Fog of war": in-scope fog you can't ticket yet; graduates as the frontier advances -->

## Out of scope

<!-- see "Out of scope": work ruled beyond the destination; closed, never graduates -->
```

### Tickets

Each ticket is a **child issue** of the map; the tracker's issue id is its identity. Its body is the question, sized to one 100K token agent session:

```markdown
## Question

<the decision or investigation this ticket resolves>
```

Each ticket carries a `wayfinder:<type>` label — one of `research`, `prototype`, `grilling`, `task` (see [Ticket Types](#ticket-types)).

A session **claims** a ticket by assigning it to the dev driving the map, **first**, before any work, so concurrent sessions skip it. That assignee *is* the claim: an open, unassigned ticket is unclaimed.

Blocking uses the tracker's **native** dependency relationship — essential because it renders the frontier *visually* in the tracker's own UI, so the human sees what's takeable without opening the map. Only a tracker that lacks native blocking falls back to a body convention. A ticket is **unblocked** when every ticket blocking it is closed; the **frontier** is the open, unblocked, unclaimed children — the edge of the known.

The answer isn't part of the body — it's recorded on resolution (see [Work through the map](#work-through-the-map)). Assets created while resolving a ticket are linked from the issue, not pasted in.

## Ticket Types

Every ticket is either **HITL** — human in the loop, worked *with* a human who speaks for themselves — or **AFK**, driven by the agent alone. A HITL ticket only resolves through that live exchange; the agent never stands in for the human's side of it.

* **Research** (AFK): Reading documentation, third-party APIs, or local resources like knowledge bases to surface a fact a decision waits on. Resolved by a `$research` **subagent**. Use when knowledge outside the current working directory is required.
* **Prototype** (HITL): Raise the fidelity of the discussion by making a cheap, rough, concrete artifact to react to — an outline, a rough take, a stub, or UI/logic code via `$prototype`. Links the prototype as an asset. Use when "how should it look" or "how should it behave" is the key question.
* **Grilling** (HITL): Conversation via `$grilling` and `$domain-modeling`, one question at a time. The default case.
* **Task** (HITL or AFK): Manual work that must happen before a *decision* can be made — nothing to decide, prototype, or research, but the discussion is blocked until it's done. The agent drives it alone where it can; otherwise it hands the human a precise checklist. Resolved when the work is done.

## Fog of war

The map is *deliberately* incomplete: don't chart what you can't yet see. Beyond the live tickets lies the **fog of war** — the dim view of decisions and investigations you can tell are coming but can't yet pin down, because they hang on questions still open. Resolving a ticket clears the fog ahead of it, graduating whatever's now specifiable into fresh tickets — one at a time, until the way to the destination is clear and no tickets remain.

The map's **Not yet specified** section is where that dim view is written down: the suspected question, the area to revisit later. It's the undiscovered frontier *toward* the destination — everything here is in scope, just not sharp enough to ticket.

**Fog or ticket?** The test is whether you can state the question precisely now — *not* whether you can answer it now.

* **Ticket when** the question is already sharp — even if it's blocked and you can't act on it yet.
* **Not yet specified when** you can't yet phrase it that sharply.

**Not yet specified** excludes what's already decided, what's already a live ticket, and what's out of scope.

## Out of scope

Fog only ever gathers *toward* the destination. The destination fixes the scope, so work beyond it is **out of scope** — it isn't fog, and it doesn't belong in **Not yet specified**.

Out-of-scope work never graduates — the frontier stops at the destination — so it returns only if the destination is redrawn, and then as a fresh effort, not a resumption.

Ruling something out of scope is a scoping act, not a step on the route. When an existing ticket turns out to sit past the destination, close it and leave one line in **Out of scope** linking the closed ticket. It stays out of **Decisions so far**.

## Invocation

Two modes. Either way, **never resolve more than one ticket per session** — with the exception of research tickets.

### Execution Lifecycle Guardrails

1. **Pre-Flight Metadata Audit**: The exact moment you are assigned a GitHub issue number or URL, run an initial metadata pull before analyzing the text description:

   ```bash
   gh issue view <ISSUE_NUMBER> --json labels,title,body
   ```

2. **Workflow Routing**:

   * **IF** the labels contain `"wayfinder:grilling"`, proceed via `$grilling` and `$domain-modeling`, one question at a time.
   * **ELSE** based on the Ticket Type, proceed via `$research`, `$prototype`, or route to **AFK** mode and execute the task autonomously using local tools as needed.

### Chart the map

User invokes with a loose idea.

1. **Name the destination.** Run a `$grilling` and `$domain-modeling` session to pin down what this map is finding its way to.
2. **Map the frontier.** Grill again, breadth-first, surfacing the open decisions and first steps takeable now. For software architecture, include unresolved architectural consequences. If this surfaces no fog, continue the grilling session to completion instead; the effort collapses into a single `$grill-with-docs` session ending with the destination reached rather than a map.
3. **Create the map** (label `wayfinder:map`): Destination and Notes filled in, Decisions-so-far empty, fog sketched into **Not yet specified**.
4. **Create the tickets you can specify now** as child issues of the map, then wire blocking edges in a second pass.
5. **Fire the research subagents.** For each `research` ticket created, spin up a `$research` subagent to resolve it in parallel, capturing findings on a throwaway `research/<name>` branch with a context pointer from the ticket.
6. **Persist repository artifacts.** If this Wayfinder session created or modified repository files, complete **Repository Persistence** before declaring the session complete.
7. Stop — charting is one session's work; it hand-resolves nothing.

The same persistence rule applies when charting collapses into a single `$grill-with-docs` session: repository artifacts must be committed and pushed before that session is considered complete.

### Work through the map

User invokes with a map or one of its decision tickets. If given a ticket, resolve its parent Wayfinder map using the tracker's native relationship or explicit `Parent Wayfinder` metadata, then treat that ticket as the named decision.

1. Load the **map** — the low-res view, not every ticket body.
2. Choose the ticket. If the user named one, use it. Otherwise take the first frontier ticket in order. **Claim it**: assign it to yourself before any work.
3. Resolve it — **zoom as needed**: fetch the full body of any related or closed ticket on demand; invoke the skills the `## Notes` block names. If in doubt, use `$grilling` and `$domain-modeling`. For architectural decisions, apply **Resolve architecture before handoff**.
4. **Persist the resolution.**

   * reconcile any required authoritative architecture records;
   * if repository files changed, complete **Repository Persistence**;
   * only after required repository persistence succeeds, post the answer as a resolution comment, close the issue, and append its context pointer to the map's **Decisions so far**.
5. Add newly surfaced tickets and wire dependencies; graduate newly specifiable fog; move newly out-of-scope work out of the frontier. If the decision invalidates other parts of the map, update or delete those tickets.

### Post-Resolution Gate

After every resolved decision, **re-evaluate the parent map before ending the session**, including re-entry into an already-closed map.

Confirm:

* no open decision tickets remain;
* **Not yet specified** contains no unresolved in-scope fog;
* no material architecture question remains unresolved;
* required authoritative architecture records are reconciled;
* the new decision has not left stale or contradictory map state or affected prior decisions unreconciled;
* all Wayfinder-owned repository changes are committed and pushed.

When a new decision supersedes or invalidates an earlier decision, preserve the historical resolution but update the affected map/ticket state enough to make the supersession explicit. Do not leave stale guidance looking current.

A closed map or existing derived Spec does **not** waive this gate.

If another unresolved decision or newly specifiable fog remains, continue routing through the map rather than presenting a downstream handoff.

The route is not clear while decision tickets or in-scope fog remain, while any material architecture question remains unresolved, while a resolved architectural decision still requires reconciliation with its authoritative records, while affected prior map state remains contradictory or stale, or while Wayfinder-owned repository changes remain uncommitted or unpushed.

When the Post-Resolution Gate passes and the destination is an implementation specification, halt with a Human Handoff Intercept:

> ✅ **Wayfinder route is clear.**
>
> Please run:
>
> ```
> $to-specs - <Wayfinder Map Title> (<Map URL>)
> ```

Always hand `$to-specs` the **Wayfinder map**, never an individual decision ticket or derived spec. `$to-specs` owns deciding whether this creates a new spec or delegates an existing-spec update to `$to-remediation-specs`.

The user may run unblocked tickets in parallel, so expect other sessions to be editing the tracker concurrently.
