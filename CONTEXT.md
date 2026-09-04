# Polaris Domain Glossary

## Portfolio

A **Portfolio** is a durable, explicitly identified investment responsibility under which an economically bounded share of capital and Positions is managed together through time under an Investment Mandate and Investment Authority Regime.

Portfolio identity represents the continuing investment responsibility rather than its current contents. Changes to holdings, capital, Portfolio State, account, broker, Investment Strategy, manager, or Mandate version do not by themselves create a new Portfolio. Portfolio closure, split, merge, or fundamental reconstitution requires explicit identity semantics rather than being inferred from mutable state.

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

Exposure is distinct from Allocation and Portfolio Risk. Allocation describes a distribution of capital; Exposure describes economic sensitivity or concentration; Portfolio Risk describes possible adverse economic outcomes or objective shortfall associated with the Portfolio, its Exposures, market conditions, and other investment-relevant conditions.

## Portfolio State

**Portfolio State** is the time-specific economic condition of a Portfolio within its Portfolio Boundary, including attributable capital, Positions, obligations, valuations, Allocations, Exposures, liquidity, performance state, and other economic measures needed to describe what the Portfolio is at that time.

Account State is distinct from Portfolio State. Operational account facts may constrain or inform a Portfolio without becoming Portfolio identity or automatically becoming Portfolio State.

Externally authoritative facts and Polaris-derived Portfolio measures retain their separate provenance and authority even when represented together as part of Portfolio State.

Unqualified Portfolio State refers to an actual or historically actual state at an as-of time. A **Projected Portfolio State** is an attributable hypothetical Portfolio condition represented as expected or decision-relevant under a stated Investment Scenario, candidate disposition, or decision alternative. A raw simulated state does not automatically become a Projected Portfolio State.

## Investment Mandate

An **Investment Mandate** is the durable, temporally applicable statement of a Portfolio's investment purpose, Investment Objectives, Investment Principles, and Formal Constraints. It establishes what the Portfolio is intended to accomplish, how investment judgment should generally be guided, and which investment boundaries are explicitly authoritative.

The Investment Mandate is distinct from Portfolio identity, Portfolio State, Investment Strategy, current Portfolio Risk, external operational constraints, and the Investment Authority Regime. A Portfolio may retain identity across Mandate revisions, and the Mandate version applicable to a historical decision must remain reconstructable.

A Polaris Investment Recommendation may conflict with an Investment Principle or violate a Formal Constraint. Polaris must preserve the distinction between its investment judgment, interpretive Mandate assessment, deterministic Formal Constraint results, and any authority consequence or Mandate Exception required for the Investment Recommendation to proceed.

## Investment Objective

An **Investment Objective** is a desired investment outcome that guides how success and tradeoffs should be evaluated for a Portfolio.

Investment Objectives are not deterministic compliance boundaries. An Investment Recommendation may be assessed as advancing, detracting from, or having uncertain effect on an Investment Objective, but failure to advance an Objective is not by itself a Mandate violation.

A Benchmark may be incorporated into an Investment Objective, such as an objective to outperform a specified reference, without the Benchmark becoming the Objective itself.

## Investment Principle

An **Investment Principle** is qualitative, context-sensitive guidance intended to shape investment judgment without defining a deterministic boundary.

Investment Principles may be interpreted for alignment, tension, or uncertainty. They are inherently defeasible: a justified departure from a Principle does not require a Mandate Exception merely because tension exists. An interpretive assessment of a Principle must not be represented as deterministic compliance.

## Formal Constraint

A **Formal Constraint** is an authoritative, machine-evaluable restriction in an Investment Mandate whose scope, measurement basis, and evaluation semantics are sufficiently explicit to determine its result without investment judgment.

A Formal Constraint need not be numerical; it may be categorical, Boolean, set-based, quantitative, or expressed relative to an explicitly specified Benchmark or qualified Risk Score. Natural-language Mandate text does not become a Formal Constraint solely because Polaris can interpret it. Formalization must be explicit and authoritative.

Only Formal Constraints may produce deterministic Mandate satisfaction or violation results. A Formal Constraint may be indeterminate at evaluation time when required authoritative facts or required measurements are unavailable, stale, or insufficient without becoming interpretive itself.

## Mandate Exception

A **Mandate Exception** is an explicit, attributable, scoped authorization to permit a decision or resulting Portfolio condition despite violation of an otherwise applicable Formal Constraint, without changing the underlying Investment Mandate or the violated constraint.

A Mandate Exception does not make a violated Formal Constraint satisfied. It changes whether the scoped departure is authorized. Exceptions may arise from concrete investment circumstances and do not need to be exhaustively predefined in the Investment Mandate.

A Mandate Exception is distinct from a Mandate amendment and from a noncompliant human decision. The Investment Authority Regime determines whether a Formal Constraint is exceptionable and who, if anyone, may authorize an Exception. Polaris may identify, propose, or justify an Exception but cannot authorize one merely through its own Investment Recommendation.

## Investment Authority Regime

An **Investment Authority Regime** is the temporally applicable structure of authority assignments, scopes, limits, and conditions that determines which attributable actors or processes may exercise particular investment-authority powers for a Portfolio or Investment Decision.

Investment authority is power-specific. Authority to make a Human Investment Decision, grant Approval, authorize a Mandate Exception, accept Governed Residual Risk, or exercise execution authority must not be inferred from possession of another authority. Actor Attribution establishes who performed an act; it does not by itself establish that the actor possessed the authority required for that act.

A multi-Portfolio Investment Decision preserves the applicable authority regime and authority requirements of each Portfolio unless an explicitly authoritative cross-Portfolio regime establishes otherwise. Historical reconstruction must preserve the authority regime and material authority facts that actually applied when a judgment or authority act occurred.

## Workflow Identity

> **Legacy platform/runtime vocabulary pending re-parenting.** This entry is retained temporarily so valid runtime behavior is not deleted during canonical domain serialization; it is not canonical investment-domain vocabulary.

A **Workflow Identity** is the immutable identity of a registered workflow definition: its canonical workflow name plus the deterministic fingerprint of that definition. The fingerprint is the workflow version; it identifies a definition revision, not an individual execution or caller-supplied label.

Workflow Identity is distinct from an execution identifier. One Workflow Identity may have many executions, while a definition change creates a new Workflow Identity version.

## Governed Execution Evidence

> **Legacy platform/runtime vocabulary pending re-parenting.**

**Governed Execution Evidence** is the tier-specific durable authority and provenance record selected for one platform-created workflow execution before its governed evaluation. It is distinct from a Workflow Identity: one immutable workflow definition may have many executions, each with its own evidence-selection correlation. It is also distinct from caller-supplied evidence or an evidence identifier, neither of which may select or authorize a governed execution.

## Workflow Invocation

> **Legacy platform/runtime vocabulary pending re-parenting.**

A **Workflow Invocation** is the platform-created execution of a registered workflow definition. It is not automatically a claim-bearing Output Boundary: its runtime provenance may be governed as Baseline evidence before execution, while any resulting output is classified and governed independently at its actual Output Boundary.

## Workflow Authority Facts

> **Legacy platform/runtime vocabulary pending re-parenting.**

**Workflow Authority Facts** are the platform-owned, typed association of a registered Workflow Identity with its Risk Authority Contract. They determine the applicable consequence tier and governed-evidence variant for an execution. Workflow Authority Facts are not caller metadata, an execution identifier, or a claim about the workflow supplied by a transport.

## Investment Recommendation

An **Investment Recommendation** is an attributable, time-specific Polaris judgment within an Investment Decision that expresses Polaris's preferred economic disposition of the Decision Need for the affected Portfolio or Portfolios as formed within the applicable Decision Context using the information available to that judgment.

An Investment Recommendation may prefer action, hedging, resizing, Allocation or Exposure change, deliberate hold or no-action, waiting, or another Portfolio-relevant economic disposition. It may rank, prefer, combine, modify, or synthesize beyond Decision Alternatives previously compared and may identify zero, one, or multiple Proposed Actions or implementation preferences, but it is distinct from an Investment View, Investment Signal, Decision Alternative, and from an Order or other broker execution instruction.

Polaris may present a human-reviewable trade setup when useful, including suggested implementation, approximate quantity, preferred price region, investment invalidation, Portfolio Risk boundary, objective, or Review Condition. Those investment and implementation judgments do not make Polaris the authority for exact order placement, routing, working-order state, fills, stop orders, or take-profit orders. Lowercase `trade package` may remain noncanonical product/UX shorthand for such a review representation, but it has no independent investment-domain identity or lifecycle.

An Investment Decision may have zero, one, or multiple Investment Recommendations through time. Each Investment Recommendation is a distinct attributable judgment; a later Investment Recommendation does not rewrite an earlier one, and a new attributable judgment may reaffirm the same economic disposition. Observation or Evidence refresh alone does not create a new Investment Recommendation.

The absence of a current Investment Recommendation is distinct from an affirmative recommendation to hold, wait, defer, or take no action. Polaris must preserve whether no recommendation has yet been formed, a recommendation was explicitly withheld, or a previously issued recommendation is no longer currently supportable.

Investment Recommendation history is durable. A recommendation may cease to be currently supportable because required Evidence becomes stale, insufficient, conflicting, erroneous, or otherwise unfit for the intended decision use without ceasing to exist historically. An older recommendation does not silently reactivate when a later recommendation becomes unsupported; renewed support requires a new attributable recommendation judgment. Any notion of a current Investment Recommendation is therefore derived from durable recommendation history and current applicability rather than implemented semantically as destructive replacement of history.

A Human Investment Decision remains distinct from every Investment Recommendation even when their economic content is identical. Where knowable, Polaris preserves which Investment Recommendation or Recommendations materially informed the human judgment and any attributable acceptance, modification, rejection, Deferral response, or other relationship. A Human Investment Decision may also exist when no Investment Recommendation exists, and Polaris must not manufacture one retroactively from the human choice.

External Resolution that happens to produce a Portfolio State matching an Investment Recommendation does not establish Recommendation acceptance, a Human Investment Decision, or recommendation-driven execution. After substantive investment judgment resolution or External Resolution, prior Investment Recommendations remain historical decision basis rather than indefinitely active instructions. Deferral is different because the Decision Need remains unresolved and later Investment Recommendations may continue within the same Investment Decision when judgment resumes.

`Recommendation` is accepted shorthand for `Investment Recommendation` in existing Polaris product prose unless another narrower recommendation type is explicitly stated.

## Decision Alternative

A **Decision Alternative** is an explicitly represented coherent candidate investment disposition of an unresolved Decision Need, including substantive resolution or deliberate Deferral where applicable, considered for comparison within an Investment Decision.

Decision Alternative is scoped to the Investment Decision and Decision Need whose choice it helps represent. It may express increase, reduction, entry, exit, hold/no-action, waiting, Deferral, resizing, rebalancing, hedging, or another coherent candidate disposition and may require zero, one, or multiple Proposed Actions.

