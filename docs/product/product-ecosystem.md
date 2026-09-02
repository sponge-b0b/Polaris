# Polaris Product Ecosystem Position

**Status:** In progress  
**Purpose:** Preserve the reasoning behind Polaris's place in the investment technology stack, the specialist systems it complements rather than replaces, and the temporal contract implied by operating at portfolio decision speed rather than execution speed.

This document refines the Product Identity recorded in [`product-definition.md`](./product-definition.md). It is not a separate product identity or a premature Scope Boundaries specification. It records the ecosystem and timing implications of defining Polaris as an attentive portfolio decision system.

## Decision

Polaris occupies the **decision layer between investment information systems and investment action systems**.

Information and observation systems primarily establish what is happening or what is true. Polaris determines what the information means for a particular portfolio, what deserves attention, which existing assumptions or decisions may have changed, and what action should be considered. The human remains the consequential decision authority. Brokerage, trading, execution, accounting, and other operational systems retain responsibility for carrying out and recording the responsibilities they specialize in.

A useful conceptual model is:

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

This is a responsibility model rather than a claim that the systems are physically isolated. Polaris may ingest market data directly, show charts relevant to a decision, receive account state from a broker, or project a recommendation into another tool. Integration does not make those specialist responsibilities part of Polaris's defining product contract.

## Why this position matters

A sophisticated individual or small investment team already operates within an ecosystem of specialized software. Trying to replace every system would turn Polaris into a market-data terminal, charting workstation, research platform, portfolio-accounting system, brokerage stack, execution engine, quantitative-research environment, and general-purpose AI assistant at the same time.

That would directly conflict with the accepted Product Identity:

> **Decision system > investment intelligence > product platform.**

Polaris should instead become exceptionally good at the layer those systems usually leave to the human: connecting current evidence to portfolio context, active theses, risk, previous decisions, alternatives, and future evaluation.

## Systems Polaris complements

### Brokers, trading platforms, and execution systems

These systems are responsible for responsibilities such as:

* live order entry;
* order routing;
* fills and execution status;
* stops and limit orders;
* broker connectivity;
* buying power and account controls;
* immediate operational position state;
* broker-enforced or execution-time controls.

Polaris should not sit in the low-latency critical path between a market event and an already-authorized order action.

The intended relationship is:

```text
Polaris:
"This is what I recommend and why."

Human:
"This is what we will do."

Trading / execution system:
"This is how the authorized action is carried out."
```

Execution does not end the Polaris lifecycle. Resulting fills and portfolio state should flow back into the decision context so Polaris can observe what actually happened, preserve the human action separately from its recommendation, and continue later evaluation.

### Market-data and charting systems

Specialist systems may provide:

* high-frequency quotes;
* deep charting and drawing tools;
* order flow and market depth;
* scanners;
* specialized indicators;
* low-latency visual market inspection.

Polaris needs current market evidence and may provide decision-relevant visualizations, but it does not need to reproduce every specialist market-data or charting capability.

The distinction is:

> Market-data and charting systems help the user inspect **what is happening**. Polaris determines **which evidence materially matters to the portfolio decision and what it implies**.

### News and research services

A news or research service can optimize for comprehensive information discovery and access.

Polaris should not optimize for showing the user every story. Its job is to determine which new information materially changes a portfolio condition, active thesis, assumption, risk, recommendation, or open decision.

The distinction is therefore:

```text
News / research system:
"Here is the information available."

Polaris:
"Here is the information that changes something we currently care about,
what it changes, and what decision now deserves attention."
```

### Portfolio accounting and books-and-records systems

Polaris requires trustworthy portfolio state in order to reason about exposure, concentration, risk, alternatives, and consequences.

That does not imply ownership of:

* official books and records;
* reconciliation;
* settlement;
* tax lots;
* official NAV;
* custody records;
* transaction accounting;
* every operational portfolio state transition.

Where an authoritative portfolio or accounting system exists, Polaris should consume the state necessary for decision support rather than duplicate the operational system of record without a product reason.

### Quantitative-research and simulation environments

Polaris may need backtesting, simulation, historical analog analysis, and other quantitative evidence where those capabilities help form or evaluate decisions.

It does not automatically follow that Polaris should become a completely general quantitative-programming environment for arbitrary systematic strategy development.

