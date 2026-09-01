# Polaris Differentiation

**Status:** In progress  
**Purpose:** Preserve the product reasoning for what makes Polaris meaningfully different from adjacent investment software and AI products without defining differentiation through transient implementation features.

This document refines the Product Definition recorded in [`product-definition.md`](./product-definition.md). It describes durable product differentiation rather than a competitive feature matrix or a claim that every adjacent product behaves identically.

## Decision

Polaris differentiates by treating **portfolio decisions as durable, first-class lifecycles** rather than disposable analyses, recommendations, conversations, reports, alerts, workflows, or trades.

A Polaris decision preserves enough connected context to understand not only what happened, but why:

```text
Decision need
      ↓
Relevant evidence
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
Observed external action
      ↓
Outcome
      ↓
Evaluation
      ↓
Learning
      ↓
Future decisions
```

Polaris also differentiates through **trust by architecture** and **attentive intelligence**. Trust comes from preserving evidence, freshness, rules, reasoning, authority, human judgment, operational reality, and outcomes as distinct and inspectable parts of the decision. Attentiveness comes from durable portfolio and decision context that allows Polaris to determine when new information materially changes something the user already cares about.

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

## The decision lifecycle is the product

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
What deserves attention?
        ↓
What is happening?
        ↓
What does it mean?
        ↓
What could make that interpretation wrong?
        ↓
What does it mean for this portfolio?
        ↓
What risks and constraints matter?
        ↓
What actions are reasonable?
        ↓
What does Polaris recommend?
        ↓
What authority decisions were made?
        ↓
What did the human decide?
        ↓
What actually happened?
        ↓
What was the outcome?
        ↓
Was the reasoning useful?
        ↓
What should change next time?
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

Polaris instead preserves the decision across time:

```text
Context
   ↓
Recommendation
   ↓
Human decision
   ↓
Observed action
   ↓
Outcome
   ↓
Evaluation
   ↓
Learning
   ↓
Future decision
```

The historical object is therefore not merely a chat, report, workflow run, or trade. It is the **decision record** and the connected lifecycle around it.

This durability is what allows prior decisions to become future context rather than passive archives.

## Attentiveness rather than prompt dependence

Most AI experiences assume the user already knows that something matters, formulates the right question, and asks it.

Polaris should maintain enough portfolio and decision context to ask a different question continuously:

> **Does this new information materially affect something this portfolio currently cares about?**

That produces a selective attention loop:

```text
new information
      ↓
decision relevance?
      │
   no ├──→ absorb quietly
      │
  yes ↓
investigate
      ↓
reassess if needed
      ↓
surface prepared decision work when human judgment is required
```

The differentiation is not alerts. It is memory-grounded materiality: past decisions, theses, assumptions, invalidation conditions, risks, and review conditions help Polaris determine what deserves attention now.

## Portfolio consequence rather than generic investment opinion

A generic investment question such as:

> Is this security attractive?

is incomplete for Polaris.

The stronger question is:

> Given this portfolio, its current exposure, strategy, risk policy, existing positions, investment horizon, prior thesis, and competing alternatives, should anything change?

Polaris should therefore translate investment intelligence into **portfolio consequences** rather than stopping at a security-level or market-level opinion.

The portfolio decision, not the isolated security analysis, is the final unit of product value.

## Challenge as part of the product contract

Polaris should not treat challenge as an optional feature that exists only when the user requests a bear case or when a particular multi-agent topology is enabled.

A trustworthy recommendation should structurally account for:

```text
Preferred interpretation
Supporting evidence
Counterevidence
Strongest alternative
Material uncertainty
Invalidation conditions
```

The durable rule is:

> **A recommendation has not been adequately developed until meaningful reasons it may be wrong have been considered.**

The implementation may use one model, multiple models, deterministic analytics, human inputs, or combinations of them. The user-facing decision contract remains the same.

## Risk shapes the recommendation

Polaris should not behave like a signal generator that forms a recommendation and then decorates it with a risk score.

The intended relationship is:

```text
Investment view
      +
Portfolio state
      +
Risk
      +
Policy
      ↓
Recommendation
```

The same investment thesis may therefore produce different actions for different portfolios or under different risk constraints.