Decision Alternative is distinct from Proposed Action, Portfolio Posture, Investment Recommendation, Human Investment Decision, Action Intent, and Order. When one concrete action completely expresses the candidate disposition, one representation may legitimately carry both Decision Alternative and Proposed Action roles without collapsing their meanings.

Decision Alternatives need not be mutually exclusive or collectively exhaustive. A Decision Alternative may be economically meaningful yet violate a Formal Constraint or otherwise lack Admissibility; analytical consideration does not grant permission. Decision Alternatives that materially shape an Investment Recommendation or Human Investment Decision remain reconstructable, while transient brainstorming alternatives need not become durable first-class records.

## Proposed Action

A **Proposed Action** is an attributable concrete candidate implementation considered within an Investment Decision for producing a possible Portfolio consequence.

Proposed Action semantics follow candidate role rather than authorship. A Proposed Action may originate from Polaris or a human, may exist before, alongside, or without an Investment Recommendation, and may be selected, modified, combined, rejected, deferred, escalated, or skipped without becoming an Action Intent.

A Proposed Action is distinct from the candidate disposition represented by a Decision Alternative, the economic disposition expressed by an Investment Recommendation, the attributable Human Investment Decision, the post-human Action Intent, and any externally authoritative Order or execution fact. Exact human selection of a Proposed Action does not collapse those concepts into one fact.

Where knowable and material, Polaris preserves which Proposed Actions informed a Human Investment Decision or resulting Action Intent without assuming one-to-one cardinality. `Action Candidate` is accepted shorthand for `Proposed Action` in existing Polaris prose unless another narrower candidate type is explicitly stated.

## Capital-Relevant Output

A **Capital-Relevant Output** is a Polaris output that could reasonably influence Allocation, Position sizing, entry or exit timing, hedging, Governed Residual Risk acceptance, or Portfolio Exposure if a human acted on it.

Capital-Relevant Outputs include Investment Recommendations, Proposed Actions, Decision Alternatives or Investment Views when exposed as guidance, Portfolio Risk responses that affect Exposure, and RAG, report, or tool answers that make readiness-gating claims about Portfolio action or Risk. A noncanonical trade-package representation is capital-relevant only because of the claims and judgments it contains, not because package identity itself carries domain meaning.

Raw market data, telemetry, observability dashboards, implementation diagnostics, contextual narrative with no action or Risk implication, and internal runtime evidence not exposed as guidance are not automatically Capital-Relevant Outputs.

## Admissibility

**Admissibility** is the time-specific, subject-specific, and boundary-specific authority status describing whether a governed subject is eligible for a specified consequential use under the applicable Evidence, Policy, Mandate, Portfolio Risk, Governance, and authority conditions.

Admissibility is not a global property of an output, Investment Recommendation, Proposed Action, Human Investment Decision, or other governed subject. The same subject may be inadmissible for one consequential use while remaining legitimately visible for audit, challenge, historical reconstruction, or Decision Evaluation.

Admissibility is distinct from Approval and from Human Investment Decision. Approval is an attributable authority act that may be one condition relevant to Admissibility; Human Investment Decision is the attributable human investment judgment. Insufficient authority or readiness information must remain unresolved rather than being silently converted into affirmative permission or prohibition.

Bare governed-output `Release` is retired as canonical Polaris domain vocabulary. Use Admissibility for authority status, Approval or the applicable specific authority fact for permission, and Publication or Durable Promotion for actual Polaris output transitions. Ordinary software-release terminology is unaffected.

## Publication

**Publication** is making an output externally visible or user-facing, such as through a report, CLI response, MCP response, API response, or rendered artifact.

## Durable Promotion

**Durable Promotion** is making an output authoritative for later platform use, such as persistence as a curated record, recommendation record, RAG-eligible source, graph projection source, audit-linked evidence, or downstream workflow input.

Persisting blocked or skipped audit state is not Durable Promotion of the output's claim; it is audit retention.

## Approval

**Approval** is an attributable positive authority decision by an actor or process authorized for the applicable boundary that permits a specific governed subject to advance within a defined scope and under stated conditions, subject to independent requirements that the Approval does not itself satisfy.

Approval is subject- and scope-specific. Approval of one Investment Recommendation, Proposed Action, quantity, Portfolio scope, or governed consequence does not automatically transfer to a materially modified one. Approval does not compel human acceptance, imply Residual-Risk Acceptance, cure a missing Mandate Exception, make stale Evidence fresh, or otherwise satisfy an independent authority condition outside its scope. A model cannot grant Approval merely through model output.

## Authority Denial

An **Authority Denial** is an attributable negative authority decision by an actor or process authorized for the applicable boundary that a specific governed subject may not advance within the defined scope and stated reasons.

Authority Denial is distinct from deterministic Policy denial, an Admissibility status, and a Human Investment Decision rejecting an Investment Recommendation. Similar practical outcomes must not erase the authority source or causal meaning of the negative decision.

## Governed Residual Risk

**Governed Residual Risk** is an identified underlying Risk that remains materially relevant to a governed subject or consequential use after the applicable checks, mitigations, constraints, and review have been applied.

Governed Residual Risk is a governance-relative status or relationship of the underlying Risk rather than a new economic, evidentiary, operational, or implementation Risk species. Residual status does not imply that the remaining Risk is small, harmless, or acceptable.

Bare `Residual Risk` is not used for Polaris governance semantics because conventional investment practice may use residual risk for idiosyncratic, unexplained, or factor-residual Portfolio Risk.

## Residual-Risk Acceptance

**Residual-Risk Acceptance** is an explicit, attributable, scoped authority decision accepting specified Governed Residual Risk for a governed subject or consequential use when the applicable Investment Authority Regime permits advancement conditional on that acceptance.

Residual-Risk Acceptance preserves the existence of the accepted underlying Risk; acceptance does not mean the Risk disappeared or was determined harmless. It satisfies only the governed residual-risk condition it is authorized to address and does not by itself cure stale or insufficient Evidence, a Policy denial, a missing Mandate Exception, a missing required Approval, or another independent authority blocker. A materially changed Risk, subject, scope, or consequential use does not silently inherit a prior acceptance. Residual-Risk Acceptance is distinct from Approval. A model cannot grant Residual-Risk Acceptance merely through model output.

## Actor Attribution

**Actor Attribution** is the relationship identifying who actually formed, authored, or performed a material attributable domain act.

Actor Attribution may apply to material judgments, decisions, authority acts, and other domain acts for which performer or authorship matters. The attributable actor is a domain-recognized originator such as a human, collective or organization, Polaris, or an external originator whose output is itself preserved as that actor's judgment or act.

Actor Attribution is distinct from provenance, Evidence-source attribution, authority, Approval, correctness, and truth. Internal models, tools, retrieval steps, workflow nodes, calculators, prompts, providers, and other implementation components do not become attributable actors merely because they contributed to a Polaris-owned domain act. A canonical Polaris-owned Investment Recommendation is Actor-attributed to Polaris; its model, provider, prompt, workflow, and tool identities remain provenance.

Storage, rendering, formatting, transmission, or faithful representation by Polaris does not transfer Actor Attribution from the human or external actor who actually formed the underlying judgment. Material Polaris synthesis or transformation that forms a substantively new judgment receives its own Polaris Actor Attribution. Requesting, scheduling, configuring, prompting, reviewing, challenging, or supplying Evidence does not by itself establish joint Actor Attribution.

A Human Investment Decision remains separately human-attributed from the Polaris Investment Recommendation that informed it. Joint or collective Actor Attribution is valid only when one domain act was genuinely formed or performed jointly. Unknown, ambiguous, or disputed attribution remains so rather than being fabricated from likely role, credentials, session identity, permissions, or organizational responsibility. Later attribution correction changes the currently supported understanding of who performed the historical act without rewriting the act itself; material earlier assertions or disputes remain reconstructable where required by Durable Decision Memory.

`Performance Attribution`, `Return Attribution`, and `Risk Attribution` retain their conventional investment meanings and are distinct from Actor Attribution.

## Evidence

**Evidence** is information used to support, contradict, constrain, qualify, or reconstruct a material Polaris claim or output.

Evidence roles include:

- **Runtime Evidence**: workflow execution outputs and completed-run records that explain what happened during execution.
- **Decision Evidence**: evidence bound to claims in a decision evidence packet.
- **Supporting Evidence**: evidence cited as support for a claim.
- **Conflicting Evidence**: evidence that materially challenges a claim.
- **Reconstruction Evidence**: durable references or retained snapshots used to verify where claim support came from.
- **Contextual Evidence**: explanatory information retained for audit or narrative, but not readiness-gating by itself.

A citation, artifact, architectural projection, telemetry signal, Investment Signal, Backtest result, Investment Simulation result, Risk Score, or other information is not automatically Evidence until it is materially used in an Evidence role.

## Claim

A **Claim** is an assertion in a Polaris output that represents or explains a state of the world, Portfolio condition, Risk condition, rationale, expected effect, or recommended posture or action.

Claim materiality distinctions:

- A **Material Claim** is a Claim that could affect trust in a Capital-Relevant Output.
- A **Readiness-Gating Claim** is a Material Claim whose absence, unsupported state, conflict, or reconstruction failure must block Admissibility for the consequential use, Publication, or Durable Promotion.
- A **Contextual Claim** is explanatory or background narrative that may be audited but does not by itself block readiness.

For example, "the Portfolio is over-concentrated in semiconductors" is a Claim. "Consider trimming NVDA Exposure" is both a claim-bearing Investment Recommendation or Proposed Action and a Capital-Relevant Output. Generation timestamps and similar operational metadata are usually not Material Claims.

## Curated Record

> **Legacy platform/runtime vocabulary pending re-parenting.**

A **Curated Record** is a typed, attributable, durable platform record that has been selected and normalized for later authoritative platform use.

A Curated Record is not automatically human-approved, true, investment advice, conflict-free, RAG-indexed, graph-projected, or publishable. A record appearing in Qdrant, Neo4j, a rendered report, or a runtime dump is not Curated unless it has an owning durable platform record. Curation does not erase source lineage, materiality, or governance requirements.

## Projection

> **Legacy architecture vocabulary pending re-parenting. Bare `Projection` is not canonical investment-domain vocabulary.** The investment domain uses explicit terms such as Projected Portfolio State and Projected Portfolio Consequence. The architecture meaning below is retained temporarily so valid behavior is not deleted before re-parenting.

A **Projection** in the legacy architecture sense is a derived representation of authoritative platform records or Runtime Evidence, optimized for a particular use such as retrieval, graph traversal, presentation, search, or inspection.

An architecture Projection is rebuildable from its source records and must not become the source of truth for the business concept it represents. Rebuilding, indexing, rendering, migrating, or otherwise changing such a derived representation does not change the identity, authority, truth, temporal meaning, or historical status of the investment-domain facts it represents.

