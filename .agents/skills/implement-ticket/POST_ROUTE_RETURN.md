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

It binds the exact ticket/contract, failed candidate, verifier finding, original triage, durable
route result, unchanged-contract proof, evidence/basis set, and managed attempt status.

Validate it with:

```bash
python .agents/skills/implement-ticket/scripts/route_return.py \
  <implement-route-return.json>
```

Require `IMPLEMENT TICKET ROUTE RETURN: VALID`.

`prior_post_route_attempts` must be `0`. The prior local-attempt count from verifier triage may
already be nonzero; that does not consume this authority-return epoch.

## 3. Route-aware feasibility is mandatory before re-entry

A normal feasibility PASS is not sufficient for post-route re-entry. The PASS must explicitly
retain the returned finding as implementation-owned under the route result that sent it back.

Build:

```text
polaris.implement-post-route-context/v1
```

The context binds:

- exact route-return identity and hash;
- exact PASS feasibility artifact and hash;
- returned finding/verifier/triage/route-result identities;
- `returned_disposition: OWNED_BY_CURRENT_TICKET`; and
- the exact union of current feasibility evidence and route-return evidence as the adjudicated
  evidence frontier.

The PASS feasibility must contain the returned finding in `prior_findings` with disposition
`OWNED_BY_CURRENT_TICKET`. It may not omit that finding and may not classify it as a routing,
planning, or ambiguous gap.

Validate with:

```bash
python .agents/skills/implement-ticket/scripts/post_route_control.py context \
  <post-route-context.json> \
  --feasibility <feasibility.json> \
  --route-return <READY-route-return.json>
```

Require `IMPLEMENT TICKET POST-ROUTE CONTEXT: VALID`.

This gate exists specifically to prevent a returned finding from disappearing during re-entry and
then being rediscovered after `IN_PROGRESS` as a different routing label.

## 4. Managed route-return state

Maintain exactly one managed issue comment for one identity tuple:

```text
(ticket, verifier_result_sha256, finding_id,
 triage_artifact_sha256, route_result_sha256)
```

Normal successful execution moves:

```text
READY -> IN_PROGRESS -> CONSUMED
```

Every update must be read back and validated against the exact previous artifact.

`READY` means no post-route corrective mutation has started. `IN_PROGRESS` means the exact
re-entry gates passed and the bounded campaign is admitted. `CONSUMED` means the campaign reached
a fresh verifier result or a valid pre-verifier terminal disposition after corrective mutation.

The only permitted non-monotonic recovery is a machine-proved **no-mutation terminal reset** from
`IN_PROGRESS -> READY`. It requires a valid `polaris.implement-route-terminal/v1` artifact proving
that the current candidate-state still equals the exact returned failed candidate and that no
corrective mutation started. This is workflow-state reconciliation, not a new attempt.

## 5. Exact-candidate post-route re-entry

The retained ordinary `$implement-ticket` pre-mutation gate intentionally requires a clean
worktree. Do not weaken or bypass that rule. A post-route recovery instead resumes from the exact
preserved failed candidate already bound by the route-return record.

While the managed record is still `READY`, run:

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

The gate fails closed unless current HEAD/remote, feasibility, contract, route-return, post-route
context, candidate guard, exact failed-candidate state, and fresh Attention all agree.

Only after that PASS may the same managed record transition `READY -> IN_PROGRESS`, be read back,
and be transition-validated. Only then may the first corrective edit occur.

A re-entry failure leaves `READY` unchanged and consumes no attempt.

## 6. Same-boundary reroute prohibition

The returned finding is already adjudicated for this unchanged contract. It must remain
`OWNED_BY_CURRENT_TICKET` throughout this post-route epoch.

Do **not** turn the same finding into `planning-cell-gap`, `contract-authority-gap`,
`cell-routing-defect`, or another outbound route merely because an implementation mechanism is
unavailable, inconvenient, or introduces deployment/retention/operational consequences already
present in the adjudicated evidence frontier.

A pre-verifier outbound route is legal only for a **materially distinct new finding** discovered
after the post-route context was frozen. Build:

```text
polaris.implement-post-route-reroute/v1
```

