---
name: to-remediation-specs
description: Invoked only by `$to-specs` when a Wayfinder map already has a derived in-progress spec — not a standalone command. Recover the existing spec and its Wayfinder provenance, compute the newly resolved decision delta, and amend the spec without duplicating previously consumed decisions.
compatibility: product=codex product=claude-code system=gh network=required
disable-model-invocation: true
---

# To Remediation Specs

This skill is invoked by `$to-specs` when its source Wayfinder map already has a derived in-progress spec. It replaces fresh spec creation for that case.

The Wayfinder map remains the source input. This skill updates the existing derived spec from newly resolved Wayfinder decisions.

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

Then read the map's current resolved decisions and compare their decision-ticket IDs with those already recorded as consumed by the spec.

The difference is the **decision delta**.

If the spec predates provenance metadata, reconcile its current contents against the map once, mark decisions already represented as consumed, and continue with only the remaining delta.

Do not regenerate the spec merely to bootstrap provenance.

## 3. Apply the Decision Delta

Read the newly resolved decision tickets and their resolution comments.

Apply the delta semantically to the existing spec:

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

Do not introduce architectural decisions that are absent from the resolved Wayfinder history.

## 4. Update Provenance

After the amendment is complete, update the existing provenance marker to include every resolved Wayfinder decision now represented by the spec:

```html
<!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision>,#<new-decision> -->
```

The marker records **consumption**, not architectural authority. Wayfinder decision tickets remain the durable home of the decisions themselves.

## 5. Update the Existing Spec

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
* whether provenance was bootstrapped;
* whether any ambiguity prevented amendment.

If the decision delta is empty, make no semantic spec changes and report that the existing spec is already synchronized with the Wayfinder map.
