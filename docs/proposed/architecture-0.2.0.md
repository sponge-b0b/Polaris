# Polaris 0.2.0 Greenfield Architecture

**Status:** Proposed  
**Release:** 0.2.0  
**Roadmap milestone:** R1 — Greenfield architecture and component ownership  
**Purpose:** Define the smallest current architecture that can satisfy the approved 0.2.0 requirements without inheriting pre-greenfield implementation topology.

## Authority and derivation

This architecture is derived from:

- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md) — approved 0.2.0 requirements;
- [`../roadmap/0.2.0.md`](../roadmap/0.2.0.md) — approved 0.2.0 delivery sequence;
- [`../product/domain-model.md`](../product/domain-model.md) and [`../../CONTEXT.md`](../../CONTEXT.md) — frozen domain semantics and canonical vocabulary;
- the current product doctrine under `docs/product/`.

`legacy/v0_1/` is not an architectural authority and was not used to choose this topology. Legacy implementation may be inspected only after this architecture establishes a current owner and need for the responsibility being implemented.

This document describes architectural ownership, dependency direction, business-truth boundaries, and the initial technical shape. It does not prescribe every class, table, endpoint, model, vendor, or deployment detail.

---

# 1. Architectural decision

Polaris 0.2.0 will be a **modular monolith with ports and adapters**.

The system will have one canonical Python product codebase under `src/polaris/`, explicit module boundaries enforced inside the codebase, inward-owned ports for required external or infrastructural capabilities, and replaceable adapters for persistence, durable asynchronous follow-up, models, external Evidence, authoritative Portfolio State, external execution observations, identity, scheduling, observability, configuration, and presentation surfaces.

Conceptually:

```text
Human / machine surfaces
        │
        ▼
┌───────────────────────────────────────────────┐
│               APPLICATION                    │
│  commands · queries · use-case coordination  │
│  transaction ownership · idempotency         │
│  inward-owned capability ports               │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────┐
│                 DOMAIN                        │
│                                               │
│  Decisions      Evidence       Intelligence   │
│  Portfolio      Governance     Continuity     │
│  Learning                                      │
│                                               │
│  canonical semantics · invariants · judgments │
└──────────────────────┬────────────────────────┘
                       │ ports owned inward
          ┌────────────┴────────────┐
          ▼                         ▼
┌────────────────────┐    ┌────────────────────┐
│ INFRASTRUCTURE     │    │ EXTERNAL SYSTEMS   │
│ persistence        │    │ Evidence providers │
│ durable follow-up  │    │ Portfolio sources  │
│ model adapters     │    │ brokers/execution  │
│ source adapters    │    │ model providers    │
│ identity/secrets   │    │ distribution       │
│ scheduling         │    │ identity systems   │
│ observability      │    │ infrastructure     │
└────────────────────┘    └────────────────────┘
```

The architectural center is the **Investment Decision lifecycle and its durable business facts**, not a runtime graph, agent system, report pipeline, event stream, database product, message broker, or persistence record type.

## Why a modular monolith

A modular monolith is the smallest architecture that fits the current product and team maturity while preserving strong semantic boundaries.

It is preferred for 0.2.0 because:

- many load-bearing invariants cross Decision, Evidence, Recommendation, authority, human judgment, and later continuity;
- the approved release requires trustworthy transactional business truth more than independent service scaling;
- the product has no requirement for independently deployed domain services;
- network boundaries would add distributed consistency and operational failure modes before they create product value;
- a small team can reason about, test, and evolve one deployable codebase more reliably;
- ports and strict import rules preserve replacement and later extraction options if a real scaling or organizational boundary appears.

A modular monolith is not permission to create one undifferentiated package. Boundaries are enforced by dependency rules and ownership, not by network calls.

---

# 2. Dependency direction and technology insulation

The canonical dependency rule is:

```text
interfaces ───────► application ───────► domain
                         ▲                  ▲
                         │                  │
                  infrastructure ───────────┘
```

More precisely:

- `domain` depends only on the Python standard library and deliberately approved domain-support libraries if later justified;
- `application` depends on `domain` and defines the ports required by its use cases;
- `infrastructure` implements application/domain-facing ports and may depend inward on their contracts;
- `interfaces` call application commands and queries and may depend on presentation DTOs owned by the application boundary;
- `domain` must not import `application`, `infrastructure`, or `interfaces`;
- `application` must not import concrete `infrastructure` or `interfaces` implementations;
- no current package may import, wrap, extend, execute through, or runtime-load `legacy/`.

Dependency direction will be enforced by executable architecture tests rather than documentation alone.

## Technology-insulation principle

Polaris architecture owns **required semantics and guarantees**. Adapters own vendors, protocols, infrastructure products, and replaceable implementation patterns.

