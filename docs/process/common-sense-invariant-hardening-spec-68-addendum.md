# Spec #68 Workflow Hardening Addendum

**Status:** Active process hardening record  
**Date:** 2026-09-01  
**Governing record:** `docs/process/common-sense-invariant-hardening.md`

## Purpose

This addendum records the postmortem-derived hardening applied after the completed `$review-spec` of Spec #68 exposed false downstream completion claims.

It supplements the governing common-sense invariant-hardening record. It does not replace or narrow that record.

The changes here are deliberately **generic**. No rule depends on a Spec #68 filename, MCP implementation detail, report profile, or historical symptom.

## Postmortem Result

Backward tracing used this chain:

```text
Spec obligation
    ↓
$to-tickets coverage
    ↓
$implement-ticket implementation / acceptance reconciliation
    ↓
$verify-spec semantic proof
    ↓
$review-spec finding
```

For the confirmed Spec #68 blockers, the relevant obligations were carried into the implementation tickets. The earliest confirmed invalid lifecycle transition was ordinary `$implement-ticket` closure: the same actor implemented the candidate, interpreted the acceptance criterion, selected the proof domain/evidence, declared the criterion complete, and authorized ticket closure.

The review also demonstrated two additional facts:

1. independent verification is necessary but not sufficient when the verifier's authoritative or nested domain is incomplete;
2. Spec-level semantic proof can independently false-PASS when one proof conclusion does not actually entail every mapped Spec cell or when a quantified inner domain is never completely materialized.

Therefore the hardening target is not “add more tests” or “write stricter prose.” It is the semantic authorization boundary.

## Derived Invariants

### Independent certification at the earliest semantic close

> A candidate-producing actor may propose semantic closure evidence, but it may not authorize the semantic completion transition for that same candidate.

Every Implementation Ticket now requires a fresh non-mutating ticket closure verifier before persistence/closure, not only Review Remediation Tickets.

### One ticket certification authority

> Ordinary and remediation tickets use one closure-verification algorithm and one verdict. Remediation extends the acceptance universe; it does not create a competing verifier.

This prevents drift between “normal” and “root” closure semantics.

### Evidence entailment is per obligation

> Evidence may be shared, but every semantic obligation retains its own entailment decision.

A broad upstream architectural fact cannot silently prove a narrower externally visible, operational, or lifecycle claim merely because both concern the same subsystem.

### Nested quantified domains are transition state

> When a closure claim quantifies over a finite/discoverable domain, closure of that domain is part of the authorization state, not advisory reasoning.

Examples include profile × seam, transition × consumer, response contract × producer path, workflow invariant × entry/re-entry/fallback path, and runtime behavior × canonical composition path.

### Production behavior requires production composition proof

> Component capability is not proof of canonical operational realization when the claimed behavior depends on composition.

The verifier must follow the applicable production/composition boundary when the claim requires it.

### Fail-closed claims require meaningful falsifiers

> A negative boundary guarantee may not be certified only from well-formed canonical-path examples when an inconsistent or malformed state could still violate the boundary's own responsibility.

This does not authorize policy duplication at thin transports or adapters. The verifier tests the responsibility actually assigned to the boundary.

## Workflow Changes

### `$implement-ticket`

* common durable closure checkpoint for every ticket;
* implementation agent produces Proposed Closure Evidence only;
* automatic dispatcher-only fresh `$verify-ticket-closure` certification after the immutable checkpoint; no second human command is required for ordinary ticket closure certification;
* exact candidate/contract binding;
* PASS invalidated by substantive candidate mutation unless independently certified invalidation rules prove reuse safe;
* `IMPLEMENTED`, `CERTIFIED`, and `CLOSED` are distinct lifecycle concepts.

### `$verify-ticket-closure`

New single ticket semantic certification authority.

It independently derives:

* complete ticket acceptance universe;
* remediation/root extension when applicable;
* exact per-cell claim/domain/predicate/falsifier/evidence;
* nested quantified domains;
* production-composition proof where applicable;
* adversarial/fail-closed proof;
* one PASS/FAIL for the immutable candidate.

### `$verify-root-closure`

Retained only as a compatibility route for historical handoffs. It may not run a second root-certification algorithm or emit a new Root Closure verdict.

### `$verify-spec`

The parent retains orchestration, gates, service preflight, tests, failure disposition, repair, exact-HEAD stabilization, and receipt persistence.

At stable HEAD, one fresh non-mutating `$verify-spec-closure` certifier owns semantic proof of the deterministic Spec Contract Manifest. Parent-authored proof conclusions may not authorize PASS.

### `$verify-spec-closure`

New semantic leaf verifier for the exact integrated Spec candidate.

It is intentionally distinct from `$review-spec`: certification proves the Spec contract; review remains the later independent Standards/Spec/Architecture adversarial challenge and convergence layer.

### `$to-tickets`

Fresh Spec decomposition now closes the deterministic Spec Contract Manifest before publication.

Every Spec cell receives an explicit disposition to implementation ticket(s), verification-only responsibility, no-implementation-work with reason, or authoritative exclusion. Tickets carry exact `Spec obligations` IDs, and the parent Spec persists one Ticket Coverage Manifest.

This addresses the latent decomposition risk identified by the original audit without misclassifying it as the cause of the Spec #68 blockers.

### `$review-spec`

The adversarial review architecture remains unchanged. Frozen Blocking findings now preserve compact upstream-certification provenance when recoverable so future postmortems can trace a contradiction through ticket and Spec certification without conversational memory.

### `$verify-code`

No new lifecycle authority. Its Contract Transition Manifest and Consumer Closure Manifest remain supporting technical evidence for ticket/Spec semantic certifiers.

## Resulting Defense Layers

```text
$to-tickets
complete decomposition provenance
        ↓
$implement-ticket
implementation + proposed evidence
        ↓
$verify-ticket-closure
fresh ticket semantic certification
        ↓
$verify-spec
integration gates / repair
        ↓
$verify-spec-closure
fresh Spec semantic certification
        ↓
$review-spec
fresh adversarial Standards / Spec / Architecture review
```

Each layer answers a different question. Later layers do not excuse an earlier layer from enforcing its own transition correctly.

## Non-Goals

This hardening does not:

* encode Spec #68-specific defects into generic workflow rules;
* require whole-repository tests for every ticket;
* make `$review-spec` the first trustworthy implementation check;
* make `$verify-code` semantic ticket authority;
* require verbose private reasoning persistence;
* preserve two competing ordinary/remediation verifier algorithms;
* claim unknown-unknowns are eliminated.

The goal remains the minimum explicit and independently checkable state necessary to prevent a false semantic completion transition.
