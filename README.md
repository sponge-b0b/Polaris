# Polaris

![Polaris](assets/polaris_banner.png)

**AI-assisted portfolio decision intelligence for decisions that remain explainable after they are made.**

Polaris is being built to help sophisticated portfolio decision-makers and small investment teams turn fragmented, uncertain Evidence into reasoned, risk-aware Investment Decisions — and preserve enough truth to understand, challenge, evaluate, and learn from those decisions later.

Markets produce information. Research tools interpret pieces of it. Brokers execute actions. Polaris is being built for the difficult layer between them: **deciding what changing information means for a particular Portfolio, what could make that interpretation wrong, what Portfolio Risk and constraints matter, what alternatives are reasonable, and what deserves human judgment.**

> [!IMPORTANT]
> **Polaris is under active greenfield development.** This README describes the product Polaris is being built to become. The current implementation is intentionally being developed inside-out from durable domain semantics and is not yet a production-ready realization of the full product described below. See [Current development status](#current-development-status) for the implementation boundary today.

## Why Polaris exists

Investment decision-making is not primarily an information shortage problem.

A portfolio decision-maker may already have market data, economic data, research, news, charts, models, risk tools, broker information, and general-purpose AI. The harder problem is turning all of that into a repeatable judgment process that can answer:

- What actually deserves Attention?
- What is the unresolved investment choice?
- What Evidence matters to that choice?
- What does the Evidence mean in the context of this Portfolio?
- What is the strongest case that our interpretation is wrong?
- What Portfolio Risks, Formal Constraints, and Policies matter?
- What Decision Alternatives are reasonable?
- What does Polaris recommend, and why?
- What did the human actually decide?
- What happened afterward?
- Was the reasoning process useful given what was knowable at the time?
- What should matter the next time a similar decision appears?

Polaris is designed around that entire lifecycle rather than around one model response, report, workflow run, alert, or trade.

## The Investment Decision is the product

Polaris treats **Investment Decisions as durable, first-class lifecycles** rather than disposable analyses, recommendations, conversations, reports, alerts, workflows, or trades.

Conceptually:

```text
Attention
   ↓
Decision Need
   ↓
Decision Context + Evidence
   ↓
Investment View + Challenge
   ↓
Projected Portfolio Consequences
   ↓
Portfolio Risk + deterministic boundaries
   ↓
Investment Recommendation
   ↓
Human Investment Decision
   ↓
Action Intent, when applicable
   ↓
Observed external reality
   ↓
Outcome
   ↓
Decision Evaluation
   ↓
Lessons
   └────────────────────→ future Attention
```

**Durable Decision Memory spans that lifecycle.**

The goal is not merely to remember the final answer. Polaris is being built to preserve enough material context to reconstruct what was known, what Polaris judged, what uncertainty and disagreement existed, what constraints and authority conditions applied, what the human decided, what actually happened, and what should be learned from the result.

That turns past decisions into future decision context instead of passive archives.

## What makes Polaris different

### Decisions, not disposable answers

A typical AI interaction looks like:

```text
Question → Answer → Done
```

Many investment tools effectively stop at:

```text
Analyze → Recommend → Report → Done
```

Polaris is designed to continue:

```text
Reason
  ↓
Recommend
  ↓
Human judgment
  ↓
Observe what actually happened
  ↓
Evaluate the decision
  ↓
Learn
  ↓
Improve future Attention and reasoning
```

The durable unit of product value is the **Investment Decision**, not the chat, report, workflow, model invocation, or trade that happened around it.

### Attention, not alert overload

Most AI systems assume the user already knows something matters, formulates the right question, and asks it.

Polaris is being built to maintain enough Portfolio and decision context to ask continuously:

> **Does this new information materially affect something this Portfolio currently cares about?**

The intended flow is selective:

```text
Observe change
      ↓
Investment Relevant?
   no └──→ absorb quietly
      ↓ yes
Investment Material?
   no └──→ update context quietly
      ↓ yes
Investigate
      ↓
Attention evaluates Decision Need
      ↓
Continue unresolved work
or create a new causally linked decision
      ↓
Surface prepared decision work when human judgment is required
```

The goal is not more alerts. It is **better Attention**.

When Polaris interrupts the user, it should preferably arrive with prepared decision work: what changed, why it matters, what was reassessed, what remains uncertain, what Portfolio Risks changed, and what now requires judgment.

### Portfolio consequences, not generic market opinions

For Polaris, the question:

> Is this security attractive?

is incomplete.

The stronger question is:

> Given this Portfolio, its current Positions, Exposure, concentration, Investment Strategy, Investment Horizon, Investment Mandate, Portfolio Risk, prior Investment Thesis, and competing Decision Alternatives, should anything change?

The same Investment View can correctly lead to different recommendations for different Portfolios.

That is why Polaris is a **portfolio decision system**, not a signal generator.

### Challenge, not confirmation

Polaris is not intended to produce a preferred view and then decorate it with confidence.

A trustworthy Investment Recommendation should be able to account for:

```text
Leading Investment View
        +
Supporting Evidence
        +
Conflicting Evidence
        +
Strongest alternative Investment Hypothesis
        +
Material Investment Uncertainty
        +
Investment Assumptions
        +
Invalidation Conditions
```

Challenge is a product requirement, not a commitment to a particular multi-agent topology. One model, several models, deterministic analytics, human input, or combinations of them may participate. The user-facing contract remains the same: **meaningful reasons the preferred interpretation may be wrong must be considered.**

### Portfolio Risk inside the recommendation

Polaris does not treat Portfolio Risk as an approval stamp applied after an Investment Recommendation has already been formed.

Instead:

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

Portfolio Risk is part of the decision itself.

A good idea in isolation may still be the wrong Portfolio decision because concentration, Exposure, Investment Horizon, existing Positions, Formal Constraints, or competing opportunities change the tradeoff.

### Trust by architecture, not by model confidence

Polaris should not ask users to trust an Investment Recommendation because an AI model sounds persuasive or reports a high confidence score.

Trust should come from the structure around the reasoning:

```text
Authoritative Evidence
Judgment-Time Availability
Freshness
Investment View + Challenge
Portfolio Risk
Deterministic rule results
Power-specific authority acts
Human Investment Decision
Authoritative external reality
Outcome
```

Polaris uses AI where AI adds reasoning and synthesis value, deterministic software where explicit rules and guarantees matter, and human authority where consequential investment judgment or another power-specific authority act must remain attributable to an authorized actor.

The governing idea is simple:

> **Reduce the amount of blind trust the user must place in the model.**

### AI initiative without AI sovereignty

Polaris is designed to take substantial initiative in observation, investigation, challenge, preparation, Portfolio Risk reasoning, and Investment Recommendation formation.

That initiative does **not** automatically grant authority over capital.

Investment Recommendations and Human Investment Decisions remain distinct facts. Approval, Mandate Exception, Governed Residual Risk acceptance, and execution authority are also distinct power-specific acts rather than different names for the same thing.

Polaris can recommend. Human investment authority remains attributable. Specialist external systems remain responsible for market-facing execution.

### Durable Decision Memory that changes future behavior

Polaris is not being built merely to save old reports so they can be searched later.

Past Investment Decisions may preserve active Investment Theses, Investment Assumptions, Invalidation Conditions, deferred judgments, Portfolio Risks, Catalysts, Review Conditions, authority history, Outcomes, and Lessons.

Those facts should be capable of changing what Polaris notices and how it reasons in the future.

If a prior decision said, in effect, "maintain this Position unless condition X occurs," condition X should become materially important later without requiring the user to reconstruct the old context manually.

If Durable Decision Memory never changes future behavior, it is only an archive.

### Learn from process, not Outcome alone

Investing is probabilistic.

A good decision can lose money. A bad decision can make money.

Polaris is therefore being built to evaluate the quality of a decision using what was actually available to the relevant judgment at the time, while using later Outcomes to learn rather than rewrite history.

That makes it possible to ask different questions about:

- Evidence quality;
- reasoning quality;
- challenge quality;
- Portfolio Risk reasoning;
- Investment Recommendation quality;
- human judgment;
- implementation fidelity;
- observed Outcome.

The goal is to improve the **decision process**, not merely classify profitable outcomes as good decisions.

## The Polaris decision shorthand

The product can be summarized as:

> **Understand → Challenge → Apply Portfolio context → Decide under Portfolio Risk → Explain → Learn**

Each step exists to strengthen the same Investment Decision lifecycle.

## Core capabilities

Polaris requires nine durable product capabilities:

1. **Attention & Decision Initiation** — determine what deserves Attention, when a Decision Need exists, when unresolved work should continue, and when a resolved matter warrants a new causally linked Investment Decision.
2. **Decision Context & Evidence** — assemble decision-specific Portfolio context and attributable Evidence with provenance, freshness, sufficiency, historical integrity, and Judgment-Time Availability.
3. **Investment Reasoning & Challenge** — develop an Investment View while exposing competing hypotheses, Conflicting Evidence, Investment Uncertainty, assumptions, and Invalidation Conditions.
4. **Portfolio Consequence & Risk** — determine what an Investment View means for the actual Portfolio under current Portfolio State, Portfolio Risk, Investment Mandate, Formal Constraints, and Policy.
5. **Recommendation Formation** — compare reasonable Decision Alternatives and form an explainable Investment Recommendation, or deliberately withhold one when the decision is not supportable.
6. **Authority & Human Decision** — preserve the distinction between Polaris judgment, deterministic boundary results, power-specific authority acts, and attributable Human Investment Decision.
7. **Action Continuity & Reconciliation** — preserve intended implementation consequences where applicable and reconcile authoritative external activity back into the decision lifecycle without becoming the execution system.
8. **Durable Decision Memory** — preserve material decision history and relationships so past decisions remain inspectable and can influence future Attention, reasoning, and evaluation.
9. **Outcome Evaluation & Learning** — connect Outcomes and later Evidence to prior decisions, evaluate the process using the information available at the time, and preserve Lessons that can improve future decisions.

These are product abilities, not commitments to particular agents, models, databases, workflow engines, interfaces, or providers.

## Where Polaris fits

Polaris occupies the **decision layer between investment information systems and investment action systems**.

```text
SENSE                         DECIDE                         ACT
  │                              │                            │
Market data                     │                       Broker / trading platform
Economic data                   │                       Order entry / execution
News / research ───────────→  POLARIS  ───────────→     Operational systems
Portfolio State                 │                            │
External analytics              ↓                            │
                         Human Investment Decision ──────────┘
                                │
                                └── resulting external reality
                                    returns to Polaris
```

Information systems establish facts within the responsibilities they authoritatively own. Polaris determines what those facts mean for the Portfolio, what deserves Attention, and what should be considered. External operational systems remain authoritative for what actually happened.

Polaris owns **decisions, not everything decisions touch**.

## What Polaris is not

Polaris is deliberately not defined as:

- an autonomous trading bot;
- a broker or exchange-speed execution engine;
- a high-frequency trading system;
- an official portfolio accounting or books-and-records system;
- a generic market-data vendor;
- a generalized charting terminal;
- a general-purpose quantitative programming environment;
- an unrestricted financial chatbot;
- a generic AI-agent or workflow framework;
- a system whose value is measured by how many alerts, reports, recommendations, or trades it generates.

Polaris may integrate deeply with specialist systems in these areas and may provide focused supporting capabilities when they improve the decision experience. Integration does not transfer the specialist system's broader product responsibility to Polaris.

## Product principles

Several principles govern the product as it evolves:

- **Decisions before features.** Product progress is measured by stronger decision capability, not feature count.
- **Trust by structure, not confidence.** Important Evidence, judgments, constraints, authority, and Outcomes should remain inspectable.
- **Preserve truth before convenience.** Simplify presentation without collapsing distinctions that matter.
- **AI initiative without AI sovereignty.** Automate analytical work aggressively while preserving consequential authority boundaries.
- **Portfolio Risk shapes the decision.** Risk is part of recommendation formation, not an after-the-fact stamp.
- **Be attentive, not noisy.** Human Attention is scarce; interrupt for materiality, not novelty.
- **Current enough for the decision.** Freshness depends on the investment use, not a universal definition of real time.
- **Durable Decision Memory should change future behavior.** History should influence future Attention, reasoning, and learning.
- **Reality wins.** Authoritative external facts outrank expected or cached state.
- **Integrate before absorbing.** Specialist systems should continue to own specialist responsibilities where practical.
- **Opinionated domain, flexible process.** Configurability should live inside investment-domain concepts rather than generic workflow primitives.
- **Learn from process, not Outcome alone.** Evaluate judgment using what was knowable then; use later Outcomes to learn.

## Current development status

Polaris is in an active **greenfield rebuild**.

The previous implementation demonstrated substantial AI, market-data, orchestration, persistence, observability, reporting, and investment-analysis capability, but the new Polaris architecture does not preserve that implementation as its baseline merely because it already exists.

The rebuild is intentionally proceeding **inside-out**:

```text
product doctrine + domain semantics
          ↓
requirements
          ↓
target architecture
          ↓
durable domain kernels
          ↓
application and persistence boundaries
          ↓
capability integration
          ↓
interfaces and product experience
```

The current implementation effort is establishing the durable **Investment Decision kernel and historical-truth semantics** that later Evidence, Investment Intelligence, Governance, Action Continuity, Durable Persistence, and Decision Evaluation capabilities will depend on.

This means the repository may describe product capabilities that are not yet implemented end to end. That is intentional. The product contract is being defined first so implementation cannot accidentally redefine it from the bottom up.

No production capability should be inferred from `legacy/`, from a design document, or from the existence of a greenfield package boundary alone.

## Greenfield development model

The repository intentionally does **not** preserve the previous implementation architecture as the new baseline.

Legacy implementation is treated as donor/reference material. Existing abstractions, dependencies, schemas, workflows, tests, and architecture survive only when they independently satisfy a current product need and the new architecture.

The pristine pre-greenfield implementation is anchored by the Git tag `legacy-v0.1-baseline`.

## Repository boundaries

- `src/polaris/` — canonical source package for the greenfield Polaris implementation.
- `legacy/v0_1/` — historical pre-greenfield implementation retained only as donor/reference material.
- `docs/product/` — durable product doctrine, capabilities, differentiation, scope, requirements, and domain model.
- `docs/current/` — current approved architecture.
- `docs/adr/` — accepted architectural decisions.
- `CONTEXT.md` — canonical domain vocabulary when explicitly required by repository policy.
- `wiki/` — Living Entity Wiki containing derived architectural memory and the active Entity-ID registry.
- `docs/process/` and `.agents/` — repository and development-workflow infrastructure.
- `assets/` — Polaris project branding.

### Legacy isolation

New Polaris code, tests, configuration, migrations, and runtime paths must never import, wrap, extend, execute through, or otherwise depend on `legacy/`.

Legacy code may be studied and selectively transplanted only after a current product need and architectural owner have been independently established.

## Product documentation

The README is intentionally a concise introduction. The durable product doctrine lives under `docs/product/`.

Good starting points:

- [`product-definition.md`](docs/product/product-definition.md) — what Polaris is, who it serves, the decision lifecycle, core experience, and authority model.
- [`product-differentiation.md`](docs/product/product-differentiation.md) — why durable Investment Decisions, attentive intelligence, Portfolio consequence, challenge, and trust-by-architecture make Polaris different.
- [`product-core-capabilities.md`](docs/product/product-core-capabilities.md) — the nine durable capabilities required to close the portfolio decision lifecycle.
- [`product-principles.md`](docs/product/product-principles.md) — the product rules used to reject or refine otherwise plausible product and architecture choices.
- [`product-scope-boundaries.md`](docs/product/product-scope-boundaries.md) — what Polaris owns, what it supports, and what remains the responsibility of specialist systems.
- [`product-ecosystem.md`](docs/product/product-ecosystem.md) — where Polaris fits relative to market data, research, portfolio systems, brokers, execution, and adjacent tools.
- [`product-execution-continuity.md`](docs/product/product-execution-continuity.md) — how Polaris preserves decision continuity across external execution without becoming the execution authority.
- [`requirements-0.2.0.md`](docs/product/requirements-0.2.0.md) — the current product requirements derived from the accepted product doctrine.

## License

Polaris is licensed under the Apache License 2.0. See [LICENSE](LICENSE).
