# PortfolioState Dataclass Update

The PortfolioState dataclass in domain/portfolio/models/portfolio_state.py has been significantly expanded as well as the portfolio services files that are responsible for producing portfolio related data.
This update includes new fields that provide a comprehensive view of the portfolio's performance and exposure.
The goal of the this plan is to refactor and update all downstream files and code to utilize these new fields effectively as well the new fields produced by the other portfolio services files.

## New Portfolio and Portfolio Service Added Data

The following portfolio files have been updated and include the new data brought about by the changes to the PortfolioState dataclass update:

domain/portfolio/models/portfolio_state.py
application/services/portfolio/portfolio_service.py
application/services/portfolio/portfolio_analysis.py
application/services/portfolio/portfolio_equity.py
application/services/portfolio/portfolio_positions.py

## Analysis Summary

The PortfolioState dataclass in domain/portfolio/models/portfolio_state.py has been significantly expanded with new fields including:

### New Field Categories Added:

1. PnL breakdown: realized_pnl_pct, unrealized_pnl_pct, unrealized_intraday_pnl, unrealized_intraday_pnl_pct, pnl_total_pct
2. Market values: long_market_value, short_market_value, gross_market_value, net_market_value
3. Exposure metrics: gross_exposure, net_exposure, long_exposure, short_exposure, leverage
4. Risk metrics: largest_position_pct, concentration_score, diversification_score, beta_exposure, beta_risk, portfolio_heat, risk_intensity
5. Margin tracking: initial_margin, maintenance_margin, last_maintenance_margin, margin_utilization_ratio, initial_margin_ratio
6. Trading status flags: daytrade_count, pattern_day_trader, trading_blocked, transfers_blocked, account_blocked, trade_suspended_by_user, shorting_enabled
7. Account state: position_count, portfolio_regime, directional_bias
8. Exposure dictionaries: sector_exposure, asset_class_exposure
9. Default values: Many float fields now have default value of 0.0

The schema_version has been bumped from 1 to 2.

### Analyze Changes

Analyze the changes made to the files listed above to understand the scope of the updates and refactoring needed for downstream files.
The following list of downstream files below is not exhaustive, but it includes the most relevant files that may require updates due to the changes made in the portfolio-related files.
Modifications to some of these files have already begun like: core/database/models/portfolio_state.py and core/storage/persistence/serializers/portfolio_state_serializer.py.
Add any additional downstream files to the list as needed during the analysis and implementation process.
Likewise, you may find that some of the files listed below do not require updates after your analysis, so you can remove them from the list as you go through the implementation steps.

Downstream Files:
- application/persistence/portfolio/portfolio_persistence_service.py
- core/storage/persistence/repositories/postgres_portfolio_state_repository.py
- core/storage/persistence/serializers/portfolio_state_serializer.py
- intelligence/portfolio/management/portfolio_state_builder.py
- intelligence/portfolio/management/portfolio_manager_agent.py
- intelligence/risk/drawdown/drawdown_risk_agent.py
- intelligence/risk/exposure/exposure_risk_agent.py
- intelligence/execution/execution_risk/execution_risk_guard.py
- application/reports/morning_report_assembler.py
- tests/unit/application/persistence/portfolio/test_portfolio_persistence_service.py
- tests/unit/application/services/test_canonical_service_entrypoints.py
- tests/unit/core/database/test_portfolio_state_persistence_models.py

## Implementation Plan

### Phase 1: Database Schema Update

Update core/database/models/portfolio_state.py to add new columns:

#### PortfolioStateHistoryModel Changes:

- Add new Float columns: last_equity, realized_pnl_pct, unrealized_pnl_pct, unrealized_intraday_pnl, unrealized_intraday_pnl_pct, pnl_total_pct, long_market_value, short_market_value, gross_market_value, net_market_value,
gross_exposure, net_exposure, long_exposure, short_exposure, leverage, largest_position_pct, concentration_score, diversification_score, beta_exposure, beta_risk, portfolio_heat, risk_intensity, initial_margin,
maintenance_margin, last_maintenance_margin, margin_utilization_ratio, initial_margin_ratio
- Add new Boolean columns: daytrade_count, pattern_day_trader, trading_blocked, transfers_blocked, account_blocked, trade_suspended_by_user, shorting_enabled, buying_power_ratio
- Add new String columns: position_count, portfolio_regime, directional_bias
- Add JSONB columns: sector_exposure, asset_class_exposure, cash_ratio, equity_retention_ratio, capital_base
- Update default schema_version to 2
- Update nullable constraint for account_health to nullable=True

#### PortfolioStateLatestModel Changes:

- Apply identical column additions to mirror PortfolioStateHistoryModel

### Phase 2: Serializer Updates

Update core/storage/persistence/serializers/portfolio_state_serializer.py:

- Add all new fields to to_history_model()
- Add all new fields to to_latest_model()
- Add all new fields to from_latest_model()

### Phase 3: Migration

Create database migration to add the new columns to existing tables.

### Phase 4: Testing
- Write unit tests for PortfolioStateHistoryModel and PortfolioStateLatestModel.

# New Codex Proposed Implementation Plan

## Summary

This revised plan completes the expanded `PortfolioState` v2 adoption end-to-end instead of treating the change as only a database/schema update.

Canonical flow:

```text
Alpaca Client
  → Portfolio Provider
  → Portfolio Service
  → PortfolioState v2 domain object
  → Persistence
  → PortfolioStateBuilder
  → Risk / Portfolio / Execution agents
  → Morning report output
```

Architecture constraints:

- Agents consume service/runtime outputs, never Alpaca SDK/vendor payloads.
- `PortfolioState` remains the canonical typed domain object.
- Dicts are acceptable only at provider/client, runtime output, persistence, and report boundaries.
- No autonomous trading behavior is introduced.
- Core database/storage persistence edits are authorized for this feature.
- Full numeric precision is preserved internally; rounding is presentation-only.

## Important Corrections to the Existing Plan

- Correct field types:
  - `daytrade_count` and `position_count` are integers.
  - `pattern_day_trader`, `trading_blocked`, `transfers_blocked`, `account_blocked`, `trade_suspended_by_user`, and `shorting_enabled` are booleans.
  - `cash_ratio`, `buying_power_ratio`, `equity_retention_ratio`, and `capital_base` are floats.
  - `sector_exposure` and `asset_class_exposure` are JSON/dict boundary fields.
- Fix already-visible implementation gaps:
  - `PortfolioStateSerializer.from_latest_model()` currently restores only v1 fields.
  - `PostgresPortfolioStateRepository.persist_snapshot()` upserts only v1 latest fields.
  - `PostgresPortfolioStateRepository.get_history()` reconstructs only v1 fields.
  - `core/database/models/portfolio_state.py` appears to contain duplicate mapped fields such as `cash_ratio`, `equity_retention_ratio`, `created_at`, and `updated_at`.
  - Boolean DB fields should use SQLAlchemy `Boolean`, not `Integer`, unless there is a deliberate legacy constraint.
  - `PortfolioService.to_portfolio_state()` has key lookup bugs such as `"trading_blocked, False"` and stale key names like `margin_utilization`.
  - `PortfolioStateBuilder` currently derives positions from `portfolio_state["positions"]`, but positions are returned under `positions_state`.
  - `AlpacaPortfolioClient.get_full_portfolio_snapshot()` should not wrap async methods in `asyncio.to_thread()`.

