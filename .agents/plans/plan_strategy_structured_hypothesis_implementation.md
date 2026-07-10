  # Structured-Hypothesis Strategy Architecture Implementation Plan

  ## Summary

  Replace the current disconnected Bull/Bear/Sideways scoring architecture with a deterministic structured-hypothesis pipeline:

  Canonical runtime evidence
      ↓
  StrategyEvidenceBuilder
      ↓
  Shared StrategyEvidenceContext
      ├── BullHypothesisAgent
      ├── BearHypothesisAgent
      ├── SidewaysHypothesisAgent
      └── StrategyPriorWeightingEngine
              ↓
  StrategySynthesisAgent
              ↓
  StrategySynthesisDecision
              ↓
  PortfolioManagerAgent
              ↓
  Report / Persistence / Curated RAG projection

  All three perspective agents will evaluate the same immutable evidence snapshot independently. The synthesis layer will explicitly compare their hypotheses, evidence, assumptions, contradictions, and invalidation conditions.
  Agents will not debate or communicate directly.

  Implementation should proceed one numbered step at a time, with verification and user review before starting the next step.

  ## Cross-Plan Execution Coordination

  This plan depends on `.agents/plans/plan_canonical_curated_record_projection.md`. The two plans must be executed in the following order:

  1. **Start in the canonical projection plan:** execute Projection Steps 1–11, then stop that plan. These steps establish the generic projection contracts, durable jobs, registry, eligibility policy, coordinator, completion subscriber, DI wiring, lineage, and idempotency.
  2. **Switch to this strategy plan:** execute Strategy Steps 1–20. This stabilizes the final strategy runtime contracts and creates the first-class strategy persistence schema before any strategy projector is written.
  3. **Switch back to the projection plan:** execute Projection Steps 12–15. Strategy output normalization remains governed by this plan and must not be implemented as a generic legacy payload.
  4. **Execute the coordinated projection stage:** execute Projection Steps 16–17 together with Strategy Step 21. This is one implementation stage, not three competing implementations. Check off all applicable steps when the canonical strategy projectors and downstream recommendation mappings pass verification.
  5. **Return to this strategy plan:** execute Strategy Steps 22–25 for RAG projection, graph relationships, cleanup, and architecture documentation.
  6. **Return to the projection plan:** execute Projection Steps 18–28 for portfolio projection, operational support, integration coverage, compatibility verification, quality gates, and final persistence documentation.
  7. **Finish in this strategy plan:** execute Strategy Steps 26–27 as the final focused strategy regression and architecture-health gate.

  Ownership rules:

  - The canonical projection plan exclusively owns projection jobs, registry, eligibility, orchestration, retries, workflow-completion subscription, generic lineage, and idempotency.
  - This strategy plan exclusively owns strategy evidence, hypotheses, synthesis decisions, strategy persistence records, and strategy-specific mapping rules.
  - Strategy Step 21 extends the canonical projection infrastructure. It must not create a second coordinator, subscriber, job table, registry, retry system, or idempotency mechanism.
  - If the plans conflict, the structured strategy contracts in this plan govern strategy payloads, while the canonical projection plan governs projection infrastructure and lifecycle behavior.

  ## Canonical Contracts and Behavioral Decisions

  ### Strategy evidence

  Introduce an immutable StrategyEvidenceContext containing the normalized evidence needed by every perspective:

  - technical trend, momentum, volatility, breadth, and regime
  - macro and market context
  - fundamental signals
  - news and sentiment signals
  - portfolio state and constraints
  - aggregate risk findings
  - relevant market events
  - evidence timestamp and deterministic fingerprint
  - missing-data and data-quality indicators

  StrategyEvidenceBuilder owns normalization. Perspective agents must not independently parse raw runtime dictionaries.

  ### Strategy hypothesis

  Introduce an immutable StrategyHypothesis with:

  - perspective: bull, bear, or sideways
  - thesis
  - directional_bias: -1.0 to 1.0
  - hypothesis_strength: 0.0 to 1.0
  - confidence: 0.0 to 1.0
  - supporting_evidence
  - contradicting_evidence
  - key_assumptions
  - invalidation_conditions
  - risks
  - recommendations
  - data_quality_flags
  - evidence_fingerprint

  Sideways strength must not be represented as positive market direction:

  sideways directional_bias = 0.0
  sideways hypothesis_strength = independently calculated strength

  ### Evidence and invalidation models

  Use typed nested models:

  - StrategyEvidenceItem
  - StrategyAssumption
  - StrategyInvalidationCondition
  - StrategyHypothesisEvaluation
  - StrategySynthesisDecision

  Evidence items identify their source node and field path, observed value, explanatory label, strength, and reliability.

  Invalidation conditions are machine-evaluable and include the source field, comparison operator, threshold, current value, and breached status.

  ### Prior weighting

  Refactor AdaptiveStrategyWeightingEngine into StrategyPriorWeightingEngine.

  It will:

  - produce prior bull, bear, and sideways probabilities
  - operate from the shared evidence context
  - run independently of the three hypotheses
  - preserve full numeric precision
  - avoid using downstream hypothesis outputs or generic graph “votes”

  The existing adaptive name should not be preserved unless the implementation actually learns from historical outcome attribution.

  ### Synthesis adjudication

  For each valid hypothesis:

  contradiction_burden =
      average contradicting evidence strength × reliability

  assumption_support =
      average support score for key assumptions

  candidate_score =
      prior_weight
      × hypothesis_strength
      × confidence
      × assumption_support
      × (1 - contradiction_burden)

  A hypothesis with a breached hard invalidation condition receives a candidate score of zero. Candidate scores are normalized into posterior perspective weights.

  Synthesis then applies existing risk, breadth, volatility, market-event, and portfolio constraints without duplicating evidence already incorporated by the hypotheses.

  The synthesis decision includes:

  - selected perspective and posture
  - directional score
  - confidence and uncertainty
  - execution readiness
  - signal quality
  - prior and posterior perspective weights
  - evaluations of all three hypotheses
  - selected hypothesis
  - decisive evidence
  - unresolved conflicts
  - risks and recommendations
  - evidence fingerprint
  - decision status

  If required evidence or hypotheses are unavailable, synthesis returns an explicit degraded neutral decision with no execution readiness. It must not silently ignore missing hypotheses.

  ## Implementation Steps

  ### Step 1 — Establish the current behavioral baseline

  - Add characterization tests proving that current synthesis output does not change when Bull/Bear/Sideways outputs change.
  - Capture the existing synthesis, portfolio-manager, report, and backtest runtime output shapes.
  - Record current deterministic fixtures for bullish, bearish, and sideways scenarios.

  Verification: Focused characterization tests pass and expose the disconnected-hypothesis defect without changing production behavior.

  ### Step 2 — Add the strategy perspective and scalar contracts

  - Add StrategyPerspective.
  - Add constrained aliases or validation for directional bias, strength, confidence, evidence strength, and reliability.
  - Establish the JSON-compatible scalar type allowed for observed values and invalidation thresholds.

  Verification: Unit tests reject invalid perspectives and out-of-range values.

  ### Step 3 — Add structured evidence contracts

  - Implement immutable StrategyEvidenceItem, StrategyAssumption, and StrategyInvalidationCondition.
  - Implement deterministic serialization and deserialization.
  - Implement invalidation comparison operators without generic executable callbacks.

  Verification: Round-trip, comparison, and validation tests pass.

  ### Step 4 — Add StrategyEvidenceContext

  - Define the shared typed context and its required versus optional evidence.
  - Add deterministic canonical serialization and evidence fingerprint generation.
  - Represent missing inputs explicitly through typed quality flags rather than absent dictionary keys.

  Verification: Equivalent evidence produces the same fingerprint regardless of input mapping order.

  ### Step 5 — Implement the evidence-context normalization policy

  - Extract the existing runtime payload parsing from the three perspective agents.
  - Normalize technical, macro, fundamental, news, sentiment, risk, portfolio, and market-event inputs once.
  - Preserve full internal numeric precision.
  - Do not persist from the normalization policy.

  Verification: Existing bullish, bearish, and sideways fixtures normalize into the expected typed context.

  ### Step 6 — Add StrategyEvidenceBuilder as a runtime node

  - Make the builder consume canonical upstream runtime-node outputs.
  - Retrieve market events through the existing application-service boundary.
  - Return one serialized StrategyEvidenceContext.
  - Wire the node through the existing DI and runtime patterns.

  Verification: Node tests confirm one shared evidence fingerprint and correct degraded behavior when optional evidence is unavailable.

  ### Step 7 — Refactor the Bull agent

  - Replace independent raw-runtime parsing with StrategyEvidenceContext.
  - Move calculations into a deterministic bull-hypothesis policy.
  - Produce a complete StrategyHypothesis.
  - Express opposing evidence and hard invalidation conditions explicitly.

  Verification: Bull fixtures validate evidence, assumptions, invalidations, strength, confidence, and deterministic replay.

  ### Step 8 — Refactor the Bear agent

  - Apply the same contract and policy separation.
  - Make bearish direction negative while keeping hypothesis strength positive.
  - Ensure bullish observations appear as contradicting evidence where applicable.

  Verification: Bear fixtures validate direction, evidence lineage, invalidation behavior, and deterministic replay.

  ### Step 9 — Refactor the Sideways agent

  - Apply the shared hypothesis contract.
  - Separate sideways strength from directional bias.
  - Set canonical sideways directional bias to zero.
  - Model trend breakout and volatility expansion as invalidation conditions.

  Verification: Sideways strength can be high while directional bias remains exactly zero.

  ### Step 10 — Refactor prior weighting

  - Rename AdaptiveStrategyWeightingEngine to StrategyPriorWeightingEngine.
  - Consume StrategyEvidenceContext.
  - Return full-precision typed prior weights that sum to one.
  - Remove generic downstream graph-vote behavior and internal rounding.

  Verification: Prior weights are deterministic, normalized, and independent of hypothesis results.

  ### Step 11 — Add synthesis evaluation contracts

  - Implement StrategyHypothesisEvaluation and StrategySynthesisDecision.
  - Include prior weight, contradiction burden, assumption support, invalidation state, candidate score, posterior weight, rank, and selection status.
  - Add typed degraded-decision reasons.

  Verification: Contract tests cover normalization, all-invalidated hypotheses, ties, and serialization.

  ### Step 12 — Refactor the synthesis policy

  - Make the policy require Bull, Bear, and Sideways hypotheses.
  - Apply the canonical candidate-score formula.
  - Normalize scores into posterior weights.
  - Retain valid existing breadth, risk, market-event, and portfolio constraints as adjudication policies.
  - Compute uncertainty from posterior disagreement and existing market uncertainty.
  - Generate deterministic thesis and decision explanations; do not give an LLM decision authority.

  Verification: Modifying any hypothesis changes its evaluation and can change the selected strategy.

  ### Step 13 — Refactor StrategySynthesisAgent

  - Decode the evidence context, priors, and three hypotheses from runtime outputs.
  - Delegate comparison to the pure synthesis policy.
  - Serialize the typed decision at the runtime boundary.
  - Emit a degraded neutral decision when mandatory inputs are missing.

  Verification: Missing hypotheses cannot be silently skipped, and successful synthesis includes all three evaluations.

  ### Step 14 — Correct the workflow graph

  Change ordering to:

  analytical and risk nodes
      ↓
  StrategyEvidenceBuilder
      ├── StrategyPriorWeightingEngine
      ├── BullHypothesisAgent
      ├── BearHypothesisAgent
      └── SidewaysHypothesisAgent
              ↓
  StrategySynthesisAgent
              ↓
  PortfolioManagerAgent

  - Remove obsolete dependencies between prior weighting and perspective agents.
  - Keep analytical risk upstream of synthesis.
  - Keep ExecutionRiskGuard downstream of portfolio construction and trade packaging.

  Verification: Graph tests assert the exact required dependencies and allow the three hypotheses to execute concurrently.

  ### Step 15 — Update the portfolio manager

  - Consume the selected synthesis decision and posterior weights.
  - Use directional_bias, not hypothesis strength, for allocation direction.
  - Reject execution readiness when synthesis is degraded or materially unresolved.
  - Preserve broker independence.

  Verification: Portfolio intent follows the selected decision and does not treat sideways strength as bullish direction.

  ### Step 16 — Update professional report rendering

  Add structured strategy sections:

  - selected thesis
  - posture and confidence
  - Bull/Bear/Sideways case comparison
  - decisive supporting evidence
  - material contradictory evidence
  - key assumptions
  - invalidation conditions
  - unresolved conflicts
  - risks and execution readiness

  The complete LLM-generated narrative, when present, must remain untruncated.

  Verification: Golden report tests validate organization and complete strategy rationale.

  ### Step 17 — Extend deterministic backtesting verification

  - Add assertion paths for hypotheses, evidence, assumptions, invalidations, priors, posteriors, and selected strategy.
  - Add deterministic bullish, bearish, sideways, conflict, missing-data, and invalidation scenarios.
  - Ensure replaying identical evidence produces byte-equivalent strategy decisions after canonical serialization.

  Verification: Deterministic simulations confirm the expected strategy and explain why it was selected.

  ### Step 18 — Add observability at canonical boundaries

  Record operational events once for:

  - evidence-context construction degradation
  - hypothesis invalidation
  - missing mandatory hypotheses
  - high hypothesis disagreement
  - degraded neutral synthesis
  - synthesis completion and latency

  Use existing runtime-node lifecycle telemetry for normal execution. Do not duplicate it with per-method success logs.

  Verification: Telemetry tests validate trace-correlated degradation and disagreement events without duplicate lifecycle emission.

  ### Step 19 — Add canonical strategy persistence records

  Introduce first-class persistence models for:

  - strategy hypotheses
  - synthesis decisions
  - hypothesis evaluations and decision lineage

  Important scalar fields must be first-class columns. Structured evidence, assumptions, and invalidation collections may use JSONB only at the persistence boundary.

  Runtime nodes and analytical services must not write these records directly.

  Verification: Repository tests round-trip the complete typed records without losing precision or evidence lineage.

  ### Step 20 — Add the database migration

  - Create the new strategy hypothesis, decision, and evaluation tables.
  - Add workflow execution, node, timestamp, symbol, horizon, and evidence-fingerprint indexes.
  - Establish explicit foreign-key lineage between a synthesis decision and its evaluated hypotheses.
  - Do not preserve unused generic strategy columns as compatibility aliases.

  Verification: Alembic single-head, blank-upgrade, downgrade/upgrade, and ORM-divergence tests pass. Notify the user before running PostgreSQL-backed tests.

  ### Step 21 — Add workflow-output projection

  **Execution switch:** Perform this step only during the coordinated stage with Projection Steps 16–17. The generic projection foundation from Projection Steps 1–11 and the strategy contracts/schema from Strategy Steps 1–20 must already be complete.

  - Register the strategy hypothesis and synthesis contracts with the canonical projection registry.
  - Implement strategy-specific projectors through the existing projection coordinator, eligibility policy, durable jobs, lineage helpers, retry behavior, and completion subscriber.
  - Project successful hypothesis node outputs and synthesis output into the new typed persistence records.
  - Make projection idempotent by workflow execution, node, perspective, and evidence fingerprint.
  - Keep runtime evidence and canonical business records conceptually separate.
  - Do not create strategy-owned projection orchestration or persist directly from strategy nodes.

  Verification: Reprojecting a completed workflow creates no duplicate hypotheses or decisions, and the result is visible through the canonical projection job lifecycle.

  ### Step 22 — Extend curated RAG projection

  - Add typed structured-source support for persisted strategy decisions and hypotheses.
  - Make the synthesis decision the primary curated record.
  - Attach the three evaluated hypotheses as attributable related records.
  - Include supporting evidence, contradictions, assumptions, invalidations, and decision lineage.
  - Do not ingest arbitrary raw runtime output or generic metadata.

  Verification: Curated-document tests produce attributable “why,” “why not,” and “what would invalidate this decision” content.

  ### Step 23 — Add graph relationships

  Project explicit relationships such as:

  DECISION_EVALUATED_HYPOTHESIS
  DECISION_SELECTED_HYPOTHESIS
  HYPOTHESIS_SUPPORTED_BY
  HYPOTHESIS_CONTRADICTED_BY
  HYPOTHESIS_INVALIDATED_BY

  Use existing canonical graph-projection services rather than direct Neo4j access from strategy code.

  Verification: Unit-level projection tests validate graph payloads. Notify the user before any live Neo4j test.

  ### Step 24 — Remove obsolete strategy contracts and paths

  - Remove the unused generic StrategySignalResult if the final usage audit confirms no canonical consumer.
  - Remove old dictionary parsers made obsolete by StrategyEvidenceBuilder.
  - Remove renamed adaptive-weighting files and imports rather than adding compatibility wrappers.
  - Remove stale Polaris references from strategy documentation.

  Verification: Dead-code and exact-reference searches find no legacy strategy contract or old engine name.

  ### Step 25 — Document the architectural decision

  Document:

  - structured hypotheses instead of debate
  - shared immutable evidence context
  - no agent-to-agent communication
  - prior versus posterior weighting
  - synthesis as the only hypothesis-comparison authority
  - risk placement before synthesis and execution risk after packaging
  - workflow evidence versus canonical persistence versus RAG projection

  Update the architecture ownership ledger with canonical owners and writers.

  Verification: Documentation and implementation describe the same data lifecycle and ownership boundaries.

  ### Step 26 — Run focused regression verification

  Run focused tests for:
  - all three hypothesis agents
  - evidence builder
  - prior weighting
  - synthesis
  - workflow graph
  - portfolio manager
  - report rendering
  - backtesting
  - telemetry
  - persistence and projection

  Verification: All focused tests pass with no live service dependency unless announced beforehand.

  ### Step 27 — Run final quality and architecture checks

  Run in project-standard order:

  1. Ruff safe fixes and formatting
  2. MyPy
  3. full pytest suite
  4. duplication checks
  5. Repowise health and blast-radius review
  6. dead-code scan
  7. Graphify update

  Resolve newly introduced warnings and errors without broad unrelated cleanup.

  Verification: No new type, lint, test, duplication, architecture, or dead-code regression remains.

  ## Acceptance Criteria

  - Bull, Bear, and Sideways outputs materially influence synthesis.
  - All three perspectives consume the exact same evidence fingerprint.
  - Each perspective produces a typed, attributable, replayable hypothesis.
  - Sideways strength is never interpreted as positive directional bias.
  - Synthesis explicitly evaluates all three hypotheses.
  - Missing hypotheses produce an explicit degraded decision.
  - Identical inputs produce identical hypotheses and synthesis decisions.
  - Portfolio construction consumes posterior decision weights.
  - Reports explain the selected and rejected cases.
  - Strategy persistence has one canonical writer through workflow-output projection.
  - Curated RAG records originate from typed PostgreSQL records, not raw runtime dictionaries.
  - No direct datastore, vendor, or persistence logic is introduced into strategy agents.
  - No compatibility wrapper preserves the obsolete disconnected architecture.

  ## Assumptions and Defaults

  - This plan replaces the current strategy runtime-output contract directly; no legacy result shim will be added.
  - Hypothesis generation and adjudication remain deterministic. LLMs may improve presentation but cannot select or alter the strategy decision.
  - One shared StrategyEvidenceContext is ephemeral runtime decision evidence, not a second durable source of truth.
  - PostgreSQL is the system of record for projected strategy hypotheses and decisions.
  - Synthesis decisions are the primary RAG records; hypotheses provide supporting and competing-case lineage.
  - Live PostgreSQL, Neo4j, Qdrant, or other service-dependent verification will only run after notifying the user that the service is required.

