# Polaris Differentiation

**Status:** In progress  
**Purpose:** Preserve the product reasoning for what makes Polaris meaningfully different from adjacent investment software and AI products without defining differentiation through transient implementation features.

This document refines the Product Definition recorded in [`product-definition.md`](./product-definition.md). It describes durable product differentiation rather than a competitive feature matrix or a claim that every adjacent product behaves identically.

## Decision

Polaris differentiates by treating **Investment Decisions as durable, first-class lifecycles** rather than disposable analyses, Investment Recommendations, conversations, reports, alerts, workflows, or trades.

A Polaris Investment Decision and its Durable Decision Memory preserve enough connected context to understand not only what happened, but why:

```text
Decision Need
      ↓
Relevant Evidence
      ↓
Investment View + challenge
      ↓
Projected Portfolio Consequences
      ↓
Portfolio Risk + deterministic boundaries
      ↓
Investment Recommendation
      ↓
Admissibility / applicable authority acts
      ↓
Human Investment Decision
      ↓
Action Intent where applicable
      ↓
Observed external activity
      ↓
Outcome
      ↓
Decision Evaluation
      ↓
Lessons
      ↓
Future Attention / decisions
```

Polaris also differentiates through **trust by architecture** and **attentive intelligence**. Trust comes from preserving Evidence, freshness, deterministic rule results, Polaris judgment, power-specific authority acts, Human Investment Decision, operational reality, and Outcomes as distinct and inspectable parts of the lifecycle. Attentiveness comes from durable Portfolio and decision context that allows Polaris to determine when new information is Investment Relevant and material to something the user already cares about.

The differentiation is therefore cumulative. It is the coherent decision system created when these responsibilities reinforce one another, not any one AI model, agent topology, workflow engine, retrieval technique, report format, or integration.

## Not "AI for investing"

Polaris should not define its differentiation as simply producing better AI-generated investment analysis.

General-purpose AI and financial AI products can already answer questions such as:

* What happened in the market today?
* Summarize this company.
* Give me a bull and bear case.
* Explain this chart.
* Is this security attractive?

Excellent analysis remains necessary, but a differentiation thesis based mainly on model quality would weaken whenever foundation models improve or competitors gain access to similar models.

The more durable distinction is what surrounds, constrains, preserves, and learns from model reasoning.

## The Investment Decision lifecycle is the product

Many adjacent products own one moment of the investment process:

```text
Market-data product
"What happened?"

Research product
"What might it mean?"

Charting product
"What does the market look like?"

AI assistant
"What do you want to ask?"

Risk tool
"What could go wrong?"

Broker
"What do you want to execute?"

Trading journal
"What did you trade and how did it perform?"
```

Polaris connects those moments into a durable decision process:

```text
What deserves Attention?
        ↓
What is happening?
        ↓
What does it mean?
        ↓
What could make that interpretation wrong?
        ↓
What does it mean for this Portfolio?
        ↓
What Portfolio Risks and constraints matter?
        ↓
What Decision Alternatives are reasonable?
        ↓
What does Polaris recommend?
        ↓
What authority acts are required?
        ↓
What did the human decide?
        ↓
What external consequence was intended, if any?
        ↓
What actually happened?
        ↓
What was the Outcome?
        ↓
Was the reasoning useful?
        ↓
What Lesson should matter next time?
```

This changes the product from an analyze-and-forget tool into a closed-loop portfolio decision system.

## Durable decisions rather than disposable answers

A general AI interaction often behaves like:

```text
Question
   ↓
Answer
   ↓
Done
```

Even sophisticated investment software may effectively behave like:

```text
Analyze
   ↓
Recommendation
   ↓
Report
   ↓
Done
```

Polaris instead preserves the decision lifecycle across time:

```text
Decision Context
   ↓
Investment Recommendation
   ↓
Human Investment Decision
   ↓
Action Intent / external activity where applicable
   ↓
Outcome
   ↓
Decision Evaluation
   ↓
Lessons
   ↓
Future Attention / decision
```

The durable product meaning is therefore not merely a chat, report, workflow run, or trade. It is the Investment Decision and the Durable Decision Memory that preserves its material historical meaning and relationships.

Lowercase `decision record` may remain noncanonical shorthand for an assembled representation of that history, but it is not a separate canonical business entity.

This durability is what allows prior decisions to become future context rather than passive archives.

## Attentiveness rather than prompt dependence

Most AI experiences assume the user already knows that something matters, formulates the right question, and asks it.

