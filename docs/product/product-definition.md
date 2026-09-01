# Polaris Product Definition

**Status:** In progress  
**Purpose:** Define the durable product doctrine that should guide Polaris capability, roadmap, and implementation decisions.

This document describes **what Polaris is and who it is for**. It intentionally avoids implementation technologies and detailed architecture. The fuller reasoning behind these decisions is preserved in [`product-rationale.md`](./product-rationale.md) and in focused companion records linked from the relevant sections.

## Purpose

Polaris exists to help humans make **better, more trustworthy portfolio and investment decisions**.

It turns fragmented market, portfolio, research, risk, and model evidence into a repeatable decision process that produces explainable recommendations for human decision-makers. It should preserve what the platform knew, what it concluded, why it concluded it, what uncertainty or disagreement existed, and enough durable evidence for the decision to be inspected, challenged, replayed, and evaluated later.

Polaris is not valuable merely because it performs financial analysis or automates AI workflows. Analysis, agents, workflows, retrieval, replay, reporting, governance, and evaluation are supporting mechanisms. Their product value comes from improving the quality, trustworthiness, explainability, repeatability, or evaluation of investment decisions.

Polaris uses AI where AI adds reasoning and synthesis value, deterministic software where rules and guarantees matter, and human authority where consequential investment judgment should remain human.

### Purpose consequences

* **Decisions are the product center.** Analysis must ultimately support a decision, explanation, evaluation, or durable knowledge that improves future decisions.
* **Trustworthiness is a product concern.** A recommendation should be explainable, inspectable, reproducible where appropriate, challengeable, and evaluable after the fact.
* **AI is a participant, not the governing authority.** The surrounding system should constrain, preserve, and expose AI reasoning rather than simply delegate the whole decision to a model.
* **Portfolio context matters.** Polaris should reason about opportunities in the context of the portfolio, risk, market conditions, strategy, time horizon, and competing alternatives rather than acting as a collection of isolated market signals.
* **Human decision authority remains central.** Polaris supports consequential investment decisions; it does not define itself through autonomous capital execution.

## Users

Polaris primarily serves **sophisticated individual portfolio decision-makers and small investment teams practicing discretionary, process-driven portfolio management**.

The primary user already has responsibility for investment decisions and enough financial literacy to understand risk, exposure, drawdown, uncertainty, time horizon, and portfolio construction. Polaris is intended to improve an existing or deliberately developing investment process rather than replace basic financial education or human judgment.

The common characteristic is **decision responsibility**, not a particular title. A user may be an investor, trader, portfolio manager, analyst, fund manager, or another role, provided they are responsible for turning evidence into portfolio decisions.

Polaris should support an intentional progression from one sophisticated operator wearing several roles to a small team separating responsibilities such as portfolio management, research, risk review, and platform operation. The product model should not require those roles to be separate in order to be useful.

### User and operator distinction

The person receiving investment value from Polaris and the person operating the software are not necessarily the same role.

Early Polaris deployments may require a technically capable operator. That is a current maturity constraint, not a reason to define the product as developer software. The long-term product user is the portfolio decision-maker or investment team; installation, integration, and platform operation are supporting concerns.

### Primary-user characteristics

The intended user:

* makes recurring discretionary portfolio or investment decisions;
* values a repeatable investment process over ad hoc model answers;
* wants evidence, uncertainty, risk, and competing interpretations incorporated into recommendations;
* expects recommendations to be explainable and reviewable;
* wants past decisions and reasoning to remain inspectable and useful for evaluation;
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

Polaris is hired to help a portfolio decision-maker **turn fragmented and uncertain evidence into a reasoned, risk-aware portfolio decision; understand and defend that decision; preserve what was known and why the recommendation was made; and evaluate the decision process afterward so future decisions can improve**.

The primary job is not to generate activity. A valid result may be to act, wait, reduce, add, rebalance, hedge where appropriate, or deliberately do nothing. The product is responsible for improving decision quality rather than maximizing the number of recommendations or trades.

### Core jobs

The Polaris decision cycle has six durable user jobs:

1. **Understand the current decision context.** Turn fragmented market, macro, news, sentiment, technical, portfolio, historical, and other relevant evidence into a coherent view of what matters now.
2. **Develop and challenge an investment view.** Move from facts to a reasoned interpretation while exposing competing explanations, disagreement, uncertainty, assumptions, and evidence that could invalidate the leading thesis.
3. **Translate the view into portfolio consequences.** Determine what the evidence means given current positions, concentration, exposure, strategy, time horizon, risk, and competing opportunities.
4. **Choose among actions under explicit risk.** Compare reasonable actions and tradeoffs, allow risk to shape the recommendation itself, and explain what conditions would change the preferred action.
5. **Understand, communicate, and defend the decision.** Preserve enough evidence, assumptions, disagreement, constraints, reasoning, recommendation, and uncertainty to answer why the decision was made without reconstructing the analysis from memory.
6. **Learn from decisions over time.** Revisit what was known, what was believed, what happened, which assumptions failed, and whether the reasoning process was useful so future decisions and processes can improve.

A concise product shorthand for these jobs is:

> **Understand → Challenge → Apply portfolio context → Decide under risk → Explain → Learn**

### Decision lifecycle

Polaris should support a closed decision loop rather than an analyze-and-forget workflow:

```text
observe
  ↓
reason
  ↓
recommend
  ↓
human decision
  ↓
observe outcome
  ↓
evaluate
  ↓
learn
  └────────→ future decisions
```

A completed decision process should leave durable evidence sufficient to inspect the decision over time. The working product concept is a **decision record**: a durable representation of decision context, evidence, interpretations, disagreement, uncertainty, risk, alternatives, recommendation, reasoning, human decision where recorded, subsequent outcome, evaluation, and lessons as those become available.

`Decision record` is a product concept at this stage, not a commitment to a particular implementation object, storage model, or API.

### Job boundaries

Polaris is not primarily hired to provide raw market data, draw charts, screen securities, execute brokerage orders, manage brokerage accounts, build arbitrary AI workflows, act as an unrestricted financial chatbot, consume news, or generate reports. Any such capability must justify itself by serving the decision cycle, explanation, evaluation, or durable knowledge that improves future decisions.

## Product Identity

Polaris is an **AI-assisted portfolio decision system for sophisticated individual decision-makers and small investment teams**.

It combines investment intelligence, portfolio context, risk-aware reasoning, durable decision evidence, and evaluation into an opinionated decision lifecycle that supports—but does not replace—human investment judgment.

Polaris is delivered through a configurable and extensible product platform, but it is not a general-purpose AI, workflow, or financial-development platform. Its configurability exists to adapt the Polaris decision process to different portfolios, strategies, evidence sources, models, and operating contexts.

### Identity hierarchy

The product hierarchy is:

```text
Portfolio Decision System
        ↓ supported by
Investment Intelligence
        ↓ delivered through
Configurable Product Platform
```

The hierarchy is intentional. The decision system defines the product. Investment intelligence supplies the evidence and reasoning capabilities necessary to support that system. Platform mechanisms make the product configurable, extensible, reliable, and integratable without becoming the product's primary identity.

### Opinionated lifecycle, configurable process

Polaris should be **opinionated about the investment decision lifecycle and flexible about the investment process configured within it**.

A trustworthy Polaris decision should have recognizable concepts such as decision context, attributable evidence, portfolio state, interpretation, challenge or uncertainty, explicit risk, alternatives, recommendation, explanation, a human decision boundary, and later evaluation where applicable.

Users may vary their portfolios, strategies, indicators, evidence providers, models, risk thresholds, time horizons, and other domain configuration. That flexibility must not turn Polaris into a blank canvas for arbitrary workflow construction.

### Ecosystem position

Polaris occupies the **decision layer between investment information systems and investment action systems**.

```text
SENSE                    DECIDE                    ACT
  │                         │                       │
Market data                 │                   Broker / trading platform
Economic data               │                   Order entry / execution
News / research ───────→  POLARIS  ───────→     Operational systems
Portfolio state             │                       │
External analytics          │                       │
                            ↓                       │
                       Human decision ──────────────┘
                            │
                            └──── resulting portfolio state returns to Polaris
```

Information systems primarily establish **what is happening or what is true**. Polaris determines **what it means for this portfolio, what deserves attention, and what should be considered**. Trading, brokerage, and other operational systems carry out the human's decision and remain responsible for low-latency execution and account operations.

Polaris therefore complements rather than attempts to replace specialist systems such as:

