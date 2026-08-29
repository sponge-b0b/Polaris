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

Replace ordinary vertical slicing for this invocation.

Return the delta to `$to-tickets`; do not publish here.

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

The Spec Review remains the remediation source.

The original Spec remains the branch owner.

### Existing Spec

Use the supplied Spec as source and parent.

Do not create another Spec, branch, or Spec baseline.

## 2. Recover Required State

### Spec Review

Recover the latest durable **Root Blocker Ledger** and complete cumulative acceptance matrix, including later review/remediation updates and any canonical resynthesis.

Preserve:

* stable `RB-*` IDs and invariants;
* current root status;
* affected semantic surfaces/reference kinds;
* exit checks;
* all active acceptance cells and their current statuses/evidence;
* Owner Overrides;
* `Architecture decision required`;
* governing authority and routing.

Treat legacy `closed` root status as `satisfied`.

Acceptance cells are cumulative. Do not drop a cell merely because a later review update omitted it.

Honor an explicit durable supersession, retirement, or Owner Override.

For each unresolved root partition its active cells into:

* **remediation obligations** — `open` or `regressed` cells requiring implementation;
* **verification obligations** — `unproven` cells whose missing proof does not currently require implementation;
* **preservation obligations** — `satisfied` cells that must remain satisfied while shared root surfaces change.

`Architecture decision required: No` is ordinary remediation.

If an unresolved root has `Architecture decision required: Yes`, halt ordinary remediation slicing for that root and return an **architecture-blocked remediation result** to `$to-tickets` containing:

* Root Blocker ID and invariant;
* the unresolved architecture question/conflict;
* governing authority;
* concise evidence and material consequence.

Do not route directly to `$review-spec`; `$to-tickets` owns any lifecycle Human Handoff.

Do not synthesize, broaden, split, renumber, or redefine roots here.

### Existing Spec

Treat the current Spec as required state.

Do not reconstruct an older revision.

Existing linked tickets represent previously sliced work.

## 3. Reconcile Existing Tickets

Read relevant open and closed tickets, including body, acceptance criteria, dependencies, execution metadata, and closing context when needed.

For each current requirement:

* matching **open** ticket still covering the work → reuse;
* matching **open** ticket whose pending work changed → update;
* matching **closed** ticket whose obligation is currently satisfied → keep as historical evidence;
* matching **closed** ticket but current state requires additional work → create a new ticket;
* no matching ticket → create a new ticket.

Never reopen or rewrite a closed ticket to represent new or remaining work.

Before treating closed work as sufficient historical evidence, reconcile it with current durable root state when the obligation can still be violated.

A closed ticket is historical evidence, not proof by itself and not active remediation coverage.

For open tickets no longer required by an amended Spec, return them for closure as superseded.

### Legacy Execution Metadata

For every existing open ticket retained or updated by this remediation, inspect `Ticket baseline`.

* valid full SHA → preserve exactly;
* `Pending` → preserve;
* missing → return an update adding `Ticket baseline: Pending`;
* malformed or ambiguous → report the metadata defect rather than overwrite potentially meaningful state.

A missing `Ticket baseline` makes the remediation delta non-empty even when implementation scope is otherwise current.

`Pending` means the implementation-start baseline has not yet been pinned.

Never choose or write the baseline SHA here.

`$implement-ticket` owns replacing `Pending` with the exact pre-mutation `HEAD`.

Do not modify closed tickets solely to normalize execution metadata.

## 4. Root Blocker Reconciliation

For each Root Blocker:

* **open** → implementation/remediation remains; reuse an applicable open ticket or create one;
* **regressed** → reuse active remediation or create a new `Regression:` ticket referencing relevant closed work;
* **unproven** → determine whether implementation or verification owns the remaining obligation;
* **satisfied** or **owner-overridden** → no remediation ticket is required.

For `unproven`:

* missing or incorrect implementation → reuse/create remediation;
* implementation conforms and only proof remains missing → preserve as a verification obligation; do not invent implementation work.

`unproven` does not itself require an implementation ticket.

Never skip an `open` or `regressed` root merely because prior covering tickets are closed.

### Same-Root Preservation

When an unresolved root also contains satisfied cells, those cells remain part of its closure contract.

Do not turn satisfied cells into new implementation work.

Instead, carry them into every applicable remediation ticket as **preservation obligations**.

The ticket must make clear that:

* current remediation work closes the non-satisfied cells;
* previously satisfied cells must remain satisfied;
* changes to shared surfaces must not invalidate their existing proof;
* root closure requires a final invariant sweep across the complete current root domain.

If a root requires multiple remediation tickets, each ticket carries the preservation obligations applicable to surfaces it can affect, and the final root-closing ticket carries the complete preservation set.

## 5. Mode-Specific Delta Rules

### Spec Review

Create the smallest **root-complete** remediation track.

Prefer one ticket when one fresh implementation context can remediate and prove the root. Use multiple tickets only when independently necessary stages or dependencies require them.

