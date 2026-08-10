---
name: to-remediation-tickets
description: Invoked only by `$to-tickets` during a remediation re-invocation — not a standalone command. Reconciles a Spec Review or an existing Spec against already-linked tickets and returns only the actionable ticket delta.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Remediation Tickets

This skill is invoked by `$to-tickets` when:

* the source is a `$review-spec` parent issue titled `Spec Review: ...`; or
* the source is an existing Spec that already has linked implementation tickets.

It replaces ordinary vertical-slice drafting for that invocation. Return the resulting ticket delta to `$to-tickets`; do not publish tickets here.

## 1. Resolve the Source

### Spec Review

Recover the original Spec from the exact body line:

```markdown
**Parent Spec:** #<spec_issue_number>
```

The Spec Review issue remains the remediation source. The original Spec remains the branch owner.

### Existing Spec

Use the supplied Spec as the source and parent for any new implementation tickets.

Do not create another Spec, branch, or baseline.

## 2. Recover Required State

### Spec Review

Recover or synthesize the **Root Blocker Ledger** and acceptance matrix.

* Preserve stable root IDs (`RB-1`, `RB-2`, ...).
* Group findings by durable invariant, not symptom.
* Preserve affected surfaces/reference kinds and production-path obligations.
* Preserve `Architecture decision required` and `Governing authority` for Architecture roots.
* `Architecture decision required: No` is ordinary remediation.
* If any root has `Architecture decision required: Yes`, halt and return it to `$review-spec`. Do not ticket unresolved architecture here.

### Existing Spec

Treat the current Spec as the required state.

Do not reconstruct an older Spec revision. Existing linked tickets represent the work previously sliced from it.

## 3. Reconcile Against Existing Tickets

Read the relevant existing linked tickets, including open and closed state, body, acceptance criteria, dependencies, and closing context when needed.

For each current requirement or root:

* matching **open** ticket that still covers it → skip;
* matching **open** ticket whose pending work must change → return an update;
* matching **closed** ticket whose obligation is satisfied → skip;
* matching **closed** ticket but current state requires additional work → create a new ticket;
* no matching ticket → create a new ticket.

For existing open tickets whose work is no longer required by an amended Spec, return them for closure as superseded.

Before treating a closed ticket as sufficient, verify current source truth when the requirement or root can still be violated.

Do not reopen or rewrite closed tickets to represent newly required work.

## 4. Mode-Specific Delta Rules

### Spec Review

Create the smallest root-complete remediation track.

Each ticket must carry:

* root blocker ID and invariant;
* affected sibling surfaces/reference kinds;
* production-path acceptance criteria;
* required negative/regression proof;
* remaining unproven acceptance-matrix cells when applicable.

If a closed ticket claimed to fix the root but current evidence still violates it, create a new `Regression:` ticket referencing the prior ticket.

Do not create one ticket per symptom when several symptoms share one root.

### Existing Spec

Reconcile semantically, not by wording alone.

If an amended requirement changes pending work, prefer updating the existing open ticket when it still naturally owns that work.

If a closed ticket correctly satisfied the old requirement but the amended Spec now requires more, create an ordinary new ticket for the delta. This is not a regression unless previously required behavior actually broke.

Return dependency changes when new work must block an existing open ticket.

## 5. Preserve Normal Ticket Semantics

Every new or updated ticket must use `$to-tickets`'s normal rules and templates, including:

* tracer-bullet scope unless a wide-refactor exception applies;
* applicable Architecture context;
* correct blocking edges;
* the existing Spec's shared `Ticket branch`;
* acceptance criteria proving the required production behavior.

`$to-tickets` owns approval, publishing, parent-child linking, dependency wiring, labels, and branch metadata.

## 6. Return the Delta

Return only actionable changes:

```text
New tickets:
- ...

Update open tickets:
- ...

Close as superseded:
- ...

Dependency changes:
- ...

Skipped:
- already tracked: ...
- already satisfied: ...
```

For Spec Review remediation, also report any regressions, open root blocker IDs, and unproven acceptance-matrix cells.

If the delta is empty, report that the existing tickets already represent the current source.

Then return control to `$to-tickets` at its approval/publishing step.
