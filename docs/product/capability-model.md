# Polaris Capability Model

**Status:** Defined  
**Purpose:** Define the structural product model that connects Polaris's durable capabilities into one portfolio decision system and provides the capability-level basis for release strategy and roadmap planning.

This document operationalizes the Product Definition and the capability decisions recorded in [`product-core-capabilities.md`](./product-core-capabilities.md). It defines how Polaris capabilities relate, what product semantics cross their boundaries, how authority and trust apply across them, and how capability maturity should be evaluated without turning the roadmap into an implementation-feature checklist.

It intentionally does **not** prescribe packages, services, agents, workflows, databases, APIs, models, interfaces, or other implementation topology.

## Decision

Polaris is modeled as an opinionated **portfolio decision system** composed of:

1. eight sequential-but-iterative **core decision-lifecycle capabilities**;
2. one **cross-lifecycle core capability**, Durable Decision Memory;
3. five **supporting platform capabilities** that enable the decision system without becoming independent product centers;
4. explicit integration with **external specialist responsibilities** that retain their own authority;
5. cross-cutting **decision contracts** that every relevant capability must preserve.

The model is:

```text
                         POLARIS
                Portfolio Decision System

                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│                 CORE DECISION CAPABILITIES                 │
│                                                            │
│  Attention & Decision Initiation                           │
│             ↓                                              │
│  Decision Context & Evidence                               │
│             ↓                                              │
│  Investment Reasoning & Challenge                          │
│             ↓                                              │
│  Portfolio Consequence & Risk                              │
│             ↓                                              │
│  Recommendation Formation                                  │
│             ↓                                              │
│  Authority & Human Decision                                │
│             ↓                                              │
│  Action Continuity & Reconciliation                        │
│             ↓                                              │
│  Outcome Evaluation & Learning                             │
│             │                                              │
│             └──────────────────→ future Attention          │
│                                                            │
│  ═══════════ Durable Decision Memory spans all ═══════════ │
└────────────────────────────────────────────────────────────┘

                            │
                     enabled by
                            ▼

┌────────────────────────────────────────────────────────────┐
│              SUPPORTING PLATFORM CAPABILITIES              │
│                                                            │
│  Integration & Connectivity                                │
│  Interaction & Presentation                                │
│  Configuration & Extensibility                             │
│  Runtime Reliability & Observability                       │
│  Security & Operations                                     │
└────────────────────────────────────────────────────────────┘

                            │
                  integrates with
                            ▼

┌────────────────────────────────────────────────────────────┐
│             EXTERNAL SPECIALIST RESPONSIBILITIES           │
│                                                            │
│  Market / economic / research Evidence                     │
│  Brokerage and execution                                   │
│  Portfolio accounting / books and records                  │
│  Custody / settlement                                      │
│  External analytics                                        │
│  Communication / distribution infrastructure               │
└────────────────────────────────────────────────────────────┘
```

Across the model, source authority, deterministic rule evaluation, Polaris investment judgment, power-specific human authority, and external execution authority remain distinct.

The capability model is organized around durable product responsibility rather than current software structure.

## Relationship to the Core Capabilities record

[`product-core-capabilities.md`](./product-core-capabilities.md) is the product record for **why** these capabilities exist and what each capability means in product terms.

This document answers a different question:

> **How do those capabilities operate together as one product?**

The distinction is intentional:

```text
product-core-capabilities.md
        ↓
Why these capabilities exist
What each capability means
Why they are capabilities rather than features

capability-model.md
        ↓
How the capabilities fit together
What each consumes and establishes
Which capabilities are lifecycle versus cross-lifecycle
Where authority and trust contracts apply
What Polaris owns versus integrates
How capability maturity and breadth are evaluated
```

The capability model should therefore remain materially smaller than the full capability rationale and should not repeat it unnecessarily.

## Capability classes

### Core lifecycle capabilities

Eight core capabilities primarily advance an Investment Decision through its lifecycle:

1. **Attention & Decision Initiation**
2. **Decision Context & Evidence**
3. **Investment Reasoning & Challenge**
4. **Portfolio Consequence & Risk**
5. **Recommendation Formation**
6. **Authority & Human Decision**
7. **Action Continuity & Reconciliation**
8. **Outcome Evaluation & Learning**

They form a recognizable product progression, but they are not a rigid waterfall. A later capability may expose missing Evidence, establish an Invalidation Condition, require renewed challenge, or cause Attention to reconsider whether unresolved or renewed decision work is warranted.

### Cross-lifecycle core capability

**Durable Decision Memory** is structurally different from the other core capabilities.

It is not a final stage after evaluation. It spans the entire lifecycle and allows prior decision state to influence future Attention, reasoning, Governance, and learning.

Conceptually:

```text
                  Durable Decision Memory
                           │
       ┌───────────────────┼────────────────────┐
       ↓                   ↓                    ↓
Attention ←→ Evidence ←→ Reasoning ... ←→ Evaluation
       ↑                                        │
       └────────────────────────────────────────┘
```

Durable Decision Memory remains a core capability because Polaris would cease to satisfy its durable-decision product contract without it.

### Supporting platform capabilities

Five supporting capabilities enable the core decision system:

* **Integration & Connectivity**
* **Interaction & Presentation**
* **Configuration & Extensibility**
* **Runtime Reliability & Observability**
* **Security & Operations**

These capabilities may become sophisticated and differentiated, but their product purpose remains subordinate to the portfolio decision lifecycle.

### External specialist responsibilities

Some responsibilities materially participate in Polaris decisions while remaining owned by specialist systems.

Examples include:

* authoritative market and economic Evidence;
* brokerage and execution;
* official portfolio accounting and books and records;
* custody and settlement;
* specialist external analytics;
* communication and distribution infrastructure.

Polaris may consume, normalize, reason over, reconcile, and present these systems' state. Integration does not transfer their broader specialist authority or product responsibility to Polaris.

The governing rules remain:

> **Polaris owns decisions, not everything decisions touch.**

> **Dependency does not imply ownership.**

## Semantic capability contracts

Capabilities should exchange **product semantics**, not implementation-specific objects.

The model therefore describes what each core capability primarily consumes and what it establishes for the lifecycle.

| Capability | Primarily consumes | Primarily establishes |
| --- | --- | --- |
| Attention & Decision Initiation | unresolved Investment Decisions, Investment Theses, Review Conditions, Portfolio context, new information | **Attention assessment and Decision Need** |
| Decision Context & Evidence | Decision Need, Portfolio context, external Evidence, prior memory | **Decision Context and attributable Evidence** |
| Investment Reasoning & Challenge | Evidence, Decision Context, historical knowledge | **Investment View, alternatives, conflicting Evidence, Investment Uncertainty, Invalidation Conditions** |
| Portfolio Consequence & Risk | Investment View, actual Portfolio State, Investment Strategy, Investment Mandate, Policy | **Projected Portfolio Consequences, Portfolio Risk, applicable Formal Constraint and Policy results** |
| Recommendation Formation | reasoning, Decision Alternatives, Projected Portfolio Consequences, Portfolio Risk | **Investment Recommendation or justified withholding, alternatives, rationale** |
| Authority & Human Decision | candidate Investment Recommendation, Evidence readiness, Policy, Formal Constraint results, authority state | **Admissibility, applicable authority acts, Human Investment Decision** |
| Action Continuity & Reconciliation | Human Investment Decision, Action Intent where one exists, authoritative external activity | **Reconciled external activity and resulting Portfolio State** |
| Outcome Evaluation & Learning | historically faithful Investment Decision history, external activity, later Evidence, Outcome | **Decision Evaluation and durable Lessons** |
| Durable Decision Memory | every material lifecycle state | **Historically faithful decision meaning available to future capabilities** |

These are conceptual contracts. They do not imply one database entity, service boundary, event schema, API payload, or workflow node per capability.

