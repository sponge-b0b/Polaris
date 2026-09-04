---
status: superseded by ADR-0018
---

# 0017. Governed Output Evidence Production and Workflow Authority Facts

## Context

ADR-0016 correctly makes `WorkflowRegistry` the owner of workflow authority
facts and prevents transports from selecting durable governed evidence. Its
pre-evaluation lifecycle, however, treats every risk tier as though valid
claim-level evidence exists before a generic workflow invocation. A
`DecisionEvidencePacket` requires material claims and reconstructable support;
those inputs arise only after an output is materialized. Producing a packet at
invocation would invent claims or use caller-controlled data.

The built-in workflow catalog also needs a platform-owned source for
invocation authority facts. Its current CLI registration cannot supply those
facts without making a transport an authority boundary.

## Decision

The canonical workflow catalog supplies the invocation-level
`RiskAuthorityContract` for each built-in workflow. The registry owns the
resulting `WorkflowAuthorityFacts`; the built-in `morning_report` invocation
is Baseline. A workflow invocation is not itself a claim-bearing output
boundary.

Canonical orchestration creates and persists Baseline runtime provenance and
its one execution-and-identity selection before a governed invocation. It then
re-acquires and validates that selection before invocation evaluation.

The application boundary that materializes a claim-bearing output owns
Enhanced/Vigilant packet production. It uses only the typed output, canonical
claim bindings, completed-run provenance, immutable `WorkflowIdentity`, and
platform-created execution correlation available at that boundary. It persists
one packet and re-acquires and validates it before the output's
release/publication governance evaluation.

Every Enhanced/Vigilant packet carries typed immutable workflow-execution
provenance: the `WorkflowIdentity` and execution correlation. Reconstruction
must reject a workflow, version, or execution mismatch before governance,
release, audit capability issuance, or publication. CLI, backtest, and other
transports remain unable to provide authority facts, evidence, provenance, or
references.

## Rationale

This preserves fail-closed authority while tying claim evidence to the output
it actually supports. It keeps the workflow catalog, registry, orchestration,
output materializers, and transports within distinct ownership boundaries.

## Considered Options

* Produce Enhanced/Vigilant packets before every workflow invocation. Rejected
  because no material output or canonical claim support exists at that point.
* Classify built-in workflows in CLI or backtest code. Rejected because
  transports would become an authority source.

## Consequences

This supersedes ADR-0016. Implementation must provide catalog-owned built-in
invocation facts, typed packet workflow-execution provenance, output-specific
packet producers, durable reconstruction validation, and separate invocation
versus output-boundary governance paths.