Examples include Qdrant vectors, Neo4j graph nodes and relationships, report renderings, RAG chunks, read models, and search indexes. The eventual qualified architecture replacement name is deferred to the architecture/runtime reconciliation pass.

## Source of Truth

> **Legacy platform/architecture vocabulary pending re-parenting.**

A **Source of Truth** is the authoritative domain source for a concept or claim.

## System of Record

> **Legacy architecture vocabulary pending re-parenting.**

A **System of Record** is the durable storage boundary responsible for retaining authoritative records. In the current Polaris architecture, PostgreSQL is the System of Record for platform business state.

## Authority

> **Legacy mixed domain/architecture vocabulary pending re-parenting.** Canonical investment authority semantics are expressed through Actor Attribution, Investment Authority Regime, Approval, Authority Denial, Mandate Exception, Residual-Risk Acceptance, and related power-specific concepts.

An **Authority** is the domain or architectural owner allowed to decide, write, validate, permit, or govern a concept. An Authority can be a service, lifecycle, or contract rather than only a database.

For example, PostgreSQL may be the System of Record for an approval task, while the approval lifecycle authority defines the semantics for Approval, Contestability, Residual-Risk Acceptance, and advancement across the governed boundary.

## Investment Strategy

An **Investment Strategy** is a durable, attributable, temporally applicable, reusable investment method that defines the economic rationale, applicability, Evidence and interpretation principles, Portfolio-expression logic, and Portfolio Risk discipline by which investment-relevant conditions are transformed into Portfolio-relevant implications within the applicable Investment Mandate.

A meaningful Investment Strategy preserves, where applicable, its central economic rationale or edge, normal Investment Horizon, applicability and abstention conditions, Evidence lens, interpretation principles, Portfolio-expression logic, Risk discipline, and evaluation basis. Strategy Principle is distinct from Investment Principle; a Strategy-specific rule is distinct from a Formal Constraint or Policy unless an authoritative Mandate or Policy relationship independently establishes that role.

Investment Strategy is distinct from Investment Mandate, Investment Hypothesis, Investment View, Portfolio Posture, Investment Recommendation, and Trading System. One Portfolio may employ zero, one, or multiple Investment Strategies. A Strategy may inform hypotheses and Views and may imply strategy-relative Portfolio consequences without itself becoming a Portfolio-specific Recommendation.

An analytical dimension, indicator, formula, Investment Signal, or score alone is not an Investment Strategy. Trend, momentum, valuation, carry, volatility, mean reversion, or another dimension may found or inform a Strategy without becoming the Strategy itself. Bull, Bear, and Sideways remain analytical perspectives rather than Strategies.

Strategy identity follows the coherent recurring method rather than every parameter value. Material changes to rationale, source of expected edge or opportunity, Investment Horizon, Evidence interpretation, Portfolio-expression logic, or Risk discipline may create a new linked Investment Strategy identity; parameter changes do not mechanically decide identity. A Lesson may motivate Strategy revision but does not silently mutate the historical Strategy.

A Strategy may be configured for a Portfolio without being applicable to every Investment Decision, and applicability does not imply that the Strategy materially informed a particular judgment. Deterministic or systematic operation does not confer investment authority.

## Trading System

A **Trading System** is a sufficiently operationalized rule set whose declared inputs and rules determine concrete target trading state or actions with little or no material discretionary investment judgment remaining inside the system's declared decision method.

Trading System is distinct from Investment Strategy and from an execution system. Systematic or deterministic logic alone does not make a method a Trading System; operational completeness within the declared decision method is the boundary. Concrete entry, exit, target Position, Allocation, size, rebalance, stop, or target-state prescriptions strongly indicate Trading System semantics.

One Investment Strategy may be operationalized by zero, one, or multiple Trading Systems, and one Trading System may operationalize or combine aspects of multiple Strategies. Trading-System output is classified by its actual role: a method-relative analytical indication may be an Investment Signal, an interpretation may support an Investment Hypothesis, and a concrete candidate Portfolio implementation considered within a real Investment Decision may be a Proposed Action. Output is not automatically an Investment Recommendation, Human Investment Decision, Action Intent, or authority fact.

## Investment Hypothesis

An **Investment Hypothesis** is an attributable, falsifiable candidate interpretation of investment-relevant conditions whose supporting Evidence, conflicting Evidence, Investment Assumptions, Invalidation Conditions, Investment Horizon, material Investment Uncertainty, and Judgment Confidence remain reconstructable where material.

Multiple Investment Hypotheses may coexist, conflict, be challenged, rejected, superseded, or remain unresolved without requiring a Decision Need or Investment Decision to exist. An Investment Hypothesis is not a vote, Investment Strategy, Portfolio Posture, Investment View, or Investment Recommendation.

Bull, Bear, and Sideways are trend-oriented analytical perspectives that may produce competing Investment Hypotheses about market or Portfolio conditions. They are not themselves Investment Strategies, Market Regimes, or durable judgments merely because legacy Polaris implementation described them as strategy perspectives. Trend may be a foundational analytical dimension within an Investment Strategy without making `Bull`, `Bear`, or `Sideways` strategies.

`Strategy Hypothesis` is retired as preferred canonical vocabulary when it refers to this candidate investment-interpretation role; use `Investment Hypothesis`.

## Investment View

An **Investment View** is an attributable, time-specific synthesized interpretation of investment-relevant conditions formed through reasoning and challenge from available Evidence and relevant Investment Hypotheses.

An Investment View may express a leading interpretation, Market Regime interpretation, material alternatives or dissent, Investment Assumptions, Invalidation Conditions, Judgment Confidence, and Investment Uncertainty without thereby specifying a Portfolio action. It may exist before, alongside, or without a Decision Need or Investment Decision.

One Investment View may inform zero, one, or multiple Investment Decisions, and one Investment Decision may draw materially on zero, one, or multiple Investment Views. The same Investment View may correctly lead to different Portfolio consequences, Portfolio Postures, or Investment Recommendations for different Portfolios because Portfolio State, Investment Mandate, Portfolio Risk, Decision Scope, and other Decision Context differ.

Investment View is distinct from Portfolio Posture and Investment Recommendation. A View describes the synthesized investment interpretation; Portfolio Posture describes a Portfolio-specific economic orientation; an Investment Recommendation expresses Polaris's preferred economic disposition of a particular Decision Need.

A materially new attributable Investment View formed after new Evidence or reassessment is preserved as a new historical judgment rather than destructively rewriting an earlier View. No particular synthesis mechanism is required: multi-agent debate, hypothesis comparison, one-model reasoning, deterministic analytics, or another mechanism may contribute when the resulting domain semantics are preserved.

`Strategy Decision` is retired as canonical Polaris domain vocabulary. The legacy concept did not represent a genuine durable decision; it combined hypothesis synthesis with downstream Portfolio-specific posture under a misleading `Decision` label. Its synthesized investment-interpretation meaning belongs to Investment View, while any Portfolio-specific posture or consequence belongs downstream under Portfolio Posture, Projected Portfolio Consequence, or Investment Recommendation according to meaning. `Strategy Synthesis` may describe a reasoning or implementation mechanism that contributes to an Investment View, but it is not required as a canonical investment-domain judgment.

## Investment Horizon

An **Investment Horizon** is the explicit ex-ante temporal scope over which an Investment Objective, Investment Strategy, Investment Thesis, Investment Decision, Investment Recommendation, or intended Portfolio consequence is framed.

Investment Horizon is distinct from actual Holding Period, Observation Cadence, Review Condition, and a later evaluation window. It may be expressed as an exact date, range, duration, approximate period, or event-bounded scope without fabricating precision not supported by the judgment.

Several Investment Horizons may coexist for different judgments or purposes. Investment Horizon materially affects Evidence relevance and freshness, Portfolio Risk, Strategy applicability, expected consequences, and evaluation criteria. Actual Holding Period or later Outcome does not rewrite the ex-ante Investment Horizon, and reaching the Horizon does not impose one universal lifecycle transition.

## Investment Thesis

An **Investment Thesis** is a durable, attributable, temporally scoped investment case concerning an investment subject or opportunity that states why and how relevant conditions are expected to create, preserve, impair, or reveal economic value or Risk.

Where materially applicable, an Investment Thesis preserves its central proposition, Investment Horizon, supporting and conflicting Evidence, Investment Assumptions, Investment Uncertainty, Catalysts, and Invalidation Conditions. It may exist without a Position, Investment Decision, Investment Recommendation, or Human Investment Decision and may inform multiple Investment Decisions through time.

Investment Thesis is distinct from Investment View and Investment Hypothesis. A Thesis is a durable investment case; a View is a time-specific synthesized interpretation; a Hypothesis is a falsifiable candidate interpretation. No mandatory Hypothesis → View → Thesis pipeline is required.

Thesis identity follows the coherent central investment case rather than every Evidence change. A material change to the central proposition, mechanism, source of value/Risk, or Investment Horizon may create a new linked Thesis. An opposite or fundamentally different case is not merely a silent revision. A Position or Investment Decision ending does not automatically end the Thesis. Once invalidated, the historical Thesis remains invalidated; renewed support requires a new attributable judgment, with normal identity rules determining whether the resulting case is the same, revised, or new.

## Investment Assumption

An **Investment Assumption** is an explicit proposition materially relied upon as a premise in investment reasoning without becoming an established fact merely through that reliance.

Investment Assumption is distinct from Evidence, fact, and Investment Hypothesis. Material assumptions remain attributable to the judgment or case that relied upon them. A later finding that an assumption was false does not rewrite its historical role and does not automatically invalidate an Investment Thesis unless the assumption was materially necessary to the case or an applicable Invalidation Condition establishes that consequence. Retrospectively inferred assumptions remain retrospective rather than being fabricated as judgment-time premises.

## Invalidation Condition

An **Invalidation Condition** is an explicit analytical criterion associated with a time-specific investment case or judgment whose established satisfaction means that subject cannot remain currently supportable under its stated terms without a new attributable judgment.

Invalidation Condition is distinct from Review Condition, Formal Constraint, Policy, Admissibility, authority, and Action Intent. It may be deterministic or interpretive, but satisfaction does not itself compel a human action, establish the opposite Investment Thesis, or confer authority. Uncertain satisfaction remains unresolved. The same threshold or observation may separately possess several roles only when each role is independently established.

For reusable Investment Strategy semantics, applicability and abstention conditions are preferred over treating every reusable strategy rule as an Invalidation Condition.

## Catalyst

A **Catalyst** is an anticipated event or development expected to materially affect the timing, strength, realization, or assessment of an Investment Thesis or investment opportunity.

An expected Catalyst is distinct from the event when it later occurs. Occurrence becomes an observed fact and may assume an Evidence or Investment Signal role while the historical Catalyst expectation remains. A Catalyst may be positive, negative, mixed, or uncertain and is distinct from Investment Assumption, Invalidation Condition, and Review Condition.

