# Ticket Reslice Recovery Contract

This file is the canonical durable contract for `<!-- ticket-reslice-recovery:v1 -->`.
Both `$to-tickets` and `$implement-ticket` must read it in full before creating, changing,
or consuming a live-WIP reslice record. Historical commits are evidence only; they are not
required to reconstruct this lifecycle.

## Purpose

A live-WIP reslice exists when current ticket ownership/dependencies change while an already-
started ticket has uncommitted work that may overlap, provide, or be superseded by the new
ownership. Recovery metadata protects that donor work without changing ticket semantics.

The protected donor checkout is immutable recovery state. Never stash, reset, clean, commit,
checkout-overwrite, rebase, or otherwise mutate it merely to make the new topology executable.
All participant implementation after the reslice occurs from isolated worktrees rooted at the
current shared-branch remote tip.

Native ticket dependencies determine actionability. Recovery metadata never creates or
bypasses a dependency edge.

## Publication-time capture

Before `$to-tickets` publishes any ticket-body, coverage-manifest, routing-defect, hierarchy,
or dependency mutation that changes ownership/dependencies of an already-started ticket:

1. fingerprint the protected donor checkout using branch/HEAD, staged diff, unstaged tracked
   diff, and every untracked path plus content hash;
2. attribute every dirty tracked hunk and untracked path exactly once;
3. determine the relative native execution order of Source and Destination from the proposed
   ticket dependency graph;
4. persist exactly one recovery record on the Destination ticket;
5. read the record back exactly;
6. machine-validate the readback with `scripts.workflow_reslice_recovery`;
7. re-fingerprint the donor and require exact equality;
8. only then may the reconciliation reach human approval/publication.

The attribution row contract is:

```text
Donor item: <path + hunk/range or untracked path>
Durable owner: source ticket | destination ticket | shared dependency | neither
Authority: <exact current ticket/Spec/ADR obligation>
Disposition: preserve source | transplant later | exclude
```

`shared dependency` means the bytes remain owned by the Source ticket but are also required
by the Destination's later contract. It never authorizes copying those bytes before native
dependencies make the Destination actionable.

Ambiguous ownership is a Hard Blocker. Do not guess from filenames or implementation
convenience.

## Managed record schema

The managed comment begins exactly with:

```text
<!-- ticket-reslice-recovery:v1 -->
```

and contains these fields:

```text
**Status:** pending-prerequisite | source-complete | prerequisite-complete | source-reconciled
**Parent Spec:** #<n>
**Source ticket:** #<n>
**Destination ticket:** #<n>
**Shared branch:** <branch>
**Source ticket baseline:** <40-hex SHA>
**Reslice branch anchor:** <40-hex SHA>
**Recovery mode:** isolated-worktree
**Native execution order:** #<n> → ... → #<n>
**Execution order:** source-first | destination-first
**Protected donor checkout:** <absolute path>
**Protected donor HEAD / Execution Anchor:** <40-hex SHA>
**Protected donor candidate state:** <64-hex hash>
**Protected donor Attention receipt file SHA-256:** <64-hex hash>
**Source completion commit:** Pending | <40-hex SHA>
**Destination baseline:** Pending | <40-hex SHA>
**Destination completion commit:** Pending | <40-hex SHA>
```

New records must include `Execution order` and `Destination baseline`. A pre-existing v1
record that lacks one or both remains readable only when the missing value is mechanically
derivable: execution order from the exact `Native execution order`, and destination baseline
as `Pending` while Destination completion remains `Pending`. Persist the explicit fields at
the next owner-authorized record update.

The record must also contain `### Exact donor attribution at capture` and a complete table
covering every captured donor item.

## Execution order

Exactly one direction applies and it must agree with native dependencies:

### Source-first

Source is transitively upstream of Destination. Typical shape:

```text
Source → zero or more intermediate tickets → Destination
```

Lifecycle:

1. `pending-prerequisite`: both completion commits Pending.
2. Source becomes actionable first. `$implement-ticket`:
   - preserves the pinned Source ticket baseline;
   - creates an isolated worktree at the exact current remote shared-branch tip;
   - creates a fresh Execution Anchor there;
   - rebuilds the current Source ticket contract;
   - performs fresh contract-bound pre-mutation Attention;
   - transplants only Source-owned donor work; `shared dependency` bytes remain Source-owned;
   - independently verifies, commits, pushes, reads back, and closes Source.
3. Update the same record to `source-complete` with exact Source completion commit.
4. Intermediate native tickets execute normally in dependency order.
5. Destination becomes actionable only after all native blockers close. It executes in an
   isolated worktree at the current remote tip. If `Ticket baseline: Pending`, pin that
   isolated HEAD as Destination baseline. Consume committed upstream behavior as authority;
   do not copy preserved Source donor bytes merely because they were shared dependencies.
6. After Destination independently verifies, commits, pushes, reads back, and closes, set
   Destination baseline/completion commit and terminalize the record as `source-reconciled`.

`source-reconciled` is the retained v1 terminal spelling. In source-first mode it means both
participants are durably reconciled even though Destination closes second.

### Destination-first

Destination is transitively upstream of Source. This is the historical prerequisite-extract
shape.

Lifecycle:

1. `pending-prerequisite`: both completion commits Pending.
2. Destination becomes actionable first. Execute it in an isolated worktree at the current
   remote tip. Pin its Pending baseline there. Attribute donor bytes before any transplant;
   copy only Destination-owned bytes.
3. After Destination closes, set Destination baseline/completion commit and status
   `prerequisite-complete`.
4. Source later becomes actionable. Preserve its already-pinned baseline, create a new
   isolated worktree at the current remote tip containing the Destination completion commit,
   re-attribute donor WIP against current contracts, and transplant only remaining Source-
   owned bytes.
5. After Source closes, set Source completion commit and terminalize as `source-reconciled`.

## Participant invariants

For either execution order:

- the protected donor fingerprint must match the captured record before mutation, before
  every Human Handoff/ordinary return, and before retiring any isolated worktree;
- unexpected donor mutation is a Hard Blocker;
- every implementation participant rebuilds its current deterministic ticket contract;
- an old Attention receipt bound to a prior Ticket Contract Hash is recovery evidence only,
  not authorization for the reconciled contract;
- every isolated participant runs fresh pre-mutation Attention against its current contract
  and Execution Anchor;
- workflow-policy-only shared-branch advancement after the Reslice branch anchor is allowed
  only when proven semantically independent of Source/Destination ownership; a material
  product/contract change routes back to `$to-tickets`;
- no recovery transition may rewrite the Source ticket baseline;
- exact certified pushed commits, not local HEAD guesses, populate completion fields;
- the second participating closer terminalizes the same record; do not create replacement
  recovery comments;
- do not delete/reset/clean the protected donor after terminalization until exact proof shows
  no unique owner-local state remains.

## Machine validation

Before approval/publication and whenever `$implement-ticket` consumes or updates the record:

```bash
python -m scripts.workflow_reslice_recovery validate \
  --body <recovery-comment-body-file>
```

Require exact leading receipt:

```text
TICKET RESLICE RECOVERY: VALID
```

The validator checks schema fields, SHA/hash shapes, Source/Destination membership and order,
status/commit consistency, and donor-attribution presence. A nonzero result fails closed.

## `$to-tickets` publication receipt

When live-WIP recovery applies, the pre-publication workflow receipts additionally require:

```text
Live-WIP recovery records required: <n>
Recovery records persisted/read-back: <n>/<n>
Recovery records machine-valid: <n>/<n>
Source WIP mutation required by publication: 0
Unresolved recovery metadata: 0
```

These are current-run receipts, not prose assertions.
