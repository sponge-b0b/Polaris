# Polaris Domain Glossary

## Recommendation

A **Recommendation** is a Polaris decision-support output that proposes or explains a portfolio-relevant posture, action candidate, or risk response, backed by decision evidence. A Recommendation is not financial advice, human or organizational approval, broker execution intent, or a live order.

Related distinctions:

- A **Strategy Decision** is the selected typed synthesis outcome from structured strategy hypotheses.
- A **Proposed Action** or **Action Candidate** is a concrete candidate action that may later be packaged, resized, deferred, rejected, escalated, or skipped.
- A **Trade Package** is downstream packaging of Proposed Actions for execution-risk review.
- An **Order** is out of scope unless a future broker-execution architecture explicitly introduces it.

## Capital-Relevant Output

A **Capital-Relevant Output** is a Polaris output that could reasonably influence allocation, position sizing, entry or exit timing, hedging, risk acceptance, or portfolio exposure if a human acted on it.

Capital-Relevant Outputs include Recommendations, Proposed Actions, Action Candidates, Trade Packages, risk responses that affect exposure, Strategy Decisions when exposed as guidance, and RAG, report, or tool answers that make readiness-gating claims about portfolio action or risk.

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

For example, "the portfolio is over-concentrated in semiconductors" is a Claim. "Consider trimming NVDA exposure" is both a claim-bearing Recommendation or Proposed Action and a Capital-Relevant Output. Generation timestamps and similar operational metadata are usually not Material Claims.

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

A Strategy Decision does not by itself decide exact order placement, human or organizational Approval, Residual-Risk Acceptance, Publication, Release, broker execution, or final legal, tax, financial, investment, or trading advice. Downstream components may derive Recommendations, Proposed Actions, or Trade Packages from a Strategy Decision, subject to evidence and governance rules.

## Strategy Advisory

A **Strategy Advisory** is a read-only, non-authoritative AI-adjacent interpretation of completed canonical strategy evidence, Strategy Hypotheses, and the resulting Strategy Decision.

A Strategy Advisory may explain or critique the canonical result, surface missing or conflicting Evidence, frame counterarguments or alternative scenarios, narrate qualitative risks, and recommend topics for human review. It does not create or replace Strategy Hypotheses, participate in canonical strategy selection, or alter portfolio, risk, governance, policy, Approval, Release, or execution authority. The canonical strategy lifecycle must produce the same authoritative Strategy Decision whether Strategy Advisory succeeds, fails, is disabled, or does not exist.

## Strategy Advisory Result

A **Strategy Advisory Result** is the typed semantic output of one Strategy Advisory execution.

A Strategy Advisory Result carries advisory availability status and typed status reasons, a code-owned non-authoritative authority marker, code-owned source bindings to the canonical strategy evidence, Strategy Hypotheses, and Strategy Decision actually consumed by the advisory, optional advisory narrative, and structured Strategy Advisory Findings. It does not imply that a durable decision-evidence packet existed when the advisory ran; when the result later becomes a claim-bearing durable or published output, it receives its own decision-evidence packet through the normal evidence lifecycle. It does not carry canonical strategy-selection fields such as directional bias, strategy confidence, candidate scores, synthesis weights, rankings, Allocation, position sizing, eligibility, Approval, or execution action. Runtime and model provenance remain execution metadata rather than advisory semantics.

## Strategy Advisory Finding

A **Strategy Advisory Finding** is one structured, non-authoritative observation within a Strategy Advisory Result. A finding identifies its advisory kind, statement, concise user-facing explanation, the canonical subject it discusses, and the canonical Evidence it references where applicable.

Finding kinds may distinguish critique, counterargument, missing Evidence, scenario analysis, and an advisory recommendation. An **advisory recommendation** recommends what a human may want to investigate or consider; it is not a canonical Recommendation, Proposed Action, Strategy Decision, portfolio instruction, or governance decision.

## Execution Risk

**Execution Risk** is the risk introduced by attempting to carry out a Proposed Action or Trade Package, including timing, liquidity, sizing, slippage, concentration, volatility, operational, and governance risks.

In current Polaris, Execution Risk assessment is decision-support and governance over candidate actions. It is not live broker execution and does not imply an Order exists.

## Portfolio Posture

**Portfolio Posture** is a qualitative or bounded directional stance toward exposure, risk, liquidity, concentration, hedging, or rebalance intent.

## Allocation

**Allocation** is a concrete target or actual distribution of capital across assets, sectors, strategies, accounts, or risk buckets.

A Strategy Decision may express Portfolio Posture. A Recommendation or Proposed Action may suggest movement toward an Allocation, but exact Allocation changes are Capital-Relevant and require applicable evidence, governance, and release handling.

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

A Completed-Run Archive is broad Runtime Evidence. It is not automatically a Curated Record, RAG-eligible source, Projection, Recommendation, Approval, or Source of Truth for every business concept it contains.

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

Risk Scores are not signed directional values. Favorable or risk-on conditions should be represented by lower risk, higher stability, a separate regime label, a Recommendation, or an explicit signed Directional Bias.
