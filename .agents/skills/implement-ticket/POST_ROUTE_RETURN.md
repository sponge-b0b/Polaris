# `$implement-ticket` post-route return recovery

This file is authoritative `$implement-ticket` procedure for one narrow lifecycle boundary: a
confirmed verifier failure was triaged `ROUTE_REQUIRED`, the owning downstream workflow returned
the unchanged frozen contract to `$implement-ticket`, and implementation must now perform one
compliant realization under already-accepted authority.

It does not reopen feasibility, erase prior attempts, change ticket semantics, or authorize
repeated speculative retries.

## 1. External return creates a new bounded attempt epoch

The original `polaris.implement-verifier-failure-triage/v1` remains true historical control
evidence. In particular, `prior_local_attempts` is never reset or rewritten.

A downstream return creates one distinct **post-route attempt epoch** only when all of these are
true:

- the original triage was `ROUTE_REQUIRED`;
- the downstream result is durable and exact;
- the downstream result returns ownership to `$implement-ticket`;
- the typed ticket/remediation contract schema and hash are unchanged;
- the downstream result resolves the route through existing authority rather than creating a
  new product-semantic obligation; and
- there has been no prior post-route corrective attempt for this exact triage/route-result pair.

If the contract changed, stop this procedure and perform normal contract reconstruction,
feasibility, and lifecycle admission under the new contract. A changed contract is not a
post-route retry.

## 2. Machine route-return artifact

Before any corrective candidate mutation, build one artifact:

```text
polaris.implement-route-return/v1
```

It binds:

- exact ticket and typed contract identity;
- failed candidate state;
- exact verifier-result SHA-256 and finding identity;
- exact original triage artifact SHA-256 and owning route;
- durable route-result source and exact route-result SHA-256;
- `EXISTING_AUTHORITY_IMPLEMENTATION_RETURN`;
- unchanged-contract proof;
- prior post-route attempt count;
- complete evidence/basis set; and
- the managed attempt status.

Validate the initial record with:

```bash
python .agents/skills/implement-ticket/scripts/route_return.py \
  <implement-route-return.json>
```

Require:

```text
IMPLEMENT TICKET ROUTE RETURN: VALID
```

`prior_post_route_attempts` must be `0`. The prior local-attempt count from verifier triage may
already be nonzero; that does not consume this new authority-return epoch.

### Route-aware feasibility binding

Before post-route re-entry, a normal feasibility PASS must be bound to the route result that
returned the finding to implementation. Build `polaris.implement-post-route-context/v1` and
validate it with:

```bash
python .agents/skills/implement-ticket/scripts/post_route_control.py context \
  <post-route-context.json> \
  --feasibility <feasibility.json> \
  --route-return <READY-route-return.json>
```

Require `IMPLEMENT TICKET POST-ROUTE CONTEXT: VALID`.

The context requires the returned finding to appear in feasibility `prior_findings` as
`OWNED_BY_CURRENT_TICKET` and freezes the exact union of current feasibility evidence plus
route-return evidence as the adjudicated evidence frontier. A returned finding may not disappear
from feasibility and later be rediscovered as a routing/planning gap.

## 3. One managed record, monotonic status

Maintain exactly one managed issue comment for one identity tuple:

```text
(ticket, verifier_result_sha256, finding_id,
 triage_artifact_sha256, route_result_sha256)
```

Use marker:

```text
<!-- implement-ticket-route-return:v1
<exact polaris.implement-route-return/v1 JSON>
-->
## Implement Ticket Route Return
<exact validation receipt>
```

The normal successful path remains:

```text
READY -> IN_PROGRESS -> CONSUMED
```

Every update must be validated against the exact prior read-back artifact:

```bash
python .agents/skills/implement-ticket/scripts/route_return.py \
  --previous <previous-route-return.json> \
  <updated-route-return.json>
```

Rules:

- `READY`: downstream return is validated, but no post-route candidate mutation has started.
- `READY` is not consumed merely by reconstruction, read-only design work, failed tooling, or a
  rejected re-entry gate.
