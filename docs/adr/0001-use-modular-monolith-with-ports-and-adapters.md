---
status: accepted
---

# Use a modular monolith with ports and adapters

## Context

Polaris 0.2.0 needs strong cross-domain consistency around Investment Decision lifecycle, Evidence, Recommendation, authority, human judgment, Action Intent, and later learning. The product does not currently require independently deployed domain services, while introducing network boundaries would add distributed consistency and operational failure modes before they create product value.

At the same time, one undifferentiated application would make the greenfield reset vulnerable to recreating the pre-greenfield runtime/platform shape under new names.

## Decision

Polaris 0.2.0 will use a modular monolith with ports and adapters.

The canonical dependency direction is:

```text
interfaces -> application -> domain
                 ^            ^
                 |            |
          infrastructure -----+
```

Domain ownership is split by semantic responsibility rather than by technical workflow: Decisions, Evidence, Investment Intelligence, Portfolio & Risk, Governance & Authority, Action Continuity, and Learning.

Module boundaries are enforced inside one codebase; network boundaries are not used merely to create architectural separation.

## Rationale

A modular monolith preserves transactional reasoning and keeps the system comprehensible for the current team and maturity while still making ownership and dependency direction explicit. Ports and adapters keep external systems and infrastructure replaceable and leave open the option to extract a module later if a real scaling, deployment, or organizational boundary emerges.

The alternatives were a workflow/runtime-centric monolith, which would put technical execution back at the product center, and microservices, which would add distributed-consistency and operational complexity without a current requirement that justifies them.

## Consequences

- boundaries must be enforced by imports, contracts, and tests rather than assumed from directory names;
- application use cases own coordination and transaction semantics rather than interface or infrastructure adapters;
- infrastructure may depend inward on application/domain contracts, never the reverse;
- later service extraction is possible but must be earned by a current need rather than anticipated speculatively.
