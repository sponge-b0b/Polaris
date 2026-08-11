---
status: superseded by ADR-0018
---

# 0012. Governed Execution Evidence Contract

## Context

ADR-0011 correctly requires enforced workflow execution to enter through the
request-scoped `GovernedWorkflowExecutionService`, but it requires every such
execution to supply a `DecisionEvidencePacket`. ADR-0009 deliberately limits
that packet to Enhanced and Vigilant outputs because it carries claim-level
support, conflict, reconstruction, snapshot, retention, and readiness
semantics. Baseline internal runtime output still needs reconstructed authority
and provenance before governance evaluation, but does not require that
claim-level lifecycle.

## Decision

`GovernedWorkflowExecutionService` accepts one typed governed-execution
evidence boundary that is reconstructed and validated before policy or
governance evaluation and before audit persistence. It has tier-specific
variants:

* `BaselineRuntimeEvidence` binds a canonical `RiskAuthorityContract` with
  `RiskTier.BASELINE` and reconstructable runtime provenance.
* `DecisionEvidencePacket` remains the claim-level evidence variant for
  `RiskTier.ENHANCED` and `RiskTier.VIGILANT`.

Baseline evidence requires canonical authority and reconstructable runtime
provenance, but no material claims, supporting-evidence snapshots, conflict
adjudication, or decision-readiness semantics. Caller metadata, mappings, and
untyped runtime context cannot supply or replace either variant.

The request-scoped service derives the governance subject and typed audit
context from reconstructed governed-execution evidence, then issues the opaque
capability consumed by the application-scoped `WorkflowFacade`. The facade
continues to fail closed for enforced execution without that capability;
unenforced runtime-only facade use remains available.

## Rationale

This gives every governed run durable, verifiable authority and provenance
without redefining low-consequence Baseline runtime evidence as material
decision evidence. A common typed boundary prevents metadata-derived
classification and audit bypasses, while the variants retain controls in
proportion to consequence.

## Considered Options

* Extend `DecisionEvidencePacket` to Baseline. Rejected because it would make
  Baseline subject to the packet's claim, support, snapshot, retention, and
  readiness semantics, contradicting the risk-tier distinction recorded in
  ADR-0009.
* Continue to derive Baseline authority from caller metadata. Rejected because
  caller-controlled metadata cannot be canonical, durable, or safely audited.

## Consequences

ADR-0011 is superseded. The governed-execution service, its persistence seam,
and all enforced interface and backtest callers must migrate to the typed
evidence boundary. Missing, stale, substituted, malformed, or non-durable
evidence fails closed before evaluation or audit writes.
