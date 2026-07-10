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
      └── StrategyPerspectiveWeightingEngine
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

  ### Perspective weighting

  Refactor AdaptiveStrategyWeightingEngine into StrategyPerspectiveWeightingEngine.

  It will:

  - produce perspective bull, bear, and sideways probabilities
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
      perspective_weight
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
  - pre-synthesis and posterior perspective weights
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

  ### Step 10 — Refactor perspective weighting

  - Rename AdaptiveStrategyWeightingEngine to StrategyPerspectiveWeightingEngine.
  - Consume StrategyEvidenceContext.
  - Return full-precision typed perspective weights that sum to one.
  - Remove generic downstream graph-vote behavior and internal rounding.

  Verification: Perspective weights are deterministic, normalized, and independent of hypothesis results.

  ### Step 11 — Add synthesis evaluation contracts

  - Implement StrategyHypothesisEvaluation and StrategySynthesisDecision.
  - Include perspective weight, contradiction burden, assumption support, invalidation state, candidate score, posterior weight, rank, and selection status.
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

  - Decode the evidence context, perspective weights, and three hypotheses from runtime outputs.
  - Delegate comparison to the pure synthesis policy.
  - Serialize the typed decision at the runtime boundary.
  - Emit a degraded neutral decision when mandatory inputs are missing.

  Verification: Missing hypotheses cannot be silently skipped, and successful synthesis includes all three evaluations.

  ### Step 14 — Correct the workflow graph

  Change ordering to:

  analytical and risk nodes
      ↓
  StrategyEvidenceBuilder
      ├── StrategyPerspectiveWeightingEngine
      ├── BullHypothesisAgent
      ├── BearHypothesisAgent
      └── SidewaysHypothesisAgent
              ↓
  StrategySynthesisAgent
              ↓
  PortfolioManagerAgent

  - Remove obsolete dependencies between perspective weighting and perspective agents.
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

  - Add assertion paths for hypotheses, evidence, assumptions, invalidations, perspective weights, posteriors, and selected strategy.
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
  - pre-synthesis perspective weighting versus posterior weighting
  - synthesis as the only hypothesis-comparison authority
  - risk placement before synthesis and execution risk after packaging
  - workflow evidence versus canonical persistence versus RAG projection

  Update the architecture ownership ledger with canonical owners and writers.

  Verification: Documentation and implementation describe the same data lifecycle and ownership boundaries.

  ### Step 26 — Run focused regression verification

  Run focused tests for:
  - all three hypothesis agents
  - evidence builder
  - perspective weighting
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

### Step 7 — Refactor the Bull agent

Completed:

- Added `intelligence/strategy/hypothesis/hypothesis.py` with the immutable `StrategyHypothesis` contract for complete perspective-level strategy hypotheses.
- Added `intelligence/strategy/bull/bull_hypothesis_policy.py` as the deterministic bull-hypothesis policy that consumes `StrategyEvidenceContext` instead of raw runtime node-output dictionaries.
- Refactored `BullAgent` so it requires the `strategy_evidence_builder` output and no longer independently parses sentiment, technical, fundamental, news, or risk runtime payloads.
- Preserved the existing bull runtime output shape for downstream compatibility while adding a typed serialized `strategy_hypothesis` payload.
- Modeled supporting evidence, contradicting evidence, explicit key assumptions, hard invalidation conditions, data-quality flags, hypothesis strength, confidence, and evidence fingerprints.
- Updated breadth strategy fixtures so the bull agent is exercised through the shared evidence context while bear and sideways fixtures remain unchanged for their later steps.
- Added focused bull-hypothesis policy coverage for complete output construction, required evidence-builder input, deterministic serialized replay, opposing evidence, hard invalidations, and missing optional-input quality flags.

Verification:

- `uv run ruff check intelligence/strategy/bull intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_bull_hypothesis_policy.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py --fix`
- `uv run ruff format intelligence/strategy/bull intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_bull_hypothesis_policy.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py`
- `uv run mypy intelligence/strategy/bull intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_bull_hypothesis_policy.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/strategy/test_bull_hypothesis_policy.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py`
- `uv run pytest -q tests/unit/intelligence/strategy`
- `uv run graphify update .`

Result:

- Scoped Ruff checks passed.
- Scoped MyPy passed: `Success: no issues found in 12 source files`.
- Focused bull/breadth strategy tests passed: `9 passed`.
- Full strategy unit test scope passed: `104 passed`.
- Graphify was updated after Python changes.
- Repowise identified `intelligence/strategy/bull/bull_agent.py` as a churn-heavy hotspot, so this step kept the refactor surgical and did not modify bear, sideways, or synthesis logic beyond test fixture setup.

### Step 8 — Refactor the Bear agent

Completed:

- Added `intelligence/strategy/bear/bear_hypothesis_policy.py` as the deterministic bear-hypothesis policy that consumes `StrategyEvidenceContext` instead of raw runtime node-output dictionaries.
- Refactored `BearAgent` so it requires the `strategy_evidence_builder` output and no longer independently parses sentiment, technical, fundamental, news, or risk runtime payloads.
- Preserved the existing bear runtime output shape while adding a typed serialized `strategy_hypothesis` payload.
- Modeled bearish direction as negative `directional_score` while keeping `hypothesis_strength` and `features.bear_score` positive.
- Modeled supporting evidence, contradicting bullish evidence, explicit key assumptions, hard invalidation conditions, data-quality flags, confidence, and evidence fingerprints.
- Added focused bear-hypothesis policy coverage for complete output construction, required evidence-builder input, deterministic serialized replay, bullish contradictory evidence, hard invalidations, and missing optional-input quality flags.

Verification:

- `uv run ruff check intelligence/strategy/bear intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_bear_hypothesis_policy.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py --fix`
- `uv run ruff format intelligence/strategy/bear intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_bear_hypothesis_policy.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py`
- `uv run mypy intelligence/strategy/bear intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_bear_hypothesis_policy.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/strategy/test_bear_hypothesis_policy.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py`
- `uv run pytest -q tests/unit/intelligence/strategy`
- `uv run graphify update .`

Result:

- Scoped Ruff checks passed.
- Scoped MyPy passed: `Success: no issues found in 12 source files`.
- Focused bear/breadth strategy tests passed: `9 passed`.
- Full strategy unit test scope passed: `109 passed`.
- Graphify was updated after Python changes.
- Repowise identified `intelligence/strategy/bear/bear_agent.py` as a churn-heavy hotspot, so this step kept the refactor surgical and did not modify sideways or synthesis logic.

### Step 9 — Refactor the Sideways agent

Completed:

- Added `intelligence/strategy/sideways/sideways_hypothesis_policy.py` as the deterministic sideways-hypothesis policy that consumes `StrategyEvidenceContext` instead of raw runtime node-output dictionaries.
- Refactored `SidewaysAgent` so it requires the `strategy_evidence_builder` output and no longer independently parses sentiment, technical, fundamental, news, or risk runtime payloads.
- Preserved the existing sideways runtime output shape while adding a typed serialized `strategy_hypothesis` payload.
- Separated sideways conviction from market direction: `hypothesis_strength` and `features.sideways_score` carry sideways strength, while canonical `directional_score` and `directional_bias` are exactly `0.0`.
- Modeled trend breakout, volatility expansion, sentiment directional breakout, and technical directional breakout as explicit hard invalidation conditions.
- Added focused sideways-hypothesis policy coverage for complete output construction, required evidence-builder input, deterministic serialized replay, breakout invalidations, and missing optional-input quality flags.

Verification:

- `uv run ruff check intelligence/strategy/sideways intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_sideways_hypothesis_policy.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py --fix`
- `uv run ruff format intelligence/strategy/sideways intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_sideways_hypothesis_policy.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py`
- `uv run mypy intelligence/strategy/sideways intelligence/strategy/hypothesis tests/unit/intelligence/strategy/test_sideways_hypothesis_policy.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/strategy/test_sideways_hypothesis_policy.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py`
- `uv run pytest -q tests/unit/intelligence/strategy`
- `uv run graphify update .`

Result:

- Scoped Ruff checks passed.
- Scoped MyPy passed: `Success: no issues found in 12 source files`.
- Focused sideways/breadth strategy tests passed: `9 passed`.
- Full strategy unit test scope passed: `114 passed`.
- Graphify was updated after Python changes.
- Repowise identified `intelligence/strategy/sideways/sideways_agent.py` as a churn-heavy hotspot, so this step kept the refactor surgical and did not modify synthesis or perspective-weighting logic.

### Step 10 — Refactor perspective weighting

Completed:

- Renamed the strategy weighting runtime node from `AdaptiveStrategyWeightingEngine` to `StrategyPerspectiveWeightingEngine` and moved the implementation to `intelligence/strategy/weighting/strategy_perspective_weighting_engine.py`.
- Added the immutable typed `StrategyPerspectiveWeights` contract with full-precision bull, bear, and sideways perspective weights, confidence, evidence fingerprint, and deterministic feature metadata.
- Refactored perspective weighting to consume only `StrategyEvidenceContext` from the `strategy_evidence_builder` output.
- Removed generic graph-vote behavior from the perspective-weighting node; the node now produces pre-hypothesis perspective weights only.
- Preserved full internal precision with no `round()` calls and normalized weights so `bull_weight + bear_weight + sideways_weight == 1.0` within the typed contract tolerance.
- Updated strategy DI, the morning-report workflow graph, and strategy synthesis input validation to use the new `strategy_perspective_weighting_engine` node name.
- Updated the public future-architecture documentation reference from `AdaptiveStrategyWeightingEngine` to `StrategyPerspectiveWeightingEngine`.
- Added deterministic perspective-weighting tests proving normalization, repeatability, evidence-context consumption, independence from hypothesis outputs, and sideways-perspective behavior.

Verification:

- `uv run ruff check intelligence/strategy/weighting intelligence/strategy/di.py workflows/definitions/reports/morning_report.py intelligence/strategy/synthesis/strategy_synthesis_policy.py application/services/market_events/market_events_service.py docs/platform_future_architecture.md tests/unit/intelligence/strategy/test_strategy_perspective_weighting_engine.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/integration/workflow/test_morning_report_real_nodes.py --fix`
- `uv run ruff format intelligence/strategy/weighting intelligence/strategy/di.py workflows/definitions/reports/morning_report.py intelligence/strategy/synthesis/strategy_synthesis_policy.py application/services/market_events/market_events_service.py tests/unit/intelligence/strategy/test_strategy_perspective_weighting_engine.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/integration/workflow/test_morning_report_real_nodes.py`
- `uv run mypy intelligence/strategy/weighting intelligence/strategy/hypothesis intelligence/strategy/di.py workflows/definitions/reports/morning_report.py intelligence/strategy/synthesis/strategy_synthesis_policy.py tests/unit/intelligence/strategy/test_strategy_perspective_weighting_engine.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/integration/workflow/test_morning_report_real_nodes.py --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/strategy/test_strategy_perspective_weighting_engine.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py`
- `uv run pytest -q tests/unit/intelligence/strategy`
- `POLARIS_POSTGRES_USER=placeholder POLARIS_POSTGRES_PASSWORD=placeholder POLARIS_POSTGRES_HOST=localhost POLARIS_POSTGRES_PORT=5432 POLARIS_POSTGRES_DB=placeholder uv run pytest --collect-only -q tests/integration/workflow/test_morning_report_real_nodes.py`
- `uv run graphify update .`

Result:

- Scoped Ruff checks passed.
- Scoped MyPy passed: `Success: no issues found in 16 source files`.
- Focused perspective-weighting and synthesis tests passed: `19 passed`.
- Full strategy unit test scope passed: `119 passed`.
- Integration workflow test collection passed: `2 tests collected`.
- Attempted the full morning-report workflow integration test with placeholder PostgreSQL configuration, but it did not complete after roughly 107 seconds and was interrupted while waiting inside runtime event emission. This appears to be an existing integration/runtime event completion issue rather than a Step 10 perspective-weighting failure; no live-service test was required for this step.
- Graphify was updated after Python changes.

### Step 11 — Add synthesis evaluation contracts

Completed:

- Renamed the Step 10 weighting contract and runtime node from the interim pre-synthesis weighting terminology to `StrategyPerspectiveWeightingEngine` / `StrategyPerspectiveWeights`.
- Updated the runtime node name, workflow dependency, DI binding, synthesis input validation, output contract, tests, and public future-architecture documentation to use `strategy_perspective_weighting_engine` and `strategy_perspective_weights`.
- Renamed the Dishka provider method to `provide_perspective_weighting_agent` so production names consistently describe perspective weighting rather than generic weighting.
- Added `intelligence/strategy/synthesis/contracts.py` with immutable typed `StrategyHypothesisEvaluation` and `StrategySynthesisDecision` contracts.
- Added typed `StrategySynthesisSelectionStatus` and `StrategySynthesisDegradedReason` enums for selected, rejected, invalidated, tied, and degraded decisions.
- Added deterministic evaluation normalization that ranks candidates, assigns posterior weights, handles all-invalidated candidates, and marks tied top candidates as degraded.
- Renamed the existing runtime synthesis policy output class to `_RuntimeStrategySynthesisOutput` so the new canonical `StrategySynthesisDecision` contract can be introduced without changing Step 12 synthesis behavior early.
- Added focused contract tests for posterior normalization, all-invalidated decisions, tied candidates, and deterministic serialization/replay.

Verification:

- `uv run ruff check intelligence/strategy/weighting intelligence/strategy/synthesis intelligence/strategy/di.py workflows/definitions/reports/morning_report.py application/services/market_events/market_events_service.py docs/platform_future_architecture.md tests/unit/intelligence/strategy/test_strategy_perspective_weighting_engine.py tests/unit/intelligence/strategy/test_strategy_synthesis_contracts.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/integration/workflow/test_morning_report_real_nodes.py --fix`
- `uv run ruff format intelligence/strategy/weighting intelligence/strategy/synthesis intelligence/strategy/di.py workflows/definitions/reports/morning_report.py intelligence/strategy/synthesis/strategy_synthesis_policy.py application/services/market_events/market_events_service.py tests/unit/intelligence/strategy/test_strategy_perspective_weighting_engine.py tests/unit/intelligence/strategy/test_strategy_synthesis_contracts.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/integration/workflow/test_morning_report_real_nodes.py`
- `uv run mypy intelligence/strategy/weighting intelligence/strategy/synthesis intelligence/strategy/hypothesis intelligence/strategy/di.py workflows/definitions/reports/morning_report.py tests/unit/intelligence/strategy/test_strategy_perspective_weighting_engine.py tests/unit/intelligence/strategy/test_strategy_synthesis_contracts.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/integration/workflow/test_morning_report_real_nodes.py --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/strategy/test_strategy_synthesis_contracts.py tests/unit/intelligence/strategy/test_strategy_perspective_weighting_engine.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py`
- `uv run pytest -q tests/unit/intelligence/strategy`
- `uv run graphify update .`

