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

Polaris must be able to determine **what deserves Attention, when a Decision Need exists, when an unresolved Investment Decision should resume, and when a resolved matter warrants a new causally linked Investment Decision**.

Decision work may begin through at least three paths:

```text
User question ───────────────┐
                             │
Scheduled review ────────────┼──→ Attention / Decision Need
                             │
Polaris detects relevance ───┘
```

The capability should relate new information to active portfolio context such as:

* unresolved Investment Decisions;
* active Investment Theses;
* Investment Assumptions and Invalidation Conditions;
* material Portfolio Risk;
* Catalysts;
* deferred Investment Decisions;
* Review Conditions;
* relevant Portfolio State changes;
* newly available Evidence.

The product responsibility is not merely to emit alerts. It is to determine whether changing information is sufficiently relevant and material to establish or change a Decision Need or to contribute to existing decision work.

A useful conceptual flow is:

```text
new information
      ↓
Investment Relevant?
      │
   no └──→ absorb quietly

  yes
   ↓
Investment Material?
      │
   no └──→ update applicable context

  yes
   ↓
Attention evaluates whether a Decision Need exists
      ↓
resume same unresolved choice
or create new causally linked decision after prior resolution
```

Without this capability Polaris becomes merely responsive rather than attentive.

## 2. Decision Context & Evidence

Polaris must be able to assemble the **decision-specific context and attributable Evidence necessary to reason responsibly**.

Decision Context may include:

* Portfolio State;
* applicable Investment Strategy and Investment Mandate;
* Investment Horizon;
* applicable Formal Constraints and Policy;
* active Investment Thesis;
* previous Investment Decisions and Investment Recommendations;
* unresolved questions;
* relevant historical decision context.

Evidence may include:

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
* Judgment-Time Availability;
* freshness;
* sufficiency;
* conflicts between sources;
* historical integrity.

A useful shorthand is:

```text
relevant Decision Context
+
attributable Evidence
+
freshness
+
sufficiency
+
historical integrity
```

The objective is decision-ready Evidence, not comprehensive information possession.

## 3. Investment Reasoning & Challenge

Polaris must be able to **develop an Investment View and seriously test why it may be wrong**.

This capability may include:

* synthesis;
* Investment Hypothesis and Investment Thesis reasoning;
* causal interpretation;
* Investment Scenario reasoning;
* comparison of competing explanations;
* Investment Uncertainty identification;
* Decision Alternative generation;
* disconfirming-Evidence search;
* Investment Assumption identification;
* Invalidation Conditions;
* relevant historical comparison.

A trustworthy reasoning result should be capable of representing:

```text
Leading Investment View
        +
Supporting Evidence
        +
Conflicting Evidence
        +
Alternative explanations / Investment Hypotheses
        +
Material Investment Uncertainty
        +
Invalidation Conditions
```

Challenge is a product requirement, not a commitment to a particular multi-agent topology. One model, several models, deterministic analytics, or other mechanisms may participate as long as the product capability remains intact.

## 4. Portfolio Consequence & Risk

Polaris must be able to translate an Investment View into **Projected Portfolio Consequences and Portfolio Risk for the actual Portfolio under the applicable Investment Mandate and Policy**.

Relevant Portfolio context may include:

* Positions;
* Exposure;
* concentration;
* cash where relevant;
* Investment Objectives;
* Investment Strategy;
* Investment Horizon;
* competing Positions or opportunities;
* current and projected Portfolio Risk;
* Formal Constraints;
* applicable platform Policy.

Two different responsibilities must remain distinct:

* **Portfolio Risk reasoning:** what adverse possibilities exist, how Portfolio Risk changes, and what those risks imply for the Portfolio and alternatives.
* **Deterministic boundary evaluation:** whether applicable Formal Constraints are satisfied, violated, or indeterminate and whether platform Policy allows or denies the relevant operation or boundary crossing.

The capability therefore transforms:

```text
Investment View
        +
Portfolio State
        +
Portfolio Risk
        +
Investment Mandate / Formal Constraints
        +
Policy
        ↓
Projected Portfolio Consequences
and decision-relevant constraints
```

The same Investment Thesis may correctly imply different consequences or recommendations for different Portfolios. This capability is what prevents Polaris from becoming a generic signal or research product.

Portfolio Risk remains integrated with portfolio consequence rather than becoming a detached approval stamp. Deterministic Policy or Formal Constraint results are likewise not themselves Approval or human investment judgment.

## 5. Recommendation Formation

Polaris must be able to **compare reasonable Decision Alternatives under uncertainty and form an explainable Investment Recommendation—or deliberately withhold one**.

Decision Alternatives may include, where appropriate:

* increase;
* reduce;
* hold;
* enter;
* exit;
* rebalance;
* hedge;
* wait;
* Deferral;
* deliberate no-action.

