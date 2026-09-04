# Implementation Semantic Reconciliation

## Purpose

This research record freezes the implementation-semantic reconciliation performed after the Polaris domain model and product terminology were stabilized.

It answers one question:

> Given the frozen domain vocabulary and lifecycle semantics, how should the current implementation concepts be understood before any 0.2.0 requirements or architecture work begins?

This is an **implementation-to-domain mapping**, not an architecture proposal and not an implementation plan. It does not authorize source-code changes, package moves, database migrations, or compatibility decisions.

Canonical domain vocabulary remains owned by `CONTEXT.md`. Relationship reasoning, frozen invariants, scenario fixtures, and the discovery audit trail remain in `docs/product/domain-model.md`. Current implementation reality remains described by code, configuration, tests, accepted ADRs, and applicable `docs/current/` records.

## Status

**Implementation semantic reconciliation: COMPLETE**

The current implementation has been classified sufficiently to proceed to the final domain-discovery Definition-of-Done audit.

No production code was changed during this reconciliation.

## Scope

The reconciliation inspected the implementation areas that materially overlap the frozen investment-domain model, including:

- portfolio state and portfolio application services;
- strategy hypotheses and synthesis;
- risk signals and execution-risk gating;
- trade packaging and portfolio-manager outputs;
- recommendation persistence and recommendation-linked outcomes;
- platform evaluation;
- authority, governance review, and decision-evidence machinery;
- workflow-output contracts and projections;
- LLM/runtime safety evidence;
- market and macro source models;
- backtesting and simulation boundaries.

The classifications below describe **semantic implications**, not necessarily one-for-one future code changes. A single implementation object may require more than one classification because its current responsibilities span multiple canonical concepts.

## Classification vocabulary

- **KEEP** — the current concept's core semantics fit the frozen model and should survive materially intact.
- **RENAME** — useful behavior is present, but the current name conflicts with or obscures canonical meaning.
- **RE-PARENT** — useful behavior belongs to a different semantic or architectural owner than its current domain-facing placement suggests.
- **SPLIT** — one current concept collapses multiple canonical meanings or provenance classes and must not remain one semantic unit.
- **MERGE** — multiple current concepts should become one canonical semantic unit.
- **DEMOTE** — a current concept is useful, but must cease claiming canonical domain status and instead become a score, signal, representation, helper, or input.
- **REMOVE** — the behavior itself has no justified place in the frozen model.

A classification does not prescribe a physical package name or migration sequence.

## Frozen reconciliation map

