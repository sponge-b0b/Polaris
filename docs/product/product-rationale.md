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

## 4. Product Identity

### Decision

Polaris is an **AI-assisted portfolio decision system for sophisticated individual decision-makers and small investment teams**.

It combines investment intelligence, portfolio context, risk-aware reasoning, durable decision evidence, and evaluation into an opinionated decision lifecycle that supports—but does not replace—human investment judgment.

Polaris is delivered through a configurable and extensible product platform, but it is not a general-purpose AI, workflow, or financial-development platform. Its configurability exists to adapt the Polaris decision process to different portfolios, strategies, evidence sources, models, and operating contexts.

### Why "portfolio decision system" is the primary identity

Purpose, Users, and Jobs all converge on the same endpoint: a trustworthy portfolio decision lifecycle.

The intended user is not primarily trying to build software or assemble arbitrary workflows. The user wants help determining what to do with a portfolio, why, what could make that judgment wrong, and what should be learned afterward.

"Portfolio decision system" therefore describes the product in terms of the job it performs rather than the infrastructure it contains.

The identity hierarchy is:

```text
WHAT IS POLARIS?

Portfolio Decision System

        ↓ supported by

Investment Intelligence

        ↓ delivered through

A configurable product platform
```

The order matters. Reversing it would allow platform and infrastructure concerns to define the product instead of serving it.

### Why platform is not the primary noun

Polaris clearly contains platform-like mechanisms: runtime orchestration, workflows, providers, persistence, retrieval, telemetry, governance, replay, interfaces, and extensibility.

That does not make "platform" the right primary product identity.

A platform-first identity naturally encourages questions such as:

* What else could users build with this runtime?
* Which generic plugin system should exist?
* How arbitrary should workflow composition become?
* Which additional framework primitives should be exposed?

Those may be reasonable implementation questions in context, but they are dangerous as product drivers because almost any generic infrastructure feature can then justify itself through hypothetical future flexibility.

The governing rule should be:

> Polaris may have a platform architecture without being a platform-first product.

Platform capability is justified when it makes the portfolio decision product more configurable, reliable, extensible, or integratable.

### Why Polaris is more than a conventional application

The opposite extreme is also insufficient.

A conventional financial application could be imagined as:

```text
Dashboard
  ↓
Run analysis
  ↓
See recommendation
```

The accepted Jobs model is much richer:

```text
observe
  ↓
reason
  ↓
challenge
  ↓
apply portfolio context
  ↓
risk-aware recommendation
  ↓
human decision
  ↓
preserve
  ↓
evaluate
  ↓
learn
```

Supporting that lifecycle across different portfolios, strategies, evidence sources, models, risk policies, time horizons, and operating contexts requires meaningful configurability and extensibility.

The correct distinction is therefore not application versus platform. It is **domain product versus blank canvas**.

Polaris should be configurable as a portfolio decision product rather than programmable as an arbitrary financial-AI construction kit.

### Opinionated decision lifecycle, configurable investment process

Polaris should be **very opinionated about the decision lifecycle while remaining flexible about how users configure their investment process**.

A trustworthy Polaris decision should have recognizable concepts such as:

```text
Decision context
Evidence
Portfolio state
Interpretation
Challenge / uncertainty
Risk
Alternatives
Recommendation
Explanation
Human decision
Evaluation
```

Users should be free to vary appropriate domain inputs and policies, including:

* portfolios and asset universes;
* strategies;
* indicators and analytical methods;
* evidence and data providers;
* models;
* risk thresholds and policies;
* investment horizons;
* reporting and operating preferences.

That flexibility should not remove the product's opinion about what a trustworthy decision process requires.

A useful contrast is:

```text
Generic platform:
"Build whatever workflow you want."

Polaris:
"Configure how Polaris performs portfolio decision work."
```

### Product identity, capabilities, and delivery architecture

Three layers help keep the product concept coherent:

#### 1. Product identity — Portfolio Decision System

The core is the investment decision lifecycle:

```text
Evidence
   ↓
Decision process
   ↓
Recommendation
   ↓
Human decision
   ↓
Evaluation
```

