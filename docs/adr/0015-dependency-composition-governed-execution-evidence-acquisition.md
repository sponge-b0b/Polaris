---
status: accepted
---

# 0015. Governed Execution Evidence Acquisition

## Context

ADR-0012 requires evidence reconstruction before governed execution, but CLI
and backtest requests currently expose optional governed-execution evidence and
do not populate it in production. That leaves transports able to become
evidence/tier authorities or to fail without a single canonical acquisition
path. ADR-0013 assigns Baseline production to orchestration, and ADR-0014
assigns workflow identity to the registry; their use at interface entrypoints
needs an explicit request-scoped owner.

## Decision

`GovernedWorkflowExecutionService` invokes a request-scoped application
`GovernedExecutionEvidenceResolver` before governed evaluation. The resolver:

1. resolves `WorkflowIdentity` through the canonical registry;
2. determines the applicable `RiskAuthorityContract` from platform-owned
   workflow authority facts;
3. selects the evidence variant from that authoritative tier; and
4. acquires the corresponding durable Baseline record or Enhanced/Vigilant
   `DecisionEvidencePacket` for reconstruction and exact identity validation.

CLI and backtest transports submit only typed execution requests. They do not
accept, construct, select, forward, or persist governed-execution evidence,
risk tier, authority, or evidence identifiers. The resolver returns typed
unavailable or reconstruction failures, which transports render without
fallback or local synthesis.

## Rationale

The request-scoped service is the only boundary that can combine the
registry-selected workflow with platform-owned authority and durable evidence
without exposing an alternate transport path. This preserves thin interfaces,
the canonical runtime/backtest path, and tier-specific evidence semantics.

## Considered Options

* Require CLI and backtest to provide an evidence object or ID. Rejected
  because a transport could select, substitute, or omit authority-bearing
  evidence.
* Let each transport classify the workflow tier. Rejected because risk tier is
  platform-owned authority, not presentation or scenario metadata.
* Add an interface-local evidence store or compatibility fallback. Rejected
  because it would create a parallel durable lifecycle and fail-open risk.

## Consequences

ADR-0012's typed evidence boundary remains the enforcement input, but evidence
acquisition moves behind the request-scoped application service. Implementation
must remove caller-provided evidence fields from production CLI/backtest
requests, provide the resolver through dependency composition, and preserve
typed fail-closed outcomes. This decision is accepted but implementation
pending.
