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
│             └──────────────────→ future attention          │
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
│  Interaction & Projection                                  │
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
│  Market / economic / research evidence                     │
│  Brokerage and execution                                   │
│  Portfolio accounting / books and records                  │
│  Custody / settlement                                      │
│  External analytics                                        │
│  Communication / distribution infrastructure               │
└────────────────────────────────────────────────────────────┘

Across the model:

EVIDENCE → DETERMINISTIC → ANALYTICAL → HUMAN → EXTERNAL ACTION
                         AUTHORITY
```

The capability model is organized around durable product responsibility rather than current software structure.

## Relationship to the Core Capabilities record

[`product-core-capabilities.md`](./product-core-capabilities.md) is the decision record for **why** these capabilities exist and what each capability means in product terms.

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

Eight core capabilities primarily advance a portfolio decision through its lifecycle:

1. **Attention & Decision Initiation**
2. **Decision Context & Evidence**
3. **Investment Reasoning & Challenge**
4. **Portfolio Consequence & Risk**
5. **Recommendation Formation**
6. **Authority & Human Decision**
7. **Action Continuity & Reconciliation**
8. **Outcome Evaluation & Learning**

They form a recognizable product progression, but they are not a rigid waterfall. A later capability may expose missing evidence, invalidate an assumption, require renewed challenge, or trigger reassessment of an earlier decision state.

### Cross-lifecycle core capability

**Durable Decision Memory** is structurally different from the other core capabilities.

It is not a final stage after evaluation. It spans the entire lifecycle and allows prior decision state to influence future attention, reasoning, governance, and learning.

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
* **Interaction & Projection**
* **Configuration & Extensibility**
* **Runtime Reliability & Observability**
* **Security & Operations**

These capabilities may become sophisticated and differentiated, but their product purpose remains subordinate to the portfolio decision lifecycle.

### External specialist responsibilities

Some responsibilities materially participate in Polaris decisions while remaining owned by specialist systems.

Examples include:

* authoritative market and economic evidence;
* brokerage and execution;
* official portfolio accounting and books and records;
* custody and settlement;
* specialist external analytics;
* communication and distribution infrastructure.

Polaris may consume, normalize, reason over, reconcile, and project these systems' state. Integration does not transfer their broader specialist authority or product responsibility to Polaris.

The governing rules remain:

> **Polaris owns decisions, not everything decisions touch.**

> **Dependency does not imply ownership.**

## Semantic capability contracts

Capabilities should exchange **product semantics**, not implementation-specific objects.

The model therefore describes what each core capability primarily consumes and what it establishes for the lifecycle.

| Capability | Primarily consumes | Primarily establishes |
| --- | --- | --- |
| Attention & Decision Initiation | active decisions, theses, review conditions, portfolio context, new information | **Decision need / attention state** |
| Decision Context & Evidence | decision need, portfolio context, external evidence, prior memory | **Decision-ready context and attributable evidence** |
| Investment Reasoning & Challenge | evidence, context, historical knowledge | **Interpretation, alternatives, counterevidence, uncertainty, invalidation conditions** |
| Portfolio Consequence & Risk | interpretation, actual portfolio state, strategy, policy | **Portfolio implications, analytical risk, applicable constraints** |
| Recommendation Formation | reasoning, alternatives, portfolio consequences, risk | **Preferred action or justified withholding, alternatives, rationale** |
| Authority & Human Decision | candidate recommendation, evidence sufficiency, policy, authority state | **Admissibility, authority trace, human decision** |
| Action Continuity & Reconciliation | human decision, action intent, authoritative external action evidence | **Reconciled action/execution state and resulting portfolio state** |
| Outcome Evaluation & Learning | original decision record, observed action, later evidence, outcome | **Evaluation and durable lessons** |
| Durable Decision Memory | every material lifecycle state | **Historically faithful decision context available to future capabilities** |

These are conceptual contracts. They do not imply one database entity, service boundary, event schema, API payload, or workflow node per capability.

## The decision record as connective product state

The Product Definition uses **decision record** as the working concept for the durable representation of a portfolio decision.

The capability model treats that record as connective product state rather than as a prescribed implementation object.

As a decision matures, the durable record may progressively contain or connect:

```text
Decision need
      ↓
Decision context
      ↓
Attributable evidence
      ↓
Interpretation + challenge
      ↓
Portfolio consequences
      ↓
Risk + policy
      ↓
Recommendation
      ↓
Authority path
      ↓
Human decision
      ↓