## Durable Decision Memory as connective product state

Durable Decision Memory is the cross-cutting responsibility that keeps material Investment Decision history and relationships semantically reconstructable through time.

Lowercase `decision record` may remain noncanonical product shorthand for an assembled representation of that history. It is not a separate canonical business entity or a mandate for one storage object.

As an Investment Decision matures, Durable Decision Memory may progressively preserve or connect:

```text
Decision Need
      ↓
Decision Context
      ↓
Attributable Evidence
      ↓
Investment View + challenge
      ↓
Projected Portfolio Consequences
      ↓
Portfolio Risk + applicable Policy / Formal Constraints
      ↓
Investment Recommendation
      ↓
Authority acts / Admissibility
      ↓
Human Investment Decision
      ↓
Action Intent where one exists
      ↓
Observed external activity
      ↓
Resulting Portfolio State
      ↓
Outcome
      ↓
Decision Evaluation
      ↓
Lessons
```

The capabilities should strengthen this shared lifecycle rather than create isolated local truths that must later be reconstructed from narrative or runtime output.

## Capability interaction is iterative, not waterfall

The directional capability chain describes the dominant product flow, not a one-way execution constraint.

Examples of legitimate backward or renewed movement include:

* reasoning discovers that required Evidence is missing;
* Portfolio analysis makes an initially attractive Investment Hypothesis irrelevant;
* Policy or a Formal Constraint removes a Proposed Action from consequential use;
* recommendation formation exposes unresolved Investment Uncertainty requiring further challenge;
* implementation divergence causes Attention to evaluate whether unresolved work should resume or a renewed Decision Need exists;
* Decision Evaluation identifies a Lesson that changes future Attention criteria;
* new Evidence establishes an Invalidation Condition and causes Attention to evaluate the affected investment matter.

Conceptually:

```text
Attention
   ↓
Evidence ⇄ Reasoning ⇄ Portfolio/Risk ⇄ Recommendation
   ↑                                      ↓
   └──────── reassessment as needed ──────┘
                                          ↓
                              Human Investment Decision
                                          ↓
                                  External Activity
                                          ↓
                                  Decision Evaluation
                                          │
                                          └──→ future Attention
```

If the same coherent investment choice remains unresolved, later work may continue within the same Investment Decision. Once substantive investment judgment has resolved that choice, renewed judgment requires a new causally linked Investment Decision rather than reopening and rewriting the historical one.

The product should preserve the lifecycle's semantic state across these iterations rather than treating each analytical pass as an unrelated run.

## Authority overlays the capability model

Authority is not a late approval stamp added after analytical work, and Polaris should not treat every trust mechanism as the same kind of authority.

The accepted separation of responsibilities is:

```text
AUTHORITATIVE SOURCES
Establish the external facts they own.
        ↓
POLICY / FORMAL CONSTRAINT EVALUATION
Deterministically establish applicable rule results.
        ↓
POLARIS INVESTMENT JUDGMENT
Forms Investment Views and Investment Recommendations.
        ↓
INVESTMENT AUTHORITY REGIME
Determines who may make Human Investment Decisions,
grant Approval, authorize Mandate Exceptions,
or accept Governed Residual Risk where required.
        ↓
EXTERNAL EXECUTION AUTHORITY
External systems establish Orders, fills, and other operational facts.
```

The named **Authority & Human Decision** capability owns the explicit product responsibility for Admissibility, applicable authority acts, and preserved Human Investment Decision. That does not mean Evidence readiness, Policy, Formal Constraint evaluation, or Portfolio Risk waits until that stage.

For example, recommendation formation must already be shaped by Portfolio Risk and applicable deterministic rules:

```text
                Reasoning & Challenge
                         │
                         ▼
              Portfolio Consequence
                    & Risk
                         │
                    ┌────┴────┐
                    │         │
                    ▼         │
         Investment Recommendation
                    ▲         │
                    │         │
        Policy / Formal       │
        Constraints ──────────┘
                    │
                    ▼
             Admissibility
                    │
                    ▼
        applicable authority acts
                    │
                    ▼
        Human Investment Decision
```