* brokers, trading platforms, and execution systems;
* market-data and charting platforms;
* news and research services;
* portfolio accounting and books-and-records systems;
* specialist quantitative-research environments;
* general-purpose AI tools;
* communication and reporting destinations.

Polaris may consume information from, integrate with, or project decisions into these systems. Integration does not transfer their specialist product responsibilities to Polaris.

For the detailed rationale and category-by-category boundaries, see [`product-ecosystem.md`](./product-ecosystem.md).

### Decision-time, not trading-engine time

Polaris should be current at the speed required for **portfolio judgment**, not at the speed required for exchange execution.

Three conceptual clocks are useful:

```text
Market time       microseconds → milliseconds → seconds
                  quotes, matching, routing, execution, stops

Decision time     seconds → minutes
                  materiality, portfolio impact, risk, reassessment

Analytical time   minutes → hours → days
                  deep research, strategy analysis, evaluation
```

Polaris is not designed for the first category as a critical-path execution system. It owns the latter two, including event-aware reassessment when a fast market change makes existing decision context stale or materially changes a portfolio question.

A major market shock should therefore cause Polaris to identify affected decisions and assumptions, refresh the evidence required for those decisions, reassess them, and proactively bring prepared decision work to the human. Existing brokerage and execution systems remain responsible for immediate market action.

### Freshness is part of trustworthiness

Evidence freshness must be appropriate to the decision being supported rather than governed by one universal definition of "real time."

Polaris should preserve enough freshness metadata to determine whether critical market, portfolio, economic, research, and other evidence is current enough for the recommendation being made. If a required input is too stale, Polaris should degrade, qualify, withhold, or invalidate the affected recommendation rather than silently presenting old decision context as current.

During rapidly changing conditions, a useful conceptual response may separate:

```text
Fast deterministic triage
        ↓
Material shock detected
Affected decisions identified
Stale assumptions / breached conditions exposed
        ↓
Reasoned decision reassessment
        ↓
Updated implications, alternatives, risk, recommendation
        ↓
Human judgment
```

This preserves responsiveness without pretending that AI reasoning or human portfolio judgment should operate at exchange-engine latency.

### Identity consequences

* **Decision system before platform.** Platform architecture and extensibility must serve the portfolio decision product rather than compete with it for identity.
* **Investment intelligence is a capability family, not the endpoint.** Research and analysis are valuable when they advance the decision lifecycle.
* **Domain configurability, not general-purpose programmability.** Polaris should expose investment-domain concepts where possible rather than requiring users to think in runtime primitives such as nodes, graphs, agents, prompts, or generic tools.
* **AI-assisted, not AI-governed.** AI is an important reasoning mechanism, but the product must remain free to prefer deterministic software wherever that creates a more trustworthy result.
* **Not a portfolio-management system of record.** Polaris needs portfolio state and portfolio reasoning without implicitly owning accounting, reconciliation, order management, trade lifecycle, brokerage operations, or every operational aspect of portfolio management.
* **Decision layer, not execution layer.** Polaris decides what deserves consideration and prepares recommendations; specialist systems remain responsible for market-speed execution and operational action.
* **Decision-time current.** Polaris must be current enough for the decision at hand without adopting low-latency trading infrastructure as its product center.
* **Freshness is explicit.** Stale critical evidence may make a recommendation untrustworthy and must be surfaced or enforced accordingly.
* **The decision lifecycle is the organizing spine.** Product capabilities and existing subsystems should be evaluated by where they participate in or support that lifecycle.
* **Runtime qualities remain subordinate to user value.** Reliability, replayability, observability, provenance, and governance may be enabled by a strong runtime, but "runtime-native" is not the fundamental product purpose.

## Core Experience

Polaris provides an **attentive, decision-centered experience**. The product is organized around decisions that deserve attention rather than around a catalog of features, while keeping analytical and product capabilities directly accessible when the user wants them.

A decision may be initiated by the user, by a scheduled review, or by Polaris itself when new information materially affects an active portfolio condition, thesis, risk, assumption, prior decision, or review condition. All three initiation paths should enter the same disciplined decision lifecycle.

### Decision-first and attention-first

The primary experience should answer:

> **What deserves my attention, and what decision are we trying to make?**

