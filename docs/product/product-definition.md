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

### Execution continuity without execution authority

Polaris does not own execution, but it **does own continuity of the decision lifecycle across execution**.

When a human decision implies an external action such as entering, reducing, adding to, hedging, or closing a position, Polaris should preserve the intended action as part of the decision context and then observe what authoritative external systems report actually happened. Orders, partial fills, fills, protective stops, targets, modifications, cancellations, exits, and resulting portfolio state may all become relevant execution evidence attached to the originating decision.

The conceptual chain is:

```text
Polaris recommendation
        ↓
Human decision
        ↓
Action / execution intent
        ↓
External execution system
        ↓
Observed execution evidence
        ↓
Resulting portfolio state
        ↓
Position / action lifecycle
        ↓
Outcome
        ↓
Evaluation
        ↓
Learning
```

External execution and portfolio systems remain authoritative for what operationally occurred. Polaris should reconcile their evidence into its decision record rather than ask the user to recreate information that an authoritative system can provide.

Where association is sufficiently clear, reconciliation should occur automatically. Where multiple external actions could plausibly correspond to the same decision, Polaris should ask for lightweight confirmation rather than silently guess. External trades or position changes with no corresponding Polaris decision should remain identifiable as externally initiated activity rather than being retroactively attributed to a Polaris recommendation.

A decision may imply zero, one, or several external actions, and those actions may be partially executed, modified, abandoned, or completed over time. The decision record should distinguish the recommendation, the human decision, the intended action, the observed execution, and the eventual outcome so later evaluation can separate recommendation quality, human judgment, execution quality, risk management, and realized results.

The user should therefore experience execution continuity primarily as **automatic observation and reconciliation**, not duplicate bookkeeping.

For the detailed rationale, see [`product-execution-continuity.md`](./product-execution-continuity.md).

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
* **Execution evidence returns to the decision.** External execution authority is compatible with a closed Polaris lifecycle only if resulting actions and state can be observed and reconciled back into the decision record.
* **Operational reality outranks expected action.** External authoritative execution and portfolio state determine what actually happened; Polaris must not rewrite reality to match its recommendation or recorded intent.
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

The decision record should preserve or link the meaningful lifecycle state before, during, and after the decision. When the decision produces an external portfolio action, observed execution evidence and resulting portfolio state should join that same lifecycle automatically where practical rather than requiring duplicate user bookkeeping.

Reports, CLI output, conversational responses, APIs, MCP, and future interactive interfaces are projections or interaction surfaces over that decision state rather than separate product identities.

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
* **Execution-aware, not execution-authoritative.** Polaris should observe and reconcile external action into the decision lifecycle without becoming the system that places or controls the trade.
* **Concise first, deep on demand.** The recommendation is quickly understandable and progressively interrogable.
* **Challenge without implementation theater.** Meaningful alternatives, uncertainty, and falsifiers are exposed in investment terms.
* **Risk inside the recommendation.** Risk shapes the proposed action rather than merely approving or rejecting it afterward.
* **Recommendation and human decision remain distinct.** Polaris can propose; consequential investment judgment remains explicitly human.
* **Persistent.** Consequential decisions become durable memory and remain available for future attention, evaluation, and learning.
* **Calm.** Polaris should not manufacture urgency or equate activity with intelligence; "no action warranted" is a valid and useful conclusion.
* **Interface-independent.** User questions, scheduled reviews, Polaris-initiated reassessments, reports, CLI, API, MCP, and future interactive surfaces should converge on the same decision model.

A governing experience principle is:

> **Polaris should reduce the cognitive work required to assemble and evaluate a portfolio decision without hiding the evidence, uncertainty, tradeoffs, freshness, execution reality, or authority required to make it.**

## Authority Model

Polaris uses a **separation-of-powers authority model**. Capability does not imply authority, and no single component should own facts, enforceable rules, analytical interpretation, consequential investment judgment, and market-facing action at the same time.

