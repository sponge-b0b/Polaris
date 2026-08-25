---
status: superseded by ADR-0018
---

# 0016. Governed Execution Evidence Resolution Lifecycle

## Context

ADR-0013 assigns Baseline evidence production to canonical orchestration,
ADR-0014 assigns immutable workflow identity to `WorkflowRegistry`, and
ADR-0015 assigns tier-specific evidence acquisition to the request-scoped
governed-execution service. They do not determine the typed authority facts,
execution correlation, durable selection relationship, or production ordering
needed for the resolver to acquire the record without a caller-provided
evidence object or identifier.

Without those semantics, the implementation would have to invent whether
evidence is reusable across executions, how an execution identifies its
record, and when the record exists relative to governed evaluation. That would
permit stale or substituted evidence, or create an interface-local authority
path.

## Decision

`WorkflowRegistry` is the canonical source of typed **Workflow Authority
Facts**. For each registered workflow definition, those facts bind its
immutable `WorkflowIdentity` to its `RiskAuthorityContract`; they determine
the tier and evidence variant for a governed execution.

Canonical runtime/workflow orchestration creates a platform-owned execution
correlation for each governed invocation. The durable evidence selection key is
that execution correlation plus the resolved `WorkflowIdentity`. It is not a
caller-supplied workflow version, evidence object, or evidence identifier.
One canonical governed-evidence selection exists for a key: it identifies one
Baseline record for Baseline, or one matching `DecisionEvidencePacket` for
Enhanced or Vigilant.

Before a governed evaluation may begin, canonical orchestration resolves the
Workflow Authority Facts, creates and authoritatively persists the selected
tier-specific evidence for the execution, and makes the durable selection
available to the request-scoped `GovernedExecutionEvidenceResolver`. The
resolver re-acquires the record using only the platform-derived key,
reconstructs it, and validates exact identity and authority before it supplies
the typed inputs for policy/governance evaluation or issues an audit
capability.

Missing, non-unique, stale, mismatched, malformed, tampered, or unavailable
selection/evidence fails closed before evaluation, audit persistence, or
capability issuance. CLI, backtest, and other transports submit typed execution
requests only; they do not create the correlation, choose a record, or carry
an authority-bearing evidence reference.

## Rationale

An execution-scoped relation prevents valid evidence for one invocation from
being replayed for another invocation of the same workflow definition. Keeping
the authority facts adjacent to the registry-owned identity prevents an
independent tier mapping from drifting from the registered definition. Durable
production followed by resolver re-acquisition proves that enforcement used a
system-of-record record rather than an in-memory or caller-controlled value.

## Considered Options

* Reuse evidence by `WorkflowIdentity` alone. Rejected because one definition
  may have many executions, so that key cannot prevent cross-execution replay.
* Let transports provide an evidence ID or select a durable record. Rejected
  because that makes an interface an authority boundary and enables
  substitution.
* Let the resolver synthesize evidence on demand. Rejected because it would
  merge production and enforcement ownership and bypass authoritative
  persistence.

## Consequences

ADR-0013 through ADR-0015 remain active and are completed by this lifecycle
contract. Implementation must represent registry-owned Workflow Authority
Facts, platform-owned execution correlation, and the one-to-one durable
selection relationship; migrate governed callers away from evidence-carrying
requests; and preserve tier-specific Baseline versus packet semantics. This is
an accepted, realization-required decision.
