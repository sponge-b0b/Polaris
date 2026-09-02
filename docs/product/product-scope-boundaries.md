# Polaris Scope Boundaries

**Status:** In progress  
**Purpose:** Preserve the product reasoning for which responsibilities Polaris owns, which capabilities may support the decision system without becoming independent product mandates, and which specialist responsibilities remain outside the product's defining scope.

This document refines the Product Definition recorded in [`product-definition.md`](./product-definition.md). It defines product responsibility boundaries rather than a feature blacklist or implementation architecture.

## Decision

Polaris owns the **portfolio decision lifecycle** and the trust, context, provenance, attention, reasoning, authority, continuity, evaluation, and learning responsibilities necessary to make that lifecycle coherent.

It does not need to own every system or capability that supplies evidence to, supports, or receives action from that lifecycle.

The governing distinction is:

> **Polaris owns decisions, not everything decisions touch.**

Two additional rules follow:

> **Dependency does not imply ownership.**

> **Feature presence does not imply product-category ownership.**

A capability may exist inside Polaris, and may become sophisticated, without turning the broader capability category into an independent product center.

## Three scope rings

Polaris scope is best understood as three concentric responsibility rings.

### Ring 1 — Polaris-owned responsibilities

These are responsibilities without which Polaris stops being the product defined by Purpose, Users, Jobs, Product Identity, Core Experience, and Authority Model.

Conceptually they include:

```text
Attention / materiality
        ↓
Decision context
        ↓
Evidence use + provenance
        ↓
Interpretation + challenge
        ↓
Portfolio consequences
        ↓
Risk-aware reasoning
        ↓
Authority + governance
        ↓
Recommendation
        ↓
Human decision continuity
        ↓
External-action reconciliation
        ↓
Outcome
        ↓
Evaluation
        ↓
Learning
```

These labels are product responsibilities, not a commitment to software modules or service boundaries.

Polaris must own the semantics and integrity of this decision lifecycle even when underlying facts or operational actions come from specialist external systems.

### Ring 2 — Supporting capabilities

Capabilities outside the core lifecycle may exist within Polaris when they materially improve portfolio decision-making, reduce user friction, support explanation, preserve continuity, or improve later evaluation.

Examples may include:

* charts and visualizations;
* news ingestion;
* technical indicators;
* opportunity discovery and screening;
* simulation and backtesting;
* historical analog analysis;
* reports and PDFs;
* email or messaging delivery;
* conversation;
* dashboards;
* research tools;
* collaboration;
* integrations.

Supporting status does not mean low quality or intentionally shallow functionality. A supporting capability may be excellent when excellence materially improves the decision experience.

The constraint is purpose:

> **Supporting capabilities must justify themselves through decision value rather than developing independent product mandates.**

For example, excellent interactive charting may be justified when it helps a user interrogate material evidence behind a recommendation. That does not imply Polaris should compete for every charting use case merely because it contains charts.

### Ring 3 — External specialist responsibilities

Some responsibilities remain deliberately owned by specialist systems even when Polaris integrates with them deeply.

Examples include:

* exchange-speed execution;
* brokerage operations;
* official books and records;
* portfolio accounting;
* custody;
* settlement;
* tax accounting;
* comprehensive market-data vending;
* generalized charting platforms;
* generalized quantitative-programming environments;
* general-purpose AI systems;
* broad news-terminal or publishing functions;
* communication infrastructure;
* broad regulatory and compliance operations not intrinsic to Polaris decision governance.

Polaris may consume evidence from these systems, project information into them, observe their resulting state, and offer narrower supporting features in adjacent areas. Integration does not transfer their specialist product responsibility to Polaris.

## Market data

Market evidence is necessary for current portfolio decisions, but producing a comprehensive low-latency market-data service is not a defining Polaris responsibility.

In scope are responsibilities such as:

* obtaining decision-relevant market evidence;
* normalizing it where necessary;
* preserving attribution and provenance;
* evaluating decision-appropriate freshness;
* determining whether evidence is sufficient for the decision contract;
* connecting market changes to affected portfolio decisions.

Outside the defining scope is becoming the authoritative producer and distributor of a comprehensive exchange-speed market feed.

The data provider may own the underlying feed. Polaris owns whether and how that evidence can support a trustworthy portfolio decision.

## Portfolio state