The authority chain is:

```text
Evidence authority
Authoritative evidence sources establish operational facts.
        ↓
Deterministic authority
Rules, invariants, freshness requirements, and configured constraints govern admissibility and trust conditions.
        ↓
Analytical authority
AI and analytical machinery interpret, challenge, synthesize, prioritize, and recommend.
        ↓
Human authority
The human makes consequential investment decisions and material governance changes.
        ↓
Action authority
External operational systems carry out market-facing action.
        ↓
Evidence returns
Observed execution and resulting state re-enter the decision lifecycle.
```

### Authority boundaries

* **Sources own facts.** Polaris may interpret and reconcile authoritative evidence but must not rewrite operational reality to match a recommendation, expectation, or preferred narrative.
* **Deterministic software owns enforceable rules.** Explicit invariants, freshness requirements, hard risk limits, and other configured constraints should be enforced deterministically where practical.
* **AI owns reasoning, not authority over capital.** Polaris may autonomously observe, investigate, reassess, challenge, compare alternatives, reason about risk, recommend, explain, and proactively escalate a decision that deserves attention.
* **Humans own consequential investment judgment.** A human may accept, modify, reject, defer, or act differently from a Polaris recommendation and retains authority over material policy and governance changes.
* **External operational systems own market-facing action.** Orders, fills, stops, exits, and other execution responsibilities remain outside Polaris even though their evidence returns to the decision record.

Human authority does not require human initiation. Polaris may initiate substantial analytical work on its own; the human boundary applies when consequential investment judgment or a material governance change is required.

### Hard constraints cannot be reasoned away

Polaris should distinguish hard constraints from soft analytical guidance.

AI may weigh soft constraints and may intellectually challenge a hard policy. It may not silently modify, bypass, or reinterpret a hard constraint in order to approve its preferred action. If a hard policy should change, that is an explicit human governance decision.

Missing evidence, stale required context, violated hard constraints, or sufficiently unresolved uncertainty may cause Polaris to qualify, withhold, or invalidate a recommendation rather than manufacture certainty.

### Internal analytical autonomy

Polaris may autonomously perform governed internal informational, analytical, and decision-state actions when evidence and policy support doing so. Examples include refreshing evidence, detecting staleness, recalculating risk, initiating reassessment, scheduling evaluation, reconciling unambiguous external execution evidence, and surfacing a material change.

When uncertainty materially changes the meaning of an internal transition, Polaris should preserve the ambiguity and escalate for confirmation rather than silently guess.

### Preserve the full authority path

Every **material authority decision** across the lifecycle must be durably preserved and inspectable **whether the authority layers agree or disagree**.

Polaris should preserve not only conflicts, blocks, overrides, failures, and exceptions, but also affirmative authority decisions such as:

* evidence accepted as sufficient and current;
* policies evaluated and satisfied;
* candidate actions permitted;
* recommendations issued or deliberately withheld;
* human acceptance, modification, rejection, or deferral;
* successful execution reconciliation;
* faithful or divergent external action;
* resulting outcomes.

A terminal result must not erase the authority path that produced it. A policy that evaluated and permitted an action is different from a policy that was bypassed or never evaluated; silence is not evidence that authority was correctly exercised.

The working product concept is an **authority trace**: durable provenance of which authority evaluated each material transition, what decision it made, and how that authority decision affected the lifecycle.

The authority trace should be **always preserved and always inspectable**, while the Core Experience remains concise-first and progressively disclosed. Material authority effects should surface prominently in the normal decision experience; the complete trace should remain available on demand.

### Authority provenance complements evidence provenance

The authority trace complements Polaris's evidence model rather than replacing it.

**Evidence provenance** answers what was known, where it came from, when it was observed, and whether it was attributable and current.

**Authority provenance** answers which authority evaluated that evidence or decision state, what that authority decided, which rules or constraints were applied, what the analytical layer recommended, what the human decided, and what the action system actually did.