## Step Results

### Step 1 — Establish the current behavioral baseline

Completed:

- Added `tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py` characterization coverage.
- Proved the current `StrategySynthesisAgent` output is unchanged when `bull_agent`, `bear_agent`, and `sideways_agent` runtime outputs are injected and materially changed, exposing the disconnected-hypothesis defect without changing production behavior.
- Captured deterministic current synthesis fixtures for bullish, bearish, and sideways weighting scenarios.
- Captured current runtime output shapes for strategy synthesis and portfolio management.
- Captured current morning-report action-plan rendering shape.
- Captured current backtest result serialization shape with strategy node output embedded in a deterministic backtest step.

Verification:

- `uv run ruff format tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py`
- `uv run ruff check tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py --fix`
- `uv run mypy tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py`
- `uv run pytest -q tests/unit/intelligence/strategy`

Result:

- Focused strategy tests passed: `18 passed`.
- No production behavior was changed.

### Step 2 — Add the strategy perspective and scalar contracts

Completed:

- Added `intelligence/strategy/hypothesis/contracts.py` as the canonical home for structured-hypothesis scalar contracts.
- Added `StrategyPerspective` with the three independent perspectives: `bull`, `bear`, and `sideways`.
- Added constrained validation helpers for directional bias, hypothesis strength, confidence, evidence strength, and evidence reliability.
- Added `StrategyJsonScalar` and validation for JSON-compatible scalar observed values and invalidation thresholds.
- Added package exports through `intelligence/strategy/hypothesis/__init__.py`.
- Added unit tests proving invalid perspectives, out-of-range numeric values, non-finite values, booleans-as-numeric values, and non-scalar evidence values are rejected.