Polaris should maintain enough Portfolio and decision context to ask a different question continuously:

> **Does this new information materially affect something this Portfolio currently cares about?**

That produces a selective Attention loop:

```text
new information
      ↓
Investment Relevant?
      │
   no ├──→ absorb quietly
      │
  yes ↓
Investment Material?
      │
   no ├──→ update context quietly
      │
  yes ↓
investigate
      ↓
Attention evaluates Decision Need
      ↓
continue unresolved work or create a new linked decision after prior resolution
      ↓
surface prepared decision work when human judgment is required
```

The differentiation is not alerts. It is memory-grounded Investment Materiality: past Investment Decisions, Investment Theses, Investment Assumptions, Invalidation Conditions, Portfolio Risks, Catalysts, Lessons, and Review Conditions help Polaris determine what deserves Attention now.

## Portfolio consequence rather than generic investment opinion

A generic investment question such as:

> Is this security attractive?

is incomplete for Polaris.

The stronger question is:

> Given this Portfolio, its current Exposure, Investment Strategy, Investment Mandate, Portfolio Risk, existing Positions, Investment Horizon, prior Investment Thesis, and competing Decision Alternatives, should anything change?

Polaris should therefore translate investment intelligence into **Projected Portfolio Consequences** rather than stopping at a security-level or market-level opinion.

The Investment Decision, not the isolated security analysis, is the final unit of product value.

## Challenge as part of the product contract

Polaris should not treat challenge as an optional feature that exists only when the user requests a bear case or when a particular multi-agent topology is enabled.

A trustworthy Investment Recommendation should structurally account for:

```text
Preferred Investment View
Supporting Evidence
Conflicting Evidence
Strongest alternative Investment Hypothesis
Material Investment Uncertainty
Investment Assumptions
Invalidation Conditions
```

The durable rule is:

> **An Investment Recommendation has not been adequately developed until meaningful reasons it may be wrong have been considered.**

The implementation may use one model, multiple models, deterministic analytics, human inputs, or combinations of them. The user-facing decision contract remains the same.

## Portfolio Risk shapes the Investment Recommendation

Polaris should not behave like an Investment Signal generator that forms an Investment Recommendation and then decorates it with a generic or qualified Risk Score.

The intended relationship is:

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
Investment Recommendation
```

These inputs remain semantically distinct. Portfolio Risk is economic risk; Formal Constraints are authoritative machine-evaluable Mandate restrictions; Policy deterministically governs platform operations or boundaries. None is automatically Approval or Human Investment Decision.

The same Investment Thesis may therefore produce different Investment Recommendations for different Portfolios or under different Portfolio Risk, Mandate, and Policy conditions.

This makes Polaris a portfolio decision system rather than a source of isolated directional opinions.

## Trust by architecture

Polaris should not ask users to trust an Investment Recommendation merely because an AI model is confident or capable.

Trust should emerge from the structure surrounding the reasoning:

```text
Evidence
Judgment-Time Availability
Freshness
Investment View + challenge
Portfolio Risk
Policy / Formal Constraint results
Power-specific authority acts
Human Investment Decision
Authoritative external truth
Outcome
```

The product should be capable of reconstructing the material decision, causal where supportable, and authority relationships from what was available to the relevant judgments at the time.

This is stronger than a generic explanation of why a model produced a particular answer.

## Evidence provenance plus authority history

Polaris preserves complementary forms of decision provenance.

### Evidence provenance

Evidence provenance answers:

* What Evidence existed?
* Where did it come from?
* When was it observed?
* Was it attributable?
* Was it available to the relevant judgment?
* Was it fresh enough for the intended use?

### Authority history

Authority history answers:

* Which Policy and Formal Constraint results applied?
* What did Polaris recommend?
* Which power-specific authority acts were required?
* Was Approval granted or denied where required?
* Was a Mandate Exception authorized where required?
* Was Governed Residual Risk accepted where required?
* What Human Investment Decision was formed?
* What did the external action system actually do?

Together:

```text
Evidence provenance
What was known and where it came from
        +
Authority history
Which rule results and authority acts applied
        ↓
