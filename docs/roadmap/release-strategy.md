# Polaris Release Strategy

**Status:** Defined  
**Purpose:** Define how Polaris should advance from the current product state to a stable 1.0 release without turning roadmap planning into feature accumulation or subsystem sequencing.

This document applies the Product Definition and [`capability-model.md`](../product/capability-model.md) to release planning. It defines how releases are constructed, how capability maturity and breadth should evolve, what pre-1.0 releases are intended to accomplish, and what product threshold defines Polaris 1.0.

It intentionally does **not** assign version numbers to specific roadmap stages or prescribe implementation architecture.

## Release strategy

A Polaris release should represent a meaningful improvement in an end-to-end portfolio decision ability, not merely a bundle of completed features, subsystems, infrastructure changes, or tickets.

The governing release rule is:

> **Prefer narrow, trustworthy, end-to-end capability over broad, shallow feature coverage.**

A release should be understandable in product language:

```text
Polaris can now do <meaningful portfolio decision job>
within <declared operating breadth>
with <declared capability maturity and trust properties>.
```

Features, integrations, services, workflows, agents, persistence changes, reports, and infrastructure are implementation evidence for that product claim. They are not the release thesis by themselves.

## Narrow and trustworthy before broad and shallow

Polaris should normally deepen capability maturity before aggressively expanding capability breadth.

A narrowly supported decision lifecycle with strong provenance, portfolio context, risk, authority, durable memory, and operational continuity is more valuable than broad provider, asset, workflow, or interface coverage whose decision semantics remain weak.

This does not mean breadth is unimportant. A capability must eventually support enough operating contexts to make the product useful. The distinction is that breadth and maturity are separate planning dimensions:

```text
Capability maturity
How well does Polaris fulfill the responsibility?

Capability breadth
Across how many supported operating contexts can Polaris fulfill it?
```

Adding another provider, broker, model, asset class, interface, or evidence source usually expands breadth. It does not automatically advance maturity.

## Every release needs a product thesis

Every release should have one primary product thesis that explains what meaningful product ability becomes possible, stronger, broader, or more trustworthy.

A release thesis should not primarily be stated as:

```text
Add PostgreSQL persistence
Add RAG
Add another agent
Add telemetry
Add a report
Add a broker adapter
```

Instead it should describe the product outcome those mechanisms enable.

A release may advance several capabilities underneath one thesis, but the release should remain coherent enough that its purpose can be explained without enumerating implementation components.

## Capability envelope

Every planned release should define an explicit **capability envelope**.

The envelope records:

1. relevant capability maturity before the release;
2. intended maturity after the release;
3. supported breadth;
4. important operating boundaries;
5. declared non-goals.

The capability envelope should use the maturity model defined in the Capability Model:

```text
M1 — Bounded
M2 — Integrated
M3 — Governed
M4 — Adaptive
```

A release does not need to advance every capability uniformly. It must make every capability required by the release thesis sufficiently mature for that thesis to be true.

## Prefer vertical capability slices

Release planning should prefer coherent end-to-end decision slices over subsystem-first development.

The default should not be:

```text
finish evidence
then finish reasoning
then finish risk
then finish recommendation
then finally assemble a product
```

Instead, Polaris should establish bounded but usable versions of connected capabilities and deepen them together:

```text
Decision need
    ↓
Evidence
    ↓
Reasoning + challenge
    ↓
Portfolio consequence + risk
    ↓
Recommendation
    ↓
Authority + human decision
    ↓
Action continuity
    ↓
Evaluation

Durable Decision Memory spans the lifecycle.
```

Capability maturity may remain uneven when the release thesis does not require equal maturity everywhere.

## Trust floor

Trust properties are not optional polish when a release makes a governed decision claim.

A release may be analytically simple or deliberately narrow, but it must not claim a trustworthy product outcome while required trust contracts are knowingly absent.

Depending on the claim, those contracts may include:

* evidence provenance;
* decision-appropriate freshness;
* meaningful challenge and uncertainty;
* portfolio-aware risk;
* deterministic policy;
* authority provenance;
* human-decision distinction;
* decision-time integrity;
* operational reality;
* historically faithful durable state.

The required trust floor depends on the claim being made. Exploratory analysis may support a different contract than an actionable portfolio recommendation.

The governing rule is:

> **If required trust properties are absent, reduce the claim rather than lower the standard.**

## Close the lifecycle early

Polaris should prefer closing the complete portfolio decision lifecycle at bounded maturity before maximizing sophistication in isolated analytical stages.

The differentiating product loop is:

```text
Attention
   ↓
Decision work
   ↓
Recommendation
   ↓
Human decision
   ↓
External action
   ↓
Observed reality
   ↓
Outcome
   ↓
Evaluation
   ↓
Learning
   └────────→ future decisions
```

A bounded but complete loop establishes the actual Polaris product earlier than an increasingly sophisticated system that still ends at analysis, a recommendation, or a report.

## Deepen the durable differentiators

After a bounded lifecycle exists, releases should disproportionately strengthen the three durable differentiators established by the Product Definition.

### Durable decisions

Strengthen:

* decision continuity;
* historical fidelity;
* durable decision state;
* action reconciliation;
* outcome connection;
* evaluability;
* active decision memory.

### Trust by architecture

Strengthen:

* evidence provenance;
* freshness enforcement;
* challenge;
* uncertainty handling;
* deterministic governance;
* authority provenance;
* historical integrity;
* external-reality reconciliation.

### Attentive intelligence

Strengthen:

* materiality detection;
* active-thesis awareness;
* review and invalidation conditions;
* automatic reassessment;
* selective interruption;
* prepared decision work;
* proactive attention grounded in durable memory.

These differentiators should normally receive greater strategic weight than simply increasing the number of analyses or integrations Polaris can perform.

## Adaptive maturity requires trustworthy history

M4 — Adaptive means durable state materially changes future behavior.

Adaptive capability should normally build on sufficiently governed historical state. Polaris should not treat unreliable or semantically incomplete history as a trustworthy learning substrate merely because it is available.

The intended progression is meaningful:

```text
M1 Bounded
    ↓
M2 Integrated
    ↓
M3 Governed
    ↓
M4 Adaptive
```

Early heuristics may exist before M3, but product-level adaptation should not outrun the integrity of the evidence, authority, decision, action, and outcome history from which it learns.

## Breadth expansion requires justification

Breadth releases are valid and often necessary, but breadth should be explicit rather than confused with maturity.

Examples include support for:

* another portfolio context;
* another broker;
* another asset class;
* another evidence provider;
* another model;
* another interface;
* another distribution destination.

Each breadth proposal should ask:

> **Does this materially expand access to an existing Polaris capability, or does it quietly create a new product responsibility?**

The Scope Boundaries doctrine still applies: integrate before absorbing specialist responsibilities unless product strategy explicitly justifies expansion.

## Supporting platform work must attach to a product need

Supporting platform capabilities are legitimate release work when they strengthen a core product outcome.

Relevant supporting capabilities include:

* Integration & Connectivity;
* Interaction & Projection;
* Configuration & Extensibility;
* Runtime Reliability & Observability;
* Security & Operations.

Their roadmap justification should normally take the form:

```text
supporting capability advance
        ↓
removes a constraint / improves trust / improves breadth
        ↓
core decision capability becomes stronger
```

Supporting infrastructure should not acquire an independent roadmap simply because it can become more sophisticated.

## Three release-advancement types

A release may primarily advance one or more of three dimensions.

### Capability maturity

The release deepens how well Polaris fulfills an existing responsibility:

```text
M1 → M2
M2 → M3
M3 → M4
```

### Capability breadth

The release expands the operating contexts in which an established capability is supported.

### Lifecycle closure