Policy evaluation is not Approval. Formal Constraint satisfaction is not Approval. Human Investment Decision is not Approval. Each power or result remains distinct even when they lead to the same practical outcome.

A capability may be able to perform an operation without possessing authority for a consequential use. Capability and authority must remain distinct.

## Cross-cutting decision contracts

Several product responsibilities apply horizontally across capabilities. They should not be promoted into additional top-level capabilities merely because they are important.

### Decision provenance

Material Evidence, reasoning, constraints, authority decisions, human judgment, observed activity, and Outcome should remain attributable enough to reconstruct the meaningful decision path.

### Judgment-time integrity

Polaris must distinguish:

```text
What is known now
```

from:

```text
What was available to a particular judgment then
```

Later Evidence may inform Decision Evaluation and learning without becoming retroactively available to an earlier judgment.

### Decision-appropriate freshness

Evidence must be current enough for the investment use or judgment being claimed.

When required Evidence is stale, Polaris should preserve that insufficiency and qualify or withhold the affected current judgment or consequential use rather than silently lower the trust standard. Historical judgments remain historical facts even when they are no longer currently supportable.

### Meaningful challenge and Investment Uncertainty

Material Conflicting Evidence, alternative explanations, Investment Uncertainty, Investment Assumptions, and Invalidation Conditions should not disappear merely because the system has formed a preferred Investment View or Investment Recommendation.

### Authority integrity

Policy, Formal Constraints, Admissibility, Approval, Authority Denial, Human Investment Decision, Mandate Exception, Residual-Risk Acceptance, and external execution authority must remain semantically distinct where material.

Positive authority acts and satisfied deterministic conditions should be preserved when material rather than inferred from the absence of recorded failure.

### Operational reality

When Polaris's expectation conflicts with an authoritative external source within that source's responsibility domain, the authoritative external fact remains authoritative.

Polaris may preserve and investigate the discrepancy. It must not silently rewrite external reality to match its previous Investment Recommendation or Action Intent.

## Supporting capability relationships

Supporting capabilities should be evaluated by how effectively they enable the core decision system rather than by independent feature-count metrics.

### Integration & Connectivity

Primarily enables:

* Decision Context & Evidence;
* Portfolio Consequence & Risk;
* Action Continuity & Reconciliation;
* Outcome Evaluation & Learning;
* relevant portions of Durable Decision Memory.

Its product question is:

> Can Polaris reliably obtain, attribute, and reconcile the external state required by the decision lifecycle?

The number of integrations is a breadth measure, not sufficient evidence of capability maturity.

### Interaction & Presentation

Enables user and machine interaction with shared decision semantics through surfaces such as conversation, UI, reports, CLI, API, MCP, email, and messaging.

Conceptually:

```text
                 Polaris decision system

                       ↓  ↓  ↓

Web / Conversation / Reports / CLI / API / MCP / Messaging
```

Surfaces should present common governed decision state rather than reconstruct competing versions of the decision.

### Configuration & Extensibility

Enables Polaris to adapt to differences in:

* Portfolio;
* Investment Strategy;
* asset universe;
* Investment Horizon;
* Evidence providers;
* analytical models;
* Policy;
* Investment Mandate and Formal Constraints;
* Review Conditions;
* operating preferences.

Configurability should remain expressed through investment-domain concepts rather than turning Polaris into an arbitrary workflow or agent platform.

### Runtime Reliability & Observability

Enables decision work to execute reliably, preserve relevant state, expose failures, support recovery, and remain operationally inspectable.

Its value is measured by trustworthy decision continuity rather than by runtime sophistication for its own sake.

### Security & Operations

Protects credentials, Portfolio information, integrations, configuration, access boundaries, and other operational trust assumptions required by the product's maturity.

Security and operations span the system but remain enabling responsibilities rather than a separate user-facing product center.