Portfolio context is load-bearing for Polaris.

Polaris needs enough trustworthy portfolio state to reason about holdings, exposure, concentration, cash where relevant, risk, alternatives, resulting actions, and decision outcomes.

That does not make Polaris the official portfolio ledger by default.

Where another system has authoritative responsibility for holdings, accounting, or operational portfolio state, Polaris should consume and reconcile that state while preserving the source's factual authority.

The boundary is:

> **Polaris owns decision-oriented portfolio context; it does not automatically own the official operational portfolio record.**

## Research and information

Research, synthesis, and interpretation are central to Polaris, but comprehensive information possession is not the product objective.

Polaris should be able to gather, attribute, preserve, synthesize, compare, challenge, and connect research to active theses and portfolio decisions.

It does not follow that Polaris must become the largest financial-news archive, analyst-report terminal, or general research database.

The optimization target is **decision-relevant research**, not maximum information volume.

## Simulation, backtesting, and historical analysis

Simulation and historical analysis are in scope when they help form, challenge, evaluate, or improve portfolio decisions or the decision process itself.

Examples include:

* testing how a strategy or decision rule behaved historically;
* evaluating whether a reasoning pattern was useful;
* finding materially similar historical decisions;
* comparing alternative portfolio actions;
* assessing decision or recommendation behavior under relevant scenarios.

Polaris is not thereby obligated to become a general-purpose quantitative research and algorithm-development environment for arbitrary systematic trading systems.

The scope test is whether the analytical capability materially supports the Polaris decision lifecycle or its evaluation.

## Risk

Risk is a core Polaris responsibility where it affects portfolio judgment.

Polaris owns questions such as:

* what could go wrong;
* how risk has changed;
* how portfolio exposure affects the decision;
* whether a recommendation satisfies configured decision policy;
* how risk should alter the preferred action.

Execution-time risk controls remain the responsibility of specialist operational systems where they own functions such as margin enforcement, buying-power controls, order rejection, exchange controls, or market-speed kill switches.

Polaris may observe and reason about those operational controls without becoming the system required to enforce them at market latency.

## Reporting and distribution

Reports, PDFs, emails, dashboards, CLI output, MCP, APIs, and other delivery mechanisms are valid Polaris surfaces.

They should remain projections of shared decision state rather than independent product centers that reconstruct their own version of the decision.

Conceptually:

```text
Decision record
      ↓
Web / dashboard
PDF
Email / messaging
CLI
API
MCP
```

Distribution may be sophisticated, but the durable product object remains the decision lifecycle rather than any one rendering or channel.

## Governance versus broad compliance operations

Decision governance is core Polaris scope because the Authority Model requires enforceable constraints, evidence sufficiency, human authority, policy evaluation, and durable authority provenance.

That does not automatically place broad regulatory operations inside Polaris scope.

Functions such as regulatory filing, comprehensive records-retention administration, employee surveillance, generalized trade-preclearance operations, or an institution-wide compliance platform would represent distinct product responsibilities unless later product strategy explicitly adopts them.

The boundary is:

> **Decision governance is core; broad regulatory operations are not automatically part of the product.**

## Collaboration versus enterprise organization machinery

Small-team decision collaboration is consistent with the accepted user model.

Polaris may therefore need capabilities such as review, commentary, handoff, decision ownership, challenge, approval, or role-aware authority as team usage matures.

That does not make enterprise organizational infrastructure a present design center.

Complex enterprise IAM, large role matrices, departmental workflow systems, organization hierarchies, and multi-tenant enterprise administration should be justified by actual product maturity rather than assumed because financial institutions may eventually use Polaris.

## Opportunity discovery and screening

Polaris may surface relevant opportunities outside the current portfolio when doing so serves the decision process.

For example, an attentive system may reasonably identify that a materially relevant opportunity deserves a portfolio decision even though the user did not explicitly screen for it.

That does not require comprehensive security screening to become a defining product responsibility.

The boundary is:

> **Opportunity discovery may support the attentive decision system; generalized screening is not itself the product center.**

## Conversation

Conversation is an important possible interface to portfolio decisions, evidence, risk, history, and authority state.

Polaris is not a general financial chatbot.

Conversational flexibility should remain grounded in durable portfolio context and the decision lifecycle rather than creating an unrestricted parallel product whose answers are disconnected from governed decision state.

