# Ticket Reslice Recovery Contract

This file is the canonical durable contract for `<!-- ticket-reslice-recovery:v1 -->`.
Both `$to-tickets` and `$implement-ticket` must read it in full before creating, changing,
or consuming a live-WIP reslice record. Historical commits are evidence only; they are not
required to reconstruct this lifecycle.

## Purpose

A live-WIP reslice exists when current ticket ownership/dependencies change while an already-
started ticket has uncommitted work that may overlap, provide, be superseded by, move to, or
precede the new ownership. Recovery metadata protects that donor work without changing ticket
semantics.

The protected donor checkout is immutable recovery state. Never stash, reset, clean, commit,
checkout-overwrite, rebase, or otherwise mutate it merely to make the new topology executable.
All participant implementation after the reslice occurs from isolated worktrees rooted at the
current relevant shared-branch remote tip.

Native ticket/Spec dependencies determine actionability. Recovery metadata never creates or
bypasses a dependency edge.

A reslice has exactly one Source disposition:

- `execute` — Source remains a current executable ticket and one of the normal source-first or
  destination-first lifecycles applies;
- `retire` — Source's entire current contract has been removed/superseded by authoritative
  planning, so Source must close `not_planned` and must never manufacture a completion commit
  merely to satisfy recovery bookkeeping. Any reusable donor bytes are preserved for one exact
  Destination ticket, which may belong to a different Parent Spec/branch.

## Publication-time capture

Before `$to-tickets` publishes any ticket-body, coverage-manifest, routing-defect, hierarchy,
dependency, or retirement mutation that changes ownership/dependencies of an already-started
ticket:

1. fingerprint the protected donor checkout using branch/HEAD, staged diff, unstaged tracked
   diff, and every untracked path plus content hash;
2. attribute every dirty tracked hunk and untracked path exactly once;
3. determine either:
   - the relative native execution order of Source and Destination for `execute`; or
   - `destination-only` execution for a planning-retired Source;
4. capture the Source `$implement-ticket` Attention receipt identity while its Git-metadata
   receipt file is still available. For current `polaris.implement-ticket-attention/v2`
   receipts, persist the exact canonical `Attention Receipt Hash` printed by the gate; do not
   substitute the SHA-256 of the receipt file bytes, whose trailing newline is not part of
   that canonical identity;
5. persist exactly one recovery record on the Destination ticket;
6. read the record back exactly;
7. machine-validate the readback with `scripts.workflow_reslice_recovery`;
8. re-fingerprint the donor and require exact equality;
9. only then may the reconciliation reach human approval/publication.

The attribution row contract is:

```text
Donor item: <path + hunk/range or untracked path>
Durable owner: source ticket | destination ticket | shared dependency | neither
Authority: <exact current ticket/Spec/ADR obligation>
Disposition: preserve source | transplant later | exclude
```

`shared dependency` is valid only when Source remains executable. It means the bytes remain
owned by Source but are also required by Destination's later contract. It never authorizes
copying those bytes before native dependencies make Destination actionable.

For `retire`, every donor item must be attributable to `destination ticket` or `neither`.
There is no executable Source contract left to own future delivery. `destination ticket`
items use `transplant later`; `neither` items use `exclude` and remain preserved only as
historical donor state until recovery terminalization.

Ambiguous ownership is a Hard Blocker. Do not guess from filenames or implementation
convenience.

## Managed record schema

The managed comment begins exactly with:

```text
<!-- ticket-reslice-recovery:v1 -->
```

### Execute-source records

Existing v1 records without `Source disposition` remain valid and mean `execute`.
New execute-source records should include `**Source disposition:** execute` and otherwise
retain the established schema:

```text
**Status:** pending-prerequisite | source-complete | prerequisite-complete | source-reconciled
**Parent Spec:** #<n>
**Source ticket:** #<n>
**Destination ticket:** #<n>
**Source disposition:** execute
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

`Source branch` / `Destination branch`, when explicitly present on an execute-source record,
must both equal `Shared branch`. `Destination Parent Spec`, when explicitly present, must
equal `Parent Spec`.

### Retired-source records

A retired-source record is explicit and may cross a Spec/branch boundary:

```text
**Status:** pending-source-retirement | source-retired | source-reconciled
**Parent Spec:** #<source-parent-spec>
**Destination Parent Spec:** #<destination-parent-spec>
**Source ticket:** #<n>
**Destination ticket:** #<n>
**Source disposition:** retire
**Source branch:** spec-<source-parent-spec>
**Destination branch:** spec-<destination-parent-spec>
**Source ticket baseline:** <40-hex SHA>
**Reslice branch anchor:** <40-hex SHA>
**Recovery mode:** isolated-worktree
**Native execution order:** #<destination prerequisite> → ... → #<destination>
**Execution order:** destination-only
**Protected donor checkout:** <absolute path>
**Protected donor HEAD / Execution Anchor:** <40-hex SHA>
**Protected donor candidate state:** <64-hex hash>
**Protected donor Attention receipt file SHA-256:** <64-hex hash>
**Source completion commit:** Not applicable
**Source retirement:** Pending | closed-not-planned
**Destination baseline:** Pending | <40-hex SHA>
**Destination completion commit:** Pending | <40-hex SHA>
```

A retired-source record must not contain `Shared branch`; Source is no longer an executable
participant and the Destination may live on another Spec branch. Its `Native execution order`
contains the current executable Destination path only and must not contain the retired Source.

All records must contain `### Exact donor attribution at capture` and a complete table
covering every captured donor item.