The same anticipated event may be a Catalyst for multiple Investment Theses. An unexpected event is not retroactively converted into an anticipated Catalyst. Nonoccurrence may become Evidence and invalidates a Thesis only when a separate analytical relationship establishes that consequence. A Catalyst may cause Attention but does not automatically establish Decision Need, Investment Recommendation, or authority.

## Investment Signal

An **Investment Signal** is a time-specific, method-relative analytical indication derived from investment-relevant observations or measures and expressing a condition, tendency, transition, threshold crossing, relative attractiveness, prediction, or other possible investment implication.

Indicator, observation, measure, score, or raw analytical value is not automatically an Investment Signal; Signal semantics arise from a method-relative analytical interpretation or implication. An Investment Signal may describe state, event, transition, ranking, threshold, relationship, prediction, or another analytical indication and may be directional or nondirectional.

Investment Signal is distinct from Investment Hypothesis, Investment View, Investment Thesis, Portfolio Posture, Proposed Action, Investment Recommendation, and Human Investment Decision. Labels such as `BUY`, `SELL`, `HOLD`, `LONG`, `SHORT`, `bullish`, `bearish`, or `strong buy` do not determine semantic role by themselves. A generic method-relative buy/sell indication may remain a Signal, while a concrete candidate Portfolio implementation introduced into an Investment Decision has Proposed Action semantics.

Investment Signal is not automatically Evidence; it assumes an Evidence role when materially used to support, contradict, constrain, qualify, or reconstruct a material judgment. Underlying observations and the derived Signal may independently assume Evidence roles. Multiple conflicting Signals derived from the same observations under different methods may legitimately coexist.

Market Regime, Catalyst, Review Condition, Invalidation Condition, Formal Constraint result, Risk measure, and Investment Signal remain distinct roles even when one observation participates in several. A Signal may cause Attention but does not automatically establish Decision Need, Portfolio Posture, Proposed Action, Investment Recommendation, or authority.

Materially used Investment Signals must remain reconstructable to the degree required by Durable Decision Memory, including sufficient subject, method/version or analytical basis, parameters where material, as-of time, temporal scope, source, and derivation lineage. Transient Signals that never materially affect durable judgment need not automatically become permanent records.

## Portfolio Posture

**Portfolio Posture** is an attributable, time-specific, Portfolio-relative and scope-aware investment judgment describing the integrated economic orientation judged appropriate for a Portfolio across one or more dimensions such as Exposure, risk-taking, liquidity, concentration, diversification, hedging, or rebalance direction, without itself requiring a concrete Proposed Action, target Allocation, or Investment Recommendation.

Portfolio Posture is distinct from actual Portfolio State, Allocation, Exposure, Proposed Action, Investment Recommendation, Position Direction, and a strategy-relative implication. Role, not authorship, determines Posture semantics; a human, Polaris, or another attributable actor may express a Posture without attribution itself granting authority.

One Portfolio may have several contemporaneous scoped Postures across dimensions or Horizons; there is no required single global mutable posture. Investment Views, Investment Strategies, Portfolio State, Investment Mandate, Portfolio Risk, Investment Horizon, and other Decision Context may inform Posture. The same Investment View may imply different Postures for different Portfolios.

A hypothetical alternative does not become historical Portfolio Posture merely because it was analyzed. A new attributable Posture preserves history rather than destructively replacing prior Postures. Divergence between actual Portfolio State and judged Portfolio Posture may cause Attention but does not automatically establish a Decision Need.

## Allocation

**Allocation** is a concrete target or actual distribution of capital across assets, sectors, strategies, accounts, or Risk buckets.

An Investment View or Portfolio Posture may inform an Investment Recommendation or Proposed Action suggesting movement toward an Allocation, but Allocation remains distinct from Exposure, Portfolio Posture, and Portfolio Risk.

## Projected Portfolio Consequence

A **Projected Portfolio Consequence** is an attributable, prospective, Portfolio-relative statement of a material expected economic effect or change under a stated Investment View, Investment Scenario, status-quo continuation, Decision Alternative, Proposed Action, Investment Recommendation, or other candidate disposition, relative to a reconstructable Portfolio baseline and under the applicable assumptions, Investment Horizon, scenario conditions, and Investment Uncertainty where material.

Projected Portfolio Consequence is distinct from Proposed Action, Projected Portfolio State, Portfolio Risk, and Outcome. It may be qualitative, quantitative, bounded, probabilistic, or scenario-specific and may describe expected changes in Allocation, Exposure, concentration, liquidity, diversification, drawdown sensitivity, objective alignment, opportunity cost, or other material Portfolio effects.

One source judgment or Decision Alternative may have multiple Projected Portfolio Consequences, and alternatives may be compared against one another or against status quo. A projected Risk change is a prospective consequence concerning Portfolio Risk, not the underlying Risk itself. Later Outcome does not rewrite the historical projection; comparison belongs in Decision Evaluation.

A Projected Portfolio Consequence does not establish Admissibility, Approval, Human Investment Decision, Action Intent, or authority.

## Investment Relevance

**Investment Relevance** is a time-, subject-, and use-specific relationship indicating that information, a condition, change, or prior domain fact legitimately bears on an investment subject, Portfolio, Investment Thesis, Investment Strategy, Investment Decision, or investment judgment.

Investment Relevance is contextual rather than intrinsic and is distinct from truth, authority, sufficiency, freshness, Investment Materiality, and Decision Need. `Decision Relevance` may be used as a qualified case when the use is specifically an Investment Decision. Relevance may be deterministic, interpretive, or unresolved and may change through time without rewriting an earlier reasonable relevance assessment.

## Investment Materiality

**Investment Materiality** is the time-, subject-, and use-specific significance of investment-relevant information, change, uncertainty, Portfolio Risk, condition, or absence such that omitting, mischaracterizing, or properly incorporating it could reasonably alter investment interpretation, Investment Thesis, Investment View, Portfolio Posture, Portfolio Risk Assessment, Projected Portfolio Consequence, candidate economic disposition, Investment Recommendation, or whether a Portfolio-relevant choice warrants deliberate judgment.

Investment Materiality presupposes Investment Relevance for the same use but is distinct from relevance. It concerns reasonable potential significance at the assessment time rather than whether an Outcome or final action eventually changed. Missing, stale, conflicting, or uncertain information may itself be Investment Materiality.

Investment Materiality is contextual and need not use a universal numeric threshold. It may be deterministic, interpretive, or unresolved and is distinct from Decision Need, Capital-Relevant Output, truth, freshness, sufficiency, authority, Admissibility, and Approval. It is also distinct from platform, operational, governance, or authority materiality, although one fact may independently possess several materiality roles.

## Portfolio Risk

**Portfolio Risk** is the time-, Portfolio-, Investment-Horizon-, and scenario-relative possibility of materially adverse economic outcomes or material shortfall relative to applicable Investment Objectives arising from actual or projected Portfolio State, Exposures, market conditions, and other investment-relevant conditions.

Portfolio Risk exists independently of whether Polaris or any actor has identified, measured, represented, or understood it. It is distinct from Exposure, volatility, VaR, beta, drawdown measures, qualified Risk Scores, realized loss, Outcome, Investment Uncertainty, Projected Portfolio Consequence, Formal Constraint, Policy, Admissibility, and authority.

Portfolio Risk is naturally multidimensional and need not collapse into one scalar, probability, volatility value, score, or signed direction. It may be described quantitatively, qualitatively, probabilistically, scenario-wise, through stress conditions, as a bounded range, or as unresolved when stronger precision is unsupported.

Current Portfolio Risk and projected or incremental Portfolio Risk under a Decision Alternative, Investment Scenario, Proposed Action, or Projected Portfolio State are qualified uses of the same concept. The same Financial Instrument, Position, Exposure, or market condition may create materially different Portfolio Risk for different Portfolios, Investment Horizons, or scenarios.

A favorable Outcome does not prove prior Portfolio Risk was absent. When an adverse possibility materializes, the observed consequence becomes Outcome or another authoritative historical fact while remaining future Portfolio Risk is assessed separately. Material Portfolio Risk or material change in Risk may cause Attention but does not automatically establish Decision Need.

Bare `Risk` is not the canonical Polaris investment-domain noun when ambiguity with evidence, governance, operational, implementation, or platform risks matters. Conventional qualified finance uses such as credit risk, liquidity risk, market risk, or residual factor risk remain available according to their actual meanings.

## Investment Uncertainty

**Investment Uncertainty** is the time-, subject-, and judgment-relative limitation in what can be established about investment-relevant facts, causal relationships, future states, probabilities, model applicability, or economic consequences.

Investment Uncertainty is a semantic qualification rather than a mandatory independent entity. It is distinct from Portfolio Risk and may concern favorable, adverse, neutral, mixed, or unresolved possibilities. It may arise from missing, stale, conflicting, or insufficient Evidence; unknown probabilities; causal ambiguity; model uncertainty; scenario uncertainty; structural change; or genuine unknowability.

Evidence deficiency does not automatically imply material Investment Uncertainty, and substantial Investment Uncertainty may remain even when available Evidence is fresh and internally consistent. High Investment Uncertainty does not necessarily imply high Portfolio Risk, and high Portfolio Risk may exist under comparatively well-characterized uncertainty.

Investment Uncertainty must not be converted into unsupported probabilities or confidence values merely to make it machine-readable. Material uncertainty that qualifies an Investment Thesis, Investment View, Portfolio Risk Assessment, Projected Portfolio Consequence, Investment Recommendation, or Decision Evaluation remains reconstructable where required by Durable Decision Memory. Later resolution does not rewrite the uncertainty actually present or recognized at an earlier judgment time.

## Portfolio Risk Assessment

A **Portfolio Risk Assessment** is an attributable, time-specific analytical judgment describing the nature, sources, severity, range or likelihood where supportable, interactions, and material Investment Uncertainty of Portfolio Risk under an applicable Portfolio baseline, Investment Horizon, Investment Scenario, stress condition, or Decision Alternative.

Portfolio Risk Assessment is a canonical analytical judgment role rather than a mandatory standalone entity. One Assessment may address multiple Risk dimensions, current or projected Portfolio Risk, status quo, stress scenarios, or several alternatives. Different actors or methods may legitimately form different Assessments of the same underlying Portfolio Risk without disagreement alone proving one erroneous.

Risk measures, qualified Risk Scores, Investment Signals, statistical models, stress tests, deterministic calculations, scenario analysis, human judgment, or Polaris reasoning may inform a Portfolio Risk Assessment without becoming the underlying Portfolio Risk or the complete Assessment.

A trustworthy Portfolio Risk Assessment preserves material Investment Uncertainty and may remain incomplete, qualified, withheld, or unresolved where support is insufficient. Materially used Assessments preserve Actor Attribution and sufficient judgment-time Evidence, assumptions, method, scenario, Investment Horizon, uncertainty, and provenance for reconstruction. Later Evidence, model changes, or Outcomes do not destructively rewrite the historical Assessment.

