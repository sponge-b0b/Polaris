# Polaris Product Definition

**Status:** Defined  
**Purpose:** Define the durable product doctrine that should guide Polaris capability, roadmap, and implementation decisions.

This document describes **what Polaris is and who it is for**. It intentionally avoids implementation technologies and detailed architecture. The fuller reasoning behind these decisions is preserved in [`product-rationale.md`](./product-rationale.md) and in focused companion records linked from the relevant sections.

## Purpose

Polaris exists to help humans make **better, more trustworthy portfolio and investment decisions**.

It turns fragmented market, Portfolio, research, Portfolio Risk, and model Evidence into a repeatable decision process that produces explainable Investment Recommendations for human decision-makers. It should preserve what was known, what Polaris judged, why it judged it, what Investment Uncertainty or disagreement existed, what authority conditions applied, and enough Durable Decision Memory for the Investment Decision to remain inspectable, challengeable, semantically reconstructable, and evaluable later.

Polaris is not valuable merely because it performs financial analysis or automates AI workflows. Analysis, agents, workflows, retrieval, replay, reporting, Governance, and evaluation are supporting mechanisms. Their product value comes from improving the quality, trustworthiness, explainability, repeatability, continuity, or evaluation of Investment Decisions.

Polaris uses AI where AI adds reasoning and synthesis value, deterministic software where explicit rules and guarantees matter, and human authority where consequential investment judgment or another power-specific authority act must remain attributable to an authorized actor.

### Purpose consequences

* **Investment Decisions are the product center.** Analysis must ultimately support decision work, explanation, evaluation, or durable knowledge that improves future decisions.
* **Trustworthiness is a product concern.** An Investment Recommendation should be explainable, inspectable, challengeable, and evaluable after the fact; material decision history should remain semantically reconstructable.
* **AI is a participant, not the governing authority.** The surrounding system should constrain, preserve, and expose Polaris reasoning rather than simply delegate the whole decision to a model.
* **Portfolio context matters.** Polaris should reason about opportunities in the context of Portfolio State, Portfolio Risk, Market Regime, Investment Strategy, Investment Horizon, Investment Mandate, and Decision Alternatives rather than acting as a collection of isolated Investment Signals.
* **Human investment authority remains central.** Polaris supports consequential Investment Decisions; it does not define itself through autonomous capital execution.

## Users

Polaris primarily serves **sophisticated individual portfolio decision-makers and small investment teams practicing discretionary, process-driven portfolio management**.

The primary user already has responsibility for investment decisions and enough financial literacy to understand Portfolio Risk, Exposure, drawdown, Investment Uncertainty, Investment Horizon, and portfolio construction. Polaris is intended to improve an existing or deliberately developing investment process rather than replace basic financial education or human judgment.

The common characteristic is **decision responsibility**, not a particular title. A user may be an investor, trader, portfolio manager, analyst, fund manager, or another role, provided they are responsible for turning Evidence into Portfolio-relevant investment judgment.

Polaris should support an intentional progression from one sophisticated operator wearing several roles to a small team separating responsibilities such as portfolio management, research, risk review, and platform operation. The product model should not require those roles to be separate in order to be useful.

### User and operator distinction

The person receiving investment value from Polaris and the person operating the software are not necessarily the same role.

Early Polaris deployments may require a technically capable operator. That is a current maturity constraint, not a reason to define the product as developer software. The long-term product user is the portfolio decision-maker or investment team; installation, integration, and platform operation are supporting concerns.

### Primary-user characteristics

The intended user:

* makes recurring discretionary Portfolio or investment decisions;
* values a repeatable investment process over ad hoc model answers;
* wants Evidence, Investment Uncertainty, Portfolio Risk, and competing interpretations incorporated into Investment Recommendations;
* expects Investment Recommendations to be explainable and reviewable;
* wants past Investment Decisions and reasoning to remain inspectable and useful for Decision Evaluation;
* understands that Polaris augments judgment rather than predicting the future with certainty.

### Not primary users

Polaris is not primarily designed for:

* beginner investors seeking basic financial education or simple buy/sell answers;
* passive investors whose process has little recurring decision complexity;
* high-frequency or latency-sensitive traders whose core requirements are execution speed and market microstructure;
* fully autonomous or systematic trading operations whose primary need is algorithmic strategy and execution infrastructure;
* large institutional organizations when enterprise identity, access, compliance, integration, and organizational complexity would dominate product design;
* software developers seeking a generic AI-agent or workflow framework.

These exclusions define the primary design center, not an assertion that Polaris can never support adjacent users.

## Problems / Jobs to Be Done

Polaris is hired to help a portfolio decision-maker **turn fragmented and uncertain Evidence into a reasoned, risk-aware Investment Decision; understand and defend that decision; preserve what was available to the material judgments and why an Investment Recommendation was formed; and evaluate the decision process afterward so future decisions can improve**.

The primary job is not to generate activity. A valid result may be to act, wait, reduce, add, rebalance, hedge where appropriate, defer judgment, or deliberately do nothing. The product is responsible for improving decision quality rather than maximizing the number of Investment Recommendations or trades.

### Core jobs

The Polaris decision cycle has six durable user jobs:

1. **Understand the current Decision Context.** Turn fragmented market, macro, news, sentiment, technical, Portfolio, historical, and other Investment-Relevant Evidence into a coherent view of what matters now.
2. **Develop and challenge an Investment View.** Move from facts to a reasoned interpretation while exposing competing Investment Hypotheses, disagreement, Investment Uncertainty, Investment Assumptions, and Evidence that could satisfy an Invalidation Condition or otherwise challenge the leading view.
3. **Translate the view into Projected Portfolio Consequences.** Determine what the Evidence means given current Positions, concentration, Exposure, Investment Strategy, Investment Horizon, Portfolio Risk, Investment Mandate, and competing opportunities.
4. **Choose among Decision Alternatives under explicit Portfolio Risk.** Compare reasonable economic dispositions and tradeoffs, allow Portfolio Risk and applicable deterministic boundaries to shape the Investment Recommendation, and explain what conditions would change the preferred disposition.
5. **Understand, communicate, and defend the decision.** Preserve enough Evidence, Investment Assumptions, disagreement, constraints, reasoning, Investment Recommendation, authority history, and Investment Uncertainty to answer why the judgment was made without reconstructing the analysis from memory.
6. **Learn from decisions over time.** Revisit what was available to each material judgment, what was believed, what happened, which assumptions held or failed, and whether the decision process was useful so future decisions and processes can improve.

A concise product shorthand for these jobs is:

> **Understand → Challenge → Apply Portfolio context → Decide under Portfolio Risk → Explain → Learn**

### Decision lifecycle

Polaris should support a closed decision loop rather than an analyze-and-forget workflow:

```text
Attention
  ↓
Decision Need
  ↓
reason / challenge
  ↓
Investment Recommendation
  ↓
Human Investment Decision
  ↓
Action Intent where applicable
  ↓
observe external reality
  ↓
Outcome
  ↓
Decision Evaluation
  ↓
Lessons
  └────────→ future Attention
```

Durable Decision Memory spans that lifecycle. Material Investment Decision history, provenance, temporal relationships, supported causal relationships, authority relationships, and unresolved ambiguity should remain semantically reconstructable through time independent of any one workflow execution, report, conversation, or storage representation.

Lowercase `decision record` may remain product shorthand for an assembled representation of that durable history. It is not a separate canonical business entity and is not a commitment to one storage object, document format, or API resource.

### Job boundaries

Polaris is not primarily hired to provide raw market data, draw charts, screen securities, execute brokerage Orders, manage brokerage accounts, build arbitrary AI workflows, act as an unrestricted financial chatbot, consume news, or generate reports. Any such capability must justify itself by serving the decision lifecycle, explanation, Decision Evaluation, or durable knowledge that improves future decisions.

## Product Identity

Polaris is an **AI-assisted portfolio decision system for sophisticated individual decision-makers and small investment teams**.

It combines investment intelligence, Portfolio context, Portfolio Risk reasoning, Durable Decision Memory, authority integrity, and Decision Evaluation into an opinionated decision lifecycle that supports—but does not replace—human investment judgment.

Polaris is delivered through a configurable and extensible product platform, but it is not a general-purpose AI, workflow, or financial-development platform. Its configurability exists to adapt the Polaris decision process to different Portfolios, Investment Strategies, Evidence sources, models, Investment Mandates, Policies, and operating contexts.

### Identity hierarchy

The product hierarchy is:

```text
Portfolio Decision System
        ↓ supported by
Investment Intelligence
        ↓ delivered through
Configurable Product Platform
```

The hierarchy is intentional. The decision system defines the product. Investment intelligence supplies the Evidence and reasoning capabilities necessary to support that system. Platform mechanisms make the product configurable, extensible, reliable, and integratable without becoming the product's primary identity.

### Opinionated lifecycle, configurable process

Polaris should be **opinionated about the investment decision lifecycle and flexible about the investment process configured within it**.

A trustworthy Investment Decision should have recognizable concepts such as Decision Need, Decision Context, attributable Evidence, Portfolio State, Investment View, meaningful challenge and Investment Uncertainty, Portfolio Risk, Decision Alternatives, Investment Recommendation, explicit Human Investment Decision, and later Outcome and Decision Evaluation where applicable.

Users may vary their Portfolios, Investment Strategies, indicators, Evidence providers, models, Investment Mandates, Policies, Investment Horizons, and other domain configuration. That flexibility must not turn Polaris into a blank canvas for arbitrary workflow construction.

### Ecosystem position

Polaris occupies the **decision layer between investment information systems and investment action systems**.

```text
SENSE                    DECIDE                    ACT
  │                         │                       │
Market data                 │                   Broker / trading platform
Economic data               │                   Order entry / execution
News / research ───────→  POLARIS  ───────→     Operational systems
Portfolio State             │                       │
External analytics          │                       │
                            ↓                       │
                 Human Investment Decision ─────────┘
                            │
                            └──── resulting Portfolio State returns to Polaris
```

Information systems primarily establish **what is happening or what is true within the facts they authoritatively provide**. Polaris determines **what those facts mean for this Portfolio, what deserves Attention, and what should be considered**. Trading, brokerage, and other operational systems carry out externally authorized activity and remain responsible for low-latency execution and account operations.

Polaris therefore complements rather than attempts to replace specialist systems such as:

* brokers, trading platforms, and execution systems;
* market-data and charting platforms;
* news and research services;
* portfolio accounting and books-and-records systems;
* specialist quantitative-research environments;
* general-purpose AI tools;
* communication and reporting destinations.

Polaris may consume information from, integrate with, or present decision state through these systems. Integration does not transfer their specialist product responsibilities to Polaris.

For the detailed rationale and category-by-category boundaries, see [`product-ecosystem.md`](./product-ecosystem.md).

### Execution continuity without execution authority

Polaris does not own execution, but it **does own continuity of the Investment Decision lifecycle across execution**.

When a Human Investment Decision establishes an externally observable implementation consequence, Polaris should preserve that consequence as one or more Action Intents and then observe what authoritative external systems report actually happened. Orders, partial fills, fills, protective or contingent Orders, modifications, cancellations, exits, and resulting Portfolio State may all become relevant external Evidence associated with the Investment Decision when the relationship is supported.

The conceptual chain is:

```text
Investment Recommendation
        ↓
Human Investment Decision
        ↓
Action Intent where applicable
        ↓
External execution system
        ↓
Authoritative external activity / Evidence
        ↓
Resulting Portfolio State
        ↓
Outcome
        ↓
Decision Evaluation
        ↓
Lessons
```

External execution and Portfolio systems remain authoritative for what operationally occurred. Polaris should reconcile their Evidence into Durable Decision Memory rather than ask the user to recreate information that an authoritative system can provide.

Where an association is sufficiently supported, reconciliation should occur automatically. Where multiple external activities could plausibly correspond to the same Action Intent and the distinction materially changes meaning, Polaris should preserve the ambiguity and ask for lightweight confirmation rather than silently guess. External trades or Position changes with no supported originating Polaris relationship should remain identifiable as externally initiated activity rather than being retroactively attributed to a Polaris Investment Recommendation or Human Investment Decision.

A Human Investment Decision may establish zero, one, or multiple Action Intents. Deferral and deliberate hold/no-action do not require synthetic Action Intents merely to duplicate the human judgment. One Action Intent may correspond to zero, one, or multiple external activities.

The user should therefore experience execution continuity primarily as **automatic observation and reconciliation**, not duplicate bookkeeping.

For the detailed rationale, see [`product-execution-continuity.md`](./product-execution-continuity.md).

### Decision-time, not trading-engine time

Polaris should be current at the speed required for **portfolio judgment**, not at the speed required for exchange execution.

Three conceptual clocks are useful:

```text
Market time       microseconds → milliseconds → seconds
                  quotes, matching, routing, execution, stops

Decision time     seconds → minutes
                  Attention, Investment Materiality, Portfolio impact,
                  Portfolio Risk, reassessment

Analytical time   minutes → hours → days
                  deep research, strategy analysis, Decision Evaluation
```

Polaris is not designed for the first category as a critical-path execution system. It owns the latter two, including Attention-driven reassessment when a fast market change makes existing Decision Context stale or materially changes a Portfolio-relevant investment question.