### Attention receipt identity compatibility

The v1 field name `Protected donor Attention receipt file SHA-256` is retained for schema
compatibility, but for current Attention receipts its durable value is the canonical
`Attention Receipt Hash` emitted by `$implement-ticket`, not the SHA-256 of the serialized
JSON file including its trailing newline. Historical v1 records that actually captured the
raw file SHA-256 remain valid when that live file still exists and matches.

The receipt file itself lives under per-worktree Git metadata and is not part of the protected
donor candidate tree. It can therefore disappear during a lawful worktree reconstruction even
when the branch, HEAD, and candidate bytes are preserved exactly. Later live-donor validation
must always fail closed on branch, HEAD, or candidate-state drift. A missing old receipt file
does not by itself invalidate recovery once its identity has been durably captured in the
managed record. When the file still exists, its raw file SHA-256 or canonical receipt hash must
match the captured value; a present-but-mismatching receipt is a Hard Blocker.

This compatibility rule does not authorize Destination implementation. The old Source receipt
remains recovery evidence only; every executable reconciled participant still requires its own
fresh contract-bound pre-mutation Attention receipt.

## Execution order

### Source-first

Source remains executable and is transitively upstream of Destination. Typical shape:

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

### Destination-first

Source remains executable and Destination is transitively upstream of Source. This is the
historical prerequisite-extract shape.

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

### Destination-only after Source retirement

Use this mode only when authoritative planning removes the Source ticket's entire executable
contract. It is not a shortcut for an inconvenient Source implementation failure.

Lifecycle:

1. Before any retirement/publication mutation, persist `pending-source-retirement` on the
   exact Destination ticket. `Source retirement` is `Pending`; Destination baseline and
   completion remain `Pending`.
2. After human-approved `$to-tickets` publication closes Source `not_planned`, updates current
   coverage/dependencies, and exact readback proves Source no longer owns a current route,
   update the same record to `source-retired` with `Source retirement: closed-not-planned`.
   Source never receives a fabricated completion commit.
3. Destination becomes actionable only under its own current Parent Spec/branch and native
   prerequisites. Its workflow rebuilds the current Destination contract before transplant.
   If the Destination ticket itself is later deterministically reconciled, recovery follows
   the surviving Destination issue identity and its current contract; recovery metadata does
   not freeze stale ticket semantics.
4. Re-attribute the protected donor against the current Destination contract before copying.
   Transplant only rows still owned by Destination; excluded or no-longer-owned rows remain
   untouched in the donor.
5. After Destination independently verifies, commits, pushes, reads back, and closes, pin its
   baseline/completion commit and terminalize the record as `source-reconciled`.

For retired-source mode, terminal `source-reconciled` means the retired Source donor state is
durably accounted for and the Destination-owned subset has been independently delivered. It
does not imply a Source completion commit.

## Participant invariants

For every mode:

- the protected donor fingerprint must match the captured record before mutation, before
  every Human Handoff/ordinary return, and before retiring any isolated worktree;
- unexpected donor mutation is a Hard Blocker;
- every executable implementation participant rebuilds its current deterministic ticket
  contract;
- an old Attention receipt bound to a prior Ticket Contract Hash is recovery evidence only,
  not authorization for a reconciled contract;
- every isolated executable participant runs fresh pre-mutation Attention against its current
  contract and Execution Anchor;
- workflow-policy-only shared-branch advancement after the Reslice branch anchor is allowed
  only when proven semantically independent of executable ownership; a material product/
  contract change routes back to `$to-tickets`;
- no recovery transition may rewrite the Source ticket baseline;
- exact certified pushed commits, not local HEAD guesses, populate executable completion
  fields;
- do not create replacement recovery comments;
- do not delete/reset/clean the protected donor after terminalization until exact proof shows
  no unique owner-local state remains.

For execute-source mode, the second participating closer terminalizes the same record.
For retired-source mode, Destination is the only executable closer and terminalizes the same
record after Source retirement has been read back exactly.

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

The validator checks schema fields, SHA/hash shapes, Source disposition, same-Spec versus
cross-Spec branch shape, execution order, status/completion/retirement consistency, and
donor-attribution presence. A nonzero result fails closed.

When consuming an existing record, validate the live protected donor with the current
`workflow_reslice_donor` runtime as well. Branch, HEAD, and candidate-state mismatches always
fail closed. Receipt-file presence is required at publication-time capture, but later
consumption may rely on the durable recorded receipt identity when per-worktree Git metadata
has been lawfully lost; a present receipt must still match exactly under the compatibility
rule above.

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
