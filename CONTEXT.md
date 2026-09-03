# Polaris Domain Glossary

## Portfolio

A **Portfolio** is a durable, explicitly identified investment responsibility under which an economically bounded share of capital and Positions is managed together through time under an investment mandate and investment authority regime.

Portfolio identity represents the continuing investment responsibility rather than its current contents. Changes to holdings, capital, portfolio state, account, broker, strategy, manager, or mandate version do not by themselves create a new Portfolio. Portfolio closure, split, merge, or fundamental reconstitution requires explicit identity semantics rather than being inferred from mutable state.

## Portfolio Boundary

A **Portfolio Boundary** is the time-specific attribution of capital, Positions, and economic obligations to a Portfolio that determines the economic state for which that Portfolio is responsible.

The same economic interest cannot be fully attributed to more than one Portfolio at the same time, although an economic interest may be partitioned between Portfolios. Account boundaries do not inherently define Portfolio Boundaries: one Portfolio may span more than one account, and one account may contain economic interests attributed to more than one Portfolio.

Portfolio attribution is historical fact. A later boundary change must not rewrite which Portfolio an economic interest belonged to at an earlier time.

## Financial Instrument

A **Financial Instrument** is an identifiable tradable financial security or contract in which a Position may be established.

Financial Instrument identity is not merely a ticker, display symbol, or product-family name. AAPL common stock, SPY ETF shares, and a specific ES futures contract are Financial Instruments; an index, macroeconomic series, or other analytical reference is not a Financial Instrument merely because Polaris reasons about it.

Ordinary Portfolio cash is capital or liquidity rather than automatically a Financial Instrument. A security or contract used as a cash equivalent, such as a money-market fund share or Treasury bill, may itself be a Financial Instrument.

## Position

A **Position** is a Portfolio-scoped current economic holding or obligation in a Financial Instrument, characterized by its quantity and **Position Direction**.

**Position Direction** describes the Portfolio's relationship to the Financial Instrument as **Long** or **Short**. Position Direction is distinct from an action or order side such as Buy or Sell, and it does not by itself determine the direction of the economic Exposure produced by the Position.

Externally reported account holdings are operational source facts rather than automatically being Polaris Positions. Where an account contains economic interests attributable to more than one Portfolio, those interests may be partitioned into separate Portfolio-scoped Positions without duplicating the same economic interest.

## Exposure

**Exposure** is a time-specific economic sensitivity or concentration attributable to a Portfolio with respect to a Financial Instrument or another economically relevant dimension, arising from its Positions and other attributable economic interests or obligations.

One Position may create several Exposures, and several Positions may contribute to one Exposure. Position Direction does not by itself determine Exposure direction.

Exposure is distinct from Allocation and Risk. Allocation describes a distribution of capital; Exposure describes economic sensitivity or concentration; Risk describes possible adverse outcomes associated with the Portfolio, its Exposures, and other conditions.

## Portfolio State

**Portfolio State** is the time-specific economic condition of a Portfolio within its Portfolio Boundary, including attributable capital, Positions, obligations, valuations, Allocations, Exposures, liquidity, performance state, and other economic measures needed to describe what the Portfolio is at that time.

Account State is distinct from Portfolio State. Operational account facts may constrain or inform a Portfolio without becoming Portfolio identity or automatically becoming Portfolio State.

Externally authoritative facts and Polaris-derived Portfolio measures retain their separate provenance and authority even when represented together as part of Portfolio State.

Unqualified Portfolio State refers to an actual or historically actual state at an as-of time. A **Projected Portfolio State** is a hypothetical state expected to result from a candidate action or decision consequence and must remain distinguishable from actual Portfolio State.

## Investment Mandate

An **Investment Mandate** is the durable, temporally applicable statement of a Portfolio's investment purpose, Investment Objectives, Investment Principles, and Formal Constraints. It establishes what the Portfolio is intended to accomplish, how investment judgment should generally be guided, and which investment boundaries are explicitly authoritative.

The Investment Mandate is distinct from Portfolio identity, Portfolio State, Investment Strategy, current Risk, external operational constraints, and the Investment Authority Regime. A Portfolio may retain identity across Mandate revisions, and the Mandate version applicable to a historical decision must remain reconstructable.

