# Polaris Domain Model

**Status:** In progress  
**Purpose:** Discover and define the canonical Polaris domain: the concepts Polaris owns or reasons about, their meanings, identities, relationships, lifecycle semantics, authority boundaries, temporal behavior, and distinction from supporting platform/runtime concepts.

This document is a **domain discovery and definition artifact**. It is intentionally implementation-neutral. It does not prescribe packages, services, databases, APIs, workflows, agents, aggregates, bounded contexts, events, or other software topology.

The objective is not methodological purity. Domain-driven design techniques such as ubiquitous language, explicit boundaries, identity analysis, lifecycle modeling, and scenario testing are useful here because they force semantic precision. Polaris is not required to adopt DDD patterns merely because those techniques are used during discovery.

The governing question is:

> **What is the world Polaris actually understands and participates in, and what must each important concept mean for that world to remain coherent through time?**

The domain model must be sufficiently clear before 0.2.0 requirements and architecture are defined. Requirements should constrain implementation against known domain semantics rather than allowing the current workflow-centric architecture to define those semantics implicitly.

## Relationship to existing product doctrine

This document is downstream of the durable product decisions already recorded in:

* [`product-definition.md`](./product-definition.md);
* [`product-core-capabilities.md`](./product-core-capabilities.md);
* [`capability-model.md`](./capability-model.md);
* [`product-execution-continuity.md`](./product-execution-continuity.md).

Those documents already establish several domain-level truths:

* Polaris exists to improve portfolio and investment decision quality;
* decisions are the product center;
* portfolio context and risk materially shape recommendations;
* consequential investment judgment remains human;
* external specialist systems retain authority over the operational facts they own;
* Polaris owns continuity of its decision lifecycle across externally executed action;
* decisions become durable memory and later evaluation context;
* workflow execution, reports, RAG, models, agents, runtime infrastructure, and interaction surfaces are supporting mechanisms rather than product identity.

This document must sharpen the concepts implied by those truths without prematurely turning them into architecture.

## Relationship to `CONTEXT.md`

[`../../CONTEXT.md`](../../CONTEXT.md) is the repository's canonical domain vocabulary.

The responsibilities are deliberately different:

```text
CONTEXT.md
    ↓
canonical term definitions
meaningful distinctions
useful aliases / deprecated terminology
small domain-level relationships

this document
    ↓
domain shape
concept relationships
identity and lifecycle reasoning
temporal semantics
ownership and authority boundaries
scenario analysis
unresolved semantic questions
```

When a term or distinction becomes resolved during this work, its canonical definition belongs in `CONTEXT.md` as well as any broader relationship reasoning that remains useful here.

This document must not become a second glossary containing competing definitions.

### Scenario preservation rule

Semantically distinct use cases and examples that materially establish, disambiguate, or pressure-test a domain concept are part of this domain-discovery artifact and should be preserved here rather than left only in conversation history.

The rule is intentionally selective rather than exhaustive:

* preserve an example when it proves a different boundary, authority distinction, identity rule, lifecycle behavior, temporal behavior, or invalid state;
* preserve representative variants when different variants lead to different domain outcomes;
* do not duplicate conversational examples that prove the same semantic point without adding another distinction;
* treat preserved scenarios as illustrative fixtures rather than a closed enumeration of all valid domain behavior;
* if a future scenario contradicts a frozen invariant, revisit the invariant rather than silently bending the example or implementation around it.

Canonical definitions remain in [`../../CONTEXT.md`](../../CONTEXT.md); the scenarios in this document preserve the reasoning needed to apply those definitions correctly.

## Discovery rules

The domain will be discovered using the following rules.

### Domain truth before implementation shape

Existing code is evidence of current behavior, not automatic proof of correct domain semantics.

When current implementation and the emerging domain disagree, classify the discrepancy rather than silently preserving implementation behavior.

Useful classifications include:

```text
KEEP
Current concept already represents the domain correctly.

RENAME
Semantics are useful but the current name is misleading or overloaded.

RE-PARENT
Concept is useful but currently owned by the wrong product/runtime boundary.

SPLIT
One current concept carries several distinct domain meanings.

MERGE
Several current concepts represent one domain meaning.

DEMOTE
A runtime, workflow, transport, or persistence concept has been mistaken for product state.

REMOVE
A concept exists only because of accidental architecture and has no durable product meaning.
```

These are discovery labels, not automatic refactoring instructions.

### Capabilities are not automatically subdomains

The nine core capabilities describe **what Polaris must be able to accomplish**.

They do not automatically define nine subdomains, bounded contexts, aggregates, services, or packages.

Domain boundaries should emerge from cohesive language, responsibility, identity, lifecycle, authority, and invariants rather than mirroring the capability list mechanically.

### Product concepts are not automatically entities

A named domain concept does not automatically imply an entity, aggregate root, table, repository, service, or event stream.

For example, discovering that Portfolio Decision has durable identity does not yet determine its persistence or aggregate topology.

### External authority remains explicit

Polaris may observe, normalize, preserve, reason over, or reconcile an external fact without owning that fact.

The domain model must distinguish:

```text
Polaris-owned meaning
        from
externally authoritative fact
```

especially for market observations, portfolio/accounting state, broker activity, orders, fills, and resulting operational state.

### Time is a domain concern

The model must preserve the distinction between:

```text
what is known now
```

and:

```text
what was knowable when the decision was made
```

Identity, revision, reassessment, supersession, staleness, review conditions, execution divergence, and later evaluation are therefore domain questions rather than merely persistence concerns.

## Current domain center

The Product Definition establishes the portfolio decision lifecycle as Polaris's organizing spine and durable source of product value.

The current working domain hypothesis is therefore:

> **Polaris's core domain is the formation, governance, continuity, memory, and evaluation of portfolio decisions under uncertainty.**

This hypothesis does **not** yet settle whether `Portfolio Decision` is best modeled as an entity, aggregate, process, lifecycle, record, or combination of those ideas. That semantic question is part of this discovery.

It also does not imply that every important Polaris concept is subordinate to one giant Portfolio Decision object.

## Candidate domain areas

The following are **candidate areas of cohesive domain responsibility**, not frozen bounded contexts or implementation modules.

They are starting hypotheses to be tested against concrete scenarios, identity, lifecycle, vocabulary, and ownership.

### Portfolio Decision

Candidate responsibilities:

* why decision work exists;
* what portfolio question or choice is being resolved;
* stable decision identity;
* initiation, reopening, reassessment, deferral, and supersession;
* current decision state;
* relationship between Recommendation and Human Portfolio Decision;
* review or invalidation conditions;
* decision closure or continuation.

Candidate concepts include:

* Decision Need;
* Portfolio Decision;
* Decision Context;
* Recommendation;
* Human Portfolio Decision;
* Review Condition;
* Reassessment;
* Deferral;
* Supersession.

This area is the first priority for semantic discovery because 0.2.0 makes Portfolio Decision the product's canonical unit.

### Investment Intelligence

Candidate responsibilities:

* attributable evidence used in decision work;
* claims and materiality;
* interpretation and thesis formation;
* competing hypotheses;
* counterevidence;
* assumptions;
* uncertainty;
* alternatives;
* invalidation conditions;
* relevant historical comparison.

Existing terms such as Evidence, Claim, Strategy Hypothesis, Directional Bias, and Confidence provide useful starting vocabulary but may require re-scoping or renaming.

### Portfolio & Risk

Candidate responsibilities:

* decision-relevant portfolio state;
* current and proposed portfolio posture;
* allocation consequences;
* exposure and concentration;
* analytical risk;
* decision constraints and risk implications;
* expected portfolio consequence of candidate actions.

External portfolio/accounting systems may remain authoritative for underlying operational holdings and accounting facts even when Polaris owns the interpretation of those facts for a decision.

### Authority & Governance

Candidate responsibilities:

* deterministic policy;
* admissibility;
* governance review;
* positive and negative authority provenance;
* Approval;
* Residual-Risk Acceptance;
* contestability;
* distinction between what Polaris may recommend and what a human chooses;
* preservation of authority decisions through the lifecycle.

This area must preserve the fundamental distinction:

```text
what Polaris recommended
        ≠
what governance permitted
        ≠
what the human decided
```

### Decision Continuity

Candidate responsibilities:

* intended external consequence of a Human Portfolio Decision;
* Action Intent;
* association of authoritative external activity to the originating decision;
* reconciliation confidence and ambiguity;
* divergence between intended and observed action;
* resulting portfolio state;
* externally initiated activity that has no originating Polaris decision.

Polaris owns continuity and reconciliation meaning; external operational systems retain authority for what actually occurred.

### Outcome & Learning

Candidate responsibilities:

* observed outcome;
* evaluation of the original decision process using historically faithful information;
* recommendation quality;
* human modification or override;
* implementation fidelity;
* risk-management adherence;
* causal interpretation with explicit uncertainty;
* durable lessons;
* later influence on future attention, reasoning, or policy review.

Outcome must remain distinct from decision quality.

### Durable Decision Memory

Durable Decision Memory may prove to be a cross-domain responsibility rather than a separate subdomain.

Candidate responsibilities include preserving or connecting:

* decision identity;
* historical context;
* evidence provenance;
* reasoning and challenge;
* recommendation history;
* authority trace;
* human judgment;
* action continuity;
* outcome;
* evaluation;
* lessons;
* active conditions that can make a prior decision relevant again.

The important discovery question is whether Decision Memory is best understood as a domain area of its own or as a temporal property of all decision-domain concepts.

### Attention

Attention may also be primarily a cross-domain capability rather than a standalone subdomain.

It depends on active decisions, theses, risks, review conditions, portfolio state, catalysts, new evidence, and memory to determine whether new information creates, changes, or reopens decision work.

This relationship will be clarified after Portfolio Decision identity and lifecycle semantics are better understood.

## Initial vocabulary audit

The current `CONTEXT.md` contains valuable language, but it reflects several eras of Polaris and currently mixes investment-domain, governance-domain, runtime, architecture, and infrastructure concepts.

### Strong existing domain language to preserve and sharpen

The following current terms appear to represent durable domain meaning and should be treated as strong candidates for retention:

* Recommendation;
* Capital-Relevant Output;
* Approval;
* Residual-Risk Acceptance;
* Evidence and its material roles;
* Claim, Material Claim, Readiness-Gating Claim, Contextual Claim;
* Authority;
* Strategy Hypothesis;
* Portfolio Posture;
* Allocation;
* Risk and its meaningful categories;
* Policy;
* Governance;
* Review Task;
* Contestability;
* Confidence;
* Directional Bias;
* Risk Score;
* Source of Truth;
* Projection where it is used as a domain-facing distinction between authoritative state and derived representation.

Retention does not mean every existing definition is already final.

### Important missing or not-yet-canonical product terms

The newer Product Definition and Capability Model rely on important concepts that are not yet defined canonically in `CONTEXT.md`, including:

* Decision Need;
* Portfolio Decision;
* Human Portfolio Decision;
* Decision Context;
* Decision Lifecycle;
* Durable Decision Memory;
* Decision-Time Availability;
* Review Condition;
* Reassessment;
* Supersession;
* Action Intent;
* Reconciliation;
* External Activity;
* Outcome;
* Decision Outcome Evaluation;
* Lesson.

These concepts should not be added merely because they appear in product prose. Each should be sharpened through concrete scenarios first.

### Language collisions requiring resolution

#### `Decision record` versus `Portfolio Decision`

The Product Definition currently uses `decision record` as a working concept for the durable representation of decision state, while the 0.2.0 roadmap and release contract use `Portfolio Decision` as the canonical durable product concern.

The likely distinction is:

```text
Portfolio Decision
= the domain decision/lifecycle itself

Decision Record
= durable representation of the decision through time
```

This is only a working hypothesis until identity and lifecycle scenarios confirm it.

#### `Strategy Decision` versus portfolio/human decision

`CONTEXT.md` currently defines Strategy Decision as a typed synthesis result produced from competing Strategy Hypotheses.

That concept may be useful, but the word `Decision` now collides with the much more consequential Portfolio Decision and Human Portfolio Decision semantics.

Discovery must determine whether Strategy Decision should remain canonical language or be renamed to something closer to Strategy Synthesis, Strategy Assessment, or another term that describes what it actually is.

#### `Release`

`CONTEXT.md` defines Release as a governed decision allowing an output to cross a controlled boundary.

The product roadmap also uses release in the ordinary software-version sense (`0.2.0 release`, `1.0 release`).

A ubiquitous language should not rely on context to distinguish two important meanings unnecessarily. The governed-output concept likely needs a more specific canonical term if both meanings remain important.

#### Proposed Action / Action Candidate versus Action Intent

A Proposed Action or Action Candidate is currently a possible action under consideration.

Action Intent, introduced by execution-continuity doctrine, represents the external portfolio consequence implied by the human decision and expected to be observed later.

These must remain separate unless scenario testing proves they are the same concept.

### Platform/runtime language currently mixed into the glossary

The current glossary includes concepts such as:

* Workflow Identity;
* Governed Execution Evidence;
* Workflow Invocation;
* Workflow Authority Facts;
* Completed-Run Archive;
* Application Service;
* Provider;
* Client;
* Backtest as canonical-runtime behavior;
* current PostgreSQL System-of-Record wording.

