---
status: accepted
---

# 0013. Baseline Runtime Evidence Production Lifecycle

## Context

ADR-0012 requires every governed Baseline execution to reconstruct canonical
authority and durable runtime provenance before policy or governance evaluation.
The current persistence seam can reconstruct a Baseline record but has no
canonical production owner that creates and persists one. Letting CLI,
backtest, or other callers construct it would reintroduce caller-controlled
authority and create parallel evidence lifecycles.

## Decision

The canonical runtime/workflow orchestration boundary owns production of
`BaselineRuntimeEvidence`. An application-layer Baseline evidence lifecycle
service, invoked by that boundary once it holds the canonical workflow identity,
version, `RiskAuthorityContract`, and runtime provenance, is the sole component
allowed to create and authoritatively persist a Baseline evidence record.

The PostgreSQL repository remains a persistence adapter. The request-scoped
`GovernedWorkflowExecutionService` and all interface or backtest paths may only
identify, reconstruct, and consume the durable record; they may not synthesize,
replace, or persist Baseline authority or provenance. Missing or unreconstructable
records continue to fail closed under ADR-0012.

## Rationale

Placing production at canonical orchestration keeps workflow authority and
provenance adjacent to the runtime facts that establish them, while preserving
the request-scoped service as the reconstruction and enforcement boundary. It
keeps interfaces thin and PostgreSQL authoritative without broadening Baseline
into the claim-level `DecisionEvidencePacket` lifecycle.

## Considered Options

* Let CLI and backtest callers create evidence. Rejected because transports
  could supply or substitute authority and would create parallel lifecycles.
* Make the repository infer or assemble evidence. Rejected because persistence
  adapters do not own workflow classification or runtime provenance semantics.
* Create Baseline `DecisionEvidencePacket` records. Rejected by ADR-0012 and
  ADR-0009 because Baseline does not carry claim-level evidence semantics.

## Consequences

ADR-0018 carries forward the reconstruction-before-enforcement rule and this
ADR extends it with a concrete production owner. Implementation has added the
typed application lifecycle service and write contract at the canonical
orchestration boundary, while retaining reconstruction as the only accepted
enforcement input. This realization-required decision is implemented.