## Implementation Steps

Each step should be completed independently, verified, documented in the `## Step Results` section, and then paused for review before starting the next step.

### Step 1 — Append the New Plan to the Plan File

Update `.agent/plans/plan_alpaca_portfolio_data_update.md` by appending this recommended plan under `# New Codex Proposed Implementation Plan`.

Also add a `## Step Results` section at the bottom if one does not already exist.

Verification:

```bash
rg "New Codex Proposed Implementation Plan|Step Results" .agent/plans/plan_alpaca_portfolio_data_update.md
```

### Step 2 — Establish the Canonical PortfolioState v2 Field Contract

Review `domain/portfolio/models/portfolio_state.py` and confirm the canonical field list, defaults, and types.

Implementation details:

- Keep `schema_version = 2`.
- Prefer `@dataclass(frozen=True, slots=True)` if practical, unless current mutation patterns prevent it.
- Do not add speculative fields.
- Ensure defaults are safe for missing Alpaca/backtest data.
- Preserve full numeric precision; do not round internal values.

Verification:

- Add or update a focused domain test confirming default values and v2 schema fields.
- Confirm no fields from the current v2 contract are missing.

### Step 3 — Fix Alpaca Client Async Snapshot Behavior

Update `integration/clients/portfolio/alpaca_portfolio_client.py`.

Implementation details:

- Keep the client responsible only for Alpaca SDK access and JSON/vendor-boundary normalization.
- Fix `get_full_portfolio_snapshot()` to gather the async methods directly:

```python
account, positions, portfolio = await asyncio.gather(
    self.get_account(),
    self.get_positions(),
    self.get_portfolio_history(),
)
```

- Do not introduce domain logic into the client.
- Keep Alpaca placeholders such as `sector` and `beta` deterministic until a proper enrichment provider exists.

Verification:

- Add/update a unit test with mocked async methods confirming the combined snapshot returns resolved dict/list values, not coroutine objects.

### Step 4 — Complete Backtest/Simulated Portfolio Data Parity

Update the simulated/backtest portfolio provider path so it can supply fields needed by the v2 service path.

Implementation details:

- Add deterministic account fields where available:
  - `id`
  - `last_equity`
  - `long_market_value`
  - `short_market_value`
  - `initial_margin`
  - `maintenance_margin`
  - account restriction flags
  - `daytrade_count`
- Add deterministic position fields where available:
  - `cost_basis`
  - `unrealized_pl`
  - `unrealized_plpc`
  - `unrealized_intraday_pl`
  - `unrealized_intraday_plpc`
  - `asset_class`
  - `sector`
  - `beta`
- Use neutral defaults where simulated data cannot know a live broker value.

Verification:

- Add/update simulated provider tests confirming live-compatible keys exist.

### Step 5 — Fix Portfolio Service v2 Mapping Bugs

Update `application/services/portfolio/portfolio_service.py`.

Implementation details:

- Fix incorrect key lookups:
  - `last_maintenance_margin`
  - `margin_utilization_ratio`
  - `trading_blocked`
  - `transfers_blocked`
  - `trade_suspended_by_user`
- Source `directional_bias` from portfolio analytics, not equity state.
- Source `risk_signals` from a merged or deliberate canonical risk signal packet, not only equity state.
- Confirm `to_portfolio_state()` fills every `PortfolioState` v2 field.
- Keep provider data access inside the service; do not let agents call providers.

Verification:

- Add/update a service test that builds a `PortfolioState` from representative account, positions, and portfolio history data and asserts v2 fields are populated.

### Step 6 — Verify Portfolio Analysis, Equity, and Position Calculations

Review and adjust:

- `application/services/portfolio/portfolio_analysis.py`
- `application/services/portfolio/portfolio_equity.py`
- `application/services/portfolio/portfolio_positions.py`

Implementation details:

- Ensure all v2 fields used by `PortfolioService.to_portfolio_state()` are produced with matching names.
- Preserve full precision.
- Keep rounding out of these files.
- Do not introduce large refactors unless needed to fix incorrect field production.
- Keep dicts here only as service-boundary/transitional structures; the service should convert to `PortfolioState`.

Verification:

- Add/update tests for:
  - no-position portfolio
  - long-only portfolio
  - mixed long/short portfolio
  - margin/account restriction flags
  - PnL percentage calculations

### Step 7 — Repair Database Model Definitions

Update `core/database/models/portfolio_state.py`.

Implementation details:

- Ensure `PortfolioStateHistoryModel` and `PortfolioStateLatestModel` mirror `PortfolioState` v2.
- Remove duplicate mapped columns.
- Use correct SQLAlchemy types:
  - `Float` for numeric ratios/amounts.
  - `Integer` for counts.
  - `Boolean` for flags.
  - `String` for regimes/status text.
  - `JSONB` for exposure dicts and risk signals.
- Keep `account_health` nullable if legacy rows may not have it.
- Keep schema defaults additive and non-destructive.

Verification:

- Update model tests to assert the key v2 columns and correct SQLAlchemy types.

### Step 8 — Add an Additive Alembic Migration

Create a migration for v2 portfolio state columns.

Implementation details:

- Add missing columns to both `portfolio_state_history` and `portfolio_state_latest`.
- Use additive, non-destructive migration operations.
- Include server defaults where needed to avoid breaking existing rows.
- Remove defaults afterward only if that is the repo’s existing Alembic pattern.
- Include downgrade logic that removes only the added v2 columns.

Verification:

- Run Alembic syntax/import validation.
- Confirm migration references correct table and column names.

### Step 9 — Complete Serializer Round Trip

Update `core/storage/persistence/serializers/portfolio_state_serializer.py`.

Implementation details:

- `to_history_model()` must serialize all v2 fields.
- `to_latest_model()` must serialize all v2 fields.
- `from_latest_model()` must restore all v2 fields.
- Prefer a small internal helper only if it reduces duplicated field lists without over-abstracting.

Verification:

- Update serializer tests so `restored_state == state` for a fully populated v2 `PortfolioState`.

### Step 10 — Complete Repository Latest and History Persistence

Update `core/storage/persistence/repositories/postgres_portfolio_state_repository.py`.

Implementation details:

- Latest upsert must include all v2 fields in both insert values and conflict update values.
- `get_history()` should use the serializer or a shared hydration path instead of manually reconstructing only v1 fields.
- Preserve current commit behavior unless a test reveals it is wrong.
- Do not alter unrelated repository contracts.

Verification:

- Add/update repository tests for:
  - latest upsert preserves v2 fields
  - history read preserves v2 fields
  - JSON exposure fields round-trip

### Step 11 — Update Application Persistence Service Coverage

Update tests and only adjust `application/persistence/portfolio/portfolio_persistence_service.py` if needed.

Implementation details:

- Confirm the application persistence service can persist and retrieve v2 `PortfolioState`.
- Avoid changing unrelated expanded portfolio persistence models unless directly required.
- Preserve the distinction between account-level `PortfolioState` and separate portfolio expansion records.

Verification:

- Update `tests/unit/application/persistence/portfolio/test_portfolio_persistence_service.py` fixture to include representative v2 fields.