The release connects previously disconnected lifecycle responsibilities, such as:

```text
Recommendation
    ↓
Human Decision
    ↓
External Action
```

or:

```text
Outcome
    ↓
Evaluation
    ↓
Future Attention
```

As a default strategic priority:

```text
1. Close missing lifecycle segments.
2. Make the existing lifecycle trustworthy.
3. Make the lifecycle adaptive.
4. Expand breadth.
```

This is a planning preference, not an absolute prohibition. Breadth may move earlier when lack of breadth blocks meaningful product use.

## Explicit non-goals

Every release should declare material non-goals and unsupported breadth.

A bounded operating envelope is a deliberate product decision, not an embarrassment to hide.

Examples may include:

```text
Supported:
- one asset class
- one broker
- one portfolio model

Not goals for this release:
- generalized screening
- broad options modeling
- autonomous execution
- enterprise IAM
```

Explicit non-goals reduce scope creep and make the release thesis falsifiable.

## Product acceptance defines release completion

Engineering completion is necessary but not sufficient for a release.

Closed issues, passing CI, completed migrations, and implemented code prove engineering work. They do not by themselves prove the product thesis.

The release-completion question is:

> **Can Polaris reliably perform the release thesis within the declared capability envelope and supported breadth?**

Release acceptance should therefore be stated in product language and verified through the canonical product path.

## Pre-1.0 purpose

Pre-1.0 releases exist to progressively turn Polaris into the complete product defined by the Product Definition until one narrow but genuinely trustworthy closed-loop portfolio decision system is stable.

The pre-1.0 progression is:

```text
Establish the decision system
        ↓
Close the decision loop
        ↓
Govern and trust the loop
        ↓
Stabilize the product
        ↓
1.0
```

These are strategic stages rather than predetermined version numbers. The roadmap may use one or several releases to complete a stage.

## Stage 1 — Establish the decision system

The first objective is to make the portfolio decision lifecycle itself canonical and authoritative.

Polaris already contains substantial analytical and platform machinery. The Product Definition establishes that the product center is not an isolated workflow run, agent response, report, RAG response, or trade. It is the durable portfolio decision lifecycle.

Stage 1 therefore establishes shared product semantics around:

```text
Decision need
    ↓
Context + evidence
    ↓
Reasoning + challenge
    ↓
Portfolio consequence + risk
    ↓
Recommendation
    ↓
Authority
    ↓
Human decision
```

with Durable Decision Memory spanning the lifecycle.

The objective is semantic consolidation, not a mandatory architectural rewrite.

### Stage 1 success

Polaris can take one bounded decision from initiation through a preserved recommendation and human decision while maintaining the material evidence, reasoning, risk, and authority distinctions required by the Product Definition.

The important transition is:

> **There is one canonical Polaris decision lifecycle rather than several useful but disconnected product artifacts.**

## Stage 2 — Close the decision loop

Stage 2 connects the human decision to external operational reality and later evaluation.

The target lifecycle becomes:

```text
Polaris recommendation
        ↓
Human decision
        ↓
Action intent
        ↓
External operational system
        ↓
Observed action
        ↓
Resulting portfolio state
        ↓
Outcome
        ↓
Evaluation
```

The supported path may remain deliberately narrow. One supported external-action and reconciliation path can be sufficient if it proves the lifecycle faithfully.

### Stage 2 success

A real bounded portfolio decision can proceed from decision need through human judgment, observed external reality, outcome, and evaluation, and Polaris can later reconstruct the connected thread.

The important transition is:

> **A Polaris decision no longer disappears after the recommendation or human decision.**

## Stage 3 — Govern and trust the complete loop

Stage 3 hardens the claims Polaris makes across the closed lifecycle.

The bounded lifecycle should enforce the relevant decision contracts, including:

* evidence provenance;
* decision-time integrity;
* decision-appropriate freshness;
* meaningful challenge;
* explicit uncertainty;
* portfolio-aware risk;
* deterministic policy;
* authority provenance;
* human-decision distinction;
* external-action authority;
* operational reality;
* historically faithful evaluation.

The transition is:

```text
Polaris can perform the lifecycle
        ↓
Polaris can make trustworthy claims about the lifecycle
```

### Stage 3 success

Within the declared operating envelope, the material decision path can be reconstructed coherently:

* what evidence existed;
* whether it was current enough;
* what interpretations and counterarguments were considered;
* what risks and constraints shaped the recommendation;
* what Polaris recommended;
* what authorities evaluated the decision;
* what the human decided;
* what happened externally;
* whether reality diverged from intent;
* what happened afterward;
* what the evaluation concluded.

## Stage 4 — Stabilize the product

The final pre-1.0 stage turns the bounded, governed decision system into product behavior Polaris is prepared to support as stable.

This stage emphasizes supporting capabilities where they are required by the supported product contract:

* runtime reliability and recovery;
* durable-state integrity;
* dependency and failure handling;
* configuration within the supported operating envelope;
* integration reliability;
* projection consistency;
* operational observability;
* security and credential handling;
* deployment reproducibility;
* migration and upgrade safety;
* explicit compatibility commitments.

Stage 4 should not become a generic infrastructure-polish phase. Every hardening item should remain attached to the bounded 1.0 product contract.

### Stage 4 success

The complete bounded product model not only works; Polaris is prepared to support its defined behavior, data integrity, recovery expectations, and product contracts as stable.

## Polaris 1.0 definition

Polaris 1.0 is:

> **The first stable release in which the complete portfolio decision lifecycle is usable, governed, durable, and operationally dependable within an explicitly bounded supported operating envelope.**

1.0 does not mean every Polaris capability has reached its ultimate depth or breadth.

It means the Product Definition is genuinely true for a declared supported context.

## 1.0 core capability floor

The intended minimum capability maturity for 1.0 is:

| Core capability | 1.0 minimum |
| --- | --- |
| Attention & Decision Initiation | M1–M2 |
| Decision Context & Evidence | **M3** |
| Investment Reasoning & Challenge | **M3** |
| Portfolio Consequence & Risk | **M3** |
| Recommendation Formation | **M3** |
| Authority & Human Decision | **M3** |
| Action Continuity & Reconciliation | **M2+, preferably M3 for the supported path** |
| Durable Decision Memory | **M3** |
| Outcome Evaluation & Learning | **M2** |

This establishes the 1.0 emphasis:

> **Governed decision-making first; sophisticated attentiveness and adaptive learning later.**

### Attention & Decision Initiation

1.0 requires a real entry into governed decision work but does not require fully autonomous attentive intelligence. User initiation and scheduled initiation may satisfy the bounded product contract.

### Decision Context & Evidence

1.0 requires governed evidence semantics, including the provenance, freshness, and sufficiency necessary for the supported decision claim.

### Investment Reasoning & Challenge

1.0 recommendations must structurally account for meaningful challenge and uncertainty rather than merely produce an analytical answer.

### Portfolio Consequence & Risk

1.0 must apply actual portfolio context and risk so that Polaris produces portfolio decisions rather than generic investment opinions.

### Recommendation Formation

The supported recommendation contract must be explainable, risk-shaped, governed, and capable of withholding a recommendation when the decision contract is not satisfied.

### Authority & Human Decision

Recommendation, deterministic policy, authority provenance, and human judgment must remain explicitly distinguishable.

### Action Continuity & Reconciliation

The complete product requires a supported path from human decision into authoritative external reality. Broad multi-provider sophistication is not required, but the supported path must be integrated and trustworthy enough for lifecycle continuity.

### Durable Decision Memory

Durable decision state must be governed and historically faithful enough to reconstruct the supported lifecycle over time.

### Outcome Evaluation & Learning

1.0 requires meaningful integrated evaluation but does not require adaptive product learning across the lifecycle.