Several of these have useful precise meanings, but they are primarily runtime, architecture, integration, or infrastructure vocabulary rather than the investment/decision domain itself.

The repository's current domain-modeling policy states that `CONTEXT.md` is a domain glossary and must not contain implementation or architecture details.

Therefore discovery must determine whether each such entry should:

* remain because it expresses genuine cross-product domain meaning;
* be renamed/reframed into domain language;
* move to architecture/reference documentation;
* or be retired after its product responsibility is represented correctly elsewhere.

No glossary entry should be removed merely to make the file shorter.

## First semantic problem: what is a Portfolio Decision?

Before the candidate domain map can be trusted, Polaris must answer what a Portfolio Decision actually represents.

The following questions are deliberately unresolved and form the first discovery sequence.

### Purpose and subject

* What makes a situation a Portfolio Decision rather than research, analysis, monitoring, or an ordinary question?
* What is the decision's subject: a security, portfolio posture, exposure, risk condition, strategy, proposed change, or explicit question?
* Can one Portfolio Decision concern several securities or several portfolio actions?
* Can a Portfolio Decision correctly terminate in deliberate inaction?

### Creation

* What event causes a Portfolio Decision to come into existence?
* Does a user question always create one, or only when the question requires consequential portfolio judgment?
* Does a scheduled review create a new decision or reopen an existing one?
* When Polaris detects material change, does it create a new decision, reopen an active decision, or create a reassessment of a prior decision?

### Identity

* What makes two rounds of work the same Portfolio Decision?
* Which changes are revisions of the same decision and which create a new decision?
* Can one Portfolio Decision span several analyses, evidence refreshes, recommendations, and runtime executions?
* Can a decided Portfolio Decision be reopened without losing its original historical meaning?

### Lifecycle

* What is the minimal lifecycle of a Portfolio Decision?
* Which lifecycle facts are immutable history and which represent current state?
* What does defer mean semantically?
* What does close mean if later evidence can make the decision relevant again?
* What does supersession mean, and how is it different from reassessment?

### Relationship to Recommendation

* Can a Portfolio Decision exist without a Recommendation? The current product doctrine strongly suggests yes.
* Can a Portfolio Decision produce several Recommendations over time?
* Does a revised Recommendation remain part of the same decision or imply a new decision?
* What does it mean for Polaris to withhold a Recommendation while the Portfolio Decision remains valid decision work?

### Relationship to Human Portfolio Decision

* Is the Human Portfolio Decision a terminal judgment within the Portfolio Decision lifecycle or a separate but linked domain object?
* Can the human modify only the proposed action, or also the reasoning/conditions that define the intended decision?
* Does deferral leave the same Portfolio Decision active?
* If the human rejects Polaris and later acts differently, how should that relate to the original Portfolio Decision?

### Time and reassessment

* If material new evidence arrives after a human decision, does Polaris reopen the same Portfolio Decision or create a new linked decision?
* If an invalidation condition is breached, is that a new Decision Need or a state transition of the old decision?
* How should Polaris preserve the exact historical recommendation and human judgment while also representing the current reassessed view?

These questions should be resolved through concrete portfolio scenarios rather than abstract naming preference alone.

## Scenario-driven discovery plan

The first domain pass should stress-test Portfolio Decision semantics with a small set of deliberately different situations.

Candidate scenarios:

1. **User-initiated fresh decision** — "Should we increase SPY exposure today?"
2. **Scheduled review with no material change** — the portfolio thesis is reviewed and remains valid.
3. **Scheduled review with changed recommendation** — the same thesis is reviewed but portfolio/risk context now favors reducing exposure.
4. **Material shock** — a rapid market move invalidates important assumptions behind an earlier recommendation.
5. **Deferred judgment** — Polaris recommends waiting for CPI and the human defers action until that catalyst.
6. **Human modification** — Polaris recommends a 25% reduction and the human decides on 10%.
7. **Rejected recommendation** — the human rejects Polaris's recommendation while the underlying decision concern remains relevant.
8. **No recommendation possible** — required evidence is stale or conflicted, so Polaris preserves decision work but withholds a recommendation.
9. **Unrelated external action** — the user changes SPY exposure outside Polaris with no originating Portfolio Decision.
10. **Repeated question** — the user asks essentially the same question twice under unchanged conditions.

For each scenario, discovery should answer:

```text
What exists before the scenario?
What creates or changes the Decision Need?
Is this a new Portfolio Decision or the same one?
What facts are immutable history?
What current state changes?
Can a Recommendation exist?
What does the human decide?
What would make the decision close, defer, reopen, or be superseded?
What later facts must remain causally linked?
```

## Domain/implementation reconciliation

After important semantics are resolved, current code concepts should be mapped against the domain using KEEP / RENAME / RE-PARENT / SPLIT / MERGE / DEMOTE / REMOVE.

This should occur **after** the semantic question is understood sufficiently to avoid allowing current file/class boundaries to choose the answer.

Likely high-value reconciliation targets include:

* workflow execution identity;
* decision evidence packets;
* strategy hypotheses and strategy synthesis;
* portfolio allocation intent;
* trade packaging / trade intent;
* governance review and approval records;
* completed-run archive;
* portfolio state records;
* existing evaluation contracts;
* CLI/MCP/report projections.

## Definition of done for Polaris Domain Discovery and Definition

This phase is complete enough to allow 0.2.0 requirements and architecture only when:

1. the core Polaris domain purpose and ownership boundary are explicit;
2. major domain areas are understood well enough that their responsibilities do not materially overlap by accident;
3. Portfolio Decision has a precise meaning, identity, lifecycle, and temporal model;
4. Recommendation and Human Portfolio Decision have precise meanings and relationships to Portfolio Decision;
5. decision initiation, reassessment, deferral, reopening, closure, and supersession are semantically distinguishable;
6. evidence, reasoning, portfolio/risk, governance, action continuity, memory, outcome, and learning concepts have known relationships to the decision lifecycle;
7. external specialist authority is explicit for operational facts Polaris does not own;
8. important current-language collisions are resolved;
9. `CONTEXT.md` contains the resolved canonical vocabulary without architecture/runtime pollution;
10. current implementation concepts have been reconciled against the domain sufficiently to identify the major KEEP / RENAME / RE-PARENT / SPLIT / MERGE / DEMOTE / REMOVE implications;
11. unresolved semantic questions that could change 0.2.0 requirements or architecture have been resolved rather than deferred into implementation.

At that point, requirements can state what the product must do using stable domain language, and architecture can decide how the existing Polaris machinery should be reorganized to make that domain true.

## Resolved foundational portfolio semantics

Portfolio Decision discovery exposed a more foundational question: what Polaris means by `Portfolio`. The following semantics are now resolved and canonicalized in [`../../CONTEXT.md`](../../CONTEXT.md).

### Portfolio identity

A Portfolio is a continuing investment responsibility, not a collection of current holdings or an account wrapper.

Its identity is explicit and durable. It is not inferred from mutable characteristics such as:

* current Positions;
* current capital or portfolio value;
* account or broker;
* strategy;
* manager;
* current mandate version;
* current Portfolio State.

Changes to those facts are changes **to** the Portfolio unless an explicit identity transition says otherwise.

A Portfolio may therefore remain the same Portfolio when it changes holdings, becomes all cash, temporarily has no Positions, changes broker or account, changes manager, or evolves its investment mandate.

Closure is likewise explicit. Zero capital or zero Positions does not silently terminate Portfolio identity.

### Portfolio Boundary

Portfolio identity and Portfolio Boundary are distinct.

```text
Portfolio identity
Which continuing investment responsibility is this?

Portfolio Boundary
Which economic interests belong to that responsibility at this time?
```

The Portfolio Boundary is temporal. It determines the capital, Positions, and economic obligations attributable to a Portfolio at a particular time.

The same economic interest cannot be fully attributed to more than one Portfolio simultaneously. It may be partitioned between Portfolios, but it must not be duplicated merely to support multiple analytical views.

This makes Portfolio an economic management boundary rather than an arbitrary grouping or filter.

Overlapping analytical groupings such as technology holdings, high-beta holdings, or other cross-cutting views may include the same Position repeatedly without becoming Portfolios.

### Account boundary versus Portfolio Boundary

An external account is an operational/accounting boundary, not the definition of a Portfolio.

Conceptually, both relationships are valid:

```text
one Portfolio → multiple accounts
multiple Portfolios → one account
```

when the economic attribution is explicit and non-duplicative.

The current implementation's use of `account_id` in `PortfolioState` is therefore an implementation-shaped relationship rather than proof that Account identity and Portfolio identity are the same domain concept.

### Position and external holdings

A Polaris Position is Portfolio-scoped.

An externally authoritative system may report an account-level holding, while Polaris attributes that economic interest to one or more Portfolios without duplicating it.

For example:

```text
external account holding
100 AAPL long
        │
        │ economic attribution
        ├───────────────┐
        ▼               ▼
Portfolio A         Portfolio B
60 AAPL long        40 AAPL long
```

Position Direction is Long or Short and describes the Portfolio's relationship to the financial instrument. It is distinct from Buy/Sell action or order side and from the directional economic Exposure produced by the Position.

### Temporal and historical integrity

Portfolio attribution is historical fact.

If part of a Position moves from Portfolio A to Portfolio B, the later boundary change changes current Portfolio State but does not rewrite earlier attribution. Decisions made while the economic interest belonged to Portfolio A remain historically associated with Portfolio A.

This supports the wider Polaris invariant:

```text
what is true now
        ≠
what was true or knowable then
```

### Mandate and identity

An investment mandate governs how a Portfolio's capital is managed but is not itself Portfolio identity.

A Portfolio may evolve its mandate while retaining identity. Historical Investment Decisions must remain interpretable against the mandate that applied when they were made rather than against a later mandate revision.

A sufficiently fundamental restructuring may require an explicit choice about identity continuity, but Polaris must not infer a new Portfolio merely because a mandate changed materially.

### Split, merge, closure, and reconstitution

Portfolio split, merge, closure, and fundamental reconstitution require explicit identity semantics.

A split must preserve that predecessor Portfolio attribution existed before the split rather than pretending successor Portfolios always existed. A merge must likewise preserve predecessor lineage. Whether a merge creates a new Portfolio or one Portfolio continues and absorbs another is an explicit domain fact rather than something inferred from capital arithmetic.

### Frozen portfolio invariants

The following invariants are now accepted:

1. **Portfolio identity represents a continuing investment responsibility, not current holdings.**
2. **Portfolio identity is explicit; it is not inferred from mutable state.**
3. **Portfolio Boundary is temporal and determines economic attribution at a point in time.**
4. **The same economic interest cannot be fully attributed to multiple Portfolios simultaneously; it may be partitioned.**
5. **Account Boundary ≠ Portfolio Boundary.**
6. **A Polaris Position is Portfolio-scoped; externally reported account holdings are operational source facts from which Portfolio attribution may be established.**
7. **Exposure is derived from attributed Positions and other commitments; Exposure does not establish Portfolio membership.**
8. **Analytical groupings that overlap economically are not Portfolios merely because they are useful views.**
9. **An investment mandate governs a Portfolio but does not constitute its identity.**
10. **Portfolio State changes do not by themselves change Portfolio identity.**
11. **Current Portfolio attribution never rewrites historical attribution.**
12. **Portfolio closure, split, merge, or fundamental reconstitution requires explicit identity semantics rather than inference.**

### Consequence for decision terminology

Resolving Portfolio makes the canonical decision noun less certain, not more.

A consequential decision may concern one Position, one Exposure, an entire Portfolio, or several Portfolios at once. A cross-Portfolio capital-allocation decision is clearly an investment decision but is awkward to describe as belonging to one Portfolio.

Therefore `Investment Decision` is now the leading candidate for the canonical decision concept, with one or more Portfolios potentially forming its decision scope. This is **not yet canonical vocabulary**. `Portfolio Decision`, `Investment Decision`, decision scope, and decision subject remain part of the next discovery step and must not be changed in `CONTEXT.md` until resolved.

## Resolved financial-instrument, exposure, and portfolio-state semantics

The next foundational pass clarifies the economic vocabulary that surrounds Portfolio and Position. These semantics are now resolved and canonicalized in [`../../CONTEXT.md`](../../CONTEXT.md).

### Financial Instrument

A Financial Instrument is the identifiable tradable security or contract in which a Position can be established.

Instrument identity is therefore more precise than a display symbol or product-family label. For example:

```text
AAPL common stock
→ Financial Instrument

SPY ETF shares
→ Financial Instrument

specific ES futures contract
→ Financial Instrument

ES root/product symbol
→ not by itself a specific Financial Instrument
```

Polaris may analyze many economically relevant things that are not Financial Instruments. An index, macroeconomic series, rate, breadth measure, or other market reference can provide Evidence without being something in which the Portfolio can establish a Position.

Ordinary Portfolio cash is treated as capital or liquidity rather than being forced into Financial Instrument merely for model uniformity. A money-market fund share, Treasury bill, or other tradable security used as a cash equivalent remains a Financial Instrument in its own right.

### Exposure

Exposure describes what a Portfolio is economically sensitive or concentrated toward rather than what it literally holds.