### Step 12 — Update PortfolioStateBuilder Runtime Output

Update `intelligence/portfolio/management/portfolio_state_builder.py`.

Implementation details:

- Use `positions_state["positions"]`, not `portfolio_state["positions"]`.
- Surface v2 fields in output features:
  - `portfolio_state`
  - `equity_state`
  - `positions_state`
  - `risk_features`
- Include account restriction and margin fields in risk features where useful.
- Do not recompute canonical exposure if already produced by `PortfolioService`.
- Keep runtime output serialized as dicts at the runtime boundary.

Verification:

- Add/update a unit test for builder output shape and v2 field propagation.

### Step 13 — Update Portfolio and Risk Agents to Consume v2 Fields

Review and update as needed:

- `intelligence/portfolio/management/portfolio_manager_agent.py`
- `intelligence/risk/drawdown/drawdown_risk_agent.py`
- `intelligence/risk/exposure/exposure_risk_agent.py`
- `intelligence/execution/execution_risk/execution_risk_guard.py`

Implementation details:

- Prefer canonical v2 fields from `PortfolioStateBuilder`.
- Use `drawdown_percent`, `risk_intensity`, `portfolio_heat`, `margin_utilization_ratio`, `concentration_score`, `leverage`, and account restriction flags where relevant.
- Do not introduce vendor-specific Alpaca assumptions.
- Do not create order execution behavior.
- Keep changes surgical because these files have elevated health/risk concerns.

Verification:

- Add focused tests or fixture assertions for agent behavior with blocked/restricted account state and high portfolio risk.

### Step 14 — Update Morning Report Portfolio Rendering

Update `application/reports/morning_report_assembler.py`.

Implementation details:

- Render new v2 data in a professional portfolio section:
  - portfolio value
  - cash/cash ratio
  - realized/unrealized/intraday PnL
  - gross/net/long/short exposure
  - leverage
  - concentration/diversification
  - margin utilization
  - account health and restrictions
  - portfolio regime and directional bias
- Keep rounding only in report formatting.
- Do not truncate underlying LLM/report content.
- Preserve existing report structure and avoid large unrelated report rewrites.

Verification:

- Update morning report assembler tests to assert the new fields appear in report sections/tables.

### Step 15 — Review API/CLI Boundary Impact

Review:

- `interfaces/api/routes/portfolio.py`
- CLI/report output paths that consume morning report data
- Any workflow output renderer consuming portfolio state

Implementation details:

- Only change boundary serialization if tests or current code show missing v2 output.
- Keep boundary output dict/JSON-friendly.
- Do not add new CLI flags unless required.

Verification:

- Run existing CLI/report rendering tests touched by portfolio output.

### Step 16 — Add/Update Integration-Level Portfolio Service Test

Add or update a scoped integration-style test that runs:

```text
fake provider
  → PortfolioService
  → PortfolioState
  → serializer/repository boundary where feasible
```

Implementation details:

- Use fake provider data; do not call Alpaca.
- Confirm v2 fields survive the service path.
- Confirm defaults are safe when provider data is missing.

Verification:

- Run the new integration/service test directly.

### Step 17 — Run Focused Validation

Run focused tests first:

```bash
uv run pytest -q \
  tests/unit/core/database/test_portfolio_state_persistence_models.py \
  tests/unit/application/persistence/portfolio/test_portfolio_persistence_service.py \
  tests/unit/application/services/test_canonical_service_entrypoints.py \
  tests/unit/application/reports/morning/test_morning_report_assembler.py
```

Then run any new/updated tests added during the implementation.

### Step 18 — Run Static Checks

Run:

```bash
uv run ruff check .
uv run mypy .
```

If full-project checks reveal unrelated existing failures, document them clearly and run the most relevant scoped checks instead.

### Step 19 — Update Plan Step Results

After validation, update the bottom `## Step Results` section in `.agent/plans/plan_alpaca_portfolio_data_update.md`.

Include:

- files changed
- tests run
- pass/fail status
- any known follow-up work
- any intentionally deferred non-blocking cleanup

### Step 20 — Final Diff Review

Review the final diff before commit.

Implementation details:

- Confirm every changed line traces to this feature.
- Confirm no vendor SDK access leaked above the integration client/provider layer.
- Confirm no internal rounding was introduced.
- Confirm no autonomous trading behavior was introduced.
- Confirm no unrelated dirty files were accidentally included.

Verification:

```bash
git diff --check
git status --short
```

## Test Plan

Minimum required test coverage:

- `PortfolioState` v2 defaults and schema version.
- Alpaca combined snapshot resolves async values correctly.
- Simulated/backtest provider emits live-compatible keys.
- Portfolio service builds a fully populated v2 `PortfolioState`.
- Portfolio DB models expose correct column types.
- Serializer round-trips all v2 fields.
- Repository latest/history persistence preserves all v2 fields.
- PortfolioStateBuilder runtime output includes v2 portfolio, equity, positions, and risk features.
- Risk/portfolio/execution agents consume v2 fields without vendor coupling.
- Morning report renders v2 portfolio data professionally.

## Assumptions and Defaults

- Core database/storage persistence edits are authorized for this feature.
- This feature remains recommendation-only and does not add autonomous trade execution.
- Alpaca is treated as a live data source only through the client/provider layer.
- Missing Alpaca or simulated fields default to neutral safe values.
- Full numeric precision is preserved internally.
- Rounding is allowed only in report/CLI presentation.
- If full-project `mypy` or `ruff` failures are unrelated to this work, they will be documented rather than fixed opportunistically.

## Step Results

### Step 1 — Append the New Plan to the Plan File

Status: Completed.

Files changed:

- `.agent/plans/plan_alpaca_portfolio_data_update.md`

Verification:

- Added `# New Codex Proposed Implementation Plan`.
- Added `## Step Results` at the bottom of the file.
- Next step: Step 2 — Establish the Canonical PortfolioState v2 Field Contract.

### Step 2 — Establish the Canonical PortfolioState v2 Field Contract

Status: Completed.

Files changed:

- `domain/portfolio/models/portfolio_state.py`
- `tests/unit/domain/test_portfolio_state.py`

Implementation notes:

- Confirmed `PortfolioState` is the canonical schema-version-2 domain contract.
- Updated `PortfolioState` to use `@dataclass(frozen=True, slots=True)` because no current field-mutation usage was found and platform rules prefer immutable typed domain objects.
- Added focused tests for v2 defaults, expected field contract coverage, and immutability.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/domain/test_portfolio_state.py
```

Result: Passed — `3 passed`.

Next step: Step 3 — Fix Alpaca Client Async Snapshot Behavior.

### Step 3 — Fix Alpaca Client Async Snapshot Behavior

Status: Completed.

Files changed:

- `integration/clients/portfolio/alpaca_portfolio_client.py`
- `tests/unit/integration/clients/portfolio/test_alpaca_portfolio_client.py`
- `graphify-out/` generated graph files updated by `graphify update .`

Implementation notes:

- Replaced the incorrect `asyncio.to_thread(self.get_account)` pattern in `get_full_portfolio_snapshot()` with direct `asyncio.gather()` over the existing async client methods.
- Added a focused unit test that instantiates the client without calling Alpaca credentials or the SDK constructor, monkeypatches async data methods, and verifies the combined snapshot contains resolved values rather than awaitable/coroutine objects.
- Kept Alpaca SDK access isolated inside the integration client boundary.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/clients/portfolio/test_alpaca_portfolio_client.py
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check integration/clients/portfolio/alpaca_portfolio_client.py tests/unit/integration/clients/portfolio/test_alpaca_portfolio_client.py
UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
```

