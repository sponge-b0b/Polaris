# `$implement-ticket` Workflow Invocation Journal Integration

This file defines how `$implement-ticket` consumes the shared
`.agents/skills/WORKFLOW_INVOCATION_JOURNAL.md` contract.

The WIJ accelerates the current `$implement-ticket` lifecycle. It does not add a new
termination state, weaken any existing gate, or replace authoritative durable state.

## Bootstrap

A normal `$implement-ticket - <Title> (<URL>)` invocation performs the existing fresh
authoritative reconstruction and starts a new best-effort journal.

Only an explicit `resume $implement-ticket - <Title> (<URL>)` request attempts to consume a
prior nonterminal journal. Missing, ambiguous, incompatible, unreadable, corrupt, or
unwritable WIJ state falls back to the ordinary current `$implement-ticket` procedure and
must not block progress.

For a ticket under Parent Spec `#N`, the ticket issue is the journal `subject` and the Parent
Spec is `lifecycle_scope`.

## Resume invariant

The WIJ never selects the lifecycle phase. Resume first performs the current authoritative
Steps 1-3 of `$implement-ticket`:

1. re-read ticket, native parent, Parent Spec, current coverage, CCL, blockers/dependencies,
   governance, recovery records, remote/branch state, and current v3 closure checkpoint;
2. re-establish current branch/Ticket-baseline legality and any required recovery custody;
3. rebuild and validate the exact current ordinary Ticket Contract or Review Remediation
   Contract.

Only after those checks succeed may journal evidence be classified for reuse.

The consumer then recomputes the current candidate identity, compares workflow authority,
classifies journal evidence, emits a concise resume receipt, and continues at the earliest
currently required incomplete step.

## Authority snapshot

The invocation should record the materially relevant current workflow authority, including
at least the active versions of:

```text
AGENTS.md
.agents/skills/WORKFLOW_INVOCATION_JOURNAL.md
.agents/skills/implement-ticket/SKILL.md
.agents/skills/implement-ticket/ROUTING_CONTROL_PLANE.md
.agents/skills/implement-ticket/PROCEDURE.md
.agents/skills/implement-ticket/EXECUTION_ANCHOR.md
.agents/skills/implement-ticket/CONTROL_PLANE.md
.agents/skills/implement-ticket/WORKFLOW_INVOCATION_JOURNAL.md
.agents/skills/to-tickets/TICKET_RESLICE_RECOVERY.md
```

A material authority change makes prior workflow-dependent evidence ineligible for automatic
reuse in V1. Historical journal facts remain readable; current rules decide what must be
re-run.

## Binding snapshot

After current authoritative recovery/contracts are established, record the exact current
bindings when applicable:

```text
mode
branch
Ticket baseline
Execution Anchor
Parent Spec
Spec Contract Hash
Ticket Contract Hash or Review Remediation Contract Hash
coverage identity/destination
recovery record identity/status
```

These values are comparison evidence only. Resume always reconstructs them from current
authority.

## Pre-mutation Attention

After the required `$implement-ticket pre-mutation` Attention sweep and machine gate succeed,
record `check_result` with `check_id: attention-pre-mutation` and the exact receipt/binding
pointer available from the authoritative gate.

The journal entry is never proof that the gate ran. Existing Attention Git-metadata state and
current gate rules remain authoritative. WIJ loss must not create a new pre-mutation blocker;
the existing `$implement-ticket` rules determine whether current candidate state is legally
resumable.

## Implementation progress

Do not journal individual edits, reads, searches, or shell navigation. Code/product work is
already durable in the checkout.

Meaningful optional `work_completed` milestones may include:

```text
implementation-pass
migration-authored
wiki-sync
implementation-evidence-index
```

They are hints/evidence, not lifecycle truth.

## Technical-check roster

Record terminal PASS/FAIL results for applicable expensive or correctness-significant checks.
Use stable `check_id` values where selected by current workflow, including:

```text
ruff
mypy
focused-pytest
architecture-pytest
postgres-readiness
alembic-roundtrip
alembic-check
arid
jscpd
diff-check
candidate-guard
project-delivery-guard
attention-pre-closure
attention-pre-closure-verify
```