Polaris should assemble relevant known context rather than make the user repeatedly reconstruct their investment world. It should connect current portfolio state, strategy, risk policy, active theses, prior decisions, unresolved questions, invalidation conditions, expected catalysts, historical knowledge, and new evidence where relevant.

Features remain available as tools, but they do not define the main interaction model. The user should not have to manually traverse market data, research, risk, simulation, retrieval, reports, and other capabilities merely to assemble the context for a decision.

### Attentive and proactive

Polaris should not require the user to identify every important question first.

It should continuously relate relevant change to the user's current investment context and distinguish **decision relevance** from general event importance. Immaterial changes may be absorbed quietly. Material changes may cause Polaris to investigate, reassess affected decision state, and surface prepared work for human attention.

A useful initiative progression is:

```text
Observe
  ↓
Connect
  ↓
Investigate when warranted
  ↓
Surface when materially relevant
  ↓
Propose a recommendation
  ↓
Escalate to human judgment
```

Polaris may take substantial initiative in attention, analysis, challenge, preparation, and recommendation. That initiative does not itself grant authority to take consequential investment action.

### Prepared engagement, not alerts

When Polaris interrupts the user, it should preferably bring **prepared decision work rather than merely demand attention**.

A useful proactive interaction explains what changed, why it matters to the portfolio or an existing thesis, what Polaris reassessed, whether the prior view changed, what the current recommendation is, which alternatives and risks remain material, and what now requires human judgment.

The desired distinction is:

```text
Alert:
"Something happened. You may want to look at it."

Polaris:
"Something changed that materially affects a decision we care about.
I investigated it. Here is what changed, what it means, and what now
requires your judgment."
```

Polaris should remain calm and selective. Proactivity that surfaces every market event would recreate the cognitive overload the product exists to reduce.

### Shock response and stale decision context

A rapid market event does not turn Polaris into an execution system, but it can make existing decision state unsafe to reuse without reassessment.

For example, if a broad equity index suddenly falls 15%, immediate order handling, stops, routing, fills, and broker controls remain the responsibility of the trading and execution stack. Polaris should instead:

1. recognize that the event is materially capable of invalidating existing decision context;
2. identify exposed portfolios, active theses, assumptions, risks, and recommendations;
3. mark affected prior recommendations or assumptions as requiring reassessment rather than presenting them as current;
4. refresh the evidence necessary for the affected portfolio decisions;
5. perform risk-aware reassessment at decision speed;
6. proactively surface the decisions that now require human attention.

The goal is not to compete with exchange-time systems. It is to ensure that the human receives a current, prepared portfolio decision frame as conditions change.

### Decision-appropriate freshness

The experience should make evidence recency and decision validity understandable where they matter.

A recommendation during a fast market shock may require market and portfolio state that is seconds or minutes old, while a long-horizon macro judgment may remain valid with substantially slower-moving evidence. Polaris should judge freshness relative to the decision contract.

If critical portfolio state, market state, or another required source is stale beyond what the decision can tolerate, Polaris should be able to say that it cannot presently support a current recommendation rather than disguising the uncertainty in a footnote.

### Progressive disclosure and interrogation

The default presentation should be concise enough for a decision-maker to understand the current conclusion quickly while allowing progressive inspection of the reasoning and evidence.

A natural depth progression is:

```text
Current assessment
Preferred action
Why
Material risks
What could change the view
        ↓
Reasoning
        ↓
Alternatives and challenge
        ↓
Risk analysis
        ↓
Evidence
        ↓
Sources / provenance
        ↓
Underlying analytical detail
```

Trustworthiness does not require dumping every internal detail into the default view. It requires that meaningful reasoning, evidence, uncertainty, assumptions, and provenance remain available and navigable.

### Recommendation as a decision package

A Polaris recommendation should be more than a directional answer or confidence score. The decision package should be able to communicate, as applicable:

* preferred action;
* why that action is preferred;
* material evidence;
* portfolio consequences;
* risk constraints;
* meaningful alternatives;
* strongest counterarguments or disagreement;
* key uncertainty;
* invalidation conditions;
* time horizon or review conditions.

Challenge should be visible in investment terms rather than as agent or model theater. The user should see meaningful disagreement, counterarguments, uncertainty, and invalidation conditions without needing to understand which internal agent, prompt, model, or workflow produced them.

