# Implement Ticket Feasibility Authority Closure

This file strengthens `PRE_IMPLEMENTATION_FEASIBILITY.md` without replacing any of its
provider/dependency checks. Its purpose is to make the feasibility verdict mechanically bind
the authority evidence that existed before implementation begins, so a later step cannot use
the same evidence to invalidate a prior `IMPLEMENT TICKET FEASIBILITY: PASS` and start a new
architecture-routing loop.

## Authority closure is part of feasibility

Provider ownership alone is not enough for `PASS`.

For every required production seam, classify both:

1. **ownership status** — the existing `PRESENT_UPSTREAM`, `OWNED_BY_CURRENT_TICKET`,
   `DEFERRED_COMPOSITION`, `MISSING_UPSTREAM`, or `AMBIGUOUS_OWNER`; and
2. **authority status** — exactly one of:
   - `FIXED_UPSTREAM`;
   - `FIXED_IMPLEMENTATION_LOCAL`;
   - `FIXED_DEFERRED`;
   - `UNRESOLVED_MATERIAL_CHOICE`.

`OWNED_BY_CURRENT_TICKET` means only that the ticket owns the implementation/proof seam. It
does **not** prove that current CCL/ADR/architecture authority determines the behavior strongly
enough to implement it without inventing a new material semantic choice.

Use `FIXED_IMPLEMENTATION_LOCAL` only when current accepted authority fixes the required
observable guarantee and leaves the remaining physical encoding, private algorithm, query
organization, vendor mechanism, or equivalent realization as implementation choice.

Use `UNRESOLVED_MATERIAL_CHOICE` when correct implementation still requires choosing material
behavior not fixed by current authority. A preferred mechanism being unavailable, difficult,
or vendor-specific is not by itself an unresolved material choice.

## Machine feasibility artifact

Before emitting the human feasibility receipt, write one JSON artifact with schema:

```text
polaris.implement-feasibility/v1
```

The artifact binds:

- ticket number;
- exact typed ticket/remediation `contract_schema` plus `contract_hash`;
- branch and exact execution HEAD;
- the complete evidence source set used by feasibility;
- every required seam and its ownership + authority disposition;
- authority and realization basis for each seam;
- every materially applicable prior finding and its disposition;
- exact `PASS` or `BLOCKED` outcome;
- exact blocked classification/route when blocked.

`contract_schema` is exactly one of `polaris.ticket-contract/v1` or
`polaris.review-remediation-contract/v1`. Hash equality without schema equality is not contract
identity.

Every authority/realization/prior-finding basis must name evidence already present in the
artifact's `evidence_sources`. This makes the pre-PASS evidence frontier explicit.

Validate with:

```bash
python .agents/skills/implement-ticket/scripts/feasibility_authority.py \
  <implement-feasibility.json>
```

Require exactly one leading receipt:

```text
IMPLEMENT TICKET FEASIBILITY: PASS
```

or:

```text
IMPLEMENT TICKET FEASIBILITY: BLOCKED
```

A machine `PASS` is impossible when any seam has `UNRESOLVED_MATERIAL_CHOICE`, any required
provider remains missing/ambiguous, or a prior finding remains routing/planning-ambiguous.

The existing human-readable provider counts remain useful diagnostics, but they do not replace
the machine artifact.

## Pre-mutation gate binding

The exact validated feasibility artifact is mandatory input to the existing pre-mutation
Attention gate:

```bash
python .agents/skills/implement-ticket/scripts/attention_gate.py pre-mutation \
  --ticket <ticket-number> \
  --contract <ticket-or-remediation-contract.json> \
  --baseline <ticket-baseline> \
  --branch <ticket-branch> \
  --feasibility <implement-feasibility.json> \
  --attention-result <pre-mutation-attention-result-file>
```

The gate fails closed unless the feasibility artifact is `PASS` and matches the exact ticket,
contract schema, contract hash, branch, and current execution HEAD. This prevents a prose-only
or stale feasibility claim from authorizing mutation.

## Architecture routing after feasibility

After a validated `PASS`, `$implement-ticket` may not create or hand off an architecture
blocker using only evidence that was already in the feasibility artifact.

If later inspection shows that pre-existing evidence should have produced
`UNRESOLVED_MATERIAL_CHOICE`, the correct action is **feasibility correction**:

1. stop before product mutation when still pre-mutation;
2. rebuild the feasibility artifact as `BLOCKED` with classification
   `contract-authority-gap`;
3. validate it;
4. only then prepare architecture routing.

If genuinely new evidence appears after `PASS`, architecture routing is permitted only when
that evidence establishes a material semantic-authority gap rather than merely defeating one
implementation mechanism.

Prepare one JSON route request with schema:

```text
polaris.architecture-route-request/v1
```

It must bind the same ticket, contract schema, and contract hash and include:

- `question_kind: semantic-authority-gap`;
- the exact unresolved `authority_coordinate`;
- every governing source actually checked;
- the complete route basis;
- `post_feasibility_evidence` containing only evidence genuinely unavailable to the validated
  feasibility artifact.

Validate before any architecture Human Handoff:

```bash
python .agents/skills/architecture-remediation/scripts/architecture_route_guard.py \
  --feasibility <implement-feasibility.json> \
  --request <architecture-route-request.json>
```

Require:

```text
ARCHITECTURE ROUTE: VALID
```

For a feasibility `PASS`, an empty or pre-existing `post_feasibility_evidence` set fails
closed and requires feasibility correction instead. For feasibility `BLOCKED`, architecture
routing is allowed only when the blocked classification is exactly `contract-authority-gap`.

## Durable architecture blocker evidence

When routing is valid, persist the exact feasibility JSON, exact route-request JSON, both
machine receipts, and the normal `architecture-blocker:v1` report in the same durable source
comment or in exact linked durable comments. Read them back before finalizing the Human
Handoff.

An `architecture-blocker:v1` from `$implement-ticket` that lacks this provenance is not valid
input for new architecture decision work under this policy. `$architecture-remediation` must
send it back for feasibility correction rather than opening/reopening Wayfinder or owner
semantic work.
