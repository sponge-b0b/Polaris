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

This document describes architectural ownership, dependency direction, business-truth boundaries, and the initial technical shape. It does not prescribe every class, table, endpoint, model, or deployment detail.

---

# 1. Architectural decision

Polaris 0.2.0 will be a **modular monolith with ports and adapters**.

The system will have one canonical Python product codebase under `src/polaris/`, one transactional primary business store, explicit module boundaries enforced inside the codebase, and replaceable adapters for models, external Evidence, authoritative Portfolio State, external execution observations, identity, scheduling, and presentation surfaces.

Conceptually:

```text
Human / machine surfaces
        │
        ▼
┌───────────────────────────────────────────────┐
│               APPLICATION                    │
│  commands · queries · use-case coordination  │
│  transaction ownership · idempotency         │
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
┌───────────────────┐     ┌────────────────────┐
│ INFRASTRUCTURE    │     │ EXTERNAL SYSTEMS   │
│ persistence       │     │ Evidence providers │
│ model adapters    │     │ Portfolio sources  │
│ source adapters   │     │ brokers/execution  │
│ identity/secrets  │     │ model providers    │
│ scheduling        │     │ distribution       │
│ observability     │     │ identity systems   │
└───────────────────┘     └────────────────────┘
```

The architectural center is the **Investment Decision lifecycle and its durable business facts**, not a runtime graph, agent system, report pipeline, event stream, or persistence record type.

## Why a modular monolith

A modular monolith is the smallest architecture that fits the current product and team maturity while preserving strong semantic boundaries.

It is preferred for 0.2.0 because:

- many load-bearing invariants cross Decision, Evidence, Recommendation, authority, human judgment, and later continuity;
- the approved release requires trustworthy transactional business truth more than independent service scaling;
- the product has no requirement for independently deployed domain services;
- network boundaries would add distributed consistency and operational failure modes before they create product value;
- a small team can reason about, test, and evolve one deployable codebase more reliably;
- ports and strict import rules preserve extraction options if a real scaling or organizational boundary later appears.

A modular monolith is not permission to create one undifferentiated package. Boundaries are enforced by dependency rules and ownership, not by network calls.

---

# 2. Dependency direction

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

The Decisions module is the owner of **decision lifecycle identity**, but it is not a giant aggregate containing every fact associated with a decision.

An Investment Decision is the durable lifecycle root that other modules reference. Evidence, judgments, authority acts, Action Intents, Outcomes, and Lessons retain their own semantic ownership.

## 3.2 Evidence

**Owns:**

- attributable Evidence identity;
- source provenance;
- observation/as-of time;
- Judgment-Time Availability;
- Freshness Requirement evaluation inputs/results where the question is evidence fitness;
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

**Attention** is primarily an application capability that evaluates current observations against Portfolio and decision memory using domain semantics. It may use deterministic and AI-assisted analysis without becoming a separate source of business truth.

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
- persisting all business changes atomically where the invariant requires it;
- writing any required outbox notification in the same transaction;
- returning success only after the business transaction commits.

Long model calls and external network calls must not hold database transactions open.

A typical long-running analytical operation is therefore:

```text
1. load decision/context + capture expected versions
2. commit/close read transaction
3. acquire external Evidence / call model outside DB transaction
4. open command transaction
5. re-check versions, freshness, and governing preconditions
6. reject/re-evaluate if material state changed
7. commit attributable judgment + Evidence bindings + outbox atomically
```

This prevents slow external work from turning database locks into orchestration state while also preventing stale model output from silently overwriting newer business truth.

## Idempotency and concurrency

Every retryable command or externally observed fact ingestion path must support an idempotency identity appropriate to that operation.

Investment Decision identity is **not** the idempotency key for every operation.

The architecture will use optimistic concurrency/version checks on mutable lifecycle roots or equivalent compare-and-set semantics so competing work cannot silently overwrite newer state.

At-least-once technical execution is acceptable when business commands are idempotent and committed facts remain singular.

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

