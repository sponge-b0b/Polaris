# Polaris Product Definition

**Status:** In progress  
**Purpose:** Define the durable product doctrine that should guide Polaris capability, roadmap, and implementation decisions.

This document describes **what Polaris is and who it is for**. It intentionally avoids implementation technologies and detailed architecture. The fuller reasoning behind these decisions is preserved in [`product-rationale.md`](./product-rationale.md).

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

### Identity consequences

* **Decision system before platform.** Platform architecture and extensibility must serve the portfolio decision product rather than compete with it for identity.
* **Investment intelligence is a capability family, not the endpoint.** Research and analysis are valuable when they advance the decision lifecycle.
* **Domain configurability, not general-purpose programmability.** Polaris should expose investment-domain concepts where possible rather than requiring users to think in runtime primitives such as nodes, graphs, agents, prompts, or generic tools.
* **AI-assisted, not AI-governed.** AI is an important reasoning mechanism, but the product must remain free to prefer deterministic software wherever that creates a more trustworthy result.
* **Not a portfolio-management system of record.** Polaris needs portfolio state and portfolio reasoning without implicitly owning accounting, reconciliation, order management, trade lifecycle, brokerage operations, or every operational aspect of portfolio management.
* **The decision lifecycle is the organizing spine.** Product capabilities and existing subsystems should be evaluated by where they participate in or support that lifecycle.
* **Runtime qualities remain subordinate to user value.** Reliability, replayability, observability, provenance, and governance may be enabled by a strong runtime, but "runtime-native" is not the fundamental product purpose.

## Current product framing

The working product framing is:

> **Polaris is an AI-assisted portfolio decision system for sophisticated individual decision-makers and small investment teams, delivered through a configurable portfolio intelligence and decision-support platform.**

It helps them turn fragmented market, portfolio, research, risk, and model evidence into a systematic, explainable, risk-aware, repeatable decision process while keeping consequential investment authority human and preserving the decision lifecycle for later evaluation and learning.

This framing remains subject to refinement as the remaining Product Definition sections are completed.

## Product Definition work remaining

The following areas remain intentionally unresolved and will be defined before this document is considered complete:

1. Core experience
2. Authority model
3. Scope boundaries
4. Differentiation
5. Core capabilities
6. Product principles
