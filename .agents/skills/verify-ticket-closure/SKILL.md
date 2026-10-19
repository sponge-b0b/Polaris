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

## Result-finalization and verifier self-retraction

A retained PASS/FAIL result is **not admissible by `$implement-ticket` until one exact
result-finalization handshake completes in this same verifier context**. The parent supplies
the SHA-256 of the exact PASS/FAIL bytes it received and asks only for result finalization;
it may not argue findings, introduce new evidence, suggest a desired outcome, or ask the
verifier to reinterpret the frozen contract.

During finalization, re-check only the internal consistency of the exact returned result
against the already-bound deterministic contract and already-used evidence. Confirm that:

* every finding/falsifier is derived from an assigned cell, applicable exclusion, or valid
  gap classification rather than an out-of-contract semantic assumption;
* the result does not contain mutually incompatible claims about the same frozen predicate;
* PASS/FAIL completeness and failure-saturation statements are internally consistent with
  the result's own per-cell and guardrail dispositions.

Do not inspect new candidate evidence, mutate anything, broaden the semantic universe, or
invent a new finding during this handshake.

If the exact result remains internally consistent, return exactly:

```text
TICKET CLOSURE RESULT: CONFIRMED
Result SHA-256: <sha256 of exact PASS/FAIL bytes supplied by parent>
Ticket: #<n>
Ticket Contract Hash: <hash>
Attention Receipt Hash: <hash>
Execution Anchor: <sha>
Candidate state: <hash>
```

If this verifier discovers that its own exact PASS/FAIL is internally contradictory or
relied on an out-of-contract semantic assumption, it must retract that result itself and
return exactly:

```text
TICKET CLOSURE: INVALID
Invalid reason: self-contradictory-verdict
Retracted result SHA-256: <sha256 of exact PASS/FAIL bytes supplied by parent>
Retracted verdict: <PASS|FAIL>
Ticket: #<n>
Ticket Contract Hash: <hash>
Attention Receipt Hash: <hash>
Execution Anchor: <sha>
Candidate state: <hash>
Contradiction: <concise verifier-owned description of the incompatible or out-of-contract claim>
```

`INVALID` is not PASS or FAIL and carries no implementation finding. After emitting it,
this verifier context is finished and must not emit a replacement semantic verdict. Only
the same verifier context may retract its own result; neither `$implement-ticket` nor a
human may manufacture this payload on the verifier's behalf.

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
