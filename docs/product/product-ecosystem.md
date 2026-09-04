# Polaris Product Ecosystem Position

**Status:** In progress  
**Purpose:** Preserve the reasoning behind Polaris's place in the investment technology stack, the specialist systems it complements rather than replaces, and the temporal contract implied by operating at portfolio decision speed rather than execution speed.

This document refines the Product Identity recorded in [`product-definition.md`](./product-definition.md). It is not a separate product identity or a premature Scope Boundaries specification. It records the ecosystem and timing implications of defining Polaris as an attentive portfolio decision system.

## Decision

Polaris occupies the **decision layer between investment information systems and investment action systems**.

Information and observation systems primarily establish the external facts for which they are authoritative. Polaris determines what those facts mean for a particular Portfolio, what deserves Attention, which Investment Assumptions, Investment Theses, Investment Recommendations, Review Conditions, or unresolved Investment Decisions may be affected, and what Decision Alternatives should be considered. The applicable Investment Authority Regime governs consequential human authority. Brokerage, trading, execution, accounting, and other operational systems retain responsibility for carrying out and recording the operational responsibilities they specialize in.

A useful conceptual model is:

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

This is a responsibility model rather than a claim that the systems are physically isolated. Polaris may ingest market data directly, show charts relevant to an Investment Decision, receive account state from a broker, or present an Investment Recommendation through another tool. Integration does not make those specialist responsibilities part of Polaris's defining product contract.

## Why this position matters

A sophisticated individual or small investment team already operates within an ecosystem of specialized software. Trying to replace every system would turn Polaris into a market-data terminal, charting workstation, research platform, portfolio-accounting system, brokerage stack, execution engine, quantitative-research environment, and general-purpose AI assistant at the same time.

That would directly conflict with the accepted Product Identity:

> **Decision system > investment intelligence > product platform.**

Polaris should instead become exceptionally good at the layer those systems usually leave to the human: connecting current Evidence to Portfolio State, active Investment Theses, Portfolio Risk, previous Investment Decisions, Decision Alternatives, and future Decision Evaluation.

## Systems Polaris complements

### Brokers, trading platforms, and execution systems

These systems are responsible for responsibilities such as:

* live Order entry;
* Order routing;
* fills and execution status;
* protective and limit Orders;
* broker connectivity;
* buying power and account controls;
* immediate operational Position state;
* broker-enforced or execution-time controls.

Polaris should not sit in the low-latency critical path between a market event and an already-authorized Order action.

The intended relationship is:

```text
Polaris:
"This is what I recommend and why."

Human:
"This is the Human Investment Decision."

Trading / execution system:
"This is how the externally authorized action is carried out."
```

Execution does not end the Polaris lifecycle. Resulting fills and Portfolio State should flow back as authoritative external Evidence so Polaris can preserve what actually happened, keep Human Investment Decision separate from Investment Recommendation, reconcile Action Intent where one exists, and continue later Decision Evaluation.

### Market-data and charting systems

Specialist systems may provide:

* high-frequency quotes;
* deep charting and drawing tools;
* order flow and market depth;
* scanners;
* specialized indicators;
* low-latency visual market inspection.

Polaris needs current market Evidence and may provide decision-relevant visualizations, but it does not need to reproduce every specialist market-data or charting capability.

The distinction is:

> Market-data and charting systems help the user inspect **what is happening**. Polaris determines **which Evidence is Investment Relevant and material to the Portfolio decision and what it implies**.

### News and research services

A news or research service can optimize for comprehensive information discovery and access.

Polaris should not optimize for showing the user every story. Its job is to determine which new information materially changes Portfolio State, an Investment Thesis, Investment Assumption, Portfolio Risk, Investment Recommendation, Review Condition, or unresolved Investment Decision.

The distinction is therefore:

```text
News / research system:
"Here is the information available."

Polaris:
"Here is the information that materially changes something we currently care about,
what it changes, and whether Attention now identifies a Decision Need."
```

### Portfolio accounting and books-and-records systems

Polaris requires trustworthy Portfolio State in order to reason about Exposure, concentration, Portfolio Risk, Decision Alternatives, and Projected Portfolio Consequences.

That does not imply ownership of:

* official books and records;
* settlement;
* tax lots;
* official NAV;
* custody records;
* transaction accounting;
* every operational Portfolio State transition.

Where an authoritative portfolio or accounting system exists, Polaris should consume the state necessary for decision support rather than silently treating an internal copy or expectation as an equally authoritative operational fact.

### Quantitative-research and simulation environments

Polaris may need Backtests, Investment Simulations, historical analog analysis, and other quantitative Evidence where those capabilities help form, challenge, or evaluate Investment Decisions or investment methods.