When Polaris depends on a capability whose implementation is external, infrastructural, vendor-specific, or materially volatile, the dependency should normally sit behind an inward-owned port unless that technology is itself part of the product semantics.

This principle applies particularly to:

- durable persistence;
- asynchronous follow-up and messaging;
- model/provider access;
- Evidence sources;
- authoritative Portfolio State sources;
- execution-observation sources;
- identity providers;
- secrets backends;
- schedulers;
- notification/distribution systems;
- observability backends;
- caches, object stores, retrieval/vector stores, and similar infrastructure if later required.

Ports must express what the application or domain requires, not mirror a vendor API. Examples include:

```text
persist these decision-domain changes atomically
load this historical Decision Memory view
invoke this analytical model capability
observe authoritative Portfolio State
register required durable asynchronous follow-up
resolve authenticated actor context
```

rather than:

```text
execute SQL
publish to Kafka
call vendor X endpoint
write to Redis
```

This does **not** require an abstraction around every library. Pure internal helpers, standard parsing utilities, calculation libraries, UUID generation, and similar implementation details do not earn ports merely because they could someday be replaced.

The rule is:

> **Abstract across boundaries of ownership, authority, infrastructure, or meaningful volatility—not across every import.**

## Replaceability without lowest-common-denominator design

Technology insulation does not require crippling adapters to the weakest feature set shared by every conceivable implementation.

An adapter may use technology-specific capabilities internally when they help satisfy the inward-owned contract. A PostgreSQL adapter may use PostgreSQL transactions, constraints, indexing, and JSON support. A broker-backed messaging adapter may use the broker's native delivery guarantees. A model adapter may use provider-specific structured-output features.

Replacing such an adapter may require:

- a new adapter implementation;
- a new physical schema or migration strategy;
- operational migration;
- different deployment configuration.

It should not require redefining Investment Decision semantics, authority semantics, or application use-case contracts merely because the underlying technology changed.

---

# 3. Logical domain ownership

The capability model does not require one software module per capability. The following modules are earned because they own materially distinct semantics and invariants.

## 3.1 Decisions

**Owns:**

- Decision Need;
- Investment Decision identity;
- Subject and Decision Scope relationships;
- unresolved/resumable state;
- Deferral;
- substantive resolution;
- External Resolution;
- Supersession and causal linkage to renewed Investment Decisions;
- Review Condition relationships that affect decision continuity.

The Decisions module owns **decision lifecycle identity**, but it is not a giant aggregate containing every fact associated with a decision.

An Investment Decision is the durable lifecycle root that other modules reference. Evidence, judgments, authority acts, Action Intents, Outcomes, and Lessons retain their own semantic ownership.

## 3.2 Evidence

**Owns:**

- attributable Evidence identity;
- source provenance;
- observation/as-of time;
- Judgment-Time Availability;
- Freshness Requirement evaluation inputs/results where the question is Evidence fitness;
- sufficiency and unresolved/missing/conflicting Evidence representation;
- bindings showing which Evidence materially supported a judgment or governed use.

Evidence does not own external factual authority. It preserves which external source owns the fact and how Polaris observed or used it.

## 3.3 Investment Intelligence

**Owns:**

- Investment Hypothesis;
- Investment View;
- Investment Thesis relationships where applicable;
- Investment Assumptions;
- Investment Uncertainty;
- Invalidation Conditions;
- Catalysts;
- Decision Alternatives;
- materially used Signals as analytical provenance;
- Investment Recommendation;
- Proposed Actions as recommendation-stage candidates.

This module owns attributable analytical judgment. It does **not** own Human Investment Decision, Approval, execution authority, or external factual truth.

## 3.4 Portfolio & Risk

**Owns:**

- Portfolio identity as continuing investment responsibility;
- decision-oriented Portfolio State representation;
- Position, Exposure, Allocation distinctions;
- Projected Portfolio State and Projected Portfolio Consequence;
- Portfolio Risk and Portfolio Risk Assessment;
- Investment Objective, Investment Principle, Investment Strategy, Investment Horizon, Investment Mandate, and Formal Constraint semantics that shape portfolio judgment;
- deterministic Formal Constraint evaluation logic where the constraint is machine-evaluable.

Authoritative operational Portfolio State may come from an external source. The module owns its decision meaning inside Polaris, not external books-and-records authority.

## 3.5 Governance & Authority

**Owns:**

- Policy definitions/results applicable to Polaris boundaries;
- Investment Authority Regime;
- Admissibility;
- Approval and Authority Denial;
- Mandate Exception authority act;
- Residual-Risk Acceptance;
- Human Investment Decision;
- review/contest/override relationships where materially required;
- actor attribution for authority acts.

Governance does not own Portfolio Risk, external identity authentication, or model provenance. It consumes those facts through explicit contracts.