A major market shock should therefore cause Attention to identify affected Portfolios, Investment Theses, assumptions, Review Conditions, and Investment Decisions; refresh the Evidence required for the affected work; and determine whether unresolved decision work should continue or a renewed Decision Need exists. Existing brokerage and execution systems remain responsible for immediate market action.

### Freshness is part of trustworthiness

Evidence freshness must be appropriate to the investment use being supported rather than governed by one universal definition of "real time."

Polaris should preserve enough temporal metadata to determine whether critical market, Portfolio, economic, research, and other Evidence is current enough for the material judgment or consequential use. If required Evidence is too stale, Polaris should preserve that insufficiency and qualify or withhold the affected current judgment or use rather than silently presenting stale Decision Context as current.

A historical Investment Recommendation does not cease to exist merely because it is no longer currently supportable. Its historical meaning remains in Durable Decision Memory; current support requires current applicable Evidence and, when renewed, a new attributable judgment.

During rapidly changing conditions, a useful conceptual response may separate:

```text
Fast deterministic triage
        ↓
Material shock detected
Affected investment matters identified
Stale assumptions / breached conditions exposed
        ↓
Attention determines required decision work
        ↓
Reasoned reassessment
        ↓
Updated implications, Decision Alternatives,
Portfolio Risk, Investment Recommendation
        ↓
Human Investment Decision where required
```

This preserves responsiveness without pretending that AI reasoning or human portfolio judgment should operate at exchange-engine latency.

### Identity consequences

* **Decision system before platform.** Platform architecture and extensibility must serve the portfolio decision product rather than compete with it for identity.
* **Investment intelligence is a capability family, not the endpoint.** Research and analysis are valuable when they advance the decision lifecycle.
* **Domain configurability, not general-purpose programmability.** Polaris should expose investment-domain concepts where possible rather than requiring users to think in runtime primitives such as nodes, graphs, agents, prompts, or generic tools.
* **AI-assisted, not AI-governed.** AI is an important reasoning mechanism, but the product must remain free to prefer deterministic software wherever that creates a more trustworthy result.
* **Not the authoritative portfolio accounting or operational record.** Polaris needs trustworthy Portfolio State and portfolio reasoning without implicitly owning official accounting, brokerage operations, execution records, custody, settlement, or every operational aspect of portfolio management.
* **Decision layer, not execution layer.** Polaris determines what deserves consideration and forms Investment Recommendations; specialist systems remain responsible for market-speed execution and operational action.
* **External activity returns to the decision lifecycle.** External execution authority is compatible with a closed Polaris lifecycle only if resulting activity and Portfolio State can be observed and reconciled into Durable Decision Memory where the relationship is supported.
* **Operational reality outranks expected action.** Authoritative external execution and Portfolio State determine what actually happened; Polaris must not rewrite reality to match an Investment Recommendation or Action Intent.
* **Decision-time current.** Polaris must be current enough for the investment judgment at hand without adopting low-latency trading infrastructure as its product center.
* **Freshness is explicit.** Stale critical Evidence may make a current judgment or consequential use unsupported and must be surfaced or enforced accordingly.
* **The decision lifecycle is the organizing spine.** Product capabilities and existing subsystems should be evaluated by where they participate in or support that lifecycle.
* **Runtime qualities remain subordinate to user value.** Reliability, replayability, observability, provenance, and Governance may be enabled by a strong runtime, but "runtime-native" is not the fundamental product purpose.

## Core Experience

Polaris provides an **attentive, decision-centered experience**. The product is organized around investment matters that deserve Attention and deliberate judgment rather than around a catalog of features, while keeping analytical and product capabilities directly accessible when the user wants them.

Decision work may begin from a user request, a scheduled review, or Polaris observing materially relevant change. All three paths should enter the same Attention and Decision Need semantics rather than creating identity from the trigger itself.

If the same coherent unresolved investment choice is already represented by an Investment Decision, later triggers and Evidence contribute to that decision. Once substantive investment judgment has resolved the choice, a renewed Decision Need creates a new causally linked Investment Decision rather than reopening and rewriting the resolved one.

### Decision-first and attention-first

The primary experience should answer:

> **What deserves my Attention, and what unresolved investment choice are we trying to judge?**

Polaris should assemble relevant known Decision Context rather than make the user repeatedly reconstruct their investment world. It should connect current Portfolio State, Investment Strategy, Investment Mandate, applicable Policy and Formal Constraints, active Investment Theses, prior Investment Decisions and Investment Recommendations, unresolved questions, Invalidation Conditions, Catalysts, Review Conditions, historical knowledge, and new Evidence where relevant.

Features remain available as tools, but they do not define the main interaction model. The user should not have to manually traverse market data, research, Portfolio Risk, Investment Simulation, retrieval, reports, and other capabilities merely to assemble Decision Context.

### Attentive and proactive

Polaris should not require the user to identify every important question first.

It should continuously relate available change to the user's investment context and distinguish **Investment Relevance** from **Investment Materiality**. Irrelevant or immaterial changes may be absorbed quietly. Material change may cause Polaris to investigate, update Decision Context, or cause Attention to determine whether a Decision Need exists.

A useful initiative progression is:

```text
Observe
  ↓
Assess Investment Relevance
  ↓
Assess Investment Materiality
  ↓
Investigate when warranted
  ↓
Attention evaluates Decision Need
  ↓
Form or continue decision work
  ↓
Human Investment Decision at the applicable authority boundary
```

Polaris may take substantial initiative in Attention, analysis, challenge, preparation, and Investment Recommendation formation. That initiative does not itself grant authority to take consequential investment action.

### Prepared engagement, not alerts

When Polaris interrupts the user, it should preferably bring **prepared decision work rather than merely demand attention**.

A useful proactive interaction explains what changed, why it is Investment Relevant and material to the Portfolio or an existing Investment Thesis, what Polaris reassessed, whether the prior Investment View or current support changed, which Decision Alternatives and Portfolio Risks remain material, and what now requires human judgment.

The desired distinction is:

```text
Alert:
"Something happened. You may want to look at it."

Polaris:
"Something changed that materially affects an investment matter we care about.
I investigated it. Here is what changed, what it means, and what now
requires your judgment."
```

Polaris should remain calm and selective. Proactivity that surfaces every market event would recreate the cognitive overload the product exists to reduce.

### Shock response and stale Decision Context

A rapid market event does not turn Polaris into an execution system, but it can make existing Decision Context unsafe to reuse without reassessment.

For example, if a broad equity index suddenly falls 15%, immediate Order handling, stops, routing, fills, and broker controls remain the responsibility of the trading and execution stack. Polaris should instead:

1. recognize that the event may be Investment Relevant and material;
2. identify exposed Portfolios, active Investment Theses, Investment Assumptions, Portfolio Risks, Review Conditions, and Investment Recommendations;
3. preserve any previously formed Investment Recommendations as historical judgments while marking current support unresolved or insufficient where appropriate;
4. refresh the Evidence necessary for the affected investment matters;
5. have Attention determine whether unresolved work continues or a renewed Decision Need exists;
6. perform Portfolio-aware reassessment at decision speed;
7. proactively surface the work that now requires human attention.

The goal is not to compete with exchange-time systems. It is to ensure that the human receives a current, prepared Portfolio decision frame as conditions change.

### Decision-appropriate freshness

The experience should make Evidence recency and current support understandable where they matter.

An Investment Recommendation during a fast market shock may require market and Portfolio State that is seconds or minutes old, while a long-horizon macro judgment may remain supportable with substantially slower-moving Evidence. Polaris should judge freshness relative to the intended investment use.

If critical Portfolio State, market state, or another required source is stale beyond the applicable Freshness Requirement, Polaris should be able to say that it cannot presently support a current Investment Recommendation rather than disguising the insufficiency in a footnote.

### Progressive disclosure and interrogation

The default presentation should be concise enough for a decision-maker to understand the current judgment quickly while allowing progressive inspection of the reasoning and Evidence.

A natural depth progression is:

```text
Current Investment View / Recommendation
Preferred economic disposition
Why
Material Portfolio Risks
What could change the view
        ↓
Reasoning
        ↓
Decision Alternatives and challenge
        ↓
Portfolio Risk analysis
        ↓
Evidence
        ↓
Sources / provenance
        ↓
Underlying analytical detail
```

Trustworthiness does not require dumping every internal detail into the default view. It requires that meaningful reasoning, Evidence, Investment Uncertainty, Investment Assumptions, and provenance remain available and navigable.

### Investment Recommendation as a reviewable decision representation

An Investment Recommendation should be more than a directional answer or confidence score. It should be able to communicate, as applicable:

* preferred economic disposition;
* why that disposition is preferred;
* Material Claims and Evidence;
* Projected Portfolio Consequences;
* Portfolio Risk;
* applicable Policy or Formal Constraint effects;
* meaningful Decision Alternatives;
* Proposed Actions or implementation preferences where useful;
* strongest counterarguments or Conflicting Evidence;
* material Investment Uncertainty;
* Invalidation Conditions;
* Investment Horizon or Review Conditions.

Polaris may present a human-reviewable trade setup when useful, but suggested implementation details do not become Orders, Action Intents, or execution authority merely because they appear in an Investment Recommendation.

Challenge should be visible in investment terms rather than as agent or model theater. The user should see meaningful disagreement, alternative Investment Hypotheses, Investment Uncertainty, and Invalidation Conditions without needing to understand which internal agent, prompt, model, or workflow produced them.

Portfolio Risk belongs **inside** recommendation formation. It should be possible to understand how Portfolio State and Portfolio Risk changed an otherwise plausible disposition rather than seeing risk as a detached approval stamp.

### Explicit Human Investment Decision boundary

The Investment Recommendation and Human Investment Decision are distinct facts.

The human may select, modify, reject, defer, or otherwise dispose of the Portfolio-relevant investment choice and may optionally record rationale. Polaris should preserve that judgment separately from its own Investment Recommendation even when the economic content is identical.

Human Investment Decision is also distinct from Approval, Mandate Exception, Residual-Risk Acceptance, and other power-specific authority acts. The same human may perform several such acts when authorized, but one must not be inferred from another.

That distinction supports later Decision Evaluation of both Polaris judgment and human judgment.

### Decisions become Durable Decision Memory

Material Investment Decision history should naturally become Durable Decision Memory rather than requiring the user to remember to save a report or transcript.

Durable Decision Memory should preserve or connect the meaningful lifecycle state before, during, and after the Investment Decision. When the Human Investment Decision establishes an external Action Intent, observed external Evidence and resulting Portfolio State should join that same historical relationship automatically where practical rather than requiring duplicate user bookkeeping.

Reports, CLI output, conversational responses, APIs, MCP, and future interactive interfaces are interaction or presentation surfaces over shared decision semantics rather than separate product identities.

Past Investment Decisions should also help Polaris determine what future changes matter. Investment Theses, Investment Assumptions, Portfolio Risks, Invalidation Conditions, deferred decisions, Catalysts, Review Conditions, and Lessons can make Durable Decision Memory operational by changing future Attention and reasoning.

### The experience continues after substantive judgment

Polaris should follow Investment Decisions through applicable Action Intent continuity, Outcome, Decision Evaluation, and Lessons rather than stopping when an Investment Recommendation is produced or a Human Investment Decision is recorded.

Substantive investment judgment resolution is a milestone within the Investment Decision lifecycle, not necessarily the end of all continuity or evaluation. Later Outcome and Decision Evaluation remain linked to the historical decision without reopening its resolved investment judgment.

The product should reconnect later Evidence and Outcomes to earlier Investment Decisions when they become material for Decision Evaluation or future Attention. A renewed Decision Need after prior resolution creates a new causally linked Investment Decision rather than mutating the old one.

### Core experience characteristics

* **Decision-first, not feature-first.** Features remain accessible, but the main experience is organized around Investment Decisions and Attention.
* **Attentive, not merely responsive.** Polaris can determine when Investment-Relevant, material change warrants a Decision Need.
* **Context-aware, not repeatedly re-prompted.** Known Portfolio, Investment Strategy, Investment Mandate, Policy, history, and Decision Context should be reused when relevant.
* **Selective, not noisy.** Investment Materiality is evaluated relative to the Portfolio and intended use; immaterial change can be absorbed quietly.
* **Prepared, not alert-driven.** When possible, Polaris investigates before interrupting and brings implications rather than assigning analysis back to the user.
* **Decision-time current, not exchange-time driven.** Polaris should respond fast enough for Portfolio judgment while leaving low-latency execution to specialist systems.
* **Freshness-aware.** Evidence recency and staleness are part of current judgment trustworthiness, not incidental metadata.
* **Execution-aware, not execution-authoritative.** Polaris should observe and reconcile external activity into Durable Decision Memory without becoming the system that places or controls Orders.
* **Concise first, deep on demand.** The current Investment View or Recommendation is quickly understandable and progressively interrogable.
* **Challenge without implementation theater.** Meaningful alternatives, Investment Uncertainty, and Invalidation Conditions are exposed in investment terms.
* **Portfolio Risk inside recommendation formation.** Portfolio Risk shapes the preferred disposition rather than merely approving or rejecting it afterward.
* **Investment Recommendation and Human Investment Decision remain distinct.** Polaris can recommend; attributable human investment judgment remains separately preserved.
* **Persistent.** Material Investment Decision history becomes Durable Decision Memory and remains available for future Attention, Decision Evaluation, and learning.
* **Calm.** Polaris should not manufacture urgency or equate activity with intelligence; "no action warranted" is a valid and useful judgment.
* **Interface-independent.** User questions, scheduled reviews, Polaris-initiated Attention, reports, CLI, API, MCP, and future interactive surfaces should converge on the same decision semantics.

