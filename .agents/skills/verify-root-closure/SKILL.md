---
name: verify-root-closure
description: Compatibility route for historical Root Blocker verification handoffs. Current review remediation is certified only through `$verify-ticket-closure` against `review-remediation-contract/v1`.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Verify Root Closure — Compatibility Route

`$verify-root-closure` is not a certification authority.

Current Review Remediation Tickets are normalized to:

```text
review-spec-finding-ledger:v2
        ↓
polaris.review-remediation-contract/v1
        ↓
$implement-ticket
        ↓
$verify-ticket-closure
```

No new `ROOT CLOSURE: PASS|FAIL` verdict exists.

## Historical invocation

If a historical ticket still depends on Root Blocker/checkpoint state:

1. recover the ticket and Parent Spec/Spec Review;
2. preserve the historical record unchanged;
3. if no current normalized RF-backed remediation contract exists, route through
   `$review-spec` and `$to-tickets` first;
4. once normalized, resume `$implement-ticket` and its v3 closure checkpoint.

If a current v3 checkpoint already exists, return:

```text
$verify-ticket-closure - <Ticket Title> (<Ticket URL>)
```

through `$implement-ticket` dispatcher recovery.

This skill never executes a separate semantic verifier and never treats an old Root PASS as
current certification for a changed candidate.
