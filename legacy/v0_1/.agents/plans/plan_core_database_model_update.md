  # Revised Core Database Model Coverage and Schema Cleanup Plan

  ## Summary

  Current core/database/models/ models are incomplete relative to current application service and intelligence-node outputs. The revised plan will include both:

  1. Additive model expansion for missing canonical platform data.
  2. Destructive schema cleanup where existing columns are legacy, misnamed, redundant, or inconsistent with current service contracts.

  The goal is to make PostgreSQL a clean system-of-record for curated platform data before future RAG ingestion or embedding pipelines rely on it.

  Recommended persistence architecture remains hybrid:

  - Relational columns for canonical, queryable, durable platform signals.
  - JSON/JSONB payloads for complete nested service/intelligence outputs.
  - No preservation of legacy aliases when they conflict with canonical service naming.
  - Destructive renames/drops are allowed as part of the migration plan.

  ## Schema Cleanup Policy

  ### Allowed in this plan

  - Rename legacy columns to canonical service/output names.
  - Drop redundant legacy columns after data is migrated.
  - Replace ambiguous JSON columns with semantically named payload columns.
  - Normalize inconsistent naming across market, portfolio, macro, sentiment, news, and agent-intelligence models.
  - Update migrations, models, serializers, repositories, and tests together.

  ### Required safeguards

  - Use Alembic migrations.
  - Preserve existing data during rename/move operations where feasible.
  - Prefer ALTER TABLE ... RENAME COLUMN when the meaning is unchanged.
  - Use backfill migration logic when replacing one column with another.
  - Drop legacy columns only after values are copied or intentionally deemed obsolete.
  - Document intentional data loss if a dropped field is not migrated.
  - Do not round numeric values during migration or persistence.
  - Update all ORM models, persistence mappers, tests, and exports in the same implementation sequence.

  ## Key Model Findings

  ### Market / Technical

  core/database/models/market.py does not fully model the current TechnicalAnalysisService result:

  {
      "symbol": symbol,
      "technical_score": technical_score,
      "snapshot": snapshot,
      "market_context": market_context,
      "micro_regime": micro_regime,
      "trend": trend,
      "volatility": volatility,
      "breadth": breadth,
      "raw_regime": regime,
      "regime": calibrated,
  }

  Major gaps:

  - technical_score
  - snapshot
  - market_context
  - micro_regime
  - trend
  - volatility
  - breadth
  - raw_regime
  - calibrated regime
  - VIX/VVIX context
  - SP500 breadth context
  - AD-line metrics
  - McClellan metrics
  - participation/leadership/divergence scores
  - top_50_constituents
  - market_caps

  Existing market breadth column names are also inconsistent with canonical service naming in places, for example advancing_count / declining_count versus service-level advances_count / declines_count.

  ### Market Events

  MarketEventsService has no clear first-class database model for:

  - market_pressure_score
  - volatility_forecast
  - regime_bias
  - events
  - high_impact_events
  - event_count
  - high_impact_count
  - risk_projection

  ### Portfolio

  Portfolio models are mostly present but under-model current portfolio service outputs.

  Missing or under-modeled fields include:

  - account metadata
  - buying-power variants
  - pending transfers
  - options approval/trading levels
  - enriched position fields
  - beta/sector/exposure metadata
  - full portfolio/equity/position payload preservation

  ### Macro

  Macro models preserve top-level regime data but should include clearer columns/payloads for:

  - market_bias
  - summary
  - inflation analysis
  - Fed analysis
  - liquidity analysis
  - yield-curve analysis
  - economic-regime payload

  ### Sentiment

  Sentiment models should better reflect current sentiment service output:

  - market_bias
  - directional_signal
  - momentum
  - stability
  - divergence
  - provider payloads
  - features payload
  - sentiment payload
  - fusion components

  ### News

  News persistence should explicitly preserve:

  - headline_score
  - vendor raw payload
  - normalized article payload
  - derived analysis payloads

  ### Agent / Intelligence

  Generic agent persistence appears broadly usable but needs contract tests proving current runtime-node outputs are persisted with full fidelity.

  ## Implementation Plan

  ### Step 1 — Create a model-output coverage contract

  Add tests that map current service and intelligence outputs to persistence coverage.

  Each output key must be classified as:

  - canonical relational column
  - full-fidelity JSON/JSONB payload field
  - intentionally not persisted

  Coverage targets:

  - technical analysis
  - market context
  - breadth
  - market events
  - portfolio state
  - portfolio equity
  - portfolio positions
  - macro analysis
  - sentiment analysis
  - news analysis
  - representative intelligence-node outputs

  This test suite becomes the schema drift guard.

  ### Step 2 — Define canonical database naming rules

  Before modifying models, establish naming rules in tests and model comments where useful:

  - Use service-output names when they are already canonical.
  - Use singular domain concepts for snapshot identifiers.
  - Use _payload suffix for JSON/JSONB nested objects.
  - Use _score, _regime, _count, _ratio, _pct, _change_*, _ema_*, _slope_* consistently.
  - Avoid duplicate legacy/canonical aliases.
  - Rename or drop legacy names during the migration.

  Examples:

  - Rename advancing_count to advances_count.
  - Rename declining_count to declines_count.
  - Prefer metadata_payload over ambiguous metadata.
  - Prefer analysis_payload, inputs_payload, or domain-specific payload names over generic outputs where the meaning is unclear.

  ### Step 3 — Refactor market technical snapshot model

  Update TechnicalAnalysisSnapshotModel to directly represent the current technical-analysis result.

  Add canonical relational columns:

  - technical_score
  - directional_technical_score
  - bull_score
  - bear_score
  - sideways_score
  - trend_strength
  - trend_quality
  - trend_risk_score
  - volatility_risk_score
  - breadth_risk_score
  - strategy_environment
  - confidence

  Add full-fidelity payload columns:

  - snapshot_payload
  - market_context_payload
  - micro_regime_payload
  - trend_payload
  - volatility_payload
  - breadth_payload
  - raw_regime_payload
  - regime_payload

  Cleanup existing ambiguous columns:

  - Replace generic indicator_outputs with snapshot_payload where it represents indicator facts.
  - Replace generic analysis_outputs with domain-specific payload columns.
  - Drop legacy generic payload columns after migration/backfill if they become redundant.

  ### Step 4 — Refactor market context snapshot model

  Update MarketContextSnapshotModel to include canonical market-context fields.

  Add VIX/VVIX fields:

  - vix_20
  - vix_50
  - vix_percentile_252
  - vix_trend_ratio
  - vix_change_5d
  - vix_change_20d
  - vvix_20
  - vvix_50
  - vvix_percentile_252
  - vvix_trend_ratio
  - vvix_change_5d
  - vvix_change_20d

  Add SP500 / breadth context fields:

  - market_cap_index
  - market_cap_index_20
  - market_cap_index_50
  - market_cap_index_change_5d
  - market_cap_index_change_20d
  - advances_count
  - declines_count
  - unchanged_count
  - active_count
  - net_breadth
  - breadth_percent
  - ad_ratio
  - top_50_constituents_payload
  - market_caps_payload

  Add availability flags:

  - has_vix
  - has_vvix
  - has_sp500
  - has_ad_line
  - has_breadth

  Cleanup:

  - Rename/drop legacy count columns that conflict with canonical service naming.
  - Replace ambiguous inputs / outputs columns with inputs_payload and market_context_payload where appropriate.

  ### Step 5 — Refactor market breadth snapshot model

  Update MarketBreadthSnapshotModel to fully represent canonical breadth output.

  Add columns:

  - ad_line_ema_10
  - ad_line_ema_20
  - ad_line_ema_50
  - ad_line_slope_5
  - ad_line_slope_20
  - ad_line_trend_ratio
  - ad_line_trend_score
  - price_ad_divergence
  - new_high_low_diff
  - new_high_low_ratio
  - net_breadth_ema_19
  - net_breadth_ema_39
  - mcclellan_oscillator
  - mcclellan_summation_index
  - participation_score
  - leadership_score
  - mcclellan_score
  - divergence_score
  - confirmation_score
  - risk_regime
  - strategy_environment
  - has_breadth_data

  Add payloads:

  - components_payload
  - source_metrics_payload
  - breadth_payload

  Cleanup:

  - Rename advancing_count to advances_count.
  - Rename declining_count to declines_count.
  - Drop redundant legacy count columns after migration.
  - Replace generic outputs with breadth_payload if redundant.

  ### Step 6 — Add market events model

  Add a first-class model:

  MarketEventSnapshotModel

  Recommended fields:

  - event_snapshot_id
  - symbol
  - timestamp
  - source
  - market_pressure_score
  - volatility_forecast
  - regime_bias
  - event_count
  - high_impact_count
  - events_payload
  - high_impact_events_payload
  - risk_projection_payload
  - workflow/runtime lineage fields
  - metadata_payload
  - created/updated timestamps

  Update model exports.

  Add migration to create the table.

  ### Step 7 — Refactor portfolio state models

  Update portfolio state/history/latest models to align with portfolio service output.

  Add account/equity fields:

  - account_number
  - status
  - currency
  - regt_buying_power
  - daytrading_buying_power
  - non_marginable_buying_power
  - options_buying_power
  - multiplier
  - accrued_fees
  - pending_transfer_in
  - pending_transfer_out
  - options_approved_level
  - options_trading_level

  Add payloads:

  - portfolio_state_payload
  - equity_state_payload
  - risk_signals_payload

  Cleanup:

  - Rename ambiguous or duplicate equity/account columns to match current service contract.
  - Drop legacy columns whose meanings are superseded by canonical fields.

  ### Step 8 — Refactor portfolio position models

  Update historical/latest portfolio position models for enriched position output.

  Add fields:

  - qty_available
  - entry_price
  - current_price
  - lastday_price
  - change_today
  - signed_market_value
  - unrealized_intraday_pnl
  - unrealized_intraday_pnl_pct
  - asset_id
  - exchange
  - asset_class
  - asset_marginable
  - sector
  - beta
  - swap_rate
  - avg_entry_swap_rate
  - exposure_weight

  Add payloads:

  - position_payload
  - position_risk_payload

  Cleanup:

  - Rename existing position fields that use provider-specific names when a canonical platform name exists.
  - Drop redundant legacy provider-shaped columns after migration/backfill.

  ### Step 9 — Refactor macro models

  Update macro persistence models with current macro service contract.

  Add fields:

  - market_bias
  - summary
  - macro_score

  Add payloads:

  - macro_data_payload
  - inflation_analysis_payload
  - fed_analysis_payload
  - liquidity_analysis_payload
  - yield_curve_analysis_payload
  - economic_regime_payload
  - components_payload

  Cleanup:

  - Replace ambiguous inputs / outputs payloads with domain-specific payloads.
  - Drop redundant legacy payload columns after backfill.

  ### Step 10 — Refactor sentiment models

  Update sentiment persistence models with current sentiment service contract.

  Add fields:

  - market_bias
  - directional_signal
  - momentum
  - stability
  - divergence
  - sentiment_regime
  - composite_sentiment
  - confidence

  Add payloads:

  - providers_payload
  - features_payload
  - sentiment_payload
  - fusion_components_payload
  - raw_payload

  Cleanup:

  - Rename ambiguous sentiment columns to match canonical names.
  - Drop redundant legacy payload columns after migration.

  ### Step 11 — Refactor news models

  Update news persistence models with current news service output.

  Add fields:

  - headline_score
  - relevance_score if currently produced by downstream analysis
  - published_at consistency checks
  - normalized article identifier fields

  Add payloads:

  - normalized_article_payload
  - raw_payload
  - analysis_payload

  Cleanup:

  - Rename overlapping score fields only if their meaning matches the new canonical field.
  - If importance_score and headline_score mean different things, preserve both.
  - If importance_score was being used as headline_score, migrate and rename it.

  ### Step 12 — Verify agent and intelligence persistence models

  Audit current outputs from:

  - technical agent
  - strategy synthesis agent
  - risk agents
  - portfolio manager agent
  - trade packaging / recommendation layer
  - execution risk guard

  For each output:

  - confirm first-class query fields exist where needed
  - confirm full payload preservation exists
  - add model fields only when a field is durable and queryable
  - avoid unnecessary domain tables if generic agent signal persistence is sufficient

  Cleanup:

  - Rename generic agent payload columns only if they are ambiguous or inconsistent.
  - Do not duplicate agent output fields across multiple models unless there is a clear query/use-case reason.

  ### Step 13 — Create destructive Alembic migration set

  Create migrations that:

  - add new canonical columns
  - rename legacy columns to canonical names
  - backfill renamed/replaced data
  - move generic payload data into domain-specific payload columns
  - drop obsolete columns
  - create the new market-events table
  - update indexes where needed

  Migration sequencing:

  1. Add new columns/tables.
  2. Backfill from old columns.
  3. Rename columns where direct rename is safe.
  4. Validate non-null assumptions only where safe.
  5. Drop obsolete legacy columns.
  6. Add/update indexes.

  Indexes should prioritize:

  - symbol
  - timestamp
  - source
  - workflow_name
  - execution_id
  - key regimes
  - major scores used for querying/RAG curation

  ### Step 14 — Update persistence mappers and repositories

  Update all persistence code that writes these models.

  Rules:

  - service outputs are translated at the persistence boundary
  - application services should not know ORM details
  - intelligence nodes should not know ORM details
  - no rounding during persistence
  - no silent dropping of nested data
  - missing optional fields should persist as NULL, not fake defaults

  Update mappers for:

  - technical analysis
  - market context
  - breadth
  - market events
  - portfolio state
  - portfolio positions
  - portfolio equity
  - macro
  - sentiment
  - news
  - agent/intelligence outputs where applicable

  ### Step 15 — Update model exports and imports

  Update:

  - core/database/models/__init__.py
  - any repository imports
  - migration imports
  - persistence serializers
  - tests

  Remove references to dropped legacy columns.

  Do not keep compatibility shims for removed database fields.

  ### Step 16 — Add schema migration tests

  Add tests that verify:

  - all new models are importable
  - SQLAlchemy metadata includes expected tables/columns
  - dropped legacy columns are absent
  - renamed columns use canonical names
  - new indexes exist where expected
  - migrations can upgrade from the previous schema state

  ### Step 17 — Add persistence round-trip tests

  Add round-trip tests for realistic outputs from:

  - TechnicalAnalysisService
  - market breadth analysis
  - market context derivation
  - MarketEventsService
  - portfolio state/equity/positions
  - macro service
  - sentiment service
  - news service
  - representative intelligence-node output

  Each test should verify:

  - canonical columns are populated
  - full payloads are preserved
  - numeric precision is preserved
  - optional missing fields do not fail persistence
  - old legacy column names are no longer required
  - output can be read back into the expected persistence representation

  ### Step 18 — Update documentation / architectural notes

  Briefly document the database persistence convention:

  - PostgreSQL is the system of record.
  - ORM models should expose canonical query fields.
  - Full nested service outputs should be preserved in payload columns.
  - Legacy schema names should not be preserved once replaced.
  - Persistence is a boundary where JSON payloads are acceptable.
  - Internal service/agent contracts should remain typed where feasible.

  ### Step 19 — Verification

  Run:

  uv run ruff check . --fix
  uv run ruff format .
  uv run mypy . --explicit-package-bases
  uv run pytest tests/unit/core/database tests/unit/core/storage tests/unit/application/persistence
  uv run graphify update .

  If PostgreSQL integration tests are available, also run the relevant migration and persistence integration tests.

  ## Assumptions

  - Destructive schema cleanup is approved for this plan.
  - Legacy database column names do not need to be preserved for backward compatibility.
  - Data should be migrated where the old field has a clear canonical successor.
  - Data may be intentionally dropped only when the old field is redundant, ambiguous, or obsolete.
  - PostgreSQL remains the system of record.
  - Future RAG ingestion should use curated PostgreSQL records.
  - JSON/JSONB is acceptable at persistence boundaries.
  - Canonical, stable, queryable fields should be relational columns.