- `IN_PROGRESS` authorizes continuation of that **same** bounded corrective campaign across
  resume/context boundaries. It does not authorize starting a second campaign.
- After the next independent verifier result, update the same record to `CONSUMED`, bind the fresh
  verifier-result SHA-256, and validate the transition from the exact prior `IN_PROGRESS` bytes.
- A `CONSUMED` record may never return to `READY` or `IN_PROGRESS`.
- Do not create a second managed record for the same identity tuple.

A new independent verifier result or a materially changed contract is a new lifecycle input and
must be handled by its normal owning procedure; it is not a reset of this record.

### Exact pre-verifier terminal exception

A campaign can terminate before a fresh verifier. Do not invent a verifier digest. Build
`polaris.implement-route-terminal/v1` and validate it with:

```bash
python .agents/skills/implement-ticket/scripts/post_route_control.py terminal \
  <route-terminal.json> \
  --route-return <IN_PROGRESS-route-return.json>
```

Then pass the same artifact to the transition validator:

```bash
python .agents/skills/implement-ticket/scripts/route_return.py \
  --previous <IN_PROGRESS-route-return.json> \
  --terminal <route-terminal.json> \
  <updated-route-return.json>
```

Two fail-closed outcomes exist:

- if no corrective mutation started, the current candidate state must still equal the exact failed
  candidate, `attempt_consumed=false`, and the same record may reconcile `IN_PROGRESS -> READY`;
- if corrective mutation started, `attempt_consumed=true`, the record moves
  `IN_PROGRESS -> CONSUMED`, and the v1 legacy `result_verifier_sha256` field contains the exact
  route-terminal artifact SHA as the terminal-result digest.

The no-mutation reset is the only permitted backward status transition. It is workflow-state
reconciliation and does not create a second attempt.

## 4. Post-route re-entry is distinct from ordinary pre-mutation

The retained ordinary `$implement-ticket` pre-mutation gate intentionally requires a clean
worktree. Do **not** weaken or bypass that rule. A post-route recovery is different: its whole
purpose is to resume from the exact preserved failed candidate already bound into the route-return
record.

Therefore ordinary `attention_gate.py pre-mutation --route-return ...` is not the post-route
entry path. Before consuming `READY`, run the dedicated re-entry gate:

```bash
python .agents/skills/implement-ticket/scripts/post_route_reentry.py \
  --ticket <ticket> \
  --contract <contract.json> \
  --baseline <ticket-baseline> \
  --branch <spec-branch> \
  --execution-anchor <current-fetched-spec-branch-tip> \
  --remote origin \
  --default-branch main \
  --feasibility <polaris.implement-feasibility-v1.json> \
  --route-return <exact-READY-route-return.json> \
  --post-route-context <polaris.implement-post-route-context-v1.json> \
  --attention-result <fresh-pre-mutation-attention-result>
```

Require:

```text
IMPLEMENT TICKET ATTENTION: POST-ROUTE REENTRY VALID
```

The dedicated gate must fail closed unless all of these are true:

1. current `HEAD` equals the freshly fetched remote shared-Spec-branch tip and the supplied
   Execution Anchor;
2. current feasibility is PASS and matches the exact ticket, branch, contract, and HEAD;
3. the route-return artifact is still exactly `READY` and matches the ticket/contract;
4. the post-route context proves the returned finding remains implementation-owned and binds the
   exact feasibility/route-return evidence frontier;
5. the policy-sync-aware candidate guard passes, so no protected workflow/control-plane mutation
   is being smuggled in;
6. the current candidate-state hash equals the exact `failed_candidate_state` bound by `READY`;
   and
7. a fresh nonblocking `$implement-ticket pre-mutation` Attention result is supplied.

The dedicated re-entry gate writes the normal `polaris.implement-ticket-attention/v2` receipt
for that exact preserved candidate. It deliberately does **not** require a clean worktree because
exact candidate identity replaces cleanliness as the admission proof for this one boundary.

