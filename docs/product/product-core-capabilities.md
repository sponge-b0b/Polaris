# Polaris Core Capabilities

**Status:** In progress  
**Purpose:** Preserve the product reasoning for the durable abilities Polaris must provide to make the defined portfolio decision system real, independent of current implementation topology.

This document refines the Product Definition recorded in [`product-definition.md`](./product-definition.md). It defines **what Polaris must be able to do**, not which packages, agents, workflows, databases, interfaces, or technologies must implement those abilities.

## Decision

Polaris requires nine core product capabilities that together close the portfolio decision lifecycle:

1. **Attention & Decision Initiation**
2. **Decision Context & Evidence**
3. **Investment Reasoning & Challenge**
4. **Portfolio Consequence & Risk**
5. **Recommendation Formation**
6. **Authority & Human Decision**
7. **Action Continuity & Reconciliation**
8. **Durable Decision Memory**
9. **Outcome Evaluation & Learning**

Conceptually:

```text
Attention & Decision Initiation
            ↓
Decision Context & Evidence
            ↓
Investment Reasoning & Challenge
            ↓
Portfolio Consequence & Risk
            ↓
Recommendation Formation
            ↓
Authority & Human Decision
            ↓
Action Continuity & Reconciliation
            ↓
Outcome Evaluation & Learning
            │
            └────────→ future attention

Durable Decision Memory spans the entire lifecycle.
```

These are durable product abilities. Their implementation may change substantially without changing the capability model.

## Why capabilities are not features or subsystems

A capability answers:

> **What must Polaris be able to accomplish for the product contract to be true?**

It does not answer:

> How is Polaris currently built?

Therefore technologies and implementation mechanisms such as agents, retrieval, replay, workflow orchestration, telemetry, databases, MCP, APIs, report generators, or particular model providers are not core capabilities by themselves. They may implement, expose, strengthen, or observe one or more capabilities.

The capability model should survive replacement of those mechanisms.

## 1. Attention & Decision Initiation

Polaris must be able to determine **what deserves attention and when a portfolio decision should be created, reopened, or reassessed**.

Decision work may begin through at least three paths:

```text
User question ───────────────┐
                             │
Scheduled review ────────────┼──→ Decision work
                             │
Polaris detects relevance ───┘
```

The capability should relate new information to active portfolio context such as:

* current decisions;
* active theses;
* assumptions and invalidation conditions;
* material risks;
* catalysts;
* deferred decisions;
* review conditions;
* relevant portfolio changes;
* newly available evidence.

The product responsibility is not merely to emit alerts. It is to determine whether changing information materially creates or changes a portfolio decision.

A useful conceptual flow is:

```text
new information
      ↓
relevant to active decision context?
      │
   no └──→ absorb quietly

  yes
   ↓
material?
      │
   no └──→ update context

  yes
   ↓
investigate / initiate decision work
```

Without this capability Polaris becomes merely responsive rather than attentive.

## 2. Decision Context & Evidence

Polaris must be able to assemble the **decision-specific context and attributable evidence necessary to reason responsibly**.

Decision context may include:

* portfolio state;
* strategy and mandate;
* investment horizon;
* risk policy;
* active thesis;
* previous decisions and recommendations;
* unresolved questions;
* historical decision context.

Decision evidence may include:

* market evidence;
* macroeconomic evidence;
* company or security evidence;
* news and research;
* technical evidence;
* historical evidence;
* portfolio facts;
* execution facts;
* relevant external analytics.

The capability must do more than acquire information. It must preserve or determine, where material:

* provenance;
* observation time;
* decision-time availability;
* freshness;
* sufficiency;
* conflicts between sources;
* historical integrity.

A useful shorthand is:

```text
relevant context
+
attributable evidence
+
freshness
+
sufficiency
+
historical integrity
```

The objective is decision-ready evidence, not comprehensive information possession.

## 3. Investment Reasoning & Challenge

Polaris must be able to **develop an investment interpretation and seriously test why it may be wrong**.

This capability may include:

* synthesis;
* thesis formation;
* causal interpretation;
* scenario reasoning;
* comparison of competing explanations;
* uncertainty identification;
* alternative generation;
* disconfirming-evidence search;
* assumption identification;
* falsification or invalidation conditions;
* relevant historical comparison.

A trustworthy reasoning result should be capable of representing:

```text
Leading interpretation
        +
Supporting evidence
        +
Counterevidence
        +
Alternative explanations
        +
Key uncertainty
        +
Invalidation conditions
```

Challenge is a product requirement, not a commitment to a particular multi-agent topology. One model, several models, deterministic analytics, or other mechanisms may participate as long as the product capability remains intact.

## 4. Portfolio Consequence & Risk

Polaris must be able to translate an investment view into **consequences for the actual portfolio under explicit risk and policy**.

Relevant portfolio context may include:

* holdings;
* exposure;
* concentration;
* cash where relevant;
* portfolio objectives;
* strategy;
* horizon;
* competing positions;
* existing and incremental risk;
* configured policies and constraints.

Risk participates in two complementary forms:

* **Analytical risk:** what could go wrong, how risk has changed, and what the implications are.
* **Deterministic risk authority:** which explicit configured constraints permit, constrain, or prohibit an action.

The capability therefore transforms:

```text
Investment view
        +
Portfolio state
        +
Analytical risk
        +
Policy constraints
        ↓
Portfolio consequences
```

The same investment thesis may correctly imply different actions for different portfolios. This capability is what prevents Polaris from becoming a generic signal or research product.

Risk remains integrated with portfolio consequence rather than becoming a detached approval stamp.

## 5. Recommendation Formation

Polaris must be able to **compare reasonable portfolio actions under uncertainty and form an explainable preferred course of action—or deliberately withhold one**.

Candidate actions may include, where appropriate:

* increase;
* reduce;
* hold;
* enter;
* exit;
* rebalance;
* hedge;
* wait;
* defer;
* deliberately do nothing.

A recommendation should be capable of communicating a decision package containing, as applicable:

* preferred action;
* rationale;
* material evidence;
* portfolio consequence;
* risk;
* meaningful alternatives;
* strongest counterargument;
* key uncertainty;
* invalidation conditions;
* horizon or review conditions.

The capability is not merely BUY/SELL/HOLD generation. It includes the ability to conclude that no action is warranted or that the decision contract cannot presently support a responsible recommendation.

## 6. Authority & Human Decision

Polaris must be able to **apply the separation-of-powers authority model and preserve the human decision as distinct from the system recommendation**.

This capability includes, where material:

* evidence sufficiency decisions;
* deterministic policy evaluation;
* hard and soft constraints;
* recommendation admissibility;
* positive authority provenance;
* human acceptance;
* human modification;
* rejection;
* deferral;
* human rationale where supplied.

Conceptually:

```text
Candidate recommendation
      ↓
Evidence sufficient?
      ↓
Policies evaluated
      ↓
Admissible recommendation
      ↓
Human judgment
      ↓
Decision
```

Every material authority decision should remain attributable, including affirmative decisions such as satisfied constraints and permitted actions. Silence is not proof that authority was exercised correctly.

## 7. Action Continuity & Reconciliation

Polaris must be able to **follow a human decision into externally executed reality without acquiring execution authority**.

This capability begins with the intended external consequence of the human decision and reconciles it with authoritative external evidence.

It may need to understand:

* intended action;
* observed order or activity;
* partial execution;
* complete execution;
* modified action;
* abandoned action;
* stops and targets;
* exits;
* ambiguous associations;
* unrelated externally initiated activity;
* resulting portfolio state.

The core contract is:

> **Observe, associate, reconcile, and track external action without owning market-facing execution.**

Where evidence makes an association sufficiently unambiguous, reconciliation should be automatic. Where ambiguity materially changes meaning, Polaris should preserve the ambiguity and request lightweight confirmation rather than guess.

Without this capability the decision lifecycle loses continuity between human judgment and later outcome.