Each remediation ticket must carry:

* Root Blocker ID and stable invariant;
* governing Architecture context when applicable;
* affected semantic sibling surfaces/reference kinds;
* current remediation obligations;
* applicable verification obligations;
* satisfied same-root cells as explicit preservation obligations;
* production-path acceptance criteria;
* required negative/fail-closed/regression proof;
* root-complete invariant sweep required for closure.

Do not slice directly from the latest finding bullets.

Do not create one ticket per symptom when several symptoms share one root.

Do not omit satisfied cells merely because they require no new implementation.

A root-complete ticket is not complete unless an implementer and `$verify-root-closure` can determine both:

1. what must change; and
2. what established same-root behavior must remain true.

### Regression Naming

Use a `Regression:` ticket only when durable root state establishes that previously satisfied behavior was actually broken later.

A **missed prior finding**, root-definition gap, newly exposed child symptom, or incomplete prior closure is ordinary remediation unless current durable state explicitly classifies it as a regression.

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

`$implement-ticket` still owns halting on a newly discovered material architecture blocker.

Replace stale absolute readiness language when updating an open ticket.

## 6. Preserve Ticket Semantics

Every new or updated ticket must follow `$to-tickets` rules, including:

* tracer-bullet scope unless a wide-refactor exception applies;
* applicable Architecture context;
* scoped readiness language;
* correct blocking edges;
* the existing Spec's shared `Ticket branch`;
* a durable `Ticket baseline`;
* acceptance criteria proving required production behavior;
* preservation obligations for satisfied cells of an unresolved Root Blocker.

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

Return only actionable ticket changes:

```text
Architecture-blocked roots:
- RB-<n>: <question/conflict> — <governing authority/evidence>

New tickets:
- <ticket>
  Root: RB-<n>
  Remediation obligations:
  - ...
  Verification obligations:
  - ...
  Preservation obligations:
  - ...
  Root-complete sweep:
  - ...

Update open tickets:
- ...

Close as superseded:
- ...

Dependency changes:
- ...

Verification-only obligations:
- RB-<n>: ...

Skipped:
- ...
```

Omit `Architecture-blocked roots` when none exist.

For Spec Review remediation, also report:

* each unresolved Root Blocker;
* whether implementation remediation remains required;
* the open/new ticket covering required remediation;
* preservation obligations carried into that ticket;
* unproven evidence obligations that do not currently require implementation;
* actual regressions and referenced closed tickets.

Never report an `open` or `regressed` Root Blocker as skipped merely because prior covering tickets are closed.

An empty delta is valid only when:

* no current requirement needs new or changed implementation work;
* no `open` or `regressed` Root Blocker lacks active remediation coverage;
* no retained open ticket requires metadata normalization;
* any remaining `unproven` obligations require verification only.

Before returning a proposed Spec Review remediation ticket, confirm that no satisfied active cell of the same unresolved root was silently discarded.

If one was omitted from the ticket, the delta is incomplete.

The returned ticket blocks are the authoritative semantic input to `$to-tickets`' approval proposal. `$to-tickets` may improve presentation but must not condense, merge, reclassify, or omit any returned obligation.

Return control to `$to-tickets` at its approval/publishing step.

## Transition-Bound Root Delta Coverage

For Spec Review remediation, the cumulative active Root Blocker acceptance matrix is a finite source universe. Before returning any ticket delta, materialize one **Root Delta Coverage** row for every active cell of every unresolved root:

```text
Root: RB-<n>
Cell: <stable acceptance-cell ID>
Current status: <open | regressed | unproven | satisfied | owner-overridden | scope-retired>
Obligation type: <remediation | verification | preservation | retired>
Ticket mapping: <open/new ticket identity | None>
Reason/authority: <why the disposition and mapping are complete>
```

Required mapping:

* `open` / `regressed` → `remediation` and active remediation-ticket coverage;
* `unproven` → `verification` unless direct evidence establishes missing/incorrect implementation, in which case `remediation`;
* `satisfied` on an unresolved same root → `preservation`, carried to every applicable remediation ticket and completely to the final root-closing ticket;
* `owner-overridden` / durably `scope-retired` → `retired` with the exact durable authority; neither status may be inferred here.

Every active cell appears exactly once. A cell may map to more than one ticket only when shared-surface preservation or staged remediation genuinely requires it, and the reason must state why. Closed historical tickets are evidence, not active remediation coverage.

Before returning the delta require:

```text
Active root cells: <n>
Root delta rows: <n>
Missing cells: 0
Unknown cells: 0
Unclassified obligation types: 0
Required remediation without active ticket coverage: 0
Satisfied same-root cells omitted from preservation: 0
Rows without reason/authority: 0
```

An empty remediation delta is legal only after this table proves that every active cell is verification-only, preserved without new work, or durably retired/overridden. Do not derive emptiness from absence of newly noticed symptoms.
