---
name: architecture-remediation
description: Route unresolved architecture blockers back into the existing governing Wayfinder effort, reopening that map when authoritative re-entry requires it, creating or reusing one decision ticket per independent architectural decision, and handing resolution to `$wayfinder`.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# Architecture Remediation

Use when `$implement-ticket`, `$review-spec`, `$to-remediation-specs`, or another workflow cannot continue because of unresolved or incomplete architecture.

This is a **routing workflow**. Do not resolve architecture, modify implementation, amend a Spec, or create a new Wayfinder map here.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting. Prior-session summaries or remembered conclusions are routing context only and must not substitute for required durable evidence.

If required durable state cannot be recovered, report the missing artifact rather than infer or recreate it from memory.

## 1. Capture the Blocker Set

Use the caller-provided context to capture every unresolved architecture blocker at the stopping point.

A blocker includes:

* an unresolved material architecture decision;
* a blocking `[source-conflict]` among applicable authorities;
* current authority invalidating architecture required by the work;
* a required obligation that cannot be implemented without violating or changing current authority;
* a required obligation that cannot be implemented without inventing a durable architectural owner, contract, key, path, boundary, dependency direction, lifecycle rule, or authority semantic.

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

Questions belong to the same decision when they jointly define the same durable contract, lifecycle, ownership model, or canonical path and answering one materially constrains the others.

Ask:

> Can each question be resolved independently without materially changing the decision space of the others?

If **No**, combine them into one decision with multiple explicit questions.

If **Yes**, keep them independent.

Do not create separate decisions merely because the caller reported several numbered blockers.

## 2. Recover the Existing Governing Wayfinder Effort

Read the parent Spec and recover its complete current Wayfinder governance from durable evidence:

* canonical source provenance:

  ```html
  <!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision> -->
  ```

* every applicable remediation provenance marker:

  ```html
  <!-- wayfinder-remediation: #<map>; decisions: #<decision>,#<decision> -->
  ```

* matching `Derived Spec` / `Remediation Spec` handoff metadata on canonical Wayfinder maps;
* source ticket / Spec Review lineage supplied by the caller.

Preserve original source provenance. Remediation governance is additive and must never replace `wayfinder-source`.

Resolve the **exact governing Wayfinder whose scope owns the architecture blocker being routed**. A Spec may have more than one governor; do not default to the original source when the blocker belongs to a later remediation Wayfinder.

If one candidate governor is established unambiguously, use it. If multiple governors plausibly own the blocker and durable context does not distinguish one, fail closed. Do not guess, create a replacement map, or duplicate the decision under several maps.

Blockers remain under that governing map unless one is genuinely outside its destination.

## 3. Test Existing Architecture Coverage

Before creating or reusing a decision ticket, inspect relevant accepted authority and resolved Wayfinder decisions.

A prior decision resolves the blocker only when current accepted authority **directly determines the exact durable choice the caller says is missing**.

For each blocker ask:

> Can the blocked work proceed from current authority without inventing another durable architectural choice?

If **Yes**:

* record the exact accepted decision/authority that determines the missing choice;
* explain concisely how it resolves that specific blocker;
* do not create a duplicate decision.

If **No**, the blocker remains unresolved.

**Related subject matter is not coverage.** Do not treat a closed decision or ADR as resolving a blocker merely because it concerns the same subsystem, owner, contract, or lifecycle.

For example, deciding **who owns** a lifecycle does not automatically determine its required inputs, durable selection key, or ordering.

If existing authority resolves only part of a blocker, preserve only the unresolved dimensions and re-apply **Decision Coupling** to them.

## 4. Re-enter the Governing Wayfinder Before New Decision Work

Perform this step only when at least one architecture blocker remains unresolved after Step 3.

Re-read the exact governing Wayfinder immediately before mutation.

If it is closed:

1. reopen that same Wayfinder issue with an explicit lifecycle-reentry reason identifying the blocked Spec/work;
2. re-read it and require state `open`;
3. invoke `$project-delivery-management` `reconcile` **after** the reopen is durable.

Reopening restores authoritative Wayfinder lifecycle state; it does **not** restore project focus. `$project-delivery-management` reconciliation must never auto-focus the reopened map or silently replace another focused map.

If the Wayfinder is already open, do not create a synthetic reopen/close cycle.

If the map cannot be reopened or its identity/state cannot be verified, halt. Do not create/reuse a decision ticket against a lifecycle state that still says delivery-complete.

## 5. Create or Reuse Decision Tickets

For every blocker still unresolved after the coverage test, inspect the governing map's open child decisions.

Reuse an open child only when it represents the same underlying unresolved decision.

Otherwise create exactly one child decision under the existing governing map using repository Wayfinding operations.

Use `wayfinder:grilling` unless the caller established another appropriate Wayfinder ticket type.

Use:

```markdown
**Parent Wayfinder:** #<wayfinder_map>
**Parent Spec:** #<spec_issue>
**Source Ticket:** #<source_ticket>
**Spec Review:** #<spec_review_issue>

## Question

<single architectural decision to resolve>

When coupled:

1. <question/dimension>
2. <question/dimension>

## Discovery Context

<caller evidence and why current work cannot proceed>

## Blocked Obligation

<exact requirement that cannot currently be satisfied, when applicable>

## Governing Authority

<applicable ADRs/docs/contracts and what they determine or leave unresolved>
```