Everything else exists to participate in or support that lifecycle.

#### 2. Product capabilities — Investment Intelligence

Capabilities such as market understanding, research, portfolio intelligence, risk, strategy reasoning, historical knowledge, simulation, and evaluation supply the information and reasoning necessary for decisions.

Investment intelligence is therefore important, but it is not the endpoint.

A product that merely tells the user "everything you should know today" stops before the job Polaris has accepted.

#### 3. Delivery architecture — Configurable product platform

The product may need qualities such as:

```text
configurable
composable
extensible
replayable
observable
integratable
```

These qualities allow Polaris to support different portfolios and investment processes without becoming a fixed monolith.

They remain subordinate to the domain product.

### Why investment intelligence is insufficient as the whole identity

"Investment intelligence" usefully covers research, market understanding, synthesis, knowledge, portfolio context, and risk.

Its weakness is that it does not clearly specify the endpoint.

A pure investment-intelligence product might stop at:

> Here is what matters today.

Polaris is intended to go farther:

> Given what matters today, what are the reasonable portfolio actions, which is preferred, why, what could make that view wrong, and how should the decision be evaluated afterward?

Investment intelligence is therefore a major capability family within the portfolio decision system rather than the fundamental identity itself.

### Why decision support is accurate but incomplete as the primary phrase

"Decision-support system" correctly communicates that the human retains authority.

Its weakness is that it can imply a passive analytical application: data, dashboards, and tools that leave nearly all synthesis to the user.

Polaris is intended to be more active. It gathers evidence, reasons, synthesizes, challenges, applies portfolio and risk context, forms recommendations, preserves decision evidence, and supports evaluation.

For that reason, **AI-assisted portfolio decision system** is the stronger primary identity, while **portfolio intelligence and decision-support platform** remains useful explanatory and positioning language.

### Why "AI-assisted" rather than "AI-native"

AI is central enough to Polaris that hiding it would be misleading, but it should remain a means rather than product ideology.

Calling Polaris "AI-native" risks encouraging future design choices to begin with:

> How can AI do this?

The stronger question is:

> What implementation produces the most trustworthy decision outcome?

The accepted authority direction already points toward:

```text
AI where reasoning and synthesis add value
Deterministic software where rules and guarantees matter
Human judgment where consequential authority matters
```

"AI-assisted" communicates the importance of AI without implying that every meaningful capability should be model-driven.

Polaris should be perfectly willing to solve a product problem deterministically when that is the better solution.

### Why Polaris is not a portfolio-management system

"Portfolio management system" sounds close to the intended domain but carries a much larger operational contract.

It can imply ownership of:

* portfolio accounting;
* books and records;
* reconciliation;
* trade lifecycle;
* order management;
* broker operations;
* execution;
* compliance operations;
* performance accounting;
* client accounting.

Polaris needs authoritative enough portfolio state to reason about decisions, but that does not mean it should own every operational responsibility associated with managing a portfolio.

"Portfolio decision system" is more precise and avoids accidentally expanding the product contract into a full investment-operations stack.

### The decision lifecycle as the organizing spine

Once Polaris is understood as a portfolio decision system, the decision lifecycle becomes the natural organizing spine of the product.

A conceptual view is:

```text
                 POLARIS

          Portfolio Decision System

                   │
       ┌───────────┴───────────┐
       │                       │
Decision Intelligence      Decision Memory
       │                       │
Market                    Decision records
Research                  Outcomes
Portfolio                 Evaluations
Risk                      Historical context
Strategy                  Lessons
       │                       │
       └───────────┬───────────┘
                   │
             Decision Lifecycle
                   │
                 Human
```

Those exact capability labels are not yet frozen. The durable point is that agents, workflows, services, storage technologies, and runtime components should not become the conceptual spine merely because they are prominent in implementation.

This gives later capability and architecture reviews a powerful question:

> Where does this subsystem participate in or support the decision lifecycle?

If the answer is unclear, it is either a supporting platform mechanism whose value should be demonstrated or a candidate for removal from the product.

