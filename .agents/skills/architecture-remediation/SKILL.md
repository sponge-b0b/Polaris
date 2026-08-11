---
name: architecture-remediation
description: Route unresolved architecture blockers back into the existing Wayfinder effort, creating or reusing one decision ticket per independent architectural decision and handing resolution to `$wayfinder`.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# Architecture Remediation

Use when `$implement-ticket`, `$review-spec`, or another workflow cannot continue because of unresolved architecture.

This is a **routing workflow**. Do not resolve architecture, modify implementation, amend a Spec, or create a new Wayfinder map here.

## 1. Capture the Blocker Set

Use the caller-provided context to capture every unresolved architecture blocker at the stopping point.

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
* exact blocked requirement/acceptance obligation when applicable;
* source ticket or review finding.

Also capture:

* parent Spec;
* Spec Review issue when applicable.

Preserve caller evidence and terminology. Do not invent a resolution.

### Decision Coupling

De-duplicate by **independent architectural decision**, not by caller bullet or symptom.

Multiple questions belong to the **same blocker/decision ticket** when they jointly define the same durable contract, lifecycle, ownership model, or canonical path and answering one materially constrains the others.

Ask:

> Can each question be resolved independently without materially changing the decision space of the others?

If **No**, combine them into one Wayfinder decision ticket with multiple explicit questions.

If **Yes**, keep them as independent blockers.

Examples of coupled dimensions include:

* producer ownership + required producer inputs;
* contract identity/version semantics + validation semantics;
* lifecycle ownership + persistence/reconstruction responsibility;
* authority selection + the canonical evidence path that selection controls.

Do not create separate Wayfinder decisions merely because the caller presented several numbered architecture blockers.

Multiple symptoms of one architectural decision produce one ticket. Genuinely independent durable choices remain separate.

## 2. Recover the Existing Wayfinder Effort

Read the parent Spec and recover its Wayfinder provenance.

Prefer:

```html id="tcrl50"
<!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision> -->
```

If absent, use another explicit and unambiguous tracker relationship.

If the originating Wayfinder map cannot be determined reliably, halt. Do not guess or create a replacement map.

Blockers remain under that map unless one is genuinely outside its destination. Report such a blocker separately rather than silently creating another map.

## 3. Create or Reuse Decision Tickets

For each independent architectural decision produced by the coupling step, inspect the map's open child decisions.

If an open child already represents the same underlying decision, reuse it.

Otherwise create exactly one child decision under the existing map using repository Wayfinding operations.

Use `wayfinder:grilling` unless the caller established another appropriate Wayfinder ticket type.

Use:

```markdown id="4j0r47"
**Parent Wayfinder:** #<wayfinder_map>
**Parent Spec:** #<spec_issue>
**Source Ticket:** #<source_ticket>
**Spec Review:** #<spec_review_issue>

## Question

<single architectural decision to resolve>

When the decision has coupled dimensions:

1. <question/dimension>
2. <question/dimension>
3. <question/dimension>

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
* create duplicate decisions because the same blocker surfaced at multiple workflow stages;
* split one coupled architectural lifecycle/contract into separate decision tickets merely because it contains multiple questions.

The decision ticket must preserve enough context for `$wayfinder` to determine whether authority must change, the blocked obligation must change, or both must be reconciled.

## 4. Human Handoff Intercept

After every independent architectural decision has one corresponding open Wayfinder ticket, halt the current workflow.

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

`$wayfinder` owns decision sequencing and resolves one decision ticket per session. A single decision ticket may contain several tightly coupled questions that must be resolved together.

## 5. Return Path

After the required decisions are resolved:

```text id="uqgmuf"
$wayfinder
→ $to-specs
→ $to-remediation-specs when an existing Spec is affected
→ $to-tickets
→ $implement-ticket
```

Do not hand directly back to the blocked implementation ticket when an architectural decision changes or invalidates its Spec/remediation obligation.

`$to-remediation-specs` owns reconciling existing Spec requirements, acceptance obligations, and downstream ticket intent against newly resolved architecture.

## Completion

This skill is complete when:

* the existing Wayfinder map is recovered;
* caller blockers are consolidated into the minimum set of genuinely independent architectural decisions;
* every independent decision is represented by exactly one open Wayfinder ticket;
* blocked requirements/acceptance obligations are preserved when applicable;
* no duplicate or artificially split decision tickets were introduced;
* the Human Handoff Intercept is presented.

`$wayfinder` owns architectural resolution and authority reconciliation.

`$to-specs` / `$to-remediation-specs` own propagating the resulting architecture back into the existing Spec before implementation resumes.