Result:

- Scoped Ruff checks passed.
- Scoped MyPy passed: `Success: no issues found in 20 source files`.
- Focused synthesis/weighting/baseline/gating tests passed: `23 passed`.
- Full strategy unit test scope passed: `123 passed`.
- Graphify was updated after Python changes.
- Repowise identified `intelligence/strategy/synthesis/strategy_synthesis_policy.py` as a churn-heavy hotspot, so this step introduced the canonical contracts in a separate module and limited policy changes to a safe class rename only.

### Step 12 — Refactor the synthesis policy

Completed:

- Refactored `StrategySynthesisInputs.from_runtime_payloads()` so strategy synthesis now requires typed serialized `strategy_hypothesis` payloads from `bull_agent`, `bear_agent`, and `sideways_agent` in addition to the canonical `strategy_perspective_weighting_engine` output.
- Added pure synthesis evaluation helpers that compute each hypothesis candidate score from the canonical formula: perspective weight × hypothesis strength × confidence × assumption support × `(1 - contradiction burden)`, with invalidated hypotheses receiving a zero candidate score.
- Normalized hypothesis candidate scores into posterior weights and used those posterior weights as the base synthesis weights before the existing market-event, risk, portfolio, and breadth adjudication policies are applied.
- Added posterior-disagreement uncertainty to the existing market uncertainty calculation so conflicting or diffuse hypotheses reduce confidence deterministically.
- Added deterministic thesis, selected perspective, selection status, degraded reasons, candidate scores, posterior weights, selected hypothesis, and full `StrategySynthesisDecision` details into synthesis features.
- Updated synthesis tests so mutating a Bull/Bear/Sideways hypothesis now changes synthesis evaluation and can change the selected strategy.
- Updated breadth-gating and structured-baseline tests to include required typed hypothesis payloads and to assert the new hypothesis-driven synthesis feature contract.

Verification:

- `uv run ruff check intelligence/strategy/synthesis tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py --fix`
- `uv run ruff format intelligence/strategy/synthesis tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py`
- `uv run mypy intelligence/strategy tests/unit/intelligence/strategy --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/strategy/test_strategy_synthesis_contracts.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py`
- `uv run pytest -q tests/unit/intelligence/strategy`
- `uv run graphify update .`

Result:

- Scoped Ruff checks passed and formatting completed.
- Scoped MyPy passed: `Success: no issues found in 39 source files`.
- Focused synthesis contract/gating/baseline tests passed: `18 passed`.
- Full strategy unit test scope passed: `123 passed`.
- Graphify was updated after Python changes.
- Repowise identified `intelligence/strategy/synthesis/strategy_synthesis_policy.py` as churn-heavy, so this step kept the refactor limited to the synthesis policy and focused tests; no interface, persistence, or runtime contracts were changed.

### Step 13 — Refactor StrategySynthesisAgent

Completed:

- Moved runtime payload decoding for strategy synthesis out of the pure synthesis policy and into `StrategySynthesisAgent`, so the agent owns the runtime boundary while `synthesize_strategy()` consumes typed `StrategySynthesisInputs`.
- Required decoded runtime outputs from `strategy_perspective_weighting_engine`, `risk_aggregator_agent`, `portfolio_state_builder`, `technical_agent`, `bull_agent`, `bear_agent`, and `sideways_agent`.
- Removed `StrategySynthesisInputs.from_runtime_payloads()` and the policy-level runtime helper functions so mandatory Bull/Bear/Sideways hypotheses cannot be silently skipped by the pure policy.
- Added degraded neutral fallback serialization that emits a typed `StrategySynthesisDecision` with three invalidated Bull/Bear/Sideways evaluations when mandatory inputs are missing.
- Added `intelligence/strategy/market_context.py` for shared symbol-constituent extraction and updated `StrategyEvidenceBuilder` plus `StrategySynthesisAgent` to use it, removing an inappropriate evidence-builder dependency on synthesis policy and fixing a circular import uncovered by Step 13 tests.
- Expanded synthesis tests to assert missing upstream inputs and missing hypotheses produce a degraded neutral decision with all three evaluations serialized at the runtime boundary.

Verification:

- `uv run ruff check intelligence/strategy/market_context.py intelligence/strategy/synthesis/strategy_synthesis_agent.py intelligence/strategy/synthesis/strategy_synthesis_policy.py intelligence/strategy/hypothesis/evidence_builder.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py --fix`
- `uv run ruff format intelligence/strategy/market_context.py intelligence/strategy/synthesis/strategy_synthesis_agent.py intelligence/strategy/synthesis/strategy_synthesis_policy.py intelligence/strategy/hypothesis/evidence_builder.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py`
- `uv run pytest -q tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py tests/unit/intelligence/strategy/test_strategy_synthesis_contracts.py`
- `uv run mypy intelligence/strategy tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py tests/unit/intelligence/strategy/test_strategy_synthesis_contracts.py --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/strategy`
- `grep -R "from_runtime_payloads" -n intelligence tests application workflows --exclude-dir=__pycache__`
- `uv run graphify update .`
- `git diff --check`