Together they create a more complete decision provenance:

```text
Evidence provenance
What was known and where it came from
        +
Authority provenance
Who or what evaluated it and what authority decision followed
        ↓
Trustworthy decision provenance
```

This is a product-level relationship, not a commitment to a particular event schema, database representation, or current evidence-model implementation.

### Authority consequences

* **Capability does not imply authority.**
* **Operational reality outranks expectation.**
* **AI may initiate analysis without acquiring capital-action authority.**
* **Hard constraints cannot be silently reasoned away.**
* **Uncertainty that materially changes meaning escalates rather than being guessed away.**
* **Polaris may withhold a recommendation when the decision contract cannot be satisfied.**
* **Every material authority decision is positively preserved, including approvals and satisfied constraints.**
* **The terminal outcome never substitutes for the authority path that produced it.**
* **Agreement, disagreement, policy effects, human overrides, execution fidelity, and outcomes are all learnable information.**
* **Evidence provenance and authority provenance are complementary trust mechanisms.**

For the detailed rationale, see [`product-authority-model.md`](./product-authority-model.md).

## Scope Boundaries

Polaris owns the **portfolio decision lifecycle** and the trust, context, provenance, attention, reasoning, authority, continuity, evaluation, and learning responsibilities necessary to make that lifecycle coherent. It does not need to own every system or capability that supplies evidence to, supports, or receives action from that lifecycle.

The governing rules are:

> **Polaris owns decisions, not everything decisions touch.**

> **Dependency does not imply ownership.**

> **Feature presence does not imply product-category ownership.**

### Three scope rings

Polaris scope has three responsibility rings:

1. **Polaris-owned responsibilities.** The decision lifecycle itself: attention and materiality, decision context, evidence use and provenance, interpretation and challenge, portfolio consequences, risk-aware reasoning, authority and governance, recommendation, human-decision continuity, external-action reconciliation, outcome, evaluation, and learning.
2. **Supporting capabilities.** Capabilities such as charts, research tools, news ingestion, screening, simulation, backtesting, reports, conversation, dashboards, collaboration, and integrations may exist inside Polaris when they materially improve decision quality, reduce friction, support explanation, preserve continuity, or improve evaluation.
3. **External specialist responsibilities.** Responsibilities such as exchange-speed execution, brokerage operations, official books and records, portfolio accounting, custody, settlement, tax accounting, comprehensive market-data vending, generalized quantitative development, general-purpose AI, and broad regulatory operations remain outside Polaris's defining product responsibility unless the Product Definition is explicitly reconsidered.

Supporting status does not imply low quality. A supporting capability may be sophisticated and differentiated when excellence materially improves the decision experience. Its evolution must remain accountable to the portfolio decision system rather than developing an independent product mandate.

### Integrate rather than duplicate ownership

Where a specialist external system has factual or operational authority, Polaris should normally integrate with it and preserve that authority rather than create a competing shadow system of record.

Polaris may cache, normalize, derive, preserve, reconcile, and reason over external state. Where another system owns the underlying fact, operational reality remains authoritative.

This applies to market data, portfolio state, execution evidence, accounting facts, and other externally authoritative information.

### Decision-oriented scope examples