A Polaris Investment Recommendation may conflict with an Investment Principle or violate a Formal Constraint. Polaris must preserve the distinction between its investment judgment, interpretive Mandate assessment, deterministic Formal Constraint results, and any authority consequence or Mandate Exception required for the Investment Recommendation to proceed.

## Investment Objective

An **Investment Objective** is a desired investment outcome that guides how success and tradeoffs should be evaluated for a Portfolio.

Investment Objectives are not deterministic compliance boundaries. An Investment Recommendation may be assessed as advancing, detracting from, or having uncertain effect on an Investment Objective, but failure to advance an Objective is not by itself a Mandate violation.

## Investment Principle

An **Investment Principle** is qualitative, context-sensitive guidance intended to shape investment judgment without defining a deterministic boundary.

Investment Principles may be interpreted for alignment, tension, or uncertainty. They are inherently defeasible: a justified departure from a Principle does not require a Mandate Exception merely because tension exists. An interpretive assessment of a Principle must not be represented as deterministic compliance.

## Formal Constraint

A **Formal Constraint** is an authoritative, machine-evaluable restriction in an Investment Mandate whose scope, measurement basis, and evaluation semantics are sufficiently explicit to determine its result without investment judgment.

A Formal Constraint need not be numerical; it may be categorical, Boolean, set-based, or quantitative. Natural-language Mandate text does not become a Formal Constraint solely because Polaris can interpret it. Formalization must be explicit and authoritative.

Only Formal Constraints may produce deterministic Mandate satisfaction or violation results. A Formal Constraint may be indeterminate at evaluation time when required authoritative facts are unavailable, stale, or insufficient without becoming interpretive itself.

## Mandate Exception

A **Mandate Exception** is an explicit, attributable, scoped authorization to permit a decision or resulting Portfolio condition despite violation of an otherwise applicable Formal Constraint, without changing the underlying Investment Mandate or the violated constraint.

A Mandate Exception does not make a violated Formal Constraint satisfied. It changes whether the scoped departure is authorized. Exceptions may arise from concrete investment circumstances and do not need to be exhaustively predefined in the Investment Mandate.

A Mandate Exception is distinct from a Mandate amendment and from a noncompliant human decision. The Investment Authority Regime determines whether a Formal Constraint is exceptionable and who, if anyone, may authorize an Exception. Polaris may identify, propose, or justify an Exception but cannot authorize one merely through its own Investment Recommendation.

## Workflow Identity

A **Workflow Identity** is the immutable identity of a registered workflow
definition: its canonical workflow name plus the deterministic fingerprint of
that definition. The fingerprint is the workflow version; it identifies a
definition revision, not an individual execution or caller-supplied label.

Workflow Identity is distinct from an execution identifier. One Workflow
Identity may have many executions, while a definition change creates a new
Workflow Identity version.

## Governed Execution Evidence

**Governed Execution Evidence** is the tier-specific durable authority and
provenance record selected for one platform-created workflow execution before
its governed evaluation. It is distinct from a Workflow Identity: one
immutable workflow definition may have many executions, each with its own
evidence-selection correlation. It is also distinct from caller-supplied
evidence or an evidence identifier, neither of which may select or authorize
a governed execution.

## Workflow Invocation

A **Workflow Invocation** is the platform-created execution of a registered
workflow definition. It is not automatically a claim-bearing Output Boundary:
its runtime provenance may be governed as Baseline evidence before execution,
while any resulting output is classified and governed independently at its
actual Output Boundary.

## Workflow Authority Facts

**Workflow Authority Facts** are the platform-owned, typed association of a
registered Workflow Identity with its Risk Authority Contract. They determine
the applicable consequence tier and governed-evidence variant for an
execution. Workflow Authority Facts are not caller metadata, an execution
identifier, or a claim about the workflow supplied by a transport.

## Investment Recommendation

An **Investment Recommendation** is an attributable, time-specific Polaris judgment within an Investment Decision that expresses Polaris's preferred economic disposition of the Decision Need for the affected Portfolio or Portfolios under the decision-time context then available.

An Investment Recommendation may prefer action, hedging, resizing, Allocation or Exposure change, deliberate hold or no-action, waiting, or another Portfolio-relevant economic disposition. It may identify one or more Proposed Actions or implementation preferences, but it is distinct from a strategy/model signal and from an Order or other broker execution instruction.

Polaris may present a human-reviewable trade setup when useful, including suggested implementation, approximate quantity, preferred price region, investment invalidation, Risk boundary, objective, or review condition. Those investment and implementation judgments do not make Polaris the authority for exact order placement, routing, working-order state, fills, stop orders, or take-profit orders.

