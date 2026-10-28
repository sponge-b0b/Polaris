---
name: implement-ticket
description: Implement one exact deterministic ticket contract, run applicable technical checks, obtain fresh independent closure proof, and close only the exact certified candidate.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Implement Ticket

## Authoritative procedure composition

Before executing this skill, read all of these files in full:

1. `.agents/skills/implement-ticket/ROUTING_CONTROL_PLANE.md`
2. `.agents/skills/to-tickets/TICKET_RESLICE_RECOVERY.md`
3. `.agents/skills/WORKFLOW_INVOCATION_JOURNAL.md`
4. `.agents/skills/implement-ticket/WORKFLOW_INVOCATION_JOURNAL.md`
5. `.agents/skills/implement-ticket/BOUNDED_EXECUTION.md`

`ROUTING_CONTROL_PLANE.md` preserves the previously authoritative `$implement-ticket`
entrypoint and recursively composes `PROCEDURE.md`, `EXECUTION_ANCHOR.md`, and
`CONTROL_PLANE.md`, including the protected workflow/control-plane boundary, durable routing
defects, deterministic ticket contract, Attention, closure, and shared Human Handoff rules.
`CONTROL_PLANE.md` additionally composes `POST_ROUTE_RETURN.md` for the narrow
existing-authority return-to-implementation boundary.
`TICKET_RESLICE_RECOVERY.md` is the canonical durable contract for every
`ticket-reslice-recovery:v1` record and overrides the shorter recovery summary retained in
`PROCEDURE.md`. `WORKFLOW_INVOCATION_JOURNAL.md` at the skills root owns the shared WIJ
storage/schema/non-authority contract; this skill's WIJ document owns only `$implement-ticket`
integration and resume classification. `BOUNDED_EXECUTION.md` owns pre-closure concern
admission, post-verifier-failure bounded triage, mandatory durable stage checkpoints, and the
narrow `Durable Continuation` terminal. On those subjects it overrides retained procedure and
skill-local WIJ language, including the retained three-terminal-condition limit. On the
post-route return boundary, `POST_ROUTE_RETURN.md` as composed by `CONTROL_PLANE.md` wins. On
any other conflict, this file wins. Failure to load any retained
execution/recovery/bounded-execution/route-return authority file is a Hard Blocker.

WIJ is a best-effort execution optimization, never a lifecycle prerequisite. Journal failure,
loss, corruption, ambiguity, or incompatibility must degrade to the ordinary current
`$implement-ticket` reconstruction and must not create a new blocker or termination state.
Only an explicit `resume $implement-ticket - <Title> (<URL>)` invocation may consume an old
journal; an ordinary invocation starts fresh. The workflow-durable
`implement-ticket-continuation:v1` comment defined by `BOUNDED_EXECUTION.md` is distinct from
WIJ and is the only source that can authorize the narrow `Durable Continuation` terminal.

All retained requirements remain mandatory unless explicitly overridden here,
`BOUNDED_EXECUTION.md`, or `POST_ROUTE_RETURN.md` on their narrow owned subjects.

## Execution-anchor invariant

Retain the accepted distinction between the immutable historical **Ticket baseline** and the
current attempt's **Execution Anchor**. Do not require the current shared branch to equal that
historical SHA. Before a fresh attempt, fetch the actual remote ticket branch and, only while
clean, fast-forward only when the local branch is strictly behind and is an ancestor. The
retained Execution Anchor and Attention-gate rules remain mandatory.

## Live-WIP recovery consumption boundary

Before ordinary Ticket-baseline handling, inspect durable recovery state exactly as required
by the shared contract. Any current recovery record that names this ticket as Source or
Destination must be read back and machine-validated before substantive mutation:

```bash
python -m scripts.workflow_reslice_recovery validate \
  --body <recovery-comment-body-file>
```

Require `TICKET RESLICE RECOVERY: VALID`. Malformed, duplicate, contradictory, ambiguous, or
native-order-inconsistent recovery state is a Hard Blocker.

### Recovery validator execution source

`scripts.workflow_reslice_recovery` is workflow control-plane runtime, not product candidate
content. Resolve and fetch the current remote default-branch tip before validating a recovery
record. When the caller branch does not contain that helper, or its helper blob is not exactly
the current default-branch blob, execute the validator from a clean detached checkout/worktree
at the exact fetched default-branch tip and pass the recovery-comment body by path. Do not
copy, cherry-pick, merge, or synchronize the validator or its workflow tests into the active
Spec branch merely to validate recovery state.