## External specialist boundary

The capability model should make ownership boundaries visible because roadmap pressure can otherwise convert every dependency into a proposed Polaris subsystem.

The default relationship is:

```text
External specialist owns authoritative responsibility
                  ↓
Polaris integrates required state
                  ↓
Polaris applies decision semantics
                  ↓
Polaris preserves provenance / reconciliation
```

Examples:

| External responsibility | External authority | Polaris responsibility |
| --- | --- | --- |
| Market/economic Evidence | responsible Evidence provider | determine Investment Relevance, freshness, provenance, sufficiency, interpretation |
| Brokerage/execution | broker or execution system | preserve Action Intent where one exists, observe and reconcile what occurred |
| Official Portfolio State | authoritative portfolio/accounting system where applicable | consume trustworthy state and apply it to Investment Decisions |
| Custody/settlement | specialist operational system | use relevant resulting Evidence when it affects decision state |
| External analytics | specialist analytical source | attribute and incorporate relevant Evidence without laundering it into native fact |
| Distribution infrastructure | communication destination/provider | present Polaris decision state without creating independent semantics |

A proposal to absorb an external specialist responsibility should therefore carry an explicit burden of proof when it creates a new primary user job, authority domain, latency regime, operational contract, regulatory burden, or product identity.

## Capability dependency model

Core capabilities depend on one another, but dependency does not mean roadmap sequencing must complete one capability before another begins.

The dependency direction is primarily semantic:

```text
Attention
   requires durable context about what matters

Evidence
   requires a Decision Need and relevant external/internal context

Reasoning
   requires decision-ready Evidence

Portfolio/Risk
   requires an Investment View plus real Portfolio State,
   Investment Mandate, and applicable Policy

Recommendation
   requires challenged reasoning,
   Decision Alternatives, and Projected Portfolio Consequences

Authority/Human Decision
   requires a candidate Investment Recommendation,
   Admissibility, and explicit authority state

Action Continuity
   requires a Human Investment Decision and,
   when an external consequence exists, Action Intent plus authoritative external Evidence

Evaluation/Learning
   requires historically faithful decision, external activity, and Outcome state

Durable Decision Memory
   preserves and reconnects the lifecycle across all of the above
```

This dependency model should guide architecture and release planning without forcing subsystem-first development.

## Vertical capability maturity

Polaris should mature capabilities through coherent end-to-end product slices rather than fully developing one subsystem while adjacent lifecycle capabilities remain absent.

A useful release may therefore provide bounded but trustworthy versions of many capabilities at once:

```text
                 Release N

Attention                ── bounded but usable
Evidence                 ── bounded but trustworthy
Reasoning                ── bounded but challenged
Portfolio/Risk           ── bounded but real
Recommendation           ── usable
Authority                ── explicit
Action continuity        ── bounded
Memory                   ── durable
Evaluation               ── bounded

              = coherent product slice
```

Later releases should deepen, govern, adapt, or broaden those same capabilities rather than merely accumulate disconnected features.

## Capability maturity model

Core capability maturity is evaluated using four levels.

### M1 — Bounded

The capability produces its defined product outcome for a deliberately limited operating context.

Examples:

* Attention can identify materially changed conditions for a limited set of supported Decision Contexts.
* Action Continuity can reconcile a deliberately limited class of external activity reliably.
* Evidence can construct trustworthy Decision Context from a deliberately limited source set.

M1 is not a prototype label. The supported boundary should be explicit enough that behavior inside it can be trusted.

### M2 — Integrated

The capability participates in the canonical Polaris decision lifecycle and exchanges the correct shared product semantics with adjacent capabilities.

An excellent isolated subsystem that produces a disconnected report has not reached M2 merely because its local function is sophisticated.

Integration means the capability strengthens the durable decision lifecycle.

### M3 — Governed

The capability enforces or preserves the relevant cross-cutting decision contracts for its responsibility domain.

Depending on the capability, that may include:

* provenance;
* freshness;
* power-specific authority;
* Investment Uncertainty;
* historical integrity;
* explicit fail-closed behavior;
* external factual authority;
* durable semantic state.

M3 means the capability is not merely useful; it participates in the product's trust model.

### M4 — Adaptive

Durable Portfolio, Investment Decision, authority, Outcome, and Lesson state materially changes the capability's future behavior where appropriate.

Examples include:

```text
Previous Invalidation Condition
        ↓
New Evidence
        ↓
Attention evaluates renewed decision need
```

or:

```text
Previous Decision Evaluation
        ↓
Future Attention / reasoning / Policy or Mandate review improves
```

Adaptive maturity should be grounded in durable product state rather than vague claims that an AI model "learns."

### No terminal "complete" level

The model intentionally does not define an M5 such as **Complete**.

Core capabilities can deepen indefinitely as Polaris supports richer Portfolios, more Evidence, stronger decision contracts, better analytical techniques, more sophisticated reconciliation, and improved learning.

Roadmap planning should identify the maturity required for a release rather than imply that a durable capability has been permanently finished.

## Breadth is separate from maturity

Capability maturity and capability breadth are independent dimensions.

**Maturity** asks:

> How well does Polaris fulfill this responsibility within the supported operating context?

**Breadth** asks:

> Across how many operating contexts can Polaris fulfill it?

Breadth may include dimensions such as:

* asset classes;
* broker or execution providers;
* Evidence providers;
* Portfolio structures;
* Investment Strategies;
* Investment Horizons;
* Policy and Investment Mandate configurations;
* user/team operating models;
* delivery surfaces.

A capability may be narrow and mature:

```text
1 broker
1 asset class
1 portfolio style
+
strong provenance
strong reconciliation
clear authority
historical integrity
```

Or broad and immature:

```text
many brokers
many asset classes
many Evidence sources
+
weak decision semantics
weak provenance
weak authority
```

The first may represent greater product progress than the second.

Roadmap discussions should therefore avoid using provider count, interface count, model count, or other breadth metrics as substitutes for capability maturity.

## Capability-level roadmap discipline

The capability model exists partly to prevent the roadmap from becoming a feature backlog.

A release should be described primarily in terms of changes such as:

* a previously absent end-to-end capability becomes usable;
* a bounded capability becomes integrated;
* an integrated capability becomes governed;
* a governed capability becomes adaptive;
* a capability becomes materially broader without weakening its maturity;
* several capabilities combine into a new coherent end-to-end user outcome.

Implementation features remain necessary, but they are evidence of how the capability advance is delivered rather than the primary roadmap unit.

The governing release question is:

> **What portfolio decision ability becomes newly usable, more trustworthy, more connected, more adaptive, or meaningfully broader?**

## Capability acceptance language

Capability progress should eventually be testable in product language.

Examples include:

* **Attention:** Can Polaris identify that something materially changed, determine whether a Decision Need exists, and explain why it affects the relevant investment matter?
* **Evidence:** Can Polaris reconstruct the attributable Evidence available to a material judgment and determine whether it was current enough for that use?
* **Challenge:** Can the user inspect meaningful Evidence or reasoning against the preferred Investment View?
* **Portfolio & Risk:** Can Polaris explain how actual Portfolio State and Portfolio Risk changed Projected Portfolio Consequences or the Investment Recommendation?
* **Recommendation:** Can Polaris explain the preferred disposition, meaningful Decision Alternatives, and conditions that would change the view?
* **Authority:** Can the material authority path be reconstructed without conflating Policy, Formal Constraints, Approval, or Human Investment Decision?
* **Continuity:** Can Polaris determine whether an Action Intent was reflected in authoritative external activity when one existed?
* **Memory:** Can Polaris reconstruct what was available to the material judgments and reuse Durable Decision Memory later?
* **Learning:** Can Polaris form Decision Evaluations separately from Outcome and preserve useful Lessons?

These questions should later inform release acceptance criteria without requiring roadmap documents to prescribe implementation topology.