One Position may create several Exposures:

```text
100 AAPL long
    ↓
AAPL exposure
Apple issuer exposure
technology exposure
equity exposure
USD exposure
market-beta exposure
```

Several Positions may also contribute to one Exposure:

```text
AAPL ──┐
MSFT ──┼──→ Technology Exposure
NVDA ──┘
```

Position Direction and Exposure direction are distinct. A Long Position in a derivative may create negative or otherwise non-obvious exposure to its underlying reference.

Exposure is also distinct from Allocation and Risk:

```text
Allocation
How is capital distributed?

Exposure
What is the Portfolio economically sensitive or concentrated toward?

Risk
What adverse outcomes may arise, with what significance, given the Portfolio, its Exposures, and current conditions?
```

Derivatives and hedges make the separation especially important because capital allocation, gross exposure, net exposure, and assessed Risk may diverge substantially.

### Portfolio State

Portfolio State describes the Portfolio's economic condition at a particular time within the Portfolio Boundary.

Conceptually:

```text
Portfolio
    ↓
Portfolio Boundary @ T
    ↓
Portfolio State @ T
    ├── capital
    ├── cash / liquidity
    ├── Positions
    ├── obligations
    ├── valuations
    ├── Allocation
    ├── Exposure
    ├── leverage
    ├── performance / drawdown
    └── other economic measures
```

Portfolio State should not become a catch-all for every analytical judgment about the Portfolio. Market-regime interpretation, investment thesis, directional recommendation, governance judgment, and human decision are analyses or judgments about Portfolio State and other Evidence rather than intrinsic Portfolio State merely because they are useful near it.

### Account State and authority

Account State is operational/accounting state associated with an external account and is distinct from Portfolio State.

Account restrictions, margin facts, balances, permissions, transfer restrictions, and similar operational facts may constrain or inform Portfolio decisions without defining Portfolio identity or automatically becoming Portfolio State.

A Portfolio State may represent both externally authoritative facts and Polaris-derived economic measures. Representation together does not erase authority boundaries.

For example:

```text
100 AAPL
→ externally authoritative holding fact

31% technology exposure
→ Polaris-derived Portfolio measure
```

Both may participate in the same decision-time Portfolio State while retaining separate provenance and authority.

### Actual and projected state

Unqualified Portfolio State means an actual or historically actual Portfolio condition at an as-of time.

A hypothetical state expected to result from a candidate action or decision consequence is a Projected Portfolio State and must remain visibly distinct from actual Portfolio State.

```text
Current Portfolio State
        ↓
Candidate action
        ↓
Projected Portfolio State
```

A projection does not become actual Portfolio State merely because Polaris recommends or expects it.

### Current implementation reconciliation

The current `domain/portfolio/models/portfolio_state.py` concept combines several semantic families, including account operational restrictions, Portfolio economic facts, Exposure measures, risk assessments, market/regime interpretation, directional bias, and risk signals.

That is evidence of useful existing behavior, but it is a semantic **SPLIT** candidate rather than proof that all of those meanings belong to one domain concept. Architecture may later choose to transport or compose several of them together, but the domain model must preserve their distinct meanings and authorities.

### Frozen financial-state invariants

The following invariants are now accepted:

1. **A Financial Instrument is a Position-bearing tradable security or financial contract; a ticker or product-family symbol does not by itself define Financial Instrument identity.**
2. **Market indexes, macro series, and similar analytical references are not Financial Instruments merely because Polaris reasons about them.**
3. **Ordinary Portfolio cash is capital or liquidity rather than automatically a Financial Instrument.**
4. **Exposure describes economic sensitivity or concentration; Position describes an attributable holding or obligation.**
5. **One Position may create several Exposures, and several Positions may contribute to one Exposure.**
6. **Position Direction does not determine Exposure direction.**
7. **Exposure ≠ Allocation.**
8. **Exposure ≠ Risk.**
9. **Portfolio State is the time-specific economic condition of a Portfolio within its Portfolio Boundary.**
10. **Account State ≠ Portfolio State, although Account facts may materially constrain or inform Portfolio State and decisions.**
11. **Externally authoritative facts and Polaris-derived Portfolio measures retain their separate authority even when represented together.**
12. **Actual Portfolio State ≠ hypothetical Projected Portfolio State.**

## Resolved investment-mandate semantics

Investment Mandate discovery exposed an important boundary between investment judgment and deterministic authority. A Mandate can contain meaningful narrative intent without pretending that every sentence is a machine rule, and Polaris can surface economically preferred actions that conflict with the Mandate without silently rewriting either the investment judgment or the governing boundary.

These semantics are now resolved and canonicalized in [`../../CONTEXT.md`](../../CONTEXT.md).

### Mandate shape

An Investment Mandate is the durable, temporally applicable statement of a Portfolio's investment purpose, Investment Objectives, Investment Principles, and Formal Constraints.

Its semantic roles are deliberately different:

```text
Purpose
Why does this Portfolio exist?

Investment Objective
What outcomes should the Portfolio pursue?

Investment Principle
What qualitative guidance should shape investment judgment?

Formal Constraint
What explicit boundaries are deterministically authoritative?
```

The Mandate is distinct from Portfolio identity, Portfolio State, current Risk, external Account constraints, Investment Strategy, and the Investment Authority Regime.

A Portfolio may use multiple simultaneous Investment Strategies under one Mandate when those Strategies remain means of managing the same continuing investment responsibility. Mandate compliance concerns the resulting Portfolio as a whole; individually acceptable Strategies can still combine into a Portfolio condition that violates a Formal Constraint.

### Objectives and Principles

Investment Objectives describe desired outcomes rather than deterministic compliance boundaries.

For example, `seek long-term real capital growth` establishes what successful management is trying to accomplish. A Recommendation may advance, detract from, or have uncertain effect on that Objective, but failure to advance it is not by itself a Mandate violation.

Investment Principles provide qualitative, context-sensitive guidance. Statements such as `avoid excessive concentration`, `favor long-term compounding over unnecessary turnover`, or `use derivatives primarily for risk management` require investment judgment to apply.

Polaris may assess a Recommendation as aligned with, in tension with, or uncertain against an Investment Principle. That assessment is interpretive and must not masquerade as deterministic Policy or compliance authority.

Principles are inherently defeasible. A justified departure from a Principle does not require a Mandate Exception merely because tension exists. If the user intends an absolute or machine-enforceable boundary, that boundary must instead be formalized as a Formal Constraint.

### Formal Constraints and deterministic evaluation

A Formal Constraint is authoritative and machine-evaluable in principle. It need not be mathematical or numerical; categorical, Boolean, set-based, and quantitative restrictions may all qualify when their semantics are sufficiently explicit.

Examples include:

```text
Short Positions prohibited.

Permitted Financial Instrument types:
common equity, ETF, Treasury.

Single-position weight <= 10% of Portfolio NAV.

Technology Exposure <= 30% of Portfolio NAV.
```

Natural-language precision is not automatically Formal Constraint precision. Statements such as `no leverage` or `single Position <= 10%` may still be ambiguous about measurement basis, derivative treatment, valuation basis, or other domain semantics.

Therefore an LLM interpretation of Mandate prose cannot silently create deterministic authority. Formalization must be explicit and authoritative.

A Formal Constraint may produce a deterministic result such as satisfied or violated when the required facts are available. If authoritative facts are missing, stale, or insufficient, evaluation may be indeterminate. That does not turn the Formal Constraint into an interpretive Principle; it means the rule is deterministic in principle but cannot currently be evaluated reliably.

### Recommendation versus Mandate assessment

Polaris's investment judgment and Mandate assessment answer different questions.

```text
Investment judgment
What does Polaris believe should be done?

Mandate assessment
How does that Recommendation relate to Objectives,
Principles, and Formal Constraints?

Authority consequence
What authorization, Exception, or other disposition
is required for the Recommendation to proceed?
```

Polaris may therefore recommend an action that conflicts with a Principle or violates a Formal Constraint. It must expose that conflict rather than weakening or censoring the underlying investment reasoning merely to produce a compliant-looking Recommendation.

For example:

```text
Primary Investment Recommendation:
Increase AAPL to 14%.

Formal Constraint:
Single-position maximum = 10%.

Constraint result:
VIOLATED.

Mandate-compliant alternative:
Increase AAPL to 10%.

Authority consequence:
Mandate Exception required for 14%.
```

A Mandate assessment must not be collapsed into one overall `mandate_compliant` Boolean that hides the distinction between Objectives, Principles, Formal Constraints, and Exceptions.

### Mandate Exception

A Mandate Exception is a decision-time authority fact, not another pre-enumerated Mandate term.

It authorizes a scoped departure from an otherwise applicable Formal Constraint without changing the underlying Mandate or rewriting the deterministic constraint result.

For example:

```text
Formal Constraint:
AAPL <= 10%.

Recommendation:
AAPL = 14%.

Constraint result:
VIOLATED.

Mandate Exception:
AUTHORIZED for this scoped decision up to 14%.
```

The constraint remains violated. The Exception changes whether that violation is authorized for the defined scope.

Exceptions may arise from circumstances that could not reasonably have been enumerated in advance. Polaris may identify, propose, or justify an Exception, but it does not gain authority to authorize one from its own Recommendation.

The Investment Authority Regime determines whether a Formal Constraint is exceptionable and which attributable actor or process may authorize the Exception.

### Exception, amendment, and noncompliant choice

Three facts must remain distinct:

```text
Mandate Exception
The governing rule remains unchanged,
but a scoped departure is authorized.

Mandate Amendment
The governing Mandate itself changes.

Noncompliant Human Investment Decision
The governing rule remains unchanged,
no applicable Exception authorizes the departure,
and the human nevertheless chooses it.
```

Human behavior does not retroactively rewrite Mandate truth. An authorized Exception must not be represented as a satisfied constraint, and an unauthorized human choice must not become compliant merely because an authorized human made it.

### Multi-Portfolio decisions

A consequential investment decision may span several Portfolios with different Mandates.

There is no implicit synthetic Mandate for the decision. Each Portfolio retains its own applicable Mandate, Portfolio State, Formal Constraint results, and any Portfolio-specific Exceptions.

The same Evidence may therefore support different Portfolio consequences under different Mandates without creating inconsistent reasoning.

This further strengthens `Investment Decision` as the leading candidate for the eventual canonical consequential-decision noun, while leaving that terminology unresolved until Decision Scope and Decision Subject are fully tested.

### Temporal integrity

The applicable Mandate is part of decision-time context.

A Portfolio may retain identity across Mandate revisions, but historical decisions must remain reconstructable against the Mandate version, Formal Constraint semantics and results, interpretive assessments, and Mandate Exceptions that actually applied when the decision was made.

A later Mandate amendment must not rewrite whether an earlier Recommendation violated the Mandate that governed it at the time.

### Frozen investment-mandate invariants

The following invariants are now accepted:

1. **Investment Mandate contains distinct semantic roles: Purpose, Investment Objectives, Investment Principles, and Formal Constraints.**
2. **Investment Objectives describe desired outcomes; failure to advance an Objective is not a deterministic Mandate violation.**
3. **Investment Principles provide qualitative, context-sensitive investment guidance; they may be interpreted for alignment or tension but do not produce deterministic compliance results.**
4. **Investment Principles are inherently defeasible. A justified departure from a Principle does not require a Mandate Exception merely because tension exists.**
5. **A Formal Constraint is authoritative and machine-evaluable in principle; it need not be numerical, but its scope, measurement basis, and evaluation semantics must be explicit.**
6. **Natural-language Mandate text does not become a Formal Constraint solely because Polaris can interpret it. Formalization must be explicit and authoritative.**
7. **Only Formal Constraints may produce deterministic Mandate satisfaction or violation results.**
8. **Missing or stale required facts may make a Formal Constraint evaluation indeterminate without making the constraint itself interpretive.**
9. **Investment Mandate assessment must not be collapsed into a single Boolean that hides the distinction between Objectives, Principles, Formal Constraints, and Exceptions.**
10. **Polaris may recommend an action that conflicts with an Investment Principle or violates a Formal Constraint, provided the conflict and resulting authority consequences are explicit.**
11. **A Mandate Exception is separate from the Investment Mandate and authorizes a scoped departure from a Formal Constraint without changing that constraint or its violation result.**
12. **Mandate Exceptions need not be exhaustively anticipated in advance; they may arise from concrete investment decisions.**
13. **Polaris may propose or justify a Mandate Exception but does not gain authority to authorize one from its own Recommendation.**
14. **Mandate Exception ≠ Mandate Amendment ≠ noncompliant Human Investment Decision.**
15. **Whether a Formal Constraint is exceptionable and who may authorize an Exception belongs to the Investment Authority Regime.**
16. **A multi-Portfolio investment decision evaluates each Portfolio against its own applicable Mandate and any Portfolio-specific Exceptions.**
17. **Historical decisions must preserve the Mandate version, Formal Constraint results, interpretive assessments, and Mandate Exceptions that actually applied at decision time.**

## Resolved decision scope, subject, and canonical decision terminology

The decision-layer stress tests now resolve `Decision Scope`, `Decision Subject`, `Investment Decision`, and `Human Investment Decision`. These semantics are canonicalized in [`../../CONTEXT.md`](../../CONTEXT.md).