## 3.6 Action Continuity

**Owns:**

- Action Intent;
- relationships between Action Intent and authoritative external activity;
- reconciliation state and support strength;
- partial/divergent/abandoned implementation semantics;
- explicit ambiguity and unassociated external activity.

It has no outbound market-execution responsibility. There is intentionally no domain port for `place_order`, `cancel_order`, or equivalent execution authority in 0.2.0.

## 3.7 Learning

**Owns:**

- Outcome;
- Decision Evaluation;
- Lesson;
- retrospective criteria and attributable evaluation judgment;
- relationships allowing Lessons to influence future decision work without becoming authority-bearing rules.

Outcome remains observation; Decision Evaluation remains retrospective judgment; Lesson remains scoped learning.

## 3.8 What is intentionally not a domain module

The following are intentionally **not** first-class domain modules merely because they are important:

- Durable Decision Memory;
- Attention;
- workflows;
- jobs;
- reports;
- RAG;
- model providers;
- telemetry;
- replay;
- plugins.

**Durable Decision Memory** is a cross-lifecycle architectural responsibility produced by preserving and composing the canonical facts owned by the domain modules.

**Attention** is primarily an application capability that evaluates current observations against Portfolio and Decision Memory using domain semantics. It may use deterministic and AI-assisted analysis without becoming a separate source of business truth.

The remaining items are supporting implementation mechanisms that may be introduced when a current use case earns them.

---

# 4. Application architecture

The application layer owns **use-case coordination and transaction boundaries**. It does not contain a second domain model.

Representative use cases include:

```text
initiate_decision
resume_decision_work
defer_decision
externally_resolve_decision
supersede_decision

assemble_decision_context
bind_evidence
refresh_evidence_support

form_investment_view
challenge_investment_view
assess_portfolio_consequence
form_or_withhold_recommendation

record_rule_results
record_authority_act
record_human_investment_decision

establish_action_intent
reconcile_external_activity

record_outcome
evaluate_decision
record_lesson

evaluate_attention
query_decision_memory
```

These names are conceptual responsibilities, not a required one-function-per-command API.

## Commands and queries

Application entry points are divided conceptually into:

- **commands** — may establish new durable business facts or state transitions;
- **queries** — assemble current or historical views without becoming authoritative business writers.

Interfaces, scheduled work, and background workers call the same application use cases. No interface receives a privileged alternate path to business truth.

## Transaction ownership

A command that establishes durable business truth owns a single application transaction boundary.

The application layer is responsible for:

- loading the required current business state;
- checking expected versions/preconditions;
- invoking domain behavior;
- committing all business changes atomically where the invariant requires it;
- registering any required durable asynchronous follow-up atomically with the business changes when loss of that follow-up would violate the use case;
- returning success only after the required durable commit succeeds.

The application transaction boundary is semantic. It must not expose database-vendor transaction objects or messaging-vendor primitives to the domain.

Long model calls and external network calls must not hold durable-store transactions open.

A typical long-running analytical operation is therefore:

```text
1. load decision/context + capture expected versions
2. close the read transaction/session
3. acquire external Evidence / call model outside durable-store transaction
4. open command transaction
5. re-check versions, freshness, and governing preconditions
6. reject/re-evaluate if material state changed
7. atomically commit attributable judgment + Evidence bindings
   + any required durable follow-up obligation
```

This prevents slow external work from turning persistence locks into orchestration state while also preventing stale model output from silently overwriting newer business truth.

## Idempotency and concurrency

Every retryable command or externally observed fact ingestion path must support an idempotency identity appropriate to that operation.

Investment Decision identity is **not** the idempotency key for every operation.

The application contract requires optimistic concurrency/version checks or equivalent compare-and-set semantics on mutable lifecycle roots so competing work cannot silently overwrite newer state.

At-least-once technical execution is acceptable when business commands are idempotent and committed business facts remain singular.

---

# 5. Durable Decision Memory and business truth

Durable Decision Memory is not a workflow archive and not an event-log product.

## Direct business persistence

Material business facts are persisted directly under their owning semantics.

Examples include:

- Investment Decision lifecycle facts;
- Evidence observations and judgment bindings;
- attributable Investment Views and Recommendations;
- Portfolio snapshots used for material judgment;
- Portfolio Risk Assessments and Projected Portfolio Consequences;
- deterministic rule results;
- authority acts and Human Investment Decisions;
- Action Intents and reconciliation relationships;
- Outcomes, Decision Evaluations, and Lessons.

A workflow/job/model trace may point to those facts as technical provenance. It must never be the only place from which their business meaning can be reconstructed.

## Historical model

Material attributable judgments and authority acts are immutable once committed.