A governing experience principle is:

> **Polaris should reduce the cognitive work required to assemble and evaluate an Investment Decision without hiding the Evidence, Investment Uncertainty, tradeoffs, freshness, external reality, Portfolio Risk, or authority distinctions required to make it trustworthy.**

## Authority Model

Polaris uses a **separation-of-powers authority model**. Capability does not imply authority, and no single component should own external facts, deterministic rules, Polaris investment judgment, consequential human authority, and market-facing execution at the same time.

The decision chain keeps these responsibilities distinct:

```text
Authoritative fact sources
Establish the external facts they own.
        ↓
Deterministic rule evaluation
Policy / Formal Constraints / freshness and readiness.
        ↓
Polaris investment judgment
Investment Views, Portfolio Risk Assessments,
Investment Recommendations.
        ↓
Investment Authority Regime
Determines who may form Human Investment Decisions,
grant Approval, authorize Mandate Exceptions,
or accept Governed Residual Risk.
        ↓
External execution authority
External systems establish Orders, fills,
and other operational facts.
        ↓
Evidence returns
Observed activity and resulting Portfolio State
re-enter the decision lifecycle.
```

### Authority boundaries

* **Authoritative sources own the external facts within their responsibility.** Polaris may interpret and reconcile their Evidence but must not rewrite operational reality to match an Investment Recommendation, Action Intent, or preferred narrative.
* **Deterministic software evaluates explicit rules.** Policy, Formal Constraints, Freshness Requirements, readiness conditions, and invariants should be evaluated deterministically where practical. Their results are not automatically Approval or Human Investment Decision.
* **Polaris owns its investment judgment, not authority over capital.** Polaris may autonomously observe, investigate, challenge, compare Decision Alternatives, form Portfolio Risk Assessments and Investment Recommendations, explain, and cause Attention to evaluate matters that deserve judgment.
* **The Investment Authority Regime owns power allocation.** Human Investment Decision, Approval, Authority Denial, Mandate Exception, Residual-Risk Acceptance, and execution authority are power-specific and must not be inferred from one another.
* **External operational systems own market-facing execution facts.** Orders, fills, protective Orders, exits, and other execution responsibilities remain outside Polaris even though their Evidence returns to Durable Decision Memory.

Human authority does not require human initiation. Polaris may initiate substantial analytical work on its own; the authority boundary applies when a particular consequential power must be exercised.

### Deterministic boundaries and analytical guidance remain distinct

Older product language grouped many things under `hard constraints` and `soft constraints`. The canonical model is more specific:

* an **Investment Mandate Formal Constraint** is an authoritative machine-evaluable Mandate restriction;
* a **Policy** deterministically governs whether a platform operation or boundary crossing may happen;
* a **Freshness Requirement** or readiness condition governs whether Evidence is fit for a particular use;
* an **Investment Principle** or other analytical consideration guides judgment without becoming deterministic Mandate compliance.

AI may reason about these conditions and may recommend that humans revisit them where appropriate. It may not silently change their authoritative meaning, fabricate satisfaction, or bypass a required authority act.

Missing Evidence, stale required context, Formal Constraint violation, Policy denial, unresolved authority requirements, or sufficiently material Investment Uncertainty may each affect whether a current Investment Recommendation or consequential use is supportable. These are distinct reasons and should remain distinguishable.

### Internal analytical autonomy

Polaris may autonomously perform governed internal informational, analytical, and decision-state operations when no separately required consequential authority power is being exercised. Examples include refreshing Evidence, detecting staleness, recalculating analytical measures, forming a Portfolio Risk Assessment, causing Attention to evaluate a possible Decision Need, initiating Decision Evaluation, reconciling unambiguous external activity to an Action Intent, and surfacing material change.

When ambiguity materially changes the meaning of a transition, Polaris should preserve the ambiguity or request targeted confirmation rather than silently guess.

### Preserve the material authority path

Every materially required authority act and deterministic result across the lifecycle should remain durably reconstructable **whether the participants agree or disagree**.

Polaris should preserve not only conflicts, blocks, overrides, failures, and exceptions, but also materially relevant positive facts such as:

* Evidence accepted as sufficient and current enough for the use;
* Policy evaluated and allowed;
* Formal Constraints evaluated and satisfied;
* Approval granted where required;
* Mandate Exception authorized where required;
* Governed Residual Risk accepted where required;
* Human Investment Decision formed;
* external activity reconciled where supportable;
* faithful or divergent implementation;
* resulting Outcome.

A terminal result must not erase the path that produced it. A Policy allow is different from Approval; a satisfied Formal Constraint is different from a Mandate Exception; a Human Investment Decision is different from all of them. Silence is not evidence that a materially required evaluation or authority act occurred.

Lowercase `authority trace` may remain product shorthand for an assembled representation of this material authority and rule history. It is not a separate canonical authority power or a commitment to one storage entity.

The authority history should be **preserved and inspectable**, while the Core Experience remains concise-first and progressively disclosed. Material authority effects should surface prominently in the normal decision experience; fuller detail should remain available on demand.

### Authority history complements Evidence provenance

Evidence provenance answers what Evidence existed, where it came from, when it was observed, and whether it was available to a particular material judgment.

Authority history answers which power applied, who possessed it under the Investment Authority Regime, what authority act occurred, and which Policy or Formal Constraint results materially affected the consequential use.

Together they create trustworthy decision provenance without laundering one kind of fact into another.

This is a product-level relationship, not a commitment to a particular event schema, database representation, or current evidence-model implementation.

### Authority consequences

* **Capability does not imply authority.**
* **Operational reality outranks expectation.**
* **AI may initiate analysis without acquiring capital-action authority.**
* **Policy, Formal Constraints, readiness, Approval, Human Investment Decision, Mandate Exception, Residual-Risk Acceptance, and execution authority remain distinct.**
* **Ambiguity that materially changes meaning remains unresolved or is escalated rather than guessed away.**
* **Polaris may withhold an Investment Recommendation when the available Evidence or analytical judgment cannot support it.**
* **Material positive authority acts and deterministic results are preserved when required, not inferred from silence.**
* **The terminal Outcome never substitutes for the authority path that produced it.**
* **Authority history, implementation fidelity, and Outcomes can become Evidence in later Decision Evaluation while retaining their original semantic roles.**

For the detailed rationale, see [`product-authority-model.md`](./product-authority-model.md).

## Scope Boundaries