Result:

- Ruff checks and formatting passed.
- Focused synthesis tests passed: `19 passed`.
- Scoped MyPy passed: `Success: no issues found in 30 source files`.
- Full strategy unit test scope passed: `124 passed`.
- No source or test usages of `from_runtime_payloads` remain.
- Graphify was updated after Python changes.
- `git diff --check` passed.
- Initial focused test execution exposed a circular import caused by `StrategyEvidenceBuilder` importing shared market-context behavior from synthesis policy. This was fixed by moving the shared helper to `intelligence/strategy/market_context.py`.
- No live services were required.

### Step 14 — Correct the workflow graph

Completed:

- Updated `MorningReportWorkflow` so `strategy_perspective_weighting_engine`, `bull_agent`, `bear_agent`, and `sideways_agent` are sibling nodes that depend only on `strategy_evidence_builder`.
- Removed obsolete `strategy_perspective_weighting_engine` and direct `risk_aggregator_agent` dependencies from the Bull, Bear, and Sideways hypothesis agents; risk evidence remains upstream through `strategy_evidence_builder`.
- Preserved `strategy_synthesis_agent` as the single downstream comparison authority requiring all three hypotheses, the perspective weights, portfolio state, risk aggregation, and technical context.
- Preserved downstream portfolio and execution ordering: `portfolio_manager_agent` after synthesis, `trade_packager` after portfolio construction, and `execution_risk_guard` after trade packaging plus risk aggregation.
- Strengthened workflow graph tests to assert exact strategy evidence, concurrent hypothesis/weighting, synthesis, portfolio, trade packaging, and execution guard dependencies.

Verification:

- `uv run ruff check workflows/definitions/reports/morning_report.py tests/unit/intelligence/strategy/test_strategy_evidence_builder.py --fix`
- `uv run ruff format workflows/definitions/reports/morning_report.py tests/unit/intelligence/strategy/test_strategy_evidence_builder.py`
- `uv run pytest -q tests/unit/intelligence/strategy/test_strategy_evidence_builder.py`
- `uv run mypy workflows/definitions/reports/morning_report.py tests/unit/intelligence/strategy/test_strategy_evidence_builder.py --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/strategy`
- `POLARIS_POSTGRES_USER=placeholder POLARIS_POSTGRES_PASSWORD=placeholder POLARIS_POSTGRES_HOST=localhost POLARIS_POSTGRES_PORT=5432 POLARIS_POSTGRES_DB=placeholder uv run pytest --collect-only -q tests/integration/workflow/test_morning_report_real_nodes.py`
- `POLARIS_POSTGRES_USER=placeholder POLARIS_POSTGRES_PASSWORD=placeholder POLARIS_POSTGRES_HOST=localhost POLARIS_POSTGRES_PORT=5432 POLARIS_POSTGRES_DB=placeholder uv run python - <<'PY' ... PY` to inspect the live `MorningReportWorkflow().build_graph()` dependencies.
- `uv run graphify update .`
- `git diff --check`

Result:

- Scoped Ruff checks and formatting passed.
- Focused strategy evidence/workflow graph tests passed: `5 passed`.
- Scoped MyPy passed: `Success: no issues found in 2 source files`.
- Full strategy unit test scope passed: `126 passed`.
- Morning-report workflow integration test collection passed: `2 tests collected`.
- Direct workflow graph inspection confirmed the four post-evidence strategy nodes share the exact `("strategy_evidence_builder",)` dependency and can execute concurrently after evidence construction.
- Graphify was updated after Python changes.
- `git diff --check` passed.
- No live services were required.

### Step 15 — Update the portfolio manager

Completed:

- Updated `PortfolioManagerAgent` to require and deserialize the canonical `strategy_synthesis_decision` emitted by `StrategySynthesisAgent` instead of treating legacy Bull/Bear/Sideways weights as the portfolio decision contract.
- Changed portfolio target allocation to use posterior weights from the selected synthesis decision evaluations.
- Changed portfolio directional intent to use the selected synthesis decision `directional_score`, preserving sideways neutrality even when a sideways hypothesis has high posterior strength.
- Added synthesis readiness gating so degraded, unresolved, unselected, or reason-bearing synthesis decisions force portfolio execution status to `rejected` and scale factor to `0.0`.
- Added first-class portfolio output features for selected perspective, selection status, degraded reasons, posterior weights, and synthesis execution blocking.
- Removed remaining `round()` usage from the touched portfolio manager output path so internal precision is preserved.
- Preserved broker independence; the portfolio manager still consumes runtime node outputs only and does not call providers, clients, or broker APIs.
- Expanded portfolio-manager tests to cover account restrictions, selected-decision precedence over legacy synthesis fields, sideways neutrality, and degraded synthesis rejection.
- Updated the structured-hypothesis baseline fixture to include the required canonical synthesis decision payload and expected portfolio feature shape.

