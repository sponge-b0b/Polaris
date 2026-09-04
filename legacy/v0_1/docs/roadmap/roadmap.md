# Polaris Roadmap

**Status:** Defined  
**Purpose:** Translate the Polaris Product Definition, Capability Model, Release Strategy, and completed current-state capability audit into the release sequence from the current 0.1.0 baseline to the first stable 1.0 product contract.

This roadmap defines **what product ability should become true in each release**. It does not prescribe packages, services, agents, workflows, database tables, APIs, or other implementation topology.

The governing planning hierarchy is:

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
Specs / tickets / implementation
```

The roadmap should therefore remain a capability and product-outcome artifact rather than becoming a feature backlog.

## Planning basis

This roadmap applies:

* [`../product/product-definition.md`](../product/product-definition.md) — durable product identity, users, jobs, experience, and boundaries;
* [`../product/product-core-capabilities.md`](../product/product-core-capabilities.md) — the nine core product capabilities;
* [`../product/capability-model.md`](../product/capability-model.md) — capability relationships, maturity, authority, trust contracts, and external-system boundaries;
* [`../product/product-execution-continuity.md`](../product/product-execution-continuity.md) — continuity across externally owned execution;
* [`release-strategy.md`](./release-strategy.md) — release construction, maturity strategy, pre-1.0 stages, and the 1.0 threshold.

The current-state maturity ratings below are the frozen result of the capability audit completed against the 0.1.0 codebase on `main`.

## Current audited baseline

### Core capabilities

| Core capability | Current maturity | Current product-level finding |
| --- | --- | --- |
| Attention & Decision Initiation | **M1 — Bounded** | Useful initiation and attention ingredients exist, but decision attention is still largely execution/workflow initiated rather than preserved as canonical portfolio-decision state. |
| Decision Context & Evidence | **M1 — Bounded** | Locally sophisticated evidence provenance, reconstruction, readiness, and persistence exist, but they are not yet integrated through a canonical Portfolio Decision context. |
| Investment Reasoning & Challenge | **M1 — Bounded** | Structured hypotheses, counterevidence, assumptions, invalidation conditions, uncertainty, and synthesis are real but remain rooted in the current workflow execution path. |
| Portfolio Consequence & Risk | **M1 — Bounded** | Portfolio state and multiple risk dimensions materially shape allocation/execution posture, but the result is still a workflow/runtime output rather than shared Portfolio Decision state. |
| Recommendation Formation | **M1 — Bounded** | Polaris produces concrete trade/recommendation-like outputs, but no canonical Recommendation boundary yet connects evidence, challenge, portfolio consequence, risk, alternatives, and authority as one product object. |
| Authority & Human Decision | **M1 — Bounded** | Governance mechanics are substantial and trustworthy, but governance approval is not yet joined to a first-class Human Portfolio Decision. |
| Action Continuity & Reconciliation | **M0 — Ad hoc** | Trade-intent and broker-facing ingredients exist, but no end-to-end causal chain joins Human Decision, Action Intent, authoritative external activity, reconciliation, and resulting portfolio consequence. |
| Durable Decision Memory | **M0 — Ad hoc** | Strong persistence, provenance, replay, governance memory, and portfolio-state persistence exist without a canonical Portfolio Decision identity spanning the lifecycle. |
| Outcome Evaluation & Learning | **M0 — Ad hoc** | AI/output evaluation is substantial, but realized portfolio decisions are not yet evaluated through original context, human choice, external action, outcome, causal interpretation, and durable lessons. |

### Supporting platform capabilities

| Supporting capability | Current maturity | Current product-level finding |
| --- | --- | --- |
| Integration & Connectivity | **M1 — Bounded** | Strong provider/client boundaries and evidence attribution exist for a narrow operating context, but external action observation and reconciliation are incomplete. |
| Interaction & Projection | **M1 — Bounded** | CLI, MCP, reports, and inspection surfaces are useful, but they project workflow/application fragments rather than one canonical Portfolio Decision state. |
| Configuration & Extensibility | **M1 — Bounded** | Technical/provider/model/runtime configurability is strong; investment-domain configuration remains incomplete. |
| Runtime Reliability & Observability | **M1 — Bounded** | Runtime execution, checkpoints, replay, health, telemetry, and inspection are sophisticated, but the protected unit is primarily Workflow Execution rather than Portfolio Decision continuity. |
| Security & Operations | **M0 — Ad hoc** | Useful secret handling, redaction, transport authentication, readiness, and local operations exist without a bounded product-wide security and operational trust contract. |

### How to read this baseline

The maturity model is intentionally strict.

M1 recognizes that a capability can produce a trustworthy result inside a deliberately narrow supported context. M2 requires the capability to participate in the **canonical Polaris Portfolio Decision lifecycle** and exchange the correct shared product semantics with adjacent capabilities.

That canonical lifecycle does not yet exist as the product's authoritative unit. Therefore local subsystem sophistication does not elevate a current capability above M1 merely because portions of its implementation are already M2- or M3-grade in isolation.

This distinction is central to the roadmap:

> **The primary pre-1.0 problem is not lack of sophisticated infrastructure. It is that valuable infrastructure is organized around Workflow Execution rather than the durable Portfolio Decision lifecycle.**

## Architectural starting point

The current system can be simplified conceptually as:

```text
External providers
       ↓