The relevant test is:

> Does this analytical capability materially support the Polaris decision lifecycle or its evaluation?

### General-purpose AI tools

Users may continue to use general-purpose AI systems for open-ended research, writing, exploration, coding, or broad reasoning.

Polaris does not differentiate itself merely by having access to an LLM. Its stronger contract is that reasoning occurs in the presence of durable portfolio state, active decision context, attributable evidence, risk, governance, historical decisions, and evaluation memory.

General-purpose AI may answer an investment question. Polaris should know **why this question matters now, what prior decisions it affects, what portfolio it applies to, and whether the resulting recommendation remains trustworthy later**.

### Communication and reporting systems

Email, messaging, document, dashboard, API, and other distribution systems may remain the best way to deliver information to particular people or workflows.

Polaris should be able to project durable decision state into those surfaces without turning distribution into the product identity.

## What Polaris intentionally does not compete on

Polaris should not make product strategy depend on winning at:

* lowest-latency market data;
* exchange-speed decisioning;
* order routing or execution speed;
* chart customization breadth;
* comprehensive real-time news presentation;
* official portfolio accounting or tax accounting;
* generalized quantitative-programming flexibility;
* general-purpose chatbot breadth.

This does not prohibit useful supporting features in these areas. It means those features must serve the portfolio decision system rather than become independent competitive centers.

Polaris should compete on:

> **Taking sufficiently current and trustworthy evidence from the surrounding ecosystem, understanding what materially matters to this portfolio and its ongoing decisions, preparing a risk-aware and explainable recommendation, involving the human at the correct authority boundary, and preserving the decision lifecycle afterward.**

## The temporal contract

Describing Polaris as simply "real-time" or "not real-time" is misleading.

Three conceptual clocks clarify the product boundary.

### Market time

```text
microseconds → milliseconds → seconds
```

This is the domain of:

* exchange matching;
* streaming quotes;
* order routing;
* stops;
* low-latency execution;
* automated market-response controls.

This is **not Polaris's design center**.

### Decision time

```text
seconds → minutes
```

This is the domain of questions such as:

* Did something materially change?
* Which portfolio decisions or assumptions are affected?
* Is the prior recommendation still current?
* How did portfolio risk change?
* What action should now be considered?

This **is core Polaris territory**.

### Analytical time

```text
minutes → hours → days
```

This includes:

* deeper research;
* strategy review;
* historical evaluation;
* simulation;
* retrospective learning;
* long-form synthesis.

This is also Polaris territory.

The resulting temporal product rule is:

> **Polaris operates at decision time, not trading-engine time. It should remain current enough to detect and reason about material changes before presenting consequential portfolio recommendations, while leaving low-latency market execution to systems designed for that purpose.**

## Major market shock example

A sudden 15% decline in the S&P 500 is a useful boundary test.

### What the trading and execution stack does

Any existing:

* stop orders;
* limit orders;
* orders already in flight;
* broker risk controls;
* execution instructions;

must continue to operate according to the trading platform's guarantees and latency characteristics.

Polaris should not insert an LLM-mediated reasoning cycle into that critical path.

### What Polaris does

The shock should cause Polaris to ask whether existing decision context has become stale or materially wrong.

A mature response should conceptually proceed as follows:

```text
Broad market shock
        ↓
Materiality triage
        ↓
Which portfolios / theses / decisions are exposed?
        ↓
Which assumptions, risk conditions, or recommendations may now be stale?
        ↓
Refresh required market + portfolio + risk + contextual evidence
        ↓
Reassess affected decisions
        ↓
Surface prepared decision work
        ↓
Human judgment
```

Polaris may conclude that the appropriate action is to reduce risk, add exposure, wait, hedge where applicable, or do nothing. The market move itself does not predetermine the recommendation.

A representative interaction is closer to:

> The market decline materially affects three active portfolio decisions. I reassessed them. One prior recommendation is now stale, one thesis remains intact, and one position now exceeds its intended risk contribution. The following decision deserves your attention first.

That is materially different from both a raw market alert and an autonomous trading system.

## Two-speed response

During rapidly evolving conditions, full reasoned analysis may take longer than deterministic recognition that existing decision context is unsafe to reuse.

