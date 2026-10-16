---
name: to-remediation-specs
description: Compatibility helper for `$to-specs` that mechanically recovers existing Wayfinder Spec handoffs and reconciles provenance markers without interpreting or amending Spec semantics.
compatibility: product=codex product=claude-code system=gh network=required
disable-model-invocation: true
---

# To Remediation Specs

This skill is a **temporary compatibility helper** during the CCL workflow migration.

It no longer owns semantic Spec remediation. `$to-specs` owns the desired CCL projection
and every semantic/body amendment.

Its only job is to recover the exact existing Wayfinder-managed Spec set and make the
forward/Spec-local provenance mechanically consistent enough for `$to-specs` to reconcile
those Specs in place.

## Inputs

Invoked only by `$to-specs` with one exact Wayfinder map.

Recover correctness-critical state from the current tracker. Do not use chat memory.

## Recover handed-off Specs

Resolve both handoff roles:

* **Derived Spec** — created from this Wayfinder and carrying this map in a
  `wayfinder-source` marker;
* **Remediation Spec** — retains its original source and carries this map through
  `wayfinder-remediation` provenance.

Use both:

* forward `## Spec Handoff` metadata on the map; and
* unambiguous Spec-local `wayfinder-source` / `wayfinder-remediation` markers.

If reverse provenance proves an unambiguous linkage missing from the map, add only that
missing forward linkage. If a forward linkage points to a Spec whose local provenance is
unambiguously missing the matching marker, add only that matching marker.

Never:

* convert Derived ↔ Remediation roles;
* replace original source provenance;
* infer a linkage from Project fields, issue order, branch names, or conversational
  history;
* create a new Spec;
* edit semantic Spec sections;
* inspect Decision Analysis/ADR prose to infer contract meaning;
* compute decision-state semantic hashes or deltas;
* decide whether current Spec content is correct;
* route architecture remediation.

Ambiguous/malformed provenance fails closed and returns the ambiguity to `$to-specs`.

## Legacy decision-state markers

Existing `wayfinder-decision-states:v1` comments are historical provenance only.

Do not create, update, remove, or use them to decide semantic synchronization. Exact CCL
`contract@revision#assertion` addresses now provide semantic consumption identity in the
parent `$to-specs` projection.

## Preserve lifecycle identity

For every recovered Spec return, but do not mutate:

* issue identity;
* original planning provenance;
* branch and fixed baseline lineage;
* existing implementation tickets;
* native dependencies;
* Spec Review lineage.

## Return

Return exactly one result:

```text
SPEC HANDOFF RECOVERY: PASS | BLOCKED
Wayfinder: <map identity>
Derived Specs: <exact issue set>
Remediation Specs: <exact issue set>
Forward links added: <exact set | None>
Spec-local markers added: <exact set | None>
Ambiguous relationships: <count + details>
Semantic Spec changes performed: 0
```

`PASS` requires zero ambiguous relationships.

On `PASS`, return normally to `$to-specs`; the parent computes the desired CCL projection
and performs any in-place Spec amendment.

This helper is intentionally non-semantic and is expected to disappear once legacy
handoff recovery no longer needs a separate compatibility boundary.
