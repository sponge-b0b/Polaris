# Polaris Product Rationale

**Status:** In progress  
**Purpose:** Preserve the reasoning, alternatives, and consequences behind the durable decisions recorded in [`product-definition.md`](./product-definition.md).

This is a product decision record, not a transcript and not a feature backlog. Each section records the decision, why it was chosen, meaningful alternatives, and the consequences that should constrain later product and roadmap work.

## 1. Purpose

### Decision

Polaris exists to help humans make **better, more trustworthy portfolio and investment decisions**.

The product is not defined by performing financial analysis or by orchestrating AI workflows. Those are means. The center of gravity is the decision process: gathering relevant evidence, understanding it, exposing disagreement and uncertainty, applying risk and portfolio context, forming a recommendation, preserving the reasoning, and leaving consequential judgment with a human decision-maker.

A concise working thesis is:

> Polaris turns fragmented market, portfolio, research, risk, and model evidence into a repeatable decision process that produces explainable recommendations for human decision-makers. It preserves what the platform knew, what it concluded, why it concluded it, what uncertainty or disagreement existed, and enough durable evidence for the decision to be inspected, challenged, replayed, and evaluated later.

### Why decisions are the product center

Polaris can gather market data, calculate technical indicators, retrieve research, summarize news, reason about macro conditions, assess risk, run simulations, and generate reports. None of those activities independently justify the product.

The valuable chain is closer to:

```text
evidence
  ↓
understanding
  ↓
alternatives / disagreement
  ↓
risk
  ↓
judgment
  ↓
recommendation
  ↓
human decision
```

A system that accumulates large amounts of analysis without materially improving that chain becomes an expensive research dashboard. A useful discipline therefore follows:

> Analysis that does not contribute to a decision, explanation, evaluation, or durable knowledge should have to justify why Polaris contains it.

This is intentionally restrictive. It gives future roadmap and intake decisions a reason to reject attractive but product-irrelevant capabilities.

### Why trustworthiness matters

General-purpose LLMs can already answer questions such as "Should I buy SPY?" Producing another unconstrained answer is not a meaningful reason for Polaris to exist.

The harder and more valuable questions are:

* What did the system know at the time?
* Which evidence did it use?
* Which evidence materially affected the conclusion?
* Where did sources, agents, or models disagree?
* What assumptions were made?
* Which risk constraints applied?
* Why was the recommendation produced?
* Can the decision be reproduced or replayed where the underlying process is deterministic enough to permit it?
* What happened afterward?
* Was the reasoning useful or misleading?
* Can the decision still be audited months later?

This reframes several existing Polaris mechanisms. Runtime evidence, persistence, replay, governance, evaluation, curated knowledge, provenance, observability, and deterministic simulation are not independent product features competing for attention. They are mechanisms that can make a recommendation more trustworthy.

A strong product principle suggested by this reasoning is:

> A financial recommendation that cannot be explained, inspected, challenged, and evaluated is not trustworthy enough for Polaris.

The exact wording may evolve when Product Principles are formally defined, but the underlying constraint should remain.

### Why AI is not the governing authority

A naive AI-finance architecture would collapse the system into:

```text
data → large model → answer
```

Polaris should deliberately resist that shape.

The preferred conceptual model is closer to:

```text
deterministic data and services
        ↓
typed / attributable evidence
        ↓
specialized reasoning and synthesis
        ↓
risk and governance constraints
        ↓
recommendation
        ↓
human authority
```

AI is valuable where interpretation, synthesis, comparison, and reasoning are useful. Deterministic software is preferable where explicit rules, invariants, reproducibility, accounting, validation, and guarantees matter. Human judgment should remain authoritative for consequential investment decisions.

This leads to another durable product idea:

> Use AI selectively to improve investment reasoning while making the surrounding decision system more deterministic, inspectable, and accountable than the AI itself.

That is a materially different philosophy from maximizing AI autonomy.

### Why portfolio context is central

Polaris should not behave like a collection of isolated security scorers.

The relevant question is not merely:

> Is this asset bullish?

It is closer to:

> What does this opportunity mean given the current portfolio, market regime, risk, existing exposure, alternative opportunities, time horizon, and strategy?

Portfolio context gives research and analysis a decision frame. It also distinguishes Polaris from generic market-analysis assistants and stock-picking chatbots.