Every candidate-bound result records the exact current `$implement-ticket` candidate state.
Failures are useful history and should be journaled; a later PASS on another candidate does
not erase them.

### V1 reusable checks

With unchanged relevant workflow authority and the exact same candidate, deterministic
candidate-bound PASS evidence may be reused for expensive checks such as Ruff, Mypy,
selected pytest scopes, architecture verification, Alembic verification, Arid, JSCPD, and
diff hygiene when their recorded scope/config/external prerequisites still match.

### Always-refresh/live checks

The following are not made durable truth by WIJ and must be refreshed when required by the
current procedure:

```text
native blockers/dependencies
remote branch/tip state
current project-delivery/actionability guard
current candidate guard
mutable PostgreSQL/service readiness before another DB test operation
current external recovery/tracker state
```

When reuse is uncertain, re-run the smallest check that resolves the uncertainty.

## Pre-closure Attention

A recorded pre-closure Attention PASS never replaces the authoritative Attention receipt.
On resume with the exact candidate and recorded receipt, run the current
`attention_gate.py verify` against the current contract/baseline/branch/candidate. If that
verification succeeds, the reasoning sweep need not be repeated solely because context was
lost. Candidate mutation makes the receipt stale under the existing procedure.

## Implementation Evidence Index

The concise current Implementation Evidence Index may be stored in a `work_completed` event
because it is intentionally bounded retrieval evidence. It is reusable only while its exact
contract, Attention receipt, candidate, and technical-evidence bindings remain current.

## Durable closure checkpoint dominates WIJ

Once `implement-ticket-closure-checkpoint:v3` exists, the GitHub checkpoint is durable
closure authority. Record successful managed writes/readbacks as `external_write` events,
but on every resume read and validate the actual current v3 comment first.

Any disagreement resolves in favor of current authoritative GitHub state.

## Independent verifier

A fresh `$verify-ticket-closure` context may own a separate child WIJ. The parent records
`child_invocation_started` and exact `child_result_observed` events only; it never rewrites
child evidence.

A raw verifier PASS/FAIL is not admissible until the current same-context result-finalization
handshake completes. If context is lost after raw PASS/FAIL but before required finalization,
the WIJ may record that the raw result occurred, but it cannot salvage or certify the
verdict. Follow current closure rules and dispatch a fresh verifier attempt when required.

A finalized result already durably admitted to v3 is recovered from v3, not from WIJ.

## Verifier FAIL and corrective mutation

After implementation-owned verifier findings cause candidate mutation, old verifier evidence,
pre-closure Attention, and candidate-bound technical checks are stale exactly as required by
the current procedure. Journal history remains append-only; resume simply classifies the old
results as non-reusable.

## Certified persistence

Commit, push, exact remote readback, closure evidence, ticket closure, and recovery-record
updates may be recorded as `external_write` events only after their ordinary required
readback succeeds.

On resume, verify Git/GitHub again. A journal claim never substitutes for the current remote
branch, closure evidence, ticket state, or recovery record.

Because `$implement-ticket` candidate identity is representation-independent for unchanged
final path bytes/modes, committing an unchanged certified candidate does not itself create a
new candidate identity.

## Frontier handoff

Post-closure frontier state is always recomputed from current coverage, ticket states,
native blockers, and contract identity. Do not reuse a previously generated Human Handoff
merely because it appears in WIJ. Run the current shared handoff generate/verify gate again.

After the legal `$implement-ticket` terminal Human Handoff/Completed boundary is satisfied,
best-effort append `invocation_completed`.

## Resume receipt

Before continuing from usable WIJ state, report a concise receipt containing at least:

```text
WORKFLOW RESUME: $implement-ticket
Ticket / journal identity
current Execution Anchor and candidate
workflow-authority compatibility
reusable candidate-bound checks
checks/live state that must be refreshed
stale/non-reusable evidence
current durable v3 stage when present
actual resume point
```

If WIJ cannot be safely used, report `WORKFLOW JOURNAL: DEGRADED` (or NONE/AMBIGUOUS as
applicable) and continue the ordinary procedure without introducing a new stop condition.