Trustworthy decision provenance
```

This combination makes the decision process inspectable beyond the model output alone.

## Positive authority provenance

Polaris should preserve materially required positive rule results and authority acts even when nothing went wrong.

It should be possible to distinguish:

```text
Policy evaluated and allowed
```

from:

```text
No Policy denial happened to be recorded
```

Likewise, the lifecycle may preserve affirmative facts such as:

* required Evidence accepted as sufficient;
* Freshness Requirements satisfied;
* Formal Constraints evaluated and satisfied;
* Approval granted where required;
* Governed Residual Risk accepted where required;
* Human Investment Decision formed;
* external activity reconciled faithfully.

These are not interchangeable facts. Positive preservation creates a stronger trust model than systems that record only exceptions, violations, or overrides.

## High analytical autonomy with bounded human authority

Two common product extremes are insufficient.

### Passive decision support

```text
Here are dashboards and tools.
You assemble the decision.
```

### Autonomous trading agent

```text
I analyzed the situation and acted for you.
```

Polaris occupies a deliberate middle position:

```text
I noticed something.
I investigated it.
I challenged the Investment View.
I applied Portfolio and Portfolio Risk context.
I recommend this.
Here is the Evidence and authority history.
Here is what could make the view wrong.

You decide where human investment judgment is required.
```

The distinction can be summarized as:

> **Maximum useful analytical initiative without surrendering consequential human investment judgment.**

Human authority therefore does not make Polaris passive.

## Execution continuity without execution ownership

Many decision-support systems end when the Investment Recommendation is produced. Trading systems begin when an Order is submitted.

Polaris deliberately does not become the execution system, but it continues the decision thread across that boundary:

```text
Investment Recommendation
      ↓
Human Investment Decision
      ↓
Action Intent where applicable
      ↓
External execution
      ↓
Observed external activity / Portfolio State
      ↓
Outcome
      ↓
Decision Evaluation
```

A Human Investment Decision may establish zero Action Intents. Deferral and deliberate hold/no-action do not require synthetic Action Intents merely to duplicate the human judgment.

This continuity allows Decision Evaluation to distinguish among:

* Investment Recommendation quality;
* Human Investment Decision;
* implementation fidelity and Trade Implementation Risk;
* Portfolio Risk reasoning;
* Policy and Formal Constraint effects;
* observed Outcome.

A favorable Outcome is not automatically Evidence of good reasoning, and an unfavorable Outcome is not automatically Evidence of bad reasoning.

## Learning from the decision process, not P&L alone

Polaris should be capable of evaluating questions such as:

* Which Investment Assumptions proved correct or incorrect?
* Which Evidence was misleading or decisive?
* Which Portfolio Risks were underestimated?
* Was the Investment Thesis invalidated or did an adverse Outcome occur despite reasonable reasoning?
* Did the Human Investment Decision materially improve or degrade the disposition relative to the Investment Recommendation?
* Did a Policy or Formal Constraint protect the Portfolio or unnecessarily constrain the decision?
* Did implementation divergence explain the observed result?
* Was the reasoning process good even when the Outcome was unfavorable?

This makes learning about **decision quality**, not merely trade profitability.

## Historical truth rather than hindsight reconstruction

Meaningful Decision Evaluation requires preserving Judgment-Time Availability.

Polaris should resist hindsight reconstruction in which later information is treated as though it were available to an earlier judgment.

The intended historical contract is:

```text
Decision-time world
        ↓
Evidence available to the judgment
        ↓
Decision Context and reasoning
        ↓
Attributable judgment
        ↓
Later Outcome / Evidence
        ↓
Decision Evaluation against what was available then
```

Historical integrity makes retrospective learning materially more trustworthy.

## Decision-time truth rather than generic real time

A market terminal may compete on the freshest possible feed.

Polaris should compete on whether Evidence is sufficiently current for the investment use and whether the system can recognize when it is not.

For example:

```text
Current Investment Recommendation requires current Portfolio State
        ↓
Portfolio State exceeds the applicable Freshness Requirement
        ↓
