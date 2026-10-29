# Verify Ticket Closure — Policy-Sync Candidate Admission

This file owns candidate-admission mechanics for `$verify-ticket-closure` whenever the
implementation attempt has an immutable Execution Anchor and the shared Spec branch has
advanced afterward through committed workflow-policy synchronization.

It does **not** change the frozen ticket/remediation contract, verifier proof independence,
or product semantics. It only makes the verifier use the same machine-defined candidate
universe that `$implement-ticket` used to freeze the candidate it is being asked to certify.

## Core invariant

The immutable **Execution Anchor** remains the pre-mutation semantic/candidate anchor for the
attempt. Current `HEAD` may differ from that anchor only through committed delivery-tip
movement admitted by:

```text
.agents/skills/implement-ticket/scripts/candidate_guard.py
```

That guard owns the policy-sync exception and delegates protected-path definitions to the
canonical root workflow guard. A verifier must execute the guard itself; it must not trust a
parent-reported guard result.

Before semantic proof, fetch current `origin/main` and run:

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

The admitted candidate universe therefore excludes only committed policy-sync paths that
satisfy all current machine predicates, including exact-main blob equality and policy-only
commit ancestry. It continues to include dirty/staged/untracked product, test, migration,
wiki, and other candidate paths. A local edit to a synchronized policy file remains a
protected candidate violation.

The following remain invalid verification and must emit neither PASS nor FAIL:

- current `HEAD` is not a descendant of the Execution Anchor;
- committed movement after the anchor includes product/test/migration/wiki or other
  non-policy-sync paths;
- a commit mixes an otherwise admissible policy sync with non-policy content;
- a synchronized protected blob does not exactly equal current `origin/main`;
- a protected workflow/control-plane path is locally dirty/staged/untracked;
- the policy-aware guard cannot be executed and proven.

Authorized policy-only delivery-tip movement is **not** candidate mutation and does not mint
or reinterpret the Execution Anchor.

## Attention identity

After the policy-aware guard passes, mechanically admit the existing Attention receipt with:

```bash
python .agents/skills/implement-ticket/scripts/attention_gate.py verify \
  --ticket <ticket-number> \
  --contract <ticket-or-remediation-contract.json> \
  --baseline <immutable-ticket-baseline> \
  --branch <ticket-branch> \
  --execution-anchor <execution-anchor> \
  --expected-receipt-hash <attention-receipt-hash>
```

Require exact `IMPLEMENT TICKET ATTENTION: VALID`, exact Ticket baseline, exact Execution
Anchor, exact contract identity, exact Attention Receipt Hash, and exact policy-sync-aware
candidate state equal to the dispatched `TICKET_CLOSURE_STATE`.

Any retained procedure example that omits `--execution-anchor`, computes candidate identity
from Ticket baseline, or treats every `HEAD != Execution Anchor` state as invalid is
superseded by this file.

## Terminal verifier recheck

Immediately before emitting either terminal `TICKET CLOSURE: PASS` or `TICKET CLOSURE: FAIL`,
the same verifier context must:

1. fetch current `origin/main` again;
2. rerun the exact policy-aware candidate guard above against the same Execution Anchor;
3. rerun `attention_gate.py verify` against the same contract, Attention Receipt Hash, and
   Execution Anchor;
4. require the recomputed candidate state to equal the originally dispatched
   `TICKET_CLOSURE_STATE`.

If any identity or admission predicate changed, return `TICKET CLOSURE: INVALID`; emit
neither PASS nor FAIL.

## Result-finalization boundary

The same policy-aware candidate admission remains authoritative during the verifier's
result-finalization handshake. The handshake does not re-open semantic proof, but a result
confirmation may not bind a different Execution Anchor or candidate state.

Proof independence is preserved: `$verify-ticket-closure` independently runs the machine
admission checks and independently proves the frozen semantic contract. Sharing the exact
candidate-universe definition with `$implement-ticket` prevents the two workflows from
certifying different byte sets; it does not let the implementation actor certify itself.
