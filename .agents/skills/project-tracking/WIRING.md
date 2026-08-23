# Project Tracking Wiring

`$project-tracking` is internal composition for Polaris lifecycle owners.

For every durable lifecycle transition that creates a formal workflow artifact or changes an existing artifact's Project projection, the owning lifecycle skill must invoke `$project-tracking` after the authoritative tracker/repository mutation succeeds and before the owner's Human Handoff or ordinary return.

This applies to `$wayfinder`, `$to-specs`, `$to-tickets`, `$implement-ticket`, `$verify-spec`, `$review-spec`, `$spec-merge-cleanup`, and `$architecture-remediation`.

## Project-delivery overlay

Before project-delivery bootstrap activation, existing lifecycle owners may send their ordinary base projection directly to `$project-tracking`.

After activation, every Wayfinder-managed projection must first recover current project-delivery context from `$project-delivery-management` canonical state. The lifecycle owner supplies:

* its ordinary lifecycle `Workflow State`, `Next Skill`, and `Work Status`;
* the current `Project Delivery State` classification required by `$project-tracking`.

`$project-tracking` validates the ordinary lifecycle route first, then applies only the focus-aware `Work Status` / `Next Skill` overlay. It never rewrites `Workflow State` to represent focus.

This keeps ownership separated:

* lifecycle owner → artifact lifecycle stage and ordinary next action;
* `$project-delivery-management` → focus/eligibility truth;
* `$project-tracking` → deterministic non-authoritative projection of those already-established facts.

A Wayfinder with multiple governors is project-delivery `focused` when at least one current eligible governor is focused. Do not ask `$project-tracking` to choose among governors or infer focus from Project fields.

The lifecycle owner supplies the desired base projection from the durable state it just established. If one transition changes multiple artifacts, synchronize every affected artifact in the same reconciliation step. Examples include ticket closure changing its parent Spec frontier, review remediation changing both Spec and Spec Review state, and merge cleanup completing a Spec, optional Spec Review, or one or more governing Wayfinders.

Do not invoke `$project-tracking` before the semantic transition succeeds, and do not use Project state to decide the transition. Internal helpers return their result to the lifecycle owner; the owner performs Project synchronization unless an explicit reconciliation flow already owns it. Independent verifiers never synchronize Project state.

`PROJECT TRACKING: DRIFT` never rolls back or rewrites the authoritative workflow transition or project-delivery focus. Report the drift and continue to treat durable tracker/repository state as authoritative.

The one-time addition of `$project-delivery-management` to the existing `Next Skill` single-select field is owned by `ROLLOUT.md`. Steady-state `$project-tracking` never repairs Project schema.