The word "portfolio" may still be refined as the product definition develops, but portfolio-level decision context is currently considered load-bearing.

### Why trading and execution do not define the product

Earlier Polaris planning explored a progression toward trading and execution. That is not currently considered the product center.

The more coherent boundary is recommendation-oriented decision support with human authority. Execution may be adjacent to a user's workflow, but making automated order placement part of Polaris's identity would introduce a different class of latency, brokerage, operational-risk, compliance, and control requirements.

The product should therefore not be defined as an autonomous trading system merely because execution is technically possible.

### Alternatives considered

#### Financial analysis platform

This framing is too weak because it makes analysis itself the endpoint. It does not explain why Polaris needs durable evidence, replay, governance, evaluation, or portfolio-level synthesis, and it provides little protection against adding endless analytical features.

#### AI-agent platform for finance

This framing describes an implementation technique rather than a user outcome. It would also invite Polaris to become a generic agent framework, causing runtime and orchestration capabilities to compete with the investment product for identity.

The runtime may be sophisticated and reusable without becoming the product.

#### Investment intelligence platform

This is plausible and usefully broad. It accommodates research, analysis, risk, strategy, and portfolio recommendations. Its weakness is that "intelligence" can become vague enough to include almost anything.

#### Portfolio decision-support platform

This is the strongest current center of gravity. It defines a concrete endpoint—portfolio decisions—while allowing research, market intelligence, risk, simulation, retrieval, reporting, and workflow automation to serve that endpoint.

#### AI-native investment operating system

This framing is conceptually attractive because Polaris may eventually coordinate research, decisions, knowledge, evaluation, governance, reporting, and automation. It is currently rejected as the primary framing because "operating system" creates an easy justification for expanding into every adjacent investment function.

### Consequences

The Purpose decision implies:

* product capabilities should be evaluated by their contribution to decision quality, trustworthiness, explanation, evaluation, or durable knowledge;
* analysis is not automatically valuable merely because it can be produced;
* replay, evidence, governance, evaluation, and provenance should be understood as trust mechanisms;
* AI autonomy is subordinate to the integrity of the decision system;
* portfolio context is more important than isolated signal generation;
* autonomous brokerage execution is not part of the product's defining purpose;
* the implementation should be able to evolve without changing this product thesis.

## 2. Users

### Decision

Polaris primarily serves **sophisticated individual portfolio decision-makers and small investment teams practicing discretionary, process-driven portfolio management**.

The primary user already has responsibility for investment decisions and wants a more systematic, evidence-driven, explainable, and repeatable way to make them.

The user is defined by **decision responsibility**, not by a particular job title or organization type.

### Why "serious" or sophisticated decision-makers

Polaris should not be designed primarily for a novice asking:

> What stock should I buy?

That user needs education, simplification, and a different level of advisory guardrails.

The intended Polaris user already understands concepts such as:

* risk;
* exposure;
* drawdown;
* time horizon;
* portfolio construction;
* uncertainty;
* the limitations of forecasts and models.

Polaris is intended to improve their reasoning process rather than substitute for basic financial literacy.

### Why decision responsibility matters more than title

The intended user may call themselves an investor, trader, analyst, portfolio manager, fund manager, or something else. Those labels are secondary.

The common responsibility is:

> Given the available evidence and the current portfolio context, decide what should be done.

This keeps the product centered on the job rather than forcing an artificial market category such as "hedge funds" or "retail traders."

### Why one operator through a small team

Polaris should not be defined as a single-user personal investing application, but it also should not begin by modeling the organizational complexity of a large institution.

The preferred design center is:

> One sophisticated decision-maker through a small collaborative investment team.

At the simplest level, one person may wear every role:

```text
Portfolio Manager
Researcher
Risk Reviewer
Platform Operator
        ↓
      Polaris
```

As usage grows, those responsibilities may separate:

```text
Portfolio Manager ─┐
Analyst ────────────┤
Risk Reviewer ──────┼── Polaris
Researcher ─────────┤
Platform Operator ──┘
```

The product should not require those roles to be separate in order to be useful. This permits a natural maturity path without prematurely adding enterprise role and permission complexity.

### User versus operator

Current Polaris operation may require substantial technical competence. That does not mean "developer" should be the product persona.