and validate:

```bash
python .agents/skills/implement-ticket/scripts/post_route_control.py reroute \
  <post-route-reroute.json> \
  --context <post-route-context.json> \
  --feasibility <BLOCKED-feasibility.json>
```

Require `IMPLEMENT TICKET POST-ROUTE REROUTE: VALID` before generating any `$to-specs`,
`$to-tickets`, `$architecture-remediation`, or other outbound lifecycle handoff from an active
post-route epoch.

The validator requires all of the following:

- `new_finding_id` differs from the returned finding;
- the returned finding remains `OWNED_BY_CURRENT_TICKET` in blocked feasibility;
- the new finding is explicitly represented as the routing/planning gap;
- `new_evidence_sources` are nonempty and disjoint from the adjudicated context frontier;
- the new evidence is present in blocked feasibility; and
- the artifact declares the new fact was first observed after the post-route context.

Relabeling the returned finding or reusing already-adjudicated evidence is invalid.

## 7. Pre-verifier terminalization

A post-route campaign can stop before a fresh verifier. The state machine must not require a fake
verifier digest.

Build:

```text
polaris.implement-route-terminal/v1
```

and validate it with:

```bash
python .agents/skills/implement-ticket/scripts/post_route_control.py terminal \
  <route-terminal.json> \
  --route-return <IN_PROGRESS-route-return.json>
```

The terminal artifact binds the exact route-return state, candidate state, whether corrective
mutation actually started, whether the attempt is consumed, durable evidence/basis, and terminal
disposition.

Then validate the route-return transition using the same terminal artifact:

```bash
python .agents/skills/implement-ticket/scripts/route_return.py \
  --previous <IN_PROGRESS-route-return.json> \
  --terminal <route-terminal.json> \
  <updated-route-return.json>
```

Rules:

- **No corrective mutation started:** `mutation_started=false`, `attempt_consumed=false`, current
  candidate state must equal the exact failed candidate, and the managed record returns
  `IN_PROGRESS -> READY`. The attempt remains available.
- **Corrective mutation started but campaign terminates before verifier:**
  `mutation_started=true`, `attempt_consumed=true`, the managed record moves
  `IN_PROGRESS -> CONSUMED`, and the legacy `result_verifier_sha256` field stores the exact
  route-terminal artifact SHA as the terminal-result digest. This field name is retained for v1
  compatibility; the terminal artifact makes its non-verifier meaning explicit.
- **Fresh verifier result exists:** use the ordinary `IN_PROGRESS -> CONSUMED` transition with the
  fresh verifier-result SHA and no route-terminal artifact.

Never invent a verifier result merely to satisfy terminalization.

## 8. What one post-route attempt means

One post-route attempt is one bounded implementation campaign to satisfy the returned authority.
It may contain cohesive edits/tests needed for that realization, but it may not branch into
multiple alternative production prototypes.

A genuinely new material boundary may route only through the validated new-finding/new-evidence
gate above. The returned finding itself remains implementation-owned.

If a fresh verifier fails, triage that **new exact verifier result** under `BOUNDED_EXECUTION.md`.
The old route-return record is consumed.

## 9. #465 normative recovery example

For #465, `F-465-1` and the prior local attempt remain historical facts. The repaired
`$architecture-remediation` result establishes that the candidate-created
post-business-commit/pre-durable-history interval is forbidden by existing authority and returns
the unchanged remediation contract to `$implement-ticket`.

Therefore `F-465-1` must remain `OWNED_BY_CURRENT_TICKET` in post-route feasibility. PostgreSQL
commit-timestamp lifetime, logical-decoding/WAL-retention implications, and operational ownership
concerns already associated with that returned boundary do not become a new planning gap merely by
being restated after re-entry.

If no corrective product mutation occurred after a defective `READY -> IN_PROGRESS` transition,
prove the unchanged failed-candidate state with `polaris.implement-route-terminal/v1` and restore
the same managed record to `READY`; do not consume the attempt.

The compliant realization must satisfy the existing atomic durable-admission and historical
reconstruction obligations without exposing the forbidden partial-publication state.
