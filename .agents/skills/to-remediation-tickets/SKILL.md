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

## Session Independence

Assume no prior conversational or agent-session state.

Recover correctness-critical inputs from the invocation, repository, and durable tracker artifacts.

Prior-session summaries are routing context only.

If required durable state cannot be recovered, report the missing artifact rather than infer it.

## 1. Resolve the Source

### Spec Review

Recover the original Spec from:

```markdown
**Parent Spec:** #<spec_issue_number>
```

The Spec Review remains the remediation source. The original Spec remains the branch owner.

### Existing Spec

Use the supplied Spec as source and parent.

Do not create another Spec, branch, or Spec baseline.

## 2. Recover Required State

### Spec Review

Recover the latest **Root Blocker Ledger** and acceptance matrix, including later review/remediation updates.

Preserve:

* stable `RB-*` IDs and invariants;
* current root status;
* affected surfaces/reference kinds;
* production-path obligations;
* unproven cells;
* `Architecture decision required`;
* governing authority.

`Architecture decision required: No` is ordinary remediation.

If an unresolved root has `Architecture decision required: Yes`, halt and return it to `$review-spec`.

Do not synthesize new roots here.

### Existing Spec

Treat the current Spec as required state.

Do not reconstruct an older revision. Existing linked tickets represent previously sliced work.

## 3. Reconcile Existing Tickets

Read relevant open and closed tickets, including body, acceptance criteria, dependencies, execution metadata, and closing context when needed.

For each current requirement:

* matching **open** ticket still covering the work → reuse;
* matching **open** ticket whose pending work changed → update;
* matching **closed** ticket whose obligation is currently satisfied → skip;
* matching **closed** ticket but current state requires additional work → create a new ticket;
* no matching ticket → create a new ticket.

Never reopen or rewrite a closed ticket to represent new or remaining work.

Before treating closed work as sufficient, verify current source truth when the obligation can still be violated.

A closed ticket is historical work evidence, not proof by itself.

For open tickets no longer required by an amended Spec, return them for closure as superseded.

### Legacy Execution Metadata

For every existing open ticket retained or updated by this remediation, inspect `Ticket baseline`.

* valid full SHA → preserve exactly;
* `Pending` → preserve;
* missing → return an update adding `Ticket baseline: Pending`;
* malformed or ambiguous value → report the metadata defect rather than overwrite potentially meaningful state.

A missing `Ticket baseline` makes the remediation delta **non-empty** even when implementation scope is otherwise current.

`Pending` is not an invented baseline. It means the implementation-start baseline has not yet been pinned.

Never choose or write the baseline SHA here. `$implement-ticket` owns replacing `Pending` with the exact pre-mutation `HEAD`.

Do not modify closed tickets solely to normalize execution metadata.

## 4. Root Blocker Reconciliation

For each Root Blocker:

* **open** → implementation/remediation remains; reuse an applicable open ticket or create one;
* **regressed** → reuse active remediation or create a new `Regression:` ticket referencing relevant closed work;
* **unproven** → determine what the outstanding obligation actually requires;
* **satisfied** or **Owner-overridden** → no remediation ticket required.

For `unproven`:

* if current evidence identifies missing or incorrect implementation → reuse/create remediation;
* if implementation currently conforms and only required evidence remains missing → preserve the root/cell as `unproven`; do not invent implementation work.

`unproven` does not by itself determine the next workflow or require an active implementation ticket. Follow the ownership of the outstanding obligation.

Never skip an `open` or `regressed` root merely because prior covering tickets are closed.

## 5. Mode-Specific Delta Rules

### Spec Review

Create the smallest **root-complete** remediation track.

Each remediation ticket must carry:

* Root Blocker ID and invariant;
* affected sibling surfaces/reference kinds;
* production-path acceptance criteria;
* required negative/regression proof;
* applicable remaining unproven acceptance cells.

If closed work claimed to satisfy a root but current evidence shows it is `open` or `regressed`, create a new `Regression:` ticket referencing that work.

Do not create one ticket per symptom when several symptoms share one root.

### Existing Spec

Reconcile semantically, not by wording alone.

If an amended requirement changes pending work, update the existing open ticket when it still naturally owns that work.

If a closed ticket satisfied the old requirement but the amended Spec now requires more, create an ordinary new ticket for the delta.

Treat it as a regression only when previously required behavior actually broke.

Return dependency changes when new work must block an existing open ticket.

### Architecture Readiness Language

When creating or updating Architecture context, scope readiness claims to current established knowledge.

When applicable:

> All architecture decisions currently required by this ticket are accepted; no known architecture blocker remains unresolved.

Do not claim:

* `no architecture decision remains unresolved`;
* `architecture is fully resolved`;
* `all architecture is settled`;
* equivalent global/final assertions.

Ticket readiness means no **known current architecture blocker** prevents implementation.

`$implement-ticket` still owns halting on newly discovered material architecture.

Replace stale absolute readiness language when updating an open ticket.

## 6. Preserve Ticket Semantics

Every new or updated ticket must follow `$to-tickets` rules, including:

* tracer-bullet scope unless a wide-refactor exception applies;
* applicable Architecture context;
* scoped readiness language;
* correct blocking edges;
* the existing Spec's shared `Ticket branch`;
* a durable `Ticket baseline`;
* acceptance criteria proving required production behavior.

For new tickets:

```text
Ticket baseline: Pending
```

For existing open tickets:

* preserve a valid pinned SHA;
* preserve `Pending`;
* add `Pending` when the field is missing.

Never reset a pinned SHA to `Pending`.

`$to-tickets` owns approval, publishing, parent-child links, dependencies, labels, and ticket metadata.

`$implement-ticket` owns pinning `Pending` to the implementation-start `HEAD`.

## 7. Return the Delta

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
- ...
```

A metadata-only normalization is an **Update open tickets** delta.

For Spec Review remediation, also report:

* each unresolved Root Blocker;
* whether implementation remediation remains required;
* the open/new ticket covering required remediation;
* preserved unproven evidence obligations that do not currently require implementation;
* regressions and referenced closed tickets.

Never report an `open` or `regressed` Root Blocker as skipped merely because prior covering tickets are closed.

An empty delta is valid only when:

* no current requirement needs new or changed implementation work;
* no `open` or `regressed` Root Blocker lacks active remediation coverage;
* no retained open ticket requires metadata normalization;
* any remaining `unproven` obligations do not currently establish a need for implementation remediation.

Return control to `$to-tickets` at its approval/publishing step.