Two questions must remain separate:

**Who receives value from Polaris?**  
The portfolio decision-maker and investment team.

**Who installs, configures, integrates, and operates Polaris?**  
Initially, likely a technically capable user; later, possibly a dedicated operator or increasingly automated deployment tooling.

Technical operation is therefore a maturity and delivery concern, not product identity.

This distinction will matter when later evaluating interfaces such as CLI, MCP, API, and web UI.

### Why a repeatable investment process matters

The strongest-fit Polaris user does not want an AI oracle. They either have or want to develop a repeatable investment process.

Their desired interaction is closer to:

> Gather the relevant evidence, apply the process, challenge the conclusion, account for portfolio and risk context, explain the recommendation, preserve the evidence, and later help evaluate whether the reasoning was good.

That expectation aligns naturally with Polaris's emphasis on decision evidence, replay, evaluation, and governance.

### Not primary users

#### Beginner retail investors

They require a more educational and advisory product centered on simplification and foundational guidance rather than sophisticated decision support.

#### Passive buy-and-hold investors

Their recurring decision complexity is usually too low to justify the full Polaris decision process as a primary product need.

#### High-frequency or latency-sensitive traders

Their defining requirements include low latency, streaming market microstructure, execution quality, and rapid automated response. Optimizing Polaris around those needs would distort the product.

#### Fully autonomous or systematic trading operations

Their primary need is algorithmic strategy and execution infrastructure rather than human-centered discretionary decision support.

#### Large institutional investment organizations

They may eventually benefit from Polaris, but designing for them now would make enterprise identity, authorization, compliance, integration, organizational workflow, and operating complexity dominate the product before the core decision-support experience is mature.

#### Developers seeking a generic AI platform

Polaris may contain reusable runtime and workflow technology, but those mechanisms should not redefine the product as a general-purpose AI framework.

### SPY and swing trading as origins, not doctrine

SPY and swing trading are valuable reference use cases because they provide a concrete investment process against which to build and test the platform.

They should not currently be treated as permanent product constraints.

A more durable boundary is discretionary portfolio decision-making over investment horizons where research, synthesis, portfolio context, risk, and human judgment materially matter.

That does not imply support for every asset class, every strategy, or every time horizon. Those boundaries remain to be defined through later product and capability work.

### Alternatives considered

#### Retail investing application

Rejected as the primary identity because it would require a beginner-oriented user experience, educational framing, stronger simplification, and a different product promise.

#### Hedge-fund platform

Too organization-specific. The product should be defined by the decision job rather than by whether the user operates a hedge fund.

#### Institutional portfolio-management platform

Potentially compatible with a distant future, but too broad and operationally heavy as the present design center.

#### Developer platform

Rejected as the user identity. Current technical operation does not make developers the people for whom the investment product exists.

#### Sophisticated individual only

Too narrow. It would unnecessarily bake single-user assumptions into the product and make later collaboration harder even though the underlying decision process naturally supports a small team.

### Consequences

The Users decision implies:

* Polaris should optimize first for sophisticated discretionary decision-making, not beginner education;
* one user must be able to operate the complete product without enterprise organizational machinery;
* small-team collaboration should remain a natural extension rather than a future architectural rewrite;
* technical installation requirements should not be confused with the target user's identity;
* enterprise identity/access/compliance features must justify themselves against actual roadmap needs rather than being assumed because financial institutions exist;
* latency-sensitive execution and fully autonomous trading should not drive architecture or roadmap priorities;
* SPY and swing trading may remain strong reference scenarios without becoming universal product constraints;
* generic runtime features must justify their value to Polaris rather than turning Polaris into a general-purpose AI platform.

## 3. Problems / Jobs to Be Done

### Decision

Polaris is hired to help a portfolio decision-maker **turn fragmented and uncertain evidence into a reasoned, risk-aware portfolio decision; understand and defend that decision; preserve what was known and why the recommendation was made; and evaluate the decision process afterward so future decisions can improve**.

The product supports an investment decision cycle rather than a single analytical task. Its value is not measured by how many analyses, recommendations, or trades it produces. A valid outcome may be to act, wait, reduce, add, rebalance, hedge where appropriate, or deliberately do nothing.

The primary job can be expressed as:

> Given an uncertain and changing investment environment, help me determine what—if anything—I should do with my portfolio, why I should do it, what could make that judgment wrong, and whether the decision process proved useful afterward.

### Why the job is a decision cycle

A serious investment decision is not complete when a system emits a directional label, score, or confidence value.

The useful sequence is closer to:

```text
What is happening?
        ↓
What matters?
        ↓
What does it mean for this portfolio?
        ↓
What are the plausible interpretations?
        ↓
What could go wrong?
        ↓
What actions are reasonable?
        ↓
Which action is preferred, and why?
        ↓
What evidence would invalidate that view?
        ↓
Human decision
        ↓
What happened afterward?
        ↓
What should we learn?
```

This makes decision quality—not recommendation activity—the product objective.

### The six durable jobs

#### 1. Understand the current decision context

The user needs to turn fragmented market conditions, macro information, news, sentiment, technical evidence, portfolio state, exposure, prior decisions, and relevant historical knowledge into a coherent picture of **what matters now**.

The fundamental problem is not lack of data. It is fragmentation, noise, contradictory evidence, changing conditions, and limited human attention.

#### 2. Develop and challenge an investment view

The user needs to move from a collection of facts to a reasoned interpretation.

Polaris should help expose:

* plausible competing explanations;
* material disagreement;
* uncertainty;
* assumptions;
* evidence that would weaken or invalidate the leading thesis.

The purpose is not artificial debate for its own sake. The purpose is to prevent a plausible first explanation from becoming an unquestioned conclusion.

#### 3. Translate the view into portfolio consequences

An investment thesis is not yet a portfolio decision.

The user needs to understand what the evidence means in the context of:

* existing positions;
* concentration;
* exposure;
* risk tolerance and constraints;
* strategy;
* time horizon;
* competing opportunities.

The same bullish conclusion may rationally imply adding exposure, holding, changing another position, reducing risk elsewhere, or doing nothing depending on portfolio context.

#### 4. Choose among actions under explicit risk

The user needs a recommendation that makes reasonable choices and tradeoffs visible rather than simply producing a directional answer.

Potential choices may include acting, waiting, reducing, adding, rebalancing, hedging where applicable, or remaining unchanged.

Risk must influence the recommendation itself. It should not be reduced to a final compliance stamp saying that an otherwise independent recommendation is approved. Polaris should make clear what risk changed about the preferred action and what conditions would change the recommendation.

#### 5. Understand, communicate, and defend the decision

The user needs to answer **why** without reconstructing the entire analysis from memory.

Polaris should preserve enough of the decision context to make the result inspectable by the same decision-maker later or understandable to another member of the investment team. Relevant material includes evidence, assumptions, disagreement, constraints, reasoning, recommendation, and uncertainty.

This is not merely a reporting job. Explanation is part of making the decision trustworthy.

#### 6. Learn from decisions over time

The user needs to revisit previous decisions and ask:

* What did we know at the time?
* What did we believe?
* Which assumptions proved wrong?
* Was the recommendation reasonable given what was knowable then?
* Were particular signals, sources, models, reasoning patterns, or strategies consistently useful or misleading?
* What should change in the future decision process?

This is broader than backtesting a price rule. The job is to improve the **decision process itself**.

It closes the loop from one decision into better future decisions.

### Cognitive fragmentation as a core problem

A serious portfolio decision-maker may use a brokerage platform, market-data tools, economic calendars, news feeds, research notes, spreadsheets, charts, LLM conversations, portfolio records, simulation tools, PDFs, bookmarks, and personal memory.

The problem is not simply that these tools are separate. The deeper problem is that **decision context is fragmented across them**.

The human must mentally connect questions such as:

> What does this new macro evidence mean relative to the technical setup, the current portfolio exposure, the prior thesis, research reviewed weeks ago, the present risk environment, and a recommendation made under similar conditions in the past?

General-purpose LLMs can help with fragments of this work, but they do not by themselves establish durable authoritative context, a stable investment process, portfolio state, reproducible evidence, governance, or historical decision memory.

The resulting product problem is:

> Investment decisions are often made from fragmented evidence without a durable system connecting what was known, how it was interpreted, what action followed, and what was learned afterward.

Polaris should close that chain rather than merely add another analytical surface.