## Step Results

### Step 1 Results

- Added `tests/unit/core/database/test_model_output_coverage.py` as the initial model-output coverage contract.
- The test classifies service and intelligence output keys as relational columns, payload fields, or intentionally unpersisted fields.
- The test also pins the current schema gap report so later steps can reduce the expected gaps as models and migrations are updated.
- Focused verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_model_output_coverage.py` (`3 passed`), `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/unit/core/database/test_model_output_coverage.py`, and `UV_CACHE_DIR=/tmp/uv-cache uv run mypy tests/unit/core/database/test_model_output_coverage.py --explicit-package-bases`.

### Step 2 Results

- Extended `tests/unit/core/database/test_model_output_coverage.py` with canonical database naming rules.
- Added explicit cleanup targets for legacy/misaligned schema names such as `advancing_count`, `declining_count`, `advance_decline_line`, generic `inputs` / `outputs`, and technical `indicator_outputs` / `analysis_outputs`.
- Added checks that required payload targets use `_payload`, relational targets do not use payload suffixes, known legacy names have canonical successors, and score/risk/confidence fields follow canonical suffix patterns.
- Focused verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_model_output_coverage.py` (`6 passed`), `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/unit/core/database/test_model_output_coverage.py`, and `UV_CACHE_DIR=/tmp/uv-cache uv run mypy tests/unit/core/database/test_model_output_coverage.py --explicit-package-bases`.