Technical configuration
       ↓
Morning Report / workflow
       ↓
Workflow runtime
       ↓
Workflow execution state
       ↓
Workflow outputs
       ↓
CLI / MCP / reports

+ workflow persistence
+ workflow replay
+ workflow observability
+ workflow-oriented governance and evidence assembly
```

This topology contains substantial reusable value. The roadmap does not require discarding it.

The required inversion is:

```text
          External authoritative systems
                     ↓
           Integration & Connectivity
                     ↓
            Portfolio Decision System
                     │
      ┌──────────────┼──────────────┐
      │              │              │
   Evidence      Reasoning      Portfolio/Risk
      │              │              │
      └──────────────┼──────────────┘
                     ↓
               Recommendation
                     ↓
               Human Decision
                     ↓
        External Action / Outcome
                     ↓
                Evaluation

       Durable Decision Memory spans all.

                     ↑
       ┌─────────────┼─────────────┐
       │             │             │
      CLI           MCP       Reports / UI
       └──── shared projections ────┘

                  Runtime
                     ↑
           used when orchestration,
        recovery, or multi-step work helps
```

The governing architectural roadmap rule is:

> **Preserve useful mechanisms; change ownership. Workflows may orchestrate Polaris capabilities, but Workflow Execution must stop defining what Polaris is capable of doing.**

This is dependency inversion and semantic consolidation, not a mandate for indiscriminate rewrite.

## Pre-1.0 supported operating envelope

Pre-1.0 should deliberately prove the complete product within a narrow operating context before broadening it.

The default supported envelope for roadmap planning is:

* one sophisticated individual operator or small-team operating model;
* one bounded portfolio context;
* SPY as the primary security and decision path;
* one supported brokerage / authoritative external-action path, using Alpaca where it remains fit for the required observation and reconciliation contract;
* the current evidence-provider family where necessary for the supported SPY decision contract;
* discretionary human investment authority;
* decision-time and analytical-time responsiveness rather than exchange-engine latency;
* existing CLI, MCP, and reporting surfaces where they efficiently expose the shared product state.

The default pre-1.0 non-goals are:

* autonomous market-facing execution;
* broad multi-broker support;
* broad asset-class expansion;
* generalized screening or quantitative-research platform behavior;
* high-frequency or latency-sensitive trading infrastructure;
* enterprise IAM or institutional compliance operations;
* a general-purpose AI-agent or workflow platform;
* a large UI program merely to create another surface;
* M4 adaptive learning before trustworthy lifecycle history exists.

Breadth may move earlier only when the absence of breadth prevents a meaningful bounded product claim.

## Roadmap at a glance

| Release | Product thesis | Primary strategic stage |
| --- | --- | --- |
| **0.1.0 — Current baseline** | Polaris has a sophisticated workflow, evidence, reasoning, risk, governance, persistence, evaluation, and runtime substrate, but no canonical durable Portfolio Decision lifecycle. | Baseline |
| **0.2.0 — Canonical Decision System** | A Polaris portfolio decision becomes durable shared product state independent of any one workflow execution. | Establish the decision system |
| **0.3.0 — Closed Decision Loop** | A human portfolio decision remains causally connected through authoritative external action, resulting state, outcome, and evaluation. | Close the decision loop |
| **0.4.0 — Governed Decision Loop** | Polaris can make trustworthy, reconstructable claims about the complete bounded decision lifecycle. | Govern and trust the loop |
| **0.5.0 — Stable Product Candidate** | The bounded governed decision system is operationally dependable enough to support as a stable product candidate. | Stabilize the product |
| **1.0.0 — Stable Bounded Product** | The complete bounded Portfolio Decision lifecycle satisfies the defined maturity, trust, durability, operational, and compatibility threshold. | Stable product contract |

The numbered releases implement the strategic stages in [`release-strategy.md`](./release-strategy.md). They are product milestones, not subsystem completion buckets.

# 0.2.0 — Canonical Decision System

## Product thesis

> **A Polaris portfolio decision becomes a durable product object and lifecycle independent of any individual workflow run.**

This release establishes the semantic center required by every later release.

The target bounded lifecycle is:

```text
Decision need
    ↓