Action intent
      ↓
Observed external action
      ↓
Resulting state
      ↓
Outcome
      ↓
Evaluation
      ↓
Lessons
```

The capabilities should strengthen this shared lifecycle rather than create isolated local truths that must later be reconstructed.

## Capability interaction is iterative, not waterfall

The directional capability chain describes the dominant product flow, not a one-way execution constraint.

Examples of legitimate backward movement include:

* reasoning discovers that required evidence is missing;
* portfolio analysis makes an initially attractive thesis irrelevant;
* deterministic policy removes an action from consideration;
* recommendation formation exposes unresolved uncertainty requiring further challenge;
* execution divergence reopens the decision;
* outcome evaluation identifies a lesson that changes future attention criteria;
* new evidence invalidates an active thesis and reinitiates decision work.

Conceptually:

```text
Attention
   ↓
Evidence ⇄ Reasoning ⇄ Portfolio/Risk ⇄ Recommendation
   ↑                                      ↓
   └──────── reassessment as needed ──────┘
                                          ↓
                                   Human Decision
                                          ↓
                                     External Action
                                          ↓
                                       Evaluation
                                          │
                                          └──→ future Attention
```

The product should preserve the lifecycle's semantic state across these iterations rather than treating each analytical pass as an unrelated run.

## Authority overlays the capability model

Authority is not a late approval stamp added after analytical work.

The accepted separation-of-powers model applies across the capability system:

```text
EVIDENCE AUTHORITY
What is true?
        ↓
DETERMINISTIC AUTHORITY
What is admissible and trustworthy?
        ↓
ANALYTICAL AUTHORITY
What does this mean and what should we consider?
        ↓
HUMAN DECISION AUTHORITY
What will we do?
        ↓
EXTERNAL ACTION AUTHORITY
What actually gets carried out?
        ↓
EVIDENCE RETURNS
What actually happened?
```

The named **Authority & Human Decision** capability owns the explicit transition from an admissible recommendation to preserved human judgment and authority provenance.

That does not mean deterministic or evidence authority waits until that stage.

For example, recommendation formation must already be shaped by portfolio risk and applicable deterministic policy:

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
              Recommendation  │
                    ▲         │
                    │         │
         Deterministic policy │
         and constraints ─────┘
                    │
                    ▼
           admissible recommendation
                    │
                    ▼
              Human Decision
```

A capability may be able to perform an action without possessing the authority to make the corresponding consequential decision. Capability and authority must remain distinct.

## Cross-cutting decision contracts

Several product responsibilities apply horizontally across capabilities. They should not be promoted into additional top-level capabilities merely because they are important.

### Decision provenance

Material evidence, reasoning, constraints, authority decisions, human judgment, observed action, and outcome should remain attributable enough to reconstruct the meaningful decision path.

### Decision-time integrity

Polaris must distinguish:

```text
What is known now
```

from:

```text
What was knowable then
```

Later evidence may inform evaluation and learning without rewriting the historical decision-time world.

### Decision-appropriate freshness

Evidence must be current enough for the decision contract being claimed.

When required evidence is stale, Polaris should qualify, degrade, withhold, or invalidate the affected decision state rather than silently lower the trust standard.

### Meaningful challenge and uncertainty

Material counterevidence, alternative explanations, uncertainty, and invalidation conditions should not disappear merely because the system has formed a preferred interpretation or recommendation.

### Authority integrity

Evidence, deterministic, analytical, human, and external action authorities must remain semantically distinct where material.

Positive authority decisions such as satisfied constraints and permitted actions should be preservable rather than inferred from the absence of recorded failure.

### Operational reality

When Polaris's expectation conflicts with an authoritative external source within that source's responsibility domain, operational reality wins.

Polaris may preserve and investigate the discrepancy. It must not silently rewrite external reality to match its previous recommendation or expected state.

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

### Interaction & Projection

Enables user and machine interaction with shared decision semantics through surfaces such as conversation, UI, reports, CLI, API, MCP, email, and messaging.

Conceptually:

```text
                 Polaris decision system

                       ↓  ↓  ↓

Web / Conversation / Reports / CLI / API / MCP / Messaging
```

Surfaces should project common governed decision state rather than reconstruct competing versions of the decision.

### Configuration & Extensibility

Enables Polaris to adapt to differences in:

* portfolio;
* strategy;
* asset universe;
* investment horizon;
* evidence providers;
* analytical models;
* risk policy;
* review conditions;
* operating preferences.