## What the capability model deliberately excludes

The model does not elevate implementation or delivery mechanisms into top-level capabilities merely because they are important.

Examples include:

* AI agents;
* LLM providers;
* retrieval or RAG;
* vector databases;
* replay engines;
* workflow orchestration;
* event buses;
* telemetry;
* PostgreSQL;
* MCP;
* APIs;
* reports;
* dashboards;
* CLI;
* email;
* particular market-data providers;
* particular broker integrations.

These mechanisms may implement, expose, strengthen, observe, or broaden one or more capabilities.

The capability model should survive substantial replacement of those mechanisms.

## Architecture relationship

Capabilities are not software boundaries.

Architecture may choose to implement:

* several capabilities in one component;
* one capability across several components;
* shared infrastructure across many capabilities;
* deterministic and analytical mechanisms within the same capability;
* different derived representations over common decision semantics.

The architecture is correct when it preserves the capability and authority contracts—not when the package tree visually resembles this document.

This avoids turning a product model into accidental service decomposition.

## Capability-model decision tests

When evaluating a proposed roadmap item, architecture, subsystem, or major feature, ask:

1. **Which defined capability does this materially advance?**
2. **What product outcome becomes possible or stronger?**
3. **Does it improve maturity, breadth, or both?**
4. **Which semantic capability contracts does it consume or establish?**
5. **Which cross-cutting decision contracts apply?**
6. **Does the proposal preserve the accepted authority boundaries?**
7. **Could a specialist external system continue to own the underlying adjacent responsibility?**
8. **Does this strengthen a coherent end-to-end decision slice or merely add isolated feature surface?**
9. **Would the same capability still exist if the proposed implementation technology were replaced?**

A proposal that cannot answer these questions has not yet demonstrated product-level justification.

## Consequences

The Capability Model implies:

* the nine accepted core capabilities remain the durable product capability spine;
* eight capabilities primarily advance the decision lifecycle while Durable Decision Memory spans and reconnects the entire lifecycle;
* capability interaction is iterative rather than a rigid waterfall;
* capabilities exchange durable product semantics rather than prescribing implementation-specific objects;
* lowercase `decision record` is representation shorthand rather than a separate canonical domain entity;
* authority overlays the lifecycle but Policy, Formal Constraints, Admissibility, Approval, Human Investment Decision, and external authority remain distinct;
* Portfolio Risk and deterministic boundaries shape recommendation formation before Human Investment Decision;
* decision provenance, Judgment-Time Availability, freshness, challenge, authority integrity, and operational reality are cross-cutting contracts rather than additional top-level capabilities;
* supporting platform capabilities are evaluated by how effectively they enable the decision system;
* external specialist systems may remain authoritative even when Polaris integrates with them deeply;
* dependency does not imply ownership;
* releases should mature coherent vertical slices rather than complete isolated subsystems sequentially;
* core capability maturity follows **M1 Bounded → M2 Integrated → M3 Governed → M4 Adaptive**;
* capability breadth is evaluated separately from maturity;
* no durable core capability is considered permanently complete;
* roadmap progress should be described primarily through newly usable, more trustworthy, better connected, more adaptive, or materially broader portfolio decision abilities;
* architecture should implement the capability model without being forced to mirror it structurally.

## Relationship to release strategy and roadmap

This Capability Model is the direct product input to release strategy.

Release strategy should determine how Polaris advances coherent capability maturity over time without reverting to subsystem-first or feature-count planning.

The roadmap should then express those strategic choices as releases and milestones that answer:

> **Which portfolio decision abilities become usable, trustworthy, integrated, governed, adaptive, or broader in this release?**

The expected planning chain is:

```text
Product Definition
        ↓
Core Capabilities
        ↓
Capability Model
        ↓
Release Strategy
        ↓
Roadmap
        ↓
Release Scope
        ↓
Specs / Tickets
```

That ordering keeps implementation subordinate to the durable product contract.