| Current implementation concept | Primary classification | Canonical semantic target / owner | Frozen finding |
| --- | --- | --- | --- |
| Current `PortfolioState` | **SPLIT + RE-PARENT** | Portfolio State plus externally authoritative account/broker facts | The object is keyed around account identity and mixes broker/account controls such as margin/buying-power facts with derived Portfolio measures. Canonical Portfolio State must be Portfolio-scoped and may compose Position, Allocation, Exposure, liquidity/performance measures, and other Portfolio facts without erasing provenance. |
| Portfolio application services | **KEEP + SPLIT outputs** | External fact acquisition plus deterministic Portfolio analytics | The service boundary is useful. Broker/account facts and deterministic analytics should survive; the semantic split belongs in the resulting state and provenance rather than by deleting the service. |
| `PortfolioStateDecision` | **RENAME + SPLIT** | Portfolio snapshot normalization / derivation | It is deterministic normalization, not an Investment Decision. Its representation payload is architecture-level projection data. Concentration, drawdown, and risk-like features are measures or assessment inputs rather than a substitute for canonical Portfolio Risk. |
| `StrategyHypothesis` family | **KEEP + RENAME + SPLIT** | Investment Hypothesis, Investment Assumption, Invalidation Condition | Supporting/conflicting Evidence, assumptions, invalidation conditions, and perspective provenance are strong matches. `StrategyHypothesis`, `StrategyAssumption`, and `StrategyInvalidationCondition` should not remain competing canonical names. Bare confidence, hypothesis-strength, and directional fields require explicit semantics. Embedded recommendations are analytical implications/candidate ideas until recommendation formation occurs. |
| `StrategySynthesisDecision` | **RENAME + SPLIT** | Primarily Investment View, with qualified Judgment Confidence, Investment Uncertainty, Market Regime, Investment Signal references, risk relationships, and downstream recommendation formation | Synthesis is analytical judgment, not an Investment Decision and not deterministic decision authority. The current aggregate bundles too many distinct canonical roles into one object. |
| `strategy_synthesis_decision_authority()` and similar authority helpers | **KEEP behavior + RE-PARENT + RENAME** | Platform/runtime authority classification | Platform-owned authority metadata is useful and models must not self-declare governance power. The helpers must not imply that analytical synthesis is itself a deterministic investment decision or authority act. |
| `RiskSignalContract` and universal normalized risk fields | **DEMOTE + RENAME + SPLIT** | Method-qualified Risk Scores, Investment Signals, or inputs to Portfolio Risk Assessment | The current contract compresses volatility, drawdown, exposure, composite risk, pressure, stability, regime/bias, and recommendations into universal score surfaces. Canonical Portfolio Risk is multidimensional and Portfolio/Horizon/scenario-relative. A directional score must not be inverted into risk. |
| `ExecutionRiskGuard` | **SPLIT** | Portfolio Risk / assessment inputs, deterministic Policy or Admissibility where genuinely authoritative, Proposed Action shaping, and external broker constraints | The guard currently combines analytical risk, hard-coded thresholds, broker restrictions, sizing adjustment, and `blocked/reduced/scaled/normal` outcomes. Those are not one authority. Generic risk thresholds are not Mandate Formal Constraints unless backed by an authoritative Mandate rule. |
| `TradePackager` / `TradeIntentContract` | **RE-PARENT + RENAME + SPLIT** | Investment Recommendation and/or Proposed Action formation; presentation package | Direction, size, entry/stop/target preferences, and implementation ideas are useful economic judgment. The current pre-human `trade intent` must **not** be renamed to canonical Action Intent: Action Intent exists only after Human Investment Decision and only for an externally observable consequence. A trade package may remain presentation shorthand. |
| `PortfolioManagerAgent.target_allocation` over Bull/Bear/Sideways | **RENAME** | Perspective/hypothesis weights | Bull/Bear/Sideways analytical weights are not Portfolio Allocation because they are not capital buckets. |
| `PortfolioManagerAgent` posture-like output | **RENAME + SPLIT** | Portfolio Posture plus separately owned risk/policy/human-authority effects | `offensive`, `defensive`, `balanced`, and `capital_preservation` are posture-like analytical outputs. They must remain distinct from Allocation and from execution authority. |
| `PortfolioManagerAgent.execution_status = approved / approved_with_caution / restricted / rejected` | **RENAME + SPLIT** | Analytical risk shaping and/or explicit Policy/Admissibility result when a real deterministic rule exists | Hard-coded score thresholds cannot manufacture power-specific human Approval. `approved`/`rejected` labels currently conflate Portfolio Risk, Policy-like gating, Approval, Portfolio Posture, and execution status. |
| `RecommendationRecord` | **KEEP + REFINE/RENAME fields** | Partial persistence representation of Investment Recommendation | Polaris already has durable curated recommendation persistence and explicitly remains decision-support oriented. The concept is therefore not a blank-slate gap. Generic `bias`, `confidence`, `risk_score`, and entry/stop/target payloads require qualification or separation into the canonical recommendation/action/risk concepts they actually represent. |
| `TradeSetupRecord` | **KEEP + RE-PARENT/RENAME** | Candidate Proposed Action / broker-agnostic implementation proposal | A broker-agnostic setup derived from a recommendation is useful, but it is pre-human and therefore not Action Intent. Generic confidence and risk fields need the same qualification discipline as other score surfaces. |
| `RecommendationOutcomeRecord` | **SPLIT + RENAME** | Legacy recommendation-audit observation; future canonical Outcome and Decision Evaluation must be decision-relative | It directly attaches `human_action`, `outcome`, return, and notes to a Recommendation. The frozen lifecycle requires Human Investment Decision identity and separates realized Outcome from retrospective Decision Evaluation. This record is a useful predecessor, not the canonical lifecycle model. |
| `domain/evaluation` and `application/evaluations` | **KEEP + RE-PARENT + RENAME** | AI/model/RAG/workflow-output evaluation | Current targets include RAG answers, morning reports, strategy synthesis, MCP responses, agent tasks, model replacement gates, and similar platform-quality concerns. This is valuable evaluation infrastructure, but it is not canonical Decision Evaluation. |
| `domain/workflow_outputs` / workflow serialization contracts | **RE-PARENT + selective RENAME** | Runtime/projection/serialization contracts | The registry is architecture/runtime machinery rather than investment-domain state. Contract names such as `execution.risk_decision`, `portfolio.allocation_intent`, `strategy.synthesis`, and `trade.recommendation` inherit the semantic corrections in this record. |
| `application/projections/workflow_outputs` | **KEEP** | Architecture-level derived projections | `Projection` is appropriate here because these are derived/runtime representations. The domain cleanup does not require removing architecture vocabulary where it is actually architecture vocabulary. |
| `domain/authority`, `RiskTier`, `RiskAuthorityContract`, source-of-truth/authority classifiers | **KEEP behavior + RE-PARENT + selective RENAME** | Governance/platform authority classification | The mechanics correctly prevent model-declared authority and encode release/governance concerns. They are not investment-domain concepts such as Portfolio Risk, Approval, or Human Investment Decision merely because some names contain `risk`, `authority`, or `decision`. |
| Governance approval lifecycle (`GovernanceReviewTaskRecord`, immutable review decisions, residual-risk acceptance, release gates) | **KEEP + RE-PARENT subject semantics** | Investment Authority Regime support plus platform governance | Human review mechanics are mature and should survive. The deficiency is semantic attachment: current records are primarily attached to generic `AutomatedDecisionSubject` identities and risk-tier/output governance, rather than a canonical Investment Decision and power-specific investment-authority subject where that is the business meaning. |
| `domain/decision_evidence` / `DecisionEvidencePacket` | **KEEP** | Decision-support evidence packaging and reconstruction support | Material claims, evidence references, versions, limitations, uncertainty, retention, and reconstruction support are useful. They support governed judgment but are not the Investment Decision lifecycle itself. |
| `domain/llm` reasoning-trace safety and governed execution evidence | **KEEP + RE-PARENT** | Runtime/model safety and governance evidence | These are legitimate platform concerns. `BaselineRuntimeEvidence` and similar artifacts are runtime provenance evidence, not investment Evidence, Outcome, or Decision Evaluation. |
| Macro source observations and snapshots | **KEEP** | External/normalized Evidence inputs | `MacroIndicatorObservation` and `MacroDataSnapshot` model source observations and normalized macro facts. They should not be promoted to Investment Signals merely because downstream reasoning consumes them. |
| Market source models such as `SP500Data` | **KEEP** | External/normalized market facts | A canonical normalized market-data representation is compatible with the domain model. “Canonical” here means canonical input representation, not canonical investment judgment. |
| Agent/technical/sentiment/risk signal persistence | **KEEP + QUALIFY + DEMOTE where generic** | Investment Signal or method-specific analytical evidence only when semantics are explicit | Signal infrastructure is useful, but `signal`, `score`, `confidence`, `bias`, and `risk` are not interchangeable canonical facts. Each persisted signal must retain subject, method, meaning, horizon/scope, and provenance sufficient to know what it claims. |
| Backtesting runtime, simulated providers, `BacktestPortfolioLedger`, backtest metrics | **KEEP + QUALIFY** | Backtest / Investment Simulation support with explicit simulated provenance | The runtime-native design correctly avoids a second execution engine and live broker placement. Simulated portfolio state, fills, decisions, actions, and outcomes must stay visibly hypothetical. Runtime scenario/assertion mechanics are not automatically canonical Investment Simulation entities merely because they simulate investment behavior. |
| Backtest aliases for `strategy`, packaged `trade intent`, and `execution_risk` | **RENAME with upstream concepts** | Simulated Investment View / Recommendation / Proposed Action / policy-risk outputs as applicable | Backtesting should inherit corrected upstream semantics rather than freeze retired names into its public inspection aliases. |