Later change is represented by new facts, explicit correction/supersession relationships, or new decision state—not by silently mutating what an earlier actor or model actually judged.

Mutable current-state helpers or read projections are permitted for efficient access, but they are not the sole historical authority.

## No universal event-sourcing requirement

0.2.0 will **not** use universal event sourcing as the business persistence model.

Domain events or application notifications may exist as internal coordination signals. Durable asynchronous follow-up may be implemented through an outbox, queue, broker, event bus, change-data-capture relay, or another adapter that satisfies the required guarantees.

Regardless of mechanism, the product's business truth is the direct domain state and immutable historical facts—not reconstruction from a universal runtime event stream.

## Decision Memory Query

A dedicated application query boundary will assemble a coherent current or historical Investment Decision view across owning modules.

Conceptually:

```text
Decision identity/lifecycle
        +
Evidence + judgment-time bindings
        +
Investment intelligence
        +
Portfolio/Risk
        +
Governance/authority
        +
Action continuity
        +
Outcome/Evaluation/Lessons
        ↓
Decision Memory View
```

The assembled view is a query representation. It is not a new canonical `DecisionRecord` entity.

---

# 6. Durable persistence boundary

Polaris requires a **durable transactional business persistence capability**. The architecture does not make a database product part of Polaris business identity.

## Required persistence semantics

The inward-owned persistence contracts must be able to satisfy, where the applicable use case requires them:

- atomic commitment of related business facts;
- durable concurrent command handling;
- optimistic concurrency/version checks or equivalent compare-and-set behavior;
- uniqueness and idempotency guarantees;
- preservation of immutable historical facts;
- efficient current-state queries;
- temporal ordering and historical reconstruction;
- explicit identity and provenance relationships;
- coordinated persistence across multiple owner-specific stores within one application transaction;
- durable recovery after process restart or ordinary infrastructure interruption.

These are architectural requirements. SQL, tables, document collections, ORM sessions, database locks, and vendor-specific transaction APIs are adapter implementation details.

## Inward-owned persistence ports

Persistence contracts are owned by the application/domain responsibility that needs them.

Examples may include owner-specific stores and an application Unit of Work that coordinates them. A generic "repository for everything" is discouraged because it erases ownership and tends to leak persistence shape into the domain.

Ports must not expose PostgreSQL row types, ORM sessions, SQL expressions, or another vendor's native persistence objects.

## Initial PostgreSQL adapter

PostgreSQL is the **initial/reference persistence adapter for 0.2.0**, not the architectural identity of the persistence boundary.

It is a strong first choice because the supported path requires:

- transactional invariants spanning related business facts;
- robust concurrency and uniqueness constraints;
- explicit relational identity/provenance links;
- immutable history plus efficient current-state queries;
- ordered temporal queries;
- structured flexibility for attributable analytical payloads.

The PostgreSQL adapter may use PostgreSQL-specific strengths internally when doing so cleanly satisfies the inward-owned contract.

Replacing PostgreSQL later may require a new adapter, new physical schema, data migration, and operational changes. It should not require changing canonical Investment Decision semantics or application use-case contracts.

This architecture does not choose an ORM, migration library, connection library, or physical schema. Those are R2 implementation decisions.

## Fresh persistence lineage

Greenfield Polaris will create a fresh current persistence lineage. The initial PostgreSQL implementation therefore gets a fresh root migration lineage and greenfield schema.

No current migration or persistence adapter may target a legacy table merely because that table exists under the quarantined implementation.

---

# 7. AI and model boundary

AI is an analytical mechanism behind an application port. It is not a domain authority layer.

## Model interaction contract

Application reasoning use cases may call a model port with explicitly assembled Decision Context and Evidence.

The model adapter returns a **draft analytical result** with technical provenance, not already-authoritative business state.

Conceptually:

```text
Application
  │
  ├─ assembles allowed context/evidence
  ▼
Model Port
  ▼
Provider Adapter
  ▼
Model
  ▼
structured draft result
  ▼
deterministic validation
  ▼
application/domain acceptance
  ▼
attributable business judgment committed
```

A model may propose an Investment View, challenge, Recommendation content, uncertainty, assumptions, or evaluation reasoning. It cannot commit an Approval, Human Investment Decision, Mandate Exception, Residual-Risk Acceptance, or external fact by emitting text that claims one occurred.

## Provider independence

Provider/model identity is technical provenance attached to an attributable analytical operation.

It is not business capability identity and must remain replaceable without redefining Investment Decision semantics.

## Structured validation

Model adapters must support deterministic validation of required response shape and explicit handling of malformed, incomplete, timed-out, or refused responses before any durable judgment is accepted.

Retry is technical behavior and must not create duplicate business judgments.

## No required agent topology

The architecture does not require:

- Bull/Bear/Sideways agents;
- multiple models;
- debate rounds;
- an agent registry;
- generic tools/plugins;
- a workflow graph.

Those mechanisms may be introduced only if a later implementation need demonstrates value inside this boundary.

---

# 8. Evidence and external fact integration

External specialist systems remain authoritative for facts inside their responsibility domains.

The application layer accesses external state through narrow capability ports such as:

- Evidence source/observation port;
- authoritative Portfolio State source port;
- external execution/activity observation port;
- model/reasoning port;
- actor identity/authentication context port;
- clock/time source port;
- notification/distribution port when a product use case earns it.

Exact protocol/vendor adapters live in `infrastructure`.

Ports must use Polaris-owned contract types or deliberately stable standards where justified; vendor SDK types must not leak into domain/application contracts merely for convenience.

## External facts are observations, not ownership transfer

Adapters normalize external data into attributable observations that preserve:

- external source identity;
- externally meaningful identity where needed;
- observed/as-of time;
- ingestion time;
- relevant source metadata;
- source authority classification.

Polaris may derive decision meaning from those observations. It must not silently replace the source's authoritative operational fact with an expected or cached value.

## Execution is deliberately inbound-only

0.2.0 permits observation/reconciliation of broker or execution facts.

The architecture intentionally defines no outbound execution command port. Adding one would require explicit reconsideration of the approved product scope and authority model.

---

# 9. Governance and authority execution

Governance is represented through explicit deterministic results and attributable authority acts rather than a generic approval workflow.

## Deterministic rules

Formal Constraints and platform Policy are evaluated through deterministic domain services where their rules are machine-evaluable.

Results are explicit facts such as:

```text
satisfied
violated
indeterminate
allowed
denied
```

The exact result vocabulary belongs to the owning domain semantics; rule evaluation is not inferred from model prose or absence of failure.

## Human authority

A human-facing command receives an authenticated `ActorContext` from the interface/identity boundary.

The Governance module evaluates whether the actor possesses the specific power under the applicable Investment Authority Regime and records the power-specific act separately.

Authentication, application authorization, and investment authority remain distinct layers.

## Human Investment Decision

Human Investment Decision is an explicit command and durable business fact.

It may adopt, modify, reject, defer, or differ from a Recommendation, and it may exist when no Recommendation was supportable.

Recording it does not retroactively mutate the Recommendation.

---

# 10. Interfaces and presentation

All presentation surfaces are thin adapters over the same application commands and queries.

```text
Human surface
     │
     ├── query Decision Memory / current decision view
     ├── submit correction/context
     ├── record review/authority act when authorized
     └── record Human Investment Decision
             │
             ▼
       Application API
             │
             ▼
       shared domain truth
```

R1 does not require choosing web, CLI, API, MCP, or another protocol as permanent product identity.

For the first R3 human slice, one deliberately small surface may be chosen. Whatever surface is selected must use the same application boundary later surfaces will use; it may not reconstruct or persist an independent report-specific decision model.

Reports, PDFs, email, messaging, and MCP remain optional presentation/distribution adapters until a current roadmap need earns them.

---

# 11. Background work, scheduling, Attention, and durable follow-up

Scheduled and asynchronous work are supporting runtime concerns, not business identity.

A scheduler or worker invokes normal application use cases with technical work identity and idempotency metadata.

A job identifier may answer:

> Which technical attempt is running?

It must not answer:

> Which Investment Decision is this?

## Attention flow

A representative attentive path is:

```text
external/scheduled observation
        ↓
normalize + persist attributable observation
        ↓
deterministic relevance/freshness/materiality triage where possible
        ↓
query affected Decision Memory / Portfolio context
        ↓
Attention application use case
        ↓
quietly absorb
or resume unresolved decision work
or establish new Decision Need / linked Investment Decision
        ↓
optional deeper AI-assisted investigation
        ↓
surface prepared work when human Attention is warranted
```

Fast deterministic invalidation of stale current support may occur before slower AI reasoning.

## Durable asynchronous follow-up boundary

The architectural requirement is **reliable durable follow-up after committed business changes**, not a specific outbox, queue, broker, or event-bus implementation.

When a committed business change requires later asynchronous work, Polaris must be able to durably register that follow-up such that the required work cannot be silently lost between business commit and asynchronous dispatch.

Conceptually:

```text
APPLICATION TRANSACTION
        │
        ├── commit business facts
        │
        └── register durable follow-up obligation
                  │
                  │ atomic where required
                  ▼
            committed state

                  ↓ later

FOLLOW-UP DELIVERY
        │
        ├── claim / receive
        ├── dispatch / invoke application use case
        ├── retry safely
        └── preserve idempotent business effect
```

The follow-up obligation is an application/runtime coordination concept, not a new canonical investment-domain entity and not a source of business truth.