Decision context + attributable evidence
    ↓
Reasoning + challenge
    ↓
Portfolio consequence + risk
    ↓
Recommendation
    ↓
Authority state
    ↓
Human Portfolio Decision

Durable Decision Memory spans the lifecycle.
```

## Product abilities established

Within the supported SPY decision context, Polaris should be able to:

* create or reopen one identifiable Portfolio Decision through a supported user-initiated or scheduled path;
* preserve a stable identity for that decision across multiple analyses, runtime executions, process restarts, and projections;
* attach decision-specific context and attributable evidence to that decision rather than only to a workflow run or report;
* preserve structured reasoning, meaningful challenge, assumptions, uncertainty, alternatives, and invalidation conditions as decision state;
* apply actual portfolio context, analytical risk, and applicable deterministic policy to the decision;
* establish a canonical Recommendation distinct from intermediate strategy synthesis, allocation intent, trade packaging, and presentation output;
* preserve governance/admissibility judgments without confusing them with the human's investment choice;
* record the Human Portfolio Decision as accept, modify, reject, or defer, with rationale where supplied;
* reconstruct the material lifecycle state after process restart;
* expose the same decision semantics through at least one direct interaction path without requiring the complete Morning Report workflow to run;
* allow the Morning Report to consume/orchestrate the same canonical capabilities rather than remaining their owner.

## Capability envelope

| Capability | 0.1.0 | 0.2.0 target |
| --- | ---: | ---: |
| Attention & Decision Initiation | M1 | **M2** |
| Decision Context & Evidence | M1 | **M2** |
| Investment Reasoning & Challenge | M1 | **M2** |
| Portfolio Consequence & Risk | M1 | **M2** |
| Recommendation Formation | M1 | **M2** |
| Authority & Human Decision | M1 | **M2** |
| Durable Decision Memory | M0 | **M2** |
| Interaction & Projection | M1 | **M2 for the supported decision projection** |
| Runtime Reliability & Observability | M1 | **M2 for decision-linked runtime work** |

Action Continuity & Reconciliation and Outcome Evaluation & Learning do not need to advance yet because 0.2 deliberately stops at the Human Portfolio Decision boundary.

## Architectural consequences

0.2 should establish the smallest authoritative semantic spine necessary to bind the lifecycle. It should not create one new subsystem per capability.

The release should preferentially re-parent existing strengths:

* decision-evidence packets, claim binding, readiness, reconstruction, and persistence;
* structured strategy hypotheses, counterevidence, assumptions, invalidation conditions, and synthesis;
* portfolio state and risk analysis;
* recommendation/trade-intent ingredients;
* governance and separation-of-powers authority machinery;
* PostgreSQL durability;
* runtime execution, checkpoints, replay, and telemetry;
* CLI/MCP/report projection mechanisms.

Workflow execution identity may remain useful operational metadata, but it must become subordinate to Portfolio Decision identity.

The release should not create a second persistence framework, governance engine, runtime, evidence system, or orchestration platform merely because the product semantics are changing.

## Product acceptance

0.2 is complete when a supported SPY decision can demonstrate all of the following:

1. It has one stable Portfolio Decision identity.
2. The decision can begin without treating a Morning Report workflow execution as its identity.
3. Its evidence, reasoning/challenge, portfolio consequence, risk, Recommendation, authority state, and Human Portfolio Decision can be inspected as one coherent lifecycle.
4. The Recommendation, governance/admissibility judgment, and Human Portfolio Decision are visibly distinct facts.
5. A later process can reconstruct the decision's material state without rebuilding it from a report or conversation transcript.
6. At least one product interaction path can directly inspect or advance that decision state without running the entire Morning Report.
7. The Morning Report, if retained, consumes the same canonical decision semantics rather than creating a parallel product truth.

## Non-goals

0.2 does not require:

* broker order/fill reconciliation;
* realized-outcome evaluation;
* active learning;
* broad proactive attention;
* additional brokers or asset classes;
* a new web UI;
* broad infrastructure replacement.

# 0.3.0 — Closed Decision Loop

## Product thesis

> **A Polaris decision no longer disappears after the human decides.**

0.3 connects the canonical decision to externally owned operational reality and later outcome evaluation without giving Polaris execution authority.

The target lifecycle becomes:

```text
Portfolio Decision
      ↓