Results:

- Pytest passed — `1 passed, 1 warning`.
- Ruff passed.
- Graphify update completed.

Next step: Step 4 — Complete Backtest/Simulated Portfolio Data Parity.


### Step 4 — Complete Backtest/Simulated Portfolio Data Parity

Status: Completed.

Files changed:

- `backtesting/providers/portfolio/simulated_portfolio_provider.py`
- `tests/unit/backtesting/providers/portfolio/test_simulated_portfolio_provider.py`
- `tests/unit/integration/providers/portfolio/test_backtest_portfolio_provider.py`
- `graphify-out/` generated graph files updated by `graphify update .`

Implementation notes:

- Added deterministic live-compatible account fields to the simulated provider, including account identity, prior equity, long/short market values, margin fields, account restriction flags, day-trading fields, options levels, buying-power variants, and neutral transfer/fee defaults.
- Added deterministic live-compatible position fields, including `qty`, `qty_available`, `avg_entry_price`, `cost_basis`, realized-compatible unrealized PnL fields, intraday neutral defaults, asset metadata, sector, and beta.
- Added small `SimPosition` helper methods for cost basis and unrealized PnL calculations to keep the provider output internally consistent without introducing service or domain logic into the provider.
- Kept simulated-only unknown broker values as neutral deterministic defaults.
- Added direct simulated-provider coverage and backtest-wrapper coverage because Repowise flagged the provider path as an untested hotspot/test gap.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/backtesting/providers/portfolio/test_simulated_portfolio_provider.py tests/unit/integration/providers/portfolio/test_backtest_portfolio_provider.py
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check backtesting/providers/portfolio/simulated_portfolio_provider.py tests/unit/backtesting/providers/portfolio/test_simulated_portfolio_provider.py tests/unit/integration/providers/portfolio/test_backtest_portfolio_provider.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
```

Results:

- Pytest passed — `3 passed`.
- Ruff passed.
- Graphify update completed.

Next step: Step 5 — Fix Portfolio Service v2 Mapping Bugs.

### Step 5 — Fix Portfolio Service v2 Mapping Bugs

Status: Completed.

Files changed:

- `application/services/portfolio/portfolio_service.py`
- `tests/unit/application/services/portfolio/test_portfolio_service.py`
- `tests/unit/application/services/test_canonical_service_entrypoints.py`
- `graphify-out/` generated graph files updated by `graphify update .`

Implementation notes:

- Fixed incorrect v2 key lookups for `last_maintenance_margin`, `margin_utilization_ratio`, `trading_blocked`, `transfers_blocked`, and `trade_suspended_by_user`.
- Changed `directional_bias` mapping to source from portfolio analytics instead of equity state.
- Changed PnL mapping so aggregate unrealized values come from the portfolio analytics packet, with an intraday percentage fallback sourced from normalized position rows until Step 6 completes portfolio analytics parity.
- Replaced direct `float()`, `int()`, and `bool()` conversions with local safe conversion helpers so malformed or string boolean values do not silently map incorrectly.
- Merged `risk_signals` from equity, positions, and portfolio analytics instead of persisting only equity risk signals.
- Added focused service coverage that runs provider data through `PortfolioService`, captures the persisted `PortfolioState`, and asserts representative v2 fields are populated.
- Updated the canonical portfolio-service fake provider with an account id and portfolio-history boundary method so the canonical service entrypoint remains compatible with the current service contract.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/application/services/test_canonical_service_entrypoints.py::test_portfolio_service_canonical_run
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/services/portfolio/portfolio_service.py tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/application/services/test_canonical_service_entrypoints.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
```

Results:

- Pytest passed — `2 passed`.
- Ruff passed.
- Graphify update completed.

Next step: Step 6 — Verify Portfolio Analysis, Equity, and Position Calculations.

### Step 6 — Verify Portfolio Analysis, Equity, and Position Calculations

Status: Completed.

Files changed:

- `application/services/portfolio/portfolio_analysis.py`
- `application/services/portfolio/portfolio_positions.py`
- `tests/unit/application/services/portfolio/test_portfolio_calculations.py`
- `graphify-out/` generated graph files updated by `graphify update .`

Files reviewed with no source change required:

- `application/services/portfolio/portfolio_equity.py`

Implementation notes:

- Changed aggregate unrealized PnL percentage calculation to use total unrealized PnL divided by aggregate absolute cost basis instead of summing per-position percentages.
- Added aggregate unrealized intraday PnL percentage calculation and included the `unrealized_intraday_pnl_pct` key in both populated and empty portfolio analysis outputs.
- Treated empty portfolio-history payloads as no-history states instead of marking empty dictionaries as usable history.
- Fixed short-position default unrealized PnL in position enrichment so missing vendor PnL values use `cost_basis - market_value` for shorts and `market_value - cost_basis` for longs.
- Added focused coverage for no-position, long-only, mixed long/short, margin/account restriction flags, and PnL percentage calculations.
- Kept numeric precision intact; no rounding was introduced.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/portfolio/test_portfolio_calculations.py tests/unit/application/services/portfolio/test_portfolio_service.py
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/services/portfolio/portfolio_analysis.py application/services/portfolio/portfolio_equity.py application/services/portfolio/portfolio_positions.py tests/unit/application/services/portfolio/test_portfolio_calculations.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
git diff --check
```

Results:

- Pytest passed — `5 passed`.
- Ruff passed.
- Graphify update completed.
- `git diff --check` passed.

Next step: Step 7 — Repair Database Model Definitions.

### Step 7 — Repair Database Model Definitions

Status: Completed.

Files changed:

- `core/database/models/portfolio_state.py`
- `core/storage/persistence/serializers/portfolio_state_serializer.py`
- `tests/unit/core/database/test_portfolio_state_persistence_models.py`
- `graphify-out/` generated graph files updated by `graphify update .`

Implementation notes:

- Updated both `PortfolioStateHistoryModel` and `PortfolioStateLatestModel` so the SQLAlchemy model columns mirror the `PortfolioState` v2 field contract plus persistence metadata.
- Removed duplicate mapped column declarations from both model classes.
- Changed account restriction and brokerage capability flags to use SQLAlchemy `Boolean` instead of integer columns.
- Kept `account_health` nullable in both history/latest models for legacy row compatibility.
- Preserved `Float` for numeric ratios and amounts, `Integer` for counts/schema version, `String` for textual status/regime fields, and `JSONB` for risk/exposure payloads.
- Removed duplicate serializer keyword arguments that blocked test collection after the duplicate model-column repair.
- Added focused model tests for v2 domain field coverage, SQLAlchemy column types, JSONB fields, nullable account health, lineage/timestamps, and duplicate mapped attribute detection.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_portfolio_state_persistence_models.py
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check core/database/models/portfolio_state.py core/storage/persistence/serializers/portfolio_state_serializer.py tests/unit/core/database/test_portfolio_state_persistence_models.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
git diff --check
```

Results:

- Pytest passed — `7 passed`.
- Ruff passed.
- Graphify update completed.
- `git diff --check` passed.

Next step: Step 8 — Add an Additive Alembic Migration.

### Step 8 — Add an Additive Alembic Migration

Status: Completed.

Files changed:

- `migrations/versions/20260606_0001_add_portfolio_state_v2_columns.py`
- `tests/unit/core/database/test_portfolio_state_v2_migration.py`
- `tests/unit/application/persistence/health/test_health_persistence_service.py`
- `tests/unit/application/persistence/diagnostics/test_diagnostics_persistence_service.py`
- `tests/unit/core/storage/persistence/test_health_persistence_contracts.py`
- `graphify-out/` generated graph files updated by `graphify update .`

Implementation notes:

- Added linear Alembic revision `20260606_0001` after `20260530_0019`.
- Added v2 `PortfolioState` columns to both `portfolio_state_history` and `portfolio_state_latest` with additive `op.add_column()` operations.
- Used temporary server defaults for non-null existing-row safety, then dropped those server defaults so the database schema remains aligned with the SQLAlchemy model defaults.
- Used `Float` for numeric ratios/amounts, `Integer` for counts, `Boolean` for flags, `String` for nullable regime/bias text, and PostgreSQL `JSONB` for exposure dictionaries.
- Relaxed legacy `account_health` and `risk_signals` nullability to match the repaired models and support legacy/incomplete rows.
- Kept downgrade logic scoped to dropping only the newly added v2 columns.
- Updated persistence health/diagnostics tests that assert the current Alembic head from `20260530_0019` to `20260606_0001`.
- Added focused migration tests for importability, revision chain, target tables, expected v2 columns/types, additive behavior, and downgrade coverage.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_portfolio_state_v2_migration.py tests/unit/core/database/test_portfolio_state_persistence_models.py tests/unit/application/persistence/health/test_health_persistence_service.py tests/unit/application/persistence/diagnostics/test_diagnostics_persistence_service.py tests/unit/core/storage/persistence/test_health_persistence_contracts.py
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check migrations/versions/20260606_0001_add_portfolio_state_v2_columns.py tests/unit/core/database/test_portfolio_state_v2_migration.py tests/unit/application/persistence/health/test_health_persistence_service.py tests/unit/application/persistence/diagnostics/test_diagnostics_persistence_service.py tests/unit/core/storage/persistence/test_health_persistence_contracts.py
UV_CACHE_DIR=/tmp/uv-cache uv run python -m compileall -q migrations/versions/20260606_0001_add_portfolio_state_v2_columns.py
UV_CACHE_DIR=/tmp/uv-cache uv run alembic heads
UV_CACHE_DIR=/tmp/uv-cache uv run alembic upgrade head --sql
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
git diff --check
```

Results:

- Pytest passed — `25 passed`.
- Ruff passed.
- Migration compile/import validation passed.
- Alembic head validation passed — `20260606_0001 (head)`.
- Alembic offline SQL generation passed.
- Graphify update completed.
- `git diff --check` passed.

Next step: Step 9 — Complete Serializer Round Trip.

### Step 9 — Complete Serializer Round Trip

Status: Completed.

Files changed:

- `core/storage/persistence/serializers/portfolio_state_serializer.py`
- `tests/unit/core/database/test_portfolio_state_persistence_models.py`

Implementation notes:

- Replaced partial v1 serializer field lists with a small dataclass-field helper so history/latest persistence serialization covers every `PortfolioState` v2 field.
- Updated latest-model hydration to restore every v2 field into a `PortfolioState`.
- Added safe legacy nullable hydration for `account_health`, `portfolio_regime`, `directional_bias`, `risk_signals`, `sector_exposure`, and `asset_class_exposure`.
- Updated serializer tests to use a fully populated v2 `PortfolioState` with high-precision numeric values and all v2 flags/exposure/risk fields.
- Added assertions that every dataclass field is preserved in history model, latest model, and latest-model restoration.
- Deferred repository persistence/upsert changes to Step 10 per plan.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_portfolio_state_persistence_models.py
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check core/storage/persistence/serializers/portfolio_state_serializer.py tests/unit/core/database/test_portfolio_state_persistence_models.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
git diff --check
```

Results:

- Pytest passed — `8 passed`.
- Ruff passed.
- Graphify update completed with no code-graph topology changes.
- `git diff --check` passed.

Next step: Step 10 — Complete Repository Latest and History Persistence.

### Step 10 — Complete Repository Latest and History Persistence

Status: Completed.

Files changed:

- `core/storage/persistence/repositories/postgres_portfolio_state_repository.py`
- `core/storage/persistence/serializers/portfolio_state_serializer.py`
- `tests/unit/core/storage/persistence/test_postgres_portfolio_state_repository.py`
- `graphify-out/` generated graph files updated by `graphify update .`

Implementation notes:

- Replaced the repository's manual latest upsert field list with a dataclass-field-driven value helper so all `PortfolioState` v2 fields are included in latest insert values.
- Updated latest conflict update values to include every non-key v2 field, plus existing workflow/execution lineage fields and `updated_at = now()`.
- Added `PortfolioStateSerializer.from_history_model()` and changed `get_history()` to use the serializer instead of manually reconstructing a partial v1 `PortfolioState`.
- Preserved existing repository commit behavior.
- Added focused repository coverage for latest upsert v2 field coverage, latest read v2 round-trip behavior, history read v2 round-trip behavior, and JSON exposure/risk signal round trips.
- Kept Step 10 scoped to the repository/serializer persistence boundary; application persistence service coverage remains Step 11.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/storage/persistence/test_postgres_portfolio_state_repository.py tests/unit/core/database/test_portfolio_state_persistence_models.py
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check core/storage/persistence/repositories/postgres_portfolio_state_repository.py core/storage/persistence/serializers/portfolio_state_serializer.py tests/unit/core/storage/persistence/test_postgres_portfolio_state_repository.py tests/unit/core/database/test_portfolio_state_persistence_models.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
git diff --check
```

Results:

- Pytest passed — `11 passed`.
- Ruff passed.
- Graphify update completed and rebuilt `graphify-out/graph.json` plus `graphify-out/GRAPH_REPORT.md`.
- `git diff --check` passed.

Next step: Step 11 — Update Application Persistence Service Coverage.

### Step 11 — Update Application Persistence Service Coverage

Status: Completed.

Files changed:

- `tests/unit/application/persistence/portfolio/test_portfolio_persistence_service.py`
- `graphify-out/` generated graph files updated by `graphify update .`

Files reviewed with no source change required:

- `application/persistence/portfolio/portfolio_persistence_service.py`

Implementation notes:

- Kept the application persistence service unchanged because it already delegates account-level `PortfolioState` persistence and retrieval through the state repository without trimming fields.
- Updated the portfolio-state fixture from a partial v1-style state to a representative v2 `PortfolioState` with high-precision numeric values, margin fields, restriction flags, exposure dictionaries, and nested risk signals.
- Renamed the state repository coverage to v2 terminology and added explicit assertions for representative v2 fields returned through `get_latest_state()`.
- Preserved the separation between account-level `PortfolioState` state snapshots and separate portfolio expansion records.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/persistence/portfolio/test_portfolio_persistence_service.py
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/unit/application/persistence/portfolio/test_portfolio_persistence_service.py application/persistence/portfolio/portfolio_persistence_service.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
git diff --check
```