Verification:

- `uv run ruff format intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_strategy_hypothesis_contracts.py`
- `uv run ruff check intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_strategy_hypothesis_contracts.py --fix`
- `uv run mypy intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_strategy_hypothesis_contracts.py --explicit-package-bases`
- `uv run python -m pytest -q tests/unit/intelligence/strategy/test_strategy_hypothesis_contracts.py`
- `uv run python -m pytest -q tests/unit/intelligence/strategy`
- `uv run graphify update .`

Result:

- Focused hypothesis contract tests passed: `54 passed`.
- Full strategy unit test scope passed: `72 passed`.
- Graphify was updated after Python changes.

### Step 3 — Add structured evidence contracts

Completed:

- Added `intelligence/strategy/hypothesis/evidence.py` with immutable typed evidence contracts:
  - `StrategyEvidenceItem`
  - `StrategyAssumption`
  - `StrategyInvalidationCondition`
  - `StrategyInvalidationOperator`
- Added deterministic `to_dict()`, `from_dict()`, and `to_canonical_json()` serialization paths for each evidence contract.
- Added deterministic invalidation comparison operators without executable callbacks or dynamic predicate functions.
- Validated evidence IDs, sources, names, descriptions, scalar observed values, scalar thresholds, perspective values, confidence, strength, reliability, and numeric comparison compatibility.
- Exported the new evidence contracts through `intelligence/strategy/hypothesis/__init__.py`.
- Added focused unit coverage for round trips, canonical JSON stability, immutability, invalid perspectives, invalid scalar values, invalid thresholds, invalid operators, and comparison behavior.