Polaris can therefore conceptually support two response speeds:

```text
FAST DETERMINISTIC TRIAGE
        ↓
Material shock detected
Affected decisions identified
Stale assumptions / breached conditions exposed
Prior recommendations prevented from masquerading as current
        ↓

REASONED DECISION REASSESSMENT
        ↓
Updated evidence
Portfolio consequences
Alternatives and challenge
Risk-aware recommendation
        ↓
Human judgment
```

This is not a commitment to a particular implementation architecture. It is a product requirement that responsiveness and trustworthiness should not require pretending AI can reason at exchange-engine speed.

## Freshness as part of trustworthiness

A recommendation is only as current as the evidence required by the decision it supports.

"Fresh" is contextual.

A slow-moving macro decision may remain trustworthy with evidence updated on a daily or release cadence. A recommendation during a fast market dislocation may require market and portfolio state updated within seconds or minutes.

Polaris should therefore preserve enough temporal provenance to answer questions such as:

```text
How current is the portfolio state?
How current is the market state?
Which economic release is being used?
When was relevant research or news refreshed?
When was this recommendation formed?
Has a material event occurred since then?
```

The exact interface is not yet defined. The durable rule is:

> **Freshness requirements belong to the decision contract, not to a single universal system-wide definition of real time.**

## Stale evidence can invalidate a recommendation

Freshness metadata should not be decorative.

If a decision requires current portfolio state and the authoritative portfolio source is stale beyond the tolerable decision window, Polaris may need to say:

> I cannot presently support a current portfolio recommendation because the required portfolio state is stale.

Likewise, a material market event may invalidate a previously sound recommendation even if the underlying record is preserved correctly.

Polaris should be able to distinguish:

* historically valid recommendation evidence;
* still-current recommendation evidence;
* stale or superseded decision context;
* insufficiently fresh evidence to form a trustworthy new recommendation.

That distinction is a direct consequence of treating trustworthiness as a product concern.

## Feedback after action

The ecosystem relationship is not a one-way handoff.

```text
Polaris recommendation
        ↓
Human decision
        ↓
Trading / operational system
        ↓
Execution or state change
        ↓
Updated portfolio / account state
        ↓
Polaris observes the result
        ↓
Decision record continues
        ↓
Outcome → evaluation → learning
```

Polaris therefore works alongside execution systems without becoming one. The action system performs the authorized operational change; Polaris continues the decision lifecycle around the resulting state.

## Consequences

This ecosystem and temporal position implies:

* Polaris should integrate well with specialist data, research, portfolio-state, brokerage, execution, and distribution systems rather than assume it must replace them;
* specialist integration does not make specialist functionality part of Polaris's product identity;
* Polaris must not become a low-latency execution dependency for already-authorized market actions;
* immediate market mechanics and broker controls belong to execution systems;
* Polaris must react quickly enough to recognize when material change invalidates assumptions, risk conditions, or prior recommendations;
* prior recommendations must not be presented as current when relevant decision context has become stale;
* market and portfolio freshness should be decision-appropriate and inspectable;
* critical stale evidence may require degrading, withholding, or invalidating a recommendation;
* deterministic triage may precede slower reasoned reassessment during fast-moving conditions;
* market shocks should trigger selective reassessment of affected decision state rather than indiscriminate re-analysis of everything;
* the human remains the bridge from Polaris's recommendation to consequential portfolio action;
* resulting execution and portfolio state should flow back into Polaris so the decision lifecycle can continue through evaluation and learning;
* "real-time" should be discussed in terms of decision latency and evidence freshness rather than exchange-engine latency.

## Relationship to later Product Definition work

This record intentionally does not settle every Scope Boundary or Authority Model question.

It does establish constraints those later decisions should respect:

* **Authority Model** must distinguish analytical initiative from authority to act on capital and should account for deterministic fast-path protections when decision evidence becomes stale.
* **Scope Boundaries** should formalize which adjacent system responsibilities Polaris excludes, integrates with, or supports only as subordinate features.
* **Core Capabilities** should include whatever is required to maintain decision-appropriate context and freshness without treating market-data or execution infrastructure as ends in themselves.
* **Product Principles** should capture the relationship between trustworthiness, staleness, calm selectivity, and decision-time responsiveness.