## 8. Durable Decision Memory

Polaris must be able to **preserve a decision faithfully through time and use that memory as active product context**.

Decision memory may preserve or connect:

* the decision need;
* decision context;
* evidence and provenance;
* what was knowable at the time;
* interpretation and challenge;
* risk and alternatives;
* recommendation;
* authority trace;
* human decision;
* intended external action;
* observed execution;
* resulting state;
* outcome;
* evaluation;
* lessons.

This capability is richer than saving workflow output, reports, or chat history.

A fundamental trust requirement is the ability to distinguish:

```text
What we know now
```

from:

```text
What was knowable then
```

Decision memory is also operational rather than merely archival. Previous theses, assumptions, invalidation conditions, risks, catalysts, deferred decisions, and review conditions can determine what future information deserves attention.

For that reason Durable Decision Memory spans the entire capability loop rather than occurring only after action.

## 9. Outcome Evaluation & Learning

Polaris must be able to **evaluate the decision process and derive useful lessons from outcomes without reducing quality to realized P&L**.

Evaluation should be capable of distinguishing, where evidence permits:

* evidence quality;
* reasoning quality;
* thesis quality;
* risk reasoning;
* policy effects;
* recommendation quality;
* human modification or override;
* execution fidelity;
* realized outcome.

A profitable result is not automatically proof of good reasoning, and a negative probabilistic outcome is not automatically proof that a well-formed decision was poor.

Useful evaluation questions may include:

* Which assumptions held or failed?
* Which evidence was material or misleading?
* Was risk identified appropriately?
* Did policy improve or degrade the decision?
* Did the human alter the recommendation?
* Was execution faithful to the decision?
* Did execution divergence explain the outcome?
* Did the thesis fail, or did an adverse outcome occur despite reasonable reasoning?
* Which lesson should influence future attention, reasoning, policy review, or decision-making?

The learning loop is:

```text
Evaluation
    ↓
Lessons
    ↓
Future context / attention / reasoning / policy review
```

This capability closes the lifecycle.

## Why AI is not a separate core capability

AI is an important method used across several core capabilities, particularly attention, evidence interpretation, reasoning, challenge, recommendation, and evaluation.

It is not itself the user capability.

The same principle applies to deterministic software. Polaris should continue to use AI where reasoning and synthesis add value and deterministic mechanisms where guarantees and explicit rules matter.

The capability model should therefore remain organized around product responsibilities rather than implementation techniques.

## Why evidence domains are not top-level core capabilities

Market, macroeconomic, news, sentiment, technical, fundamental, and similar forms of intelligence are important evidence domains.

At this level they primarily participate in **Decision Context & Evidence** and **Investment Reasoning & Challenge** rather than becoming independent product centers.

This prevents the capability model from recreating a feature-oriented architecture such as:

```text
Market
Macro
News
Sentiment
Technical
```

The domains may be decomposed further in later capability or architecture work without changing the top-level product model.

## Why interfaces are not top-level core capabilities

Reports, dashboards, conversation, CLI, API, MCP, email, and future interfaces are projections or interaction surfaces over the same decision system.

They should not create competing decision semantics.

Conceptually:

```text
                Polaris decision system

                      ↓  ↓  ↓

Web / Conversation / Reports / CLI / API / MCP / Messaging
```

The underlying product capability remains the same regardless of surface.

## Supporting platform capabilities

The core nine depend on important supporting platform capabilities. These are product-enabling responsibilities rather than independent product centers.

### Integration & Connectivity

Connect Polaris to decision-relevant evidence, portfolio state, execution systems, external tools, and distribution destinations.

### Interaction & Projection

Expose shared decision state through appropriate user and machine surfaces such as conversation, interactive UI, reports, CLI, API, MCP, email, or messaging.

### Configuration & Extensibility

Adapt Polaris to different portfolios, strategies, asset universes, evidence providers, models, risk policies, horizons, and operating preferences without turning the product into an arbitrary workflow platform.

### Runtime Reliability & Observability