### The closed decision loop

Without durable follow-through, the product degenerates into:

```text
analyze → recommend → forget
```

The desired product loop is:

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

This loop explains why persistence, replay, evaluation, historical knowledge, and related mechanisms can be product-relevant. They allow Polaris to learn from the lifecycle of decisions rather than treating every run as an isolated event.

### Decision record as a product concept

A completed Polaris decision process should leave durable evidence that can be inspected over time.

The working product concept is a **decision record** containing or linking the meaningful lifecycle context as it becomes available:

```text
Decision context
Evidence
Interpretations
Disagreement
Uncertainty
Risk
Alternatives
Recommendation
Reasoning
Human decision
Subsequent outcome
Evaluation
Lessons
```

This does not yet prescribe a database entity, runtime object, document format, API schema, or user-interface artifact. `Decision record` is product language: it describes the durable thing the user should be able to revisit even if the underlying implementation spans multiple artifacts.

That distinction is intentional. "Persisted workflow run" is an architectural concept; "decision record" describes user value.

### Jobs that do not define Polaris

Users do not primarily hire Polaris to:

* obtain raw market data;
* draw charts;
* screen thousands of securities;
* execute brokerage orders;
* manage brokerage accounts;
* build arbitrary AI workflows;
* use an unrestricted financial chatbot;
* consume financial news;
* generate attractive reports or PDFs.

Some of these may be useful supporting capabilities. Their inclusion must be justified by their contribution to the decision cycle, explanation, evaluation, or durable knowledge.

For example, news ingestion is useful when it improves decision context; building a world-class standalone news reader would not automatically follow. Backtesting is useful when it evaluates strategy, reasoning, or recommendation behavior; building a generic quantitative-research framework would not automatically follow.

### Product shorthand

The six jobs can be summarized as:

> **Understand → Challenge → Apply portfolio context → Decide under risk → Explain → Learn**

Together with Purpose and Users, the emerging product logic is:

```text
WHO?
Sophisticated individual portfolio decision-makers
and small investment teams

        ↓

WHAT PROBLEM?
Investment decisions require synthesizing fragmented,
uncertain, conflicting evidence in portfolio context

        ↓

WHAT JOB?
Determine what to do, why, what could make the
decision wrong, and whether the process worked

        ↓

WHAT DOES POLARIS PROVIDE?
A systematic, explainable, risk-aware,
repeatable decision process

        ↓

WHAT REMAINS HUMAN?
Consequential investment judgment

        ↓

OUTCOME → EVALUATION → LEARNING → BETTER FUTURE DECISION
```

### Alternatives considered

#### Analytical feature collection

Rejected as the job model because it makes each analytical capability an end in itself and provides no principled way to reject feature growth.

#### Recommendation generator

Rejected because it optimizes for producing answers rather than improving decisions. It also creates pressure to recommend activity when doing nothing may be the correct portfolio decision.

#### Research assistant

Useful but incomplete. Research serves the decision process, but the Polaris job extends through portfolio context, risk, recommendation, explanation, outcome evaluation, and learning.

#### Generic investment workflow automation

Rejected as the primary job because automation describes how work is executed rather than the investment outcome the user is trying to achieve.

### Consequences

The Jobs decision implies:

* every major product capability should map to one or more of the six durable jobs;
* producing more analysis or more recommendations is not itself a success metric;
* "do nothing" must remain a legitimate outcome of the decision process;
* portfolio context and explicit risk are required before an investment view becomes a portfolio recommendation;
* challenge and falsification are part of decision quality, not decorative multi-agent behavior;
* explanation is part of the product contract rather than merely report formatting;
* the lifecycle after a recommendation matters: outcomes, evaluation, and learning are product concerns;
* historical state should preserve what was knowable at decision time rather than judging the past using future information;
* the decision record should remain a product concept until later product and architecture work determines its best implementation;
* supporting capabilities such as news, simulation, retrieval, reporting, and automation must justify themselves through the decision cycle rather than becoming independent product centers.

## Open Product Definition sequence

The next Product Definition topics remain:

1. Product identity
2. Core experience
3. Authority model
4. Scope boundaries
5. Differentiation
6. Core capabilities
7. Product principles

New rationale should be added as those decisions are made rather than reconstructed after the full exercise is complete.