* **Market data:** decision-relevant acquisition, attribution, freshness, sufficiency, and interpretation are in scope; comprehensive exchange-speed market-data vending is not a defining responsibility.
* **Portfolio state:** decision-oriented holdings, exposure, concentration, and risk context are in scope; official portfolio accounting and books-and-records ownership are not implied.
* **Research:** gathering, attributing, synthesizing, challenging, and connecting research to decisions are in scope; comprehensive information possession is not the objective.
* **Simulation and backtesting:** in scope when they form, challenge, evaluate, or improve decisions; generalized quantitative-programming infrastructure is not itself a Polaris job.
* **Risk:** portfolio decision risk and configured decision policy are core; exchange-time margin, buying-power, and execution controls remain with specialist operational systems.
* **Reporting and distribution:** reports, PDFs, email, dashboards, CLI, API, and MCP may project shared decision state; they do not become independent product centers.
* **Governance:** decision governance is core; broad regulatory operations require separate product justification.
* **Collaboration:** small-team decision collaboration is in scope; enterprise organization machinery is not presently a design center.
* **Opportunity discovery:** may support an attentive decision system; generalized screening is not the product center.
* **Conversation:** an important decision interface, not a general financial chatbot.
* **Workflow infrastructure:** reusable internal infrastructure is compatible with Polaris; arbitrary workflow construction is not a primary user job.

### Scope decision test

Before a major capability becomes Polaris scope, ask:

1. Does it materially support **Understand, Challenge, Apply portfolio context, Decide under risk, Explain, or Learn**?
2. Does Polaris need to own the responsibility to fulfill its decision contract?
3. Can a specialist system own the underlying responsibility while Polaris consumes, reconciles, or projects the necessary evidence?
4. Would a narrower Polaris-native capability materially improve decision quality or reduce user friction?
5. Would owning the full category create a new primary user job or materially change Polaris's authority model, latency contract, operational responsibility, regulatory burden, or product identity?

If the final answer is yes, there is a strong presumption that the broader category is outside scope until the Product Definition is explicitly reconsidered.

### Scope consequences

* **Core responsibilities must close the decision lifecycle.**
* **Supporting features justify themselves through decision value.**
* **A supporting capability may be excellent without becoming a new product center.**
* **Authoritative specialist systems should remain authoritative for the responsibilities they own.**
* **Polaris should integrate and reconcile rather than casually create shadow systems of record.**
* **Expansion that creates a new primary job, authority domain, latency regime, regulatory burden, or operational contract is presumed outside scope until explicitly reconsidered.**

For the detailed rationale, see [`product-scope-boundaries.md`](./product-scope-boundaries.md).

## Differentiation

Polaris differentiates by treating **portfolio decisions as durable, first-class lifecycles** rather than disposable analyses, recommendations, conversations, reports, alerts, workflows, or trades.

A Polaris decision keeps the material evidence, reasoning, challenge, portfolio context, risk, authority path, human judgment, external action evidence, outcome, evaluation, and lessons connected over time. The decision is therefore the durable product object; interfaces, models, reports, workflows, and analytical techniques are replaceable means used to form, inspect, project, or evaluate it.

### Three central differentiators

1. **Durable decisions.** The decision persists as a closed lifecycle rather than ending at analysis or recommendation. Past decisions remain operational context for future attention, evaluation, and learning.
2. **Trust by architecture.** Polaris creates trust through attributable evidence, decision-appropriate freshness, deterministic constraints, analytical challenge, positive authority provenance, explicit human judgment, and authoritative external operational truth rather than model confidence alone.
3. **Attentive intelligence.** Durable portfolio and decision context allows Polaris to determine which new information materially affects an active thesis, risk, assumption, review condition, or decision; investigate relevant change proactively; and remain quiet when nothing material changed.

### Portfolio decision quality over generic intelligence

Polaris does not stop at an investment opinion. Investment intelligence must be translated into consequences for the actual portfolio, shaped by risk and policy, challenged before recommendation, and evaluated afterward.

The intended progression is:

```text
Investment evidence
        ↓
Interpretation + challenge
        ↓
Portfolio consequences
        ↓
Risk + policy
        ↓
Recommendation
        ↓
Human decision
        ↓
Observed result
        ↓
Evaluation + learning
```

This makes the portfolio decision—not a security opinion, chat answer, signal, or model output—the final unit of product value.

### Human-governed initiative