An Investment Decision may have zero, one, or multiple Investment Recommendations through time. Each Investment Recommendation is a distinct attributable judgment; a later Investment Recommendation does not rewrite an earlier one, and a new attributable judgment may reaffirm the same economic disposition. Observation or Evidence refresh alone does not create a new Investment Recommendation.

The absence of a current Investment Recommendation is distinct from an affirmative recommendation to hold, wait, defer, or take no action. Polaris must preserve whether no recommendation has yet been formed, a recommendation was explicitly withheld, or a previously issued recommendation is no longer currently supportable.

Investment Recommendation history is durable. A recommendation may cease to be currently supportable because required Evidence becomes stale, insufficient, conflicting, erroneous, or otherwise unfit for the intended decision use without ceasing to exist historically. An older recommendation does not silently reactivate when a later recommendation becomes unsupported; renewed support requires a new attributable recommendation judgment. Any notion of a current Investment Recommendation is therefore derived from durable recommendation history and current applicability rather than implemented semantically as destructive replacement of history.

A Human Investment Decision remains distinct from every Investment Recommendation even when their economic content is identical. Where knowable, Polaris preserves which Investment Recommendation or Recommendations materially informed the human judgment and any attributable acceptance, modification, rejection, deferral response, or other relationship. A Human Investment Decision may also exist when no Investment Recommendation exists, and Polaris must not manufacture one retroactively from the human choice.

External Resolution that happens to produce a Portfolio state matching an Investment Recommendation does not establish Recommendation acceptance, a Human Investment Decision, or recommendation-driven execution. After substantive investment judgment resolution or External Resolution, prior Investment Recommendations remain historical decision basis rather than indefinitely active instructions. Deferral is different because the Decision Need remains unresolved and later Investment Recommendations may continue within the same Investment Decision when judgment resumes.

`Recommendation` is accepted shorthand for `Investment Recommendation` in existing Polaris product prose unless another narrower recommendation type is explicitly stated.

Related distinctions:

- A **Strategy Decision** is the selected typed synthesis outcome from structured strategy hypotheses and is not itself the canonical Investment Recommendation.
- A **Proposed Action** or **Action Candidate** is a concrete candidate implementation that may help achieve the economic disposition expressed by an Investment Recommendation and may later be resized, deferred, rejected, escalated, or skipped.
- A **Trade Package** is downstream packaging of Proposed Actions for execution-risk review.
- An **Order** is an execution-domain instruction describing exact market-facing action. Orders, routing, working-order state, fills, stop orders, and take-profit orders remain externally authoritative execution facts unless Polaris product scope is explicitly changed.

## Capital-Relevant Output

A **Capital-Relevant Output** is a Polaris output that could reasonably influence allocation, position sizing, entry or exit timing, hedging, risk acceptance, or portfolio exposure if a human acted on it.

Capital-Relevant Outputs include Investment Recommendations, Proposed Actions, Action Candidates, Trade Packages, risk responses that affect exposure, Strategy Decisions when exposed as guidance, and RAG, report, or tool answers that make readiness-gating claims about portfolio action or risk.

Raw market data, telemetry, observability dashboards, implementation diagnostics, contextual narrative with no action or risk implication, and internal runtime evidence not exposed as guidance are not automatically Capital-Relevant Outputs.

## Release

**Release** is the domain decision that a governed output is allowed to cross a controlled boundary after evidence, governance, and residual-risk checks pass.

## Publication

**Publication** is making an output externally visible or user-facing, such as through a report, CLI response, MCP response, API response, or rendered artifact.

## Durable Promotion

**Durable Promotion** is making an output authoritative for later platform use, such as persistence as a curated record, recommendation record, RAG-eligible source, graph projection source, audit-linked evidence, or downstream workflow input.

Persisting blocked or skipped audit state is not Durable Promotion of the output's claim; it is audit retention.

## Approval

**Approval** is an attributable governance review outcome that allows a requested action, output, or promotion to proceed if all other required checks pass.

Approval does not imply Residual-Risk Acceptance when residual risk remains. A model cannot grant Approval.

## Residual-Risk Acceptance

**Residual-Risk Acceptance** is an explicit, scoped, attributable acknowledgement that remaining identified risk is accepted for a specific subject, evidence version, review scope, residual-risk scope, action, and sink.