### Step 3 Results

- Refactored `TechnicalAnalysisSnapshotModel` so the ORM schema now exposes canonical technical-analysis query fields: `technical_score`, `directional_technical_score`, bull/bear/sideways scores, trend quality/strength, risk scores, strategy environment, and confidence.
- Replaced the legacy ambiguous technical snapshot payload columns with explicit persistence-boundary JSONB payloads: `inputs_payload`, `snapshot_payload`, `market_context_payload`, `micro_regime_payload`, `trend_payload`, `volatility_payload`, `breadth_payload`, `raw_regime_payload`, and `regime_payload`.
- Updated the database model tests to require the new canonical columns and assert the removed legacy technical columns (`directional_score`, `inputs`, `indicator_outputs`, `analysis_outputs`) are no longer present on the ORM model.
- Updated the model-output coverage contract so `technical_analysis_result` no longer reports missing relational or payload columns after the Step 3 ORM refactor.
- Focused verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check --fix core/database/models/market.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_market_persistence_models.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format core/database/models/market.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_market_persistence_models.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/database/models/market.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_market_persistence_models.py --explicit-package-bases`, and `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_market_persistence_models.py` (`15 passed`).
- Refreshed the local Graphify map with `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`.
- Note: downstream market persistence records, serializers, repositories, and migrations still reference the previous technical snapshot names and should be updated in their planned follow-up steps before broad storage tests are expected to pass.

### Step 4 Results

- Refactored `MarketContextSnapshotModel` so the ORM schema now exposes the canonical market-context fields returned by the current technical-analysis service, including VIX/VVIX metrics, market-cap index metrics, breadth counts, AD-line metrics, participation metrics, McClellan metrics, and data-availability flags.
- Replaced the legacy ambiguous market-context JSONB columns with explicit persistence-boundary payload columns: `inputs_payload`, `market_context_payload`, `top_50_constituents_payload`, and `market_caps_payload`.
- Updated the market database model tests to require the new canonical market-context columns, validate Boolean flag column types, validate JSONB payload columns, and assert the removed legacy context columns (`inputs`, `outputs`) are no longer present on the ORM model.
- Updated the model-output coverage contract so `market_context` no longer reports missing relational or payload columns after the Step 4 ORM refactor.
- Focused verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check --fix core/database/models/market.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_market_persistence_models.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format core/database/models/market.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_market_persistence_models.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/database/models/market.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_market_persistence_models.py --explicit-package-bases`, and `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_market_persistence_models.py` (`15 passed`).
- Refreshed the local Graphify map with `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`.
- Note: downstream market persistence records, serializers, repositories, and migrations still reference the previous market-context payload names and should be updated in their planned follow-up steps before broad storage tests are expected to pass.

### Step 5 Results