Polaris combines substantial analytical autonomy with constrained capital authority. It may notice, investigate, reassess, challenge, recommend, and proactively bring prepared work to the human without waiting for every prompt. Consequential investment judgment remains human, and external systems remain responsible for execution.

The differentiating interaction is therefore neither passive decision support nor autonomous trading:

> **Maximum useful analytical initiative without surrendering consequential human investment judgment.**

### Decision provenance and historical integrity

Evidence provenance and authority provenance should make the material decision path reconstructable from what was knowable at the time. Historical evaluation should distinguish reasoning quality, policy effects, human judgment, execution fidelity, and realized outcome rather than treating P&L alone as proof of decision quality.

Polaris should not silently use future information to rewrite what a past decision should have known, and stale current context should reduce, qualify, or invalidate a recommendation when the decision requires fresher evidence.

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
Authority-provenanced
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

* **The decision is the durable product object.**
* **Closed loop beats analyze-and-forget.**
* **Trust comes from provenance and separation of powers, not model confidence alone.**
* **Portfolio consequence matters more than generic investment opinion.**
* **Challenge is structural, not optional implementation theater.**
* **Risk shapes recommendations.**
* **Human authority coexists with strong AI initiative.**
* **External execution remains connected without becoming Polaris-controlled.**
* **Learning evaluates reasoning, authority, execution, and outcome rather than P&L alone.**
* **Historical evaluation uses what was knowable then.**
* **Attention quality matters more than notification quantity.**
* **The coherent system is the differentiation; implementation features are replaceable means.**

For the detailed rationale and adjacent-product comparison, see [`product-differentiation.md`](./product-differentiation.md).

## Core Capabilities

Polaris requires **nine core product capabilities** that together close the portfolio decision lifecycle. These capabilities describe what Polaris must be able to do, not how those abilities are implemented.

The core capability spine is:

1. **Attention & Decision Initiation.** Determine what deserves attention and when a portfolio decision should be created, reopened, or reassessed through user, scheduled, or Polaris-initiated work.
2. **Decision Context & Evidence.** Assemble the decision-specific portfolio context and attributable evidence necessary for responsible reasoning, including provenance, freshness, sufficiency, conflicts, and historical integrity where material.
3. **Investment Reasoning & Challenge.** Develop an investment interpretation, compare alternatives, expose uncertainty and assumptions, seek meaningful counterevidence, and seriously test why the leading view may be wrong.
4. **Portfolio Consequence & Risk.** Translate an investment view into consequences for the actual portfolio under analytical risk, portfolio state, strategy, horizon, and deterministic policy constraints.
5. **Recommendation Formation.** Compare reasonable portfolio actions under uncertainty and form an explainable preferred course of action—or deliberately withhold one when the decision contract cannot support a responsible recommendation.
6. **Authority & Human Decision.** Apply the separation-of-powers authority model, preserve positive and negative authority decisions, and keep the Polaris recommendation distinct from human acceptance, modification, rejection, or deferral.
7. **Action Continuity & Reconciliation.** Observe, associate, reconcile, and track externally executed action and resulting portfolio state without acquiring execution authority.
8. **Durable Decision Memory.** Preserve the decision faithfully through time, distinguish what was knowable then from what is known now, and use prior decision state as active context for future attention and reasoning.
9. **Outcome Evaluation & Learning.** Evaluate evidence, reasoning, risk, policy, recommendation, human judgment, execution fidelity, and outcome without reducing decision quality to realized P&L alone, then feed useful lessons into future decisions.

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

### Capability model, not implementation map

AI models, agents, workflows, retrieval systems, replay, persistence technologies, APIs, interfaces, reports, and other technical mechanisms may implement, expose, strengthen, or observe one or more core capabilities. They are not themselves the durable capability model.

Likewise, evidence domains such as market, macroeconomic, news, sentiment, fundamental, and technical analysis are important inputs to decision-oriented capabilities rather than independent top-level product centers at this level.

The capability model should remain stable even if the implementation underneath it changes substantially.

