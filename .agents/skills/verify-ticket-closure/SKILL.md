---
name: verify-ticket-closure
description: Independently certify whether one exact immutable candidate satisfies its frozen deterministic ticket contract; never redefine the ticket, Spec, or CCL universe.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Verify Ticket Closure

## Authoritative procedure composition

Before executing this skill, read `.agents/skills/verify-ticket-closure/PROCEDURE.md` in
full. That file preserves the complete established independent-verifier procedure. This
`SKILL.md` is the authoritative entrypoint and owns the Execution Anchor and protected
control-plane bindings below; on conflict, this file wins.

All retained frozen-contract, proof-independence, per-cell proof, exclusion-guardrail,
retry, gap-classification, PASS/FAIL completeness, and non-mutation rules remain normative.

## Execution Anchor invocation integrity

A current v3 verification dispatch must receive and bind both:

* **Ticket baseline** — immutable historical/per-ticket lineage anchor;
* **Execution Anchor** — exact fetched shared-Spec-branch commit admitted by
  `$implement-ticket` before this attempt's substantive mutation.

`TICKET_CLOSURE_STATE` is computed relative to the Execution Anchor, not relative to the
Ticket baseline. Upstream/prerequisite/shared-branch commits between those two anchors are
not part of this ticket candidate.

Before semantic proof, independently require the protected-candidate gate:

```bash
python -m scripts.workflow_candidate_guard check \
  --anchor <execution-anchor>
```

Require exact:

```text
WORKFLOW CANDIDATE GUARD: VALID
Protected control-plane paths: 0
```

A protected path is invalid verification. The verifier must not repair, restore, suppress,
format, or otherwise mutate it; return invalid verification and emit neither PASS nor FAIL.
This prevents a product-ticket candidate from laundering workflow/control-plane or semantic
authority changes through independent verification.

Mechanically admit the Attention lifecycle state with:

```bash
python .agents/skills/implement-ticket/scripts/attention_gate.py verify \
  --ticket <ticket-number> \
  --contract <ticket-or-remediation-contract.json> \
  --baseline <immutable-ticket-baseline> \
  --branch <ticket-branch> \
  --execution-anchor <execution-anchor> \
  --expected-receipt-hash <attention-receipt-hash>
```

Require exact `IMPLEMENT TICKET ATTENTION: VALID`, exact printed Ticket baseline, exact
printed Execution Anchor, and exact printed candidate state equal to the dispatched
`TICKET_CLOSURE_STATE`.

Missing/mismatched Execution Anchor, a v1 Attention receipt, HEAD movement after the anchor,
candidate state derived from Ticket baseline, or a protected control-plane candidate is
invalid verification: emit neither PASS nor FAIL. Never mint, repair, or reinterpret an
Execution Anchor in the verifier.

## Frozen result identity

Every retained PASS/FAIL result contract is strengthened to include:

```text
Ticket baseline: <immutable sha>
Execution Anchor: <sha>
Candidate state: <hash relative to Execution Anchor>
```

Retry state must preserve the same Execution Anchor unless `$implement-ticket` legally
abandons the stale attempt before mutation and starts a new pre-mutation attempt from a new
clean exact-remote anchor. A verifier never performs that transition.

Immediately before either terminal PASS or FAIL, rerun the protected-candidate gate against
the same Execution Anchor. Any protected path invalidates the verifier run.

All other result fields and proof obligations in the retained procedure remain unchanged.
