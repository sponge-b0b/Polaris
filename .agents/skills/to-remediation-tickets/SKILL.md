---
name: to-remediation-tickets
description: Reconcile Spec Review or existing-Spec remediation into a root-complete ticket delta; remediation tickets are later certified by the common `$verify-ticket-closure` verifier.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Remediation Tickets

## Base Procedure

Read this file first, then read in full:

```text
.agents/skills/to-remediation-tickets/procedure.md
```

The base procedure remains normative for source recovery, Root Blocker/cumulative-matrix reconciliation, remediation/verification/preservation partitioning, architecture-blocked routing, existing-ticket reconciliation, root-complete ticket construction, transition-bound Root Delta Coverage, and return to `$to-tickets`.

This file supersedes only references that make `$verify-root-closure` a separate remediation certification authority.

## Common Closure Verifier

Every remediation ticket produced by this workflow is ultimately certified by:

```text
$verify-ticket-closure
```

not by a separate `$verify-root-closure` algorithm.

Interpret any base sentence of the form:

> an implementer and `$verify-root-closure` must be able to determine/prove root closure

as:

> the implementer must provide complete Proposed Closure Evidence and one fresh `$verify-ticket-closure` verifier must independently certify the combined ordinary + remediation acceptance universe.

The remediation delta must still carry all existing:

* Root Blocker ID and stable invariant;
* remediation obligations;
* verification-only obligations;
* same-root preservation obligations;
* production-path and negative/fail-closed proof requirements;
* root-complete invariant sweep;
* protected behavior needed for root closure.

Those obligations extend the common ticket acceptance universe. They are not weakened or converted into ordinary implementation-only claims.

## One Verdict

Do not design or publish remediation tickets that require:

```text
ordinary ticket verifier PASS
        ↓
root verifier PASS/FAIL
```

The required lifecycle is:

```text
implementation + Proposed Closure Evidence
        ↓
$verify-ticket-closure
  ordinary ticket obligations
  + remediation/root obligations
        ↓
one TICKET CLOSURE: PASS | FAIL
```

The historical `$verify-root-closure` skill exists only as a compatibility route for old handoffs and must not appear as the certification owner in newly proposed remediation tickets.