This section supersedes earlier discovery-era passages in this document that describe `Investment Decision`, Decision Scope, or Decision Subject as unresolved or that treat `Portfolio Decision` as the preferred canonical consequential-decision noun. Those earlier passages are retained as discovery history until the broader decision lifecycle pass reconciles the remaining identity, lifecycle, and product-document language.

### Decision Scope

Decision Scope answers:

```text
Which Portfolio or Portfolios bear the direct investment consequences of this decision?
```

A scoped Portfolio contributes more than analytical context. Its Portfolio State, applicable Investment Mandate, Formal Constraints, Risk, and any Mandate Exceptions are directly relevant to evaluating the decision's consequences.

A Portfolio that is merely consulted as Evidence or contextual comparison does not become part of Decision Scope solely because it influenced reasoning.

A multi-Portfolio Investment Decision retains each Portfolio's independent state and Mandate semantics. Scope does not create a synthetic combined Portfolio or synthetic shared Mandate.

Decision Scope may be unresolved while decision work is being initiated. Polaris may recognize a Decision Need before the applicable Portfolio is known, but a final Capital-Relevant Recommendation or Human Investment Decision must not silently invent Portfolio applicability.

### Decision Subject

Decision Subject answers:

```text
What investment matter is actually being judged?
```

The Subject is not restricted to one entity type. It may concern:

* an existing Position;
* whether to establish exposure through a Financial Instrument;
* an Exposure;
* an Allocation;
* Portfolio Posture;
* a cross-Portfolio capital allocation;
* or another coherent investment matter.

A Decision Subject may be composite when its elements form one mutually dependent tradeoff. If component judgments can be resolved independently without materially changing one another, they should normally be separate Investment Decisions rather than one artificially broad Subject.

For example, deciding how to allocate one fixed amount of new capital between AAPL and MSFT may be one coherent composite Subject because the alternatives compete for the same capital. Independently deciding whether to increase AAPL and whether to reduce an unrelated XOM Position would normally be two decisions unless a real dependency makes them one judgment.

The Subject is also distinct from the thing that triggered or implements the decision. For example:

```text
Evidence
CPI surprise

Analysis
inflation / rates implications

Decision Subject
equity-beta Exposure

Decision Scope
Portfolio A

Action Instrument
ES futures
```

The thing that caused the decision, the thing analyzed, the thing being judged, the Portfolio affected, and the Financial Instrument used to implement the result may all be different.

The same Decision Subject can recur in later Investment Decisions under different circumstances. Subject therefore contributes meaning but does not establish Investment Decision identity by itself.

### Investment Decision versus portfolio-independent analysis

Portfolio-independent investment intelligence can exist without an Investment Decision.

For example:

```text
Is AAPL undervalued?
→ investment analysis / assessment

Should Portfolio A establish AAPL exposure?
→ Investment Decision
```

The distinction is consequential Portfolio applicability. An Investment Decision is an identified unit of investment judgment whose potential capital consequences are evaluated within one or more Portfolio scopes.

### Canonical decision noun

`Investment Decision` is now the canonical general noun for consequential investment judgment in Polaris.

`Portfolio Decision` is too narrow because one coherent decision may span several Portfolios or may concern a Subject such as Exposure, cross-Portfolio capital allocation, or another investment matter rather than the Portfolio as an object.

For example:

```text
Decision
Move capital from Portfolio A to Portfolio B.

Decision Scope
Portfolio A + Portfolio B

Decision Subject
cross-Portfolio capital allocation
```

Calling that the Portfolio Decision of A or B would assign ownership that the domain does not actually have. `Investment Decision` preserves the investment meaning while allowing Decision Scope to express the affected Portfolios explicitly.

### Investment Decision and Human Investment Decision

`Investment Decision` names the durable, identifiable consequential decision lifecycle. It may exist while the matter is still unresolved:

```text
Investment Decision D-47
Decision Subject: AAPL exposure
Decision Scope: Portfolio A
Recommendation: available
Human judgment: pending
```

This usage is consistent with ordinary language: there can be an investment decision to make before the choice has been made.

A Human Investment Decision is the attributable human judgment within that lifecycle. It may select, modify, reject, defer, or otherwise dispose of the consequential choice.

The distinction is therefore:

```text
Investment Decision
The enduring, identified consequential decision concern and lifecycle.

Human Investment Decision
The attributable human judgment made within that lifecycle.
```

No additional lifecycle noun such as `Decision Case` is introduced because the approved distinction is sufficient and a second noun would add conceptual weight without solving a demonstrated ambiguity.

### Frozen decision-scope and subject invariants

The following invariants are now accepted:

1. **Decision Scope identifies the Portfolio or Portfolios whose investment state, Mandates, capital, and consequences are directly governed by an Investment Decision.**
2. **A Portfolio used only as Evidence or analytical context is not automatically part of Decision Scope.**
3. **A multi-Portfolio Investment Decision preserves each scoped Portfolio's independent Portfolio State, Investment Mandate, Formal Constraints, Risk, and applicable Exceptions.**
4. **Decision Subject identifies the investment matter whose disposition is being judged; it is not restricted to a Financial Instrument, Position, or Portfolio.**
5. **A Decision Subject may concern an existing Position, establishing exposure through a Financial Instrument, an Exposure, Allocation, Portfolio Posture, or another coherent investment matter.**
6. **A Decision Subject may be composite when its elements form one mutually dependent investment judgment; independently resolvable matters should normally be separate Investment Decisions.**
7. **Decision Subject ≠ Decision Scope.**
8. **Decision Subject ≠ Evidence.**
9. **Decision Subject ≠ Action Instrument or Proposed Action.**
10. **The thing analyzed, thing decided, Portfolio affected, and instrument used to implement the decision may all differ.**
11. **The same Decision Subject may appear in multiple Investment Decisions through time; Subject alone does not establish Investment Decision identity.**
12. **Decision Scope may be unresolved during initiation, but final Capital-Relevant Recommendation or Human Investment Decision must not silently assume an unresolved Portfolio scope.**
13. **Portfolio-independent investment analysis may be Investment Intelligence or assessment without yet constituting an Investment Decision.**
14. **`Investment Decision` is the canonical general consequential-decision noun because one decision may span several Portfolios or concern a Subject other than a Portfolio itself.**
15. **`Investment Decision` names the durable identified decision lifecycle while `Human Investment Decision` names the attributable human judgment within it; no additional lifecycle noun is warranted unless later scenario testing exposes a real ambiguity.**

## Resolved Attention and temporal observation semantics

The Attention boundary is now resolved in two dimensions: **what Polaris may observe** and **when information about an observed subject becomes available or sufficiently current for investment use**. These semantics are canonicalized in [`../../CONTEXT.md`](../../CONTEXT.md).

### Attention is bounded by both subject and time

Attention does not imply universal financial-market surveillance, and it also does not imply one universal polling interval.

Polaris evaluates only information and investment context it is configured or otherwise authorized to observe. Within that bounded universe, different subjects and conditions may have different temporal semantics based on their source, Portfolio relevance, user configuration, and current decision use.

Conceptually:

```text
observable subject / condition
        +
normal temporal observation semantics
        +
current Portfolio and decision context
        ↓
newly available or newly due information
        ↓
Attention
        ↓
possible Decision Need
```

The question is therefore not `How often does Attention run?` as one global product cadence. The meaningful question is `When should information about this subject become available or be reconsidered, and how fresh must it be for this investment use?`

### Observation Cadence

Observation Cadence describes the normal temporal pattern for obtaining or reconsidering information about an observed subject or condition.

Valid temporal modes include:

```text
event-driven
new authoritative information itself causes reconsideration

periodic
information is refreshed or reconsidered on a recurring cadence

scheduled
a known time or calendar event makes review due

on-demand
information is obtained when explicit decision work requires it

condition-driven
a prior state or decision condition becoming true makes review due
```

These modes are not mutually exclusive. One observed subject may legitimately have several modes for different information roles.

There is no canonical `one minute`, `five minute`, or `one hour` frequency for Polaris as a whole. Even the same market subject may have a different normal cadence for a long-horizon Portfolio than for a tactical Portfolio.

### Observation Cadence versus Freshness Requirement

Observation Cadence and Freshness Requirement answer different questions:

```text
Observation Cadence
How often is this information normally obtained or reconsidered?

Freshness Requirement
How current must this information be for this particular investment use?
```

For example, SPY market data may normally be observed every five minutes while an active hedge decision requires a price observation no more than one minute old.

An active Investment Decision may therefore tighten the information freshness required for its reasoning without permanently changing the normal Observation Cadence for that subject.

If an available source cannot satisfy the applicable Freshness Requirement, Polaris must preserve the resulting evidence insufficiency. A delayed or stale observation does not become current merely because it is the newest value Polaris has.

### Temporally composed decision context

Polaris does not have one globally synchronized `current state` that refreshes all information in lockstep.

A decision context may legitimately combine facts and measures such as:

```text
market observation       @ 10:31:00
VIX observation          @ 10:30:47
Portfolio Position fact  @ 10:30:10
Exposure measure         @ 10:30:10
CPI observation          @ 08:30:00
Investment Mandate       effective since an earlier date
```

Representing those facts together does not imply simultaneous observation. Each fact or derived measure retains its own as-of time, provenance, and freshness.

This temporal composition is important both for current decision quality and for later historical reconstruction of what was knowable at decision time.

### Information velocity versus decision velocity

Observation state may change much more frequently than Investment Decision state.

A high-frequency stream of price observations must not automatically generate an equal-frequency stream of Decision Needs, Investment Decisions, or decision revisions.

Conceptually:

```text
many observations
        ↓
Attention filters relevance
        ↓
possibly no Decision Need
        ↓
or one meaningful change to existing decision work
```

An Investment Decision changes when newly available information materially affects that decision's work, not merely because another observation exists.

Attention therefore separates **information velocity** from **decision velocity**.

### Frozen Attention and temporal-observation invariants

The following invariants are now accepted:

1. **Attention is bounded by what Polaris is configured or otherwise authorized to observe; it does not imply universal surveillance.**
2. **Attention has no single global frequency.**
3. **Observation Cadence is specific to the observed subject or condition and may vary by source, Portfolio context, configured investment use, and current decision context.**
4. **Observation may be event-driven, periodic, scheduled, on-demand, condition-driven, or a combination of those modes.**
5. **Observation Cadence ≠ Freshness Requirement.**
6. **An active Investment Decision may require fresher information than the normal Observation Cadence without permanently changing that cadence.**
7. **If available information cannot satisfy the applicable Freshness Requirement, Polaris must preserve the insufficiency rather than treating stale information as current.**
8. **Newly available or newly due information may cause Attention to evaluate without requiring all Polaris state to refresh in lockstep.**
9. **Polaris decision context is temporally composed: facts and derived measures retain their own as-of times, provenance, and freshness.**
10. **Representing facts together does not imply that they were observed or recomputed simultaneously.**
11. **Observation state may refresh frequently while Investment Decision state changes only when information materially affects decision work.**
12. **Attention separates information velocity from decision velocity; observation frequency does not determine Decision Need or Investment Decision frequency.**

## Resolved Investment Decision identity and lifecycle semantics

The Investment Decision identity/lifecycle pass is now resolved sufficiently to distinguish same-versus-new decision identity, substantive judgment resolution, Deferral, Review Conditions, Supersession, and the effect of external Portfolio changes. These semantics are canonicalized in [`../../CONTEXT.md`](../../CONTEXT.md).

This section supersedes discovery-era language that treats reopening a substantively resolved decision as the default response to renewed judgment. Historical decisions remain intact; renewed judgment after substantive resolution creates a new causally linked Investment Decision.

### Identity follows the unresolved investment choice

Investment Decision identity is explicit and durable. It is not computed from mutable decision content such as Decision Subject, Decision Scope, Evidence, Recommendation, workflow execution, Risk, or current Portfolio State.

The semantic continuity test is whether Polaris is still attempting to resolve the same coherent unresolved investment choice.

For example:

```text
D-100
Decision Need:
Should Portfolio A reduce SPY Exposure?

09:00  Recommendation: Hold
10:00  SPY falls
10:30  VIX rises
11:00  new macro Evidence arrives
11:15  Recommendation: Reduce 15%
```

Those changes remain part of D-100 while they are still attempts to answer the same unresolved choice.

Therefore Evidence refresh, Evidence staleness, changed Portfolio State, changed Risk, revised reasoning, or a revised or reversed Recommendation do not by themselves create new Investment Decision identity.

Decision Subject and Decision Scope may also refine while identity remains stable when the refinement continues to describe the same coherent unresolved choice. Discovery of an independently resolvable investment concern creates a separate Decision Need instead.

### Deferral versus deliberate inaction

Deferral and deliberate no-action can both produce no immediate Portfolio change, but their meanings are opposite with respect to resolution.

```text
Deferral
We do not yet have the substantive answer.
→ Decision Need remains unresolved.

Deliberate hold / no-action
Our substantive answer is to leave the Portfolio unchanged.
→ investment judgment may be resolved.
```

A Human Investment Decision can therefore be attributable without substantively resolving the Investment Decision. A human may reject a Recommendation and request further analysis, or defer judgment until a catalyst, while the underlying Decision Need remains active.