Polaris owns the **portfolio decision lifecycle** and the trust, Decision Context, provenance, Attention, reasoning, Governance, continuity, Decision Evaluation, and learning responsibilities necessary to make that lifecycle coherent. It does not need to own every system or capability that supplies Evidence to, supports, or receives action from that lifecycle.

The governing rules are:

> **Polaris owns decisions, not everything decisions touch.**

> **Dependency does not imply ownership.**

> **Feature presence does not imply product-category ownership.**

### Three scope rings

Polaris scope has three responsibility rings:

1. **Polaris-owned responsibilities.** The decision lifecycle itself: Attention and Investment Materiality, Decision Context, Evidence use and provenance, Investment View formation and challenge, Projected Portfolio Consequences, Portfolio Risk reasoning, Governance and authority integrity, Investment Recommendation, Human Investment Decision continuity, external-activity reconciliation, Outcome, Decision Evaluation, and Lessons.
2. **Supporting capabilities.** Capabilities such as charts, research tools, news ingestion, screening, Investment Simulation, Backtest, reports, conversation, dashboards, collaboration, and integrations may exist inside Polaris when they materially improve decision quality, reduce friction, support explanation, preserve continuity, or improve Decision Evaluation.
3. **External specialist responsibilities.** Responsibilities such as exchange-speed execution, brokerage operations, official books and records, portfolio accounting, custody, settlement, tax accounting, comprehensive market-data vending, generalized quantitative development, general-purpose AI, and broad regulatory operations remain outside Polaris's defining product responsibility unless the Product Definition is explicitly reconsidered.

Supporting status does not imply low quality. A supporting capability may be sophisticated and differentiated when excellence materially improves the decision experience. Its evolution must remain accountable to the portfolio decision system rather than developing an independent product mandate.

### Integrate rather than duplicate ownership

Where a specialist external system has factual or operational authority, Polaris should normally integrate with it and preserve that authority rather than silently treat an internal copy or expectation as an equal authoritative fact.

Polaris may cache, normalize, derive, preserve, reconcile, and reason over external state for decision purposes. Where another system owns the underlying fact, that source's authority remains explicit.

This applies to market data, Portfolio State, execution Evidence, accounting facts, and other externally authoritative information.

### Decision-oriented scope examples

* **Market data:** decision-relevant acquisition, attribution, freshness, sufficiency, and interpretation are in scope; comprehensive exchange-speed market-data vending is not a defining responsibility.
* **Portfolio State:** decision-oriented Positions, Exposure, concentration, Portfolio Risk context, and resulting state are in scope; official portfolio accounting and books-and-records ownership are not implied.
* **Research:** gathering, attributing, synthesizing, challenging, and connecting research to Investment Decisions are in scope; comprehensive information possession is not the objective.
* **Investment Simulation and Backtest:** in scope when they form, challenge, evaluate, or improve Investment Decisions or investment methods; generalized quantitative-programming infrastructure is not itself a Polaris job.
* **Portfolio Risk and deterministic boundaries:** Portfolio Risk reasoning, Investment Mandate interpretation, Formal Constraint evaluation, and applicable Policy are core; exchange-time margin, buying-power, and execution controls remain with specialist operational systems.
* **Reporting and distribution:** reports, PDFs, email, dashboards, CLI, API, and MCP may present shared decision state; they do not become independent product centers.
* **Governance:** decision Governance is core; broad regulatory operations require separate product justification.
* **Collaboration:** small-team decision collaboration is in scope; enterprise organization machinery is not presently a design center.
* **Opportunity discovery:** may support an attentive decision system; generalized screening is not the product center.
* **Conversation:** an important decision interface, not a general financial chatbot.
* **Workflow infrastructure:** reusable internal infrastructure is compatible with Polaris; arbitrary workflow construction is not a primary user job.

### Scope decision test

Before a major capability becomes Polaris scope, ask:

1. Does it materially support **Understand, Challenge, Apply Portfolio context, Decide under Portfolio Risk, Explain, or Learn**?
2. Does Polaris need to own the responsibility to fulfill its decision contract?
3. Can a specialist system own the underlying responsibility while Polaris consumes, reconciles, interprets, or presents the necessary Evidence or state?
4. Would a narrower Polaris-native capability materially improve decision quality or reduce user friction?
5. Would owning the full category create a new primary user job or materially change Polaris's authority model, latency contract, operational responsibility, regulatory burden, or product identity?

If the final answer is yes, there is a strong presumption that the broader category is outside scope until the Product Definition is explicitly reconsidered.

### Scope consequences

* **Core responsibilities must close the decision lifecycle.**
* **Supporting features justify themselves through decision value.**
* **A supporting capability may be excellent without becoming a new product center.**
* **Authoritative specialist systems should remain authoritative for the responsibilities they own.**
* **Polaris should integrate and reconcile rather than casually create competing factual authority.**
* **Expansion that creates a new primary job, authority domain, latency regime, regulatory burden, or operational contract is presumed outside scope until explicitly reconsidered.**

For the detailed rationale, see [`product-scope-boundaries.md`](./product-scope-boundaries.md).

## Differentiation

Polaris differentiates by treating **Investment Decisions as durable, first-class lifecycles** rather than disposable analyses, recommendations, conversations, reports, alerts, workflows, or trades.

An Investment Decision has durable identity for one coherent unresolved Portfolio-relevant investment choice. Durable Decision Memory keeps the material Evidence, reasoning, challenge, Decision Context, Portfolio Risk, authority relationships, Human Investment Decision, Action Intent where applicable, external activity, Outcome, Decision Evaluation, and Lessons connected through time. Interfaces, models, reports, workflows, and analytical techniques are replaceable means used to form, inspect, present, or evaluate that decision history.

### Three central differentiators

1. **Durable decisions.** Investment Decision identity and Durable Decision Memory preserve a closed lifecycle rather than ending at analysis or Investment Recommendation. Prior decisions remain historical context for future Attention, Decision Evaluation, and learning without being silently reopened or rewritten.
2. **Trust by architecture.** Polaris creates trust through attributable Evidence, decision-appropriate freshness, deterministic rule results, analytical challenge, power-specific authority provenance, explicit Human Investment Decision, and authoritative external operational truth rather than model confidence alone.
3. **Attentive intelligence.** Durable Portfolio and decision context allows Polaris to determine which new information is Investment Relevant and material to an active Investment Thesis, Portfolio Risk, Investment Assumption, Review Condition, unresolved decision, or prior judgment; investigate relevant change proactively; and remain quiet when nothing material changed.

### Portfolio decision quality over generic intelligence

Polaris does not stop at an investment opinion. Investment intelligence must be translated into Projected Portfolio Consequences for the actual Portfolio, shaped by Portfolio Risk and applicable deterministic boundaries, challenged before Investment Recommendation, and evaluated afterward.