Results:

- Pytest passed — `9 passed`.
- Ruff passed.
- Graphify update completed and rebuilt `graphify-out/graph.json` plus `graphify-out/GRAPH_REPORT.md`.
- `git diff --check` passed.

Next step: Step 12 — Update PortfolioStateBuilder Runtime Output.

### Step 12 — Update PortfolioStateBuilder Runtime Output

Status: Completed.

Files changed:

- `intelligence/portfolio/management/portfolio_state_builder.py`
- `tests/unit/intelligence/portfolio/test_portfolio_state_builder.py`
- `graphify-out/` generated graph files updated by `graphify update .`

Implementation notes:

- Fixed portfolio position extraction to use canonical `positions_state["positions"]` instead of stale `portfolio_state["positions"]`.
- Preserved and augmented canonical `positions_state` instead of replacing it with only `positions` and `position_count`.
- Surfaced v2 equity fields in runtime output `features["equity_state"]`, including buying-power variants, market values, exposure ratios, margin fields, account restriction flags, options levels, and risk signals.
- Added useful v2 margin, cash, buying-power, account restriction, beta, heat, concentration, and diversification fields to `features["risk_features"]` while preserving existing keys for downstream compatibility.
- Kept `features["portfolio_state"]` as the canonical serialized service output and did not recompute canonical exposure in the runtime node.
- Added focused builder coverage proving v2 field propagation and guarding against the stale `portfolio_state["positions"]` bug.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/portfolio/test_portfolio_state_builder.py
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check intelligence/portfolio/management/portfolio_state_builder.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
git diff --check
```

Results:

- Pytest passed — `1 passed`.
- Ruff passed.
- Graphify update completed and rebuilt `graphify-out/graph.json` plus `graphify-out/GRAPH_REPORT.md`.
- `git diff --check` passed.

Next step: Step 13 — Update Portfolio and Risk Agents to Consume v2 Fields.

### Step 13 — Update Portfolio and Risk Agents to Consume v2 Fields

Status: Completed.

Files changed:

- `intelligence/portfolio/management/portfolio_manager_agent.py`
- `intelligence/risk/drawdown/drawdown_risk_agent.py`
- `intelligence/risk/exposure/exposure_risk_agent.py`
- `intelligence/execution/execution_risk/execution_risk_guard.py`
- `tests/unit/intelligence/portfolio/test_portfolio_manager_agent.py`
- `tests/unit/intelligence/risk/test_drawdown_risk_agent.py`
- `tests/unit/intelligence/risk/test_exposure_risk_agent.py`
- `tests/unit/intelligence/execution/test_execution_risk_guard.py`

Implementation notes:

- Updated portfolio manager risk posture to incorporate canonical v2 `portfolio_heat`, `risk_intensity`, `margin_utilization_ratio`, and hard account restriction flags from `PortfolioStateBuilder` output.
- Updated drawdown risk analysis to consume canonical v2 `drawdown_percent` and propagate margin/account restriction context.
- Updated exposure risk analysis to use canonical `positions_state["position_count"]`, v2 `concentration_score`, and v2 portfolio pressure fields instead of stale dictionary-length behavior.
- Updated execution risk guard to block hard account restrictions and include account restriction/margin context in `execution_guard` output.
- Added focused tests for restricted account handling, canonical v2 drawdown propagation, high portfolio exposure pressure, and blocked execution risk guard behavior.
- Kept changes surgical due elevated health/risk findings and did not introduce vendor-specific Alpaca assumptions or order execution behavior.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/portfolio/test_portfolio_state_builder.py tests/unit/intelligence/portfolio/test_portfolio_manager_agent.py tests/unit/intelligence/risk/test_drawdown_risk_agent.py tests/unit/intelligence/risk/test_exposure_risk_agent.py tests/unit/intelligence/risk/test_volatility_risk_agent.py tests/unit/intelligence/execution/test_execution_risk_guard.py
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check intelligence/portfolio/management/portfolio_manager_agent.py intelligence/risk/drawdown/drawdown_risk_agent.py intelligence/risk/exposure/exposure_risk_agent.py intelligence/execution/execution_risk/execution_risk_guard.py tests/unit/intelligence/portfolio/test_portfolio_manager_agent.py tests/unit/intelligence/risk/test_drawdown_risk_agent.py tests/unit/intelligence/risk/test_exposure_risk_agent.py tests/unit/intelligence/execution/test_execution_risk_guard.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
git diff --check
```

Results:

- Pytest passed — `11 passed`.
- Ruff passed.
- Graphify update completed; no code-graph topology changes were detected, so generated graph outputs were left untouched.
- `git diff --check` passed.

Next step: Step 14 — Update Morning Report Portfolio Rendering.

### Step 14 — Update Morning Report Portfolio Rendering

Status: Completed.

Files changed:

- `application/reports/morning_report_assembler.py`
- `tests/unit/application/reports/morning/test_morning_report_assembler.py`
- `graphify-out/` generated graph files updated by `graphify update .`

Implementation notes:

- Expanded the morning report `Portfolio Snapshot` section to render canonical v2 portfolio data in a human-readable financial-report structure.
- Added v2 portfolio summary metrics for leverage, margin utilization, portfolio regime, and directional bias while preserving existing portfolio value, cash, cash allocation, gross exposure, and net exposure metrics.
- Added professional portfolio tables for:
  - `Portfolio PnL` — total, realized, unrealized, and intraday unrealized PnL values.
  - `Portfolio Exposure` — gross/net/long/short market values, long/short exposure, and leverage.
  - `Portfolio Risk & Constraints` — position count, largest position, concentration, diversification, portfolio heat, risk intensity, drawdown, beta exposure/risk, margin utilization, account health, and account restrictions.