Recovery validation is read-only with respect to both the caller candidate and the protected
donor. It must not checkout, reset, stash, clean, commit, or otherwise mutate either worktree.
If the exact current default-branch validator cannot be executed and proven, fail closed;
do not fall back to a stale candidate-branch helper or manually recreate the validation.

Native dependencies determine actionability. Recovery metadata never makes a blocked ticket
actionable and never changes its deterministic ticket contract.

### Source-first recovery

When native order places Source transitively upstream of Destination:

- Source executes first from an isolated worktree at the exact current remote shared-branch
  tip while preserving its pinned historical Ticket baseline;
- the isolated worktree receives a fresh Execution Anchor and a fresh pre-mutation Attention
  receipt bound to the **current** reconciled Ticket Contract Hash;
- an old Attention receipt from the protected donor is recovery evidence only;
- transplant only Source-owned donor items. `shared dependency` items remain Source-owned and
  become ordinary committed upstream behavior for the later Destination;
- after exact certification/push/readback/closure, update the same recovery record to
  `source-complete` with the exact Source completion commit and machine-validate/read back it;
- intermediate native tickets execute normally;
- Destination executes only when its blockers close, from an isolated worktree at current
  remote tip; if its Ticket baseline is `Pending`, pin that isolated HEAD and read it back;
- after exact Destination closure, populate Destination baseline/completion commit and
  terminalize the same record as `source-reconciled` with both completion commits.

### Destination-first recovery

When native order places Destination transitively upstream of Source, preserve the historical
prerequisite-extract lifecycle from the shared contract:

- Destination executes first in an isolated worktree and, after closure, updates the record
  to `prerequisite-complete` with exact Destination baseline/completion commit;
- Source later executes from a new isolated worktree at current remote tip containing the
  prerequisite completion, re-attributing donor WIP against current contracts;
- after Source closure, populate its exact completion commit and terminalize as
  `source-reconciled`.

For either order, the protected donor checkout remains immutable. Recompute its strong
fingerprint before every Human Handoff/ordinary return and before retiring any isolated
participant worktree. The second participating closer terminalizes the same managed record;
do not create a replacement record.

### Retired-source destination recovery

When the recovery record has `Source disposition: retire`, the protected Source donor is
recovery evidence, not an executable participant. Preserve the shared contract's retirement,
attribution, fingerprint, transplant, and terminalization requirements, with this execution-
location correction:

- before the Source is durably `closed-not-planned`, do not begin Destination implementation;
- once the record is `source-retired` with `Source retirement: closed-not-planned`, the
  record's `Recovery mode: isolated-worktree` means that the **protected donor checkout**
  remains isolated and immutable; it does **not** require the Destination implementation to
  run in a separate worktree;
- the Destination follows the ordinary `$implement-ticket` shared-Spec-branch rules. When
  the caller checkout is clean, is on the exact declared Destination branch, tracks its
  exact remote branch, and can synchronize to the fetched remote tip by fast-forward only,
  execute there normally. Do not create a separate implementation worktree merely because
  the retired-source recovery record exists;
- if the caller checkout is dirty, ahead, diverged, stale, or otherwise fails the ordinary
  branch/Execution-Anchor guards, preserve it and fail closed or use an isolated worktree
  only where the ordinary caller-worktree safety rules independently require one;
- before transplant, recompute the protected donor fingerprint and re-attribute every donor
  item against the current Destination contract. Copy only still-Destination-owned bytes
  into the Destination candidate; never mutate, commit, reset, clean, or checkout-overwrite
  the protected donor;
- capture a fresh Destination Execution Anchor and fresh contract-bound pre-mutation
  Attention receipt in the actual Destination execution checkout. A donor Attention receipt
  remains recovery evidence only;
- after exact Destination certification, commit, push, readback, and closure, populate the
  exact Destination baseline/completion commit and terminalize the same managed record as
  `source-reconciled`.

This retired-source correction does not weaken execute-source recovery: source-first and
destination-first records continue to use their required isolated participant worktrees.

## Retained protected control-plane boundary