## No event-sourcing requirement

0.2.0 will **not** use universal event sourcing as the business persistence model.

Domain events may exist as internal notifications, and an outbox may durably publish committed changes to background work, but the product's business truth is the direct domain state and immutable historical facts—not reconstruction from a universal runtime event stream.

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

# 6. Primary persistence architecture

Polaris 0.2.0 will use **PostgreSQL as the initial canonical transactional business store**.

This is a fresh greenfield choice justified by the approved requirements, not by legacy usage.

PostgreSQL fits because 0.2.0 requires:

- transactional invariants spanning related business facts;
- durable concurrent command handling;
- explicit relational identity and provenance links;
- immutable historical facts plus efficient current-state queries;
- robust uniqueness/idempotency constraints;
- ordered temporal queries and reconstruction;
- enough structured flexibility for attributable analytical payloads without making opaque documents the sole truth.

This decision does not choose an ORM, migration library, connection library, or physical schema yet. Those are implementation decisions for R2 after the architecture is approved.

## Fresh lineage

Greenfield Polaris will create a fresh root migration lineage and greenfield schema.

No new migration may alter a legacy table merely because that table exists under the quarantined implementation.

## Persistence ports

Persistence contracts are owned inward by the application/domain responsibility that needs them. Infrastructure provides PostgreSQL adapters.

A generic "persistence repository for everything" is discouraged because it erases ownership. A single application Unit of Work may coordinate multiple owner-specific stores within one transaction.

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

The exact result vocabulary belongs to the owning domain semantics; the important architectural rule is that rule evaluation is not inferred from model prose or absence of failure.

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

# 11. Background work, scheduling, and Attention

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
query affected decision memory / portfolio context
        ↓
Attention application use case
        ↓
quietly absorb
or resume unresolved decision work
or establish new Decision Need / linked Investment Decision
        ↓
optional deeper AI-assisted investigation
        ↓
