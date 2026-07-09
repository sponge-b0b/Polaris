  # Phase 2 Plan — Downstream Breadth Adoption Audit and Updates

  ## Summary

  I audited downstream consumers of the new get_sp500_data / expanded S&P 500 breadth pipeline. Phase 1 updated TechnicalAgent and MorningReportAssembler, but several intelligence nodes still ignore the new breadth context and
  therefore do not yet reflect the upstream changes in risk, strategy, synthesis, or trade packaging.

  No core runtime changes are needed.

  ## Files That Require Updating

  ### Required downstream updates

  - intelligence/risk/volatility/volatility_risk_agent.py
      - Currently consumes technical_agent but only uses snapshot and volatility.
      - Add breadth-aware volatility risk pressure using features.breadth_state.
      - Include breadth risk, participation weakness, McClellan weakness, and price/A-D divergence in risk features, signals, risks, and recommendations.

  - intelligence/risk/aggregation/risk_aggregator_agent.py
  - intelligence/risk/regime/risk_regime_coupling.py
      - Currently couples risk only with calibrated technical regime and volatility.
      - Add breadth context as an input to regime coupling.
      - Increase risk pressure for weak/deteriorating breadth or price/A-D divergence.
      - Reduce risk pressure slightly for strong confirmed breadth.

  - intelligence/strategy/bull/bull_agent.py
      - Penalize bullish score and confidence when breadth is weak, narrow, or divergent.
      - Add bullish confirmation when breadth is strong and participation is broad.
      - Add risks like breadth_not_confirming_bullish_setup.

  - intelligence/strategy/bear/bear_agent.py
      - Increase bearish opportunity quality when breadth is weak or deteriorating.
      - Penalize bearish conviction when breadth is strong.
      - Add risks like strong_breadth_countertrend_risk.

  - intelligence/strategy/sideways/sideways_agent.py
      - Increase sideways/neutral score when breadth is mixed, narrow, or divergent.
      - Add range-bound / uncertainty risks when participation is weak but direction is unclear.

  - intelligence/strategy/synthesis/strategy_synthesis_agent.py
      - Include breadth context in uncertainty, execution readiness, signal quality, signals, risks, and features.
      - Weak or divergent breadth should lower execution readiness and increase uncertainty.

  - intelligence/execution/trade_packaging/trade_packager.py
      - Add breadth to trade reasoning and position sizing.
      - Long bias should be dampened by weak/divergent breadth.
      - Short bias should be dampened by strong breadth.
      - Add risks/recommendations for breadth-confirmation failures.

  ### Recommended shared helper

  Add a small immutable intelligence-layer helper, for example:

  intelligence/analysts/technical/technical_breadth_context.py

  Purpose:

  - Convert serialized technical_agent.outputs.features into a typed internal object.
  - Avoid duplicating fragile dict extraction across risk, strategy, synthesis, and trade packaging.
  - Keep dictionaries at runtime boundaries, but use typed breadth context internally.

  Suggested fields:

  - has_breadth_data
  - breadth_regime
  - breadth_score
  - breadth_risk_score
  - participation_score
  - leadership_score
  - mcclellan_score
  - price_ad_divergence

  ## Files That Do Not Require Updating Now

  - intelligence/portfolio/management/portfolio_manager_agent.py
      - Should continue consuming synthesized strategy and aggregated risk only.
      - Breadth should reach it indirectly through synthesis/risk.

  - intelligence/execution/execution_risk/execution_risk_guard.py
      - Should continue treating risk_aggregator_agent as the source of truth.
      - No direct technical/breadth dependency needed.

  - intelligence/attribution/attribution_engine.py
      - Optional future enhancement only.
      - Current score-level attribution remains valid.

  - application/reports/morning_report_renderer.py
      - No direct update needed because the assembler already builds the human-readable breadth section.

  - interfaces/cli/*
      - No required production update found.
      - Test fixtures may be expanded only if needed to lock report rendering expectations.

  - integration/clients/market_data/fred_data_client.py
      - get_ad_line_data appears legacy and unreferenced.
      - No phase 2 update required unless we choose a separate cleanup.

  ## Additional Upstream Consistency Fixes Found

  These are not new downstream files, but they should be fixed during phase 2 because they affect correctness:

  - application/services/technical/volatility_analysis.py
      - _compute_breadth_confirmation_score() reads market_context["breadth_score"], but breadth_score is produced later by breadth_analysis.
      - Fix by computing volatility breadth confirmation only from raw market context fields, or by explicitly passing computed breadth into volatility analysis.

  - application/services/technical/breadth_analysis.py
      - _compute_leadership_score() has an unreachable new_high_low_ratio < 0.33 branch after a broader < 0.75 branch.
      - Fix branch ordering so severe new-low leadership weakness is actually applied.

  ## Implementation Steps

  - [x] Step 1: Add typed breadth context extractor and unit tests.
  - [x] Step 2: Fix upstream consistency issues in volatility and breadth analysis.
  - [x] Step 3: Update VolatilityRiskAgent to consume breadth context.
  - [x] Step 4: Update risk aggregation / regime coupling to include breadth context.
  - [x] Step 5: Update bull, bear, and sideways strategy agents.
  - [x] Step 6: Update strategy synthesis breadth gating.
  - [x] Step 7: Update trade packaging breadth-aware reasoning and sizing.
  - [x] Step 8: Add/expand unit tests for risk, strategy, synthesis, and trade packaging.
  - [x] Step 9: Expand the real morning report workflow integration test to assert breadth propagation beyond technical_agent.
  - [x] Step 10: Run scoped validation with uv run pytest, ruff, and scoped mypy.

  ## Test Plan

  - Unit tests for the new breadth context extractor.
  - Unit tests for weak breadth / price-A/D divergence raising volatility risk.
  - Unit tests for risk coupling increasing risk under deteriorating breadth.
  - Unit tests for bull/bear/sideways strategy score changes under strong vs weak breadth.
  - Unit tests for synthesis lowering execution readiness under divergent breadth.
  - Unit tests for trade packaging reducing sizing or adding risks when breadth does not confirm.
  - Integration test confirming real morning report workflow propagates breadth context into risk and strategy outputs.

  ## Assumptions

  - Phase 2 should update intelligence/application edge layers only; no core runtime contract changes.
  - Breadth should influence recommendations, risk posture, sizing hints, and confidence, but must not create autonomous execution behavior.
  - Missing breadth data should be neutral and should not penalize outputs.


## Codex Revision — Step 4 Resume Review (2026-06-07)

Status: Approved for implementation in Default mode.

Recommendations:
- Keep Step 4 focused on `RiskAggregatorAgent` and `risk_regime_coupling`; do not advance into strategy, synthesis, trade packaging, reporting, or workflow files yet.
- Use the canonical typed `TechnicalBreadthContext` extractor already introduced in Step 1 instead of adding new dict-based breadth parsing.
- Preserve missing breadth as neutral: no risk pressure penalty, no breadth risk flags, and no breadth-specific signals when `has_breadth_data` is false.
- Add focused Step 4 unit coverage immediately for risk-regime coupling and risk aggregation, even though broader risk/strategy tests remain in Step 8.
- Preserve internal numeric precision and remove presentation-style rounding from newly touched risk-regime coupling outputs.
- Surface Repowise risk note: `risk_aggregator_agent.py` has moderate health and high co-change scatter, so Step 4 should stay surgical and avoid broad refactoring of the existing long `_execute` method.

## Step Results

### Step 1 — Typed breadth context extractor and unit tests

Status: Complete

Changed files:
- `intelligence/analysts/technical/technical_breadth_context.py`
- `tests/unit/intelligence/analysts/technical/test_technical_breadth_context.py`

Implementation notes:
- Added immutable slotted `TechnicalBreadthContext` dataclass for downstream intelligence nodes.
- Added extractors for serialized `technical_agent` node outputs and inner `features` payloads.
- Missing breadth data now resolves to an unavailable/neutral typed context so downstream nodes are not penalized.
- Added helper properties for weak/strong breadth, confirmation score, risk pressure, and canonical breadth risk flags.

Validation:
- `uv run pytest -q tests/unit/intelligence/analysts/technical/test_technical_breadth_context.py` — passed, 3 tests.
- `uv run ruff check intelligence/analysts/technical/technical_breadth_context.py tests/unit/intelligence/analysts/technical/test_technical_breadth_context.py` — passed.
- `uv run mypy --explicit-package-bases --ignore-missing-imports --follow-imports=skip intelligence/analysts/technical/technical_breadth_context.py tests/unit/intelligence/analysts/technical/test_technical_breadth_context.py` — passed.


### Step 2 — Upstream volatility and breadth consistency fixes

Status: Complete

Changed files:
- `application/services/technical/volatility_analysis.py`
- `application/services/technical/breadth_analysis.py`
- `tests/unit/application/services/technical/test_breadth_volatility_analysis.py`

Implementation notes:
- Removed volatility analysis dependency on `market_context["breadth_score"]`, which is produced later by `breadth_analysis` and is not part of raw market context.
- Reworked volatility breadth confirmation to compute from raw S&P 500 breadth context: participation, leadership, McClellan, price/A-D divergence, and canonical A/D trend score.
- Fixed unreachable severe leadership branch in `_compute_leadership_score()` by checking `new_high_low_ratio < 0.33` before the broader `< 0.75` branch.
- Added service-level tests for raw breadth confirmation, neutral missing breadth behavior, and severe leadership branch reachability.
- Corrected misleading `legacy_ad_line_trend_score` naming; volatility analysis now preserves the canonical `ad_line_trend_score` name from `market_context`.

Validation:
- `uv run pytest -q tests/unit/application/services/technical/test_breadth_volatility_analysis.py` — passed, 3 tests.
- `uv run ruff check application/services/technical/volatility_analysis.py application/services/technical/breadth_analysis.py tests/unit/application/services/technical/test_breadth_volatility_analysis.py` — passed.
- `uv run mypy --explicit-package-bases --ignore-missing-imports --follow-imports=skip application/services/technical/volatility_analysis.py application/services/technical/breadth_analysis.py tests/unit/application/services/technical/test_breadth_volatility_analysis.py` — passed.


### Step 3 — VolatilityRiskAgent breadth context adoption

Status: Complete

Changed files:
- `intelligence/risk/volatility/volatility_risk_agent.py`
- `tests/unit/intelligence/risk/test_volatility_risk_agent.py`

Implementation notes:
- Wired `VolatilityRiskAgent` to consume the typed `TechnicalBreadthContext` extractor from serialized `technical_agent` outputs.
- Added breadth-aware volatility risk modifier: missing breadth is neutral, weak/divergent breadth raises composite volatility risk, and strong confirming breadth can modestly reduce pressure.
- Added serialized breadth context, breadth confirmation score, breadth risk pressure, modifier, and breadth risk flags to volatility risk features.
- Added breadth-specific signals, risk flags, and recommendations to the volatility risk node output without changing core runtime contracts.

Validation:
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/risk/test_volatility_risk_agent.py` — passed, 6 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check intelligence/risk/volatility/volatility_risk_agent.py tests/unit/intelligence/risk/test_volatility_risk_agent.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy --explicit-package-bases --ignore-missing-imports --follow-imports=skip intelligence/risk/volatility/volatility_risk_agent.py tests/unit/intelligence/risk/test_volatility_risk_agent.py` — passed.

### Step 4 — Risk aggregation and regime coupling breadth context adoption

Status: Complete

Changed files:
- `intelligence/risk/regime/risk_regime_coupling.py`
- `intelligence/risk/aggregation/risk_aggregator_agent.py`
- `tests/unit/intelligence/risk/test_risk_regime_coupling.py`
- `tests/unit/intelligence/risk/test_risk_aggregator_agent.py`

Implementation notes:
- Added optional typed `TechnicalBreadthContext` input to risk-regime coupling while preserving missing breadth as neutral.
- Added deterministic breadth modifiers: weak/divergent breadth modestly raises aggregate risk pressure and composite risk; strong confirming breadth modestly lowers risk pressure.
- Removed presentation-style rounding from touched risk-regime coupling outputs so internal risk calculations preserve full numeric precision.
- Wired `RiskAggregatorAgent` to extract serialized technical breadth into the typed breadth context, pass it into coupling, and expose breadth context, modifiers, flags, signals, and recommendations in the runtime output.
- Kept Step 4 surgical and did not advance into strategy, synthesis, trade packaging, reporting, workflow, or core runtime files.

Validation:
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/risk/test_risk_regime_coupling.py tests/unit/intelligence/risk/test_risk_aggregator_agent.py` — passed, 6 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/risk` — passed, 14 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check intelligence/risk/aggregation/risk_aggregator_agent.py intelligence/risk/regime/risk_regime_coupling.py tests/unit/intelligence/risk/test_risk_regime_coupling.py tests/unit/intelligence/risk/test_risk_aggregator_agent.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy --explicit-package-bases --ignore-missing-imports --follow-imports=skip intelligence/risk/aggregation/risk_aggregator_agent.py intelligence/risk/regime/risk_regime_coupling.py tests/unit/intelligence/risk/test_risk_regime_coupling.py tests/unit/intelligence/risk/test_risk_aggregator_agent.py` — passed.

### Step 5 — Bull, bear, and sideways strategy breadth adoption

Status: Complete

Changed files:
- `intelligence/strategy/bull/bull_agent.py`
- `intelligence/strategy/bear/bear_agent.py`
- `intelligence/strategy/sideways/sideways_agent.py`
- `tests/unit/intelligence/strategy/test_breadth_strategy_agents.py`

Implementation notes:
- Wired bull, bear, and sideways strategy agents to consume the typed `TechnicalBreadthContext` from serialized `technical_agent` outputs.
- Bull strategy now penalizes weak, narrow, or divergent breadth and credits strong confirming breadth.
- Bear strategy now credits weak/deteriorating breadth and lowers conviction when strong breadth creates countertrend risk.
- Sideways strategy now treats weak, narrow, mixed, or divergent breadth as range/uncertainty confirmation and reduces sideways conviction when breadth is strongly confirming trend participation.
- Added breadth context, confirmation score, risk pressure, score/confidence modifiers, and breadth risk flags to each strategy agent's features.
- Added breadth-specific signals, risks, and recommendations without changing core runtime contracts or advancing into synthesis/trade packaging.
- Repowise noted all three strategy agents have large/complex `_execute` methods and co-change scatter, so the implementation stayed surgical and avoided broad refactors.

Validation:
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/strategy/test_breadth_strategy_agents.py` — passed, 3 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/risk tests/unit/intelligence/strategy/test_breadth_strategy_agents.py` — passed, 17 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check intelligence/strategy/bull/bull_agent.py intelligence/strategy/bear/bear_agent.py intelligence/strategy/sideways/sideways_agent.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy --explicit-package-bases --ignore-missing-imports --follow-imports=skip intelligence/strategy/bull/bull_agent.py intelligence/strategy/bear/bear_agent.py intelligence/strategy/sideways/sideways_agent.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py` — passed.

### Step 6 — Strategy synthesis breadth gating

Status: Complete

Changed files:
- `intelligence/strategy/synthesis/strategy_synthesis_agent.py`
- `tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py`

Implementation notes:
- Wired `StrategySynthesisAgent` to consume the typed `TechnicalBreadthContext` from serialized `technical_agent` outputs.
- Missing breadth data remains neutral with zero breadth modifiers, no breadth signals, and no breadth-specific risks.
- Weak, narrow, elevated-risk, or price/A-D divergent breadth now increases synthesis uncertainty, lowers execution readiness, and lowers signal quality.
- Strong confirming breadth now modestly lowers uncertainty, raises execution readiness, and raises signal quality.
- Added breadth context, confirmation score, risk pressure, modifiers, and risk flags to synthesis features.
- Added breadth-specific synthesis signals, risks, and recommendations without changing core runtime contracts or advancing into trade packaging.
- Repowise noted the synthesis node has a large/complex `_execute` method and co-change scatter, so Step 6 stayed surgical and added focused tests for the new gating behavior.

Validation:
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py` — passed, 3 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/risk tests/unit/intelligence/strategy` — passed, 20 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check intelligence/strategy/synthesis/strategy_synthesis_agent.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy --explicit-package-bases --ignore-missing-imports --follow-imports=skip intelligence/strategy/synthesis/strategy_synthesis_agent.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py` — passed.

### Step 7 — Trade packaging breadth-aware reasoning and sizing

Status: Complete

Changed files:
- `intelligence/execution/trade_packaging/trade_packager.py`
- `tests/unit/intelligence/execution/test_trade_packager_breadth.py`

Implementation notes:
- Wired `TradePackager` to consume the typed `TechnicalBreadthContext` from serialized `technical_agent` outputs.
- Missing breadth data remains neutral with zero entry-bias modifier, a 1.0 position-size multiplier, no breadth signals, and no breadth-specific risks.
- Weak or divergent breadth now dampens positive/long trade intent and reduces the position sizing hint.
- Strong confirming breadth now dampens negative/short trade intent and reduces the position sizing hint for short setups.
- Added breadth context, confirmation score, risk pressure, entry-bias modifier, position-size multiplier, and breadth risk flags to trade packaging features and trade-intent reasoning.
- Added breadth-specific signals, risks, and recommendations without changing core runtime contracts or adding autonomous execution behavior.
- Repowise noted the trade packager has a large `_execute` method and high co-change scatter, so Step 7 stayed scoped to packaging behavior and added focused tests.

Validation:
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/execution/test_trade_packager_breadth.py` — passed, 3 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/risk tests/unit/intelligence/strategy tests/unit/intelligence/execution` — passed, 24 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check intelligence/execution/trade_packaging/trade_packager.py tests/unit/intelligence/execution/test_trade_packager_breadth.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy --explicit-package-bases --ignore-missing-imports --follow-imports=skip intelligence/execution/trade_packaging/trade_packager.py tests/unit/intelligence/execution/test_trade_packager_breadth.py` — passed.

### Step 8 — Expanded breadth adoption unit coverage

Status: Complete

Changed files:
- `tests/unit/intelligence/risk/test_volatility_risk_agent.py`
- `tests/unit/intelligence/risk/test_risk_aggregator_agent.py`
- `tests/unit/intelligence/strategy/test_breadth_strategy_agents.py`
- `tests/unit/intelligence/execution/test_trade_packager_breadth.py`

Implementation notes:
- Expanded risk tests to assert serialized breadth confirmation scores, breadth risk pressure, and breadth risk flags for weak and strong breadth paths.
- Added strategy-agent coverage confirming missing breadth remains neutral across bull, bear, and sideways agents: zero breadth modifiers, no risk flags, and no breadth signals.
- Added trade-packaging coverage for the gating case where weak/divergent breadth moves an otherwise long setup back to flat and records the related signal, risk, and recommendation.
- Kept Step 8 test-only; no production intelligence or runtime behavior was changed.
- Repowise noted existing test duplication in breadth fixtures; Step 8 stayed scoped and did not introduce a shared helper module to avoid broader test-suite refactoring during this step.

Validation:
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/risk tests/unit/intelligence/strategy tests/unit/intelligence/execution` — passed, 26 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/unit/intelligence/risk/test_volatility_risk_agent.py tests/unit/intelligence/risk/test_risk_aggregator_agent.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py tests/unit/intelligence/execution/test_trade_packager_breadth.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy --explicit-package-bases --ignore-missing-imports --follow-imports=skip tests/unit/intelligence/risk/test_volatility_risk_agent.py tests/unit/intelligence/risk/test_risk_aggregator_agent.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py tests/unit/intelligence/execution/test_trade_packager_breadth.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .` — passed.

### Step 9 — Morning report workflow breadth propagation integration coverage

Status: Complete

Changed files:
- `tests/integration/workflow/test_morning_report_real_nodes.py`
- `intelligence/strategy/di.py`
- `intelligence/strategy/synthesis/strategy_synthesis_agent.py`
- `tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py`

Implementation notes:
- Expanded the real morning report workflow integration test to assert S&P 500 breadth data is produced by `technical_agent` and propagated into downstream real nodes beyond the technical layer.
- Added assertions for breadth context propagation through `volatility_risk_agent`, `risk_aggregator_agent`, `bull_agent`, `bear_agent`, `sideways_agent`, `strategy_synthesis_agent`, `trade_packager`, and `execution_risk_guard`.
- Locked runtime-boundary serialized breadth fields: `breadth_context`, `breadth_confirmation_score`, `breadth_risk_pressure`, and `breadth_risk_flags`.
- Added trade-packager-specific assertions for breadth-aware entry bias and position sizing fields.
- Step 9 exposed a prerequisite strategy synthesis wiring gap: the real workflow uses the canonical `adaptive_weighting_engine` node name, but synthesis was still looking for `weighting_engine`. Updated synthesis to consume the canonical workflow node output directly.
- Step 9 also exposed incomplete strategy synthesis event-service wiring. Updated strategy DI to inject `MarketEventsService`, `ServiceRunner`, and `IntelligenceTelemetry`, and updated synthesis to call the typed `market_events.state` service request through `ServiceRunner`.
- Updated existing strategy synthesis breadth unit tests to construct the agent with explicit typed dependencies instead of relying on the removed no-arg constructor.
- No core runtime changes were made.

Validation:
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/integration/workflow/test_morning_report_real_nodes.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py` — passed, 4 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/integration/workflow/test_morning_report_real_nodes.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py intelligence/strategy/di.py intelligence/strategy/synthesis/strategy_synthesis_agent.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy --explicit-package-bases --ignore-missing-imports --follow-imports=skip tests/integration/workflow/test_morning_report_real_nodes.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py intelligence/strategy/di.py intelligence/strategy/synthesis/strategy_synthesis_agent.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .` — passed.

### Step 10 — Scoped Phase 2 validation

Status: Complete

Changed files:
- `application/services/technical/breadth_analysis.py`
- `intelligence/strategy/synthesis/strategy_synthesis_agent.py`
- `.agent/plans/plan_breadth_adoption_phase2.md`

Implementation notes:
- Ran the full scoped Phase 2 validation set across breadth analysis, volatility analysis, risk, strategy, execution packaging, canonical service entrypoints, and the real morning report workflow integration test.
- Initial scoped ruff validation surfaced two unused local variables in `application/services/technical/breadth_analysis.py`: `ad_line_ema_10` and `net_breadth`.
- Removed only those unused assignments; no breadth scoring behavior, core runtime contracts, or downstream intelligence behavior was changed.
- `git diff --check` surfaced one trailing-whitespace line in the Step 9 synthesis file; removed whitespace only with no behavior change.
- Repowise health/risk review noted `breadth_analysis.py` is a churn-heavy hotspot with a large `analyze` function, so the lint fix stayed deliberately surgical.

Validation:
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/analysts/technical/test_technical_breadth_context.py tests/unit/application/services/technical/test_breadth_volatility_analysis.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/intelligence/risk tests/unit/intelligence/strategy tests/unit/intelligence/execution tests/integration/workflow/test_morning_report_real_nodes.py` — passed, 40 tests, 1 dependency deprecation warning.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/services/market_events/market_events_service.py application/services/technical/breadth_analysis.py application/services/technical/volatility_analysis.py intelligence/analysts/technical/technical_breadth_context.py intelligence/risk/volatility/volatility_risk_agent.py intelligence/risk/regime/risk_regime_coupling.py intelligence/risk/aggregation/risk_aggregator_agent.py intelligence/strategy/bull/bull_agent.py intelligence/strategy/bear/bear_agent.py intelligence/strategy/sideways/sideways_agent.py intelligence/strategy/di.py intelligence/strategy/synthesis/strategy_synthesis_agent.py intelligence/execution/trade_packaging/trade_packager.py tests/unit/intelligence/analysts/technical/test_technical_breadth_context.py tests/unit/application/services/technical/test_breadth_volatility_analysis.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/intelligence/risk/test_volatility_risk_agent.py tests/unit/intelligence/risk/test_risk_regime_coupling.py tests/unit/intelligence/risk/test_risk_aggregator_agent.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/intelligence/execution/test_trade_packager_breadth.py tests/integration/workflow/test_morning_report_real_nodes.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy --explicit-package-bases --ignore-missing-imports --follow-imports=skip application/services/market_events/market_events_service.py application/services/technical/breadth_analysis.py application/services/technical/volatility_analysis.py intelligence/analysts/technical/technical_breadth_context.py intelligence/risk/volatility/volatility_risk_agent.py intelligence/risk/regime/risk_regime_coupling.py intelligence/risk/aggregation/risk_aggregator_agent.py intelligence/strategy/bull/bull_agent.py intelligence/strategy/bear/bear_agent.py intelligence/strategy/sideways/sideways_agent.py intelligence/strategy/di.py intelligence/strategy/synthesis/strategy_synthesis_agent.py intelligence/execution/trade_packaging/trade_packager.py tests/unit/intelligence/analysts/technical/test_technical_breadth_context.py tests/unit/application/services/technical/test_breadth_volatility_analysis.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/intelligence/risk/test_volatility_risk_agent.py tests/unit/intelligence/risk/test_risk_regime_coupling.py tests/unit/intelligence/risk/test_risk_aggregator_agent.py tests/unit/intelligence/strategy/test_breadth_strategy_agents.py tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py tests/unit/intelligence/execution/test_trade_packager_breadth.py tests/integration/workflow/test_morning_report_real_nodes.py` — passed, 23 source files.
- `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .` — passed.
