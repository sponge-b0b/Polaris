# `$implement-ticket` bounded execution and durable continuation

This file is authoritative `$implement-ticket` procedure. It strengthens the retained
implementation/Attention/verifier/WIJ procedure without changing ticket semantics, CCL,
closure criteria, or verifier independence.

It exists to prevent three failure modes:

1. a pre-closure concern that can falsify the frozen contract being mislabeled as a
   nonblocking follow-up;
2. a verifier FAIL turning `$implement-ticket` into an unbounded implementation/research
   spike; and
3. a long invocation losing substantial completed work because local WIJ state was never
   checkpointed durably before context or usage exhaustion.

Where this file conflicts with the retained `$implement-ticket` procedure or its skill-local
WIJ document on these three subjects, this file wins.

## 1. Pre-closure concern admission is fail-closed

After the normal `$attention` pre-closure sweep and before the pre-closure Attention gate,
build one exact JSON artifact with schema:

```text
polaris.implement-preclosure-concerns/v1
```

The artifact binds the exact ticket, typed contract identity, current candidate state, the
complete evidence-source set used to disposition concerns, and every material concern known
at pre-closure.

For each concern record all exact intersections with:

- assigned ticket/remediation cells;
- frozen remediation/verifier falsifiers; and
- preservation guardrails.

Disposition is exactly one of:

```text
DISPROVEN
    positive current candidate-bound evidence proves the concern cannot falsify the frozen
    contract; `disproof_evidence` is mandatory.

BLOCKING
    the concern could still falsify an assigned cell, frozen falsifier, or preservation
    guardrail, or current evidence is insufficient to disprove that possibility.

DEFERRED_OUTSIDE_CONTRACT
    the concern is genuinely outside the current frozen contract and has no intersection
    with assigned cells, frozen falsifiers, or preservation guardrails.
```

“Narrow”, “unlikely”, “future follow-up”, “separate issue”, or “not observed in the happy
path” are not disproof. A concern that intersects an assigned cell, frozen falsifier, or
preservation guardrail cannot be `DEFERRED_OUTSIDE_CONTRACT`.

Validate the artifact:

```bash
python .agents/skills/implement-ticket/scripts/bounded_execution.py concerns \
  <preclosure-concerns.json>
```

Require:

```text
PRE-CLOSURE CONCERNS: PASS
```

`PASS` means every known concern is either positively `DISPROVEN` or genuinely
`DEFERRED_OUTSIDE_CONTRACT`; there are zero `BLOCKING` rows.

The exact artifact is also mandatory input to the pre-closure Attention machine gate:

```bash
python .agents/skills/implement-ticket/scripts/attention_gate.py pre-closure \
  ... \
  --concerns <preclosure-concerns.json> \
  --attention-result <pre-closure-attention-result-file>
```

The gate fails closed unless the concern artifact is PASS and matches the exact ticket,
contract schema/hash, and current candidate state. Candidate mutation makes the concern
artifact stale.

The #465 archival-crash-window pattern is normative: if a crash window can make a committed
owner act permanently unreconstructable at an exact historical cutoff, that concern touches
the frozen historical-reconstruction obligation and is `BLOCKING` unless current proof
positively disproves it. It may not be deferred as a nonblocking follow-up.

## 2. Verifier FAIL requires triage before mutation

A confirmed independent verifier FAIL is not permission to start editing, prototyping, vendor
mechanism exploration, or architecture research in the candidate.

After persisting the exact FAIL and before **any** candidate mutation, triage each verifier
finding with one JSON artifact using schema:

```text
polaris.implement-verifier-failure-triage/v1
```

Bind the exact ticket, typed contract identity, failed candidate state, verifier-result
SHA-256, finding identity, complete triage evidence set, and the number of local corrective
attempts already made for that exact verifier-result/finding pair.

Classify exactly:

```text
IMPLEMENTATION_LOCAL
    accepted authority already fixes the observable behavior and the correction introduces
    none of the material boundaries below. Exactly one bounded local corrective attempt is
    permitted for this verifier-result/finding pair.

ROUTE_REQUIRED
    the proposed correction requires at least one material boundary not already owned as a
    private implementation choice by the frozen contract. Do not prototype the correction;
    route the exact gap to its owning workflow.
```

Material boundaries are:

```text
new runtime dependency
new deployment or database configuration requirement
new retention/recovery lifecycle
new operational responsibility
new material semantic choice
new planning/ownership change
```

Validate before mutation:

```bash
python .agents/skills/implement-ticket/scripts/bounded_execution.py triage \
  <verifier-failure-triage.json>
```

Require:

```text
VERIFIER FAILURE TRIAGE: VALID
```

For `IMPLEMENTATION_LOCAL`, every material-boundary flag must be false,
`prior_local_attempts` must be zero, and no downstream route may be named. The permitted
correction is one bounded implementation attempt. Read-only inspection needed to classify the
finding is allowed; candidate mutation or a production prototype before triage is not.

For `ROUTE_REQUIRED`, at least one material-boundary flag must be true and the exact owning
route must be `$architecture-remediation`, `$to-specs`, or `$to-tickets`. Once that condition
is known, stop implementation experimentation. A prototype is not required to prove that a
new deployment/configuration, retention/recovery, runtime dependency, operational, semantic,
or planning boundary exists.

