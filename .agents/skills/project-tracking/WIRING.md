# Project Tracking Wiring

`$project-tracking` is an internal non-authoritative projection helper. Its normal automatic
boundary is `$spec-merge-cleanup` after authoritative Spec completion.

The Project is intentionally eventually consistent during active delivery. Routine
`$wayfinder`, `$to-specs`, `$to-tickets`, `$implement-ticket`, `$verify-spec`,
`$review-spec`, `$architecture-remediation`, and `$project-delivery-management` transitions
do not synchronize it.

Authorized current-lifecycle projection occurs only at:

1. mandatory completed-Spec reconstruction owned by `$spec-merge-cleanup`;
2. an explicit human request to refresh/reconcile the board, after the active workflow
   reconstructs the requested authoritative artifact universe.

Do not persist projection-debt queues, flags, labels, ledgers, or comments. Missing Project
membership and stale fields between those boundaries are projection lag, not workflow-state
loss.

Repository/Project setup, schema provisioning, historical backfill, and old-format
conversion are administrative work performed out of band. Runtime lifecycle skills assume
the current required Project/control schema exists and fail closed when it does not.

## Delivery overlay

Every active Wayfinder-managed projection recovers current delivery context from
`$project-delivery-management`. Independent artifacts require durable Independent
classification. `$project-tracking` validates the ordinary lifecycle route first and then
applies only the current delivery presentation overlay.

Ownership remains:

* lifecycle owner -> authoritative artifact state and ordinary next action;
* `$project-delivery-management` -> canonical focus/frontier classification;
* `$project-tracking` -> non-authoritative Project projection.

## Mandatory Spec-boundary reconstruction

At `$spec-merge-cleanup`, reconstruct the complete current lineage from authoritative state
rather than assuming prior Project synchronization. Include the completed Spec, all native
Implementation Ticket children, its conventional Spec Review, all Review Remediation Ticket
children, every governing Wayfinder required for a coherent lineage, relevant Wayfinder
Decisions, direct dependent Specs whose actionability changed, and any other formal artifact
required for internal consistency.

Derive current state from present lifecycle authority; do not replay Project deltas. Re-read
native blocker relationships when completion changes dependent actionability. The working
reconstruction set is not a durable registry.

## Explicit human refresh

A human request to refresh/reconcile the board is the only ordinary mid-Spec projection
boundary. The active workflow reconstructs the requested current authoritative universe and
invokes `$project-tracking` once for that batch.

A human focus/dependency operation is not itself a board-refresh request unless the human
also asks for board refresh.

`PROJECT TRACKING: DRIFT` never changes authoritative lifecycle state, downstream handoff
eligibility, dependencies, or project-delivery focus.
