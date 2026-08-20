---
name: to-remediation-specs
description: Invoked only by `$to-specs` when a Wayfinder map already has one or more in-progress Spec handoffs — recover derived and remediation Specs, apply newly resolved decision deltas, and amend them without duplicating previously consumed decisions.
compatibility: product=codex product=claude-code system=gh network=required
disable-model-invocation: true
---

# To Remediation Specs

Invoked by `$to-specs` when its source Wayfinder map already has one or more in-progress Spec handoffs.

Replace fresh spec creation for that handed-off scope. The Wayfinder map remains the source input for the current remediation decisions.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting. Prior-session summaries or remembered conclusions are routing context only and must not substitute for required durable evidence.

If required durable state cannot be recovered, report the missing artifact rather than infer or recreate it from memory.

## 1. Recover the Existing Specs

From the source Wayfinder map, resolve every in-progress Spec identified by the reconciled `Derived Spec` and `Remediation Spec` metadata established by `$to-specs`.

For a **Derived Spec**, confirm its durable source provenance identifies the input Wayfinder.

For a **Remediation Spec**, preserve its original source provenance even when it identifies another Wayfinder. Confirm instead that the input Wayfinder explicitly names the Spec as a `Remediation Spec` or that the Spec already has a `wayfinder-remediation` marker for the input Wayfinder.

If tracker evidence reveals an additional unambiguous handed-off Spec missing from the map's `Spec Handoff`, add the matching linkage and include that Spec before continuing.

Preserve each Spec's:

* issue identity;
* original planning/source provenance;
* branch and baseline lineage;
* existing tickets;
* Spec Review lineage, when present.

If no in-progress handed-off Specs exist, return to `$to-specs` for normal spec creation.

If any candidate relationship or handoff role is ambiguous, halt rather than guessing which Specs belong to the current remediation run.

## 2. Recover Decision Provenance

For each **Derived Spec**, read its source Wayfinder provenance marker:

```html
<!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision> -->
```

Confirm that `wayfinder-source` identifies the input map.

For each **Remediation Spec**, preserve its existing `wayfinder-source` marker unchanged and read the separate remediation marker for the input map when present:

```html
<!-- wayfinder-remediation: #<map>; decisions: #<decision>,#<decision> -->
```

Read the input map's resolved decisions and compare their IDs with those already recorded as consumed by that Spec for the input map.

The difference is that Spec's **decision delta**. Keep decision deltas independent per Spec and per Wayfinder; consumption by one Spec or one Wayfinder does not imply consumption by another.

If a Derived Spec predates source provenance metadata, reconcile its current contents against the map once, mark decisions already represented as consumed by that Spec, and continue with only its remaining delta.

If a Remediation Spec has no remediation marker yet for the input map, treat this as its initial remediation from that map. Reconcile its current contents against the map once so any already represented decisions are not duplicated, then use only the remaining resolved decisions as its delta.

Do not regenerate a Spec merely to bootstrap provenance.

## 3. Reconcile the Decision Deltas

For each Spec with a non-empty decision delta, read the newly resolved decision tickets and their resolution comments.

Apply that delta semantically to a candidate amendment for that Spec:

* update existing requirements or user stories when the decision changes the same behavior;
* replace or remove content invalidated by the decision;
* add content only for genuinely new behavior;
* reconcile **Architecture Impact** with newly resolved architecture;
* update affected implementation and testing decisions;
* preserve unaffected content.

Do not duplicate:

* user stories;
* Architecture Impact entries;
* implementation decisions;
* testing decisions;
* previously consumed Wayfinder decisions.

A new decision does not imply a new spec entry when it only clarifies or supersedes an existing one.

Do not introduce architectural decisions absent from resolved Wayfinder history.

## 4. Architecture Completeness Preflight

Before applying a materially changed architecture-dependent implementation obligation to any candidate Spec, verify that accepted architecture determines enough to implement it without inventing another durable architectural choice.

Where applicable, check:

* canonical ownership;
* typed authority/input sources;
* identity, version, selection, or correlation semantics;
* lifecycle ordering;
* persistence/retrieval responsibility;
* dependency boundaries;
* failure semantics.

### Concrete Implementability Check

For each materially changed obligation, identify the existing concrete contract and production seam expected to realize it.

Inspect only enough existing source to determine whether the accepted architecture is realizable.

Where applicable, verify:

* required domain/type inputs can exist at the lifecycle point where the obligation requires them;
* the designated producer has authoritative inputs sufficient to construct the required artifact;
* required classifications or authority facts are determined or deterministically derivable from accepted authority;
* production composition can supply required dependencies without inventing new durable semantics;
* canonical consumers can obtain required typed inputs from the authoritative path.

Search before reading. Locate the affected type, producer, consumer, or composition seam and read only the surrounding code needed to answer these questions.

Do not require implementation wiring to already exist.

Missing factories, methods, configuration objects, registration calls, repository operations, DI bindings, bootstrap wiring, or similar mechanisms are implementation work when accepted architecture already determines their semantics.

If satisfying any candidate obligation would require inventing a new durable input, meaning, authority source, classification, owner, key/path, boundary, dependency direction, or lifecycle rule, architecture remains incomplete.

Ordinary implementation details are not architecture.

If satisfying any candidate obligation would require inventing unresolved architecture:

* do not amend any Spec in the current remediation run;
* do not consume any decision delta;
* do not create or modify implementation tickets;
* collect every independent architecture blocker;
* preserve coupled questions as one blocker when they jointly define the same contract or lifecycle;

Halt with a Human Handoff:

> ⚠️ **Spec remediation is blocked by incomplete architecture.**
>
> Please run:
>
> ```
> $architecture-remediation - <Blocked Spec Title> (<Spec URL>) — <concise blocker-set summary>
> ```
>
> Pass the blocked obligation, concrete contract/production-seam evidence, material consequence, governing authority, and source Wayfinder decisions.

If more than one Spec is independently blocked, output one handoff per blocked Spec.

Do not propose the architectural resolution.

## 5. Update Provenance

After all candidate amendments pass the Architecture Completeness Preflight, update provenance per Spec and handoff role.

For a **Derived Spec**, update its existing source marker to include every resolved decision from the input Wayfinder now represented by that Spec:

```html
<!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision>,#<new-decision> -->
```

For a **Remediation Spec**, preserve its original `wayfinder-source` marker unchanged and add or update one separate remediation marker for the input Wayfinder:

```html
<!-- wayfinder-remediation: #<map>; decisions: #<decision>,#<decision>,#<new-decision> -->
```

A Spec may have remediation markers for more than one later Wayfinder. Never merge a remediation Wayfinder into `wayfinder-source` or replace the Spec's original planning provenance.

These markers record **consumption**, not architectural authority.

Wayfinder decision tickets remain the durable home of the decisions themselves.

## 6. Update the Existing Specs

Write each reconciled candidate back to its existing Spec in place.

Do not:

* create new specs for handed-off scope;
* reset branch or baseline metadata;
* replace existing ticket or review lineage;
* create implementation tickets;
* reopen or close existing remediation tickets merely because a spec changed.

Return the amended Spec set to `$to-specs`.

## Completion

Report:

* existing Specs amended or already synchronized;
* source Wayfinder map;
* handoff role (`Derived Spec` or `Remediation Spec`) per Spec;
* newly consumed decision tickets per Spec;
* spec sections changed per Spec;
* Architecture Completeness Preflight result;
* concrete contracts/production seams checked when applicable;
* whether provenance was bootstrapped per Spec;
* whether any ambiguity or architecture blocker prevented amendment.

If a Spec's decision delta is empty, make no semantic changes to that Spec and report that it is already synchronized with the input Wayfinder.

If the Architecture Completeness Preflight fails, leave all existing Specs and provenance unchanged and present the Human Handoff.