- Added account restriction formatting from canonical v2 flags without introducing vendor-specific Alpaca assumptions.
- Kept rounding strictly in report presentation formatters and did not truncate underlying LLM/report content.
- Kept changes scoped to the report rendering boundary due the assembler's hotspot/health risk profile.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/reports/morning/test_morning_report_assembler.py tests/unit/application/reports/morning/test_morning_report_renderer.py
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/reports/morning
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/reports/morning_report_assembler.py tests/unit/application/reports/morning/test_morning_report_assembler.py tests/unit/application/reports/morning/test_morning_report_renderer.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
git diff --check
```

Results:

- Focused pytest passed — `4 passed`.
- Morning report test package passed — `6 passed`.
- Ruff passed.
- Graphify update completed and rebuilt `graphify-out/graph.json` plus `graphify-out/GRAPH_REPORT.md`.
- `git diff --check` passed.

Next step: Step 15 — Review API/CLI Boundary Impact.

### Step 15 — Review API/CLI Boundary Impact

Status: Completed.

Files changed:

- `interfaces/cli/bootstrap/container.py`
- `tests/unit/interfaces/cli/output/test_workflow_output_renderer.py`
- `tests/unit/interfaces/cli/output/test_pdf_output_renderer.py`
- `tests/unit/interfaces/cli/test_workflow_rendering.py`
- `graphify-out/` generated graph files checked by `graphify update .`

Files reviewed with no report-boundary source change required:

- `interfaces/api/routes/portfolio.py`
- `interfaces/cli/commands/morning_report_command.py`
- `interfaces/cli/output/workflow_output_renderer.py`
- `interfaces/cli/output/pdf_output_renderer.py`
- `application/reports/morning_report_renderer.py`
- `application/reports/morning_report_persistence.py`

Implementation notes:

- Confirmed `interfaces/api/routes/portfolio.py` is currently empty, so there is no API serialization contract to adjust in this step.
- Confirmed CLI/report output already delegates through `render_workflow_output_bundle()`, `MorningReportAssembler`, and the typed markdown/PDF renderers, so no new CLI flags or report renderer abstractions were needed.
- Confirmed `MorningReportPersistenceMapper` persists `asdict(document)` plus per-section `asdict(section)`, so v2 portfolio metrics/tables remain JSON-friendly at the persistence boundary.
- Added CLI boundary coverage proving v2 portfolio fields render through default professional stdout, markdown artifacts, HTML artifacts, and PDF stdout paths.
- Added direct PDF renderer coverage for a portfolio section with table data so report table rendering remains exercised at the PDF boundary.
- Fixed a stale CLI bootstrap import from the removed repository compatibility path to the canonical `core.storage.persistence.portfolio.portfolio_state_repository` protocol so CLI boundary tests collect successfully.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/interfaces/cli/output/test_workflow_output_renderer.py tests/unit/interfaces/cli/output/test_pdf_output_renderer.py tests/unit/interfaces/cli/test_workflow_rendering.py tests/unit/application/reports/morning
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/unit/interfaces/cli/output/test_workflow_output_renderer.py tests/unit/interfaces/cli/output/test_pdf_output_renderer.py tests/unit/interfaces/cli/test_workflow_rendering.py application/reports/morning_report_renderer.py application/reports/morning_report_persistence.py interfaces/cli/output/workflow_output_renderer.py interfaces/cli/output/pdf_output_renderer.py interfaces/cli/commands/morning_report_command.py interfaces/cli/bootstrap/container.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
git diff --check
```

Results:

- Focused pytest passed — `51 passed, 1 warning`.
- Ruff passed.
- Graphify update completed; final run detected no topology changes and left generated graph outputs untouched.
- `git diff --check` passed.

Next step: Step 16 — Add/Update Integration-Level Portfolio Service Test.

### Step 16 — Add/Update Integration-Level Portfolio Service Test

Status: Completed.

Files changed:

- `tests/unit/application/services/portfolio/test_portfolio_service.py`
- `graphify-out/` generated graph files updated by `graphify update .`

Files reviewed with no production source change required:

- `application/services/portfolio/portfolio_service.py`
- `core/storage/persistence/serializers/portfolio_state_serializer.py`
- `core/storage/persistence/repositories/postgres_portfolio_state_repository.py`

Implementation notes:

- Added a `SerializingPortfolioRepository` test double that persists service output through `PortfolioStateSerializer.to_latest_model()`, `to_history_model()`, `from_latest_model()`, and `from_history_model()` before exposing the captured state.
- Added an integration-style service test for the fake provider path: provider data → `PortfolioService` → canonical `PortfolioState` → serializer boundary.
- Added coverage proving v2 fields survive that boundary, including intraday PnL, margin utilization, account restriction flags, shorting state, sector exposure, asset-class exposure, and merged risk signals.
- Added a sparse-provider default safety test proving missing provider data persists safe v2 defaults without calling Alpaca or any external provider.
- Kept changes test-only because the existing service and serializer path already preserved the required v2 fields.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/portfolio/test_portfolio_service.py
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/core/storage/persistence/test_postgres_portfolio_state_repository.py
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/unit/application/services/portfolio/test_portfolio_service.py core/storage/persistence/serializers/portfolio_state_serializer.py application/services/portfolio/portfolio_service.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
git diff --check
```

Results:

- Direct Step 16 pytest passed — `3 passed`.
- Focused service/repository pytest passed — `6 passed`.
- Ruff passed.
- Graphify update completed and rebuilt `graphify-out/graph.json` plus `graphify-out/GRAPH_REPORT.md`.
- `git diff --check` passed.

Next step: Step 17 — Run Focused Validation.

### Step 16 — Add/Update Integration-Level Portfolio Service Test

Status: Completed.

Files changed:

- `tests/unit/application/services/portfolio/test_portfolio_service.py`
- `graphify-out/` generated graph files updated by `graphify update .`

Files reviewed with no source change required:

- `application/services/portfolio/portfolio_service.py`
- `core/storage/persistence/serializers/portfolio_state_serializer.py`
- `tests/unit/core/storage/persistence/test_postgres_portfolio_state_repository.py`

Implementation notes:

- Added a scoped fake-provider service test that exercises `RepresentativePortfolioProvider → PortfolioService → PortfolioState → PortfolioStateSerializer` through a serializing fake repository.
- Confirmed representative v2 portfolio fields survive the service path and serializer/repository boundary, including intraday PnL, margin utilization, account restriction flags, sector exposure, asset-class exposure, and risk signals.
- Added a sparse fake-provider service test proving missing provider data safely defaults through the service and serializer boundary without calling Alpaca.
- Kept production portfolio service and serializer source unchanged because Repowise flagged both as high-churn/higher-risk files and existing code already satisfied Step 16 behavior under tests.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/portfolio/test_portfolio_service.py
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/core/storage/persistence/test_postgres_portfolio_state_repository.py
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/unit/application/services/portfolio/test_portfolio_service.py core/storage/persistence/serializers/portfolio_state_serializer.py application/services/portfolio/portfolio_service.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
git diff --check
```

Results:

- Direct service test passed — `3 passed`.
- Focused service + repository serializer tests passed — `6 passed`.
- Ruff passed.
- Graphify update completed and rebuilt `graphify-out/graph.json` plus `graphify-out/GRAPH_REPORT.md`.
- `git diff --check` passed.

Next step: Step 17 — Run Focused Validation.

### Step 17 — Run Focused Validation

Status: Completed.

Files changed:

- `tests/unit/application/services/test_canonical_service_entrypoints.py`
- `graphify-out/` generated graph files updated by `graphify update .`

Implementation notes:

- Ran the Step 17 focused validation suite plus the Step 16 portfolio service test.
- The first validation run exposed two fake-provider drift issues in `test_canonical_service_entrypoints.py`:
  - `FakeMacroProvider.get_latest_economic_data()` did not accept the current optional `client` keyword used by `MacroService`.
  - `FakeMarketDataProvider.get_sp500_data()` still returned a raw `DataFrame` instead of the canonical `SP500Data` typed DTO and lacked current S&P 500 breadth columns.