- Refactored `MarketBreadthSnapshotModel` so the ORM schema now exposes the canonical breadth-analysis output fields, including canonical advances/declines counts, AD-line metrics, new-high/new-low metrics, McClellan metrics, breadth component scores, risk/strategy regime fields, and the `has_breadth_data` availability flag.
- Replaced legacy breadth column names with canonical service names: `advancing_count` -> `advances_count`, `declining_count` -> `declines_count`, `advance_decline_line` -> `ad_line`, `percent_above_50dma` -> `pct_above_50dma`, `percent_above_200dma` -> `pct_above_200dma`, `new_highs_count` -> `new_highs`, and `new_lows_count` -> `new_lows`.
- Replaced the legacy ambiguous breadth JSONB columns with explicit persistence-boundary payload columns: `inputs_payload`, `components_payload`, `source_metrics_payload`, and `breadth_payload`.
- Updated the market database model tests to require the new canonical breadth columns, validate the Boolean flag column type, validate JSONB payload columns, and assert the removed legacy breadth columns are no longer present on the ORM model.
- Updated the model-output coverage contract so `breadth_result` no longer reports missing relational or payload columns after the Step 5 ORM refactor.
- Focused verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check --fix core/database/models/market.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_market_persistence_models.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format core/database/models/market.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_market_persistence_models.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/database/models/market.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_market_persistence_models.py --explicit-package-bases`, and `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_market_persistence_models.py` (`15 passed`).
- Refreshed the local Graphify map with `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`.
- Note: downstream market persistence records, serializers, repositories, and migrations still reference the previous breadth column/payload names and should be updated in their planned follow-up steps before broad storage tests are expected to pass.

### Step 6 Results

- Added `MarketEventSnapshotModel` as the first-class ORM model for market-events persistence with canonical relational fields for symbol, timestamp, source, market pressure, volatility forecast, regime bias, event counts, runtime lineage, metadata, and row timestamps.
- Added explicit JSONB persistence-boundary payload columns for market-events nested outputs: `events_payload`, `high_impact_events_payload`, and `risk_projection_payload`.
- Added core market-event query indexes for symbol/timestamp, source/timestamp, regime/timestamp, and workflow/execution lookup paths.
- Exported `MarketEventSnapshotModel` from `core/database/models/__init__.py` and updated database metadata tests to require the `market_event_snapshots` table.
- Added Alembic migration `migrations/versions/20260613_0001_add_market_event_snapshots.py` to create/drop the new table and its indexes after revision `20260606_0001`.
- Updated model-output coverage so `market_events` no longer reports missing relational columns, missing payload columns, or a missing persistence model.
- Focused verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check --fix core/database/models/market.py core/database/models/__init__.py tests/unit/core/database/test_market_persistence_models.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_alembic_foundation.py migrations/versions/20260613_0001_add_market_event_snapshots.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format core/database/models/market.py core/database/models/__init__.py tests/unit/core/database/test_market_persistence_models.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_alembic_foundation.py migrations/versions/20260613_0001_add_market_event_snapshots.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_market_persistence_models.py tests/unit/core/database/test_alembic_foundation.py` (`18 passed`), and `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/database/models/market.py core/database/models/__init__.py tests/unit/core/database/test_market_persistence_models.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_alembic_foundation.py migrations/versions/20260613_0001_add_market_event_snapshots.py --explicit-package-bases`.
- Refreshed the local Graphify map with `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`.
- Note: this step adds the ORM table and migration only. Downstream market-event persistence records, serializers, repositories, and round-trip tests remain scheduled for later mapper/repository steps.

### Step 7 Results

- Refactored `PortfolioStateHistoryModel` and `PortfolioStateLatestModel` to add the canonical account/equity fields from the current portfolio service contract: account number/status/currency, buying-power variants, options levels, multiplier, accrued fees, and pending transfer fields.
- Renamed persistence column names to canonical database names while preserving existing ORM/domain attributes for downstream typed objects: `cash_ratio` now maps to `cash_pct`, and `risk_signals` now maps to `risk_signals_payload`.
- Added explicit persistence-boundary JSONB payload columns: `portfolio_state_payload` and `equity_state_payload`; `risk_signals_payload` is now the canonical risk-signals payload column.
- Added Alembic migration `migrations/versions/20260613_0002_refactor_portfolio_state_account_payload_columns.py` to destructively rename the legacy portfolio-state columns, add the new account/equity/payload columns to history/latest tables, create account/status lookup indexes, and provide a reversible downgrade.
- Added `tests/unit/core/database/test_portfolio_state_account_payload_migration.py` and updated portfolio-state model tests to require the new canonical columns, JSONB payloads, and cleanup of legacy database column names.
- Updated the model-output coverage contract so `portfolio_equity` is fully covered and `portfolio_state` now only reports `portfolio_history_payload` as a remaining planned persistence gap.
- Focused verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check --fix core/database/models/portfolio_state.py tests/unit/core/database/test_portfolio_state_persistence_models.py tests/unit/core/database/test_model_output_coverage.py migrations/versions/20260613_0002_refactor_portfolio_state_account_payload_columns.py tests/unit/core/database/test_portfolio_state_account_payload_migration.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format ...`, `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_portfolio_state_persistence_models.py tests/unit/core/database/test_portfolio_state_account_payload_migration.py` (`21 passed`), `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/database/models/portfolio_state.py --explicit-package-bases`, and `UV_CACHE_DIR=/tmp/uv-cache uv run mypy migrations/versions/20260613_0002_refactor_portfolio_state_account_payload_columns.py tests/unit/core/database/test_portfolio_state_account_payload_migration.py --explicit-package-bases`.
- Broader focused mypy that imports database coverage tests still reports the known downstream `core/storage/persistence/serializers/market_persistence_serializer.py` mismatches from the earlier market model cleanup; those serializer/repository updates remain outside Step 7 and should be handled in the planned downstream mapper/repository steps.
- Refreshed the local Graphify map with `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`.

### Step 8 Results

- Refactored `PortfolioPositionHistoryModel` and `PortfolioPositionLatestModel` to include the enriched canonical portfolio-position output fields: side, available quantity, price/change fields, signed market value, unrealized PnL fields, asset metadata, marginability, swap-rate fields, and exposure weight.
- Canonicalized the persisted exposure column by mapping the existing ORM/domain `weight` attribute to the database column `exposure_weight`, removing the legacy `weight` database column name while preserving typed record compatibility.
- Added explicit persistence-boundary JSONB payload columns for position records: `position_payload` and `position_risk_payload`.
- Added Alembic migration `migrations/versions/20260613_0003_refactor_portfolio_position_output_columns.py` to rename `weight` -> `exposure_weight`, add the enriched position columns to history/latest tables, add the new payload columns, and provide a reversible downgrade.
- Updated the portfolio-position ORM tests and model-output coverage contract so `portfolio_position` no longer reports missing relational or payload columns.
- Applied a minimal downstream repository fix in `core/storage/persistence/repositories/postgres_portfolio_expansion_persistence_repository.py` so latest-position upserts set `exposure_weight` from the Postgres excluded row after the column rename.
- Added `tests/unit/core/database/test_portfolio_position_output_migration.py` to validate the new migration targets, destructive rename, added column groups, JSONB payloads, and downgrade reversibility.
- Focused verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check --fix core/database/models/portfolio.py core/storage/persistence/repositories/postgres_portfolio_expansion_persistence_repository.py tests/unit/core/database/test_portfolio_expansion_persistence_models.py tests/unit/core/database/test_model_output_coverage.py migrations/versions/20260613_0003_refactor_portfolio_position_output_columns.py tests/unit/core/database/test_portfolio_position_output_migration.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format ...`, and `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_portfolio_expansion_persistence_models.py tests/unit/core/database/test_portfolio_position_output_migration.py tests/unit/core/storage/persistence/test_portfolio_persistence_serializer.py tests/unit/core/storage/persistence/test_postgres_portfolio_expansion_persistence_repository.py` (`30 passed`).
- Focused mypy passed for the direct Step 8 model/migration/test files: `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/database/models/portfolio.py migrations/versions/20260613_0003_refactor_portfolio_position_output_columns.py tests/unit/core/database/test_portfolio_position_output_migration.py --explicit-package-bases` and `UV_CACHE_DIR=/tmp/uv-cache uv run mypy tests/unit/core/database/test_portfolio_expansion_persistence_models.py --explicit-package-bases`.
- Broader focused mypy that imports persistence repository modules still reports the known downstream `core/storage/persistence/serializers/market_persistence_serializer.py` mismatches from the earlier market model cleanup; those are unrelated to Step 8 and remain scheduled for downstream mapper/repository cleanup.
- Refreshed the local Graphify map with `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`.