Recommendation rejection is likewise not enough to establish resolution. `Reject the 20% reduction and reduce 5% instead` resolves the investment choice; `reject that Recommendation and give me more analysis` does not.

### Awaited condition versus Review Condition

The lifecycle meaning of a condition depends on whether the Investment Decision is unresolved or substantively resolved.

For a deferred unresolved decision:

```text
D-200
Human Investment Decision:
Defer until CPI.

CPI becomes available
        ↓
Attention
        ↓
resume D-200
```

The awaited event permits continued work on the same unresolved Investment Decision.

For a substantively resolved decision:

```text
D-201
Human Investment Decision:
Hold SPY.

Review after CPI.
```

When CPI arrives, the Review Condition causes Attention to reconsider whether a renewed Decision Need exists. It does not reopen D-201 and does not automatically create a new decision.

If renewed judgment is warranted:

```text
D-201 remains historical
        ↓ causal lineage
D-202 new Investment Decision
```

This preserves the original decision-time Evidence, Recommendation, Mandate, human judgment, and later evaluation context.

### Repeated questions and renewed judgment

Repeated wording does not establish Investment Decision identity.

A repeated user question while the same investment choice is already unresolved normally refers to the same Investment Decision and may request current status, fresher Evidence, or a revised Recommendation.

After a prior decision has been substantively resolved, a similar user request can mean either retrieval (`what did we decide?`) or renewed judgment (`should we make this choice now?`). Retrieval does not create a Decision Need. An explicit request for renewed judgment may create a new Decision Need even when external market conditions have not materially changed.

### Judgment resolution versus lifecycle completion

Substantive resolution of the investment judgment is a milestone within the Investment Decision lifecycle rather than necessarily the lifecycle's end.

Conceptually:

```text
Decision Need
    ↓
Investment Decision
    ↓
Evidence / reasoning / Recommendation
    ↓
Human Investment Decision
    ↓
substantive judgment resolved
    ↓
Action Intent
    ↓
External Activity
    ↓
Reconciliation
    ↓
Outcome
    ↓
Evaluation
```

A later Investment Decision may begin while the earlier decision remains active for action continuity, reconciliation, Outcome, or Evaluation. Decision lifecycles therefore need not be globally serialized.

Once substantive judgment has been resolved, later renewed judgment creates a new causally linked Investment Decision rather than mutating the old one. This keeps Durable Decision Memory historically faithful.

### External Portfolio changes while judgment is pending

External Portfolio changes do not directly determine Investment Decision identity. They flow through Attention because the changed reality may have several different meanings.

An external change may:

* update Portfolio State while the same unresolved choice remains meaningful;
* remove the unresolved choice so that no further investment judgment is required;
* or create a different Decision Need in response to the new Portfolio condition.

For example, if D-300 asks whether SPY should be reduced from 60% to 40% and external activity changes the Portfolio to 50%, the same D-300 may remain meaningful with updated consequences. If external activity changes the Portfolio to 40%, the original choice may no longer require judgment.

Polaris must not fabricate a Human Investment Decision merely because externally authoritative Portfolio State changed in a way that made the pending question moot. The domain semantics of that disposition are accepted, but its canonical name remains intentionally unresolved pending terminology testing.

A changed external state may simultaneously make one pending decision unnecessary and create a new Decision Need. For example, external establishment of an unexpectedly large AAPL Position may make `should we establish AAPL exposure?` moot while creating the separate question `should we retain or reduce this exposure?`.

### Supersession

Supersession is a relationship between Investment Decisions rather than destructive replacement.

An unresolved narrow decision may be superseded by a broader decision that makes the earlier question no longer independently meaningful. A previously resolved decision may also be superseded as the current operative investment basis by a later decision.

In either case:

```text
earlier Investment Decision
        ↓ superseded by
later Investment Decision
```

Both remain durable. Supersession does not undo historical resolution, Recommendation history, Human Investment Decisions, or other decision-time facts.

### Frozen Investment Decision identity/lifecycle invariants

The following invariants are now accepted:

1. **Investment Decision identity is explicit and durable; it is not derived from Decision Subject, Decision Scope, Evidence, Recommendation, workflow execution, or current Portfolio State.**
2. **Identity is preserved while work continues to resolve the same coherent unresolved investment choice.**
3. **New Evidence, changed Portfolio State, changed Risk, revised reasoning, or revised/reversed Recommendation do not by themselves create a new Investment Decision.**
4. **Observation frequency and Evidence refresh frequency do not determine Investment Decision frequency.**
5. **Deferral leaves the underlying Decision Need unresolved and permits the same Investment Decision to resume later.**
6. **Deliberate hold/no-action is a substantive investment judgment and may resolve the Decision Need.**
7. **A Human Investment Decision may be attributable without substantively resolving the Investment Decision, as with Deferral or Recommendation rejection accompanied by a request for further judgment.**
8. **Recommendation rejection ≠ Investment Decision resolution.**
9. **Resolution of the investment judgment is a milestone within the Investment Decision lifecycle, not necessarily lifecycle completion.**
10. **After substantive judgment resolution, a renewed Decision Need creates a new causally linked Investment Decision rather than reopening and rewriting the resolved one.**
11. **A Review Condition on a resolved decision causes Attention to reconsider whether a new Decision Need exists; it does not itself reopen the old decision or automatically create a new one.**
12. **A condition awaited by a deferred unresolved decision may resume that same Investment Decision rather than creating a new one.**
13. **Repeated wording or repeated user questions do not determine identity; an active unresolved choice normally remains the same decision, while an explicit later request for renewed judgment may create a new Decision Need.**
14. **Evidence staleness or refresh changes readiness and reasoning within a decision without itself changing identity.**
15. **External Portfolio changes flow through Attention; they may update the same unresolved decision, eliminate its remaining Decision Need, or create a different Decision Need.**
16. **Polaris must not invent a Human Investment Decision merely because external Portfolio State changed in a way that made a pending choice moot.**
17. **An Investment Decision may become unnecessary because external circumstances remove the unresolved choice; that disposition is distinct from substantive Human Investment Decision resolution.**
18. **Supersession preserves both Investment Decisions and their history; it records that another decision displaced the earlier decision's continuing applicability or operative basis.**
19. **Supersession does not undo a prior substantive resolution.**
20. **Decision Subject or Decision Scope may refine while identity remains stable when the refinement continues to represent the same coherent unresolved choice; independently arising investment choices require separate Decision Needs and Investment Decisions.**

## Illustrative scenario fixtures

The scenarios in this section preserve semantically distinct examples that materially contributed to the frozen domain model but were previously condensed or left only in conversational discovery. They are **illustrative, not exhaustive**. They do not narrow the canonical definitions in [`../../CONTEXT.md`](../../CONTEXT.md), and repeated examples that prove the same boundary are intentionally not duplicated.

A scenario belongs here when changing or removing it would make an important domain distinction easier to misunderstand. These examples should therefore be treated as durable semantic fixtures when later requirements, architecture, and implementation are evaluated against the domain.

### Portfolio identity survives mutable Portfolio state

A Portfolio can remain the same continuing investment responsibility through substantial state change:

```text
Portfolio A
Day 1: invested across equities
Day 20: entirely cash
Day 40: moved to a different broker/account
Day 80: Mandate revised
```

None of those facts alone creates a new Portfolio. A new Portfolio identity requires an explicit identity transition such as an intentional split, merge, closure, or fundamental reconstitution.

**Distinction proved:** Portfolio identity ≠ current holdings, Account, broker, or Mandate version.

### Account boundary and Portfolio Boundary can cross in both directions

One Portfolio can span operational accounts:

```text
Portfolio A
├── Brokerage Account 1
└── Brokerage Account 2
```

One operational account can also contain interests attributed to several Portfolios:

```text
Brokerage Account 9
100 AAPL long
        │ attribution
        ├── 60 AAPL → Portfolio A
        └── 40 AAPL → Portfolio B
```

The 100-share external holding is not duplicated. Polaris establishes non-overlapping Portfolio attribution over the externally authoritative account fact.

**Distinction proved:** Account Boundary ≠ Portfolio Boundary, and operational indivisibility does not require indivisible Portfolio attribution.

### Position Direction does not determine Exposure direction

Consider a long put option:

```text
Position Direction:
Long

Financial Instrument:
AAPL put option

Underlying-equity Exposure:
negative
```

The Portfolio is Long the option contract while being economically exposed to declines in the underlying equity.

**Distinction proved:** Long/Short Position Direction describes the relationship to the Financial Instrument; it does not by itself determine the sign of every resulting Exposure.

### Several Strategies remain subordinate to one Portfolio Mandate

Suppose Portfolio A uses two simultaneous Strategies:

```text
Investment Mandate:
Technology Exposure <= 30%

Core Strategy contribution:
20% technology Exposure

Tactical Strategy contribution:
18% technology Exposure
```

Each Strategy viewed in isolation is below the 30% boundary, but the resulting Portfolio has 38% technology Exposure and violates the Formal Constraint.

**Distinction proved:** the Investment Mandate ultimately constrains the Portfolio and resulting Portfolio State, not each Strategy independently.

### The same Evidence can imply different actions under different Mandates

Suppose a materially hot CPI release affects two Portfolios:

```text
Portfolio A
Purpose: retirement accumulation
Horizon: long
Leverage: prohibited

Portfolio B
Purpose: tactical return
Horizon: shorter
Limited leverage: permitted
```

The CPI Evidence can be identical while the appropriate Portfolio consequences differ. Portfolio A might retain its long-horizon exposure while Portfolio B reduces beta or adds a permitted hedge.

**Distinction proved:** a multi-Portfolio Investment Decision evaluates each scoped Portfolio against its own Portfolio State and applicable Investment Mandate; there is no synthetic shared Decision Mandate.

### Principle tension and Formal Constraint violation are different facts

Consider two Mandate statements:

```text
Investment Principle:
Avoid excessive single-stock concentration.

Formal Constraint:
Single Position <= 15% of Portfolio NAV.
```

A Recommendation to increase AAPL to 18% can simultaneously produce:

```text
Principle assessment:
meaningful tension

Formal Constraint evaluation:
VIOLATED
```

The first is interpretive. The second is deterministic when the required facts are sufficiently current and authoritative.

**Distinction proved:** Investment Principle tension ≠ Formal Constraint violation.

### Natural-language force does not create Formal Constraint precision

The statement:

```text
No leverage.
```

sounds absolute but is not yet necessarily machine-evaluable. It may mean any of several things:

```text
no margin borrowing

gross economic Exposure / NAV <= 1.0x

no leveraged ETFs

no futures

no option structures with leveraged payoff
```

Polaris may help a human formalize the intended meaning, but an LLM interpretation cannot silently become authoritative Mandate semantics.

**Distinction proved:** emphatic natural language ≠ explicit Formal Constraint semantics.

### Mandate Exception, Mandate Amendment, and noncompliant human choice preserve different history

Start with:

```text
Formal Constraint:
AAPL <= 10%

Polaris Recommendation:
AAPL = 14%

Constraint result:
VIOLATED
```

Three later outcomes mean different things:

```text
Mandate Exception
Permit AAPL <= 14% for D-47 only.
Underlying Mandate remains 10%.

Mandate Amendment
Change governing maximum from 10% to 15%.

Noncompliant Human Investment Decision
Human chooses 14% with no applicable Exception.
Underlying Mandate remains 10%; violation remains unauthorized.
```

**Distinction proved:** Exception changes scoped admissibility, Amendment changes the governing Mandate, and human behavior changes neither retroactively.

### A contextual Portfolio does not automatically enter Decision Scope

Suppose Polaris is deciding whether Portfolio A should increase AAPL. Portfolio B is consulted because its technology Exposure provides useful comparison:

```text
Decision Subject:
increasing AAPL exposure

Decision Scope:
Portfolio A

Contextual Portfolio:
Portfolio B
```

Unless the judgment directly governs Portfolio B's state or consequences, Portfolio B does not enter Decision Scope merely because its facts influenced the reasoning.

**Distinction proved:** analytical relevance ≠ Decision Scope membership.

### A Decision Subject can concern exposure that does not yet exist as a Position

Suppose Portfolio A owns no AAPL:

```text
Question:
Should Portfolio A establish AAPL exposure?

Current Position:
none

Decision Subject:
establishing AAPL exposure
```

Polaris does not need to manufacture a `Prospective Position` domain entity merely to represent the question. A Position comes into existence only when the Portfolio actually has the attributable holding or obligation.

**Distinction proved:** Decision Subject may concern a prospective investment matter without pretending its resulting Position already exists.

### The same Decision Subject and Scope can identify different Investment Decisions through time

```text
January
Portfolio A
Should we increase AAPL exposure?
→ D-100

June
Portfolio A
Should we increase AAPL exposure now?
→ D-245
```

The visible Subject and Scope can be the same while the Decision Needs, evidence context, and decision-time circumstances differ.

**Distinction proved:** Decision Subject + Decision Scope do not determine Investment Decision identity.

### Dramatic information does not necessarily create a Decision Need

Suppose CPI surprises sharply, but Portfolio A has a ten-year horizon, its current posture remains appropriate, no relevant thesis is invalidated, and no Mandate or Risk concern now requires judgment:

```text
Market significance:
high

Attention:
relevant information

Decision Need:
none
```

Now contrast a small AAPL price increase:

```text
Before move:
AAPL = 9.9% of Portfolio NAV

Formal Constraint:
AAPL <= 10%

After small move:
AAPL = 10.1%
```

The market move is minor but can create a genuine unresolved Portfolio-relevant choice about whether and how to address the violated boundary.

**Distinction proved:** external drama or magnitude ≠ Decision Need significance. Attention asks whether Portfolio-relevant judgment is now required.

### Human initiation does not require a universal materiality threshold

A human may explicitly ask:

```text
Should Portfolio A sell one share of AAPL?
```

The economic magnitude may be trivial, but it can still be a legitimate Investment Decision because the authorized human explicitly requests Portfolio-relevant judgment.

**Distinction proved:** Decision Need is not governed by one universal capital-impact score or minimum dollar threshold.

### Deterministic and interpretive Attention preserve different authority

A deterministic attention criterion might be:

```text
If Technology Exposure > 30%, evaluate.
```

Given sufficiently current authoritative facts, the criterion can deterministically match or not match.

An interpretive Attention assessment might instead be:

```text
New AAPL evidence materially challenges
an assumption supporting the current thesis.
```

That assessment can reasonably conclude that renewed judgment appears warranted, but it must preserve that the relevance determination is interpretive rather than a deterministic rule match.

**Distinction proved:** Attention may be deterministic or interpretive; interpretation does not masquerade as formal authority.

### Scheduled review is an Attention event, not automatic decision creation

Suppose a quarterly Portfolio review becomes due:

```text
Scheduled review
        ↓
Attention
```

If the review finds the current posture and its supporting assumptions still materially sound:

```text
new Decision Need:
none
```

If the review finds that concentration, assumptions, or current conditions now require a fresh choice:

```text
new Decision Need:
yes
        ↓
new Investment Decision
```

**Distinction proved:** review activity ≠ Investment Decision creation.

### Observation Cadence depends on investment use, not only observed symbol

The same SPY market information can legitimately have different normal cadence:

```text
Portfolio A
10-year horizon
SPY observation cadence:
hourly or daily may be adequate

Portfolio B
shorter tactical horizon
SPY observation cadence:
minutes may be appropriate
```

The symbol alone does not define the temporal policy.

**Distinction proved:** Observation Cadence depends on source and Portfolio/investment context, not a universal per-instrument frequency.

### An active decision can require fresher information than normal cadence

Suppose SPY is normally observed every five minutes, but an active hedge decision requires:

```text
SPY price age <= 60 seconds
VIX age <= 60 seconds
Portfolio State age <= 2 minutes
```

Polaris may obtain fresher data for that decision without permanently changing the normal five-minute cadence.

If the available source provides only fifteen-minute-delayed SPY data:

```text
Freshness Requirement:
<= 60 seconds

Available observation:
15 minutes delayed

Result:
insufficiently fresh
```

The newest available value is not silently promoted to `current` simply because no better value is available.

**Distinction proved:** Observation Cadence ≠ Freshness Requirement, and source limitation becomes evidence/readiness insufficiency.

### High information velocity does not imply high decision velocity

A one-minute market feed may produce roughly hundreds of observations during a trading session:

```text
many SPY observations
        ↓
Attention evaluations
        ↓
possibly no Decision Need
```

Polaris must not create or revise an Investment Decision merely because another price tick arrived. Decision state changes only when information materially affects the decision work.

**Distinction proved:** information velocity ≠ decision velocity.

### Repeated wording can mean continuation, retrieval, or renewed judgment

Suppose an unresolved D-500 already asks:

```text
Should Portfolio A increase AAPL?
```

Repeating the same question five minutes later normally refers to the same unresolved Investment Decision and may request fresher analysis.

After D-500 has been substantively resolved, the same words can mean different things:

```text
What did we decide about increasing AAPL?
→ retrieval of D-500
→ no new Decision Need

Given current conditions, should we increase AAPL now?
→ renewed judgment
→ possible new Decision Need and D-501
```

**Distinction proved:** repeated text does not determine Investment Decision identity; user intent and decision continuity do.

### Supersession can displace unresolved or resolved decisions without rewriting either

Unresolved narrow decision:

```text
D-600
Should Portfolio A increase AAPL?
```

A broader later decision may make it no longer independently meaningful:

```text
D-601
Should Portfolio A eliminate individual technology stocks
and move to broad-index exposure?

D-600
superseded by D-601
```

A resolved decision can also lose continuing applicability:

```text
D-610
Human Investment Decision:
Hold AAPL.

later D-611
Human Investment Decision:
Exit all individual equities.

D-610
historically resolved, later superseded by D-611
```

**Distinction proved:** Supersession changes continuing applicability or operative basis; it does not delete, reopen, or falsify historical resolution.

### Investment Decision lifecycles can overlap

Suppose D-700 has a substantively resolved Human Investment Decision and is still awaiting external reconciliation:

```text
D-700
judgment resolved
Action Intent recorded
external activity / reconciliation pending
```

A new market shock may independently create D-701 before D-700 reaches Outcome or Evaluation:

```text
D-700 ── continuing reconciliation/evaluation

D-701 ── new Decision Need and judgment work
```

**Distinction proved:** substantive judgment resolution ≠ lifecycle completion, and Investment Decision lifecycles need not be globally serialized.

## Resolved External Resolution semantics

`External Resolution` is now the canonical name for the previously unnamed lifecycle disposition in which an unresolved Investment Decision loses its Decision Need because changed circumstances remove the investment choice before a Human Investment Decision substantively resolves it. These semantics are canonicalized in [`../../CONTEXT.md`](../../CONTEXT.md).

This section supersedes earlier references in this document that describe the disposition's canonical name as unresolved or use `Obviated` as a provisional label.

### External Resolution resolves the Decision Need, not the judgment

External Resolution means that further investment judgment is no longer required because the original choice no longer exists. It does **not** mean that somebody made the missing investment judgment.

For example:

```text
D-800
Decision Need:
Should Portfolio A reduce SPY from 60% to 40%?

Human Investment Decision:
none yet

External activity:
SPY is independently reduced to 40%.

        ↓

Decision Need:
no longer exists

D-800:
Externally Resolved
```

Polaris records the changed externally authoritative Portfolio State and the cause of the disposition. It does not fabricate `Human Investment Decision: reduce SPY to 40%` merely because the observed Portfolio now has that state.

### Changed circumstances must eliminate the choice

External change alone is insufficient.

If D-801 asks whether SPY should be reduced from 60% to 40% and independent activity changes the Portfolio only to 50%, the original investment choice can remain meaningful:

```text
D-801
SPY now 50%
Question remains:
Should Portfolio A reduce SPY further to 40%?

→ same unresolved Investment Decision
→ not Externally Resolved
```

If the changed circumstances remove the choice itself, External Resolution may apply.

This distinction also covers opportunities that cease to exist:

```text
Decision Need:
Should Portfolio A acquire Financial Instrument X?

Before judgment:
Instrument X is permanently delisted and can no longer be acquired.

→ original choice no longer exists
→ Externally Resolved
```

External Resolution does not require that the contemplated or recommended outcome was achieved. It requires only that the original unresolved Decision Need has ceased to exist.

### Price or Evidence changes do not automatically resolve a decision

Suppose the question is broadly:

```text
Should Portfolio A buy AAPL?
```

and AAPL gaps from $180 to $220 before judgment. That new price materially changes Evidence and expected consequences, but the same investment choice may still require judgment. The decision therefore remains unresolved unless its actual Decision Need was specifically tied to an opportunity that has disappeared, such as `should we acquire AAPL below $185 while that opportunity exists?`.

**Distinction proved:** changed attractiveness or Evidence ≠ External Resolution unless the Decision Need itself disappears.

### `External` describes provenance relative to the judgment

`External` does not mean only `outside Polaris`.

Circumstances external to the pending judgment can include externally initiated Portfolio activity, a Position disappearing, a Financial Instrument becoming unavailable, a time-sensitive opportunity expiring, or a Portfolio Boundary changing so that the original scoped choice no longer exists.

The semantic question is whether the cause lies outside the unresolved act of investment judgment and eliminates the choice that required that judgment.

### External Resolution versus other lifecycle dispositions

The distinctions are deliberately sharp:

```text
Deferral
Choice still exists.
Judgment still required.
Resolution postponed.

Deliberate hold / no-action
Choice still existed.
Human made the substantive judgment that no change is warranted.

Supersession
Another Investment Decision displaces the earlier decision's continuing applicability or operative basis.

Cancellation / withdrawal
Decision work is stopped, but the underlying investment choice may still exist.

External Resolution
Changed circumstances eliminate the underlying Decision Need before substantive Human Investment Decision resolution.
```

A user saying `never mind; stop evaluating this` therefore does not by itself create External Resolution when the underlying investment choice remains real. Likewise, a later broader Investment Decision that displaces a narrower one is Supersession rather than External Resolution.

### External Resolution can expose a different Decision Need

The external circumstances that resolve one Investment Decision may simultaneously create another.

For example:

```text
D-810
Decision Need:
Should Portfolio A establish AAPL exposure?

External activity:
AAPL Position unexpectedly appears at 20% of Portfolio NAV.

D-810:
Externally Resolved
because establishing AAPL exposure is no longer the unresolved choice.

Attention:
20% AAPL Position may require judgment.

New Decision Need:
Should Portfolio A retain or reduce this AAPL exposure?

        ↓
D-811
```

External Resolution therefore does not suppress Attention to the new Portfolio reality.

### Frozen External Resolution invariants

The following invariants are now accepted:

1. **External Resolution occurs only when changed circumstances eliminate the unresolved Decision Need itself; an external change that merely alters Evidence, Portfolio State, or available alternatives does not qualify.**
2. **External Resolution resolves the need for further judgment, not the investment judgment itself.**
3. **An Externally Resolved Investment Decision has no inferred Human Investment Decision unless an attributable Human Investment Decision was independently observed.**
4. **External Resolution does not imply that Polaris's Recommendation was followed or that the preferred Portfolio outcome occurred.**
5. **`External` means outside the unresolved investment judgment, not necessarily outside Polaris or outside the Portfolio domain.**
6. **External Resolution ≠ Deferral: Deferral preserves an unresolved Decision Need; External Resolution eliminates it.**
7. **External Resolution ≠ deliberate hold/no-action: hold/no-action is a substantive Human Investment Decision; External Resolution requires no such judgment.**
8. **External Resolution ≠ Supersession: Supersession records displacement by another Investment Decision; External Resolution results from changed circumstances eliminating the original choice.**
9. **External Resolution ≠ cancellation or withdrawal merely because someone chooses to stop decision work while the underlying investment choice remains.**
10. **The cause of External Resolution must be preserved so later evaluation can distinguish what changed from what Polaris recommended or a human decided.**

## Resolved Investment Recommendation nature and trading boundary

`Investment Recommendation` is now the canonical name for Polaris's preferred investment judgment within an Investment Decision. Existing product prose may continue to use `Recommendation` as shorthand, but the domain meaning is specifically an **Investment Recommendation**, not a trading-platform signal or market-facing Order. These semantics are canonicalized in [`../../CONTEXT.md`](../../CONTEXT.md).

### Investment Recommendation answers the economic question

An Investment Recommendation answers:

```text
What economic Portfolio disposition does Polaris prefer
for this Decision Need under the decision-time context available?
```

It may therefore express a preferred Portfolio Posture, Allocation, Exposure change, hedge, resize, entry or exit, deliberate hold or no-action, waiting posture, or another Portfolio-relevant disposition.

For example:

```text
Decision Need:
Should Portfolio A reduce equity-beta Exposure?

Investment Recommendation:
Reduce equity-beta Exposure from approximately 0.95 to 0.70.
Prefer hedging over selling the core SPY Position because the
longer-term thesis remains constructive while near-term downside
Risk has increased materially.
```

That is the canonical Polaris judgment. It is not yet an exact broker instruction.

### Strategy or model signal is not the Investment Recommendation

Polaris is not a NinjaTrader-style strategy engine in which a trading-strategy condition directly becomes the canonical product recommendation or an executable signal.

For example:

```text
Technical strategy observation:
20 EMA crosses above 50 EMA.

Strategy/model interpretation:
bullish signal or supporting hypothesis
```

That signal may become Evidence or contribute to a Strategy Hypothesis. Polaris still evaluates it against Decision Scope, Portfolio State, current Exposure, Risk, Investment Mandate, other Evidence, alternatives, and the active Decision Need.

The same bullish signal can therefore produce different Investment Recommendations:

```text
Portfolio A
under target equity Exposure
Risk acceptable
→ Investment Recommendation may increase Exposure

Portfolio B
already at maximum permitted equity Exposure
→ Investment Recommendation may hold

Portfolio C
material concentration / conflicting Evidence
→ Investment Recommendation may reduce or withhold action
```

**Distinction proved:** strategy signal ≠ Investment Recommendation.

### Economic disposition versus Proposed Action

An Investment Recommendation can be economically precise while remaining implementation-independent.

For example:

```text
Investment Recommendation:
Reduce Portfolio A equity-beta Exposure by approximately $540,000 notional.
```

Possible implementations may include:

```text
Proposed Action A:
Sell an appropriate amount of SPY.

Proposed Action B:
Short approximately 2 ES contracts.

Proposed Action C:
Use a defined-risk SPY put hedge.
```

Polaris may compare these alternatives and identify a preferred Proposed Action. If ES later becomes unavailable or unattractive, the Investment Recommendation can remain valid while the Proposed Action changes.

**Distinction proved:** preferred economic Portfolio disposition ≠ concrete implementation.

### Concrete quantity does not automatically make Polaris an execution engine

Polaris may calculate that approximately two ES contracts are needed to produce the desired beta reduction:

```text
Target economic change:
~$540,000 reduction in equity-beta Exposure

Current ES notional:
~$270,000 per contract

Suggested implementation:
short approximately 2 ES contracts
```

That quantity can be useful decision support and may form part of a Proposed Action. It does not become an Order merely because it is concrete.

The boundary is crossed when the instruction becomes market-facing execution such as:

```text
SELL 2 ES LIMIT 5325.25
STOP 5381.00
TARGET 5255.25
DAY
```

That describes exact order placement and management rather than the economic investment judgment.

### Price guidance versus exact order instruction

Price can matter to investment judgment without making Polaris an order-management system.

For example:

```text
Preferred entry region:
5320–5330

Reason:
above this region the expected hedge economics deteriorate materially
```

can be part of a human-reviewable trade setup or Proposed Action.

By contrast:

```text
Place SELL LIMIT order for 2 ES at 5325.25
```

is a market-facing execution instruction.

**Distinction proved:** investment price preference ≠ exact broker Order.

### Investment invalidation is not a stop order

A stop-like price can represent investment reasoning rather than an execution instruction.

For example:

```text
Investment invalidation:
If ES closes above 5380, the bearish hedge thesis is no longer supported.
```

or:

```text
Risk boundary:
Do not tolerate more than 0.5% Portfolio NAV loss from this hedge.
```

Those statements describe thesis validity or Portfolio Risk.

They are semantically different from:

```text
BUY 2 ES STOP 5381.00
```

which is an externally executed protective Order.

Likewise:

```text
Review / objective region:
5250–5270
```

is distinct from:

```text
BUY 2 ES LIMIT 5255.25
```

as a take-profit Order.

**Distinction proved:** investment invalidation / Risk boundary ≠ stop order, and investment objective / review condition ≠ take-profit order.

### Polaris may present a human-reviewable trade setup

The user-facing projection may legitimately look like a trade setup:

```text
Preferred investment action:
Hedge equity Exposure.

Suggested implementation:
Short approximately 2 ES.

Preferred entry region:
5320–5330.

Investment invalidation:
Above 5380 under the defined thesis condition.

Objective / review region:
5250–5270.

Portfolio Risk:
~0.45% NAV.

Expected horizon:
2–5 trading days.
```

The lines have different domain meanings even though they are presented together. The setup remains decision support for human judgment; it is not an authoritative broker Order ticket.

### Execution remains externally authoritative

The product boundary is therefore:

```text
Polaris decision domain
───────────────────────
Investment Recommendation
Proposed Action / implementation preference
investment invalidation and Risk conditions
Human Investment Decision
Action Intent

External execution domain
─────────────────────────
Order placement
routing
working-order state
fills and partial fills
stop orders
take-profit orders
exchange execution
```

Polaris may observe, associate, reconcile, and reason about the second group after the fact or while continuity is active, but external execution systems remain authoritative for what was actually submitted and executed.

### Frozen Investment Recommendation nature/boundary invariants

The following invariants are now accepted:

1. **`Investment Recommendation` is the canonical domain term; `Recommendation` is shorthand unless a narrower recommendation type is explicitly stated.**
2. **An Investment Recommendation expresses Polaris's preferred economic disposition of a Decision Need for the affected Portfolio or Portfolios under the decision-time context then available.**
3. **Investment Recommendation ≠ trading-strategy signal. A strategy or model signal may become Evidence or a hypothesis but does not directly become the canonical Polaris Investment Recommendation.**
4. **Investment Recommendation ≠ Order. Exact market-facing order placement and management are execution-domain responsibilities.**
5. **An Investment Recommendation may be economically precise, including target Portfolio Posture, Allocation, Exposure, hedge magnitude, or other Portfolio consequence, without prescribing one immutable implementation.**
6. **A Proposed Action is a concrete candidate implementation of an Investment Recommendation; a Proposed Action may change while the underlying economic Investment Recommendation remains valid.**
7. **Concrete approximate quantity, such as `short approximately 2 ES contracts`, may be legitimate Proposed Action guidance and does not by itself make Polaris an execution engine.**
8. **Polaris may present a human-reviewable trade setup containing implementation preference, approximate quantity, price region, investment invalidation, Risk boundary, objective, horizon, or review condition.**
9. **Investment price guidance ≠ exact Order price instruction.**
10. **Investment invalidation or Risk boundary ≠ stop order; investment objective or review condition ≠ take-profit order.**
11. **The same strategy/model signal may correctly produce different Investment Recommendations for different Portfolios because Portfolio State, Exposure, Risk, Mandate, alternatives, and Decision Scope matter.**
12. **Polaris may observe and reconcile Orders and execution evidence without becoming authoritative for market-facing Order placement, routing, working-order state, fills, or exchange execution.**

## Resolved Investment Recommendation relationship and history semantics

Investment Recommendation history is now resolved as durable decision history rather than one mutable recommendation value on an Investment Decision. These semantics are canonicalized in [`../../CONTEXT.md`](../../CONTEXT.md).

The important temporal distinction is:

```text
what Polaris recommends now
        ≠
what Polaris recommended then
```

A later Investment Recommendation can replace an earlier recommendation as Polaris's currently supported preferred judgment without rewriting the earlier historical judgment.

### Zero, one, or many Investment Recommendations

An Investment Decision does not require an Investment Recommendation to exist.

For example:

```text
D-900
Decision Need:
Should Portfolio A increase AAPL?

Evidence:
materially stale / conflicted

Polaris:
responsible Investment Recommendation cannot currently be supported

Investment Decision:
still valid and unresolved
```

Absence of a current Investment Recommendation can have materially different histories:

```text
Not yet formed
Decision work has begun, but Polaris has not yet formed a recommendation judgment.

Explicitly withheld
Polaris has affirmatively determined that the current decision basis cannot support a responsible recommendation.

No longer supportable
A prior Investment Recommendation exists historically, but the current evidence basis no longer supports treating it as current.
```

These meanings must not collapse merely because a projection displays `no current recommendation`.

### No Investment Recommendation is not hold

The following are different facts:

```text
Investment Recommendation:
Hold current SPY Exposure.
```

and:

```text
Investment Recommendation:
none supportable
Reason:
required Portfolio State is insufficiently fresh.
```

The first is an affirmative Polaris judgment that no Portfolio change is preferred. The second means Polaris cannot currently establish a supportable preferred economic disposition.

Likewise:

```text
Investment Recommendation:
Wait for CPI.
```

is a real Polaris judgment. If the human responds:

```text
Human Investment Decision:
Defer until CPI.
```

then Polaris's recommendation to wait and the human's attributable Deferral remain separate facts.

**Distinction proved:** no recommendation ≠ affirmative hold/wait/no-action recommendation, and Investment Recommendation ≠ Human Investment Decision.

### Several recommendations may belong to one unresolved Investment Decision

Suppose:

```text
D-901
Decision Need:
Should Portfolio A reduce SPY Exposure?
```

At 09:00:

```text
R-1
Investment Recommendation:
Hold.
```

After materially changed evidence and reassessment:

```text
R-2
Investment Recommendation:
Reduce SPY Exposure by 15%.
```

Both belong to D-901 while Polaris is still attempting to resolve the same coherent unresolved Decision Need.

```text
D-901
├── R-1  Hold         @ 09:00
└── R-2  Reduce 15%   @ 11:15
```

R-2 may become Polaris's later preferred judgment. R-1 remains a true historical fact about what Polaris recommended earlier.

**Distinction proved:** Recommendation revision or reversal does not require new Investment Decision identity and does not authorize destructive mutation of recommendation history.

### Recommendation identity follows attributable judgment, not text

A new Investment Recommendation does not arise merely because another observation or Evidence refresh occurred.

For example:

```text
R-1:
Hold SPY.

price tick
price tick
Evidence refresh
price tick

→ still R-1 unless Polaris forms another attributable recommendation judgment
```

Conversely, materially new context and a genuine reassessment can produce a distinct Recommendation even when its economic disposition is identical:

```text
09:00
R-1:
Hold SPY.

material shock
full reassessment

11:00
R-2:
Hold SPY.
```

R-2 is a new attributable judgment under a different decision-time basis. Its identical wording does not make it the same Recommendation.

**Distinction proved:** information velocity ≠ Recommendation velocity, and Recommendation identity ≠ textual/economic-content equality.

### Historical Recommendation remains immutable when supportability changes

Suppose:

```text
R-3
Investment Recommendation:
Increase SPY 10%.

Decision-time freshness requirement:
SPY <= 2 minutes old
Portfolio State <= 5 minutes old
```

A source failure later makes the critical data stale.

The correct interpretation is:

```text
R-3
historical Recommendation:
preserved

current supportability:
insufficient

current Investment Recommendation:
none supportable
```

Polaris does not rewrite R-3 to `no recommendation`, because R-3 actually occurred.

When fresh Evidence later supports a new judgment, Polaris may produce R-4.

### An older Recommendation does not silently reactivate

Suppose:

```text
R-1:
Hold.

R-2:
Reduce 15%.
```

Polaris later discovers that R-2 relied on materially erroneous Portfolio data.

R-2 remains historical but is no longer supportable. This does **not** prove that R-1 is current again, because R-1 was formed under an older Decision Context.

The correct state can therefore be:

```text
R-1:
historical

R-2:
historical, currently unsupported

current Investment Recommendation:
none
```

If Polaris reassesses and again prefers Hold, it forms a new attributable judgment:

```text
R-3:
Hold.
```

**Distinction proved:** invalidating a later Recommendation does not resurrect an earlier recommendation judgment; reaffirmation requires a new judgment.

### Erroneous Recommendation remains historical truth

Suppose:

```text
R-5:
Reduce AAPL.

Reason:
AAPL concentration = 35%.
```

Authoritative correction later shows that concentration at recommendation time was actually 8%.

R-5 remains durable because Polaris really did issue it. Its basis can now be identified as materially erroneous. Polaris must not rewrite the historical Recommendation to match what it should have said with corrected data.

A later reassessment might produce:

```text
R-6:
Hold AAPL.
```

This distinction is essential to later evaluation and learning.

**Distinction proved:** historical occurrence ≠ historical correctness.

### Human judgment retains exact Recommendation lineage

Suppose:

```text
R-1:
Hold.

R-2:
Reduce 15%.
```

The human then decides:

```text
Human Investment Decision H-1:
Reduce 10%.
```

If H-1 materially responds to R-2, Polaris preserves that relationship:

```text
H-1
├── materially considered R-2
├── Polaris preferred: Reduce 15%
├── Human chose:       Reduce 10%
└── relationship: modified
```

A Human Investment Decision may have materially considered more than one Recommendation, so the domain does not artificially require a one-to-one relationship. Where the relationship is knowable, Polaris preserves the Recommendation or Recommendations that actually informed the human judgment and any attributable acceptance, modification, rejection, Deferral response, or other relationship.

### Acceptance still preserves two facts

Even when the human exactly accepts Polaris's judgment:

```text
R-7:
Reduce SPY 15%.

H-2:
Reduce SPY 15%.
```

the two facts remain distinct:

```text
Investment Recommendation R-7
Polaris judgment

Human Investment Decision H-2
Human judgment

relationship
H-2 accepted R-7
```

Matching economic content does not collapse system judgment into human authority.

### Human judgment can exist with no Investment Recommendation

Suppose:

```text
D-902
Evidence:
insufficient

Polaris:
Investment Recommendation withheld

Human:
I understand the uncertainty. Reduce SPY 5% anyway.
```

Then:

```text
Investment Recommendation:
none

Human Investment Decision:
Reduce 5%
```

Polaris must not manufacture `Investment Recommendation: Reduce 5%` after the fact merely because the human chose it.

**Distinction proved:** Human Investment Decision authority does not retroactively create Polaris judgment.

### External Resolution does not create Recommendation acceptance

Suppose:

```text
D-903
R-8:
Reduce SPY from 60% to 40%.

Human judgment:
pending
```

Independent external activity then changes actual SPY exposure to 40%, causing External Resolution of D-903.

The following remain unknown unless independently evidenced:

```text
Was R-8 accepted?
not established

Was there a Human Investment Decision?
none observed

Was the external activity recommendation-driven?
not established
```

Economic outcome matching the Recommendation is insufficient to infer any of those facts.

### Substantive resolution ends active Recommendation applicability

Suppose:

```text
D-904
R-9:
Hold AAPL.

Human Investment Decision:
Hold AAPL.
```

The investment judgment for D-904 is substantively resolved. R-9 remains durable historical decision basis, but it does not become an indefinitely active trading instruction.