Portfolio Risk Assessment may shape Portfolio Posture, Decision Alternatives, Projected Portfolio Consequences, Investment Recommendation, or deliberate withholding of Recommendation but does not establish Formal Constraint satisfaction, Mandate compliance, Approval, Admissibility, Residual-Risk Acceptance, or other authority. Analytical language such as `acceptable Risk` does not instantiate Residual-Risk Acceptance unless the separate authority act and scope are actually established.

## Trade Implementation Risk

**Trade Implementation Risk** is the prospective possibility that translating a Proposed Action, Human Investment Decision, or Action Intent into market-facing trading activity will materially degrade, delay, alter, or fail to achieve the intended Portfolio consequence because of materially relevant trading or implementation conditions.

Trade Implementation Risk may arise from liquidity, adverse price movement, market impact, timing, delay, partial execution, nonexecution, transaction-cost uncertainty, venue or broker conditions, settlement, or materially relevant operational trading failures. Generic platform or workflow failures are not Trade Implementation Risk unless they materially bear on implementation of the relevant trading action.

Trade Implementation Risk may be assessed hypothetically while a Proposed Action or Decision Alternative is still being considered and may continue to be reassessed after Human Investment Decision or Action Intent while implementation remains incomplete. A market-facing Order need not yet exist.

Current Portfolio Risk, projected Portfolio Risk under a candidate state, and Trade Implementation Risk involved in reaching that state are distinct questions. Known or reasonably expected transaction costs may be Projected Portfolio Consequences or implementation costs rather than Risk; materially adverse uncertainty around cost, implementation shortfall, timing, fills, market impact, or completion may constitute Trade Implementation Risk.

Sizing, Allocation, Exposure, and concentration consequences of the resulting Portfolio State belong primarily to Projected Portfolio Consequence and Portfolio Risk, although trade size may create Trade Implementation Risk through liquidity, market impact, timing, or practical implementability. Policy, Approval, Mandate Exception, Governance, or Admissibility blockers are not Trade Implementation Risk merely because they prevent advancement.

Observed fills, slippage, market impact, delay, failed execution, nonexecution, implementation shortfall, and other market-facing facts become authoritative execution evidence, Outcome, or Evaluation facts rather than remaining merely prospective Trade Implementation Risk. External execution systems remain authoritative for Orders, routing, working state, fills, cancellations, and related execution facts.

Broad Polaris-owned `Execution Risk` is retired as the umbrella for candidate-action implementation Risk. External specialist uses of `execution risk`, market impact, delay cost, opportunity cost, transaction cost, implementation shortfall, and execution quality retain their applicable meanings and may inform Trade Implementation Risk or later Evaluation without being collapsed into it.

## AI-Adjacent Output

> **Legacy governance/platform vocabulary pending re-parenting.**

An **AI-Adjacent Output** is an output produced by, transformed by, summarized by, routed through, or materially influenced by model, agent, RAG, evaluation, or automated decision-support behavior.

AI-Adjacent status does not by itself determine authority, truth, readiness, or risk tier. AI-Adjacent Outputs require classification by their effect, source of truth, intended sink, evidence sufficiency, external visibility, durable authority, governance impact, and capital relevance.

## Risk Authority Contract

> **Legacy governance/platform vocabulary pending re-parenting.**

A **Risk Authority Contract** is the canonical classification of one AI-adjacent output boundary's consequence tier, allowed effect, owner, source-of-truth category, intended sink, gate profile, and evidence or governance flags.

A Risk Authority Contract describes what an output is allowed to affect after platform classification. Model output or model-provided metadata cannot self-declare authority, production readiness, governance Approval, Residual-Risk Acceptance, or a lower risk tier.

## Risk Tier

> **Legacy governance/platform vocabulary pending re-parenting; a Risk Tier is not Portfolio Risk.**

A **Risk Tier** is a consequence classification for an AI-Adjacent Output.

Canonical Risk Tiers are:

- **Baseline**: low-consequence informational or runtime output that does not require enhanced evidence or governance controls.
- **Enhanced**: output requiring stronger evidence, readiness, or authority controls because it is externally visible, durable, capital-relevant, evidence-insufficient, non-runtime-sourced, or otherwise consequential.
- **Vigilant**: output requiring the strongest automated governance and boundary controls because it can affect capital, governance, execution decisions, durable authority, external visibility, or unresolved evidence sufficiency.
- **Prohibited / Outside Authority**: output whose requested effect is outside Polaris authority and must not be treated as allowed by model text, interface behavior, or local metadata.

## Policy

**Policy** answers whether an operation, output, or boundary crossing may happen under deterministic platform rules. Policy outcomes are allow or deny style decisions and do not by themselves store human governance Approval.

Policy is distinct from Portfolio Risk and from Formal Constraints in an Investment Mandate. A Policy may govern whether decision work is performed or an output advances without becoming the semantic definition of the underlying investment judgment.

## Governance

**Governance** answers whether an operation, output, or boundary crossing should happen given consequence, Evidence, review, Contestability, Governed Residual Risk, and applicable authority requirements.

Governance is separate from Policy. Automated Governance may allow, warn, deny, require Approval, or skip. Human or organizational review is a governance lifecycle above automated governance, not a replacement policy engine and not model-declared readiness.

## Governed Output

A **Governed Output** is an output whose consequential use, Publication, Durable Promotion, or downstream use is subject to Policy, Governance, Evidence readiness, review, Admissibility, or Residual-Risk Acceptance requirements.

Capital-Relevant Enhanced and Vigilant outputs are Governed Outputs when they are externally visible, durably authoritative, governance-impacting, or otherwise cross a controlled boundary.

## Readiness Gate

A **Readiness Gate** is a boundary check that determines whether a Claim, output, record, or legacy architecture projection is allowed to proceed to a consequential use, Publication, Durable Promotion, retrieval eligibility, or downstream use.

Readiness Gates fail closed when required Evidence, reconstruction, correctness, governance review, Residual-Risk Acceptance, or source authority is missing, stale, conflicted, rejected, or malformed.

## Output Boundary

An **Output Boundary** is a point where Polaris output leaves its current internal role and becomes visible, durable, authoritative, retrievable, or available for downstream decision use.

Examples include report Publication, recommendation rendering, RAG answer generation, MCP/API/CLI responses, curated-record persistence, graph/vector projection, and other governed consequential uses.

## Review Task

A **Review Task** is durable governance work created for a specific subject, evidence packet, evidence version, review scope, requested action, and intended sink when automated governance requires human or organizational review.

A Review Task is resolved only by attributable review decisions such as Approval, Authority Denial, contest, requested changes, or override. Model text cannot resolve a Review Task.

## Contestability

**Contestability** is the ability for an attributable reviewer or governance process to challenge, deny, request changes to, or override an automated governance outcome without deleting or rewriting the original automated audit record.

Contestability preserves the history of the automated outcome, review rationale, Evidence version, and resulting task status.

## Completed-Run Archive

> **Legacy platform/runtime vocabulary pending re-parenting.**

A **Completed-Run Archive** is the durable runtime archive of a finished workflow execution, including runtime context and node outputs needed for replay, inspection, audit, and reconstruction.

A Completed-Run Archive is broad Runtime Evidence. It is not automatically a Curated Record, RAG-eligible source, architecture Projection, Investment Recommendation, Approval, or Source of Truth for every business concept it contains.

## Curation

> **Legacy platform/runtime vocabulary pending re-parenting.**

**Curation** is the deliberate selection and normalization of workflow or platform output into a Curated Record with typed meaning, deterministic identity, temporal meaning, lineage, quality checks, and authoritative ownership.

Curation is narrower than archival and precedes selective embedding or graph projection.

## Embedding Eligibility

> **Legacy platform/runtime vocabulary pending re-parenting.**

**Embedding Eligibility** is the decision that a Curated Record is useful and safe enough to become retrieval context for RAG.

Embedding Eligibility does not make a record true, approved, capital-actionable, or release-ready. It only allows the record to be represented in retrieval projections under the applicable source, lineage, Evidence, and Governance rules.

## RAG Answer

> **Legacy platform/runtime vocabulary pending re-parenting.**

A **RAG Answer** is a retrieval-grounded answer assembled from retrieved or cited context and generated claim data.

A RAG Answer is presentation output. Its rendered text is not the Claim Source of Truth and not an authority for Approval, Residual-Risk Acceptance, or durable decision support unless the underlying Claims and Evidence pass the applicable decision-evidence and governance rules.

## Application Service

> **Legacy architecture vocabulary pending re-parenting.**

An **Application Service** is a platform boundary that owns a use-case operation, coordinates typed domain contracts, applies Policy or Governance where applicable, and delegates external access to Providers or Clients.

Application Services are the preferred domain-facing surface for interfaces such as CLI, MCP, API, reports, workflows, and future transports.

## Provider

> **Legacy architecture vocabulary pending re-parenting.**

A **Provider** is a typed boundary that normalizes a class of external or simulated capability for Application Services. Providers hide vendor-specific transport, SDK, authentication, retry, and response-shape concerns from intelligence components and workflow nodes.

## Client

> **Legacy architecture vocabulary pending re-parenting.**

A **Client** is a vendor-specific or transport-specific adapter used beneath a Provider to communicate with an external system or local service.

Clients do not own Polaris domain semantics. Provider normalization is required before external data becomes typed platform input.

## Backtest

A **Backtest** is a historically constrained counterfactual evaluation of a sufficiently specified Investment Strategy, Trading System, systematic Portfolio method, or other investment decision method through historical investment conditions to estimate how the method would have behaved and what hypothetical Portfolio states, consequences, Portfolio Risk, costs, and performance would have resulted.

Investment Strategy existence does not imply Backtestability. A method is sufficiently backtestable only to the degree its material historical decision process can be bounded and reconstructed well enough to prevent hindsight from silently determining the answer. Reproducibility does not require complete determinism; a discretionary Strategy may be Backtested when the Strategy/process, simulated historical information boundary, decision protocol, and material judgment conditions are sufficiently fixed or bounded before later outcomes are revealed.

Backtestability is distinct from Trading System semantics. A structured discretionary Backtest may legitimately produce evaluator-dependent results when discretion is part of the tested method and the evaluator or decision mechanism remains attributable and reconstructable. Unbounded retrospective judgment made with knowledge of subsequent outcomes is retrospective historical analysis rather than a trustworthy Backtest.

Backtest-generated Signals, candidate actions, Recommendations, trades, Portfolio states, and results are counterfactual and must not be represented as actual historical Investment Signals, Proposed Actions, Investment Recommendations, Human Investment Decisions, Action Intents, Orders, Positions, Portfolio States, or Outcomes unless those facts independently occurred. Backtest result is distinct from Outcome and Decision Evaluation.

A Backtest may assume an Evidence role when materially used. Material Backtests preserve the tested method/version, historical period, simulated information boundary, data vintages and revision treatment, universe construction, corporate-action treatment, Portfolio assumptions, transaction costs, liquidity/rebalancing/implementation assumptions, and other material design facts. Look-ahead, survivorship, future-universe, revised-data, future-calibration, or similar hindsight contamination must be prevented or explicitly disclosed.