Residual-Risk Acceptance is distinct from Approval. A model cannot grant Residual-Risk Acceptance.

## Evidence

**Evidence** is information used to support, contradict, constrain, qualify, or reconstruct a material Polaris claim or output.

Evidence roles include:

- **Runtime Evidence**: workflow execution outputs and completed-run records that explain what happened during execution.
- **Decision Evidence**: evidence bound to claims in a decision evidence packet.
- **Supporting Evidence**: evidence cited as support for a claim.
- **Conflicting Evidence**: evidence that materially challenges a claim.
- **Reconstruction Evidence**: durable references or retained snapshots used to verify where claim support came from.
- **Contextual Evidence**: explanatory information retained for audit or narrative, but not readiness-gating by itself.

A citation, artifact, projection, or telemetry signal is not automatically Evidence until it is used in an Evidence role.

## Claim

A **Claim** is an assertion in a Polaris output that represents or explains a state of the world, portfolio condition, risk condition, rationale, expected effect, or recommended posture or action.

Claim materiality distinctions:

- A **Material Claim** is a Claim that could affect trust in a Capital-Relevant Output.
- A **Readiness-Gating Claim** is a Material Claim whose absence, unsupported state, conflict, or reconstruction failure must block Release, Publication, or Durable Promotion.
- A **Contextual Claim** is explanatory or background narrative that may be audited but does not by itself block readiness.

For example, "the portfolio is over-concentrated in semiconductors" is a Claim. "Consider trimming NVDA exposure" is both a claim-bearing Investment Recommendation or Proposed Action and a Capital-Relevant Output. Generation timestamps and similar operational metadata are usually not Material Claims.

## Curated Record

A **Curated Record** is a typed, attributable, durable platform record that has been selected and normalized for later authoritative platform use.

A Curated Record is not automatically human-approved, true, investment advice, conflict-free, RAG-indexed, graph-projected, or publishable. A record appearing in Qdrant, Neo4j, a rendered report, or a runtime dump is not Curated unless it has an owning durable platform record. Curation does not erase source lineage, materiality, or governance requirements.

## Projection

A **Projection** is a derived representation of authoritative platform records or Runtime Evidence, optimized for a particular use such as retrieval, graph traversal, presentation, search, or inspection.

A Projection is rebuildable from its source records and must not become the source of truth for the business concept it represents. A Projection may be cited or inspected, but readiness and reconstruction must point back to canonical durable records or retained snapshots where required.

Examples include Qdrant vectors, Neo4j graph nodes and relationships, report renderings, RAG chunks, read models, and search indexes.

## Source of Truth

A **Source of Truth** is the authoritative domain source for a concept or claim.

## System of Record

A **System of Record** is the durable storage boundary responsible for retaining authoritative records. In the current Polaris architecture, PostgreSQL is the System of Record for platform business state.

## Authority

An **Authority** is the domain or architectural owner allowed to decide, write, validate, or release a concept. An Authority can be a service, lifecycle, or contract rather than only a database.

For example, PostgreSQL may be the System of Record for an approval task, while the approval lifecycle authority defines the semantics for approval, contestability, residual-risk acceptance, and release.

## Strategy Hypothesis

A **Strategy Hypothesis** is a typed, evidence-bound argument for one market or portfolio perspective, including supporting evidence, contradicting evidence, assumptions, invalidation conditions, strength, confidence, directional bias, and an evidence fingerprint.

A Strategy Hypothesis is not a vote and is not the final strategy selection. Bull, Bear, and Sideways are perspectives that produce comparable Strategy Hypotheses from the same evidence context. The final Strategy Decision comes from comparing hypotheses under the synthesis policy.

## Strategy Decision

A **Strategy Decision** is the typed synthesis outcome that selects or blends portfolio posture from competing Strategy Hypotheses under evidence, market, portfolio, and risk constraints.

A Strategy Decision may express posture or regime interpretation, directional bias, confidence and uncertainty, thesis or rationale, synthesis weights, constraints, and degradation reasons.

A Strategy Decision does not by itself decide exact order placement, human or organizational Approval, Residual-Risk Acceptance, Publication, Release, broker execution, or final legal, tax, financial, investment, or trading advice. Downstream components may derive Investment Recommendations, Proposed Actions, or Trade Packages from a Strategy Decision, subject to evidence and governance rules.