It does not automatically follow that Polaris should become a completely general quantitative-programming environment for arbitrary systematic strategy development.

The relevant test is:

> Does this analytical capability materially support the Polaris decision lifecycle or its Decision Evaluation?

### General-purpose AI tools

Users may continue to use general-purpose AI systems for open-ended research, writing, exploration, coding, or broad reasoning.

Polaris does not differentiate itself merely by having access to an LLM. Its stronger contract is that reasoning occurs in the presence of Durable Decision Memory, Portfolio State, Decision Context, attributable Evidence, Portfolio Risk, Governance, historical Investment Decisions, and Decision Evaluation.

General-purpose AI may answer an investment question. Polaris should know **why this question matters now, what prior judgments or decisions it affects, which Portfolio it applies to, and whether the resulting Investment Recommendation is currently supportable later**.

### Communication and reporting systems

Email, messaging, document, dashboard, API, and other distribution systems may remain the best way to deliver information to particular people or workflows.

Polaris should be able to present shared decision state through those surfaces without turning distribution into the product identity or allowing each surface to reconstruct independent semantics.

## What Polaris intentionally does not compete on

Polaris should not make product strategy depend on winning at:

* lowest-latency market data;
* exchange-speed decisioning;
* Order routing or execution speed;
* chart customization breadth;
* comprehensive real-time news presentation;
* official portfolio accounting or tax accounting;
* generalized quantitative-programming flexibility;
* general-purpose chatbot breadth.

This does not prohibit useful supporting features in these areas. It means those features must serve the portfolio decision system rather than become independent competitive centers.

Polaris should compete on:

> **Taking sufficiently current and trustworthy Evidence from the surrounding ecosystem, understanding what is Investment Relevant and material to this Portfolio and its ongoing decisions, preparing a Portfolio-Risk-aware and explainable Investment Recommendation, preserving the applicable authority boundary, and maintaining Durable Decision Memory afterward.**

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
* Order routing;
* protective Orders;
* low-latency execution;
* automated market-response controls.

This is **not Polaris's design center**.

### Decision time

```text
seconds → minutes
```

This is the domain of questions such as:

* Did something materially change?
* Which Portfolios, Investment Theses, Review Conditions, or Investment Decisions are affected?
* Is a prior Investment Recommendation still currently supportable?
* How did Portfolio Risk change?
* Does Attention establish or renew a Decision Need?

This **is core Polaris territory**.

### Analytical time

```text
minutes → hours → days
```

This includes:

* deeper research;
* Investment Strategy review;
* historical Decision Evaluation;
* Investment Simulation;
* retrospective learning;
* long-form synthesis.

This is also Polaris territory.

The resulting temporal product rule is:

> **Polaris operates at decision time, not trading-engine time. It should remain current enough to detect and reason about Investment-Relevant material changes before presenting consequential Investment Recommendations, while leaving low-latency market execution to systems designed for that purpose.**

## Major market shock example

A sudden 15% decline in the S&P 500 is a useful boundary test.

### What the trading and execution stack does

Any existing:

* protective Orders;
* limit Orders;
* Orders already in flight;
* broker risk controls;
* execution instructions;

must continue to operate according to the trading platform's guarantees and latency characteristics.

Polaris should not insert an LLM-mediated reasoning cycle into that critical path.

### What Polaris does

The shock should cause Attention to ask whether existing Decision Context has become stale, whether prior judgments remain currently supportable, and whether a Decision Need exists for an affected Portfolio-relevant investment matter.

A mature response should conceptually proceed as follows:

```text
Broad market shock
        ↓
Investment Relevance / Materiality triage
        ↓
Which Portfolios / Investment Theses / decisions are exposed?
        ↓
Which Investment Assumptions, Portfolio Risks,
Review Conditions, or Investment Recommendations are affected?
        ↓
Refresh required market + Portfolio + contextual Evidence
        ↓
Attention determines unresolved or renewed decision work
        ↓
Reasoned reassessment
        ↓
Surface prepared decision work
        ↓
Human Investment Decision where required
```

Polaris may conclude that the appropriate Investment Recommendation is to reduce Portfolio Risk, add Exposure, wait, hedge where applicable, or do nothing. The market move itself does not predetermine the judgment.

A representative interaction is closer to:

> The market decline materially affects three investment matters. One prior Investment Recommendation is no longer currently supportable, one Investment Thesis remains intact, and one Position now creates greater Portfolio Risk than the prior judgment assumed. The following matter deserves Attention first.

That is materially different from both a raw market alert and an autonomous trading system.

## Two-speed response

During rapidly evolving conditions, full reasoned analysis may take longer than deterministic recognition that existing Decision Context is unsafe to reuse.

Polaris can therefore conceptually support two response speeds:

```text
FAST DETERMINISTIC TRIAGE
        ↓
Material shock detected
Affected investment matters identified
Stale Evidence / breached conditions exposed
Unsupported prior recommendations prevented from masquerading as current
        ↓

ATTENTION + REASONED REASSESSMENT
        ↓
Updated Evidence
Projected Portfolio Consequences
Decision Alternatives and challenge
Portfolio-Risk-aware Investment Recommendation
        ↓
Human Investment Decision where required
```

This is not a commitment to a particular implementation architecture. It is a product requirement that responsiveness and trustworthiness should not require pretending AI can reason at exchange-engine speed.

## Freshness as part of trustworthiness

A current Investment Recommendation is only as current as the Evidence required by the judgment and consequential use it supports.

"Fresh" is contextual.

A slow-moving macro judgment may remain supportable with Evidence updated on a daily or release cadence. An Investment Recommendation during a fast market dislocation may require market and Portfolio State updated within seconds or minutes.

Polaris should therefore preserve enough temporal provenance to answer questions such as:

```text
How current is the Portfolio State?
How current is the market state?
Which economic release is being used?
When was relevant research or news refreshed?
When was this Investment Recommendation formed?
Has a material event occurred since then?
```

The exact interface is not yet defined. The durable rule is:

> **Freshness Requirements belong to the investment use, not to a single universal system-wide definition of real time.**

## Stale Evidence affects current support, not historical existence

Freshness metadata should not be decorative.

If an Investment Decision requires current Portfolio State and the authoritative source is stale beyond the applicable Freshness Requirement, Polaris may need to say:

> I cannot presently support a current Portfolio recommendation because the required Portfolio State is stale.

A material market event may likewise make a previously reasonable Investment Recommendation no longer currently supportable. That does not erase or invalidate the historical fact that the prior judgment existed under its earlier Decision Context.

Polaris should be able to distinguish:

* the historical Investment Recommendation and the Evidence available when it was formed;
* whether that recommendation remains currently supportable;
* stale or changed current Decision Context;
* insufficiently fresh Evidence to form a trustworthy new Investment Recommendation.

That distinction is a direct consequence of treating trustworthiness and Judgment-Time Availability as product concerns.

## Feedback after action

The ecosystem relationship is not a one-way handoff.

```text
Investment Recommendation
        ↓
Human Investment Decision
        ↓
Action Intent where applicable
        ↓
Trading / operational system
        ↓
Authoritative external activity
        ↓
Updated Portfolio State
        ↓
Polaris observes / reconciles
        ↓
Durable Decision Memory continues
        ↓
Outcome → Decision Evaluation → Lessons
```

Polaris therefore works alongside execution systems without becoming one. The external action system performs the operational change; Polaris continues the decision lifecycle around the resulting state.

## Consequences

This ecosystem and temporal position implies:

* Polaris should integrate well with specialist data, research, Portfolio-State, brokerage, execution, and distribution systems rather than assume it must replace them;
* specialist integration does not make specialist functionality part of Polaris's product identity;
* Polaris must not become a low-latency execution dependency for already-authorized market actions;
* immediate market mechanics and broker controls belong to execution systems;
* Polaris must react quickly enough to recognize when material change affects Investment Assumptions, Portfolio Risk, Review Conditions, or current support for prior Investment Recommendations;
* prior Investment Recommendations must not be presented as currently supportable when relevant Decision Context or Evidence no longer supports them;
* market and Portfolio freshness should be use-appropriate and inspectable;
* critical stale Evidence may require qualifying or withholding a current Investment Recommendation or consequential use without rewriting history;
* deterministic triage may precede Attention and slower reasoned reassessment during fast-moving conditions;
* market shocks should trigger selective Attention to affected investment matters rather than indiscriminate re-analysis of everything;
* the human remains the attributable investment judgment boundary under the applicable Investment Authority Regime;
* resulting external activity and Portfolio State should flow back into Polaris so Durable Decision Memory can continue through Outcome, Decision Evaluation, and learning;
* "real-time" should be discussed in terms of decision latency and Evidence freshness rather than exchange-engine latency.

## Relationship to later Product Definition work

This record intentionally does not settle every Scope Boundary or Authority Model question.

It does establish constraints those later decisions should respect:

* **Authority Model** must distinguish analytical initiative, deterministic rule evaluation, power-specific human authority, and external execution authority.
* **Scope Boundaries** should formalize which adjacent system responsibilities Polaris excludes, integrates with, or supports only as subordinate features.
* **Core Capabilities** should include whatever is required to maintain use-appropriate Decision Context and freshness without treating market-data or execution infrastructure as ends in themselves.
* **Product Principles** should capture the relationship between trustworthiness, staleness, calm selectivity, and decision-time responsiveness.