A candidate mismatch is not authority to reset, stash, clean, or reconstruct the candidate. Stop
and preserve the checkout.

## 5. Consume READY only after re-entry succeeds

The order is mandatory:

```text
READY
  -> route-aware feasibility/context PASS
  -> exact-candidate post-route re-entry Attention PASS
  -> READY -> IN_PROGRESS durable update/readback/transition validation
  -> first corrective candidate mutation
```

Do not move the managed record to `IN_PROGRESS` before the dedicated re-entry gate succeeds. A
re-entry tooling failure, feasibility failure, context failure, candidate mismatch, Attention
failure, or protected-path violation leaves the managed record `READY` and consumes no post-route
attempt.

Immediately after the re-entry PASS and before the first corrective edit:

1. update the same managed route-return comment from `READY` to `IN_PROGRESS`;
2. read it back;
3. validate the exact transition against the prior `READY` bytes with `route_return.py
   --previous ...`; and
4. only then begin the bounded corrective campaign.

Mutation after that point makes ordinary candidate-bound evidence stale exactly as usual.

## 6. What one post-route attempt means

One post-route attempt is one bounded implementation campaign to satisfy the returned authority.
It may contain the cohesive edits/tests needed for that realization, but it may not branch into
multiple alternative production prototypes.

### Same-boundary reroute prohibition

The returned finding is already adjudicated for this unchanged contract. It must remain
`OWNED_BY_CURRENT_TICKET` throughout the post-route epoch. An unavailable or difficult mechanism,
or deployment/retention/operational consequences already represented in the adjudicated evidence
frontier, do not convert that same finding into `planning-cell-gap`, `contract-authority-gap`, or
another route under a new label.

A pre-verifier outbound route is legal only for a materially distinct new finding first observed
after the post-route context. Build `polaris.implement-post-route-reroute/v1` and validate:

```bash
python .agents/skills/implement-ticket/scripts/post_route_control.py reroute \
  <post-route-reroute.json> \
  --context <post-route-context.json> \
  --feasibility <BLOCKED-feasibility.json>
```

Require `IMPLEMENT TICKET POST-ROUTE REROUTE: VALID` before generating any outbound lifecycle
handoff from an active post-route epoch.

The validator requires a different `new_finding_id`, keeps the returned finding
implementation-owned, requires nonempty evidence disjoint from the adjudicated context frontier,
and binds that new evidence/fact to the blocked feasibility artifact. Relabeling the returned
finding or reusing already-adjudicated evidence is invalid.

If the attempt exposes such a genuinely new material boundary before a fresh verifier result,
terminalize the current epoch exactly under section 3 before routing. Do not manufacture another
post-route epoch from the same returned authority.

If the fresh verifier fails, triage that **new exact verifier result** under
`BOUNDED_EXECUTION.md`. The old route-return record is already consumed.

## 7. #465 normative recovery example

For #465, verifier finding `F-465-1` and the prior local attempt remain historical facts. The
repaired `$architecture-remediation` result establishes that the candidate-created
post-business-commit/pre-durable-history interval is forbidden by existing authority and returns
the unchanged remediation contract to `$implement-ticket`.

That return permits exactly one post-route compliant-realization attempt. It does not authorize
resuming the reverted logical-WAL prototype merely because that prototype exists in historical
evidence. The new realization must satisfy the existing atomic durable-admission and historical
reconstruction obligations without exposing the forbidden partial-publication state.

`F-465-1` therefore remains `OWNED_BY_CURRENT_TICKET` in post-route feasibility. PostgreSQL commit
timestamp lifetime, logical-decoding/WAL-retention implications, and related operational ownership
concerns already associated with that returned boundary do not become a new planning gap merely by
being restated after re-entry.

If a defective workflow transition moved the record to `IN_PROGRESS` but no corrective product
mutation occurred and the candidate still equals the returned failed candidate, use the exact
no-mutation terminal proof to reconcile the same record back to `READY`; do not consume the one
post-route attempt.
