---
name: review-spec-remediation
description: Compatibility route for historical review-remediation handoffs. Current review finding continuity is owned directly by `$review-spec`, and executable remediation is sliced by `$to-tickets`.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Review Spec Remediation — Compatibility Route

`$review-spec-remediation` no longer owns a Root Blocker ledger, acceptance matrix, or
semantic remediation state.

Current review state is:

```text
review-spec-finding-ledger:v2
    stable RF-* identities
    exact current cell hashes
    frozen falsifiers
        ↓
$to-tickets
        ↓
polaris.review-remediation-contract/v1
```

## Historical invocation

If invoked from an older Pending Review Remediation or Root Blocker handoff:

1. recover the Parent Spec and conventional Spec Review;
2. preserve the historical Root Blocker/matrix record as history;
3. do not update or resynthesize it;
4. route to a fresh `$review-spec` for current finding-ledger v2 normalization.

Return:

```text
$review-spec - <Parent Spec Title> (<Parent Spec URL>)
```

After `$review-spec` persists current open remediation-owned `RF-*` rows, it hands off
directly to `$to-tickets`.

This compatibility skill performs no repository/tracker mutation and emits no remediation
ticket proposal.