Verification:

- `uv run ruff check intelligence/portfolio/management/portfolio_manager_agent.py tests/unit/intelligence/portfolio/test_portfolio_manager_agent.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py --fix`
- `uv run ruff format intelligence/portfolio/management/portfolio_manager_agent.py tests/unit/intelligence/portfolio/test_portfolio_manager_agent.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py`
- `uv run mypy intelligence/portfolio/management/portfolio_manager_agent.py tests/unit/intelligence/portfolio/test_portfolio_manager_agent.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/portfolio/test_portfolio_manager_agent.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py`
- `uv run mypy . --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/strategy tests/unit/intelligence/portfolio/test_portfolio_manager_agent.py`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run graphify update .`

Result:

- Scoped Ruff checks and formatting passed.
- Scoped MyPy passed: `Success: no issues found in 3 source files`.
- Focused portfolio/structured-baseline tests passed: `10 passed`.
- Full project MyPy passed: `Success: no issues found in 1188 source files`.
- Strategy unit tests plus the portfolio manager tests passed: `129 passed`.
- Full Ruff check and format check passed.
- Graphify was updated after Python changes.
- A broader `tests/unit/intelligence/portfolio` collection attempt was intentionally not used as a Step 15 gate because unrelated `test_portfolio_state_builder.py` collection requires database configuration and fails when `POLARIS_DATABASE_URL` or PostgreSQL component variables are unset.
- No live services were required for the completed Step 15 verification.

### Step 16 — Update professional report rendering

Completed:

- Extended the morning report recommended action plan with structured strategy synthesis content sourced from the canonical `strategy_synthesis_decision` and `selected_hypothesis` payloads.
- Added first-class report metrics for selected strategy, synthesis status, and synthesis confidence while preserving existing posture, portfolio, trade, guard, scale, quality, and readiness metrics.
- Added a Bull/Bear/Sideways strategy case-comparison table showing posterior weight, candidate score, rank, and selection status for each hypothesis case.
- Added labeled report bullets for selected thesis, posture/confidence, decisive supporting evidence, material contradictory evidence, key assumptions, invalidation conditions, unresolved conflicts, and risks/execution readiness.
- Preserved the complete strategy LLM narrative when present by carrying it into the typed report and adjusting Markdown bullet rendering so narrative text is not truncated or whitespace-collapsed.
- Expanded assembler and renderer tests to validate the structured strategy rationale, case-comparison rows, and complete untruncated strategy narrative.
- Updated the structured-hypothesis baseline report-shape test to reflect the new professional strategy metrics.

Verification:

- `uv run ruff check application/reports/morning_report_assembler.py tests/unit/application/reports/morning/test_morning_report_assembler.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py --fix`
- `uv run ruff format application/reports/morning_report_assembler.py tests/unit/application/reports/morning/test_morning_report_assembler.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py`
- `uv run pytest -q tests/unit/application/reports/morning/test_morning_report_assembler.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py`
- `uv run ruff check application/reports/morning_report_renderer.py tests/unit/application/reports/morning/test_morning_report_renderer.py --fix`
- `uv run ruff format application/reports/morning_report_renderer.py tests/unit/application/reports/morning/test_morning_report_renderer.py`
- `uv run pytest -q tests/unit/application/reports/morning/test_morning_report_assembler.py tests/unit/application/reports/morning/test_morning_report_renderer.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py`
- `uv run mypy application/reports/morning_report_assembler.py application/reports/morning_report_renderer.py tests/unit/application/reports/morning/test_morning_report_assembler.py tests/unit/application/reports/morning/test_morning_report_renderer.py tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py --explicit-package-bases`
- `uv run pytest -q tests/unit/application/reports/morning tests/unit/interfaces/cli/output/test_workflow_output_renderer.py tests/unit/interfaces/cli/output/test_pdf_output_renderer.py tests/unit/intelligence/strategy`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy . --explicit-package-bases`
- `uv run graphify update .`

Result:

- Focused Ruff checks and formatting passed.
- Focused assembler, renderer, and structured-baseline tests passed: `11 passed`.
- Scoped MyPy passed: `Success: no issues found in 5 source files`.
- Broader report, CLI output, PDF output, and strategy unit scopes passed: `144 passed`.
- Full project Ruff check and format check passed.
- Full project MyPy passed: `Success: no issues found in 1188 source files`.
- Graphify was updated after Python changes.
- Repowise identified `application/reports/morning_report_assembler.py` as a churn-heavy hotspot, so this step stayed within the report assembler/renderer boundary and focused tests rather than refactoring adjacent persistence, RAG, or CLI output layers.
- No live services were required.

### Step 17 — Extend deterministic backtesting verification

Completed:

- Expanded the deterministic backtesting golden fixture so `strategy_synthesis_agent` emits the canonical structured-hypothesis payload used by downstream runtime consumers.
- Added deterministic verification assertions for strategy synthesis decisions, selected perspective, selection status, hypothesis evaluations, posterior weights, candidate scores, selected hypothesis evidence, contradictory evidence, assumptions, and invalidation conditions.
- Added deterministic scenario coverage for bullish, bearish, sideways, conflict, missing-data, and invalidation cases.
- Added replay assertions that compare canonical JSON serialization of the strategy decision across repeated deterministic workflow executions.
- Kept the change test-focused; no production runtime, service, provider, or persistence code was changed for this step.

