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

`ROUTING_CONTROL_PLANE.md` preserves the previously authoritative `$implement-ticket`
entrypoint and recursively composes `PROCEDURE.md`, `EXECUTION_ANCHOR.md`, and
`CONTROL_PLANE.md`, including the protected workflow/control-plane boundary, durable routing
defects, deterministic ticket contract, Attention, closure, and shared Human Handoff rules.
`TICKET_RESLICE_RECOVERY.md` is the canonical durable contract for every
`ticket-reslice-recovery:v1` record and overrides the shorter recovery summary retained in
`PROCEDURE.md`. On any other conflict, this file wins. Failure to load either file is a Hard
Blocker.

All retained requirements remain mandatory unless explicitly overridden here.

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

## Retained protected control-plane boundary

An ordinary `$implement-ticket` invocation still has **zero authority** to alter repository
**workflow/control-plane** or semantic-authority files. There is deliberately **no `$implement-ticket` bypass flag**.
The retained `scripts.workflow_candidate_guard check` and `restore-protected` mechanics remain mandatory.

## Retained Human Handoff boundary

Every terminal **Human Handoff** from `$implement-ticket` remains bound to the shared gate,
including verifier `cell-routing-defect` -> `$to-tickets`, verifier `planning-cell-gap` -> `$to-specs`,
and `contract-authority-gap` routing. A recommendation, prose instruction, or bare downstream skill command is **not** a Human Handoff.

The exact downstream artifact rules remain:

- `$to-tickets` receives the exact current Parent Spec issue.
- `$to-specs` receives the exact current planning source for the Parent Spec.
- A current Spec issue is a durability source, not a substitute planning source.
- `$implement-ticket` receives each exact current actionable ticket issue.
- `$verify-spec` receives the exact current Parent Spec issue.

Generate/verify terminal handoffs only with:

```bash
python -m scripts.workflow_handoff generate \
  --manifest <handoff-manifest.json> \
  > <handoff-output.txt>
python -m scripts.workflow_handoff verify \
  --manifest <handoff-manifest.json> \
  --output <handoff-output.txt>
```

Require `WORKFLOW HANDOFF: VALID` and reproduce the generated block **byte-for-byte**. For a
normal post-closure frontier, evaluate the **complete current actionable ticket** frontier;
Do not stop after the first actionable ticket. Emit one manifest handoff entry for each
current actionable ticket. Do not emit a bare `$to-specs`, `$to-tickets`, `$architecture-remediation`,
`$implement-ticket`, or `$verify-spec` line as a terminal Human Handoff.