## What 1.0 does not require

Polaris 1.0 does not require:

* M4 Adaptive maturity across the lifecycle;
* broad autonomous opportunity discovery;
* sophisticated proactive attention;
* many brokers;
* broad asset-class coverage;
* generalized screening;
* generalized quantitative research;
* enterprise IAM;
* broad compliance operations;
* autonomous capital execution;
* every interface or distribution surface;
* every possible evidence or analytics integration;
* every existing subsystem being exposed as a product feature;
* institutional-scale deployment;
* elimination of all operator sophistication.

These may become valid later product advances without making a bounded 1.0 dishonest or incomplete.

## Pre-1.0 compatibility policy

Before 1.0, Polaris product and internal contracts may change incompatibly when necessary to make the Product Definition correct.

Compatibility should not preserve an incorrect product model.

The governing rule is:

> **Before 1.0, correctness of the durable product model outranks compatibility with an incorrect or superseded contract.**

This does not make breaking change careless.

Durable user data, historical decision integrity, migrations, external integrations, and meaningful persisted semantics should still receive deliberate treatment. Breaking a contract should remain intentional, documented where material, and accompanied by the migration or invalidation behavior appropriate to the supported maturity of the product.

At 1.0, the burden changes. Supported public and product contracts acquire meaningful stability and compatibility expectations.

## Post-1.0 advancement

After 1.0, roadmap growth should become easier to classify.

Three major advancement vectors are:

### Maturity

Deepen existing capabilities, especially from M3 Governed toward M4 Adaptive.

### Breadth

Expand supported portfolios, strategies, assets, providers, brokers, evidence domains, integrations, interfaces, or operating contexts without weakening the core product contract.

### Experience

Reduce friction and improve attentiveness, interaction, progressive disclosure, explanation, configuration, and operator/user experience while preserving shared decision semantics.

Post-1.0 releases may combine these vectors, but they should continue to have a clear product thesis and capability envelope.

## Planning hierarchy

The durable planning hierarchy is:

```text
Product Definition
        ↓
Capability Model
        ↓
Release Strategy
        ↓
Roadmap
        ↓
Release definition
        ↓
Product thesis
Capability envelope
Maturity advances
Breadth
Non-goals
Product acceptance
        ↓
Specs / tickets / implementation
```

Implementation planning should remain downstream of the product claim rather than determining it by accident.

## Consequences

This release strategy implies:

* releases are product-capability increments rather than feature bundles;
* narrow trustworthy behavior is preferred to broad shallow coverage;
* every release has a product thesis and explicit capability envelope;
* capability maturity and capability breadth remain separate planning dimensions;
* vertical lifecycle slices are preferred to horizontal subsystem completion;
* governed decision claims must meet the trust floor required by those claims;
* missing lifecycle segments should generally be closed before isolated analytical sophistication is maximized;
* durable decisions, trust by architecture, and attentive intelligence remain the primary differentiation axes to deepen;
* M4 adaptation should not outrun the integrity of its historical substrate;
* supporting platform work must attach to a core product outcome;
* releases should declare non-goals and unsupported breadth explicitly;
* release completion requires product-level acceptance, not merely engineering completion;
* pre-1.0 work progresses through establishing, closing, governing, and stabilizing the decision lifecycle;
* 1.0 is a bounded stable product contract, not a claim of universal capability breadth;
* governed evidence, reasoning, portfolio/risk, recommendation, authority, and durable memory form the strongest 1.0 maturity floor;
* sophisticated attentiveness and adaptive learning may mature after 1.0;
* pre-1.0 compatibility may yield to product correctness, while durable data and historical integrity still require deliberate handling;
* post-1.0 roadmap work should clearly distinguish maturity, breadth, and experience advances.

The next planning artifact should use this strategy to evaluate the current Polaris codebase and define the actual release roadmap from today's durable state to the 1.0 product contract.
