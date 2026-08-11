---
name: architecture-remediation
description: Route unresolved architecture blockers back into the existing Wayfinder effort, creating or reusing one decision ticket per independent blocker and handing resolution to `$wayfinder`.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# Architecture Remediation

Use when `$implement-ticket`, `$review-spec`, or another workflow cannot continue because of unresolved architecture.

This is a **routing workflow**. Do not resolve architecture, modify implementation, amend a Spec, or create a new Wayfinder map here.

## 1. Capture the Blocker Set

Use the caller-provided context to capture every independent unresolved architecture blocker at the stopping point.

A blocker includes:

* an unresolved material architecture decision;
* a blocking `[source-conflict]` among applicable authorities;
* current authority invalidating architecture required by the work;
* a required Spec, review, or remediation obligation that cannot be implemented without violating or changing current architectural authority.

For each blocker capture:

* unresolved question/conflict;
* caller evidence;
* material consequence;
* affected owners, contracts, canonical paths, boundaries, dependencies, or lifecycle responsibilities;
* governing ADR/doc references already known;
* the exact blocked requirement/acceptance obligation when applicable;
* source ticket or review finding.

Also capture:

* parent Spec;
* Spec Review issue when applicable.

Preserve caller evidence and terminology. Do not invent a resolution.

De-duplicate by underlying architectural question. Multiple symptoms of one question produce one blocker; independent questions remain separate.

## 2. Recover the Existing Wayfinder Effort

Read the parent Spec and recover its Wayfinder provenance.

Prefer:

```html id="ojdiv7"
<!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision> -->
```

If absent, use another explicit and unambiguous tracker relationship.

If the originating Wayfinder map cannot be determined reliably, halt. Do not guess or create a replacement map.

Blockers remain under that map unless one is genuinely outside its destination. Report such a blocker separately rather than silently creating another map.

## 3. Create or Reuse Decision Tickets

For each independent blocker, inspect the map's open child decisions.

If an open child already represents the same underlying architectural question, reuse it.

Otherwise create exactly one child decision under the existing map using repository Wayfinding operations.

Use `wayfinder:grilling` unless the caller established another appropriate Wayfinder ticket type.

Use:

```markdown id="v8t7uw"
**Parent Wayfinder:** #<wayfinder_map>
**Parent Spec:** #<spec_issue>
**Source Ticket:** #<source_ticket>
**Spec Review:** #<spec_review_issue>

## Question

<specific unresolved architectural question or authority conflict>

## Discovery Context

<caller evidence and why current work cannot proceed>

## Blocked Obligation

<exact Spec/review/remediation requirement that cannot currently be satisfied,
when applicable>

## Governing Authority

<applicable ADRs/docs/contracts and the relevant incompatibility>
```

`Parent Wayfinder` and `Parent Spec` are required.

Omit optional relationships or sections when they do not apply.

Do not:

* propose a preferred architectural resolution;
* rewrite the blocked obligation into a solution;
* create duplicate decisions because the same blocker surfaced at multiple workflow stages.

The decision ticket must preserve enough context for `$wayfinder` to determine whether authority must change, the blocked obligation must change, or both must be reconciled.

## 4. Human Handoff Intercept

After every independent blocker has one corresponding open Wayfinder decision, halt the current workflow.

Present all decisions and identify the next one:

> ⚠️ **Work is blocked by unresolved architecture.**
>
> The following Wayfinder decision tickets represent the unresolved blockers:
>
> * **`<Decision Ticket 1 Title> (<URL>)`**
> * **`<Decision Ticket 2 Title> (<URL>)`**
>
> Please continue with:
>
> ```
> $wayfinder - <Next Decision Ticket Title> (<URL>)
> ```

When only one exists, present only that ticket.

Do not resume implementation, review remediation, or Spec amendment until the applicable decisions are resolved and the map route is clear.

`$wayfinder` owns decision sequencing and resolves one decision at a time.

## 5. Return Path

After the required decisions are resolved:

```text id="ofssib"
$wayfinder
→ $to-specs
→ $to-remediation-specs when an existing Spec is affected
→ $to-tickets
→ $implement-ticket
```

Do not hand directly back to the blocked implementation ticket when the architectural decision changes or invalidates its Spec/remediation obligation.

`$to-remediation-specs` owns reconciling existing Spec requirements, acceptance obligations, and downstream ticket intent against the newly resolved architecture.

## Completion

This skill is complete when:

* the existing Wayfinder map is recovered;
* every independent blocker is represented by exactly one open decision ticket;
* blocked requirements/acceptance obligations are preserved when applicable;
* no duplicate decision tickets were introduced;
* the Human Handoff Intercept is presented.

`$wayfinder` owns architectural resolution and authority reconciliation.

`$to-specs` / `$to-remediation-specs` own propagating the resulting architecture back into the existing Spec before implementation resumes.
