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
* Preserve root status, affected surfaces, production-path obligations, and unproven cells.
* Preserve `Architecture decision required` and governing authority.
* `Architecture decision required: No` is ordinary remediation.
* If any unresolved root has `Architecture decision required: Yes`, halt and return it to `$review-spec`.

Do not synthesize new roots here.

### Existing Spec

Treat the current Spec as required state.

Do not reconstruct an older revision. Existing linked tickets represent previously sliced work.

## 3. Reconcile Against Existing Tickets

Read relevant open and closed tickets, including body, acceptance criteria, dependencies, and closing context when needed.

For each current requirement or Root Blocker:

* matching **open** ticket still covering remaining work → skip;
* matching **open** ticket whose pending work changed → return an update;
* matching **closed** ticket and current obligation is actually satisfied → skip;
* matching **closed** ticket but remediation remains → create a new ticket;
* no matching ticket → create a new ticket.

A closed ticket is historical work evidence, **not proof that its requirement or Root Blocker is satisfied**.

Never reopen or rewrite a closed ticket to represent remaining work.

### Unresolved Root Rule

For every Root Blocker currently `open`, `regressed`, or `unproven`, determine whether active work is still required.

* **open** → remediation remains; an open ticket must cover it or a new ticket is required.
* **regressed** → create/reuse active remediation; if prior covering work is closed, create a new `Regression:` ticket referencing it.
* **unproven** → determine whether the missing obligation can be established by verification alone.

  * verification evidence alone is sufficient → no implementation ticket; preserve the unproven verification obligation;
  * implementation/remediation is still required, or closed work failed to establish the required behavior → create a new remediation ticket.

Do not skip an unresolved root merely because one or more covering tickets are closed.

Before treating any closed ticket as sufficient, reconcile it against the **current source state and current Root Blocker status**.

For open tickets no longer required by an amended Spec, return them for closure as superseded.

## 4. Mode-Specific Delta Rules

### Spec Review

Create the smallest **root-complete** remediation track.

Each ticket must carry:

* Root Blocker ID and invariant;
* remaining affected sibling surfaces/reference kinds;
* production-path acceptance criteria;
* required negative/regression proof;
* remaining unproven acceptance cells when applicable.

If closed work claimed to fix a root but the current review still demonstrates the violation, create a new `Regression:` ticket referencing the prior ticket.

If the root is merely `unproven`, create a new ticket only when implementation work is needed; otherwise preserve it as a verification obligation.

Do not create one ticket per symptom when several symptoms share one root.

### Existing Spec

Reconcile semantically, not by wording alone.

If an amended requirement changes pending work, update the existing open ticket when it still naturally owns that work.

If a closed ticket satisfied the old requirement but the amended Spec now requires more, create an ordinary new ticket for the delta. It is a regression only when previously required behavior actually broke.

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

Verification-only obligations:
- RB-<n>: <remaining evidence>

Skipped:
- already tracked by open ticket: ...
- already satisfied by current source: ...
```

For Spec Review remediation, also report:

* open/regressed Root Blocker IDs;
* unproven Root Blockers and whether they are remediation-required or verification-only;
* regressions and referenced closed tickets.

Never report an unresolved Root Blocker as skipped merely because its covering tickets are closed.

If the delta is empty, state why every unresolved root requires no ticket delta. Do not claim closed tickets establish satisfaction unless current source evidence does.

Return control to `$to-tickets` at its approval/publishing step.
