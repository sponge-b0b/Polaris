---
status: accepted
---

# 0018. Governed Invocation and Output Evidence Boundaries

## Context

ADRs 0012 and 0016 require reconstructed evidence before governed execution,
but their combined wording makes a generic workflow invocation appear to need
an Enhanced/Vigilant claim packet before it can produce an output. Such a
packet cannot be validly produced before materialization: it requires typed
claims, canonical claim bindings, and reconstructable supporting evidence.

The platform must also distinguish authority for invoking a built-in workflow
from authority for publishing or promoting one of its resulting outputs.

## Decision

The canonical workflow catalog supplies the invocation-level
`RiskAuthorityContract` for each built-in workflow. `WorkflowRegistry` owns
the resulting immutable `WorkflowIdentity` and `WorkflowAuthorityFacts`. The
built-in `morning_report` invocation is Baseline. A workflow invocation is not
automatically a claim-bearing output boundary.

Canonical orchestration creates a platform-owned execution correlation and
persists one Baseline runtime-provenance record and selection for each
governed invocation. The request-scoped service re-acquires and validates that
record against the registry facts before invocation policy/governance
evaluation and opaque audit-capability issuance.

The application boundary that materializes a claim-bearing output owns
Enhanced/Vigilant packet production. It uses only typed output claims,
canonical claim bindings, completed-run provenance, immutable
`WorkflowIdentity`, and the platform-created execution correlation available
there. It persists one packet, then re-acquires and validates it before that
output's release, publication, durable-promotion, or output-governance
evaluation.

Every Enhanced/Vigilant packet carries typed immutable workflow-execution
provenance: the `WorkflowIdentity` and execution correlation. A mismatch in
workflow, definition version, execution, authority, availability, cardinality,
or reconstruction fails closed before output governance, release, audit
capability issuance, or publication. Transports submit typed requests only and
cannot provide authority facts, evidence, provenance, or evidence references.

## Rationale

This binds each form of evidence to the lifecycle point where its authoritative
inputs exist. It prevents synthetic pre-execution claims while preserving
registry-owned authority, durable re-acquisition, and transport thinness.

## Considered Options

* Produce claim packets before every workflow invocation. Rejected because no
  material output or canonical claim support exists then.
* Classify built-in workflows in CLI or backtest code. Rejected because
  transports would become an authority source.
* Treat a workflow invocation as its output's publication boundary. Rejected
  because invocation provenance and claim-bearing output evidence have
  different authoritative inputs and lifecycle timing.

## Consequences

This supersedes ADRs 0012, 0016, and 0017. Implementation must provide
catalog-owned invocation facts, Baseline invocation provenance/selection,
typed packet workflow-execution provenance, output-specific packet producers,
durable reconstruction validation, and separate invocation versus output
boundary governance paths.