## Execution Risk

**Execution Risk** is the risk introduced by attempting to carry out a Proposed Action or Trade Package, including timing, liquidity, sizing, slippage, concentration, volatility, operational, and governance risks.

In current Polaris, Execution Risk assessment is decision-support and governance over candidate actions. It is not live broker execution and does not imply an Order exists.

## Portfolio Posture

**Portfolio Posture** is a qualitative or bounded directional stance toward exposure, risk, liquidity, concentration, hedging, or rebalance intent.

## Allocation

**Allocation** is a concrete target or actual distribution of capital across assets, sectors, strategies, accounts, or risk buckets.

A Strategy Decision may express Portfolio Posture. An Investment Recommendation or Proposed Action may suggest movement toward an Allocation, but exact Allocation changes are Capital-Relevant and require applicable evidence, governance, and release handling.

## Risk

**Risk** is an identified possibility of adverse portfolio, operational, evidentiary, governance, or user-impact outcome.

Risk categories include:

- **Portfolio Risk**: risk arising from holdings, exposures, concentration, volatility, drawdown, liquidity, correlation, or market regime.
- **Execution Risk**: risk arising from attempting to carry out a Proposed Action or Trade Package.
- **Evidence Risk**: risk that a Claim or output is unsupported, conflicted, stale, unreconstructable, or based on rejected Evidence.
- **Governance Risk**: risk that an output or action crosses a boundary without required policy, review, Approval, contestability, or Residual-Risk Acceptance.
- **Residual Risk**: identified Risk that remains after automated checks, mitigations, review, or constraints.

## AI-Adjacent Output

An **AI-Adjacent Output** is an output produced by, transformed by, summarized by, routed through, or materially influenced by model, agent, RAG, evaluation, or automated decision-support behavior.

AI-Adjacent status does not by itself determine authority, truth, readiness, or risk tier. AI-Adjacent Outputs require classification by their effect, source of truth, intended sink, evidence sufficiency, external visibility, durable authority, governance impact, and capital relevance.

## Risk Authority Contract

A **Risk Authority Contract** is the canonical classification of one AI-adjacent output boundary's consequence tier, allowed effect, owner, source-of-truth category, intended sink, gate profile, and evidence or governance flags.

A Risk Authority Contract describes what an output is allowed to affect after platform classification. Model output or model-provided metadata cannot self-declare authority, production readiness, governance approval, residual-risk acceptance, or a lower risk tier.

## Risk Tier

A **Risk Tier** is a consequence classification for an AI-Adjacent Output.

Canonical Risk Tiers are:

- **Baseline**: low-consequence informational or runtime output that does not require enhanced evidence or governance controls.
- **Enhanced**: output requiring stronger evidence, readiness, or authority controls because it is externally visible, durable, capital-relevant, evidence-insufficient, non-runtime-sourced, or otherwise consequential.
- **Vigilant**: output requiring the strongest automated governance and release controls because it can affect capital, governance, execution decisions, durable authority, external visibility, or unresolved evidence sufficiency.
- **Prohibited / Outside Authority**: output whose requested effect is outside Polaris authority and must not be treated as allowed by model text, interface behavior, or local metadata.

## Policy

**Policy** answers whether an operation, output, or boundary crossing may happen under deterministic platform rules. Policy outcomes are allow or deny style decisions and do not by themselves store human governance Approval.

## Governance

**Governance** answers whether an operation, output, or boundary crossing should happen given consequence, evidence, review, contestability, residual risk, and release requirements.

Governance is separate from Policy. Automated Governance may allow, warn, deny, require approval, or skip. Human or organizational review is a governance lifecycle above automated governance, not a replacement policy engine and not model-declared readiness.

## Governed Output

A **Governed Output** is an output whose Release, Publication, Durable Promotion, or downstream use is subject to Policy, Governance, evidence readiness, review, or Residual-Risk Acceptance requirements.

Capital-Relevant Enhanced and Vigilant outputs are Governed Outputs when they are externally visible, durably authoritative, governance-impacting, or otherwise cross a controlled boundary.

## Readiness Gate

A **Readiness Gate** is a boundary check that determines whether a Claim, output, record, or projection is allowed to proceed to Release, Publication, Durable Promotion, retrieval eligibility, or downstream use.

Readiness Gates fail closed when required evidence, reconstruction, correctness, governance review, residual-risk acceptance, or source authority is missing, stale, conflicted, rejected, or malformed.