The inward-owned contract must express guarantees such as:

- durable registration when the originating use case requires guaranteed follow-up;
- no success response if required durable registration failed;
- recoverability after process restart;
- at-least-once delivery being acceptable when the invoked application command is idempotent;
- explicit handling of poison/permanently failing work;
- no requirement that technical delivery identity equal Investment Decision identity;
- no silent semantic duplication of business facts under retry.

Possible adapters include:

- a transactional outbox;
- a durable database-backed work queue;
- a message broker or event bus with a transaction/atomicity strategy that satisfies the port contract;
- change-data-capture or outbox-relay infrastructure;
- another durable mechanism that satisfies the same guarantees.

A plain "commit database, then publish event" sequence is insufficient when the publish may be lost after the business commit. Any adapter must address that failure window rather than hide it behind a generic `publish()` interface.

## Event bus is not rejected as infrastructure

An event bus may be a valid adapter for technical delivery or integration.

What remains rejected is making a **universal event bus or replay stream the business source of truth or the organizing product spine**. Polaris business truth remains the directly persisted decision-domain facts and their durable historical relationships.

---

# 12. Observability and technical provenance

Operational observability is supporting Evidence about software execution.

The architecture will preserve technical identifiers such as:

- request/operation ID;
- technical work-item ID;
- model/provider invocation provenance;
- adapter/source call provenance;
- timing and failure information;
- Investment Decision ID as a correlation field when applicable.

These identifiers help diagnose how business work was produced. They do not become business identity or replace durable decision provenance.

Logs/traces must be sanitized and must not contain secrets or unnecessarily expose sensitive Portfolio information.

Optional telemetry loss must not erase independently required business provenance.

The exact tracing, metrics, or logging backend remains an infrastructure-adapter choice.

---

# 13. Security and identity boundary

0.2.0 will use a small-team security model appropriate to the approved product design center rather than speculative enterprise multitenancy.

The architecture requires:

- explicit authenticated actor context at human authority boundaries;
- separation of authentication from application authorization and Investment Authority Regime powers;
- secret access through an infrastructure secret/configuration boundary;
- no secrets embedded in domain records, prompts, reports, logs, or durable decision history;
- explicit access control around sensitive Portfolio and decision information;
- untrusted Evidence/model content unable to mutate governing Policy, Formal Constraints, Mandates, or authority rules merely by being present in text.

The exact identity provider and secret backend remain adapter choices.

---

# 14. Configuration boundary

Product configuration is expressed through investment-domain concepts and owned configuration contracts.

Examples include:

- Portfolio configuration;
- supported instrument universe;
- Investment Strategy and Horizon;
- Investment Mandate and Formal Constraints;
- platform Policy;
- Investment Authority Regime;
- Freshness Requirements;
- Review Conditions;
- Evidence/model provider selection;
- operational deadlines and adapter settings.

Provider and technical configuration live outside domain objects where they are not themselves investment semantics.

Polaris does not expose a generic workflow builder, plugin graph, or arbitrary prompt pipeline as the configuration model for 0.2.0.

---

# 15. Initial package boundary

The initial source topology should be:

```text
src/polaris/
├── domain/
│   ├── decisions/
│   ├── evidence/
│   ├── intelligence/
│   ├── portfolio/
│   ├── governance/
│   ├── continuity/
│   └── learning/
├── application/
│   ├── use_cases/
│   ├── queries/
│   └── ports/
├── infrastructure/
│   ├── persistence/
│   ├── follow_up/
│   ├── sources/
│   ├── models/
│   ├── identity/
│   ├── scheduling/
│   ├── observability/
│   └── configuration/
└── interfaces/
    └── <first thin human/machine adapters>
```

`follow_up/` denotes infrastructure that implements the durable asynchronous follow-up contracts. It does not prescribe outbox, broker, queue, or event-bus technology.

Directories should be created only when implementation work first needs them. The topology is an ownership map, not permission to scaffold every folder immediately.

There is intentionally no top-level greenfield package named:

- `core`;
- `workflows`;
- `agents`;
- `plugins`;
- `runtime`;
- `rag`;
- `reports`.

If one of those mechanisms is later required, it should live under the architectural owner that needs it rather than becoming a competing product spine by default.

---

# 16. Architecture enforcement

R2 must establish executable architecture checks before substantial production code accumulates.

At minimum, checks must fail when:

