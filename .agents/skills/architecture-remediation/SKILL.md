---
name: architecture-remediation
description: Route a newly discovered unresolved material architecture decision back into the existing Wayfinder effort. Recover workflow lineage, create or reuse a linked Wayfinder decision ticket, and halt for a Human Handoff Intercept to `$wayfinder`.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# Architecture Remediation

This skill is invoked by a workflow such as `$implement-ticket` or `$review-spec` when work cannot continue without resolving a newly discovered material architecture decision.

This is a **routing workflow**. Do not resolve architecture, modify implementation, amend the spec, or create a new Wayfinder map here.

## 1. Capture the Unresolved Decision

Use the caller-provided context to identify:

* the specific unresolved architecture question;
* why it is material;
* affected entities, owners, boundaries, or lifecycle responsibilities;
* governing ADR/doc references already known;
* source ticket or review finding when applicable;
* parent spec;
* Spec Review issue when applicable.

Preserve the caller's evidence. Do not invent an architectural answer.

## 2. Resolve the Existing Wayfinder Effort

Read the parent spec and recover its Wayfinder source provenance.

Prefer the spec's explicit Wayfinder provenance marker:

```html
<!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision> -->
```

If the marker is absent, use another explicit, unambiguous tracker relationship when available.

If the originating Wayfinder map cannot be determined reliably, halt and report that its provenance must be recovered. Do not guess or create a replacement map.

The unresolved decision belongs to the existing Wayfinder map unless it is genuinely outside that map's destination.

## 3. Create or Reuse the Decision Ticket

Before creating anything, inspect the existing Wayfinder map's open child issues for the same material architecture question.

If an open child already tracks it, reuse that issue.

Otherwise create one new child decision issue under the existing Wayfinder map using the repository's configured Wayfinding operations.

Use `wayfinder:grilling` unless the caller already established another Wayfinder ticket type.

Use this body shape, including only relationships that exist:

```markdown
**Parent Wayfinder:** #<wayfinder_map>
**Parent Spec:** #<spec_issue>
**Source Ticket:** #<source_ticket>
**Spec Review:** #<spec_review_issue>

## Question

<specific unresolved material architecture question>

## Discovery Context

<why implementation or review cannot proceed without resolving this decision,
including the affected ownership, canonical path, boundary, dependency direction,
or lifecycle responsibility>
```

`Parent Wayfinder` and `Parent Spec` are required.

`Source Ticket` and `Spec Review` are optional. Omit them when no such relationship exists.

Do not include a proposed architectural resolution as though it were decided.

## 4. Human Handoff Intercept

After the decision ticket exists, halt the current workflow.

Present:

> ⚠️ **Work is blocked by an unresolved material architecture decision.**
>
> I created or recovered the decision ticket under the existing Wayfinder map:
> **`<Decision Ticket Title> (<URL>)`**
>
> Please run:
>
> ```
> $wayfinder - <Decision Ticket Title> (<URL>)
> ```

Do not continue implementation, review remediation, or spec amendment until the Wayfinder decision is resolved.

## Completion

This skill is complete when:

* the existing Wayfinder map has been resolved;
* exactly one open decision ticket represents the unresolved question; and
* the Human Handoff Intercept has been presented.

`$wayfinder` owns resolution of the decision and reconciliation of authoritative architecture records.

After resolution, `$wayfinder` hands the updated map to `$to-specs`; `$to-specs` determines whether normal creation or `$to-remediation-specs` applies.