The former Polaris runtime meaning of `Backtest` as workflow replay is retired from investment-domain vocabulary and must be re-parented under qualified runtime/architecture terminology during reconciliation.

## Investment Scenario

An **Investment Scenario** is an explicitly identified hypothetical or counterfactual configuration or path of investment-relevant conditions over a stated temporal scope used to reason about possible investment implications, Portfolio states, Portfolio Risk, Investment Strategy applicability, or Decision Alternatives.

Investment Scenario is distinct from Investment View, forecast, prediction, Outcome, and Market Regime. A Scenario does not assert that its conditions will occur and does not imply probability, likelihood, or confidence unless that separate assessment is independently established. Baseline, upside, downside, adverse, stress, historical, and counterfactual are qualified uses rather than mandatory separate domain concepts.

An Investment Scenario may be manually authored, externally supplied, analytically derived, or generated through Investment Simulation. A raw Simulation or Monte Carlo path does not become an Investment Scenario merely because it is hypothetical; it assumes Scenario semantics when explicitly identified, selected, or used as a coherent hypothetical case.

Scenario semantic identity follows the coherent hypothetical case and defining conditions rather than display label alone. A materially changed defining condition, path, or temporal scope must remain distinguishable from the Scenario definition previously used, whether represented as a revision or a related new Scenario. A durable judgment that materially relies on a Scenario remains bound to the materially relevant Scenario definition that informed it.

Historical Scenario Analysis may use genuine historical market/economic facts while applying them counterfactually to another Portfolio, time, or subject. The source facts remain historical; simulated Portfolio states, consequences, and decisions remain hypothetical. Later real-world conditions matching an earlier Scenario do not retroactively convert the Scenario or its outputs into actual Portfolio State, Decision Context, or Outcome.

## Investment Simulation

**Investment Simulation** is an analytical method that uses explicit data, models, assumptions, or sampling processes to generate or evaluate hypothetical investment conditions, paths, Portfolio states, or outcomes.

Investment Scenario is distinct from Investment Simulation: Scenario specifies or identifies a hypothetical case; Simulation is a method for generating or evaluating hypothetical cases, paths, states, or outcomes. A Scenario may be evaluated without Simulation, and one Simulation may generate or evaluate multiple Scenarios or unselected hypothetical paths.

Investment Simulation may be deterministic, stochastic, Monte Carlo, historically resampled, bootstrapped, model-based, or another explicitly defined hypothetical analytical method. Historical data use or the industry phrase `historical simulation` does not by itself make an Investment Simulation a Backtest.

Simulation-generated Portfolio states remain hypothetical and are distinct from actual Portfolio State. A raw simulated state or path does not automatically become a Projected Portfolio State or Projected Portfolio Consequence. It may support formation of those attributable judgments; when Polaris forms a Projected Portfolio State from Simulation output, Actor Attribution belongs to Polaris while the Simulation method, model, inputs, and results remain provenance.

A Simulation frequency, percentile, quantile, or modeled event rate is conditional on the Simulation's model and assumptions and is not automatically a supported real-world probability. Material Simulation assumptions, model form, distributions, parameters, Portfolio baseline, temporal scope, Scenario conditions, sampling process, Investment Uncertainty, and provenance remain reconstructable where materially relied upon. Simulation results may assume Evidence roles but do not establish Recommendation, Human Investment Decision, Action Intent, Formal Constraint result, Approval, Admissibility, Outcome, or authority.

The former Polaris runtime meaning of bare `Simulation` as controlled dependency/provider substitution is retired from investment-domain vocabulary and must be re-parented under qualified runtime/testing terminology during reconciliation.

## Judgment Confidence

**Judgment Confidence** is an attributable, time-specific qualification expressing how strongly an actor regards a specified investment judgment or material component as warranted by the Evidence, assumptions, and Investment Uncertainty applicable to that assessment.

Judgment Confidence is a qualification of another judgment or proposition rather than a mandatory independent entity. It follows Actor Attribution semantics and may be formed by a human, Polaris, a genuine collective actor, or an external originator whose confidence judgment is preserved as such. Internal models, classifiers, prompts, probability outputs, or other implementation components do not become the actor merely because they contributed.

Judgment Confidence must identify the judgment, proposition, aspect, dimension, or consequence whose warrant is being assessed. Absence of an attributable assessment is distinct from low confidence. Confidence may be qualitative, ordinal, categorical, or numeric; numeric Judgment Confidence requires an explicit scoring or calibration family sufficient to establish what the value means and how it may be interpreted.

Judgment Confidence is distinct from probability unless explicitly and supportably calibrated as probability; it is also distinct from truth, correctness, realized accuracy, favorable Outcome, Evidence quality/sufficiency/freshness, completeness, readiness, Mandate alignment, Admissibility, Approval, authority, and Investment Uncertainty. Judgment Confidence and Investment Uncertainty are not mathematical complements.

High Judgment Confidence does not itself determine Portfolio Posture, Position size, Allocation, Proposed Action, Investment Recommendation, Human Investment Decision, or authority. Later confidence reassessment creates a new time-specific assessment and does not rewrite the earlier one.

Bare `Confidence` is retired as a universal canonical Polaris investment score.

## Directional Bias

`Directional Bias` is retired as canonical Polaris investment-domain vocabulary because the legacy signed axis collapsed materially different analytical, market, Portfolio, Position, Risk, and evaluative meanings.

A method-relative directional analytical indication ordinarily uses Investment Signal semantics. An attributable synthesized directional interpretation may form part of an Investment View. A Portfolio orientation belongs to Portfolio Posture, and actual long/short holding semantics belong to Position Direction and resulting Exposure.

Bullish/bearish is distinct from Long/Short Position Direction, risk-on/risk-off, aggressive/defensive Portfolio Posture, and favorable/unfavorable relative attractiveness. Source-specific `directional bias` fields or signed directional measures may be preserved when their subject or target variable, polarity, scale, temporal scope or Investment Horizon, and method are explicit. Neutral, balanced, unknown, unavailable, insufficient-Evidence, no-signal, and conflicting-signal states must not be collapsed into numeric zero.

## Risk Score

Bare `Risk Score` is not a universal canonical Polaris investment-domain fact. A **qualified Risk Score** is a scalar, ordinal, categorical, or otherwise scored summary of a declared Risk construct for a declared subject under an explicit scoring methodology.

The Risk construct and subject remain explicit; instrument risk, Portfolio Risk, liquidity risk, concentration risk, investor risk tolerance, and other scored constructs are not equivalent merely because each uses a score. Materially used Risk Scores preserve the relevant method/version, scale, polarity or direction, temporal/as-of basis, Investment Horizon where applicable, normalization or reference universe, and other semantics that affect interpretation.

No universal score range or higher/lower convention is required. Ordinal, interval, ratio, percentile, rank, category, and other score scales do not support the same arithmetic. Multiple valid score families may produce different values for the same subject; cross-family comparison is invalid without explicit calibration or shared methodology. Methodology or normalization changes may change a score without proving that underlying Portfolio Risk changed.

Risk Score is distinct from Portfolio Risk, Portfolio Risk Assessment, probability of loss, realized loss, Outcome, Investment Uncertainty, and Judgment Confidence. Missing or indeterminate score is distinct from neutral, midpoint, or low Risk. A Risk Score or threshold may independently serve as Investment Signal, Attention condition, Review Condition, analytical classification, or Formal Constraint input only when that semantic role is separately established. Numeric form does not confer authority.

## Market Regime

A **Market Regime** is a time-, scope-, and classification-basis-specific analytical characterization of prevailing or historically prevailing market or market-relevant economic conditions representing a relatively persistent configuration of investment-relevant behavior or drivers.

Market Regime is an analytical classification rather than raw fact. Prices, returns, volatility, correlations, inflation, growth, liquidity, monetary policy, credit conditions, and similar observations may support classification without becoming the Regime itself.

Market Regime is distinct from Investment Signal, Investment Scenario, Investment View, Portfolio Posture, Portfolio Risk, Investment Strategy, and Decision Context. A Regime describes what environment a classification method regards as prevailing; a Signal expresses a possible investment implication. A Market Regime may assume an Evidence or Decision Context role only when that use is independently established for a particular judgment or Investment Decision.

`Economic Regime` does not presently require separate canonical identity. A macroeconomic or economic classification used to characterize the market-relevant investment environment may use Market Regime semantics with explicit economic classification basis and scope; external source terminology remains provenance.

Multiple legitimate Regime classifications may coexist across methods, dimensions, assets, geographies, and Investment Horizons. There is no universal scalar `current_market_regime`. Bull/Bear/Sideways remain analytical perspectives and do not automatically become Market Regimes, although another explicitly defined regime methodology may use the same labels.

Unknown, unclassified, or indeterminate Regime is distinct from neutral or stable Regime. No universal minimum duration defines a Regime. Regime persistence and transition are method-relative; transition timing may be probabilistic, interval-based, retrospectively classified, or unresolved rather than one objectively exact market-event timestamp.

Investment Strategy applicability or abstention may depend on Market Regime only when the Strategy explicitly establishes that relationship. Regime classification does not silently activate/deactivate a Strategy or confer authority.

Materially used Market Regime classifications preserve sufficient method/version, scope, temporal basis, inputs and assumptions, Investment Uncertainty, and provenance for reconstruction. Later revised data, model versions, or retrospective reclassification may coexist as new analysis but do not rewrite the Regime classification that materially informed an earlier judgment. Market Regime is a semantic analytical role rather than a mandatory durable aggregate/entity for every classification occurrence.

## Benchmark

A **Benchmark** is an explicitly specified investment comparison reference selected for a stated comparative or evaluation purpose against which the performance, Portfolio Risk, Exposures, behavior, or other relevant results of a Portfolio, Investment Strategy, Backtest, or other investment subject are assessed over an applicable period.

Benchmark is a role, relationship, and specification rather than the identity of the referenced index, portfolio, rate, liability, or other reference. A market index is not automatically a Benchmark. Appropriate Benchmarks may include asset-based indexes or reference portfolios, policy/custom portfolios, liability-based references, cash-plus or rate references, or other deliberately selected investment comparators. Peer universes or arbitrary side-by-side comparisons are not Benchmarks merely because they appear beside results; they assume Benchmark semantics only when deliberately selected for the stated comparative or accountability purpose.

Benchmark is distinct from Investment Objective, Evaluation Criterion, complete Decision Evaluation, Decision Alternative, and investment authority. Zero, one, or multiple Benchmarks may legitimately apply according to subject, purpose, dimension, Investment Horizon, or analytical question, and some Strategies may lack an appropriate Benchmark.