Verification:

- `uv run ruff format intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_strategy_hypothesis_evidence_contracts.py`
- `uv run ruff check intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_strategy_hypothesis_evidence_contracts.py --fix`
- `uv run mypy intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_strategy_hypothesis_contracts.py tests/unit/intelligence/strategy/test_strategy_hypothesis_evidence_contracts.py --explicit-package-bases`
- `uv run python -m pytest -q tests/unit/intelligence/strategy/test_strategy_hypothesis_evidence_contracts.py`
- `uv run python -m pytest -q tests/unit/intelligence/strategy`
- `uv run graphify update .`

Result:

- Focused structured evidence contract tests passed: `14 passed`.
- Full strategy unit test scope passed: `86 passed`.
- Graphify was updated after Python changes.

### Step 4 — Add StrategyEvidenceContext

Completed:

- Added `intelligence/strategy/hypothesis/context.py` with immutable typed shared context contracts:
  - `StrategyEvidenceContext`
  - `StrategyEvidenceInputQuality`
  - `StrategyEvidenceInputStatus`
- Defined required versus optional evidence collections using typed `StrategyEvidenceItem` objects.
- Added explicit input-quality flags for available, degraded, and missing upstream evidence inputs so missing inputs are represented as first-class typed data instead of absent dictionary keys.
- Added deterministic canonical serialization and SHA-256 evidence fingerprint generation.
- Normalized evidence and input-quality ordering during construction so equivalent context payloads produce identical canonical JSON and fingerprints regardless of input order.
- Added helpers for evidence lookup and required-input missing/degraded status detection.
- Exported the new context contracts through `intelligence/strategy/hypothesis/__init__.py`.
- Added focused unit coverage for round trips, fingerprint stability, explicit missing/degraded input flags, duplicate evidence ID rejection, immutability, and missing-reason validation.