### Step 9 Results

- Refactored `MacroRegimeSnapshotModel` to cover the current macro service contract by adding canonical `market_bias` and `summary` relational columns; `macro_score` was already present and remains unchanged.
- Removed the legacy database column names `inputs` and `outputs` from the macro-regime table mapping by remapping the existing ORM/domain attributes to canonical persistence columns: `inputs` -> `macro_data_payload` and `outputs` -> `economic_regime_payload`. This keeps existing typed serializer/repository code compatible while cleaning up the physical schema names.
- Added explicit macro JSONB persistence-boundary payload columns: `inflation_analysis_payload`, `fed_analysis_payload`, `liquidity_analysis_payload`, `yield_curve_analysis_payload`, and `components_payload`.
- Added Alembic migration `migrations/versions/20260613_0004_refactor_macro_regime_payload_columns.py` to rename the legacy payload columns, add the new macro contract fields/payloads, and provide a reversible downgrade.
- Added `tests/unit/core/database/test_macro_regime_payload_migration.py` and updated macro/model coverage tests so `macro_result` no longer reports missing relational or payload columns.
- Focused verification passed: `python -m py_compile core/database/models/macro.py tests/unit/core/database/test_macro_persistence_models.py tests/unit/core/database/test_model_output_coverage.py migrations/versions/20260613_0004_refactor_macro_regime_payload_columns.py tests/unit/core/database/test_macro_regime_payload_migration.py core/storage/persistence/serializers/macro_persistence_serializer.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check --fix ...`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format ...`, `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_macro_persistence_models.py tests/unit/core/database/test_macro_regime_payload_migration.py tests/unit/core/storage/persistence/test_macro_persistence_serializer.py tests/unit/core/storage/persistence/test_postgres_macro_persistence_repository.py` (`27 passed`), and `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/database/models/macro.py migrations/versions/20260613_0004_refactor_macro_regime_payload_columns.py tests/unit/core/database/test_macro_regime_payload_migration.py tests/unit/core/database/test_macro_persistence_models.py --explicit-package-bases`.
- Full-project `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases` still fails on pre-existing/out-of-step issues in service test fixtures, telemetry tests, and the market persistence serializer after the earlier market schema cleanup. The Step 9 macro files pass focused mypy, and the market serializer/repository cleanup remains planned for downstream mapper/repository steps.
- Refreshed the local Graphify map with `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`.

### Step 10 Results

- Refactored `SentimentSnapshotModel` to cover the current sentiment service contract with canonical relational query fields for `market_bias`, `directional_signal`, `momentum`, `stability`, and `divergence`; existing ORM/domain attributes for `sentiment_regime`, `composite_sentiment_score`, and `confidence` remain available for typed record/serializer compatibility.
- Removed legacy physical database column names from the sentiment snapshot mapping by remapping ORM/domain attributes to canonical schema names: `sentiment_regime` -> `market_regime`, `composite_sentiment_score` -> `composite_sentiment`, `inputs` -> `providers_payload`, `outputs` -> `sentiment_payload`, and `component_scores` -> `fusion_components_payload`.
- Added explicit sentiment JSONB persistence-boundary payload columns: `features_payload` and `raw_payload`; existing typed record payload attributes now persist through canonical `providers_payload`, `sentiment_payload`, and `fusion_components_payload` database columns.
- Added Alembic migration `migrations/versions/20260613_0005_refactor_sentiment_snapshot_payload_columns.py` to rename the legacy sentiment snapshot columns, add the new service-contract columns/payloads, and provide a reversible downgrade.
- Added `tests/unit/core/database/test_sentiment_snapshot_payload_migration.py` and updated sentiment/model coverage tests so `sentiment_result` no longer reports missing relational or payload columns.
- Focused verification passed: `python -m py_compile core/database/models/sentiment.py tests/unit/core/database/test_sentiment_persistence_models.py tests/unit/core/database/test_model_output_coverage.py migrations/versions/20260613_0005_refactor_sentiment_snapshot_payload_columns.py tests/unit/core/database/test_sentiment_snapshot_payload_migration.py core/storage/persistence/serializers/sentiment_persistence_serializer.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check --fix ...`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format ...`, `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_sentiment_persistence_models.py tests/unit/core/database/test_sentiment_persistence_migration.py tests/unit/core/database/test_sentiment_snapshot_payload_migration.py tests/unit/core/storage/persistence/test_sentiment_persistence_serializer.py tests/unit/core/storage/persistence/test_postgres_sentiment_persistence_repository.py` (`31 passed`), and `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/database/models/sentiment.py migrations/versions/20260613_0005_refactor_sentiment_snapshot_payload_columns.py tests/unit/core/database/test_sentiment_snapshot_payload_migration.py tests/unit/core/database/test_sentiment_persistence_models.py --explicit-package-bases`.
- Full-project `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases` still fails on pre-existing/out-of-step issues in service test fixtures, telemetry tests, and the market persistence serializer after the earlier market schema cleanup. The Step 10 sentiment files pass focused mypy, and the market serializer/repository cleanup remains planned for downstream mapper/repository steps.
- Refreshed the local Graphify map with `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`.


### Step 11 Results

