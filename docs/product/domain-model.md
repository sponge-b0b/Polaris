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