## Output Boundary

An **Output Boundary** is a point where Polaris output leaves its current internal role and becomes visible, durable, authoritative, retrievable, or available for downstream decision use.

Examples include report publication, recommendation projection, RAG answer generation, MCP/API/CLI responses, curated-record persistence, graph/vector projection, and governed-output release.

## Review Task

A **Review Task** is durable governance work created for a specific subject, evidence packet, evidence version, review scope, requested action, and intended sink when automated governance requires human or organizational review.

A Review Task is resolved only by attributable review decisions such as approval, denial, contest, requested changes, or override. Model text cannot resolve a Review Task.

## Contestability

**Contestability** is the ability for an attributable reviewer or governance process to challenge, deny, request changes to, or override an automated governance outcome without deleting or rewriting the original automated audit record.

Contestability preserves the history of the automated outcome, review rationale, evidence version, and resulting task status.

## Completed-Run Archive

A **Completed-Run Archive** is the durable runtime archive of a finished workflow execution, including runtime context and node outputs needed for replay, inspection, audit, and reconstruction.

A Completed-Run Archive is broad Runtime Evidence. It is not automatically a Curated Record, RAG-eligible source, Projection, Investment Recommendation, Approval, or Source of Truth for every business concept it contains.

## Curation

**Curation** is the deliberate selection and normalization of workflow or platform output into a Curated Record with typed meaning, deterministic identity, temporal meaning, lineage, quality checks, and authoritative ownership.

Curation is narrower than archival and precedes selective embedding or graph projection.

## Embedding Eligibility

**Embedding Eligibility** is the decision that a Curated Record is useful and safe enough to become retrieval context for RAG.

Embedding Eligibility does not make a record true, approved, capital-actionable, or release-ready. It only allows the record to be represented in retrieval projections under the applicable source, lineage, evidence, and governance rules.

## RAG Answer

A **RAG Answer** is a retrieval-grounded answer assembled from retrieved or cited context and generated claim data.

A RAG Answer is presentation output. Its rendered text is not the Claim source of truth and not an authority for Approval, Residual-Risk Acceptance, or durable decision support unless the underlying claims and evidence pass the applicable decision-evidence and governance rules.

## Application Service

An **Application Service** is a platform boundary that owns a use-case operation, coordinates typed domain contracts, applies policy or governance where applicable, and delegates external access to providers or clients.

Application Services are the preferred domain-facing surface for interfaces such as CLI, MCP, API, reports, workflows, and future transports.

## Provider

A **Provider** is a typed boundary that normalizes a class of external or simulated capability for Application Services. Providers hide vendor-specific transport, SDK, authentication, retry, and response-shape concerns from intelligence components and workflow nodes.

## Client

A **Client** is a vendor-specific or transport-specific adapter used beneath a Provider to communicate with an external system or local service.

Clients do not own Polaris domain semantics. Provider normalization is required before external data becomes typed platform input.

## Backtest

A **Backtest** is a deterministic replay or simulation of Polaris workflow behavior under historical, fixed, or simulated inputs through the canonical runtime.

A Backtest is not a separate strategy runtime and does not change live-versus-simulated behavior inside the runtime itself. Backtest outputs can become Evidence or Curated Records only through the same applicable evidence, curation, and governance rules as other workflow outputs.

## Simulation

A **Simulation** is a controlled substitute for live external conditions, provider responses, market data, portfolio state, or scenario inputs used to evaluate behavior deterministically.

Simulation does not imply that resulting outputs are less subject to lineage, evidence, curation, or governance requirements.

## Confidence

**Confidence** is a unit-interval estimate of certainty, reliability, strength, completeness, readiness, alignment, or quality within its declared score family.

Confidence must not be confused with probability of profit, governance Approval, truth, or Residual-Risk Acceptance.

## Directional Bias

**Directional Bias** is a signed market or portfolio posture signal where negative values indicate bearish, defensive, risk-off, short, or unfavorable posture and positive values indicate bullish, aggressive, risk-on, long, or favorable posture.

Directional Bias is not a unit risk score and must not be interpreted as Approval, Allocation, or an Order.

## Risk Score

A **Risk Score** is a unit-interval risk or intensity value where higher means more risk, more intensity, or more defensive pressure unless an explicit score family says otherwise.