Verification:

- `POLARIS_POSTGRES_PASSWORD=placeholder UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/backtesting/test_backtest_verification.py`
- `uv run ruff check tests/unit/application/services/backtesting/test_backtest_verification.py --fix`
- `uv run ruff format tests/unit/application/services/backtesting/test_backtest_verification.py`
- `POLARIS_POSTGRES_PASSWORD=placeholder UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/backtesting/test_backtest_verification.py`
- `POLARIS_POSTGRES_PASSWORD=placeholder UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/backtesting`
- `uv run mypy tests/unit/application/services/backtesting/test_backtest_verification.py --explicit-package-bases`
- `POLARIS_POSTGRES_PASSWORD=placeholder UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/backtesting tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py`
- `uv run graphify update .`
- `git diff --check`

Result:

- Focused deterministic backtesting verification tests passed: `9 passed`.
- Full backtesting service unit scope passed: `24 passed`.
- Backtesting plus structured-hypothesis baseline tests passed: `31 passed`.
- Scoped MyPy passed: `Success: no issues found in 1 source file`.
- Ruff check and formatting passed for the changed test file.
- Graphify was updated after Python changes.
- `git diff --check` passed.
- No live services were required. The test collection imports PostgreSQL settings, so verification used a non-secret placeholder PostgreSQL password environment variable without opening a database connection.

### Step 18 — Add observability at canonical boundaries

Completed:

- Added canonical intelligence telemetry emission for strategy evidence-context degradation in `StrategyEvidenceBuilder`.
- Wired `StrategyEvidenceBuilder` through DI with the existing `IntelligenceTelemetry` emitter instead of introducing a new telemetry system.
- Added one-shot strategy synthesis operational telemetry for hypothesis invalidation, missing mandatory hypotheses, high hypothesis disagreement, degraded neutral synthesis, and synthesis completion latency.
- Preserved runtime-node lifecycle telemetry as the normal execution source of truth; the new events are cause-specific operational/degradation signals only.
- Preserved existing low-confidence, data-quality, and fallback telemetry while adding the Step 18 canonical event coverage.
- Added trace-correlated tests for synthesis completion and high-disagreement events.
- Added tests for evidence-context degradation telemetry, missing mandatory hypothesis telemetry, degraded neutral fallback telemetry, and hypothesis invalidation telemetry.

Verification:

- `uv run ruff check intelligence/strategy/hypothesis/evidence_builder.py intelligence/strategy/di.py intelligence/strategy/synthesis/strategy_synthesis_agent.py tests/unit/intelligence/strategy/test_strategy_evidence_builder.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py --fix`
- `uv run ruff format intelligence/strategy/hypothesis/evidence_builder.py intelligence/strategy/di.py intelligence/strategy/synthesis/strategy_synthesis_agent.py tests/unit/intelligence/strategy/test_strategy_evidence_builder.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py`
- `uv run pytest -q tests/unit/intelligence/strategy/test_strategy_evidence_builder.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py`
- `uv run mypy intelligence/strategy/hypothesis/evidence_builder.py intelligence/strategy/di.py intelligence/strategy/synthesis/strategy_synthesis_agent.py tests/unit/intelligence/strategy/test_strategy_evidence_builder.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py --explicit-package-bases`
- `uv run pytest -q tests/unit/intelligence/strategy`
- `uv run ruff check . --fix`
- `uv run ruff format .`
- `uv run mypy . --explicit-package-bases`
- `uv run graphify update .`
- `git diff --check`

Result:

- Focused evidence/synthesis telemetry tests passed: `15 passed`.
- Full strategy unit test scope passed: `128 passed`.
- Scoped MyPy passed: `Success: no issues found in 5 source files`.
- Full project MyPy passed: `Success: no issues found in 1188 source files`.
- Full project Ruff check and formatting passed.
- Graphify was updated after Python changes.
- `git diff --check` passed.
- No live services were required.

### Step 19 — Add canonical strategy persistence records

Completed:

- Added first-class SQLAlchemy models for strategy hypotheses, synthesis decisions, and hypothesis evaluations in `core/database/models/strategy.py`.
- Added canonical typed persistence records, bundle/result contracts, deterministic ID helpers, and a repository protocol under `core/storage/persistence/strategy/`.
- Added a PostgreSQL repository adapter and serializer that keep strategy internals typed and serialize structured evidence, assumptions, invalidations, degraded reasons, and metadata only at the persistence boundary.
- Added an application-layer `StrategyPersistenceService` with typed filters for hypotheses, decisions, and evaluation lineage.
- Updated persistence/model exports so the new strategy persistence boundary is discoverable without exporting repository or model infrastructure through the application boundary.
- Added focused tests covering immutable typed records, ID generation, serialization round trips, repository idempotent upserts/rollback/listing/bundle reads, application service filters, and persistence export contracts.
- Did not add direct writes from runtime nodes or analytical services; workflow-output projection remains deferred to Step 21.
- Did not add Alembic migrations or run PostgreSQL-backed tests; schema migration work remains deferred to Step 20.