This makes Polaris a portfolio decision system rather than a source of isolated directional opinions.

## Trust by architecture

Polaris should not ask users to trust a recommendation merely because an AI model is confident or capable.

Trust should emerge from the structure surrounding the reasoning:

```text
Evidence
Freshness
Interpretation
Challenge
Deterministic constraints
Analytical recommendation
Human authority
External operational truth
Outcome
```

The product should be capable of reconstructing the material causal and authority path behind a decision from what was knowable at the time.

This is stronger than a generic explanation of why a model produced a particular answer.

## Evidence provenance plus authority provenance

Polaris preserves two complementary forms of decision provenance.

### Evidence provenance

Evidence provenance answers:

* What evidence existed?
* Where did it come from?
* When was it known?
* Was it attributable?
* Was it fresh enough for the decision?

### Authority provenance

Authority provenance answers:

* Which rules and constraints were evaluated?
* What did the analytical layer recommend?
* What did deterministic policy permit or block?
* What did the human decide?
* What did the external action system actually do?

Together:

```text
Evidence provenance
What was known and where it came from
        +
Authority provenance
Who or what evaluated it and what decision followed
        ↓
Trustworthy decision provenance
```

This combination makes the decision process inspectable beyond the model output alone.

## Positive authority provenance

Polaris should preserve authority decisions even when nothing went wrong.

It should be possible to distinguish:

```text
Policy evaluated and approved
```

from:

```text
No policy failure happened to be recorded
```

Likewise, the lifecycle may preserve affirmative facts such as:

* evidence accepted as sufficient;
* freshness requirements satisfied;
* hard constraints evaluated and passed;
* recommendation permitted;
* human recommendation accepted;
* execution reconciled faithfully.

This creates a stronger trust model than systems that record only exceptions, violations, or overrides.

## High analytical autonomy with human capital authority

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
I challenged the view.
I applied portfolio and risk context.
I recommend this.
Here is the evidence and authority path.
Here is what could make the view wrong.

You decide.
```

The distinction can be summarized as:

> **Maximum useful analytical initiative without surrendering consequential human investment judgment.**

Human authority therefore does not make Polaris passive.

## Execution continuity without execution ownership

Many decision-support systems end when the recommendation is produced. Trading systems begin when the action is submitted.

Polaris deliberately does not become the execution system, but it continues the decision thread across that boundary:

```text
Recommendation
      ↓
Human decision
      ↓
Action intent
      ↓
External execution
      ↓
Observed fill / state change
      ↓
Position lifecycle
      ↓
Exit / completion
      ↓
Outcome
```

This continuity allows evaluation to distinguish among:

* recommendation quality;
* human judgment;
* execution quality;
* risk-management effects;
* policy effects;
* realized outcome.

A profitable outcome is not automatically evidence of good reasoning, and a losing outcome is not automatically evidence of bad reasoning.

## Learning from the decision process, not P&L alone

Polaris should be capable of evaluating questions such as:

* Which assumptions proved correct or incorrect?
* Which evidence was misleading or decisive?
* Which risks were underestimated?
* Was the thesis invalidated or merely unlucky?
* Did a human override improve the outcome?
* Did a hard policy protect the portfolio or unnecessarily constrain it?
* Did execution divergence explain the realized result?
* Was the reasoning process good even when the outcome was unfavorable?

This makes learning about **decision quality**, not merely trade profitability.

## Historical truth rather than hindsight reconstruction

Meaningful evaluation requires preserving what was actually knowable at decision time.

Polaris should resist hindsight reconstruction in which later information is treated as though it should have been available earlier.

The intended historical contract is:

```text
Decision-time world
        ↓
Decision-time evidence
        ↓
Decision-time reasoning
        ↓
Decision
        ↓
Later outcome
        ↓
Evaluation against what was knowable then
```

Historical integrity makes replay and retrospective learning materially more trustworthy.

## Decision-time truth rather than generic real time

A market terminal may compete on the freshest possible feed.

Polaris should compete on whether the evidence is sufficiently current for the decision and whether the system can recognize when it is not.

For example:

```text
Recommendation requires current portfolio state
        ↓
Portfolio state exceeds allowed staleness
        ↓