## Canonical lifecycle coverage and gaps

The classification pass distinguishes **missing first-class lifecycle semantics** from useful predecessor mechanics already in the codebase. “New concept required” below means that no first-class implementation matching the canonical identity was found in the inspected domain/application/persistence inventory; it does **not** claim that Polaris lacks every supporting mechanism.

| Canonical concept | Current coverage | Reconciliation result |
| --- | --- | --- |
| Decision Need | No first-class implementation found | **NEW DOMAIN CONCEPT REQUIRED.** Workflow triggers and analytical opportunities are not enough; the lifecycle needs a durable identity for the need requiring judgment. |
| Investment Hypothesis | Strong predecessor in `StrategyHypothesis` | **RENAME/REFINE**, not new from scratch. |
| Investment View | Strong predecessor inside `StrategySynthesisDecision` | **RENAME + SPLIT**, not new from scratch. |
| Judgment Confidence | Multiple generic `confidence` fields exist | **NEW canonical semantic contract required; existing fields must be classified rather than mass-renamed.** Model probability, setup quality, evidence strength, and judgment confidence are not interchangeable. |
| Investment Uncertainty | Partial synthesis fields exist | **REFINE/EXTRACT** into an explicit analytical concept. |
| Investment Signal | Many signal-like outputs exist | **QUALIFY/CONSOLIDATE semantics**, not blank-slate functionality. Only outputs satisfying the canonical meaning should carry the canonical term. |
| Investment Recommendation | Durable `RecommendationRecord` and recommendation persistence exist | **REFINE/RE-PARENT representation.** The recommendation concept exists partially, but it currently bundles generic score/risk/action fields and lacks the complete canonical lifecycle relationships. |
| Proposed Action | Trade packaging and `TradeSetupRecord` are partial predecessors | **NEW first-class canonical identity required, using existing proposal/setup behavior as input.** It remains pre-human and distinct from Action Intent. |
| Investment Decision | No first-class canonical implementation found | **NEW DOMAIN CONCEPT REQUIRED.** `StrategySynthesisDecision`, deterministic normalization decisions, policy decisions, and governance audit decisions must not substitute for it. |
| Human Investment Decision | Human governance review exists, but not as canonical investment-decision resolution | **NEW canonical lifecycle representation required, reusing governance mechanics where appropriate.** Human review/approval is not automatically the human investment judgment. |
| Approval | Mature generic governance approval mechanics exist | **RE-PARENT/RE-BIND, not a new generic approval engine.** Power-specific Approval must be tied to the correct investment authority, subject, evidence version, and lifecycle act rather than inferred from score thresholds. |
| Action Intent | No post-human canonical implementation found; existing `TradeIntentContract` is pre-human | **NEW DOMAIN CONCEPT REQUIRED.** Do not migrate the old name mechanically. Deferral/hold/no-action may produce zero Action Intents. |
| Outcome | `RecommendationOutcomeRecord` is a partial audit predecessor | **NEW canonical lifecycle concept required + SPLIT predecessor.** Outcome must be causally attributable to the relevant Investment Decision/Action Intent context and remain distinct from evaluation. |
| Decision Evaluation | Current evaluation stack evaluates AI/RAG/workflow quality; recommendation outcome audit is insufficient | **NEW DOMAIN CONCEPT REQUIRED.** Retrospective investment judgment must be attributable to the Investment Decision and observed Outcome(s). |
| Lesson | No first-class implementation found | **NEW DOMAIN CONCEPT REQUIRED.** Lessons may synthesize learning across one or more Investment Decisions rather than being a field on a single evaluation. |
| Durable Decision Memory | Persistence, evidence reconstruction, lineage, recommendation history, governance audit, and backtest records are useful building blocks | **NEW explicit capability/composition required.** The capability is not equivalent to any one current table, workflow run, recommendation bundle, evidence packet, or generic `decision record`. |