Verification:

- `uv run ruff check core/database/models/strategy.py core/storage/persistence/strategy core/storage/persistence/serializers/strategy_persistence_serializer.py core/storage/persistence/repositories/postgres_strategy_persistence_repository.py application/persistence/strategy tests/unit/core/storage/persistence/test_strategy_persistence_contracts.py tests/unit/core/storage/persistence/test_strategy_persistence_serializer.py tests/unit/core/storage/persistence/test_postgres_strategy_persistence_repository.py tests/unit/core/storage/persistence/strategy_fixtures.py tests/unit/application/persistence/strategy/test_strategy_persistence_service.py --fix`
- `uv run ruff format core/database/models/strategy.py core/storage/persistence/strategy core/storage/persistence/serializers/strategy_persistence_serializer.py core/storage/persistence/repositories/postgres_strategy_persistence_repository.py application/persistence/strategy tests/unit/core/storage/persistence/test_strategy_persistence_contracts.py tests/unit/core/storage/persistence/test_strategy_persistence_serializer.py tests/unit/core/storage/persistence/test_postgres_strategy_persistence_repository.py tests/unit/core/storage/persistence/strategy_fixtures.py tests/unit/application/persistence/strategy/test_strategy_persistence_service.py`
- `uv run pytest -q tests/unit/core/storage/persistence/test_strategy_persistence_contracts.py tests/unit/core/storage/persistence/test_strategy_persistence_serializer.py tests/unit/core/storage/persistence/test_postgres_strategy_persistence_repository.py tests/unit/application/persistence/strategy/test_strategy_persistence_service.py tests/unit/application/persistence/test_application_persistence_exports.py`
- `uv run mypy core/database/models/strategy.py core/storage/persistence/strategy core/storage/persistence/serializers/strategy_persistence_serializer.py core/storage/persistence/repositories/postgres_strategy_persistence_repository.py application/persistence/strategy tests/unit/core/storage/persistence/test_strategy_persistence_contracts.py tests/unit/core/storage/persistence/test_strategy_persistence_serializer.py tests/unit/core/storage/persistence/test_postgres_strategy_persistence_repository.py tests/unit/core/storage/persistence/strategy_fixtures.py tests/unit/application/persistence/strategy/test_strategy_persistence_service.py --explicit-package-bases`
- `uv run ruff check . --fix`
- `uv run ruff format .`
- `uv run mypy . --explicit-package-bases`
- `uv run graphify update .`
- `git diff --check`

Result:

- Focused strategy persistence unit tests passed: `27 passed`.
- Scoped MyPy passed: `Success: no issues found in 13 source files`.
- Full project Ruff check and formatting passed.
- Full project MyPy passed: `Success: no issues found in 1201 source files`.
- Graphify was updated after Python changes.
- `git diff --check` passed.
- No live services were required for Step 19. PostgreSQL-backed migration verification is intentionally deferred to Step 20.

### Step 20 — Add the database migration

Completed:

- Added Alembic revision `f2a3b4c5d6e7` for the canonical strategy persistence schema.
- Created the `strategy_hypotheses`, `strategy_synthesis_decisions`, and `strategy_hypothesis_evaluations` tables.
- Added first-class workflow lineage, runtime lineage, node, timestamp, symbol, horizon, perspective, status, rank, and evidence-fingerprint columns rather than generic compatibility aliases.
- Added indexes for execution/node lookup, symbol/horizon/as-of lookup, status/confidence lookup, perspective/fingerprint lookup, decision/perspective lineage, and symbol/rank evaluation ordering.
- Added explicit foreign-key lineage from hypothesis evaluations to synthesis decisions with cascade deletion and from evaluations to hypotheses with nullable set-null preservation.
- Added a targeted database migration contract test that verifies the strategy schema columns, indexes, and foreign-key lineage after migrating to the new revision.
- Removed temporary command-output files used while validating PostgreSQL connectivity so no local connection details remain in generated artifacts.

Verification:

- `uv run ruff check . --fix`
- `uv run ruff format .`
- `uv run mypy . --explicit-package-bases`
- `uv run alembic heads`
- PostgreSQL-backed migration contract tests with `POLARIS_TEST_DATABASE_URL` supplied from the running local PostgreSQL container environment.
- `uv run graphify update .`
- `git diff --check`

Result:

- Full Ruff check passed.
- Full Ruff formatting completed with no file changes.
- Full project MyPy passed: `Success: no issues found in 1202 source files`.
- Alembic has a single head: `f2a3b4c5d6e7`.
- PostgreSQL-backed migration contract tests passed: `7 passed`.
- Graphify was updated after Python changes.
- `git diff --check` passed.
- PostgreSQL was the only live service required for this step; it was already running.
