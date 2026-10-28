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

Validate it with:

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

The record moves only:

```text
READY -> IN_PROGRESS -> CONSUMED
```

Rules:

- `READY`: downstream return is validated, but no post-route candidate mutation has started.
- Immediately before the first corrective mutation, update the same comment to `IN_PROGRESS`,
  read it back, and revalidate it.
- `IN_PROGRESS` authorizes continuation of that **same** bounded corrective campaign across
  resume/context boundaries. It does not authorize starting a second campaign.
- After the next independent verifier result or another terminal disposition, update the same
  record to `CONSUMED` and bind the fresh verifier-result SHA-256.
- A `CONSUMED` record may never return to `READY` or `IN_PROGRESS`.
- Do not create a second managed record for the same identity tuple.

A new independent verifier result or a materially changed contract is a new lifecycle input and
must be handled by its normal owning procedure; it is not a reset of this record.

## 4. Candidate and Attention gates still apply

Before the first post-route mutation:

1. require the policy-sync-aware candidate guard from `CONTROL_PLANE.md`;
2. require current contract/feasibility admission;
3. persist/read back/validate the route-return record as `IN_PROGRESS`; and
4. run the formal pre-mutation Attention gate with `--route-return` pointing to that exact
   `IN_PROGRESS` artifact.

The pre-mutation gate must prove that the route-return ticket/contract identity matches the
current invocation and that the current candidate state still equals the failed candidate state
bound by the route return. Mutation after that gate makes ordinary candidate-bound evidence
stale exactly as usual.

## 5. What one post-route attempt means

One post-route attempt is one bounded implementation campaign to satisfy the returned authority.
It may contain the cohesive edits/tests needed for that realization, but it may not branch into
multiple alternative production prototypes.

If the attempt exposes another material boundary before a fresh verifier result, stop and route
that new evidence normally. Do not manufacture another post-route epoch from the same returned
authority.

If the fresh verifier fails, triage that **new exact verifier result** under
`BOUNDED_EXECUTION.md`. The old route-return record is already consumed.

## 6. #465 normative recovery example

For #465, verifier finding `F-465-1` and the prior local attempt remain historical facts. The
repaired `$architecture-remediation` result establishes that the candidate-created
post-business-commit/pre-durable-history interval is forbidden by existing authority and returns
the unchanged remediation contract to `$implement-ticket`.

That return permits exactly one post-route compliant-realization attempt. It does not authorize
resuming the reverted logical-WAL prototype merely because that prototype exists in historical
evidence. The new realization must satisfy the existing atomic durable-admission and historical
reconstruction obligations without exposing the forbidden partial-publication state.