## Cross-cutting invariants for future reconciliation work

Any future requirements, architecture, or implementation work derived from this map must preserve these frozen semantic boundaries:

1. **Resolved Investment Decisions are immutable historical judgments.** Unresolved work may resume. Renewed judgment after substantive resolution creates a new causally linked Investment Decision; it does not reopen the resolved one.
2. **Action Intent is post-human.** It exists only after Human Investment Decision and only when an externally observable consequence is intended. Deferral or deliberate hold/no-action does not require a synthetic Action Intent.
3. **Recommendation, Proposed Action, Human Investment Decision, Approval, and Action Intent are distinct.** None is a status field for another.
4. **Portfolio Risk is multidimensional.** A universal scalar risk score, inverse directional score, `risk_bias`, or threshold label cannot become canonical Portfolio Risk by naming convention.
5. **Policy, Formal Constraint, analytical judgment, and human authority are distinct powers.** Deterministic platform rules may determine admissibility; Portfolio Risk may shape judgment; only the proper authority can perform a power-specific Approval, Mandate Exception, Residual-Risk Acceptance, or Human Investment Decision.
6. **External facts retain provenance.** Broker/account restrictions, market data, and macro observations are not transformed into Polaris investment judgment merely because they are normalized into typed models.
7. **Projection remains architecture vocabulary.** Runtime projections and presentation representations may continue using `Projection`; the term is simply not an investment-domain entity.
8. **Simulation never contaminates live history.** Simulated positions, actions, outcomes, and decisions must remain explicitly hypothetical and attributable to a Backtest/Investment Simulation context.
9. **Generic scores require qualification.** `confidence`, `risk_score`, `quality`, `strength`, `bias`, and similar values must identify what they measure before they can be related to canonical concepts.
10. **Governance machinery is not the investment lifecycle.** Existing review, evidence, audit, release, and residual-risk mechanics are reusable infrastructure, but their current generic subjects cannot substitute for Decision Need → Recommendation → Investment Decision → Action Intent → Outcome → Decision Evaluation → Lesson continuity.