Recommendation
      ↓
Human Portfolio Decision
      ↓
Action Intent
      ↓
Authoritative external system
      ↓
Observed external activity
      ↓
Reconciliation
      ↓
Resulting portfolio state
      ↓
Outcome
      ↓
Decision Outcome Evaluation
```

## Product abilities established

Within one deliberately narrow supported broker/action path, Polaris should be able to:

* derive and durably preserve an Action Intent from the Human Portfolio Decision without translating that intent into execution authority;
* observe authoritative external operational facts needed for the supported path;
* associate external orders, fills, partial fills, modifications, cancellations, exits, and resulting state where the provider makes those facts available and relevant;
* automatically reconcile associations that are sufficiently unambiguous;
* preserve ambiguity when multiple associations are plausible and request lightweight confirmation rather than guess;
* distinguish externally initiated activity from activity caused by a Polaris decision;
* preserve operational divergence between intent and reality rather than rewriting either side;
* link resulting portfolio state to the originating decision;
* evaluate the portfolio decision using historically faithful decision-time context plus later action/outcome evidence;
* distinguish process quality, human modification, implementation fidelity, realized outcome, and causal interpretation;
* preserve useful lessons without yet claiming adaptive product behavior.

## Capability envelope

| Capability | 0.2.0 | 0.3.0 target |
| --- | ---: | ---: |
| Action Continuity & Reconciliation | M0 | **M2** |
| Durable Decision Memory | M2 | **M2, extended through outcome** |
| Outcome Evaluation & Learning | M0 | **M2** |
| Integration & Connectivity | M1 | **M2 for the supported external-action path** |
| Interaction & Projection | M2 | **M2, extended through reconciliation/evaluation** |

The release does not need broad execution-provider coverage. One trustworthy path is enough to establish the capability.

## Architectural consequences

0.3 should preserve the specialist boundary:

> **Polaris owns the continuity of the decision lifecycle, not brokerage execution.**

Broker/execution and authoritative portfolio systems remain authoritative for what operationally occurred.

Existing `TradeIntentContract`-style concepts may provide useful ingredients, but Action Intent must be rooted in the Human Portfolio Decision rather than inferred retrospectively from a workflow's trade-packaging output.

Existing AI/output evaluation remains a supporting quality subsystem. Decision Outcome Evaluation should be a distinct product-level semantic boundary rather than stretching model/output evaluation into investment-outcome meaning.

## Product acceptance

0.3 is complete when one supported SPY decision can be followed from initiation through later evaluation such that Polaris can answer:

1. What did Polaris recommend?
2. What did governance permit or constrain?
3. What did the human actually decide?
4. What external change did that human decision intend?
5. What did the authoritative external system report actually happened?
6. Where did reality diverge from intent, if anywhere?
7. What resulting portfolio state followed?
8. What outcome was observed?
9. How should the decision process be evaluated separately from the realized result?

The complete thread must be reconstructable after the fact.

## Non-goals

0.3 does not require:

* Polaris-originated market orders;
* autonomous execution;
* multiple brokers;
* broad real-time trading infrastructure;
* M4 adaptive learning;
* perfect causal certainty where evidence does not support it.

# 0.4.0 — Governed Decision Loop

## Product thesis

> **Polaris can make trustworthy and reconstructable claims about the complete bounded Portfolio Decision lifecycle.**

0.2 establishes the lifecycle. 0.3 closes it. 0.4 raises the trust floor across it.

## Product abilities strengthened

The supported decision path should enforce or preserve the relevant trust contracts end to end:

* attributable evidence provenance;
* decision-time integrity — what was knowable then remains distinct from what is known now;
* decision-appropriate freshness and explicit stale-state handling;
* evidence sufficiency and fail-closed behavior where required inputs do not support the claimed recommendation;
* visible source conflicts and unresolved material conflict handling;
* meaningful challenge, counterevidence, alternatives, assumptions, uncertainty, and invalidation conditions;
* actual portfolio state and portfolio-aware analytical risk;
* deterministic risk/policy constraints before recommendation admissibility;
* the ability to withhold a Recommendation rather than fabricate certainty;
* positive authority provenance rather than inferring approval from absence of failure;
* explicit separation among analytical authority, deterministic authority, Human Portfolio Decision authority, and external action authority;
* operational reality outranking expected action;
* historically faithful reconstruction of the complete material decision path;
* outcome evaluation that preserves causal humility and does not equate P&L with decision quality;
* bounded review/reassessment conditions capable of re-entering the lifecycle when material state changes.

## Capability envelope

| Core capability | 0.3.0 | 0.4.0 target |
| --- | ---: | ---: |
| Attention & Decision Initiation | M2 | **M2** |
| Decision Context & Evidence | M2 | **M3** |
| Investment Reasoning & Challenge | M2 | **M3** |
| Portfolio Consequence & Risk | M2 | **M3** |
| Recommendation Formation | M2 | **M3** |
| Authority & Human Decision | M2 | **M3** |
| Action Continuity & Reconciliation | M2 | **M2+, preferably M3 for the supported path** |
| Durable Decision Memory | M2 | **M3** |
| Outcome Evaluation & Learning | M2 | **M2** |

Supporting capabilities should advance only where necessary to make those trust claims true for the supported path.

## Product acceptance

Within the declared operating envelope, Polaris must be able to reconstruct coherently:

* why the decision existed;
* what evidence existed and whether it was current and sufficient enough;
* what interpretations, assumptions, alternatives, counterarguments, uncertainties, and invalidation conditions were considered;
* how actual portfolio state and risk changed the available actions;
* what Polaris recommended or why it withheld a recommendation;
* which deterministic and governance authorities applied and what they concluded;
* what the human decided;
* what external reality reported;
* whether intent and reality diverged;
* what happened afterward;
* what the evaluation concluded and what causal uncertainty remains.

The release should fail the product claim rather than silently lower the trust standard when required evidence or authority state is missing.

## Non-goals

0.4 does not require:

* broad autonomous attention;
* M4 adaptive learning;
* many brokers, assets, strategies, or portfolio structures;
* enterprise compliance or IAM;
* a generalized policy/rules platform.

# 0.5.0 — Stable Product Candidate

## Product thesis

> **The bounded governed Portfolio Decision system is operationally dependable enough to support as a stable product candidate.**

0.5 hardens the product contract established in the earlier releases. It is not a generic infrastructure-polish release.

Every supporting-platform change must attach to a concrete requirement of the bounded 1.0 product claim.

## Supporting capability priorities

### Integration & Connectivity

For the supported evidence, portfolio, and external-action paths:

* dependency health and failure states are visible;
* provider failure does not silently become decision evidence;
* retry/degradation behavior preserves product semantics;
* external authority and provenance remain intact through normalization;
* the supported reconciliation path is operationally dependable.

### Interaction & Projection

At least the maintained CLI/MCP/report surfaces required by the supported product should project the same Portfolio Decision truth.

Surfaces should not independently reconstruct Recommendation, authority, Human Decision, external action, or evaluation semantics.

Additional surfaces are breadth, not a stability requirement.

### Configuration & Extensibility

The supported deployment should expose the investment-domain configuration required by the product envelope, such as:

* portfolio identity/context;
* supported strategy/process choices;
* security or asset universe boundary;
* investment horizon;
* evidence-provider selection where appropriate;
* model/profile selection where appropriate;
* risk policy and thresholds;
* review/reassessment conditions;
* operating preferences.

This should reuse existing configuration and DI mechanisms rather than turning Polaris into arbitrary workflow programmability.

### Runtime Reliability & Observability

Runtime behavior should now protect **decision continuity**, not only workflow-execution continuity.

Required behavior may include:

* restart/recovery without losing the material Portfolio Decision state;
* runtime failures clearly attributable to affected decision work;
* resumability where product semantics permit it;
* durable-state integrity across runtime execution boundaries;
* observability capable of following the meaningful decision thread through the underlying executions that served it.

### Security & Operations

0.5 should establish a bounded security and operating contract appropriate to the defined user and deployment envelope.

That includes, where required:

* protected credentials and secret lifecycle expectations;
* portfolio and decision information boundaries;
* authenticated externally exposed transports;
* authorization only to the degree required by the supported individual/small-team operating model;
* reproducible deployment and configuration;
* dependency readiness and diagnostics;
* durable-state backup/recovery expectations appropriate to the supported deployment;
* migration and upgrade safety;
* explicit operational assumptions and unsupported deployment modes.

Enterprise IAM is not required unless the product strategy changes.

## Capability envelope

The exact supporting maturity required is claim-dependent, but the intended 0.5 floor is:

| Supporting capability | 0.5.0 target |
| --- | ---: |
| Integration & Connectivity | **M2+, M3 where trust of the supported path requires it** |
| Interaction & Projection | **M2** |
| Configuration & Extensibility | **M2** |
| Runtime Reliability & Observability | **M3 for the supported decision lifecycle** |
| Security & Operations | **M1 — Bounded** |

Core capability maturity from 0.4 must not regress during stabilization.

## Product acceptance

0.5 is complete when the bounded product candidate can demonstrate that:

1. a clean supported deployment can be established reproducibly;
2. required dependencies have explicit health and failure behavior;
3. a process/service restart does not destroy the durable Portfolio Decision lifecycle;
4. failed underlying execution is visible in terms of affected decision work;
5. supported surfaces project the same canonical decision state;
6. configuration is sufficient for the declared portfolio/strategy/risk/operating envelope without editing runtime internals;
7. supported credentials, transport boundaries, and portfolio data receive the declared level of protection;
8. migrations/upgrades preserve or deliberately migrate supported durable decision history;
9. recovery expectations are explicit and demonstrable;
10. obsolete workflow-only product paths have either been re-parented, deliberately retained as orchestration, or explicitly deprecated after their replacement exists.

# 1.0.0 — Stable Bounded Product

## Product thesis

> **The Product Definition is genuinely true and supportable for one explicitly bounded operating context.**

1.0 is not another feature bucket after 0.5. It is the point at which the 0.5 product candidate satisfies the stable product contract and Polaris is prepared to place meaningful compatibility weight behind it.

The governing definition remains:

> **Polaris 1.0 is the first stable release in which the complete portfolio decision lifecycle is usable, governed, durable, and operationally dependable within an explicitly bounded supported operating envelope.**

## 1.0 core maturity floor

The minimum core floor remains the one defined by [`release-strategy.md`](./release-strategy.md):

| Core capability | 1.0 minimum |
| --- | ---: |
| Attention & Decision Initiation | M1–M2 |
| Decision Context & Evidence | **M3** |
| Investment Reasoning & Challenge | **M3** |
| Portfolio Consequence & Risk | **M3** |
| Recommendation Formation | **M3** |
| Authority & Human Decision | **M3** |
| Action Continuity & Reconciliation | **M2+, preferably M3 for the supported path** |
| Durable Decision Memory | **M3** |
| Outcome Evaluation & Learning | **M2** |

1.0 does not require M4 adaptive maturity or broad product breadth.

## Stability threshold

Before declaring 1.0, Polaris should be prepared to support the declared behavior and durable semantics as stable, including:

* the meaning and identity of Portfolio Decision lifecycle state;
* the distinctions among Recommendation, governance/admissibility, Human Portfolio Decision, Action Intent, observed external reality, outcome, and evaluation;
* supported durable data and reconstruction behavior;
* the supported interaction and integration contracts;
* explicit migration behavior when durable schema or semantics evolve;
* the documented operating envelope and non-goals.

Before 1.0, incorrect internal and product contracts may be broken deliberately to make the durable product model correct. At 1.0, compatibility acquires a materially higher burden.

## Product acceptance

1.0 can be released when one bounded real product path demonstrates, repeatedly and supportably:

```text
Decision need
    ↓