Current recommendation cannot be trusted
```

The ability to qualify or withhold a recommendation under stale conditions is a stronger decision property than confidently producing an answer from outdated context.

## Calm selectivity

Financial software often rewards activity through alerts, signals, breaking news, trade ideas, and urgency.

Polaris should optimize for **attention quality rather than attention quantity**.

Useful outcomes include:

> Nothing material changed.

and:

> No portfolio action is warranted.

An attentive system that knows when to remain quiet is different from a notification system that equates activity with value.

## Opinionated domain product rather than blank canvas

Polaris should natively understand durable investment-decision concepts such as:

```text
Portfolio
Thesis
Evidence
Risk
Recommendation
Authority
Decision
Action intent
Outcome
Evaluation
```

Users may configure how their investment process operates inside that domain, but they should not need to assemble the product from arbitrary workflow primitives.

This gives Polaris more domain opinion than a generic workflow or agent framework while remaining more adaptable than a fixed financial application.

## Adjacent product comparison

The following comparison describes category-level responsibility rather than asserting that every product in a category has identical boundaries.

| Product category | Primary question | Typical endpoint | Polaris distinction |
| --- | --- | --- | --- |
| Market-data terminal | What is happening? | Information | What does it mean for this portfolio and decision? |
| Charting / technical platform | What does the market look like? | Analysis | Connect evidence to portfolio consequence and action |
| Research platform | What should I know? | Research insight | Turn insight into challenged, risk-aware decisions |
| General-purpose AI | What do you want to ask? | Answer | Maintains decision context and may initiate the question |
| Financial AI copilot | What does AI think? | Recommendation | Preserves authority, human decision, execution evidence, and outcome |
| Risk platform | What risks exist? | Risk assessment / control | Risk participates directly in recommendation formation |
| Broker / trading platform | What do you want to execute? | Execution / operational state | Polaris determines what should be considered and why |
| Trading journal | What did you trade and how did it perform? | Retrospective | Preserves what was known, why, authority path, and reasoning quality |
| Workflow / agent platform | What workflow do you want to build? | Execution machinery | Polaris provides an opinionated investment decision lifecycle |

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

## Three central differentiators

The differentiation can be compressed into three durable ideas.

### Durable decisions

> **The decision persists as a lifecycle.**

Decisions retain connected evidence, reasoning, authority, human judgment, external consequences, outcomes, and lessons over time.

### Trust by architecture

> **Trust comes from provenance and separation of powers, not model confidence alone.**

Evidence, rules, reasoning, human authority, external operational truth, and outcomes remain distinct and inspectable.

### Attentive intelligence

> **Past portfolio and decision context helps Polaris determine what matters next.**

Polaris can proactively investigate relevant change and remain quiet when nothing materially affects the user's decision context.

## Consequences

The Differentiation decision implies:

* the decision record and closed lifecycle should remain more durable than any particular interface or workflow implementation;
* Polaris should optimize for decision quality rather than analysis volume, recommendation count, or notification count;
* model improvements should improve Polaris without becoming the sole basis of its value proposition;
* challenge should remain structural even if internal reasoning architecture changes;
* portfolio context and risk must remain upstream of the final recommendation;
* evidence provenance and authority provenance are central trust mechanisms rather than optional audit metadata;
* human authority should coexist with substantial proactive analytical autonomy;
* external execution should remain connected to decisions without becoming Polaris-controlled;
* outcome evaluation should distinguish reasoning quality, policy effects, human decisions, execution effects, and realized results;
* historical evaluation should preserve what was knowable at decision time;
* stale decision context should reduce or invalidate confidence in a current recommendation rather than being hidden;
* calm selectivity should be treated as a product strength;
* generic infrastructure and AI features remain subordinate to the domain decision system;
* differentiation should be evaluated as a coherent system property rather than a feature checklist.

## Relationship to later Product Definition work

This Differentiation decision establishes constraints for the remaining Product Definition work:

* **Core Capabilities** should identify the smallest coherent capability set required to produce these differentiating system behaviors rather than reproduce every existing subsystem or future-feature idea.
* **Product Principles** should compress the most durable behavioral rules behind closed-loop decisions, trust by architecture, attentiveness, portfolio context, challenge, human authority, historical integrity, and calm selectivity.
