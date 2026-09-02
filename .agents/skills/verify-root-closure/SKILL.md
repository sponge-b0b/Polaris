---
name: verify-root-closure
description: Compatibility route for historical Spec Review remediation handoffs. Root closure is now certified by the common `$verify-ticket-closure` verifier; this skill must not run a separate certification algorithm.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Verify Root Closure — Compatibility Route

`$verify-root-closure` is no longer an independent certification authority.

The common ticket verifier owns semantic closure for both ordinary and Spec Review remediation tickets:

```text
$verify-ticket-closure
```

Remediation adds the stable Root Blocker invariant, cumulative carried acceptance cells, verification obligations, same-root preservation obligations, protected roots, and Root Invariant Sweep to the **same ticket acceptance universe**. It does not create a second verifier or verdict.

## Historical Invocation

If a human invokes `$verify-root-closure` from an older durable handoff/checkpoint:

1. recover the referenced remediation ticket and current `$implement-ticket` durable state;
2. do **not** execute the historical root-certification algorithm locally;
3. resume `$implement-ticket` compatibility routing;
4. migrate a valid legacy `<!-- implement-ticket-root-checkpoint:v1 -->` into the v2 common closure checkpoint as required by current `$implement-ticket`;
5. emit or honor the current `$verify-ticket-closure` authorization/handoff for the exact current candidate.

The historical invocation may serve as user intent to continue verification, but it does not allow the `$implement-ticket` parent to self-certify and does not make an old root PASS current proof for a changed candidate.

## Current Invocation

For a ticket already using the v2 closure checkpoint, return the canonical command:

```text
$verify-ticket-closure - <Current Ticket Title> (<Ticket URL>)
```

and route through `$implement-ticket`'s dispatcher-only continuation.

## No Parallel Verdict

Do not emit:

```text
ROOT CLOSURE: PASS
ROOT CLOSURE: FAIL
```

for new verification attempts.

The only semantic ticket verdict is:

```text
TICKET CLOSURE: PASS
TICKET CLOSURE: FAIL
```

from one fresh non-mutating `$verify-ticket-closure` verifier.

Historical Root Closure Evidence remains durable history and may be consumed as evidence by the common verifier, never as current certification authority.