Risk Scores are not signed directional values. Favorable or risk-on conditions should be represented by lower risk, higher stability, a separate regime label, an Investment Recommendation, or an explicit signed Directional Bias.

## Attention

**Attention** is the Polaris domain responsibility that evaluates new observations, user requests, Portfolio changes, scheduled reviews, prior decision conditions, and other available investment context to determine whether deliberate investment judgment may now be warranted.

Attention may use deterministic criteria or interpretive investment assessment. A matched criterion, notable observation, or interpretive concern does not by itself create a Decision Need. Attention does not imply continuous surveillance of the financial world; what Polaris can evaluate is bounded by the information and investment context it is configured or otherwise authorized to observe.

Attention has no single global frequency. Temporal observation semantics may differ by observed subject, source, Portfolio context, user configuration, and current decision use. Newly available or newly due information may cause Attention to evaluate without requiring all Polaris state to refresh in lockstep. Observation updates may occur frequently while Investment Decision state changes only when the information materially affects decision work.

Polaris decision context is temporally composed rather than globally refreshed. Facts and derived measures retain their own as-of times, provenance, and freshness; representing them together does not imply that every component was observed or recomputed simultaneously.

## Observation Cadence

**Observation Cadence** is the normal temporal pattern by which information about an observed subject or condition is obtained or reconsidered for Attention.

An Observation Cadence may be event-driven, periodic, scheduled, on-demand, or condition-driven. It may differ by source, observed subject, Portfolio context, configured investment use, and current decision context.

Observation Cadence is distinct from Freshness Requirement. A cadence describes when information is normally obtained or reconsidered; it does not guarantee that the resulting information is current enough for every Investment Decision.

## Freshness Requirement

A **Freshness Requirement** is the maximum acceptable age or other temporal adequacy required of information for a particular investment use.

An active Investment Decision may require fresher information than the normal Observation Cadence without permanently changing that cadence. If available information cannot satisfy the applicable Freshness Requirement, Polaris must preserve that insufficiency rather than treating stale information as current.

## Decision Need

A **Decision Need** is an explicit determination that an unresolved Portfolio-relevant investment choice now warrants deliberate judgment.

A Decision Need records why decision work is required and is distinct from the observation, request, Evidence, Portfolio change, review condition, or other input that caused Attention to evaluate the matter. Whether a Decision Need automatically initiates an Investment Decision or instead requires human confirmation is a separate initiation-authority question.

## Decision Scope

**Decision Scope** identifies the one or more Portfolios whose investment state, capital consequences, and applicable Investment Mandates are directly implicated by an Investment Decision.

A Portfolio used only as Evidence or analytical context is not automatically part of Decision Scope. Each scoped Portfolio retains its own Portfolio State, Investment Mandate, Formal Constraints, Risk, and applicable Mandate Exceptions; a multi-Portfolio Investment Decision does not create an implicit synthetic Mandate.

Decision Scope may be unresolved while decision work is being initiated, but a final Capital-Relevant Investment Recommendation or Human Investment Decision must not silently assume Portfolio applicability that has not been established.

## Decision Subject

**Decision Subject** identifies the investment matter whose disposition is being judged within an Investment Decision.

A Decision Subject may concern an existing Position, establishing exposure through a Financial Instrument, an Exposure, Allocation, Portfolio Posture, or another coherent investment matter. It may be composite when its elements form one mutually dependent investment judgment; independently resolvable matters should normally be separate Investment Decisions.

Decision Subject is distinct from Decision Scope, Evidence, the thing analyzed, a Proposed Action, and the Financial Instrument or other means ultimately used to implement the decision. The same Decision Subject may recur in separate Investment Decisions through time and therefore does not by itself establish Investment Decision identity.

## Investment Decision

An **Investment Decision** is a durable, identifiable unit of Portfolio-relevant investment judgment created to resolve a Decision Need about a Decision Subject whose potential capital consequences are evaluated within one or more Portfolio scopes.

Investment Decision identity is explicit and durable. It is not derived from Decision Subject, Decision Scope, Evidence, Investment Recommendation, workflow execution, current Portfolio State, or any other mutable decision-time fact. Identity is preserved while work continues to resolve the same coherent unresolved investment choice, even when Evidence, Portfolio State, Risk, reasoning, Mandate assessment, Investment Recommendation, Decision Subject, or Decision Scope changes or is refined.