Verification:

- `uv run ruff format intelligence/strategy/hypothesis/context.py intelligence/strategy/hypothesis/__init__.py tests/unit/intelligence/strategy/test_strategy_evidence_context.py`
- `uv run ruff check intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_strategy_evidence_context.py --fix`
- `uv run mypy intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_strategy_hypothesis_contracts.py tests/unit/intelligence/strategy/test_strategy_hypothesis_evidence_contracts.py tests/unit/intelligence/strategy/test_strategy_evidence_context.py --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/strategy/test_strategy_evidence_context.py`
- `uv run pytest -q tests/unit/intelligence/strategy`
- `uv run graphify update .`

Result:

- Focused evidence-context tests passed: `6 passed`.
- Full strategy unit test scope passed: `92 passed`.
- Graphify was updated after Python changes.

### Step 5 — Implement the evidence-context normalization policy

Completed:

- Added `intelligence/strategy/hypothesis/normalization.py` as the shared runtime-boundary parsing policy for structured strategy evidence.
- Normalized required `sentiment_agent` and `technical_agent` runtime outputs into typed `StrategyEvidenceItem` records exactly once.
- Normalized optional macro, fundamental, news, risk, portfolio, and market-event inputs into optional typed evidence when present.
- Reused the existing technical breadth extraction helper so canonical breadth fields become typed strategy evidence without reintroducing legacy breadth parsing.
- Added explicit input-quality flags for available, degraded, and missing required/optional inputs.
- Preserved full internal numeric precision; no rounding or persistence behavior was added.
- Exported `normalize_strategy_evidence_context` through `intelligence/strategy/hypothesis/__init__.py`.
- Added focused unit coverage proving bullish, bearish, and sideways fixtures normalize into stable typed contexts with deterministic fingerprints.

