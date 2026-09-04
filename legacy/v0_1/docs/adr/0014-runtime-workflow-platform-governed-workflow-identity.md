---
status: accepted
---

# 0014. Governed Workflow Identity

## Context

Governed execution must reject evidence substituted from another workflow or
definition version. `BaselineRuntimeEvidence` currently carries a workflow name
and version, while the canonical workflow definition and registry carry only a
name. `DecisionEvidencePacket` can reconstruct completed-run provenance but
also lacks a canonical workflow-version contract. Consequently, neither
evidence variant can be compared to one authoritative requested workflow
identity before the governed-execution capability is issued.

## Decision

The canonical `WorkflowRegistry` owns immutable typed `WorkflowIdentity`.
It consists of a registered workflow name and a deterministic fingerprint of
that registered workflow definition. The fingerprint is the workflow version:
it is derived from canonical definition content, is not caller-provided, and is
not an execution identifier.

The request-scoped `GovernedWorkflowExecutionService` resolves the requested
`WorkflowIdentity` through the registry before it reconstructs evidence. A
Baseline evidence record must carry exactly that identity. An Enhanced or
Vigilant packet must reconstruct durable provenance that resolves to exactly
that identity. Any absent, mismatched, or unreconstructable identity fails
closed before policy/governance evaluation or audit-capability issuance.

## Rationale

Registry ownership binds evidence to the workflow definition the platform
actually selected, rather than to a transport string or an independently
maintained version. A shared validation rule protects every governed evidence
variant while preserving their different evidence semantics: Baseline retains
runtime provenance and Enhanced/Vigilant retain claim-level packets.

## Considered Options

* Accept workflow name and version from CLI, backtest, or other callers.
  Rejected because a caller could substitute or downgrade the identity.
* Use an execution ID as the workflow version. Rejected because an execution is
  an invocation, not the definition whose authority/evidence is being bound.
* Add a manually maintained version string to each workflow definition.
  Rejected because drift between the declaration and its actual topology would
  defeat deterministic substitution detection.

## Consequences

ADR-0018's reconstruction-before-enforcement rule and ADR-0013's production
lifecycle require one registry-resolved identity. Implementation has added the
typed identity and deterministic fingerprinting, bound Baseline evidence to it,
derived packet identity from canonical provenance, and validated both before
issuing a governed-execution capability. This realization-required decision is
implemented.