- Refactored `NewsArticleModel` to align persisted article data with the current news service output: the ORM/domain attribute `published_timestamp` now persists to the canonical database column `published_at`, and the model now includes `headline_score`, `relevance_score`, `normalized_article_payload`, and `raw_payload`.
- Preserved `importance_score` separately because it represents a distinct curated importance concept from the service-level `headline_score`; no destructive score merge was performed.
- Refactored `NewsAnalysisSnapshotModel` payload columns by remapping typed record attributes to canonical persistence columns: `inputs` -> `inputs_payload` and `outputs` -> `analysis_payload`.
- Extended typed news persistence records, serializers, repository upserts, and round-trip tests so headline/relevance scores plus normalized/raw article payloads are preserved across the PostgreSQL boundary.
- Added Alembic migration `migrations/versions/20260613_0006_refactor_news_payload_columns.py` to rename `published_timestamp` -> `published_at`, rename analysis payload columns, add the new article score/payload columns, update the published-at indexes, and support reversible downgrade.
- Added `tests/unit/core/database/test_news_payload_migration.py` and updated news model, output coverage, serializer, repository, and persistence-contract tests. `news_result` no longer reports missing relational or payload columns in the coverage contract.
- Focused verification passed: `python -m py_compile ...`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check --fix ...`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format ...`, and `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_news_persistence_models.py tests/unit/core/database/test_news_persistence_migration.py tests/unit/core/database/test_news_payload_migration.py tests/unit/core/storage/persistence/test_news_persistence_contracts.py tests/unit/core/storage/persistence/test_news_persistence_serializer.py tests/unit/core/storage/persistence/test_postgres_news_persistence_repository.py tests/unit/application/persistence/news/test_news_persistence_service.py` (`65 passed`).
- Full-project `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases` still fails on the known pre-existing/out-of-step issues in service test fixtures, telemetry tests, and the market persistence serializer after earlier market schema cleanup. The Step 11 focused tests pass, and the remaining market serializer/repository cleanup remains scheduled for downstream mapper/repository work.
- Refreshed the local Graphify map with `UV_CACHE_DIR=/tmp/uv-cache GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`.

### Step 12 Results

- Audited representative downstream intelligence-node output shapes for the technical agent, strategy synthesis agent, risk agents, portfolio manager, trade packager, and execution risk guard.
- Confirmed the generic `AgentSignalModel` remains the correct persistence target for runtime-node signal outputs because these nodes share the canonical `RuntimeNodeOutput.outputs` shape: queryable relational fields for `agent_name`, `agent_type`, `symbol`, `universe`, `timestamp`, `directional_score`, `confidence`, and `regime`; full-fidelity nested data preserved in `signals`, `risks`, `recommendations`, and `features` JSONB payloads.
- Extended `tests/unit/core/database/test_model_output_coverage.py` with separate coverage contracts for technical-agent, strategy-synthesis, risk-agent / execution-guard, portfolio-manager, trade-packager, and recommendation-layer outputs so future schema drift is caught without duplicating agent-specific columns unnecessarily.
- Confirmed curated recommendation/trade setup persistence is covered by the existing recommendation models, including `RecommendationModel`, `RecommendationRationaleModel`, `RecommendationOutcomeModel`, `TradeSetupModel`, and `WatchlistItemModel`.
- Cleaned up ambiguous agent-intelligence persistence column names by using canonical physical database names `inputs_payload` and `outputs_payload` on `agent_reasoning`, `agent_recommendations`, and `agent_risk_assessments` while preserving existing typed record/ORM attribute compatibility for `inputs` and `outputs`.
- Updated PostgreSQL agent-intelligence upsert statements to target `inputs_payload` and `outputs_payload` after the physical column rename.
- Added Alembic migration `migrations/versions/20260613_0007_refactor_agent_intelligence_payload_columns.py` to rename `inputs` -> `inputs_payload` and `outputs` -> `outputs_payload` across all agent-intelligence tables, with reversible downgrade.
- Added `tests/unit/core/database/test_agent_intelligence_payload_migration.py` and updated agent-intelligence ORM tests to require the canonical JSONB payload column names and reject the legacy physical `inputs` / `outputs` columns.
- Focused verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check --fix ...`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format ...`, `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_agent_intelligence_persistence_models.py tests/unit/core/database/test_agent_intelligence_persistence_migration.py tests/unit/core/database/test_agent_intelligence_payload_migration.py tests/unit/core/storage/persistence/test_agent_intelligence_persistence_contracts.py tests/unit/core/storage/persistence/test_agent_intelligence_persistence_serializer.py tests/unit/core/storage/persistence/test_postgres_agent_intelligence_persistence_repository.py tests/unit/application/persistence/agent_intelligence/test_agent_intelligence_persistence_service.py tests/unit/core/database/test_recommendation_persistence_models.py tests/unit/core/storage/persistence/test_recommendation_persistence_contracts.py tests/unit/core/storage/persistence/test_recommendation_persistence_serializer.py` (`82 passed`), and `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/database/models/agent_intelligence.py migrations/versions/20260613_0007_refactor_agent_intelligence_payload_columns.py tests/unit/core/database/test_agent_intelligence_payload_migration.py tests/unit/core/database/test_agent_intelligence_persistence_models.py --explicit-package-bases`.
- Broader focused mypy that imports persistence repository packages still reports the known out-of-step `core/storage/persistence/serializers/market_persistence_serializer.py` mismatches from earlier market schema cleanup. The direct Step 12 model/migration/test files pass mypy, and the market serializer/repository cleanup remains scheduled for downstream mapper/repository work.
- Refreshed the local Graphify map with `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`.

### Step 13 Results