## What should survive largely intact

The reconciliation strongly favors reuse over replacement. The following implementation capabilities are materially sound building blocks:

- external provider and normalized market/macro fact acquisition;
- portfolio service acquisition and deterministic analytics;
- hypothesis evidence, assumption, invalidation, and provenance mechanics;
- evidence packet versioning, claim binding, reconstruction, and retention support;
- human governance review durability, attribution, contestability, requested changes, overrides, and residual-risk acceptance;
- runtime/workflow output projection infrastructure;
- platform AI/RAG/model evaluation infrastructure;
- curated recommendation persistence;
- backtest provider substitution, simulated portfolio ledger, metrics, persistence, and reporting;
- runtime/model safety and governance evidence.

The frozen model changes what these mechanisms **mean and own**, not whether all of them should exist.

## No major MERGE or behavioral REMOVE finding

This pass found no major case where two implementation concepts should already be declared one canonical semantic object, and no major capability whose behavior should simply be deleted.

Some **names and claimed semantics must retire**—for example treating strategy synthesis as an Investment Decision, treating pre-human trade packaging as Action Intent, treating Bull/Bear/Sideways weights as Portfolio Allocation, treating score-threshold `approved/rejected` labels as Approval, or treating normalized risk signals as canonical Portfolio Risk. Retiring those meanings does not imply deleting the underlying analytical or governance behavior.

## Future implementation implications — not an architecture plan

The classification implies a safe semantic dependency direction for later work, without choosing packages, schemas, migrations, or ticket structure:

1. establish first-class decision-lifecycle identities and relationships before adapting downstream persistence or UI representations;
2. separate external account/broker facts from canonical Portfolio State while preserving provenance;
3. extract Investment View, confidence/uncertainty, signals, risk relationships, recommendations, and Proposed Actions from the current synthesis/package aggregates;
4. rebind existing governance/evidence mechanisms to the proper lifecycle subjects and power-specific authority acts rather than creating a second governance system;
5. introduce post-human Action Intent only after Human Investment Decision semantics are explicit;
6. model Outcome, Decision Evaluation, Lesson, and Durable Decision Memory as causal retrospective continuity rather than recommendation annotations;
7. then update persistence records, runtime output contracts, projections, reports, and backtest aliases to reflect the corrected semantics.

The exact architecture and migration order remain future work. They must not be inferred from this research record alone.

## Evidence surface inspected

Representative implementation sources inspected during reconciliation include:

- `domain/portfolio/`
- `application/services/portfolio/`
- `domain/strategy/`
- `intelligence/strategy/`
- `domain/risk/`
- `domain/authority/`
- `domain/decision_evidence/`
- `domain/evaluation/`
- `domain/workflow_outputs/`
- `domain/llm/`
- `domain/governed_execution_evidence.py`
- `domain/macro/`
- `domain/market/`
- `domain/execution/`
- `application/governance/`
- `application/decision_evidence/`
- `application/evaluations/`
- `application/projections/workflow_outputs/`
- `application/persistence/recommendations/`
- `core/storage/persistence/recommendations/`
- `core/storage/persistence/governance_audit/`
- `application/services/backtesting/`
- `application/persistence/backtesting/`
- `docs/current/backtesting-simulation-system.md`

Absence findings are intentionally phrased as “no first-class implementation found in the inspected inventory.” Code search and filename inspection are supporting evidence, not proof that no incidental field or string exists anywhere in the repository.

## Reconciliation conclusion

The frozen domain model and the current implementation are **structurally compatible but semantically misaligned in several high-value seams**.

The implementation already contains substantial analytical, evidence, governance, persistence, and simulation machinery. The central deficiency is that those mechanisms grew around workflow/output identities and overloaded terms before the investment-domain lifecycle was made explicit. The next architecture phase should therefore not begin by rewriting Polaris from scratch. It should begin from the frozen semantic map above, preserve good mechanisms, and introduce the missing investment lifecycle as the organizing business model.

This reconciliation is complete. The next permitted step is the **final domain-discovery Definition-of-Done audit**. Only if that audit is green should Polaris move into 0.2.0 requirements/architecture work.