`Parent Wayfinder` and `Parent Spec` are required.

Omit optional relationships or sections when they do not apply.

Do not:

* propose a preferred resolution;
* rewrite the blocked obligation into a solution;
* duplicate a decision because the same blocker surfaced at multiple workflow stages;
* split one coupled contract/lifecycle into artificial separate decisions.

The ticket must preserve enough context for `$wayfinder` to determine whether authority must change, the blocked obligation must change, existing authority must be completed, or both must be reconciled.

After the required decision-ticket/map mutations are durable, invoke `$project-delivery-management` `reconcile`. This reduction may remove invalid focus but must never select, switch, or broaden focus.

## Mandatory Project Reconciliation

After every architecture-remediation tracker transition is durable and after `$project-delivery-management` reconciliation, invoke `$project-tracking` as prescribed internal composition **before** any Human Handoff or ordinary return.

Synchronize only formal artifacts whose authoritative lifecycle state this skill actually created, reopened, or changed:

* a governing Wayfinder map reopened or kept active because unresolved architectural decision work now exists → base `Wayfinder Map / Architecture Decision / $wayfinder / Ready`;
* each newly created or lifecycle-changed open Wayfinder decision → base `Wayfinder Decision / Architecture Decision / $wayfinder / Ready`;
* a source Spec, Implementation Ticket, Spec Review, or Review Remediation Ticket only when this skill itself durably records that artifact in `Architecture Remediation` → use that artifact type's `Architecture Remediation / $architecture-remediation / Blocked` base route;
* any additional formal artifact whose lifecycle state this skill durably changes.

Do not manufacture a source-artifact transition merely because the caller arrived with an architecture blocker. When existing authority fully resolves the blocker set and this skill makes no lifecycle mutation, there may be no Project reconciliation target; return control to the caller without inventing one.

Supply current Project Delivery State separately from the base lifecycle projection. `$project-tracking` owns validation, delivery overlay, and mutation; it does not discover which artifacts this skill changed.

If Project synchronization fails, report `PROJECT TRACKING: DRIFT`. Do not undo durable Wayfinder/decision state and do not suppress an otherwise-authorized handoff or resolved-authority return.

## 6. Human Handoff Intercept

### Unresolved Decisions Remain

When any blocker remains unresolved, halt the current workflow after every independent decision has one corresponding open Wayfinder ticket.

Present all decisions and identify the next one:

> ⚠️ **Work is blocked by unresolved architecture.**
>
> The following Wayfinder decision tickets represent the unresolved blockers:
>
> * **`<Decision Ticket Title> (<URL>)`**
>
> Please continue with:
>
> ```
> $wayfinder - <Next Decision Ticket Title> (<URL>)
> ```

When only one exists, present only that ticket.

Do not resume implementation, review remediation, or Spec amendment until the applicable decisions are resolved and the map route is clear.

`$wayfinder` owns decision sequencing and resolves one decision ticket per session. Its project-delivery focus guard applies at that substantive decision-entry boundary. If this remediation reopened a previously completed map, `$wayfinder` may require an explicit human focus/switch/parallel decision before resolution proceeds.

### Existing Authority Fully Resolves the Blocker Set

If every reported blocker is directly resolved by current accepted authority, create no Wayfinder decision and do not reopen a closed Wayfinder solely to restate existing authority.

Report for each blocker:

* exact governing decision/authority;
* the durable choice it determines;
* why no architectural invention remains necessary.

Do not infer resolution from topic overlap.

If current authority invalidates or materially changes the existing Spec/remediation obligation, continue through the normal Wayfinder-to-Spec reconciliation path rather than returning directly to implementation.

Otherwise report that the blocker set is already architecturally resolved and return control to the calling workflow.

## 7. Return Path

After new architectural decisions are resolved, or existing accepted authority requires Spec reconciliation:

```text
$wayfinder
→ $to-specs
→ $to-remediation-specs when an existing Spec is affected
→ $to-tickets
→ $implement-ticket
```

Do not hand directly back to a blocked implementation ticket when architecture changes or invalidates its Spec/remediation obligation.

`$to-remediation-specs` owns reconciling existing Spec requirements and downstream ticket intent against newly resolved architecture.

A legitimately reopened Spec or blocker participates through the existing native dependency graph. Do not write a separate satisfaction/ineligibility flag; downstream frontier guards must re-read current open/closed blocker state.

## Completion

This skill is complete when:

* the exact existing governing Wayfinder map is recovered without rewriting source/remediation provenance;
* caller blockers are reduced to the minimum set of genuinely independent decisions;
* existing accepted authority is tested against the exact missing durable choices;
* when unresolved decision work re-enters a closed map, that same map is reopened and verified open before decision work is created/reused;
* every unresolved decision is represented by exactly one open Wayfinder ticket;
* blocked obligations are preserved when applicable;
* project-delivery reconciliation runs after authoritative reopen/decision-tracker transitions without auto-focusing a map;
* mandatory `$project-tracking` reconciliation runs for every formal artifact whose lifecycle state this skill changed;
* no duplicate or artificially split decisions were introduced;
* the appropriate Human Handoff or resolved-authority return is presented.

`$wayfinder` owns architectural resolution and authority reconciliation.

`$to-specs` / `$to-remediation-specs` own propagating changed architecture back into an existing Spec before implementation resumes.
