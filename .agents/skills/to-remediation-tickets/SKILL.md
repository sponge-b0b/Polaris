---
name: to-remediation-tickets
description: Invoked only by `$to-tickets` during remediation re-invocation — reconcile a Spec Review or existing Spec against linked tickets and return only the actionable ticket delta.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Remediation Tickets

Invoked by `$to-tickets` when:

* the source is a `Spec Review: ...` issue; or
* an existing Spec already has linked implementation tickets.

Replace ordinary vertical slicing for this invocation. Return the delta to `$to-tickets`; do not publish here.

## 1. Resolve the Source

### Spec Review

Recover the original Spec from:

```markdown
**Parent Spec:** #<spec_issue_number>
```

The Spec Review remains the remediation source. The original Spec remains the branch owner.

### Existing Spec

Use the supplied Spec as source and parent.

Do not create another Spec, branch, or baseline.

## 2. Recover Required State

### Spec Review

Recover the latest **Root Blocker Ledger** and acceptance matrix, including later review/remediation updates.

* Preserve stable `RB-*` IDs and invariants.
* Preserve current root status, affected surfaces, production-path obligations, and unproven cells.
* Preserve `Architecture decision required` and governing authority.
* `Architecture decision required: No` is ordinary remediation.
* If any unresolved root has `Architecture decision required: Yes`, halt and return it to `$review-spec`.

Do not synthesize new roots here.

### Existing Spec

Treat the current Spec as required state.

Do not reconstruct an older revision. Existing linked tickets represent previously sliced work.

## 3. Reconcile Against Existing Tickets

Read relevant open and closed tickets, including body, acceptance criteria, dependencies, and closing context when needed.

For each current requirement:

* matching **open** ticket still covering remaining work → skip;
* matching **open** ticket whose pending work changed → return an update;
* matching **closed** ticket whose obligation is satisfied → skip;
* matching **closed** ticket but current state requires additional work → create a new ticket;
* no matching ticket → create a new ticket.

Never reopen or rewrite closed tickets to represent new or remaining work.

Before treating a closed ticket as sufficient, verify that the current source state actually satisfies the requirement.

For open tickets no longer required by an amended Spec, return them for closure as superseded.

### Root Blocker Invariant

For Spec Review remediation, every Root Blocker currently `open`, `regressed`, or `unproven` must be represented by an active open ticket.

* matching open ticket covers the remaining root obligation → reuse/update it;
* no matching open ticket → create a new ticket;
* prior covering tickets are closed → create a new ticket and reference the relevant prior ticket(s).

A closed ticket is historical lineage, not active coverage and not proof that the Root Blocker is resolved.

Do not skip an unresolved Root Blocker because its previous tickets are closed.

## 4. Mode-Specific Delta Rules

### Spec Review

Create the smallest **root-complete** remediation track.

Each ticket must carry:

* Root Blocker ID and invariant;
* affected sibling surfaces/reference kinds;
* production-path acceptance criteria;
* required negative/regression proof;
* remaining unproven acceptance cells when applicable.

If closed work claimed to satisfy a root but the root remains `open` or `regressed`, create a new `Regression:` ticket referencing the prior work.

For an `unproven` root with no active covering ticket, create a new remediation ticket whose acceptance establishes the outstanding root obligations and applies the minimum correction required if they are not met.

Do not create one ticket per symptom when several symptoms share one root.

### Existing Spec

Reconcile semantically, not by wording alone.

If an amended requirement changes pending work, update the existing open ticket when it still naturally owns that work.

If a closed ticket satisfied the old requirement but the amended Spec requires more, create an ordinary new ticket for the delta. It is a regression only when previously required behavior actually broke.

Return dependency changes when new work must block an existing open ticket.

## 5. Preserve Normal Ticket Semantics

Every new or updated ticket must follow `$to-tickets` rules, including:

* tracer-bullet scope unless a wide-refactor exception applies;
* applicable Architecture context;
* correct blocking edges;
* the existing Spec's shared `Ticket branch`;
* acceptance criteria proving required production behavior.

`$to-tickets` owns approval, publishing, parent-child linking, dependencies, labels, and branch metadata.

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
- already tracked by open ticket: ...
- already satisfied by current source: ...
```

For Spec Review remediation, also report:

* every unresolved Root Blocker;
* the open ticket that covers it, or the new ticket required;
* regressions and referenced closed tickets.

Never report an `open`, `regressed`, or `unproven` Root Blocker as skipped merely because its covering tickets are closed.

If the delta is empty, every unresolved Root Blocker must already have active open-ticket coverage.

Return control to `$to-tickets` at its approval/publishing step.