- Created Alembic migration `migrations/versions/20260613_0008_refactor_market_technical_payload_columns.py` after revision `20260613_0007` to complete the destructive market technical/context/breadth schema cleanup set.
- The migration renames legacy technical-analysis columns to canonical schema names: `directional_score` -> `directional_technical_score`, `inputs` -> `inputs_payload`, `indicator_outputs` -> `snapshot_payload`, and `analysis_outputs` -> `regime_payload`.
- The migration adds missing canonical technical-analysis columns and payloads for service outputs, including bull/bear/sideways scores, trend quality/strength, risk scores, `strategy_environment`, and the market context / micro-regime / trend / volatility / breadth / raw-regime payload columns.
- The migration renames legacy market-context payload columns `inputs` -> `inputs_payload` and `outputs` -> `market_context_payload`, then adds the current VIX/VVIX, market-cap, breadth, AD-line, participation, McClellan, data-availability, top-50-constituents, and market-caps fields required by the ORM model.
- The migration renames legacy market-breadth fields to canonical names (`advancing_count` -> `advances_count`, `declining_count` -> `declines_count`, `new_highs_count` -> `new_highs`, `new_lows_count` -> `new_lows`, `advance_decline_line` -> `ad_line`, `percent_above_50dma` -> `pct_above_50dma`, `percent_above_200dma` -> `pct_above_200dma`, `outputs` -> `breadth_payload`) and adds the remaining canonical breadth metrics, score components, risk/strategy regimes, and payload columns.
- Added indexes for the newly introduced queryable regime/environment columns: `ix_technical_analysis_snapshots_strategy_environment`, `ix_market_breadth_snapshots_risk_regime`, and `ix_market_breadth_snapshots_strategy_environment`.
- Added `tests/unit/core/database/test_market_technical_payload_migration.py` to verify the migration exists, imports, targets the expected tables, performs the destructive renames, adds canonical output columns, creates/drops indexes, and remains reversible without table rebuilds.
- Focused verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check --fix migrations/versions/20260613_0008_refactor_market_technical_payload_columns.py tests/unit/core/database/test_market_technical_payload_migration.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format ... --check`, `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_market_technical_payload_migration.py tests/unit/core/database/test_market_persistence_models.py tests/unit/core/database/test_model_output_coverage.py` (`26 passed`), and `UV_CACHE_DIR=/tmp/uv-cache uv run mypy migrations/versions/20260613_0008_refactor_market_technical_payload_columns.py tests/unit/core/database/test_market_technical_payload_migration.py --explicit-package-bases`.
- Acknowledged the user-authorized mypy ignore list for unrelated pre-existing files; no full-project mypy cleanup was attempted as part of Step 13.
- Refreshed the local Graphify map with `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`.

### Step 14 Results

- Updated the market persistence boundary records to match the canonical ORM schema introduced in Steps 3-6 and Step 13. `MarketContextSnapshotRecord`, `TechnicalAnalysisSnapshotRecord`, and `MarketBreadthSnapshotRecord` now expose the current market-context, technical-analysis, and breadth-analysis relational fields and explicit `_payload` JSONB fields instead of legacy generic `inputs` / `outputs` style names.
- Added first-class `MarketEventSnapshotRecord` support, including a stable `new_market_event_snapshot_id()` helper and `MarketPersistenceBundle.event_snapshots`, so market-events service outputs are no longer silently dropped at the persistence boundary.
- Updated `MarketPersistenceSerializer` to serialize and hydrate the canonical market context, technical analysis, breadth, and market-event snapshot fields without rounding and without omitting nested payloads.
- Updated `MarketPersistenceRepository`, `PostgresMarketPersistenceRepository`, and `MarketPersistenceService` to persist/list market-event snapshots and to count event snapshots in atomic market persistence bundles.
- Corrected `MarketEventSnapshotModel.volatility_forecast` from `Float` to `String` because the current market-events service emits categorical forecasts such as `high`, `medium`, and `low`.
- Added Alembic migration `migrations/versions/20260613_0009_refactor_market_event_volatility_forecast_type.py` to convert `market_event_snapshots.volatility_forecast` from numeric to categorical text after revision `20260613_0008`, with a reversible numeric-only downgrade fallback.
- Added/updated unit tests for market persistence contracts, serializers, PostgreSQL repository behavior, application persistence service behavior, ORM model typing, and the new market-event volatility-forecast migration.
- Focused verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check --fix ...`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format ...`, `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/storage/persistence/test_market_persistence_contracts.py tests/unit/core/storage/persistence/test_market_persistence_serializer.py tests/unit/core/storage/persistence/test_postgres_market_persistence_repository.py tests/unit/application/persistence/market/test_market_persistence_service.py tests/unit/core/database/test_market_persistence_models.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/database/test_market_event_volatility_forecast_migration.py` (`93 passed`), and `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/database/models/market.py core/storage/persistence/market/market_persistence_models.py core/storage/persistence/market/market_persistence_repository.py core/storage/persistence/market/__init__.py core/storage/persistence/serializers/market_persistence_serializer.py core/storage/persistence/repositories/postgres_market_persistence_repository.py application/persistence/market/market_persistence_service.py application/persistence/market/__init__.py tests/unit/core/storage/persistence/test_market_persistence_contracts.py tests/unit/core/storage/persistence/test_market_persistence_serializer.py tests/unit/core/storage/persistence/test_postgres_market_persistence_repository.py tests/unit/application/persistence/market/test_market_persistence_service.py tests/unit/core/database/test_market_persistence_models.py tests/unit/core/database/test_market_event_volatility_forecast_migration.py --explicit-package-bases`.
- Refreshed the local Graphify map with `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`.

### Step 15 Results

- Updated the root application persistence export boundary to include `MarketEventSnapshotPersistenceFilters`, keeping the market-event persistence filter available from `application.persistence` after Step 14 added first-class market-event persistence.
- Cleaned up telemetry persistence package exports so `application.persistence.telemetry.__all__` remains limited to service/filter contracts. `TelemetryPersistenceMapper`, `TelemetryPersistenceSink`, and `TelemetryPersistenceSinkConfig` remain importable from their concrete modules, but are no longer re-exported through the application persistence boundary.
- Updated telemetry mapper/sink tests to import mapper and sink implementation types from their concrete modules instead of the service/filter-only package boundary.
- Audited active persistence/database source for removed market legacy physical column names (`advancing_count`, `declining_count`, `new_highs_count`, `new_lows_count`, `advance_decline_line`, `percent_above_50dma`, `percent_above_200dma`, `indicator_outputs`, `analysis_outputs`, and legacy mapped-column targets) and found no remaining active references in `core/database/models`, `core/storage/persistence`, or `application/persistence`.
- Focused verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check --fix ...`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format ...`, `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/persistence/test_application_persistence_exports.py tests/unit/application/persistence/telemetry/test_telemetry_event_mapper.py tests/unit/application/persistence/telemetry/test_telemetry_persistence_sink.py tests/unit/application/persistence/market/test_market_persistence_service.py tests/unit/core/database/test_market_persistence_models.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/storage/persistence/test_market_persistence_contracts.py tests/unit/core/storage/persistence/test_market_persistence_serializer.py tests/unit/core/storage/persistence/test_postgres_market_persistence_repository.py` (`103 passed`), and `UV_CACHE_DIR=/tmp/uv-cache uv run mypy application/persistence/__init__.py application/persistence/telemetry/__init__.py tests/unit/application/persistence/test_application_persistence_exports.py tests/unit/application/persistence/telemetry/test_telemetry_event_mapper.py tests/unit/application/persistence/telemetry/test_telemetry_persistence_sink.py tests/unit/application/persistence/market/test_market_persistence_service.py tests/unit/core/database/test_market_persistence_models.py tests/unit/core/database/test_model_output_coverage.py tests/unit/core/storage/persistence/test_market_persistence_contracts.py tests/unit/core/storage/persistence/test_market_persistence_serializer.py tests/unit/core/storage/persistence/test_postgres_market_persistence_repository.py --explicit-package-bases`.
- Additional note: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/integration/telemetry/test_telemetry_coverage_audit.py` still has an existing unrelated failure in `test_trace_identity_is_auditable_across_runtime_boundaries` (`KeyError: 'trace_id'`). The Step 15 import cleanup in that file is syntactically valid, but the failing assertion is outside this database-model export/import cleanup step.
- Refreshed the local Graphify map with `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`.