## Generic workflow construction

Polaris may contain a powerful and reusable internal runtime.

Generic workflow construction is not itself a Polaris user job.

Infrastructure may remain general internally where that produces a better implementation, but product capability should not be justified merely because the runtime could be exposed as a framework for arbitrary financial or AI workflows.

The durable boundary is:

> **Reusable internal infrastructure is compatible with Polaris; a general-purpose workflow platform is not the product identity.**

## Preserve external authority; avoid shadow systems of record

Polaris may cache, normalize, derive, and preserve external state for decision purposes.

Where another system owns factual authority, Polaris should preserve that boundary rather than quietly becoming a competing shadow system of record.

If an authoritative broker reports one position state while Polaris expected another, Polaris should reconcile the discrepancy and preserve what each source represents. It should not elevate an internal expectation to equal factual authority merely because it was stored locally.

The same principle applies to market data, economic releases, execution events, accounting facts, and other externally authoritative evidence.

This extends the Authority Model:

> **Operational reality outranks expected or cached state.**

## Supporting capabilities may be excellent

Scope discipline should not produce an impoverished product.

A supporting capability may be sophisticated, differentiated, and deeply integrated when doing so materially improves the Polaris experience.

The restriction is that its evolution remains accountable to the portfolio decision system.

For example:

> If excellent interactive visualization materially improves a user's ability to interrogate a decision, Polaris should be willing to provide excellent visualization.

The unsupported leap would be:

> Polaris contains charts, therefore it should compete across every generalized charting use case.

Purpose constrains scope; it does not impose mediocrity.

## Scope decision test

A major proposed capability should be evaluated in order:

1. **Does it materially support a durable Polaris job?**  
   Understand, Challenge, Apply portfolio context, Decide under risk, Explain, or Learn.
2. **Does Polaris need to own this responsibility to fulfill its decision contract?**  
   If yes, it belongs in core scope.
3. **Can a specialist system own the underlying responsibility while Polaris consumes, reconciles, or projects the necessary evidence?**  
   If yes, integration should be preferred over duplicated ownership.
4. **Would a narrower Polaris-native capability materially reduce user friction or improve decision quality?**  
   If yes, it may belong as a supporting capability.
5. **Would owning the full category create a separate primary job or materially change Polaris's authority model, latency contract, operational responsibility, regulatory burden, or product identity?**  
   If yes, there is a strong presumption against expansion until the Product Definition is explicitly reconsidered.

This test should keep scope decisions tied to product responsibility rather than implementation possibility or feature enthusiasm.

## Consequences

The Scope Boundaries decision implies:

* Polaris owns the decision lifecycle and the trust mechanisms necessary to keep it coherent;
* dependency on an external capability does not require Polaris to own that capability's broader product category;
* a feature may exist within Polaris without turning the feature category into an independent product mandate;
* supporting capabilities must remain accountable to decision value;
* supporting capabilities may be deep and polished when that materially improves the decision system;
* authoritative specialist systems should usually remain authoritative for the operational facts and responsibilities they own;
* Polaris should integrate and reconcile rather than casually duplicate external systems of record;
* decision-oriented portfolio context belongs in Polaris even when official portfolio accounting does not;
* decision-relevant market evidence belongs in Polaris even when comprehensive market-data vending does not;
* research, simulation, charting, screening, reporting, conversation, and collaboration may be in scope as supporting capabilities without defining the product;
* decision governance is core while broad regulatory operations require separate justification;
* small-team collaboration is compatible with the design center while enterprise organization machinery is not assumed;
* generic internal infrastructure does not justify a general-purpose workflow product;
* expansion that creates a new primary user job, authority domain, latency regime, regulatory burden, or operational contract should be presumed outside scope until explicitly reconsidered.

## Relationship to later Product Definition work

This Scope Boundaries decision constrains the remaining Product Definition work:

* **Differentiation** should identify what makes Polaris unusually valuable inside the decision layer rather than comparing feature catalogs across adjacent specialist products.
* **Core Capabilities** should describe the capability set required to fulfill Ring 1 and the minimum supporting capabilities necessary to deliver the intended experience.
* **Product Principles** should preserve responsibility-based scope, integration over duplicated ownership, and the rule that supporting capabilities remain subordinate to decision value.