- Updated only the test fake providers to match current service/provider contracts.
- Kept production source unchanged because the failures were contract drift in test doubles, not production behavior defects.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/database/test_portfolio_state_persistence_models.py tests/unit/application/persistence/portfolio/test_portfolio_persistence_service.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/application/reports/morning/test_morning_report_assembler.py tests/unit/application/services/portfolio/test_portfolio_service.py
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/unit/application/services/test_canonical_service_entrypoints.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
git diff --check
```

Results:

- Focused validation passed — `29 passed`.
- Scoped ruff passed.
- Graphify update completed and rebuilt `graphify-out/graph.json` plus `graphify-out/GRAPH_REPORT.md`.
- `git diff --check` passed.

Next step: Step 18 — Run Static Checks.

### Step 18 — Run Static Checks

Status: Completed with documented full-project static-check blockers outside the current Alpaca portfolio scope.

Files changed:

- `.agent/plans/plan_alpaca_portfolio_data_update.md`

Implementation notes:

- Ran the requested full-project static checks.
- Did not modify production source during this step because the full-project failures are outside the current Alpaca portfolio data update scope.
- Ran relevant scoped static checks against the files currently changed by this feature branch/workstream.

Full-project checks:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
UV_CACHE_DIR=/tmp/uv-cache uv run mypy .
```

Full-project results:

- `ruff check .` failed with 4 lint issues outside the current Alpaca portfolio plan scope:
  - `application/services/technical/breadth_analysis.py` — unused `ad_line_ema_10`.
  - `application/services/technical/breadth_analysis.py` — unused `net_breadth`.
  - `backtesting/runtime/backtest_engine.py` — unused `typing.Iterable` import.
  - `integration/contracts/execution/trade_intent_contract.py` — unused `typing.Optional` import.
- `mypy .` failed before analysis with repository/package-name configuration issue:
  - `polaris is not a valid Python package name`.

Scoped checks:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/reports/morning_report_assembler.py interfaces/cli/bootstrap/container.py tests/unit/application/reports/morning/test_morning_report_assembler.py tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/interfaces/cli/output/test_pdf_output_renderer.py tests/unit/interfaces/cli/output/test_workflow_output_renderer.py tests/unit/interfaces/cli/test_workflow_rendering.py
UV_CACHE_DIR=/tmp/uv-cache uv run mypy --explicit-package-bases --follow-imports=skip application/reports/morning_report_assembler.py interfaces/cli/bootstrap/container.py tests/unit/application/reports/morning/test_morning_report_assembler.py tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/interfaces/cli/output/test_pdf_output_renderer.py tests/unit/interfaces/cli/output/test_workflow_output_renderer.py tests/unit/interfaces/cli/test_workflow_rendering.py
UV_CACHE_DIR=/tmp/uv-cache uv run mypy --explicit-package-bases --follow-imports=skip --ignore-missing-imports application/reports/morning_report_assembler.py interfaces/cli/bootstrap/container.py tests/unit/application/reports/morning/test_morning_report_assembler.py tests/unit/application/services/portfolio/test_portfolio_service.py tests/unit/application/services/test_canonical_service_entrypoints.py tests/unit/interfaces/cli/output/test_pdf_output_renderer.py tests/unit/interfaces/cli/output/test_workflow_output_renderer.py tests/unit/interfaces/cli/test_workflow_rendering.py
git diff --check
```

Scoped results:

- Scoped ruff passed.
- Scoped mypy with `--explicit-package-bases --follow-imports=skip` reached the changed files but failed on missing third-party pandas stubs in `tests/unit/application/services/test_canonical_service_entrypoints.py`.
- Scoped mypy with `--ignore-missing-imports` passed — `Success: no issues found in 8 source files`.
- `git diff --check` passed.

Known follow-up work:

- Decide whether to clean up the 4 full-project ruff failures in a separate lint cleanup step.
- Decide whether to add/configure mypy project settings and third-party stubs, especially `pandas-stubs`, so `uv run mypy .` is usable without command-line workarounds.

Next step: Step 19 — Update Plan Step Results.

### Step 19 — Update Plan Step Results

Status: Completed.

Files changed:

- `.agent/plans/plan_alpaca_portfolio_data_update.md`

Implementation notes:

- Confirmed the bottom `## Step Results` section contains implementation results for completed plan steps through Step 18.
- Added this Step 19 result entry so the plan records the validation/update checkpoint before final diff review.
- No production source or tests were changed in this step.

Current changed-file categories documented in prior step results:

- Portfolio domain/service/persistence/runtime/intelligence/reporting/CLI files updated during Steps 2–17.
- Targeted tests updated or added across domain, integration client/provider, portfolio service, persistence, intelligence agents, morning report, CLI output, and canonical service entrypoints.
- Generated `graphify-out/` files updated by required graph refreshes.
- Repowise local state files remain tool-generated working-tree changes.

Validation status documented in prior step results:

- Step 17 focused validation passed — `29 passed`.
- Step 18 scoped ruff passed.
- Step 18 scoped mypy with `--ignore-missing-imports` passed — `Success: no issues found in 8 source files`.
- `git diff --check` passed after Step 18.

Known follow-up work documented from Step 18:

- Full-project `ruff check .` currently has 4 out-of-scope lint failures.
- Full-project `mypy .` is blocked by the repository/package-name configuration issue: `polaris is not a valid Python package name`.
- Consider adding/configuring third-party stubs such as `pandas-stubs` if full mypy enforcement is desired.

Next step: Step 20 — Final Diff Review.

### Step 20 — Final Diff Review

Status: Completed.

Files changed:

- `.agent/plans/plan_alpaca_portfolio_data_update.md`

Review commands:

```bash
git status --short
git diff --stat
git diff --check
git diff --name-only -- '*.py'
git diff -U0 -- '*.py' | grep -nE '^\+.*(alpaca|Alpaca|TradingClient|StockTradingClient|yfinance|yf\.|newsapi|fredapi|massive|submit_order|place_order|create_order)'
git diff -U0 -- '*.py' | grep -nE '^\+.*round\('
git diff -U0 -- '*.py' | grep -nE '^\+.*(submit_order|place_order|create_order|MarketOrder|LimitOrder|buy_order|sell_order|execute_trade|execute_order)'
```

Review results:

- `git diff --check` passed.
- Changed Python files are limited to report rendering, CLI bootstrap import repair, and tests:
  - `application/reports/morning_report_assembler.py`
  - `interfaces/cli/bootstrap/container.py`
  - `tests/unit/application/reports/morning/test_morning_report_assembler.py`
  - `tests/unit/application/services/portfolio/test_portfolio_service.py`
  - `tests/unit/application/services/test_canonical_service_entrypoints.py`
  - `tests/unit/interfaces/cli/output/test_pdf_output_renderer.py`
  - `tests/unit/interfaces/cli/output/test_workflow_output_renderer.py`
  - `tests/unit/interfaces/cli/test_workflow_rendering.py`
- The only vendor-related added-line search hit is a test import of the typed `SP500Data` DTO from `integration.clients.market_data.yfinance_data_client`; no vendor SDK call or external provider access was added above the integration boundary.
- No added `round()` calls were found in Python diffs; formatting remains a report/CLI presentation concern.
- No added autonomous order/trade execution calls were found.
- No source diff introduces Alpaca SDK access outside the integration client/provider layer.

Working-tree note:

- `.repowise/state.json`, `.repowise/wiki.db`, `.repowise/wiki.db-shm`, and `.repowise/wiki.db-wal` are tool-generated dirty files from Repowise context/index activity and are not feature source changes.
- `graphify-out/GRAPH_REPORT.md` is a generated graph update from the required `graphify update .` runs.
- Before commit, decide whether `.repowise/*` should be excluded/restored rather than committed with feature source changes.

Next step: Step 21 — Commit/Push or final user-directed cleanup, depending on the remaining plan instructions.
