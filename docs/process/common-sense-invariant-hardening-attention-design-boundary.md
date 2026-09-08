# Common-Sense Invariant Hardening — Attention and Design Boundary

## Purpose

This record preserves the owner-approved hardening decisions made after implementation of Spec #278 Ticket #294 exposed a gap between strong upstream domain semantics and implementation-time public-contract choices.

It is durable process rationale and ChatGPT reconstitution context. Active agent behavior is enforced through `AGENTS.md`, `$attention`, and the owning workflow skills/policies.

## Triggering observations

Ticket #294 correctly inherited several frozen Investment Decision semantics, including explicit durable identity, identity independence from mutable Decision facts and technical execution, unresolved/partial Scope, immutable lifecycle facts, and non-destructive history.

However, implementation still selected consequential public representations that upstream authority had not explicitly established, including a non-empty `str` carrier for opaque domain identities and the context-free exported name `FactMetadata`.

The owner determined that this is not merely a local code-quality concern. It exposes a workflow boundary defect: implementation must not silently choose among materially different public/domain/downstream contracts simply because the higher-level semantic requirement is already known.

The owner also established a standing requirement that agents act as proactive project **Attention**: they must surface material concerns when noticed rather than relying on the owner to discover every suspicious choice.

## Frozen invariants

### 1. Proactive Attention Duty

At every level of Polaris work, an agent must surface material concerns promptly when noticed.

The current task is the immediate work surface, not the boundary of Attention. While doing the work in front of it, the agent must also evaluate what the current observation implies for Polaris as a whole across materially implicated product intent, domain semantics, architecture, authority, code, persistence, APIs, tests, documentation/wiki knowledge, workflow/process state, tracker/governance state, and upstream/downstream contracts.

This duty applies during analysis, architecture, design, specification, ticketing, implementation, verification, review, remediation, and ordinary repository work.

Use the materiality threshold:

> **Would a competent architect who understood Polaris as a whole want this brought to their attention now?**

If yes, surface it without waiting for the owner to notice first. If no, continue without distraction.

Attention is sensing/reporting authority only. It grants no authority to mutate, redesign, expand scope, approve a recommendation, or override an owning workflow.

Passing checks or lacking authority to fix a concern does not authorize silence.

### 2. Attention and authority remain separate

```text
ATTENTION
notice + surface
        ↓
AUTHORITY
existing source/workflow determines who may decide
        ↓
ACTION
mutation only after applicable authority permits it
```

A concern blocks only when an existing governing rule makes it blocking.

### 3. Implementation executes frozen design

`$implement-ticket` is not a design phase.

A material choice is not implementation-owned when two reasonable implementations could satisfy the written requirement while creating materially different public, product, domain, architecture, persistence, or downstream behavior/contracts.

Such a choice is an upstream design gap and fails closed before implementation selects a resolution.

Private semantically equivalent mechanics remain implementation-owned.

### 4. Readiness is stronger than coverage

Spec/ticket obligation coverage is necessary but insufficient.

Before implementation handoff, upstream authority must establish every material contract on which implementation or downstream consumers will rely, including identity/generation semantics, public type meaning, cardinality, lifecycle/temporal behavior, authority/provenance meaning, persistence-visible identity/reference contracts, and externally observable failure semantics where applicable.

### 5. Independent verification checks ownership of design

A ticket candidate may not pass semantic closure merely because tests and written acceptance criteria pass if implementation introduced a material public/domain contract that current authority never established.

### 6. Naming participates in domain correctness

Exported domain/public names must carry enough bounded-context meaning to remain understandable at their import/use site. Generic names such as `Fact`, `Record`, `Data`, `Metadata`, `State`, or `Manager` require qualification when the owning concept is necessary to understand the type.

This is not a demand for verbose names everywhere; it prevents exported vocabulary from depending on hidden conversational or file-local context.

## Formal Attention checkpoints

`AGENTS.md` prescribes `$attention` at the following transition boundaries:

- `$wayfinder` before route-clear/downstream handoff;
- `$to-specs` before implementation-ready publication/amendment;
- `$to-tickets` before proposal-readiness certification/publication;
- `$architecture-remediation` before bounded closure and downstream handoff;
- `$implement-ticket` before first substantive mutation and before closure candidate freeze;
- `$verify-ticket-closure` during independent adversarial certification;
- `$verify-spec` before integrated semantic certification finalizes;
- `$review-spec` before review exit/handoff.

Every formal checkpoint uses the current artifact as the starting surface, not as a limit on what may deserve Attention. Continuous spontaneous Polaris-wide Attention remains required between checkpoints.

## #294 remediation consequence

Closed Ticket #294 remains historical truth for the contract it actually implemented. It is not rewritten as though later design decisions existed at the time.

The active #278 line must instead:

1. audit every public/durable contract introduced by #294;
2. classify each as explicitly authorized, semantically equivalent implementation mechanic, or unowned design;
3. resolve unowned design upstream before code correction;
4. amend Spec #278/coverage as required;
5. create explicit remediation work rather than rewriting #294 history;
6. prevent #295 from advancing until the foundation contract is again implementation-ready and remediated.

## Non-goals

This hardening does not:

- give agents unilateral design authority;
- require agents to interrupt for trivial stylistic preferences;
- turn every private implementation choice into a Spec decision;
- create a second backlog or project-state registry;
- allow Attention to expand active scope silently;
- replace existing architecture, specification, ticketing, verification, or review authority.