The intended progression is:

```text
Investment-Relevant Evidence
        ↓
Investment View + challenge
        ↓
Projected Portfolio Consequences
        ↓
Portfolio Risk + Policy / Formal Constraints
        ↓
Investment Recommendation
        ↓
Human Investment Decision
        ↓
Authoritative external result where applicable
        ↓
Outcome
        ↓
Decision Evaluation + Lessons
```

This makes the Investment Decision—not a security opinion, chat answer, Investment Signal, or model output—the final unit of product value.

### Human-governed initiative

Polaris combines substantial analytical autonomy with constrained capital authority. It may notice, investigate, challenge, form Investment Views and Portfolio Risk Assessments, recommend, and proactively bring prepared work to the human without waiting for every prompt. Consequential investment judgment remains attributable to the human under the applicable Investment Authority Regime, and external systems remain responsible for execution.

The differentiating interaction is therefore neither passive decision support nor autonomous trading:

> **Maximum useful analytical initiative without surrendering consequential human investment judgment.**

### Decision provenance and historical integrity

Evidence provenance and power-specific authority history should make the material decision path reconstructable relative to what was available to each judgment at the time. Decision Evaluation should distinguish reasoning quality, Policy and Formal Constraint effects, human judgment, implementation fidelity, and Outcome rather than treating P&L alone as proof of decision quality.

Polaris should not silently use later information as though it were available to an earlier judgment. Likewise, stale current context may make a prior Investment Recommendation no longer currently supportable without erasing that historical judgment.

### Differentiation is cumulative, not feature-based

No single supporting feature defines Polaris. Agents, models, RAG, replay, MCP, telemetry, orchestration, databases, reports, and integrations may all improve the product, but they are replaceable implementation means.

The durable differentiation emerges from the combination:

```text
Attentive
    +
Portfolio-aware
    +
Decision-centered
    +
Challenge-oriented
    +
Risk-shaped
    +
Evidence-provenanced
    +
Authority-integrity-aware
    +
Human-governed
    +
Execution-aware
    +
Historically faithful
    +
Outcome-evaluated
    +
Learning
```

Reproducing the complete behavior would require an adjacent product to adopt the same underlying premise: **the portfolio decision lifecycle is the product**.

### Differentiation consequences

* **Investment Decision identity is durable; resolved judgments are not silently reopened or rewritten.**
* **Durable Decision Memory keeps material lifecycle meaning reconstructable across representations and technologies.**
* **Closed loop beats analyze-and-forget.**
* **Trust comes from provenance and separation of powers, not model confidence alone.**
* **Portfolio consequence matters more than generic investment opinion.**
* **Challenge is structural, not optional implementation theater.**
* **Portfolio Risk shapes Investment Recommendations.**
* **Human authority coexists with strong AI initiative.**
* **External execution remains connected without becoming Polaris-controlled.**
* **Learning evaluates reasoning, authority, implementation, and Outcome rather than P&L alone.**
* **Historical evaluation respects Judgment-Time Availability.**
* **Attention quality matters more than notification quantity.**
* **The coherent system is the differentiation; implementation features are replaceable means.**

For the detailed rationale and adjacent-product comparison, see [`product-differentiation.md`](./product-differentiation.md).

## Core Capabilities

Polaris requires **nine core product capabilities** that together close the portfolio decision lifecycle. These capabilities describe what Polaris must be able to do, not how those abilities are implemented.

The core capability spine is:

1. **Attention & Decision Initiation.** Determine what deserves Attention, when a Decision Need exists, when an unresolved Investment Decision should continue, and when a resolved matter warrants a new causally linked Investment Decision.
2. **Decision Context & Evidence.** Assemble the decision-specific Portfolio context and attributable Evidence necessary for responsible reasoning, including provenance, Judgment-Time Availability, freshness, sufficiency, conflicts, and historical integrity where material.
3. **Investment Reasoning & Challenge.** Develop an Investment View, compare Investment Hypotheses and Decision Alternatives, expose Investment Uncertainty and Investment Assumptions, seek meaningful Conflicting Evidence, and seriously test why the leading view may be wrong.
4. **Portfolio Consequence & Risk.** Translate an Investment View into Projected Portfolio Consequences and Portfolio Risk for the actual Portfolio under the applicable Investment Mandate and Policy.
5. **Recommendation Formation.** Compare reasonable Decision Alternatives under uncertainty and form an explainable Investment Recommendation—or deliberately withhold one when available Evidence or judgment cannot support a responsible preference.
6. **Authority & Human Decision.** Preserve Admissibility, applicable power-specific authority acts, deterministic rule results, and Human Investment Decision without conflating them with the Investment Recommendation or one another.
7. **Action Continuity & Reconciliation.** Observe, associate, reconcile, and track authoritative external activity against Action Intents where they exist without acquiring execution authority.
8. **Durable Decision Memory.** Preserve material Investment Decision history faithfully through time, distinguish what was available to earlier judgments from what is known now, and use prior decision state as active context for future Attention and reasoning.
9. **Outcome Evaluation & Learning.** Form Decision Evaluations using historically faithful decision and Outcome state, distinguish process quality from Outcome alone, and preserve Lessons that can improve future decisions.

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
            └────────→ future Attention