Execute decision work reliably, make failures visible, preserve relevant state and provenance, support recovery where appropriate, and make lifecycle execution inspectable.

### Security & Operations

Protect credentials, portfolio information, integrations, configuration, access boundaries, and operational trust assumptions appropriate to the product's maturity.

These supporting capabilities may become sophisticated. Their purpose remains to enable the portfolio decision system.

## Capability hierarchy

The durable hierarchy is:

```text
                        POLARIS

              Portfolio Decision System

                           │

        ┌──────────────────┴──────────────────┐
        │          CORE CAPABILITIES          │
        │                                     │
        │  Attention & Decision Initiation    │
        │  Decision Context & Evidence        │
        │  Investment Reasoning & Challenge   │
        │  Portfolio Consequence & Risk       │
        │  Recommendation Formation           │
        │  Authority & Human Decision         │
        │  Action Continuity & Reconciliation │
        │  Durable Decision Memory            │
        │  Outcome Evaluation & Learning      │
        └──────────────────┬──────────────────┘
                           │
                      enabled by
                           │
        ┌──────────────────┴──────────────────┐
        │      SUPPORTING PLATFORM            │
        │        CAPABILITIES                 │
        │                                     │
        │  Integration & Connectivity         │
        │  Interaction & Projection           │
        │  Configuration & Extensibility      │
        │  Reliability & Observability        │
        │  Security & Operations              │
        └─────────────────────────────────────┘
```

## Capabilities should be testable in product language

Core capabilities should eventually support product-level acceptance questions rather than implementation-presence checks.

Examples:

* **Attention:** Can Polaris identify that something materially changed and explain why it deserves attention?
* **Evidence:** Can Polaris show which evidence informed the decision and whether it was sufficiently current?
* **Challenge:** Can the user inspect the strongest meaningful argument against the preferred view?
* **Portfolio & Risk:** Can Polaris explain how actual portfolio state and risk changed the action implied by the investment view?
* **Recommendation:** Can Polaris explain the preferred action, alternatives, and conditions that would change the view?
* **Authority:** Can the material authority path be reconstructed, including affirmative decisions?
* **Continuity:** Can Polaris determine whether the human decision was actually implemented externally?
* **Memory:** Can Polaris reconstruct what was knowable when the decision occurred?
* **Learning:** Can Polaris evaluate the decision process separately from the realized outcome?

These questions can later become release and capability-maturity criteria without binding the roadmap to current code topology.

## Capability maturity evolves across releases

A capability being core does not mean every release must implement its ultimate depth.

For example, Action Continuity may begin with basic reconciliation of imported or polled broker activity and later mature into persistent near-real-time lifecycle observation and more sophisticated ambiguity handling.

The durable capability remains the same while its maturity increases.

This suggests a roadmap discipline:

> **Describe releases in terms of which end-to-end product abilities become usable, trustworthy, broader, or more mature—not merely which implementation features were accumulated.**

That discipline should help prevent the roadmap from reverting to a feature backlog.

## Consequences

The Core Capabilities decision implies:

* the nine core capabilities form the durable product capability spine;
* Durable Decision Memory spans and supports the entire lifecycle;
* AI, agents, workflows, retrieval, replay, persistence technologies, APIs, interfaces, and reports are implementation or delivery mechanisms rather than top-level core capabilities;
* evidence domains such as market, macro, news, sentiment, and technical analysis should remain subordinate to decision-oriented capabilities at this level;
* risk remains integrated with portfolio consequence and recommendation formation rather than treated as a detached approval step;
* execution observation and reconciliation are core even though execution authority remains external;
* evaluation must distinguish process quality from outcome alone;
* supporting platform capabilities enable the core system but do not compete with it for product identity;
* capability maturity may deepen across releases without redefining the capability model;
* roadmap milestones should increasingly be expressed as user-visible capability maturity and end-to-end decision guarantees rather than feature lists.

## Relationship to later Product Definition work

The remaining **Product Principles** section should distill the governing rules that cut across all nine capabilities and the supporting platform without restating the capability model itself.