### Step 16 Results

- Added `tests/unit/core/database/test_schema_migration_contract.py` as an aggregate schema/migration contract test for the core database model update work.
- The new test verifies that the updated database models are importable from `core.database.models` and bound to the expected SQLAlchemy metadata tables for market events, technical analysis, market context, breadth, portfolio state, portfolio positions, macro regime, sentiment, news, and agent-intelligence outputs.
- Added metadata assertions for canonical columns introduced or renamed by this plan, including explicit `_payload` JSONB boundary columns, `cash_pct`, `exposure_weight`, `published_at`, `market_bias`, `composite_sentiment`, and the market technical/context/breadth canonical fields.
- Added negative metadata assertions that the dropped legacy physical column names are absent from the final schema, including generic `inputs` / `outputs`, technical `directional_score` / `indicator_outputs` / `analysis_outputs`, breadth `advancing_count` / `advance_decline_line` style names, portfolio `cash_ratio` / `weight`, sentiment legacy names, and `published_timestamp`.
- Added index coverage checks for the newly important query paths, including market events, strategy environment, breadth risk/strategy environment, portfolio account/status, portfolio-position workflow/account lookups, macro/sentiment market bias, and news `published_at`.
- Added Alembic migration-chain checks for revisions `20260613_0001` through `20260613_0009`, proving they import cleanly, expose upgrade/downgrade functions, form a single linear upgrade path from previous schema revision `20260606_0001` to current head `20260613_0009`, and that refactor migrations do not rebuild existing tables with `op.create_table` / `op.drop_table`.
- Focused verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check --fix tests/unit/core/database/test_schema_migration_contract.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format tests/unit/core/database/test_schema_migration_contract.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_schema_migration_contract.py` (`7 passed`), `UV_CACHE_DIR=/tmp/uv-cache uv run mypy tests/unit/core/database/test_schema_migration_contract.py --explicit-package-bases`, `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_schema_migration_contract.py tests/unit/core/database/test_alembic_foundation.py tests/unit/core/database/test_market_technical_payload_migration.py tests/unit/core/database/test_market_event_volatility_forecast_migration.py tests/unit/core/database/test_model_output_coverage.py` (`29 passed`), and the focused migration suite for the `20260613_0001`-`20260613_0009` plan migrations (`57 passed`).
- The Alembic tests emit the existing configuration deprecation warning about `path_separator`; no Step 16 test failed.
- Refreshed the local Graphify map with `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`.

### Step 17 Results — Add persistence round-trip tests

- Added `tests/unit/core/storage/persistence/test_realistic_output_roundtrip_contracts.py`.
- Covered realistic persistence round trips for:
  - `TechnicalAnalysisService`-style technical snapshot outputs,
  - market breadth analysis,
  - market context derivation including `top_50_constituents_payload` and `market_caps_payload`,
  - `MarketEventsService` event snapshots,
  - portfolio state/equity, position, and risk persistence,
  - macro regime outputs,
  - sentiment outputs with optional/missing field handling,
  - news analysis outputs with full LLM response preservation,
  - representative agent signal and agent reasoning outputs.
- Verified canonical persistence columns/payload columns are populated and that legacy non-canonical names are not required for model construction.
- Verified nested payload preservation, full numeric precision preservation, optional empty payload round trips, and read-back into typed persistence representations.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/storage/persistence/test_realistic_output_roundtrip_contracts.py
# 4 passed

UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/storage/persistence/test_realistic_output_roundtrip_contracts.py tests/unit/core/storage/persistence/test_market_persistence_serializer.py tests/unit/core/storage/persistence/test_portfolio_persistence_serializer.py tests/unit/core/storage/persistence/test_macro_persistence_serializer.py tests/unit/core/storage/persistence/test_sentiment_persistence_serializer.py tests/unit/core/storage/persistence/test_news_persistence_serializer.py tests/unit/core/storage/persistence/test_agent_signal_persistence_serializer.py tests/unit/core/storage/persistence/test_agent_intelligence_persistence_serializer.py
# 28 passed

UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/unit/core/storage/persistence/test_realistic_output_roundtrip_contracts.py --fix
UV_CACHE_DIR=/tmp/uv-cache uv run ruff format tests/unit/core/storage/persistence/test_realistic_output_roundtrip_contracts.py
UV_CACHE_DIR=/tmp/uv-cache uv run mypy tests/unit/core/storage/persistence/test_realistic_output_roundtrip_contracts.py --explicit-package-bases
# ruff passed; format applied; mypy passed

GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
# graph updated
```

### Step 18 Results — Update documentation / architectural notes

- Updated `.docs/postgres_persistence.md` with a new `Persistence data contract convention` section.
- Documented that PostgreSQL is the curated platform system-of-record.
- Documented that ORM models should expose canonical relational query fields while preserving complete nested service, agent, and report outputs in JSON/JSONB payload columns.
- Documented that legacy schema names should not be preserved after canonical replacements are approved.
- Documented persistence as an acceptable serialization boundary for JSON/JSONB while keeping internal service and intelligence contracts typed where feasible.
- Reinforced full numeric precision and full LLM/report text preservation at the persistence boundary.

Verification:

```bash
git diff -- .docs/postgres_persistence.md
# reviewed documentation-only diff

GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
# graphify reported no code-graph topology changes for the documentation-only update
```

### Step 19 Results — Verification

- Ran the full plan verification sequence.
- `ruff check . --fix` completed successfully and fixed 3 lint issues.
- `ruff format .` completed successfully and reformatted 455 files; a follow-up format check reported all files already formatted.
- Full-project mypy was executed. It still fails only on the previously acknowledged unrelated file `application/services/base/service_request.py`:
  - `application/services/base/service_request.py:29: error: "RequestPayloadT" is a type variable and only valid in type context [misc]`
- Focused persistence/database/application persistence tests passed.
- Relevant no-live-PostgreSQL integration tests passed.
- `POLARIS_TEST_DATABASE_URL` was not set, so no live PostgreSQL integration run was available for this step.
- Graphify was updated after verification.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check . --fix
# Found 3 errors (3 fixed, 0 remaining).

UV_CACHE_DIR=/tmp/uv-cache uv run ruff format .
# 455 files reformatted, 517 files left unchanged

UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
# All checks passed!

UV_CACHE_DIR=/tmp/uv-cache uv run ruff format . --check
# 972 files already formatted

UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases
# Failed only on the previously acknowledged unrelated service_request.py error.

UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/core/database tests/unit/core/storage tests/unit/application/persistence
# 978 passed, 2 warnings

UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/integration/application/persistence/test_persistence_services_with_fakes.py tests/integration/workflow/test_runtime_persistence_disabled_workflow.py
# 2 passed

GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
# graph updated
```