If materially changed circumstances later require renewed judgment:

```text
Attention
    ↓
new Decision Need
    ↓
D-905
    ↓
new Investment Recommendation
```

The later Recommendation belongs to D-905 rather than being appended as another active judgment of the already resolved D-904.

### Deferral permits continued Recommendation history within the same decision

Deferral is different because the underlying Decision Need remains unresolved.

```text
D-906
R-1:
Wait for CPI.

Human Investment Decision:
Defer until CPI.
```

When CPI becomes available and judgment resumes:

```text
D-906
R-2:
Reduce SPY 10%.
```

R-2 correctly belongs to D-906 because no substantive investment judgment had resolved the Decision Need before the Deferral.

### Frozen Investment Recommendation relationship/history invariants

The following invariants are now accepted:

1. **An Investment Decision may have zero, one, or multiple Investment Recommendations through time.**
2. **Absence of an Investment Recommendation is distinct from an affirmative Investment Recommendation to hold, wait, defer, or take no action.**
3. **The domain must preserve whether no Investment Recommendation exists because one has not yet been formed, because Polaris explicitly withheld one, or because a previously issued Recommendation is no longer currently supportable.**
4. **A distinct attributable recommendation judgment creates a distinct Investment Recommendation; Recommendation identity is not derived solely from its textual or economic content.**
5. **Evidence refresh or observation change does not automatically create a new Investment Recommendation.**
6. **A materially new or explicitly reaffirmed Polaris judgment may create a new Investment Recommendation even when its economic disposition is identical to an earlier Recommendation.**
7. **A changed or reversed Investment Recommendation within the same unresolved Decision Need remains part of the same Investment Decision.**
8. **A later Investment Recommendation does not rewrite or delete earlier Investment Recommendations.**
9. **Historical Investment Recommendations remain reconstructable against the Decision Context and Evidence that supported or undermined them at the time.**
10. **An Investment Recommendation may cease to be currently supportable because Evidence becomes stale, insufficient, conflicting, erroneous, or otherwise unfit for its intended decision use without ceasing to exist historically.**
11. **When the currently preferred Investment Recommendation becomes unsupported, an older Investment Recommendation must not silently reactivate; renewed support requires a new attributable recommendation judgment.**
12. **Current Investment Recommendation, when one exists, is a temporal interpretation of durable Recommendation history—not a mutable field that overwrites history.**
13. **Human Investment Decision ≠ Investment Recommendation even when their economic content is identical.**
14. **Polaris must preserve which Investment Recommendation or Recommendations materially informed a Human Investment Decision when that relationship is knowable.**
15. **Where attributable, Polaris must preserve whether the human accepted, modified, rejected, deferred in response to, or otherwise related their judgment to a specific Investment Recommendation.**
16. **Human rejection of an Investment Recommendation does not by itself determine whether the underlying Investment Decision is substantively resolved.**
17. **A Human Investment Decision may substantively resolve an Investment Decision when no Polaris Investment Recommendation exists; Polaris must not retroactively manufacture a Recommendation from the human choice.**
18. **External Resolution that produces a Portfolio state matching an Investment Recommendation does not establish Recommendation acceptance, a Human Investment Decision, or recommendation-driven execution.**
19. **After substantive investment judgment resolution, any later renewed judgment and its Investment Recommendation belong to a new causally linked Investment Decision.**
20. **Deferral is different: because the Decision Need remains unresolved, later Investment Recommendations may continue under the same Investment Decision after judgment resumes.**
21. **An Investment Recommendation ceases to be an active current judgment once its Investment Decision's investment judgment is substantively resolved or Externally Resolved; it remains durable historical decision basis.**
22. **Investment Recommendation history must preserve enough decision-time basis to distinguish what Polaris recommended, why it recommended it, whether it remained supportable, what the human considered, and what happened afterward.**

## Resolved Decision Context and Judgment-Time Availability semantics

`Decision Context` and `Judgment-Time Availability` are now resolved sufficiently to distinguish the circumstances that actually frame an investment judgment from the information that a particular judgment could actually access. These semantics are canonicalized in [`../../CONTEXT.md`](../../CONTEXT.md).

`Judgment-Time Availability` supersedes the earlier candidate term `Decision-Time Availability`. An Investment Decision may span several attributable judgments at different times, so availability cannot be modeled truthfully as one global property of the Investment Decision. These semantics also refine earlier shorthand in this document such as `decision-time context available`: the domain now distinguishes **applicable Decision Context** from **information available to a specific judgment**.

### Decision Context is the applicable decision frame, not an evidence bag

Decision Context answers:

```text
What circumstances and existing state materially frame this judgment?
```

Evidence answers a different question:

```text
What information supports, contradicts, constrains,
qualifies, or reconstructs material claims or outputs?
```

The distinction is role-based rather than duplicative. A Portfolio State fact, applicable Investment Mandate, or prior Investment Recommendation may participate in the Decision Context and also be established, challenged, or reconstructed through Evidence without becoming two separate domain facts.

For example, the same bearish SPY Evidence can produce different consequences for two Portfolios:

```text
Portfolio A
SPY Exposure: 5%
Cash: substantial
Horizon: long

Portfolio B
SPY Exposure: 65%
Liquidity: constrained
Risk boundary: tighter
```

The external Evidence can be identical while Decision Context differs materially. Different Investment Recommendations are therefore not inconsistent merely because they arise from the same market Evidence.

**Distinction proved:** Decision Context ≠ Evidence, and identical Evidence does not imply identical judgment when applicable context differs.

### Applicable context is distinct from the representation available to a judgment

Suppose:

```text
09:00
Applicable Investment Mandate:
M-2

Polaris accidentally loads:
M-1

10:00
Investment Recommendation R-1
```

M-2 still governs the Portfolio. Polaris's failure to load it does not make M-1 the applicable Mandate.

The same distinction applies to Portfolio State:

```text
actual historical concentration:
8%

representation available to Polaris:
35%
```

If R-1 recommends reducing AAPL because Polaris believes concentration is 35%, historical reconstruction must preserve both truths:

```text
Applicable historical Decision Context:
actual concentration = 8%

Information available to R-1:
concentration represented as 35%

R-1:
formed from the erroneous representation
```

Later correction may establish that the context representation was wrong, but it must not rewrite either the actual historical Portfolio condition or the information basis from which R-1 was genuinely formed.

**Distinction proved:** applicable Decision Context ≠ a judgment participant's representation of that context, and historical occurrence ≠ historical correctness.

### Public or source availability is not Judgment-Time Availability

Suppose:

```text
09:58
SEC filing becomes publicly available.

09:59
Polaris ingestion / access fails.

10:03
R-1 is formed without the filing.
```

Then the filing can truthfully be:

```text
underlying information existed:
yes

source/public availability:
yes

available to R-1:
no
```

Later Evaluation may properly conclude that Polaris missed material information that could have been obtained. Historical reconstruction of R-1 must not silently insert that filing into R-1's information basis.

**Distinction proved:** source/public availability ≠ Judgment-Time Availability.

### Available does not mean used or fit for use

Suppose a research item was accessible in Polaris before R-1 but was never selected into the reasoning that formed R-1:

```text
Judgment-Time Availability:
yes

materially informed R-1:
no
```

Availability therefore does not prove use or material influence.

Likewise, available information may still be unusable for the intended judgment:

```text
SPY observation:
available
age = 45 minutes

Freshness Requirement:
<= 2 minutes

Judgment-Time Availability:
yes

fit for this Recommendation:
no
```

The distinction allows Polaris to explain materially different failure states such as missing information, available-but-stale information, available-but-conflicting information, and information that was available but did not materially inform the judgment.

**Distinction proved:** availability ≠ use ≠ material influence, and availability ≠ freshness, sufficiency, conflict state, admissibility, or fitness.

### Availability is relative to the attributable judgment

One Investment Decision may contain several judgments at different times:

```text
D-1000

10:00
Polaris Investment Recommendation R-1

10:05
material information arrives

10:10
Human Investment Decision H-1
```

The new information can be:

```text
available to R-1:
no

available to H-1:
yes
```

The same pattern can occur between successive Investment Recommendations within one unresolved Investment Decision.

Human availability must not be fabricated. If Polaris cannot establish whether the human actually had access to particular information, the historical availability relationship remains unknown rather than being inferred from silence.

**Distinction proved:** Judgment-Time Availability is scoped to a specific attributable judgment rather than globally to its containing Investment Decision.

### Later Evidence may reconstruct reality without contaminating the earlier judgment basis

Suppose an event occurs before R-1, but authoritative information establishing the event becomes available only later:

```text
09:00
event occurs

10:00
R-1 formed

12:00
authoritative source exposes the event
```

The later source may become Reconstruction Evidence or later Evaluation Evidence. It may establish what was historically true, but it was not available to R-1 and therefore cannot become retroactive Decision Evidence for R-1.

The same rule applies to corrected data. A later authoritative correction may change Polaris's current understanding of the historical world while preserving the erroneous representation actually available to the earlier judgment.

**Distinction proved:** later knowledge may correct historical truth without rewriting historical Judgment-Time Availability or the actual basis of an earlier judgment.

### Historical availability survives current source loss

Suppose an article was available and materially used by R-1, but its publisher later deletes it.

The current source state can be:

```text
retrievable now:
no
```

while historical reconstruction remains:

```text
available to R-1:
yes
```

Current retrievability must not rewrite historical availability. Durable reconstruction may therefore require retained lineage or reconstruction evidence, but the domain invariant is historical truth rather than any prescribed storage mechanism.

**Distinction proved:** available now ≠ available then in either direction.

### Decision Context may change without acquiring independent identity

Suppose one unresolved Investment Decision continues through material change:

```text
D-1001
Decision Need:
Should Portfolio A reduce SPY Exposure?

09:00
context applicable to R-1
        ↓
R-1: Hold

11:15
Portfolio State and market conditions materially change
        ↓
context applicable to R-2
        ↓
R-2: Reduce 15%
```

D-1001 remains the same Investment Decision while the same coherent unresolved choice is being judged. R-1 and R-2 must each remain reconstructable against the context applicable when each judgment was formed.

The domain does not require a first-class `Decision Context` identity or numbered context-version entity merely because context changes. A future architecture may choose snapshots, temporal records, references, event history, or another representation. The domain invariant is historically faithful reconstructability.

Likewise:

```text
context change
≠ new Investment Recommendation
≠ new Investment Decision
```

A new Investment Recommendation still requires a distinct attributable Polaris judgment, and a new Investment Decision still follows the already-frozen identity/lifecycle rules.

**Distinction proved:** temporal context change is a domain fact, but context-version identity and storage representation are architectural concerns.

### Frozen Decision Context and Judgment-Time Availability invariants

The following invariants are now accepted:

1. **Decision Context is the time-specific, decision-relative set of applicable conditions, constraints, domain state, and prior decision state that frame an Investment Decision or judgment within it.**
2. **Decision Context ≠ Evidence.**
3. **Context membership follows decision relevance and applicability; Evidence status follows the role information plays in supporting, contradicting, constraining, qualifying, or reconstructing claims or outputs.**
4. **The same underlying fact may participate in Decision Context and in an Evidence role without becoming two different domain facts.**
5. **Applicable Decision Context is distinct from Polaris's information or representation of that context. An applicable condition does not cease to apply merely because Polaris did not know it, could not access it, or represented it incorrectly.**
6. **Historical reconstruction must be capable of distinguishing what actually applied from what information about it was available to the judgment.**
7. **One unresolved Investment Decision may have materially changing Decision Context through time without changing Investment Decision identity.**
8. **A change in Decision Context does not by itself create a new Investment Recommendation; a new Recommendation still requires a distinct attributable Polaris judgment.**
9. **Each Investment Recommendation must remain reconstructable against the Decision Context applicable when that Recommendation was formed and the information actually available to that judgment.**
10. **Decision Context does not require independent domain identity or explicit context-version objects merely because context changes through time; historical reconstructability is the invariant, while representation/versioning strategy remains architectural.**
11. **`Judgment-Time Availability` replaces `Decision-Time Availability` as the canonical term because availability is relative to a specific attributable judgment, not globally to an Investment Decision that may span several judgments.**
12. **Judgment-Time Availability ≠ underlying fact/event time, source publication time, or current retrievability.**
13. **Judgment-Time Availability ≠ freshness, sufficiency, conflict state, admissibility, or fitness for the intended decision use.**
14. **Judgment-Time Availability ≠ selection, use, or material influence; information may be available to a judgment without materially informing it.**
15. **Availability must remain unknown when Polaris lacks sufficient provenance to establish whether information was available to a particular judgment; absence of evidence must not be converted into false unavailability.**
16. **Information may be available to one judgment within an Investment Decision and unavailable to another, including a Polaris Investment Recommendation and a later Human Investment Decision.**
17. **Later-created, later-discovered, or later-corrected information may support reconstruction, Evaluation, or learning without becoming part of an earlier judgment's historical information basis.**
18. **A later correction may change Polaris's current understanding of what was historically true without rewriting the erroneous or incomplete representation actually available to an earlier judgment.**
19. **Information that was available at judgment time remains historically available even if its source later changes, disappears, or becomes inaccessible; current availability must not rewrite historical availability.**