Once the investment judgment has been substantively resolved, a later renewed Decision Need creates a new causally linked Investment Decision rather than reopening and rewriting the resolved decision. Resolution of the investment judgment is a milestone within the Investment Decision lifecycle rather than necessarily the end of that lifecycle; action continuity, reconciliation, Outcome, and Evaluation may continue under the same decision identity.

An Investment Decision may exist before its Decision Scope is fully resolved, but final Capital-Relevant Investment Recommendation or Human Investment Decision formation requires established Portfolio applicability. Portfolio-independent investment analysis or assessment may inform a future Investment Decision without itself constituting one.

An Investment Decision may concern one or several Portfolios and may result in action, modification, rejection, Deferral, deliberate inaction, or External Resolution. Deliberate hold or no-action can substantively resolve the investment choice; Deferral leaves the underlying Decision Need unresolved; External Resolution eliminates the Decision Need because changed circumstances remove the choice before a Human Investment Decision substantively resolves it.

An Investment Decision is distinct from workflow execution, an Investment Recommendation, governance Approval, and the attributable Human Investment Decision made within its lifecycle.

## Human Investment Decision

A **Human Investment Decision** is the attributable human judgment within an Investment Decision that selects, modifies, rejects, defers, or otherwise disposes of the Portfolio-relevant investment choice.

A Human Investment Decision may or may not substantively resolve the underlying Investment Decision. Deferral, or rejection accompanied by a request for further judgment, records attributable human judgment while leaving the Decision Need unresolved; deliberate hold or another substantive choice may resolve it.

A Human Investment Decision is distinct from Polaris's Investment Recommendation, automated Policy or Governance outcomes, Approval, Residual-Risk Acceptance, and Mandate Exception authorization. Human judgment does not retroactively rewrite the Investment Recommendation, Mandate, Formal Constraint results, or other decision-time facts that preceded it.

## Deferral

A **Deferral** is an attributable Human Investment Decision that postpones substantive resolution of an Investment Decision while leaving its underlying Decision Need unresolved.

A Deferral may identify information, a time, an event, or another condition that must become available or due before judgment resumes. When that awaited condition occurs, Attention may resume the same unresolved Investment Decision rather than creating a new one solely because time passed or new Evidence became available.

Deferral is distinct from deliberate hold or no-action. Both may produce no immediate Portfolio change, but deliberate inaction can be the substantive answer to the investment choice while Deferral means that answer has not yet been made.

## Review Condition

A **Review Condition** is an explicit condition associated with a substantively resolved Investment Decision that requests reconsideration if the condition becomes true or otherwise due.

A Review Condition does not reopen the resolved Investment Decision and does not automatically create a new one. Its occurrence causes Attention to evaluate whether a renewed Decision Need exists. If renewed judgment is warranted, Polaris creates a new causally linked Investment Decision while preserving the earlier decision's historical resolution.

A condition awaited by a deferred unresolved Investment Decision is semantically different: satisfying that condition may resume the same unresolved decision.

## Supersession

**Supersession** is an explicit causal relationship in which one Investment Decision displaces an earlier Investment Decision's continuing applicability or operative investment basis without deleting or rewriting either decision.

Supersession may apply whether the earlier decision was unresolved or substantively resolved. It does not undo historical resolution, Investment Recommendation history, Human Investment Decisions, or other decision-time facts; it records that another Investment Decision has become the relevant basis going forward.

## External Resolution

**External Resolution** occurs when circumstances outside an unresolved Investment Decision eliminate the investment choice that created its Decision Need before a Human Investment Decision substantively resolves that choice. An Investment Decision in this disposition is **Externally Resolved**.

External Resolution eliminates the need for further judgment; it does not mean that an investment judgment was made, that Polaris's Investment Recommendation was followed, or that a preferred Portfolio outcome occurred. Polaris must not infer a Human Investment Decision from the changed external circumstances alone.

An external change that only alters Evidence, Portfolio State, available alternatives, or expected consequences does not constitute External Resolution while the same coherent Decision Need remains. External Resolution is distinct from Deferral, deliberate hold or no-action, Supersession, and cancellation or withdrawal of decision work while the underlying investment choice still exists.

`External` means outside the unresolved investment judgment itself, not necessarily outside Polaris or outside the Portfolio domain. The cause of External Resolution must remain attributable so later reconstruction can distinguish changed circumstances from Polaris Investment Recommendations and Human Investment Decisions.