Decision-ready context + evidence
    ↓
Reasoning + meaningful challenge
    ↓
Actual portfolio consequence + risk
    ↓
Governed Recommendation
    ↓
Human Portfolio Decision
    ↓
Action Intent
    ↓
Authoritative external reality
    ↓
Reconciliation + resulting state
    ↓
Outcome
    ↓
Decision Outcome Evaluation

Durable Decision Memory preserves the historically faithful thread.
```

The path must survive the operational conditions and recovery expectations claimed by the supported deployment.

# What should be preserved

The capability audit found substantial machinery worth retaining and reusing.

The roadmap should prefer preservation of:

* provider/client integration boundaries and dependency injection;
* evidence packets, claim references, reconstruction metadata, readiness, persistence, and provenance;
* strategy hypothesis, challenge, synthesis, assumptions, and invalidation semantics;
* existing market, macro, news, sentiment, technical, portfolio, and risk intelligence where it serves the supported decision contract;
* portfolio-state acquisition and persistence;
* governance, review, deterministic policy, and separation-of-powers machinery;
* PostgreSQL persistence and existing durable-state infrastructure;
* runtime execution, checkpoints, replay/resume, lifecycle events, health, and telemetry;
* existing AI/output evaluation and observability as supporting quality mechanisms;
* provider profiles, DI composition, and useful plugin mechanisms;
* thin transport boundaries such as CLI and MCP that delegate into canonical application behavior;
* report generation where it becomes a projection of shared decision state.

Preservation means retaining useful semantics and mechanisms, not preserving their current ownership when that ownership encodes the wrong product center.

# What should be re-parented

Several existing concepts are valuable but currently attached primarily to Workflow Execution.

As the canonical Portfolio Decision lifecycle is established, likely re-parenting targets include:

* workflow execution identity → operational execution linked to Portfolio Decision identity;
* workflow output contracts → implementation/projection results beneath canonical decision semantics;
* strategy synthesis decisions → reasoning inputs to the canonical Recommendation;
* portfolio allocation intent → portfolio consequence/risk input rather than a substitute for Human Portfolio Decision;
* trade-packaging output → Recommendation/Action-Intent ingredients rather than proof of execution continuity;
* completed-workflow archives → supporting execution history linked into Durable Decision Memory;
* workflow checkpoints/replay → runtime continuity serving decision continuity;
* workflow projections/reports → projections of shared Portfolio Decision state;
* AI/output evaluation → supporting model/product quality evidence distinct from Decision Outcome Evaluation.

The intended direction is:

```text
existing mechanism
       ↓
