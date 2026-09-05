---
status: accepted
---

# Persist direct business truth with immutable history

## Context

Polaris must preserve what was known, what was judged, what authority acts occurred, what humans decided, and what happened later. That history must remain reconstructable without depending on workflow execution, job state, report generation, model traces, or replaying a generic runtime event stream.

Universal event sourcing or a workflow/event log could provide replay mechanics, but it would make technical execution artifacts part of the path to reconstructing business truth and would risk re-centering the architecture on runtime behavior rather than Investment Decision semantics.

## Decision

Material Polaris business facts are persisted directly under their owning domain semantics, with immutable historical facts and explicit correction, supersession, or subsequent-state relationships where change must be represented.

Durable Decision Memory is composed from those directly persisted facts across domain owners; it is not a workflow archive, generic event log, or canonical `DecisionRecord` aggregate.

Universal event sourcing is not the business persistence model for 0.2.0. Domain events or application notifications may exist for coordination, but they do not become the authoritative source from which Investment Decision history must be replayed.

## Rationale

The product's trust requirement is semantic reconstructability: a future reviewer must be able to inspect the actual decision-domain facts and attributable judgments that existed at the relevant time. Direct persistence keeps those facts authoritative independently of whatever orchestration or messaging mechanism produced them.

This also allows technical workflows, workers, model providers, and delivery mechanisms to evolve without changing the identity or historical meaning of Investment Decisions.

## Consequences

- material attributable judgments and authority acts are immutable once committed;
- later corrections or changed judgment are represented explicitly rather than silently rewriting history;
- current-state projections may exist for efficiency but cannot be the sole historical authority;
- runtime/job/model identifiers may be provenance or correlation identifiers but not business identity;
- event buses and events may be used operationally without becoming the business source of truth.