### Supporting platform capabilities

The nine core capabilities are enabled by important supporting platform capabilities:

* **Integration & Connectivity** — connect to decision-relevant evidence, portfolio state, execution systems, external tools, and distribution destinations.
* **Interaction & Projection** — expose shared decision state through conversation, interactive UI, reports, CLI, API, MCP, email, messaging, and future surfaces without creating competing decision semantics.
* **Configuration & Extensibility** — adapt Polaris to different portfolios, strategies, asset universes, evidence providers, models, risk policies, horizons, and operating preferences without turning the product into an arbitrary workflow platform.
* **Runtime Reliability & Observability** — execute decision work reliably, expose failures, preserve relevant state and provenance, support recovery where appropriate, and make lifecycle execution inspectable.
* **Security & Operations** — protect credentials, portfolio information, integrations, configuration, access boundaries, and operational trust assumptions appropriate to the product's maturity.

These supporting capabilities may become sophisticated. Their purpose remains to enable the portfolio decision system rather than compete with it for product identity.

### Capability maturity evolves across releases

A capability being core does not require every release to implement its ultimate depth.

Core capability maturity may increase across releases while the capability model remains stable. Roadmap work should therefore describe which end-to-end product abilities become **usable, trustworthy, broader, or more mature** in each release rather than organizing releases around implementation feature accumulation.

Useful product-level questions include:

* Can Polaris identify why something materially deserves attention?
* Can it show which evidence informed a decision and whether that evidence was sufficiently current?
* Can the user inspect the strongest meaningful challenge to the preferred view?
* Can Polaris explain how portfolio state and risk changed the implied action?
* Can it explain the preferred action, alternatives, and conditions that would change the recommendation?
* Can the material authority path be reconstructed, including affirmative authority decisions?
* Can Polaris determine whether the human decision was actually implemented externally?
* Can it reconstruct what was knowable when the decision occurred?
* Can it evaluate the decision process separately from the realized outcome?

These questions should become more useful than asking whether a particular class, service, agent, workflow, or interface exists.

### Core capability consequences

* **The nine core capabilities form the durable product capability spine.**
* **Durable Decision Memory spans and supports the entire lifecycle.**
* **AI and deterministic software are methods used across capabilities, not separate top-level user capabilities.**
* **Risk remains integrated with portfolio consequence and recommendation rather than becoming a detached approval stage.**
* **Execution observation and reconciliation are core even though execution authority remains external.**
* **Evaluation distinguishes decision-process quality from outcome alone.**
* **Supporting platform capabilities enable the core system without becoming independent product centers.**
* **Capability maturity may deepen across releases without redefining the capability model.**
* **Roadmap milestones should be expressed in end-to-end capability maturity and product guarantees rather than feature accumulation.**

For the detailed rationale, see [`product-core-capabilities.md`](./product-core-capabilities.md).

## Current product framing

The working product framing is:

> **Polaris is an attentive, AI-assisted portfolio decision system for sophisticated individual decision-makers and small investment teams, occupying the decision layer between investment information systems and investment action systems and delivered through a configurable portfolio intelligence and decision-support platform.**

It helps them turn fragmented market, portfolio, research, risk, and model evidence into a systematic, explainable, risk-aware, repeatable decision process; proactively surfaces material changes that deserve attention; treats decisions as durable lifecycles rather than disposable outputs; creates trust through evidence and authority provenance; remains current at the speed required for portfolio judgment; separates evidence, enforceable rules, analytical reasoning, human judgment, and external action; observes external execution evidence so decisions remain connected to what actually happened; integrates with specialist systems without assuming their product responsibilities; and preserves the lifecycle for later evaluation and learning.

This framing remains subject to refinement as the remaining Product Definition sections are completed.

## Product Definition work remaining

The following area remains intentionally unresolved and will be defined before this document is considered complete:

1. Product principles