Durable Decision Memory spans the entire lifecycle.
```

### Capability model, not implementation map

AI models, agents, workflows, retrieval systems, replay, persistence technologies, APIs, interfaces, reports, and other technical mechanisms may implement, expose, strengthen, or observe one or more core capabilities. They are not themselves the durable capability model.

Likewise, Evidence domains such as market, macroeconomic, news, sentiment, fundamental, and technical analysis are important inputs to decision-oriented capabilities rather than independent top-level product centers at this level.

The capability model should remain stable even if the implementation underneath it changes substantially.

### Supporting platform capabilities

The nine core capabilities are enabled by important supporting platform capabilities:

* **Integration & Connectivity** — connect to decision-relevant Evidence, Portfolio State, execution systems, external tools, and distribution destinations.
* **Interaction & Presentation** — expose shared decision semantics through conversation, interactive UI, reports, CLI, API, MCP, email, messaging, and future surfaces without creating competing decision semantics.
* **Configuration & Extensibility** — adapt Polaris to different Portfolios, Investment Strategies, asset universes, Evidence providers, models, Investment Mandates, Policies, Investment Horizons, and operating preferences without turning the product into an arbitrary workflow platform.
* **Runtime Reliability & Observability** — execute decision work reliably, expose failures, preserve relevant state and provenance, support recovery where appropriate, and make lifecycle execution inspectable.
* **Security & Operations** — protect credentials, Portfolio information, integrations, configuration, access boundaries, and operational trust assumptions appropriate to the product's maturity.

These supporting capabilities may become sophisticated. Their purpose remains to enable the portfolio decision system rather than compete with it for product identity.

### Capability maturity evolves across releases

A capability being core does not require every release to implement its ultimate depth.

Core capability maturity may increase across releases while the capability model remains stable. Roadmap work should therefore describe which end-to-end product abilities become **usable, trustworthy, broader, or more mature** in each release rather than organizing releases around implementation feature accumulation.

Useful product-level questions include:

* Can Polaris identify why something materially deserves Attention and whether a Decision Need exists?
* Can it show which Evidence informed a material judgment and whether that Evidence was sufficiently current and available at the time?
* Can the user inspect the strongest meaningful challenge to the preferred Investment View?
* Can Polaris explain how Portfolio State and Portfolio Risk changed Projected Portfolio Consequences or the Investment Recommendation?
* Can it explain the preferred disposition, meaningful Decision Alternatives, and conditions that would change the view?
* Can the material authority path be reconstructed without conflating Policy, Formal Constraints, Approval, Human Investment Decision, or other power-specific acts?
* Can Polaris determine whether an Action Intent was reflected in authoritative external activity when one existed?
* Can it reconstruct what was available to the material judgments when they occurred?
* Can it form Decision Evaluations separately from the observed Outcome and preserve useful Lessons?

These questions should become more useful than asking whether a particular class, service, agent, workflow, or interface exists.

### Core capability consequences

* **The nine core capabilities form the durable product capability spine.**
* **Durable Decision Memory spans and supports the entire lifecycle.**
* **AI and deterministic software are methods used across capabilities, not separate top-level user capabilities.**
* **Portfolio Risk remains integrated with Projected Portfolio Consequence and Investment Recommendation formation rather than becoming a detached approval stage.**
* **Policy, Formal Constraints, Admissibility, Approval, Human Investment Decision, and other authority facts remain semantically distinct.**
* **Execution observation and reconciliation are core even though execution authority remains external.**
* **Decision Evaluation distinguishes decision-process quality from Outcome alone.**
* **Supporting platform capabilities enable the core system without becoming independent product centers.**
* **Capability maturity may deepen across releases without redefining the capability model.**
* **Roadmap milestones should be expressed in end-to-end capability maturity and product guarantees rather than feature accumulation.**

For the detailed rationale, see [`product-core-capabilities.md`](./product-core-capabilities.md).

## Product Principles

The Product Principles are the durable decision rules used when more than one plausible product, architecture, roadmap, or experience choice could satisfy the rest of the Product Definition.

The umbrella rule is:

> **Every Polaris product, architecture, and roadmap decision should strengthen the quality, trustworthiness, continuity, or learning value of the portfolio decision lifecycle—or have a clear supporting reason for existing.**

The twelve principles are:

1. **Decisions before features.** Optimize the portfolio decision lifecycle before individual feature sophistication. When feature sophistication and decision quality compete, decision quality wins.
2. **Trust by structure, not confidence.** Build trust through provenance, freshness, challenge, deterministic rule results, power-specific authority, human judgment, operational truth, and inspectability rather than model confidence alone.
3. **Preserve truth before convenience.** Simplify presentation without erasing meaningful Evidence, authority, Investment Decision, Action Intent, external activity, or historical distinctions.
4. **AI initiative without AI sovereignty.** Automate observation, investigation, reasoning, challenge, preparation, and Investment Recommendation formation aggressively while keeping consequential investment and material governance authority bounded by the Investment Authority Regime.
5. **Portfolio Risk shapes the decision.** Incorporate Portfolio Risk into Projected Portfolio Consequences and Investment Recommendation formation while preserving deterministic Policy and Formal Constraint results as distinct boundaries.
6. **Be attentive, not noisy.** Optimize for Investment Materiality and prepared intervention rather than alerts, activity, novelty, or information volume.
7. **Current enough for the decision.** Judge Evidence freshness against the investment use being supported and preserve insufficiency when required Evidence is stale rather than lowering the standard or rewriting historical judgments.
8. **Durable Decision Memory should change future behavior.** Preserve material decision history so it actively improves future Attention, reasoning, Decision Evaluation, and learning rather than becoming a passive archive.
9. **Reality wins.** Preserve authoritative external operational truth when it conflicts with expectation, Investment Recommendation, Action Intent, or expected Portfolio State.
10. **Integrate before absorbing.** Prefer specialist-system integration over expanding Polaris into adjacent product responsibilities without explicit justification.
11. **Opinionated domain, flexible process.** Make investment processes configurable while keeping the portfolio decision lifecycle and its domain concepts opinionated.
12. **Learn from process, not Outcome alone.** Evaluate judgments using what was available at the time and distinguish reasoning, authority, implementation, and Outcome when learning from results.

### Product principle consequences

* **Product progress is measured by stronger decision capability, not feature count.**
* **Trustworthy structure matters more than persuasive model confidence.**
* **User simplicity must not erase meaningful truth.**
* **Analytical autonomy should be broad while consequential authority remains bounded.**
* **Portfolio Risk is part of Investment Recommendation formation.**
* **Human Attention is a scarce resource to be spent selectively.**
* **Freshness Requirements follow the intended investment use.**
* **Durable Decision Memory must influence future behavior.**
* **Authoritative operational reality outranks expected state.**
* **External specialist responsibilities should normally remain external.**
* **Configurability should stay grounded in investment-domain concepts.**
* **Decision Evaluation should distinguish decision-process quality from Outcome.**

These principles are intended to reject or refine plausible choices, not merely describe desirable values. They should be used as explicit tests during product planning, architecture work, roadmap construction, and later doctrine revisions.

For the detailed rationale, rejection tests, and examples, see [`product-principles.md`](./product-principles.md).

## Current product framing

The product framing is:

> **Polaris is an attentive, AI-assisted portfolio decision system for sophisticated individual decision-makers and small investment teams, occupying the decision layer between investment information systems and investment action systems and delivered through a configurable portfolio intelligence and decision-support platform.**

It helps them turn fragmented market, Portfolio, research, Portfolio Risk, and model Evidence into a systematic, explainable, risk-aware, repeatable decision process; proactively surfaces Investment-Relevant material changes that deserve Attention; treats Investment Decisions as durable lifecycles rather than disposable outputs; preserves Durable Decision Memory and Judgment-Time Availability; creates trust through Evidence provenance, deterministic rule integrity, power-specific authority history, and external operational truth; remains current at the speed required for Portfolio judgment; separates Polaris investment judgment from Human Investment Decision and other authority acts; observes authoritative external activity so decisions remain connected to what actually happened; integrates with specialist systems without assuming their product responsibilities; and preserves the lifecycle for later Decision Evaluation and learning.

This Product Definition is now **defined**. Future changes should be explicit doctrine revisions rather than unresolved product-discovery work.