Risk belongs **inside** the recommendation. It should be possible to understand how portfolio state and risk changed an otherwise plausible investment action rather than seeing risk as a separate approval stamp after the recommendation has already been formed.

### Explicit human decision boundary

The Polaris recommendation and the human decision are distinct facts.

Conceptually, the user may accept, modify, reject, or defer a recommendation and may optionally record their rationale. Polaris should preserve the difference rather than rewriting history as though its recommendation and the user's action were the same.

That distinction supports later evaluation of both the system's recommendations and the user's own decision process.

### Decisions become memory

Every consequential decision should naturally become durable decision memory rather than requiring the user to remember to save a report or transcript.

The decision record should preserve or link the meaningful lifecycle state before, during, and after the decision. Reports, CLI output, conversational responses, APIs, MCP, and future interactive interfaces are projections or interaction surfaces over that decision state rather than separate product identities.

Past decisions should also help Polaris determine what future changes matter. Active theses, assumptions, risks, invalidation conditions, deferred decisions, catalysts, and review conditions can make decision memory operational: they give Polaris context for deciding when the world has changed enough to warrant reassessment.

### The experience continues after the decision

Polaris should follow decisions through outcomes, evaluation, and learning rather than stopping when a recommendation is produced or a human decision is recorded.

Conceptually, a decision may move through states such as forming, recommended, decided, being observed, ready for evaluation, evaluated, and learned from. These are product semantics, not a commitment to a specific implementation state machine.

The product should be able to reconnect later evidence and outcomes to earlier decisions and surface those decisions again when they become materially relevant or ready for evaluation.

### Core experience characteristics

* **Decision-first, not feature-first.** Features remain accessible, but the main experience is organized around decisions and attention.
* **Attentive, not merely responsive.** Polaris can recognize when relevant changes create a decision that deserves human attention.
* **Context-aware, not repeatedly re-prompted.** Known portfolio, strategy, risk, history, and decision context should be reused when relevant.
* **Selective, not noisy.** Materiality is evaluated relative to the user's portfolio and active decision context; immaterial change can be absorbed quietly.
* **Prepared, not alert-driven.** When possible, Polaris investigates before interrupting and brings implications rather than assigning analysis back to the user.
* **Decision-time current, not exchange-time driven.** Polaris should respond fast enough for portfolio judgment while leaving low-latency execution to specialist systems.
* **Freshness-aware.** Evidence recency and staleness are part of recommendation trustworthiness, not incidental metadata.
* **Concise first, deep on demand.** The recommendation is quickly understandable and progressively interrogable.
* **Challenge without implementation theater.** Meaningful alternatives, uncertainty, and falsifiers are exposed in investment terms.
* **Risk inside the recommendation.** Risk shapes the proposed action rather than merely approving or rejecting it afterward.
* **Recommendation and human decision remain distinct.** Polaris can propose; consequential investment judgment remains explicitly human.
* **Persistent.** Consequential decisions become durable memory and remain available for future attention, evaluation, and learning.
* **Calm.** Polaris should not manufacture urgency or equate activity with intelligence; "no action warranted" is a valid and useful conclusion.
* **Interface-independent.** User questions, scheduled reviews, Polaris-initiated reassessments, reports, CLI, API, MCP, and future interactive surfaces should converge on the same decision model.

A governing experience principle is:

> **Polaris should reduce the cognitive work required to assemble and evaluate a portfolio decision without hiding the evidence, uncertainty, tradeoffs, freshness, or authority required to make it.**

## Current product framing

The working product framing is:

> **Polaris is an attentive, AI-assisted portfolio decision system for sophisticated individual decision-makers and small investment teams, occupying the decision layer between investment information systems and investment action systems and delivered through a configurable portfolio intelligence and decision-support platform.**

It helps them turn fragmented market, portfolio, research, risk, and model evidence into a systematic, explainable, risk-aware, repeatable decision process; proactively surfaces material changes that deserve attention; remains current at the speed required for portfolio judgment; keeps consequential investment authority human; and preserves the decision lifecycle for later evaluation and learning.

This framing remains subject to refinement as the remaining Product Definition sections are completed.

## Product Definition work remaining

The following areas remain intentionally unresolved and will be defined before this document is considered complete:

1. Authority model
2. Scope boundaries
3. Differentiation
4. Core capabilities
5. Product principles
