# Project Tracking Wiring

`$project-tracking` is internal composition for Polaris lifecycle owners.

For every durable lifecycle transition that creates a formal workflow artifact or changes an existing artifact's Project projection, the owning lifecycle skill must invoke `$project-tracking` after the authoritative tracker/repository mutation succeeds and before the owner's Human Handoff or ordinary return.

This applies to `$wayfinder`, `$to-specs`, `$to-tickets`, `$implement-ticket`, `$verify-spec`, `$review-spec`, `$spec-merge-cleanup`, and `$architecture-remediation`.

The lifecycle owner supplies the desired projection from the durable state it just established. If one transition changes multiple artifacts, synchronize every affected artifact in the same reconciliation step. Examples include ticket closure changing its parent Spec frontier, review remediation changing both Spec and Spec Review state, and merge cleanup completing a Spec, optional Spec Review, or originating Wayfinder.

Do not invoke `$project-tracking` before the semantic transition succeeds, and do not use Project state to decide the transition. Internal helpers return their result to the lifecycle owner; the owner performs Project synchronization unless an explicit reconciliation flow already owns it. Independent verifiers never synchronize Project state.

`PROJECT TRACKING: DRIFT` never rolls back or rewrites the authoritative workflow transition. Report the drift and continue to treat durable tracker/repository state as authoritative.