Current recommendation cannot be supported
```

The historical Investment Recommendation remains part of Durable Decision Memory. The product changes current support, not historical existence.

The ability to qualify or withhold a current Investment Recommendation under stale conditions is a stronger decision property than confidently producing an answer from outdated context.

## Calm selectivity

Financial software often rewards activity through alerts, Investment Signals, breaking news, trade ideas, and urgency.

Polaris should optimize for **Attention quality rather than Attention quantity**.

Useful outcomes include:

> Nothing material changed.

and:

> No Portfolio action is warranted.

An attentive system that knows when to remain quiet is different from a notification system that equates activity with value.

## Opinionated domain product rather than blank canvas

Polaris should natively understand durable investment-decision concepts such as:

```text
Portfolio
Investment Thesis
Evidence
Portfolio Risk
Investment Recommendation
Investment Authority Regime
Human Investment Decision
Action Intent
Outcome
Decision Evaluation
```

Users may configure how their investment process operates inside that domain, but they should not need to assemble the product from arbitrary workflow primitives.

This gives Polaris more domain opinion than a generic workflow or agent framework while remaining more adaptable than a fixed financial application.

## Adjacent product comparison

The following comparison describes category-level responsibility rather than asserting that every product in a category has identical boundaries.

| Product category | Primary question | Typical endpoint | Polaris distinction |
| --- | --- | --- | --- |
| Market-data terminal | What is happening? | Information | What does it mean for this Portfolio and Investment Decision? |
| Charting / technical platform | What does the market look like? | Analysis | Connect Evidence to Projected Portfolio Consequences and decision work |
| Research platform | What should I know? | Research insight | Turn insight into challenged, Portfolio-Risk-aware decisions |
| General-purpose AI | What do you want to ask? | Answer | Maintains Decision Context and may cause Attention to identify the question |
| Financial AI copilot | What does AI think? | Recommendation | Preserves authority distinctions, Human Investment Decision, external Evidence, and Outcome |
| Risk platform | What risks exist? | Risk assessment / control | Portfolio Risk participates directly in Investment Recommendation formation |
| Broker / trading platform | What do you want to execute? | Execution / operational state | Polaris determines what should be considered and why |
| Trading journal | What did you trade and how did it perform? | Retrospective | Preserves Judgment-Time Availability, reasoning, authority history, and Decision Evaluation |
| Workflow / agent platform | What workflow do you want to build? | Execution machinery | Polaris provides an opinionated Investment Decision lifecycle |

## What does not define durable differentiation

Polaris should not define durable differentiation through the mere presence of implementation features such as:

* multiple agents;
* multiple LLMs;
* RAG or vector retrieval;
* workflow graphs;
* PostgreSQL;
* event-driven orchestration;
* replay infrastructure;
* MCP;
* telemetry;
* prompt libraries;
* particular model providers.

These may become significant implementation advantages, but they are replaceable means. A competitor can add them, and Polaris may itself change them without changing product identity.

Polaris should also avoid positioning itself around promises such as guaranteed superior investment returns or permanently superior AI accuracy. The durable product promise concerns the quality, trustworthiness, continuity, and evaluability of the decision process.

## The differentiation is cumulative

No single element is impossible for another product to copy.

The stronger differentiation emerges from the combination:

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

## Three central differentiators

The differentiation can be compressed into three durable ideas.

### Durable decisions

> **The Investment Decision persists as a lifecycle, and Durable Decision Memory preserves its material history.**

Decisions retain connected Evidence, reasoning, authority relationships, Human Investment Decision, external consequences where applicable, Outcomes, Decision Evaluations, and Lessons over time.

### Trust by architecture

> **Trust comes from provenance and separation of powers, not model confidence alone.**

Evidence, deterministic rule results, Polaris judgment, power-specific human authority, external operational truth, and Outcomes remain distinct and inspectable.

### Attentive intelligence

> **Past Portfolio and decision context helps Polaris determine what matters next.**

Polaris can proactively investigate Investment-Relevant material change and remain quiet when nothing materially affects the user's decision context.

## Consequences

The Differentiation decision implies:

* Investment Decision identity and Durable Decision Memory should remain more durable than any particular interface or workflow implementation;
* Polaris should optimize for decision quality rather than analysis volume, Investment Recommendation count, or notification count;
* model improvements should improve Polaris without becoming the sole basis of its value proposition;
* challenge should remain structural even if internal reasoning architecture changes;
* Portfolio context and Portfolio Risk must remain upstream of the final Investment Recommendation;
* Evidence provenance and power-specific authority history are central trust mechanisms rather than optional audit metadata;
* human authority should coexist with substantial proactive analytical autonomy;
* external execution should remain connected to decisions without becoming Polaris-controlled;
* Decision Evaluation should distinguish reasoning quality, Policy and Formal Constraint effects, Human Investment Decision, implementation effects, and Outcome;
* historical Decision Evaluation should preserve Judgment-Time Availability;
* stale Decision Context should reduce or remove current support for an Investment Recommendation rather than being hidden or rewriting history;
* calm selectivity should remain a product property;
* implementation features should remain replaceable means rather than durable product identity.

Polaris's differentiation is therefore not "more AI." It is a coherent, attentive, Portfolio-aware decision system whose historical meaning, authority relationships, and learning loop remain intact through time.