1. any current source/test imports a Python module from `legacy/`;
2. `domain` imports `application`, `infrastructure`, or `interfaces`;
3. `application` imports concrete `infrastructure` or `interfaces` implementations;
4. `domain` or `application` imports vendor-specific persistence, messaging, model-provider, external-source, identity, observability, or other adapter implementation packages except where a deliberately approved stable standard is itself part of the inward contract;
5. an inward-owned port exposes vendor SDK types, ORM sessions, SQL expressions, broker-native message types, or another adapter-specific representation without explicit architectural justification;
6. an interface or adapter bypasses the application command/query boundary to write business persistence directly;
7. runtime/work identifiers are used as Investment Decision identity;
8. current migrations or persistence adapters target legacy schema objects because they already exist.

The exact enforcement tool is an implementation choice. A small custom import/AST test is preferred over adding a framework solely for architecture linting unless the framework earns its dependency.

---

# 17. Initial operational targets

R1 establishes provisional measurable targets appropriate to decision-time use. R3/R7 must validate and refine them against the supported deployment.

For the initial supported path:

| Concern | Initial target |
| --- | --- |
| Durable command processing excluding external/model I/O | p95 ≤ 500 ms |
| Current Decision Memory query for one decision | p95 ≤ 1 s |
| Deterministic stale/current-support invalidation after an observation is received | p95 ≤ 5 s |
| Model/external calls | explicit per-port deadline; no unbounded wait |
| Human-initiated analytical preparation | target p95 ≤ 180 s for the narrow supported path |
| Successful business command | success returned only after required durable commit |
| Required asynchronous follow-up registration | durable before originating command reports success where atomic follow-up is required |
| Retry/recovery | no duplicate durable business fact for the same idempotent operation |

These are **decision-system targets**, not exchange-execution guarantees.

A slower provider/model may cause a visible pending, timeout, retryable failure, or withheld judgment. It must not cause Polaris to represent incomplete work as successful current decision support.

---

# 18. Deployment shape

The architecture is one logical application even if runtime roles are separated operationally.

An initial deployment may run:

```text
one interactive process
one optional background worker/scheduler process
one configured durable business store
external provider integrations as configured
```

The initial/reference durable-store adapter is expected to be PostgreSQL. That is a deployment/adapter choice, not a requirement that application/domain contracts depend on PostgreSQL.

Both processes execute the same application/domain code and use the same business truth.

This is not a microservice split. Worker/scheduler separation exists only to keep slow/background work from blocking interactive use.

The system may initially be deployed for one sophisticated operator or a small team. Enterprise tenancy, distributed service ownership, and horizontal scale are not architectural design centers for 0.2.0.

---

# 19. Testing architecture

Testing follows semantic ownership.

## Domain tests

Pure tests for lifecycle, authority, Portfolio/Risk, continuity, and learning invariants without external services.

## Application tests

Use-case tests with deterministic fakes for ports, including transaction/idempotency/concurrency behavior and durable-follow-up semantics.

## Adapter contract tests

Persistence, durable-follow-up, model, Evidence, Portfolio State, identity, and execution-observation adapters prove they satisfy their inward-owned contracts.

Contract tests must test semantic guarantees, not merely implementation-specific calls. For example, a persistence adapter test should prove required atomicity/idempotency behavior, and a follow-up adapter test should prove required durability/recovery behavior.

## Acceptance tests

The approved `AS-001` through `AS-022` scenarios are implemented as product-level acceptance Evidence across milestones.

Acceptance tests must assert canonical business facts, not merely that a workflow/job/report completed.

## Architecture tests

Import/dependency, vendor-insulation, port-contract, and legacy-isolation checks run continuously from R2 onward.

---

# 20. Requirement-family ownership

| Requirement family | Primary architectural owner / enforcement boundary |
| --- | --- |
| `GF-*` | whole architecture; dependency, technology-insulation, and legacy-isolation checks |
| `DEC-*` | Decisions + application transaction boundary |
| `ATT-*` | Attention application use cases + Decisions/Evidence/Memory queries |
| `EVD-*` | Evidence + source ports/adapters + durable persistence |
| `RSN-*` | Investment Intelligence + model port/application reasoning |
| `PRT-*` | Portfolio & Risk + authoritative Portfolio State port/adapter |
| `REC-*` | Investment Intelligence linked to Decisions |
| `AUT-*` | Governance & Authority + actor context + deterministic evaluators |
| `ACT-*` | Action Continuity + external execution-observation port/adapter |
| `MEM-*` | cross-module durable persistence + Decision Memory query boundary |
| `EVA-*` | Learning + historical Decision Memory |
| `UX-*` | interfaces over shared application commands/queries |
| `INT-*` | inward-owned application ports + infrastructure adapters |
| `CFG-*` | configuration boundary + domain-owned configuration semantics |
| `REL-*` | application transactions/idempotency + durable persistence + durable follow-up + observability |
| `SEC-*` | identity/secrets/access boundary + Governance authority semantics |
| `TMP-*` | Evidence freshness + Attention + scheduler/worker runtime |
| `SCP-*` | architecture boundary and explicit absence of unauthorized responsibilities |

