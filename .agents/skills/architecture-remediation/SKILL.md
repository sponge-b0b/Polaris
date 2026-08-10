---
name: architecture-remediation
description: Route newly discovered unresolved architecture blockers back into the existing Wayfinder effort. Recover workflow lineage, create or reuse one linked Wayfinder decision ticket per independent blocker, and halt for a Human Handoff Intercept to `$wayfinder`.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# Architecture Remediation

This skill is explicitly invoked when a workflow such as `$implement-ticket` or `$review-spec` cannot continue because of one or more unresolved architecture blockers.

This is a **routing workflow**. Do not resolve architecture, modify implementation, amend the spec, or create a new Wayfinder map here.

## 1. Capture the Architecture Blockers

Use the caller-provided context to identify every independent unresolved architecture blocker discovered at the stopping point.

A blocker may be:

* an unresolved material architecture decision;
* a blocking `[source-conflict]` among applicable architectural authorities;
* current architectural authority invalidating architecture the blocked work depends on.

For each blocker capture:

* the specific unresolved question or conflict;
* evidence establishing it;
* why it is material or blocking;
* affected entities, owners, boundaries, canonical paths, dependency directions, or lifecycle responsibilities;
* governing ADR/doc references already known;
* source ticket or review finding when applicable.

Also capture:

* parent spec;
* Spec Review issue when applicable.

Preserve the caller's evidence. Do not invent an architectural answer.

De-duplicate by underlying architectural question. Multiple symptoms or evidence examples of the same unresolved issue produce one blocker; independent unresolved questions remain separate.

## 2. Resolve the Existing Wayfinder Effort

Read the parent spec and recover its Wayfinder source provenance.

Prefer the spec's explicit Wayfinder provenance marker:

```html
<!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision> -->
```

If the marker is absent, use another explicit, unambiguous tracker relationship when available.

If the originating Wayfinder map cannot be determined reliably, halt and report that its provenance must be recovered. Do not guess or create a replacement map.

The blockers belong to the existing Wayfinder map unless one is genuinely outside that map's destination. If so, report it separately rather than silently creating another map.

## 3. Create or Reuse Decision Tickets

For each independent blocker, inspect the existing Wayfinder map's open child issues before creating anything.

If an open child already represents the same unresolved architecture question, reuse it.

Otherwise create exactly one new child decision issue for that blocker under the existing Wayfinder map using the repository's configured Wayfinding operations.

Use `wayfinder:grilling` unless the caller already established another Wayfinder ticket type.

Use this body shape, including only relationships that exist:

```markdown
**Parent Wayfinder:** #<wayfinder_map>
**Parent Spec:** #<spec_issue>
**Source Ticket:** #<source_ticket>
**Spec Review:** #<spec_review_issue>

## Question

<specific unresolved architecture question or authority conflict>

## Discovery Context

<caller-provided evidence and why the blocked work cannot proceed, including
affected ownership, canonical path, boundary, dependency direction, lifecycle
responsibility, or conflicting architectural authorities>
```

`Parent Wayfinder` and `Parent Spec` are required.

`Source Ticket` and `Spec Review` are optional. Omit them when no such relationship exists.

Do not include a proposed architectural resolution as though it were decided.

Do not create duplicate decision tickets merely because the same blocker was surfaced by multiple callers or at multiple workflow stages.

## 4. Human Handoff Intercept

After every blocker has a corresponding open Wayfinder decision ticket, halt the current workflow.

Present all unresolved decision tickets, then identify the next one to work.

Use:

> ⚠️ **Work is blocked by unresolved architecture.**
>
> The following decision tickets now represent the unresolved blockers under the existing Wayfinder map:
>
> * **`<Decision Ticket 1 Title> (<URL>)`**
> * **`<Decision Ticket 2 Title> (<URL>)`**
>
> Please continue with:
>
> ```
> $wayfinder - <Next Decision Ticket Title> (<URL>)
> ```

When only one decision ticket exists, present only that ticket.

Do not continue implementation, review remediation, or spec amendment until the applicable Wayfinder decisions are resolved and the map's route is clear.

`$wayfinder` owns decision sequencing. Resolve one decision ticket at a time; after each resolution, the map determines whether another open decision remains or the route can continue to `$to-specs`.

## Completion

This skill is complete when:

* the existing Wayfinder map has been resolved;
* every independent caller-provided architecture blocker is represented by exactly one open decision ticket, either reused or created;
* no duplicate decision tickets were introduced; and
* the Human Handoff Intercept has been presented.

`$wayfinder` owns resolution of those decisions and reconciliation of authoritative architecture records.

After the required decisions are resolved and the route is clear, `$wayfinder` hands the updated map to `$to-specs`; `$to-specs` determines whether normal creation or `$to-remediation-specs` applies.
