---
name: to-remediation-tickets
description: Compatibility route for historical remediation-ticket handoffs. Current ordinary and Spec Review ticket reconciliation is owned directly by `$to-tickets`.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Remediation Tickets — Compatibility Route

`$to-remediation-tickets` is no longer a semantic decomposition owner.

Current ticketing uses:

```text
ordinary Spec
    -> $to-tickets deterministic OBL/IMP/TEST/EXC coverage

Spec Review
    -> $to-tickets deterministic review-findings/v2 remediation contracts
```

Do not synthesize Root Blockers, acceptance matrices, semantic-consumer universes,
`ARCHSRC-*`, or prose-derived obligations here.

## Historical invocation

If invoked from an older handoff:

1. recover the referenced source;
2. preserve historical tracker artifacts unchanged;
3. determine whether the source is an ordinary Spec or conventional Spec Review;
4. return control to current `$to-tickets` with the same source.

Use:

```text
$to-tickets - <Source Title> (<Source URL>)
```

For a historical Spec Review lacking `review-spec-finding-ledger:v2`, route first to:

```text
$review-spec - <Parent Spec Title> (<Parent Spec URL>)
```

so a fresh review can normalize current findings without laundering Root Blocker semantics.

For an ordinary legacy Spec with old tickets but no v2 coverage, current `$to-tickets`
proposes a fresh human-approved mapping from exact current Spec cells. Old ticket prose is
historical execution context only.

## No mutation

This compatibility route does not:

* create/update/close tickets;
* create Root Blockers;
* reinterpret legacy acceptance prose;
* mutate Ticket Coverage Manifest;
* mutate CCL;
* publish dependencies.

Its only current function is to preserve old entry points while routing them to the
canonical owner.