Verification:

- `uv run pytest -q tests/unit/intelligence/strategy/test_strategy_evidence_normalization.py`
- `uv run ruff check intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_strategy_evidence_normalization.py --fix`
- `uv run ruff format intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_strategy_evidence_normalization.py`
- `uv run mypy intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_strategy_evidence_normalization.py --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/strategy`
- `uv run graphify update .`

Result:

- Focused evidence-normalization tests passed: `4 passed`.
- Full strategy unit test scope passed: `96 passed`.
- Graphify was updated after Python changes.

### Step 6 — Add StrategyEvidenceBuilder as a runtime node

Completed:

- Added `intelligence/strategy/hypothesis/evidence_builder.py` as the runtime node that builds one shared `StrategyEvidenceContext` from canonical upstream node outputs.
- Retrieved market events through `MarketEventsService` via the existing `ServiceRunner` application-service boundary and propagated runtime telemetry context into the service request.
- Adapted typed `MarketEventsResult` into the normalized market-event evidence shape without adding persistence or a parallel client/provider path.
- Returned a serialized `strategy_evidence_context`, stable `evidence_fingerprint`, required-input status flags, and market-events availability status through `RuntimeNodeOutput`.
- Treated market-events failures as optional degraded evidence so strategy evidence generation can continue with explicit quality flags.
- Wired `StrategyEvidenceBuilder` through `IntelligenceStrategyDIProvider`.
- Added the `strategy_evidence_builder` node to the morning-report workflow after risk aggregation and before the perspective strategy agents.
- Added the evidence-builder dependency to the bull, bear, and sideways strategy agents so later steps can switch those agents to the shared context without changing graph ordering again.

Verification:

- `uv run ruff check intelligence/strategy/hypothesis/evidence_builder.py intelligence/strategy/hypothesis/__init__.py intelligence/strategy/di.py workflows/definitions/reports/morning_report.py tests/unit/intelligence/strategy/test_strategy_evidence_builder.py --fix`
- `uv run ruff format intelligence/strategy/hypothesis/evidence_builder.py intelligence/strategy/hypothesis/__init__.py intelligence/strategy/di.py workflows/definitions/reports/morning_report.py tests/unit/intelligence/strategy/test_strategy_evidence_builder.py`
- `uv run mypy intelligence/strategy/hypothesis intelligence/strategy/di.py workflows/definitions/reports/morning_report.py tests/unit/intelligence/strategy/test_strategy_evidence_builder.py --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/strategy/test_strategy_evidence_builder.py`
- `uv run pytest -q tests/unit/intelligence/strategy`
- `uv run graphify update .`

Result:

- Focused evidence-builder tests passed: `3 passed`.
- Full strategy unit test scope passed: `99 passed`.
- Graphify was updated after Python changes.
- Note: existing `StrategySynthesisAgent` still retrieves market events directly until its later refactor step removes that transitional duplication.
