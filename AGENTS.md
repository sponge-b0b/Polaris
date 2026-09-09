# Project Tracking Wiring

`$project-tracking` is an internal projection helper whose normal automatic synchronization boundary is `$spec-merge-cleanup`.

The GitHub Project is intentionally **eventually consistent during active delivery**. Formal lifecycle owners must persist authoritative repository/tracker state immediately, but they must not invoke `$project-tracking` merely because one lifecycle transition created, changed, closed, reopened, blocked, or unblocked a formal artifact.

This deferred cadence applies to routine `$wayfinder`, `$to-specs`, `$to-tickets`, `$implement-ticket`, `$verify-spec`, `$review-spec`, and `$architecture-remediation` transitions. It also applies to internal `$project-delivery-management` focus/dependency reconciliation. Any older narrower skill wording that requires automatic Project synchronization at those ordinary boundaries is superseded by this cross-skill cadence rule.

Authorized Project projection occurs only at these boundaries:

1. **Mandatory Spec completion reconciliation** — `$spec-merge-cleanup` reconstructs the complete completed-Spec lineage from authoritative durable state and invokes `$project-tracking` once for the whole reconciliation set.
2. **Explicit human-requested board reconciliation** — when the human explicitly asks to refresh/reconcile the Project, the active workflow independently reconstructs the requested authoritative artifact universe and invokes `$project-tracking` once for that batch.
3. **Bootstrap/migration** — separately authorized one-time Project/schema setup may project state as required by its own migration contract.

Do not create a `Project update pending` flag, queue, ledger, label, comment stream, or other shadow bookkeeping merely to remember deferred projection. The repository/tracker already owns the facts needed to reconstruct the board. Missing Project membership and stale Project fields during active Spec work are therefore projection lag, not workflow-state loss.

## Project-delivery overlay

Before project-delivery bootstrap activation, an authorized reconciliation may send ordinary base projections directly to `$project-tracking`.

After activation, every Wayfinder-managed projection must recover current project-delivery context from `$project-delivery-management` canonical state. The authorized reconciliation owner supplies:

* the artifact's authoritative lifecycle `Workflow State`, `Next Skill`, and `Work Status`;
* the current `Project Delivery State` classification required by `$project-tracking`.

`$project-tracking` validates the ordinary lifecycle route first, then applies only the focus-aware `Work Status` / `Next Skill` overlay. It never rewrites `Workflow State` to represent focus.

This keeps ownership separated:

* lifecycle owner → authoritative artifact lifecycle and ordinary next action;
* `$project-delivery-management` → canonical focus/eligibility truth;
* `$project-tracking` → deterministic non-authoritative projection of those already-established facts at an authorized reconciliation boundary.

A Wayfinder with multiple governors is project-delivery `focused` when at least one current eligible governor is focused. Do not ask `$project-tracking` to choose among governors or infer focus from Project fields.

## Mandatory Spec-boundary reconstruction

At `$spec-merge-cleanup`, do not assume earlier lifecycle skills kept Project rows or membership current. Reconstruct the complete current Spec lineage from authoritative state before projection, including the completed Spec, all of its implementation tickets, its conventional Spec Review when one exists, all review-remediation tickets, every governing Wayfinder whose projection is required for a coherent lineage, relevant Wayfinder decisions, direct dependent Specs whose actionability changed, and any other formal artifact whose current projection is necessary to make the completed lineage internally consistent.

When a child transition changed decomposition/frontier state earlier in the Spec lifecycle, derive the final current frontier now from authoritative hierarchy/dependency state. Do not replay historical Project deltas. When an open/close or reopen transition affects another artifact's blocker state, re-read the dependent's complete native `blocked by` state; never remove a historical dependency merely because its blocker closed.

The reconstructed reconciliation set is working state only. Do not persist it as another workflow registry.

## Explicit human refresh

An explicit human request to refresh/reconcile the board is the only ordinary mid-Spec escape hatch. Reconstruct the requested artifact universe from current repository/tracker authority, not from existing Project rows, and perform one batch. A human focus/dependency operation is **not** implicitly a board-refresh request unless the human also asks for the Project to be refreshed.

Do not use Project state to decide an authoritative transition. Independent verifiers never synchronize Project state.

`PROJECT TRACKING: DRIFT` never rolls back or rewrites the authoritative workflow transition, recovered frontier, downstream handoff eligibility, or project-delivery focus. Report the drift and continue to treat durable tracker/repository state as authoritative.

The required `$project-delivery-management` `Next Skill` option is provisioned once during migration. Steady-state `$project-tracking` requires the existing option and never creates, alters, or repairs Project schema.