A Decision Alternative may require zero, one, or multiple concrete Proposed Actions. Proposed Actions are candidate implementations, not Human Investment Decisions or Action Intents.

An Investment Recommendation should be capable of communicating, as applicable:

* preferred economic disposition;
* rationale;
* Material Claims and Evidence;
* Projected Portfolio Consequences;
* Portfolio Risk;
* meaningful Decision Alternatives;
* Proposed Actions or implementation preferences where useful;
* strongest counterargument;
* material Investment Uncertainty;
* Invalidation Conditions;
* Investment Horizon or Review Conditions.

The capability is not merely BUY/SELL/HOLD generation. It includes the ability to conclude that no action is warranted, that judgment should be deferred, or that available Evidence cannot presently support a responsible Investment Recommendation.

## 6. Authority & Human Decision

Polaris must be able to **apply the separation-of-powers authority model and preserve Human Investment Decision as distinct from the Investment Recommendation and from other authority acts**.

This capability includes, where material:

* Evidence sufficiency and readiness determination;
* deterministic Policy evaluation;
* Formal Constraint results;
* Admissibility for the relevant consequential use;
* Approval or Authority Denial where required;
* Mandate Exception authorization where applicable;
* Residual-Risk Acceptance where applicable;
* Human Investment Decision;
* human rationale where supplied.

Conceptually:

```text
Candidate Investment Recommendation
      ↓
Evidence / readiness sufficient?
      ↓
Policy and Formal Constraints evaluated
      ↓
Admissibility established for the intended use
      ↓
Applicable authority acts satisfied where required
      ↓
Human Investment Decision
```

Approval is not synonymous with a human accepting an Investment Recommendation. Human Investment Decision, Approval, Mandate Exception, Residual-Risk Acceptance, and other authority powers remain distinct even when the same human performs more than one of those acts.

Every material authority decision should remain attributable, including affirmative decisions such as satisfied constraints, granted Approval, or accepted Governed Residual Risk. Silence is not proof that authority was exercised correctly.

## 7. Action Continuity & Reconciliation

Polaris must be able to **follow a Human Investment Decision into externally observed reality without acquiring execution authority**.

When the Human Investment Decision establishes an externally observable implementation consequence, it may establish one or more Action Intents. Polaris then reconciles authoritative external evidence against those Action Intents.

It may need to understand:

* Action Intent;
* observed Order or external activity;
* partial execution;
* complete execution;
* modified external activity;
* abandoned or absent implementation;
* externally maintained controls such as stops where they are genuinely part of the Action Intent;
* exits;
* ambiguous associations;
* unrelated externally initiated activity;
* resulting Portfolio State.

The core contract is:

> **Observe, associate, reconcile, and track external activity without owning market-facing execution.**

Where Evidence makes an association sufficiently unambiguous, reconciliation should be automatic. Where ambiguity materially changes meaning, Polaris should preserve the ambiguity and request lightweight confirmation rather than guess.

A Human Investment Decision may establish zero Action Intents. Deferral and deliberate hold/no-action do not require synthetic Action Intents merely to duplicate the human judgment.

Without this capability the decision lifecycle loses continuity between human judgment and later Outcome.

## 8. Durable Decision Memory

Polaris must be able to **preserve material Investment Decision history faithfully through time and use that memory as active product context**.

Durable Decision Memory may preserve or connect:

* Decision Need;
* Decision Context;
* Evidence and provenance;
* Judgment-Time Availability;
* Investment Views, Investment Hypotheses, and challenge;
* Portfolio Risk and Decision Alternatives;
* Investment Recommendation history;
* material authority relationships and acts;
* Human Investment Decision;
* Action Intents;
* observed external activity;
* resulting Portfolio State;
* Outcome;
* Decision Evaluation;
* Lessons.

This capability is richer than saving workflow output, reports, chat history, or a single storage record. Lowercase `decision record` may remain product shorthand for an assembled representation of this history, but it is not a separate canonical business entity.

A fundamental trust requirement is the ability to distinguish:

```text
What we know now
```

from:

```text
What was available to the judgment then
```

Durable Decision Memory is also operational rather than merely archival. Previous Investment Theses, Investment Assumptions, Invalidation Conditions, Portfolio Risks, Catalysts, deferred decisions, and Review Conditions can determine what future information deserves Attention.

For that reason Durable Decision Memory spans the entire capability loop rather than occurring only after action.

## 9. Outcome Evaluation & Learning

Polaris must be able to **form Decision Evaluations and derive useful Lessons from Outcomes without reducing decision quality to realized P&L**.

Decision Evaluation should be capable of distinguishing, where Evidence permits:

* Evidence quality;
* reasoning quality;
* Investment Thesis quality;
* Portfolio Risk reasoning;
* Policy and Formal Constraint effects;
* Investment Recommendation quality;
* Human Investment Decision and any modification or override;
* implementation fidelity;
* observed Outcome.

A favorable Outcome is not automatically proof of good reasoning, and an unfavorable Outcome is not automatically proof that a well-formed decision was poor.

Useful evaluation questions may include:

* Which Investment Assumptions held or failed?
* Which Evidence was material or misleading?
* Was Portfolio Risk identified appropriately?
* Did Policy or a Formal Constraint materially shape the decision?
* How did the Human Investment Decision relate to the Investment Recommendation?
* Was implementation faithful to the Action Intent where one existed?
* Did implementation divergence materially affect the Outcome?
* Did the Investment Thesis fail, or did an adverse Outcome occur despite reasonable reasoning?
* Which Lesson should influence future Attention, reasoning, Policy or Mandate review, or investment judgment?

The learning loop is:

```text
Decision Evaluation
    ↓
Lessons
    ↓
Future Decision Context / Attention / reasoning / Policy or Mandate review
```

This capability closes the lifecycle.

## Why AI is not a separate core capability

AI is an important method used across several core capabilities, particularly Attention, Evidence interpretation, reasoning, challenge, recommendation, and evaluation.

It is not itself the user capability.

The same principle applies to deterministic software. Polaris should continue to use AI where reasoning and synthesis add value and deterministic mechanisms where guarantees and explicit rules matter.

The capability model should therefore remain organized around product responsibilities rather than implementation techniques.

## Why evidence domains are not top-level core capabilities

Market, macroeconomic, news, sentiment, technical, fundamental, and similar forms of intelligence are important Evidence domains.

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

Reports, dashboards, conversation, CLI, API, MCP, email, and future interfaces are interaction and presentation surfaces over the same decision system.

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

Connect Polaris to decision-relevant Evidence, Portfolio State, execution systems, external tools, and distribution destinations.

### Interaction & Presentation

Expose shared decision state through appropriate user and machine surfaces such as conversation, interactive UI, reports, CLI, API, MCP, email, or messaging.

### Configuration & Extensibility

Adapt Polaris to different Portfolios, Investment Strategies, asset universes, Evidence providers, models, Policy, Investment Mandates, Investment Horizons, and operating preferences without turning the product into an arbitrary workflow platform.

### Runtime Reliability & Observability

Execute decision work reliably, make failures visible, preserve relevant state and provenance, support recovery where appropriate, and make lifecycle execution inspectable.

### Security & Operations

Protect credentials, Portfolio information, integrations, configuration, access boundaries, and operational trust assumptions appropriate to the product's maturity.

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
        │  Interaction & Presentation         │
        │  Configuration & Extensibility      │
        │  Reliability & Observability        │
        │  Security & Operations              │
        └─────────────────────────────────────┘
```

## Capabilities should be testable in product language

Core capabilities should eventually support product-level acceptance questions rather than implementation-presence checks.

Examples:

* **Attention:** Can Polaris identify that something materially changed, determine whether a Decision Need exists, and explain why?
* **Evidence:** Can Polaris show which Evidence informed a judgment and whether it was sufficiently current and available at that judgment time?
* **Challenge:** Can the user inspect the strongest meaningful argument against the preferred Investment View?
* **Portfolio & Risk:** Can Polaris explain how actual Portfolio State and Portfolio Risk changed the consequences or recommendation implied by the Investment View?
* **Recommendation:** Can Polaris explain the preferred disposition, Decision Alternatives, and conditions that would change the view?
* **Authority:** Can the material authority path be reconstructed without conflating Approval, Human Investment Decision, or other power-specific acts?
* **Continuity:** Can Polaris determine whether an Action Intent was implemented externally when one existed?
* **Memory:** Can Polaris reconstruct what was available to each material judgment when it occurred?
* **Learning:** Can Polaris evaluate the decision process separately from the observed Outcome?

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
* Evidence domains such as market, macro, news, sentiment, and technical analysis should remain subordinate to decision-oriented capabilities at this level;
* Portfolio Risk remains integrated with portfolio consequence and recommendation formation rather than treated as a detached approval step;
* Policy, Formal Constraints, Admissibility, Approval, Human Investment Decision, and related authority acts remain semantically distinct;
* execution observation and reconciliation are core even though execution authority remains external;
* Decision Evaluation must distinguish process quality from Outcome alone;
* supporting platform capabilities enable the core system but do not compete with it for product identity;
* capability maturity may deepen across releases without redefining the capability model;
* roadmap milestones should increasingly be expressed as user-visible capability maturity and end-to-end decision guarantees rather than feature lists.

## Relationship to later Product Definition work

The remaining **Product Principles** section should distill the governing rules that cut across all nine capabilities and the supporting platform without restating the capability model itself.