surface prepared work when human attention is warranted
```

Fast deterministic invalidation of stale current support may occur before slower AI reasoning.

## Outbox instead of universal event bus

When a committed business change must trigger asynchronous follow-up, the same transaction may write an outbox record.

A worker consumes the outbox at least once and invokes an idempotent application use case.

This gives reliable follow-up without making a universal event bus or replay stream the product architecture.

---

# 12. Observability and technical provenance

Operational observability is supporting evidence about software execution.

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
│   ├── sources/
│   ├── models/
│   ├── identity/
│   ├── scheduling/
│   ├── observability/
│   └── configuration/
└── interfaces/
    └── <first thin human/machine adapters>
```

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
4. an interface or adapter bypasses the application command/query boundary to write business persistence directly;
5. runtime/work identifiers are used as Investment Decision identity;
6. current migrations target legacy schema objects because they already exist.

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
| Successful business command | success returned only after durable commit |
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
one PostgreSQL database
external provider integrations as configured
```

Both processes execute the same application/domain code and use the same business store.

This is not a microservice split. Worker/scheduler separation exists only to keep slow/background work from blocking interactive use.

The system may initially be deployed for one sophisticated operator or a small team. Enterprise tenancy, distributed service ownership, and horizontal scale are not architectural design centers for 0.2.0.

---

# 19. Testing architecture

Testing follows semantic ownership.

## Domain tests

Pure tests for lifecycle, authority, Portfolio/Risk, continuity, and learning invariants without external services.

## Application tests

Use-case tests with deterministic fakes for ports, including transaction/idempotency/concurrency behavior.

## Adapter contract tests

Persistence, model, Evidence, Portfolio State, identity, and execution-observation adapters prove they satisfy their inward-owned contracts.

## Acceptance tests

The approved `AS-001` through `AS-022` scenarios are implemented as product-level acceptance evidence across milestones.

Acceptance tests must assert canonical business facts, not merely that a workflow/job/report completed.

## Architecture tests

Import/dependency and legacy-isolation checks run continuously from R2 onward.

---

# 20. Requirement-family ownership

| Requirement family | Primary architectural owner / enforcement boundary |
| --- | --- |
| `GF-*` | whole architecture; dependency and legacy-isolation checks |
| `DEC-*` | Decisions + application transaction boundary |
| `ATT-*` | Attention application use cases + Decisions/Evidence/Memory queries |
| `EVD-*` | Evidence + source adapters + persistence |
| `RSN-*` | Investment Intelligence + model port/application reasoning |
| `PRT-*` | Portfolio & Risk + authoritative Portfolio State adapter |
| `REC-*` | Investment Intelligence linked to Decisions |
| `AUT-*` | Governance & Authority + actor context + deterministic evaluators |
| `ACT-*` | Action Continuity + external execution-observation adapter |
| `MEM-*` | cross-module persistence + Decision Memory query boundary |
| `EVA-*` | Learning + historical Decision Memory |
| `UX-*` | interfaces over shared application commands/queries |
| `INT-*` | application ports + infrastructure adapters |
| `CFG-*` | configuration boundary + domain-owned configuration semantics |
| `REL-*` | application transactions/idempotency + persistence/outbox/observability |
| `SEC-*` | identity/secrets/access boundary + Governance authority semantics |
| `TMP-*` | Evidence freshness + Attention + scheduler/worker runtime |
| `SCP-*` | architecture boundary and explicit absence of unauthorized responsibilities |

Every approved requirement family therefore has a current owner or cross-cutting enforcement boundary without requiring one package per requirement family.

---

# 21. Rejected architectural defaults

The following are explicitly rejected as **default architecture for 0.2.0** unless a later current requirement reopens the question:

## Workflow-centric spine

Rejected because Investment Decision lifecycle and business facts must remain authoritative independently of workflow execution.

## Universal event sourcing / replay-as-truth

Rejected because the product requires direct reconstructable business semantics, not dependency on replaying generic runtime events.

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

Need: PostgreSQL transaction/engine mechanics behind persistence ports
→ inspect only relevant legacy database mechanics

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

No classification may create runtime dependency on `legacy/`.

---

# 23. R1 exit gate

R1 is complete only when this architecture is approved and the following are accepted explicitly:

1. modular monolith as the 0.2.0 system shape;
2. inward dependency direction through domain/application-owned ports;
3. the seven logical domain ownership areas;
4. Investment Decision as lifecycle identity without becoming a giant aggregate;
5. Durable Decision Memory as cross-lifecycle composition of direct business facts;
6. PostgreSQL as the fresh transactional business store, without inheriting the legacy schema;
7. direct business persistence plus immutable history, not universal event sourcing;
8. application-owned transaction/idempotency/concurrency boundaries;
9. AI/model access as a bounded analytical adapter with no authority power;
10. deterministic Policy/Formal Constraint results distinct from authority acts;
11. external facts entering through observation ports with external authority preserved;
12. inbound observation/reconciliation with no outbound execution port;
13. thin presentation surfaces over shared application semantics;
14. optional worker/scheduler runtime that does not become business identity;
15. outbox for required asynchronous follow-up rather than a universal event bus;
16. executable architecture and legacy-isolation checks;
17. provisional decision-time operational targets;
18. fresh greenfield migration/schema lineage;
19. requirement-family ownership as mapped above.

Approval of R1 authorizes **required component-boundary implementation planning and selective donor inspection** for the next roadmap work. It does not authorize importing legacy wholesale or bypassing the normal Spec/ticket delivery process.

# Immediate next transition

If this architecture is approved:

1. reclassify it from `docs/proposed/` to the current architecture document class;
2. capture any material architectural decisions that warrant durable ADR treatment under the repository's ADR workflow;
3. begin R2 component-boundary planning from the approved owners;
4. inspect only donor material relevant to those now-established owners;
5. create the greenfield implementation delivery lineage from the approved roadmap and architecture.