Benchmark appropriateness is subject-, purpose-, and period-specific. When a Benchmark is intended as an accountability standard for prospective or longitudinal evaluation, its material specification should be established before the evaluated period where reasonably necessary to avoid hindsight or cherry-picking. Post-hoc alternative benchmarking may be legitimate when identified as retrospective but must not be represented as the original Benchmark.

Benchmark authority follows the source establishing the Benchmark relationship. An external provider may be authoritative for index, rate, liability, or reference facts while an Investment Mandate, Investment Strategy, Portfolio relationship, or attributable analytical/evaluation act establishes why the reference is used as a Benchmark. A Mandate-specified Benchmark is an authoritative Mandate fact; an analyst-selected supplemental comparator does not amend the Mandate merely by being used in analysis.

Material Benchmark specification preserves selector or authority source, purpose, subject, period, source/reference identity, and materially relevant currency, return, weighting, rebalancing, methodology/version, liability assumptions, hurdle or rate construction, and other conventions. Routine provider or index maintenance does not mechanically create a new Benchmark relationship, but point-in-time facts remain reconstructable; material methodology or custom-benchmark changes may establish a new specification for later periods without rewriting prior history.

Benchmark outperformance does not prove a good Investment Decision, Strategy, or Recommendation, and underperformance does not prove a poor one. Benchmark misspecification may materially distort appraisal, attribution, Backtest interpretation, or Decision Evaluation without changing actual Outcome. Benchmark-relative results may assume Evidence roles when materially used. No separate canonical `Evaluation Basis` entity is presently required merely to contain Benchmark semantics.

## Attention

**Attention** is the Polaris domain responsibility that evaluates new observations, user requests, Portfolio changes, scheduled reviews, prior decision conditions, and other available investment context to determine whether deliberate investment judgment may now be warranted.

Attention may use deterministic criteria or interpretive investment assessment. A matched criterion, notable observation, Investment Signal, Market Regime change, Catalyst, or interpretive concern does not by itself create a Decision Need. Attention does not imply continuous surveillance of the financial world; what Polaris can evaluate is bounded by the information and investment context it is configured or otherwise authorized to observe.

Attention has no single global frequency. Temporal observation semantics may differ by observed subject, source, Portfolio context, user configuration, and current decision use. Newly available or newly due information may cause Attention to evaluate without requiring all Polaris state to refresh in lockstep. Observation updates may occur frequently while Investment Decision state changes only when the information materially affects decision work.

Polaris Decision Context is temporally composed rather than globally refreshed. Facts and derived measures retain their own as-of times, provenance, and freshness; representing them together does not imply that every component was observed or recomputed simultaneously.

## Observation Cadence

**Observation Cadence** is the normal temporal pattern by which information about an observed subject or condition is obtained or reconsidered for Attention.

An Observation Cadence may be event-driven, periodic, scheduled, on-demand, or condition-driven. It may differ by source, observed subject, Portfolio context, configured investment use, and current Decision Context.

Observation Cadence is distinct from Freshness Requirement. A cadence describes when information is normally obtained or reconsidered; it does not guarantee that the resulting information is current enough for every Investment Decision.

## Freshness Requirement

A **Freshness Requirement** is the maximum acceptable age or other temporal adequacy required of information for a particular investment use.

An active Investment Decision may require fresher information than the normal Observation Cadence without permanently changing that cadence. If available information cannot satisfy the applicable Freshness Requirement, Polaris must preserve that insufficiency rather than treating stale information as current.

## Decision Need

A **Decision Need** is an explicit, attributable determination that an unresolved Portfolio-relevant investment choice now warrants deliberate judgment.

A Decision Need records why decision work is required and is distinct from the observation, user request, scheduled review, condition, Evidence, Portfolio change, or other trigger that caused Attention to evaluate the matter. Trigger provenance and the attributable basis for the determination remain reconstructable where material.

Establishing a Decision Need is sufficient domain justification to initiate or continue Investment Decision work when the same coherent unresolved choice is not already represented by an unresolved Investment Decision. Human confirmation is not a canonical semantic prerequisite for the Decision Need or for initiation of that work. If an unresolved Investment Decision already represents the same coherent choice, later triggers, requests, observations, or Evidence contribute to that existing decision rather than creating duplicate identity merely because initiation occurred again.

Decision Need establishment and Investment Decision initiation are knowledge/work-state transitions, not exercises of consequential investment authority. They do not imply an Investment Recommendation, Proposed Action, Admissibility, Approval, Mandate Exception, Residual-Risk Acceptance, Human Investment Decision, Action Intent, execution authority, or Portfolio change. Interpretive Attention may establish a Decision Need while preserving that interpretive provenance; deterministic conditions do not create an Investment Decision unless a genuine unresolved investment choice requiring deliberate judgment remains.

Autonomous initiation remains bounded by the information, Portfolio context, and operating scope Polaris is configured or otherwise authorized to observe or work within. Product, access, workflow, resource, or operating Policy may further govern whether particular work is performed or suppressed without becoming part of the canonical semantic definition of Decision Need or consequential investment authority.

A later finding that a Decision Need was erroneous or unsupported does not erase the historical determination or the Investment Decision work that actually occurred. Such a case is not automatically External Resolution when no genuine unresolved choice was eliminated by changed circumstances. Likewise, stopping or dismissing Polaris decision work is not by itself a Human Investment Decision unless the human also substantively disposes of the underlying Portfolio-relevant investment choice.

## Decision Scope

**Decision Scope** identifies the one or more Portfolios whose investment state, capital consequences, and applicable Investment Mandates are directly implicated by an Investment Decision.

A Portfolio used only as Evidence or analytical context is not automatically part of Decision Scope. Each scoped Portfolio retains its own Portfolio State, Investment Mandate, Formal Constraints, Portfolio Risk, and applicable Mandate Exceptions; a multi-Portfolio Investment Decision does not create an implicit synthetic Mandate.

Decision Scope may be unresolved while decision work is being initiated, but a final Capital-Relevant Investment Recommendation or Human Investment Decision must not silently assume Portfolio applicability that has not been established.

## Decision Subject

**Decision Subject** identifies the investment matter whose disposition is being judged within an Investment Decision.

A Decision Subject may concern an existing Position, establishing Exposure through a Financial Instrument, an Exposure, Allocation, Portfolio Posture, or another coherent investment matter. It may be composite when its elements form one mutually dependent investment judgment; independently resolvable matters should normally be separate Investment Decisions.

Decision Subject is distinct from Decision Scope, Evidence, the thing analyzed, a Decision Alternative, Proposed Action, and the Financial Instrument or other means ultimately used to implement the decision. The same Decision Subject may recur in separate Investment Decisions through time and therefore does not by itself establish Investment Decision identity.

## Decision Context

**Decision Context** is the time-specific, decision-relative set of applicable conditions, constraints, domain state, and prior decision state that frame an Investment Decision or an attributable judgment within it.

Decision Context may include applicable Portfolio State, Investment Mandate, Decision Scope, Decision Subject, Investment Strategy, Investment Horizon, Portfolio Risk, Market Regime, active Investment Thesis or Investment Assumptions, prior Investment Decisions and Investment Recommendations, unresolved questions, Review Conditions or awaited conditions, and other circumstances whose applicability materially frames the judgment. Context membership follows Investment Relevance and applicability rather than mere information possession.

Decision Context is distinct from Evidence. Evidence is information used in an evidentiary role; Decision Context describes the applicable circumstances within which judgment occurs. The same underlying fact may participate in Decision Context and also play an Evidence role without becoming two different domain facts.

Applicable Decision Context is also distinct from Polaris's or a human's information or representation of that context. A Mandate, Portfolio condition, Market Regime, or other applicable circumstance does not cease to apply merely because a judgment participant did not know it, could not access it, or represented it incorrectly. Historical reconstruction must preserve the distinction between what actually applied and what information about it was available to the judgment.

One unresolved Investment Decision may encounter materially changing Decision Context through time without changing Investment Decision identity. A context change does not by itself create a new Investment Recommendation; a new Recommendation still requires a distinct attributable Polaris judgment.

## Judgment-Time Availability

**Judgment-Time Availability** is the temporal relationship between information and a specific attributable judgment that describes whether that information was accessible to the judgment process before the judgment was formed.

Judgment-Time Availability is relative to the judgment, not globally to the Investment Decision. Information may therefore be unavailable to an earlier Investment Recommendation but available to a later Human Investment Decision or later Investment Recommendation within the same Investment Decision.

Judgment-Time Availability is distinct from when an underlying fact or event occurred, when a source published or exposed information, and whether the information is retrievable now. It is also distinct from freshness, sufficiency, conflict state, Admissibility, or fitness for the intended decision use, and from whether available information was actually used or materially informed the judgment.

When Polaris cannot establish whether information was available to a particular judgment, availability remains unknown rather than being inferred as unavailable. Later-created, later-discovered, or later-corrected information may support reconstruction, Decision Evaluation, or learning without becoming retroactively available to an earlier judgment. Conversely, information that was available to a historical judgment remains historically available even if its source later changes, disappears, or becomes inaccessible.

A Backtest uses a simulated historical information boundary rather than fabricating Judgment-Time Availability for an attributable historical judgment that never actually occurred.

## Investment Decision

An **Investment Decision** is a durable, identifiable unit of Portfolio-relevant investment judgment created to resolve a Decision Need about a Decision Subject whose potential capital consequences are evaluated within one or more Portfolio scopes.

Investment Decision identity is explicit and durable. It is not derived from Decision Subject, Decision Scope, Evidence, Investment Recommendation, workflow execution, current Portfolio State, or any other mutable decision-time fact. Identity is preserved while work continues to resolve the same coherent unresolved investment choice, even when Evidence, Portfolio State, Portfolio Risk, reasoning, Mandate assessment, Investment Recommendation, Decision Subject, or Decision Scope changes or is refined.

Once the investment judgment has been substantively resolved, a later renewed Decision Need creates a new causally linked Investment Decision rather than reopening and rewriting the resolved decision. Resolution of the investment judgment is a milestone within the Investment Decision lifecycle rather than necessarily the end of that lifecycle; action continuity, reconciliation, Outcome, and Decision Evaluation may continue under the same decision identity.

An Investment Decision may exist before its Decision Scope is fully resolved, but final Capital-Relevant Investment Recommendation or Human Investment Decision formation requires established Portfolio applicability. Portfolio-independent investment analysis or assessment may inform a future Investment Decision without itself constituting one.

An Investment Decision may concern one or several Portfolios and may result in action, modification, rejection, Deferral, deliberate inaction, or External Resolution. Deliberate hold or no-action can substantively resolve the investment choice; Deferral leaves the underlying Decision Need unresolved; External Resolution eliminates the Decision Need because changed circumstances remove the choice before a Human Investment Decision substantively resolves it.

An Investment Decision is distinct from workflow execution, an Investment Recommendation, governance Approval, and the attributable Human Investment Decision made within its lifecycle.

## Human Investment Decision

