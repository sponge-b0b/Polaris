---
name: to-tickets
description: Decompose one deterministic Spec contract or structured Spec Review remediation contract into executable tickets with human-approved slicing and exact machine coverage.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Tickets

## Authoritative procedure composition

Before executing this skill, read all of these files in full:

1. `.agents/skills/to-tickets/PROCEDURE.md`
2. `.agents/skills/to-tickets/CONTROL_PLANE.md`
3. `.agents/skills/to-tickets/TICKET_RESLICE_RECOVERY.md`

Compatibility form retained for policy validation: read `.agents/skills/to-tickets/PROCEDURE.md` in full.

`CONTROL_PLANE.md` preserves the previously authoritative `$to-tickets` entrypoint,
including architecture-blocker finalization, human approval, publication/readback, and the
complete actionable frontier / shared Human Handoff contract. `PROCEDURE.md` preserves the
deterministic ticketing lifecycle. `TICKET_RESLICE_RECOVERY.md` is the canonical durable
contract for live-WIP reslicing and overrides any shorter or older recovery summary in the
retained files. On any other conflict, this file wins; on conflict, this file wins. Failure to
load any required file is a Hard Blocker.

All retained requirements remain mandatory unless explicitly overridden here.

## 9A. Routed architecture-blocker finalization

The retained Section 9A remains authoritative. A deterministic `routed -> resolved`
transition must PATCH that same managed comment in place and must finish with:

```text
Unresolved/routed blockers remaining on design-ready tickets: 0
```

Before approval, the retained Attention consumer remains mandatory:

```bash
python -m scripts.workflow_attention validate \
  --result <attention-result-file> \
  --checkpoint '$to-tickets pre-publication' \
  --require-nonblocking
```

## Live-WIP reslice durability boundary

Before changing ownership or dependencies of an already-started ticket, do not merely note
that recovery may be needed later. Complete the publication-time capture in
`TICKET_RESLICE_RECOVERY.md` before human approval and before ticket/coverage/routing
mutation whenever the proposed reslice can overlap, provide, supersede, move, or precede
active WIP.

The capture must:

- leave the protected donor checkout byte-for-byte unchanged;
- preserve an already-pinned Source ticket baseline exactly;
- attribute every dirty tracked hunk and untracked path exactly once;
- determine `source-first` versus `destination-first` from the proposed native dependency
  graph;
- persist exactly one `ticket-reslice-recovery:v1` managed record on the Destination ticket;
- read that record back exactly; and
- validate the readback mechanically:

```bash
python -m scripts.workflow_reslice_recovery validate \
  --body <recovery-comment-body-file>
```

Require:

```text
TICKET RESLICE RECOVERY: VALID
```

A nonzero validator result, ambiguous donor ownership, uncertain execution order, donor
fingerprint drift, or missing recovery metadata blocks approval/publication.

For new recovery records include the explicit `Execution order` and `Destination baseline`
fields defined by the shared contract. Existing v1 records may use only the documented
machine-derivable compatibility path and must gain explicit fields at their next authorized
update.

When live-WIP recovery applies, the **Pre-publication workflow receipts** must include the
five exact current-run recovery receipt lines required by the shared contract in addition to
the retained Project Delivery, Spec contract, decomposition, architecture-blocker, and
Attention receipts.

Human approval authorizes only the exact proposal that includes this recovery state. It does
not authorize mutation of the protected donor checkout.

## Retained Human Handoff contract

The retained frontier rule is unchanged: evaluate the **complete actionable frontier** and
**Do not stop after the first actionable ticket**. Create **one handoff entry for every actionable ticket**
in ordinary destination/topology order or review-remediation proposal alias order as
applicable. Every destination is `$implement-ticket`.

Generate and verify only through:

```bash
python -m scripts.workflow_handoff generate \
  --manifest <handoff-manifest.json> \
  > <handoff-output.txt>
python -m scripts.workflow_handoff verify \
  --manifest <handoff-manifest.json> \
  --output <handoff-output.txt>
```

Require `WORKFLOW HANDOFF: VALID`. The user-visible handoff reproduces the generated output
**byte-for-byte**. **Do not emit a bare `$implement-ticket` line** and do not hand off a
participant whose native blockers or recovery state make it non-actionable.