Every approved requirement family therefore has a current owner or cross-cutting enforcement boundary without requiring one package per requirement family.

---

# 21. Rejected architectural defaults

The following are explicitly rejected as **default architecture for 0.2.0** unless a later current requirement reopens the question.

## Workflow-centric spine

Rejected because Investment Decision lifecycle and business facts must remain authoritative independently of workflow execution.

## Universal event sourcing / replay-as-truth

Rejected because the product requires directly reconstructable business semantics, not dependency on replaying generic runtime events.

## Universal event bus as product spine

Rejected because asynchronous delivery infrastructure must remain an adapter concern and must not become the canonical organizer or source of business identity. An event bus remains a valid adapter where it satisfies an inward-owned capability contract.

## Vendor-shaped core contracts

Rejected because domain/application contracts must express Polaris semantics and guarantees rather than mirror database, broker, model-provider, SDK, or infrastructure APIs.

## Microservices

Rejected because no current scaling, team, latency, or independent-deployment requirement justifies distributed consistency and operational cost.

## Generic plugin framework

Rejected because no approved requirement requires arbitrary runtime extension machinery.

## Mandatory RAG architecture

Rejected because retrieval is an optional reasoning technique, not a product identity or universal data path.

## Mandatory multi-agent debate

Rejected because meaningful challenge is required but agent topology is not.

## Report-centric business model

Rejected because reports are presentation surfaces over shared decision truth.

## Broker/execution command integration

Rejected because 0.2.0 explicitly excludes market-facing execution authority.

---

# 22. Donor inspection after architecture approval

Architecture approval establishes enough ownership to begin selective donor inspection.

Inspection must be organized by the **new owner**, not by walking legacy directories and asking what can be saved.

Examples:

```text
Need: model adapter behind Investment Intelligence port
→ inspect only relevant legacy model-gateway donor material

Need: initial PostgreSQL adapter mechanics behind inward-owned persistence contracts
→ inspect only relevant legacy database mechanics

Need: durable asynchronous follow-up adapter
→ inspect relevant legacy job/claim/outbox/event mechanics only after
  the follow-up contract is defined; salvage mechanics, not old runtime identity

Need: structured sensitive-data sanitization behind observability/security
→ inspect only relevant legacy sanitization donor material
```

For each donor candidate, classify:

```text
TRANSPLANT INTACT
TRANSPLANT WITH BOUNDARY CLEANUP
MINE ALGORITHM / TEST ONLY
REWRITE
LEAVE IN LEGACY
```

No classification may create runtime dependency on `legacy/` or leak a legacy/vendor implementation boundary inward.

---

# 23. R1 exit gate

R1 is complete only when this architecture is approved and the following are accepted explicitly:

1. modular monolith as the 0.2.0 system shape;
2. inward dependency direction through domain/application-owned ports;
3. explicit technology insulation: core contracts own semantics/guarantees while adapters own replaceable vendors and infrastructure patterns;
4. the seven logical domain ownership areas;
5. Investment Decision as lifecycle identity without becoming a giant aggregate;
6. Durable Decision Memory as cross-lifecycle composition of direct business facts;
7. technology-neutral durable persistence boundary, with PostgreSQL as the initial/reference adapter rather than architectural identity;
8. direct business persistence plus immutable history, not universal event sourcing;
9. application-owned transaction/idempotency/concurrency boundaries;
10. technology-neutral durable asynchronous follow-up boundary whose adapters may use outbox, queue, broker, event bus, CDC, or another mechanism only if they satisfy durability/atomicity/idempotency/recovery guarantees;
11. AI/model access as a bounded analytical adapter with no authority power;
12. deterministic Policy/Formal Constraint results distinct from authority acts;
13. external facts entering through observation ports with external authority preserved;
14. inbound observation/reconciliation with no outbound execution port;
15. thin presentation surfaces over shared application semantics;
16. optional worker/scheduler runtime that does not become business identity;
17. executable architecture, vendor-insulation, and legacy-isolation checks;
18. provisional decision-time operational targets;
19. fresh greenfield persistence lineage for the selected initial adapter;
20. requirement-family ownership as mapped above.

Approval of R1 authorizes **required component-boundary implementation planning and selective donor inspection** for the next roadmap work. It does not authorize importing legacy wholesale or bypassing the normal Spec/ticket delivery process.

# Immediate next transition

If this architecture is approved:

1. reclassify it from `docs/proposed/` to the current architecture document class;
2. capture any material architectural decisions that warrant durable ADR treatment under the repository's ADR workflow;
3. begin R2 component-boundary planning from the approved owners;
4. inspect only donor material relevant to those now-established owners;
5. create the greenfield implementation delivery lineage from the approved roadmap and architecture.