A **Human Investment Decision** is the attributable human judgment within an Investment Decision that selects, modifies, rejects, defers, or otherwise disposes of the Portfolio-relevant investment choice.

A Human Investment Decision may or may not substantively resolve the underlying Investment Decision. Deferral, or rejection accompanied by a request for further judgment, records attributable human judgment while leaving the Decision Need unresolved; deliberate hold or another substantive choice may resolve it.

A Human Investment Decision is distinct from Polaris's Investment Recommendation, automated Policy or Governance outcomes, Admissibility, Approval, Residual-Risk Acceptance, and Mandate Exception authorization. Human judgment does not retroactively rewrite the Investment Recommendation, Mandate, Formal Constraint results, or other decision-time facts that preceded it. A Human Investment Decision may be historically attributable even when the actor lacked one or more authority powers required for its consequential use; attribution must not be converted into inferred authority.

A Human Investment Decision formed in response to a Polaris Investment Recommendation retains separate Actor Attribution even when it adopts the Recommendation unchanged.

## Action Intent

An **Action Intent** is attributable post-human-decision continuity state describing an externally observable implementation consequence or control established by a Human Investment Decision so Polaris can reconcile later authoritative external activity and Portfolio State without acquiring execution authority.

A Human Investment Decision may establish zero, one, or multiple Action Intents. Action Intent cardinality follows coherent intended external consequence rather than Financial Instrument count, Proposed Action count, Order count, fill count, or other execution mechanics. An Action Intent may be composite when several external changes jointly define one coherent intended Portfolio consequence; independently meaningful consequences may be represented as separate Action Intents.

A Human Investment Decision may establish Action Intent even when no Polaris Investment Recommendation or Proposed Action exists. Deliberate hold/no-action or Deferral does not by itself require a synthetic Action Intent merely to duplicate the Human Investment Decision, although the same human judgment may establish an Action Intent for a separate externally intended consequence or maintained control.

Action Intent is distinct from an Order, fill, broker instruction, or another externally authoritative execution fact. It may be specific enough for later reconciliation, including an intended quantity, target state, protection condition, or similar implementation meaning, without thereby becoming an authoritative Order. An Invalidation Condition, Portfolio Risk boundary, or Review Condition is not an Action Intent merely because it references a price or trigger; an intended externally maintained control or contingent external consequence may be an Action Intent while the resulting Order remains externally authoritative.

One Action Intent may correspond to zero, one, or multiple external activities, and one authoritative external activity may contribute to zero, one, or multiple Action Intents when those causal associations are supported. The same authoritative external fact is not duplicated merely because it relates to several Action Intents or Investment Decisions. Resulting Portfolio State or external activity that happens to match an Action Intent does not by itself establish that the intent caused or was implemented by that activity.

Partial, failed, or absent implementation does not rewrite the historical Action Intent. Changes to execution mechanics that preserve the same intended external consequence do not by themselves require a new Action Intent; a material change to the intended Portfolio consequence requires new attributable human judgment, with existing Investment Decision identity and lifecycle rules determining whether that judgment belongs to the same unresolved decision or a new causally linked decision.

Action Intent does not imply Admissibility, Approval, Mandate compliance, Residual-Risk Acceptance, authorization, or execution authority. External activity does not retroactively create an Action Intent, Human Investment Decision, Proposed Action, Decision Alternative, or Investment Recommendation merely because its economic result happens to match one of those concepts.

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

An external change that only alters Evidence, Portfolio State, available Decision Alternatives, or expected consequences does not constitute External Resolution while the same coherent Decision Need remains. External Resolution is distinct from Deferral, deliberate hold or no-action, Supersession, and cancellation or withdrawal of decision work while the underlying investment choice still exists.

`External` means outside the unresolved investment judgment itself, not necessarily outside Polaris or outside the Portfolio domain. The cause of External Resolution must remain attributable so later reconstruction can distinguish changed circumstances from Polaris Investment Recommendations and Human Investment Decisions.

## Outcome

An **Outcome** is a decision-relative, temporally scoped account of observed consequences relevant to an Investment Decision, grounded in authoritative observed facts without implying causality, decision quality, or finality.

Outcome does not replace the authoritative Portfolio State, market facts, Orders, fills, or other source facts from which it is understood. It may preserve multiple materially distinct consequence dimensions at the same Horizon or as-of point, including economic performance, Exposure, concentration, liquidity, Portfolio Risk, or other decision-relevant consequences. Investment Horizon, metric count, Financial Instrument count, Action Intent count, Order count, or fill count does not determine Outcome identity or representation.

Outcome is distinct from realized P&L alone, Decision Evaluation, causal explanation, implementation fidelity, Backtest results, Investment Simulation results, and modeled counterfactual results. Outcome may be partial, evolving, or insufficiently mature for a particular evaluative question. A later Investment Decision may truncate, redirect, or supersede an earlier realized consequence path; hypothetical continuation after the actual Portfolio path changes is counterfactual rather than observed Outcome.

A Human Investment Decision, Action Intent, or external implementation is not required for every meaningful Outcome observation. Deliberate hold/no-action and External Resolution may still have decision-relevant Outcomes. The same authoritative observed fact may be relevant to Outcomes of multiple Investment Decisions without duplication.

## Decision Evaluation

A **Decision Evaluation** is an attributable, time-specific retrospective judgment assessing one or more Investment Decisions or material components of them against explicit evaluative criteria, using a historically faithful judgment-time basis, later Evidence where relevant, implementation fidelity and observed Outcome where applicable, while preserving Investment Uncertainty, temporal standards, and limits on causal attribution.

A material Decision Evaluation must preserve what is being assessed and the criteria or standards under which the assessment is made. Evaluation target and evaluation criteria are distinct semantic roles but do not by themselves require independent canonical domain concepts. The same target may be strong under one criterion and poor under another, and one Decision Evaluation may assess several targets or criteria while preserving the individual judgments.

A Benchmark may supply one explicit comparator within a Decision Evaluation without becoming the complete evaluation basis. Benchmark outperformance does not establish good decision quality, and underperformance does not establish poor decision quality.

Decision Evaluation distinguishes ex-ante judgment quality given information actually available at the time from ex-post understanding based on later Evidence and Outcome. Later Evidence may correct historical understanding, establish which Investment Assumptions held, or support causal explanation without becoming retroactively available to the earlier judgment. Reasoning quality conditional on available information may differ from Evidence acquisition, data correctness, normalization, provenance, freshness, or readiness quality.

Favorable Outcome does not establish good reasoning, Investment Recommendation quality, human judgment, Governance, or implementation; unfavorable Outcome does not by itself establish that any of those were poor. Decision Evaluation preserves materially distinct evaluation dimensions rather than forcing them into one undifferentiated quality judgment.

Evaluation criteria, Benchmarks, and standards have temporal provenance. A later standard or Benchmark may be used for an explicitly labeled contemporary retrospective assessment, but it must not rewrite what was compliant, admissible, reasonable, or compared against under the basis actually applicable when the historical decision or authority act occurred. A materially new attributable retrospective judgment may create a new Decision Evaluation; mere arrival of new observations does not. Later Decision Evaluations do not rewrite earlier ones.

Counterfactual reasoning, Investment Scenario analysis, Backtesting, or Investment Simulation may inform Decision Evaluation but remain analytical techniques rather than observed Outcome. Material counterfactual analysis preserves its hypothesis, assumptions, method, Horizon, and Investment Uncertainty and must never masquerade as observed Outcome or historical Portfolio State.

## Lesson

A **Lesson** is an attributable, durable, scoped learning proposition derived through one or more Decision Evaluations and supporting Evidence, preserving its proposition, scope, basis, conditions, and Investment Uncertainty so it may inform future decision work without rewriting prior history or acquiring authority it does not possess.

Lesson semantics follow learning role rather than authorship. A Lesson may originate from Polaris, a human, or another attributable evaluative source. One Decision Evaluation may yield zero, one, or multiple Lessons, and one Lesson may synthesize learning from one or multiple Decision Evaluations, including cross-decision Evaluation.

Outcome alone does not create a Lesson. Lesson formation depends on evidentiary strength, mechanism, scope, generalizability, and Investment Uncertainty rather than a fixed number of historical instances. A Lesson remains scoped to the conditions supported by its Evaluation and Evidence and must not silently become a universal investment rule.

Additional Evidence that strengthens or weakens support for an unchanged Lesson proposition need not create a new Lesson. Historical existence of a Lesson is distinct from its current support or applicability. A material change to a Lesson's proposition or scope requires a new attributable, linked Lesson rather than destructive mutation; a later Lesson may refine, challenge, or supersede an earlier Lesson while preserving the earlier Lesson and its historical basis.

A Lesson may inform future Attention, Decision Context, Evidence, investment reasoning, or Policy and Mandate review. Lesson is distinct from Policy, Investment Mandate, Formal Constraint, Approval, and other authority facts; learning may motivate authoritative change but does not itself perform that change. When a Lesson participates in a later judgment, it remains subject to the same Judgment-Time Availability, Investment Relevance, applicability, provenance, freshness, and Evidence-role distinctions as other information.

## Durable Decision Memory

**Durable Decision Memory** is the cross-cutting Polaris responsibility that materially relevant Investment Decision history, provenance, temporal relationships, supported causal relationships, authority relationships, and unresolved ambiguity remain durably attributable and semantically reconstructable through time, independent of any one workflow execution, report, conversation, storage record, or architecture projection.

Durable Decision Memory is a capability, responsibility, and product invariant rather than a separate business entity competing with Investment Decision identity. It spans unresolved, deferred, substantively resolved, Externally Resolved, erroneous, partial, implemented, unimplemented, and later-evaluated decision history.

Durable Decision Memory is distinct from Persistence and from runtime replay. Persistence stores records; Durable Decision Memory requires semantic reconstruction of material domain history and relationships. Semantic reconstruction does not require reproducing every runtime byte or execution step, and runtime replay does not prove that the decision meaning remains reconstructable.

Material canonical facts must not depend on reparsing narrative reports, chat text, or workflow output when the domain requires them to be reconstructed directly. Later corrections, revised understandings, new Evidence, and new evaluations extend or qualify historical understanding rather than destructively rewriting the facts and judgments that actually existed. Unknown, absent, disputed, or unresolved material facts remain represented as such rather than being filled from hindsight.

Linked Investment Decisions preserve separate identities, and Lessons may span Decisions without merging those Decisions. External facts retain their external authority. Durability follows Investment Materiality and the applicable reconstruction contract rather than a requirement to retain every byte forever. Older memory may inform later Attention, Decision Context, Evidence, Lessons, and judgment only under applicable Judgment-Time Availability, Investment Relevance, freshness, and provenance rules; an old Investment Recommendation does not silently reactivate.

Lowercase `decision record` is noncanonical product/representation shorthand for an assembled durable representation or projection of decision history. It is not a first-class `Decision Record` entity. No separate `Decision Memory` or `Decision Record` bounded context or business entity is presently required.