retain useful semantics
       ↓
attach to canonical product responsibility
       ↓
remove accidental workflow ownership
```

# What should be deferred

Unless a release thesis specifically requires otherwise, pre-1.0 should defer:

* additional broker breadth;
* broad asset-class expansion;
* broad UI/dashboard construction;
* generalized screening;
* generalized quantitative-research environment behavior;
* arbitrary workflow/agent extensibility;
* autonomous execution;
* enterprise IAM and broad compliance operations;
* sophisticated M4 adaptive learning;
* broad autonomous opportunity discovery;
* infrastructure replacement that does not materially improve the bounded Portfolio Decision contract.

# Cross-release invariants

Every pre-1.0 release should preserve these distinctions:

> **Workflow Execution ≠ Portfolio Decision**

> **Governance Approval ≠ Human Portfolio Decision**

> **What Polaris recommended ≠ what governance permitted ≠ what the human decided ≠ what happened externally**

> **Trade Intent ≠ Observed Execution**

> **Observed External Activity ≠ Reconciled Decision Consequence**

> **Persistence ≠ Durable Decision Memory**

> **Workflow Run Identity ≠ Portfolio Decision Identity**

> **AI Evaluation ≠ Portfolio Decision Evaluation**

> **Outcome ≠ Decision Quality**

> **Technical Configuration ≠ Product Configuration**

> **Workflow Reliability ≠ Decision Continuity**

> **Integration Count ≠ Integration Capability**

> **Breadth ≠ Maturity**

Additional governing invariants are:

* decisions remain the product center;
* AI remains a reasoning participant rather than governing authority;
* deterministic software owns deterministic guarantees and policy where appropriate;
* consequential investment judgment remains human;
* external specialist systems retain authority over the operational facts they own;
* operational reality outranks Polaris's expected action;
* supporting platform work must attach to a core product outcome;
* product semantics should be shared across interaction surfaces;
* pre-1.0 compatibility must not preserve an incorrect product model;
* existing valuable infrastructure should be reused rather than duplicated unless the current mechanism cannot satisfy the corrected product responsibility.

# Roadmap change discipline

This roadmap is directional product authority downstream of the Product Definition, Capability Model, and Release Strategy.

A proposed roadmap change should answer:

1. What portfolio decision ability becomes newly usable, more trustworthy, more connected, more adaptive, or meaningfully broader?
2. Which capability maturity or lifecycle-closure gap does it address?
3. Does it strengthen the declared release thesis or create an unrelated subsystem milestone?
4. Does it expand breadth, and if so, why is that breadth necessary now?
5. Does it accidentally transfer responsibility from an external specialist system to Polaris?
6. Does it preserve the distinction between product semantics and current implementation topology?

If a planned release becomes too large, split it only where each resulting release still has a coherent product thesis and useful vertical capability slice. Do not split work merely to create separate evidence, runtime, RAG, UI, persistence, or integration milestones.

Engineering completion is necessary but not sufficient. Each release ends only when its product acceptance claim is demonstrated inside its declared capability envelope.

# Next planning transition

Once this roadmap is reviewed and accepted, implementation planning should begin with **0.2.0 — Canonical Decision System**.

Do not decompose every later roadmap release into implementation tickets immediately.

The next planning question is narrower:

> **What is the smallest correct product and architecture change set that establishes one canonical Portfolio Decision lifecycle through the Human Portfolio Decision boundary while preserving and re-parenting the strongest existing Polaris machinery?**

That release should then move through the normal architecture/specification/ticket workflow appropriate to the concrete implementation uncertainty discovered during planning.
