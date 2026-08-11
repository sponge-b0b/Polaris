---
name: to-remediation-specs
description: Invoked only by `$to-specs` when a Wayfinder map already has a derived in-progress spec — recover the existing spec, apply newly resolved decision deltas, and amend it without duplicating previously consumed decisions.
compatibility: product=codex product=claude-code system=gh network=required
disable-model-invocation: true
---

# To Remediation Specs

Invoked by `$to-specs` when its source Wayfinder map already has a derived in-progress spec.

Replace fresh spec creation for that case. The Wayfinder map remains the source input.

## 1. Recover the Existing Spec

From the source Wayfinder map, resolve the existing derived spec using explicit tracker metadata.

Preserve its:

* issue identity;
* branch and baseline lineage;
* existing tickets;
* Spec Review lineage, when present.

If no derived spec exists, return to `$to-specs` for normal spec creation.

If the relationship is ambiguous, halt rather than guessing which spec to amend.

## 2. Recover Decision Provenance

Read the existing spec's Wayfinder provenance marker:

```html
<!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision> -->
```

Confirm that `wayfinder-source` identifies the input map.

Read the map's resolved decisions and compare their IDs with those already recorded as consumed by the spec.

The difference is the **decision delta**.

If the spec predates provenance metadata, reconcile its current contents against the map once, mark decisions already represented as consumed, and continue with only the remaining delta.

Do not regenerate the spec merely to bootstrap provenance.

## 3. Reconcile the Decision Delta

Read the newly resolved decision tickets and their resolution comments.

Apply the delta semantically to a candidate amendment:

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

Before applying a materially changed architecture-dependent implementation obligation, verify that accepted architecture determines enough to implement it without inventing another durable architectural choice.

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

If satisfying the concrete contract requires inventing a new durable input, meaning, authority source, classification, owner, key/path, boundary, dependency direction, or lifecycle rule, architecture remains incomplete.

Ordinary implementation details are not architecture.

If satisfying the candidate obligation would require inventing unresolved architecture:

* do not amend the Spec;
* do not consume the decision delta;
* do not create or modify implementation tickets;
* collect every independent architecture blocker;
* preserve coupled questions as one blocker when they jointly define the same contract or lifecycle;
* halt with a Human Handoff:

> ⚠️ **Spec remediation is blocked by incomplete architecture.**
>
> Please run:
>
> ```
> $architecture-remediation - <Spec Title> (<Spec URL>) — <concise blocker-set summary>
> ```
>
> Pass the blocked obligation, concrete contract/production-seam evidence, material consequence, governing authority, and source Wayfinder decisions.

Do not propose the architectural resolution.

## 5. Update Provenance

After the candidate amendment passes the Architecture Completeness Preflight, update the existing provenance marker to include every resolved Wayfinder decision now represented by the spec:

```html
<!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision>,#<new-decision> -->
```

The marker records **consumption**, not architectural authority.

Wayfinder decision tickets remain the durable home of the decisions themselves.

## 6. Update the Existing Spec

Write the reconciled content back to the existing spec in place.

Do not:

* create another spec;
* reset branch or baseline metadata;
* replace existing ticket or review lineage;
* create implementation tickets;
* reopen or close existing remediation tickets merely because the spec changed.

Return the amended spec to `$to-specs`.

## Completion

Report:

* existing spec amended;
* source Wayfinder map;
* newly consumed decision tickets;
* spec sections changed;
* Architecture Completeness Preflight result;
* concrete contracts/production seams checked when applicable;
* whether provenance was bootstrapped;
* whether any ambiguity or architecture blocker prevented amendment.

If the decision delta is empty, make no semantic spec changes and report that the existing spec is already synchronized with the Wayfinder map.

If the Architecture Completeness Preflight fails, leave the existing spec and provenance unchanged and present the Human Handoff.