### Why "runtime-native" is not product identity

A strong runtime may be a significant implementation advantage, but the target user does not primarily need a runtime-native product.

The user needs outcomes such as:

* reliable decision execution;
* preserved evidence;
* visible failures and uncertainty;
* replay where appropriate;
* enforced governance;
* inspectable history;
* evaluable decisions.

A strong runtime can make those outcomes possible. The runtime is therefore a means to trustworthy execution, not the reason the user hires Polaris.

"Runtime-native" should be treated as an architectural or product-quality characteristic rather than the core public identity.

### Why Polaris is not a blank canvas

Freezing this identity means accepting a deliberate limitation:

> Polaris is not a toolkit from which users assemble arbitrary financial AI systems.

The product has an opinion about the domain and about how trustworthy investment decisions are formed.

Even when the implementation exposes powerful workflow composition, the preferred user-facing concepts should trend toward domain language such as:

```text
research inputs
decision evidence
portfolio context
strategy
risk policy
recommendation
review
evaluation
```

rather than forcing product users to think primarily in implementation primitives such as:

```text
nodes
edges
agents
prompts
generic tools
graphs
```

The latter may remain useful to developers and operators underneath the product surface. They should not define the investment user's conceptual model.

### Alternatives considered

#### Platform-first financial AI product

Rejected because it makes extensibility and generic construction capability the product center. This would make it too easy for runtime and framework features to outrank investment-user value.

#### Conventional portfolio application

Rejected as too narrow because the accepted decision lifecycle requires meaningful configurability, extensibility, multiple evidence sources, durable history, evaluation, and integration with different investment processes.

#### Investment intelligence platform

Useful as a capability and positioning phrase, but insufficient as the core identity because intelligence can stop before a decision and is broad enough to permit uncontrolled analytical expansion.

#### Portfolio decision-support platform

Strong and substantially correct. It remains useful public language, especially because it communicates human authority. "Portfolio decision system" is preferred as the deeper identity because Polaris actively participates in the full decision lifecycle rather than merely supplying passive support surfaces.

#### AI-native investment operating system

Rejected as the primary identity. "Operating system" is too expansive and can justify absorbing every adjacent investment function, while "AI-native" risks turning a means into ideology.

#### Portfolio management system

Rejected because it implies operational ownership well beyond the accepted decision-support product boundary.

#### Generic AI-agent or workflow framework

Explicitly rejected as product identity. The runtime may contain reusable general mechanisms, but generic developer extensibility is not the user job Polaris exists to perform.

### Consequences

The Product Identity decision implies:

* **decision system > investment intelligence > product platform** is the governing hierarchy;
* platform architecture must justify itself by improving the portfolio decision product;
* Polaris should be opinionated about the decision lifecycle rather than offering arbitrary workflow construction as the primary experience;
* users should configure domain concepts and investment process where practical rather than runtime implementation primitives;
* extensibility should primarily adapt evidence, portfolios, strategies, models, risk policies, and operating contexts to the Polaris decision process;
* AI remains an important reasoning mechanism but is not privileged over deterministic implementations when deterministic software is more trustworthy;
* "runtime-native" should be treated as an implementation/product-quality characteristic rather than the fundamental product identity;
* portfolio state is necessary, but Polaris should not implicitly become the system of record for all portfolio operations;
* investment intelligence capabilities should be judged by whether they advance the decision lifecycle rather than by analytical breadth alone;
* the decision lifecycle should organize later capability mapping and provide a test for whether existing subsystems belong in Polaris;
* public interfaces should increasingly expose investment-domain concepts without requiring the user to understand the runtime's internal graph, agent, prompt, or service topology;
* a reusable internal platform is compatible with this identity as long as it remains subordinate to the domain product.

## Open Product Definition sequence

The next Product Definition topics remain:

1. Core experience
2. Authority model
3. Scope boundaries
4. Differentiation
5. Core capabilities
6. Product principles

New rationale should be added as those decisions are made rather than reconstructed after the full exercise is complete.
