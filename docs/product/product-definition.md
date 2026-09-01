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

## Current product framing

The working product framing is:

> **Polaris is an AI-assisted portfolio intelligence and decision-support platform for sophisticated individual decision-makers and small investment teams.**

It helps them turn fragmented market, portfolio, research, risk, and model evidence into a systematic, explainable, repeatable decision process while keeping consequential investment authority human.

This framing remains subject to refinement as the remaining Product Definition sections are completed.

## Product Definition work remaining

The following areas remain intentionally unresolved and will be defined before this document is considered complete:

1. Problems / jobs to be done
2. Product identity
3. Core experience
4. Authority model
5. Scope boundaries
6. Differentiation
7. Core capabilities
8. Product principles
