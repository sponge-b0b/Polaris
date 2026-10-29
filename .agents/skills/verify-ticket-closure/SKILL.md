---
name: verify-ticket-closure
description: Independently certify whether one exact immutable candidate satisfies its frozen deterministic ticket contract; never redefine the ticket, Spec, or CCL universe.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Verify Ticket Closure

## Authoritative procedure composition

Before executing this skill, read both of these files in full:

1. `.agents/skills/verify-ticket-closure/PROCEDURE.md`
2. `.agents/skills/verify-ticket-closure/POLICY_SYNC_ADMISSION.md`

`PROCEDURE.md` preserves the complete established independent-verifier procedure.
`POLICY_SYNC_ADMISSION.md` owns the candidate-admission, Execution-Anchor, policy-sync,
Attention-identity, terminal candidate recheck, and result-finalization candidate-identity
mechanics. On those subjects it overrides retained procedure text. This `SKILL.md` is the
authoritative entrypoint; on every other conflict, this file wins. Failure to load either
retained file is invalid verification.

All retained frozen-contract, proof-independence, per-cell proof, exclusion-guardrail,
retry, gap-classification, PASS/FAIL completeness, and non-mutation rules remain normative.

## Execution Anchor invocation integrity

A current v3 verification dispatch must receive and bind both:

* **Ticket baseline** — immutable historical/per-ticket lineage anchor;
* **Execution Anchor** — exact fetched shared-Spec-branch commit admitted by
  `$implement-ticket` before this attempt's substantive mutation.

`TICKET_CLOSURE_STATE` is the exact policy-sync-aware candidate state relative to the
Execution Anchor. Upstream/prerequisite/shared-branch commits between Ticket baseline and
Execution Anchor are not part of this ticket candidate, and later committed exact-main
workflow-policy synchronization is delivery-tip history rather than candidate mutation only
when the current machine guard admits it.

Before semantic proof, independently fetch current `origin/main` and require the protected-
candidate gate defined by `POLICY_SYNC_ADMISSION.md`:

```bash
python .agents/skills/implement-ticket/scripts/candidate_guard.py check \
  --anchor <execution-anchor> \
  --remote origin \
  --default-branch main
```

Require exact:

```text
WORKFLOW CANDIDATE GUARD: VALID
Protected control-plane paths: 0
```

The verifier must execute this gate itself. It must not rely on a parent-reported guard
result. A protected path, inadmissible committed delivery-tip change, stale/non-main policy
blob, mixed policy/product commit, dirty protected path, or non-descendant HEAD is invalid
verification. The verifier must not repair, restore, suppress, format, or otherwise mutate
the candidate; return invalid verification and emit neither PASS nor FAIL.

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

Missing/mismatched Execution Anchor, a v1 Attention receipt, candidate state derived from
Ticket baseline, candidate mutation, or committed delivery-tip movement not admitted by the
policy-aware candidate guard is invalid verification: emit neither PASS nor FAIL. Never mint,
repair, or reinterpret an Execution Anchor in the verifier.

Authorized committed exact-main workflow-policy synchronization after the Execution Anchor
is not, by itself, invalid verification. It remains admissible only through the exact machine
predicates in `POLICY_SYNC_ADMISSION.md` and must be independently rechecked by this verifier.

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
Candidate state: <policy-sync-aware hash relative to Execution Anchor>
```

Retry state must preserve the same Execution Anchor unless `$implement-ticket` legally
abandons the stale attempt before mutation and starts a new pre-mutation attempt from a new
clean exact-remote anchor. A verifier never performs that transition.

Immediately before either terminal PASS or FAIL, fetch current `origin/main`, rerun the exact
policy-aware candidate guard from `POLICY_SYNC_ADMISSION.md` against the same Execution
Anchor, and rerun `attention_gate.py verify` against the same contract, Attention Receipt
Hash, and Execution Anchor. Any identity drift or inadmissible candidate/control-plane state
invalidates the verifier run and emits neither PASS nor FAIL.

All other result fields and proof obligations in the retained procedure remain unchanged.