Configurability should remain expressed through investment-domain concepts rather than turning Polaris into an arbitrary workflow or agent platform.

### Runtime Reliability & Observability

Enables decision work to execute reliably, preserve relevant state, expose failures, support recovery, and remain operationally inspectable.

Its value is measured by trustworthy decision continuity rather than by runtime sophistication for its own sake.

### Security & Operations

Protects credentials, portfolio information, integrations, configuration, access boundaries, and other operational trust assumptions required by the product's maturity.

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
| Market/economic evidence | responsible evidence provider | determine decision relevance, freshness, provenance, sufficiency, interpretation |
| Brokerage/execution | broker or execution system | preserve action intent, observe and reconcile what occurred |
| Official portfolio state | authoritative portfolio/accounting system where applicable | consume trustworthy state and apply it to portfolio decisions |
| Custody/settlement | specialist operational system | use relevant resulting evidence when it affects decision state |
| External analytics | specialist analytical source | attribute and incorporate relevant evidence without laundering it into native fact |
| Distribution infrastructure | communication destination/provider | project Polaris decision state without creating independent semantics |

A proposal to absorb an external specialist responsibility should therefore carry an explicit burden of proof when it creates a new primary user job, authority domain, latency regime, operational contract, regulatory burden, or product identity.

## Capability dependency model

Core capabilities depend on one another, but dependency does not mean roadmap sequencing must complete one capability before another begins.

The dependency direction is primarily semantic:

```text
Attention
   requires durable context about what matters

Evidence
   requires a decision need and relevant external/internal context

Reasoning
   requires decision-ready evidence

Portfolio/Risk
   requires an interpretation plus real portfolio state and policy

Recommendation
   requires challenged reasoning and portfolio consequences

Authority/Human Decision
   requires an admissible candidate recommendation and explicit authority state

Action Continuity
   requires a human decision/action intent plus authoritative external evidence

Evaluation/Learning
   requires historically faithful decision, action, and outcome state

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

* Attention can identify materially changed conditions for a limited set of supported decision contexts.
* Action Continuity can reconcile a deliberately limited class of external action reliably.
* Evidence can construct trustworthy decision context from a deliberately limited source set.

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
* authority;
* uncertainty;
* historical integrity;
* explicit fail-closed behavior;
* external factual authority;
* durable semantic state.

M3 means the capability is not merely useful; it participates in the product's trust model.

### M4 — Adaptive

Durable portfolio, decision, authority, outcome, and lesson state materially changes the capability's future behavior where appropriate.

Examples include:

```text
Previous invalidation condition
        ↓
New evidence
        ↓
Automatic reassessment
```

or:

```text
Previous decision evaluation
        ↓
Future attention / reasoning / policy review improves
```

Adaptive maturity should be grounded in durable product state rather than vague claims that an AI model "learns."

### No terminal "complete" level

The model intentionally does not define an M5 such as **Complete**.

Core capabilities can deepen indefinitely as Polaris supports richer portfolios, more evidence, stronger decision contracts, better analytical techniques, more sophisticated reconciliation, and improved learning.

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
* evidence providers;
* portfolio structures;
* strategies;
* time horizons;
* risk policies;
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
many evidence sources
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

* **Attention:** Can Polaris identify that something materially changed and explain why it affects an active portfolio decision?
* **Evidence:** Can Polaris reconstruct the attributable evidence that supported the decision and determine whether it was current enough?
* **Challenge:** Can the user inspect meaningful evidence or reasoning against the preferred interpretation?
* **Portfolio & Risk:** Can Polaris explain how actual portfolio state and risk changed the action implied by the investment view?
* **Recommendation:** Can Polaris explain the preferred action, meaningful alternatives, and conditions that would change the view?
* **Authority:** Can the material authority path be reconstructed, including affirmative policy decisions and the human decision?
* **Continuity:** Can Polaris determine whether the human decision was actually reflected in authoritative external action?
* **Memory:** Can Polaris reconstruct what was knowable when the decision occurred and reuse durable decision state later?
* **Learning:** Can Polaris evaluate process quality separately from realized outcome and preserve useful lessons?

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
* different projections over common decision semantics.

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
* the decision record is connective product state, not a mandated storage architecture;
* authority overlays the lifecycle and must not be reduced to a late approval gate;
* deterministic policy and risk must shape recommendation formation before human decision;
* decision provenance, historical integrity, freshness, challenge, authority integrity, and operational reality are cross-cutting contracts rather than additional top-level capabilities;
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