An ordinary `$implement-ticket` invocation still has **zero authority** to alter repository
**workflow/control-plane** or semantic-authority files. There is deliberately **no
`$implement-ticket` bypass flag**.

For `$implement-ticket` candidate admission, the older direct
`scripts.workflow_candidate_guard check` / `restore-protected` invocation is superseded by the
policy-sync-aware wrapper required by `CONTROL_PLANE.md`:

```text
.agents/skills/implement-ticket/scripts/candidate_guard.py
```

The canonical root guard still owns the protected-path definitions consumed by that wrapper.
This override changes attribution of already-committed authorized policy sync only; it does not
permit candidate-local edits to protected paths.

## Independent verifier result-finalization boundary

The retained dispatcher-only rule is strengthened as follows. After receiving one exact
PASS/FAIL payload from the fresh `$verify-ticket-closure` context, do **not** yet admit or
route that verdict. First compute SHA-256 over the exact returned bytes and send that same
verifier context one fixed result-finalization request containing only that digest and the
instruction to execute its authoritative result-finalization contract.

During this handshake the parent remains dispatcher-only. It must not debate a finding,
provide new evidence, suggest that the verifier is wrong, request a different semantic
interpretation, or perform its own semantic appeal. The same verifier must return exactly
one of the authoritative forms defined by `$verify-ticket-closure`:

* `TICKET CLOSURE RESULT: CONFIRMED` bound to the exact result SHA-256 and exact ticket /
  contract / Attention / Execution Anchor / candidate identities; or
* `TICKET CLOSURE: INVALID` with `Invalid reason: self-contradictory-verdict`, bound to the
  exact retracted result SHA-256 and the same identities.

Mechanically reject a confirmation/retraction whose digest or identities do not match the
exact dispatched attempt.

A confirmed result proceeds through the retained PASS/FAIL admission path unchanged, except
that a confirmed FAIL must pass the bounded verifier-failure triage in
`BOUNDED_EXECUTION.md` before any corrective candidate mutation. A self-retracted result is
neither PASS nor FAIL: preserve the original PASS/FAIL bytes as retracted evidence in the v3
attempt history, record the attempt as `invalid`, keep the candidate immutable, retire that
verifier context, and dispatch one new fresh verifier if candidate/contract/coverage/Attention
bindings remain exact.

`$implement-ticket` may not create an INVALID payload, infer self-contradiction on the
verifier's behalf, or semantically overrule a confirmed PASS/FAIL. Free-form follow-up with
a verifier after PASS/FAIL is prohibited; the one fixed result-finalization handshake is the
only same-context post-result interaction.

## Retained Human Handoff boundary

Every terminal **Human Handoff** from `$implement-ticket` remains bound to the shared gate,
including verifier `cell-routing-defect` -> `$to-tickets`, verifier `planning-cell-gap` ->
`$to-specs`, and `contract-authority-gap` routing. A recommendation, prose instruction, or bare
downstream skill command is **not** a Human Handoff.

The exact downstream artifact rules remain:

- `$to-tickets` receives the exact current Parent Spec issue.
- `$to-specs` receives the exact current planning source for the Parent Spec.
- A current Spec issue is a durability source, not a substitute planning source.
- `$implement-ticket` receives each exact current actionable ticket issue.
- `$verify-spec` receives the exact current Parent Spec issue.

Finalize terminal handoffs only through the shared runtime resolver:

```bash
python .agents/skills/shared_handoff_runtime.py finalize \
  --manifest <handoff-manifest.json> \
  --output <handoff-output.txt> \
  --repo-root .
```

The resolver may use candidate-local `scripts.workflow_handoff` only when it satisfies the
current versioned shared runtime contract. Otherwise it fetches current `origin/main`,
materializes only the canonical shared handoff runtime closure in a temporary location, and
generates/verifies there without mutating the candidate branch.

Require `WORKFLOW HANDOFF: VALID` and reproduce the generated block **byte-for-byte**. For a
normal post-closure frontier, evaluate the **complete current actionable ticket** frontier;
Do not stop after the first actionable ticket. Emit one manifest handoff entry for each
current actionable ticket. Do not emit a bare `$to-specs`, `$to-tickets`,
`$architecture-remediation`, `$implement-ticket`, or `$verify-spec` line as a terminal Human
Handoff.