A proposed correction that changes `wal_level`, introduces a replication slot, retains WAL,
adds a new recovery daemon/job, or otherwise creates a new operational persistence lifecycle
is therefore not an implementation-local retry merely because PostgreSQL can technically do
it. If that behavior is not already fixed/owned by the frozen ticket authority, route it
without building the production prototype.

If the one local corrective attempt mutates the candidate, all evidence invalidated by the
retained procedure remains stale. A fresh verifier result is required after the corrected
candidate re-passes the normal gates. Do not chain multiple speculative correction attempts
under one verifier FAIL.

## 3. Mandatory stage checkpoints

The shared WIJ remains non-authoritative and operationally nonblocking. This file does **not**
turn WIJ health into lifecycle authority.

Instead, `$implement-ticket` now has one workflow-durable managed checkpoint on the ticket:

```text
<!-- implement-ticket-continuation:v1
<exact polaris.implement-continuation/v1 JSON>
-->
## Implement Ticket Continuation Checkpoint

<exact machine validation receipt>
```

Maintain zero or one active marker. Update the same comment in place; do not create a trail of
active continuation comments. The JSON binds the exact ticket, typed contract identity,
branch, Execution Anchor, current candidate state, phase, completed/pending stage sets, exact
next action, reason, verifier state, and stale-evidence set.

Validate before persistence and again from the exact read-back bytes:

```bash
python .agents/skills/implement-ticket/scripts/bounded_execution.py continuation \
  <implement-continuation.json>
```

Require:

```text
IMPLEMENT TICKET CONTINUATION: VALID
```

Checkpoint only meaningful stage boundaries, never individual reads/edits/tests. A fresh
checkpoint is mandatory before crossing from each completed stage into the next substantial
stage:

```text
post-feasibility
post-pre-mutation
candidate-created
technical-checks-complete
post-pre-closure
post-verifier-result
post-verifier-triage
routing-prepared
```

For every successful durable checkpoint, best-effort append the corresponding WIJ `frontier`
or `interruption_checkpoint` event. WIJ append failure remains nonblocking because the
read-back GitHub continuation comment is the workflow-durable recovery source. Do not claim a
stage checkpoint succeeded unless the managed comment was written, read back, and revalidated.

When the invocation reaches Completed, Human Handoff, or Hard Blocker, supersede/remove the
active continuation marker as part of terminal durable reconciliation; the normal owning
terminal artifact becomes authoritative.

## 4. Durable Continuation terminal

The retained statement that `$implement-ticket` has exactly three terminal conditions is
narrowly overridden. `$implement-ticket` now has a fourth legal terminal condition:

```text
Durable Continuation
```

Durable Continuation means:

- no human decision is currently required;
- no Hard Blocker exists;
- the invocation has substantial remaining work;
- context compaction, an imminent usage boundary, or a tool/runtime boundary makes continuing
  the current invocation materially likely to lose progress or repeat expensive work; and
- the exact current state has been persisted/read back/validated in the active
  `implement-ticket-continuation:v1` comment with reason `context-compaction`,
  `usage-boundary`, or `tool-boundary`.

A `stage-checkpoint` reason by itself is not a terminal Durable Continuation.

After the first context compaction in a still-substantial `$implement-ticket` invocation,
finish the current atomic operation, refresh the durable checkpoint, and prefer Durable
Continuation before starting another broad implementation/research/verification campaign.
Likewise, after a verifier FAIL, do not begin a heavy corrective campaign until
`post-verifier-result` and `post-verifier-triage` are durably checkpointed.

The terminal output is concise:

```text
IMPLEMENT TICKET: DURABLE CONTINUATION
Ticket: #<n>
Continuation checkpoint: <GitHub comment URL>
Candidate state: <sha256>
Phase: <phase>
Next action: <exact action>
Resume: resume $implement-ticket - <Ticket Title> (<Ticket URL>)
```

This is **not** a Human Handoff and does not route to another skill. It is a safe same-workflow
boundary designed for finite context/usage budgets.

On explicit resume, current Git/GitHub/contract authority is still reconstructed first. The
validated continuation checkpoint then provides the durable stage/next-action hint; candidate-
bound technical evidence may be reused only where the retained WIJ/current-authority rules
already allow it.

## 5. Fail-closed precedence summary

The following sequences are invalid under current policy:

```text
known contract-touching concern -> call it nonblocking -> dispatch verifier

confirmed verifier FAIL -> mutate/prototype -> decide later whether architecture/planning was involved

start WIJ -> perform a long run -> never append/checkpoint -> lose context -> reconstruct everything
```

The valid sequence is:

```text
Attention concern
    -> machine concern disposition
    -> zero blockers
    -> pre-closure admission

confirmed verifier FAIL
    -> durable FAIL
    -> machine triage
    -> one bounded implementation-local correction OR immediate owning route

meaningful stage completion
    -> durable continuation checkpoint + readback
    -> optional/best-effort WIJ event
    -> next substantial stage

context/usage/tool boundary
    -> durable continuation checkpoint with interruption reason
    -> IMPLEMENT TICKET: DURABLE CONTINUATION
```
