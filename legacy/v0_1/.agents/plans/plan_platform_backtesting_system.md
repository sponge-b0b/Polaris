  # Platform Backtesting Implementation Plan

  ## Summary

  Build backtesting as a runtime-native simulation capability, not as a separate execution framework.

  The backtesting system should allow the platform to answer:

  > “How would this workflow, strategy, signal chain, portfolio policy, or recommendation process have behaved over a historical or simulated market timeline?”

  The core design principle is:

  WorkflowFacade / WorkflowBootstrap / RuntimeEngine stay canonical.
  Backtesting swaps providers, inputs, clocks, and persistence context.
  The runtime does not know or care whether data is live or simulated.

  Existing legacy backtesting code contains useful pieces, especially simulated providers, but the current standalone backtest engine and CLI should be retired because they bypass the new workflow runtime architecture.

  ———

  ## Goals

  - Execute backtests through the existing WorkflowFacade, WorkflowBootstrap, and RuntimeEngine without creating a parallel runtime.
  - Keep the runtime unaware of live versus simulated execution; backtesting changes providers, inputs, simulation time, and persistence context at the application/composition boundary.
  - Support deterministic input datasets and deterministic simulation timelines so known data can verify that calculations, trade recommendations, and risk assessments are correct.
  - Provide typed scenario, request, result, portfolio snapshot, fill, metric, and expected-outcome contracts so backtest assertions are explicit and replayable.
  - Preserve internal numeric precision; only report renderers may round values for human display.
  - Persist curated backtest outputs in a way that can later feed RAG/embedding pipelines from trusted PostgreSQL records.

  ———

  ## Current-State Evaluation

  ### Reuse

  Keep and refactor where needed:

  - backtesting/providers/*
      - Simulated market, portfolio, macro, news, events, and sentiment providers are aligned with the correct architectural direction.
      - They already allow provider substitution without modifying intelligence/runtime nodes.

  - integration/providers/*/backtest_*_provider.py
      - These wrappers correctly expose simulated providers through canonical provider interfaces.
      - This is the right boundary for live-vs-backtest substitution.

  - config/settings.py
      - Existing provider-selection settings are useful and should remain the main configuration mechanism.

  - WorkflowFacade.run_workflow(...)
      - Already supports mode, simulation_time, runtime_state, metadata, persistence, and checkpoint options.
      - This is the correct execution entrypoint for backtesting.

  ### Retire or Replace

  Replace rather than preserve:

  - backtesting/runtime/backtest_engine.py
      - Creates a parallel execution loop.
      - Uses older pipeline concepts.
      - Manually builds context and applies strategy outputs.
      - Should not remain the canonical backtesting engine.

  - backtesting/cli/backtest_cli.py
      - Uses legacy argparse.
      - Imports missing/non-canonical modules.
      - Bypasses current Typer CLI and WorkflowFacade patterns.

  - Empty or stubbed backtesting/analytics, execution, metrics, replay, simulation, state, and storage files
      - These should either become real runtime-adjacent backtesting modules or be removed during cleanup.

  ———

  ## Recommended Backtesting Feature Set

  ### Initial Production-Ready Feature Set

  The first complete version should support:

  - Runtime-native workflow backtests through WorkflowFacade.
  - Historical or simulated timeline execution.
  - Provider substitution for market, portfolio, macro, news, events, and sentiment data.
  - Deterministic simulation time passed into the runtime via simulation_time.
  - Backtest scenario definitions with:
      - workflow name
      - symbol universe
      - date range
      - initial portfolio state
      - provider profile
      - strategy parameters
      - benchmark symbol

  - Simulated portfolio ledger:
      - starting cash
      - positions
      - fills
      - realized/unrealized PnL
      - equity curve
      - cash history
      - exposure history

  - Recommendation-aware trade simulation:
      - consume workflow outputs such as portfolio intent, trade packages, and execution-risk decisions
      - simulate fills outside the runtime
      - never allow autonomous live execution

  - Backtest result persistence:
      - scenario metadata
      - workflow run ids
      - per-step runtime outputs
      - portfolio snapshots
      - trades/fills
      - equity curve
      - metrics
      - report artifacts

  - Human-readable reporting:
      - markdown
      - console summary
      - JSON artifact

  - Telemetry:
      - backtest run started/completed/failed events
      - step progress
      - provider latency/failure metrics
      - simulated execution metrics

  ### Later Feature Set

  After the runtime-native foundation is complete:

  - PostgreSQL-backed historical data source.
  - Walk-forward testing.
  - Parameter sweeps.
  - Monte Carlo simulations.
  - Scenario libraries.
  - Regime-specific backtests.
  - Benchmark-relative attribution.
  - Strategy comparison reports.
  - Scheduled recurring backtests.

  ———

  ## Key Architecture

  ### Backtesting Runs Through Existing Runtime

  Backtesting should execute workflows like this:

  CLI / API
    → BacktestApplicationService
    → WorkflowFacade.run_workflow(
          workflow_name=...,
          mode="backtest",
          simulation_time=current_step_time,
          runtime_state=scenario_state,
          metadata=backtest_metadata,
      )
    → RuntimeEngine
    → RuntimeNode graph
    → Application services
    → Provider interfaces
    → Backtest provider implementations

  The runtime must not branch on backtesting-specific behavior.

  Allowed runtime inputs:

  - mode="backtest"
  - simulation_time
  - runtime_state
  - metadata
  - checkpoint/persistence flags

  Not allowed:

  - backtest-specific runtime engine
  - special backtest node execution path
  - direct simulated-provider access from runtime nodes
  - intelligence nodes checking whether the run is live or simulated

  ———

  ## Public Interfaces and Typed Models

  Introduce a typed backtesting application contract.

  Recommended models:

  @dataclass(frozen=True, slots=True)
  class BacktestScenario:
      scenario_id: str
      name: str
      workflow_name: str
      start_date: date
      end_date: date
      symbols: tuple[str, ...]
      benchmark_symbol: str
      initial_cash: Decimal
      initial_positions: tuple[BacktestInitialPosition, ...]
      provider_profile: str
      parameters: Mapping[str, object]

  @dataclass(frozen=True, slots=True)
  class BacktestRunRequest:
      scenario: BacktestScenario
      persist_results: bool
      checkpoint_workflow_runs: bool
      output_format: str

  @dataclass(frozen=True, slots=True)
  class BacktestStepResult:
      timestamp: datetime
      workflow_run_id: str
      success: bool
      node_outputs: Mapping[str, object]
      portfolio_snapshot: BacktestPortfolioSnapshot
      simulated_fills: tuple[BacktestFill, ...]

  @dataclass(frozen=True, slots=True)
  class BacktestResult:
      backtest_run_id: str
      scenario: BacktestScenario
      success: bool
      started_at: datetime
      completed_at: datetime
      steps: tuple[BacktestStepResult, ...]
      metrics: BacktestMetrics
      artifacts: Mapping[str, str]

  Dictionaries are acceptable only at boundaries:

  - CLI input parsing
  - YAML/JSON scenario files
  - runtime state serialization
  - telemetry
  - persistence payloads
  - report rendering

  ———

  ## Implementation Plan

  ### Phase 1 — Backtesting Boundary and Contracts

  Create a canonical backtesting application layer.

  Changes:

  - Add typed request/result/scenario models.
  - Add BacktestApplicationService.
  - Add scenario loading from YAML/JSON.
  - Keep service orchestration outside core/runtime.
  - Do not modify RuntimeEngine.

  Success criteria:

  - A backtest request can be constructed and validated without executing anything.
  - Unit tests cover scenario validation and model serialization boundaries.

  ———

  ### Phase 2 — Runtime-Native Backtest Execution

  Implement backtest orchestration as a workflow loop that repeatedly calls WorkflowFacade.

  Behavior:

  for each timestamp in scenario timeline:
      build runtime_state
      call WorkflowFacade.run_workflow(...)
      collect RuntimeExecutionResult
      update simulated portfolio outside runtime
      persist/report step result

  Important rule:

  The loop belongs to the backtesting application service.
  The workflow runtime remains unchanged.

  Success criteria:

  - Backtest service can execute an existing workflow in mode="backtest".
  - Runtime nodes remain unaware of live-vs-simulated execution.
  - Tests verify WorkflowFacade.run_workflow is called with mode="backtest" and simulation_time.

  ———

  ### Phase 3 — Provider Profile Integration

  Formalize provider substitution.

  Changes:

  - Keep existing backtest provider wrappers.
  - Add a named provider profile concept, for example:
      - live
      - backtest_synthetic
      - backtest_postgres

  - Ensure CLI/bootstrap composition selects providers through existing DI/settings patterns.
  - Avoid provider branching inside intelligence agents or application services.

  Success criteria:

  - Same workflow can run with live providers or backtest providers using configuration only.
  - Tests verify provider profile selection does not require runtime changes.

  ———

  ### Phase 4 — Simulated Portfolio and Fill Engine

  Refactor simulated portfolio logic into a clear ledger/fill model.

  Changes:

  - Convert mutable portfolio simulation internals into typed domain models where practical.
  - Add explicit fill records.
  - Add deterministic execution rules:
      - market fill at simulated close/open price
      - cash validation
      - position update
      - realized/unrealized PnL update
      - rejected fill recording

  - Consume trade package / portfolio intent outputs from workflow node outputs.
  - Preserve the project rule that the platform recommends; simulated fills are for analysis only.

  Success criteria:

  - Backtest run produces portfolio snapshots and fill records.
  - Invalid fills are rejected and recorded.
  - No broker client or live execution path is used.

  ———

  ### Phase 5 — Backtest Metrics and Reports

  Add canonical analytics.

  Initial metrics:

  - total return
  - annualized return
  - volatility
  - max drawdown
  - Sharpe ratio
  - Sortino ratio
  - win rate
  - profit factor
  - exposure
  - turnover
  - benchmark-relative return

  Reporting outputs:

  - console summary
  - markdown report
  - JSON artifact

  Success criteria:

  - Backtest result includes metrics and report artifacts.
  - Reports are human-readable and suitable for investment review.
  - Numeric precision is preserved internally; rounding only happens in renderers.

  ———

  ### Phase 6 — Persistence

  Persist backtest results as first-class platform records.

  Recommended persisted entities:

  - backtest_runs
  - backtest_scenarios
  - backtest_steps
  - backtest_portfolio_snapshots
  - backtest_fills
  - backtest_metrics
  - backtest_artifacts

  Rules:

  - Link each backtest step to the underlying workflow run id.
  - Do not duplicate runtime persistence data unnecessarily.
  - Store curated backtest summaries for later RAG ingestion.
  - Keep raw runtime node outputs in existing runtime persistence where possible.

  Success criteria:

  - A completed backtest can be queried from PostgreSQL.
  - Backtest records link to workflow run records.
  - Persistence tests cover create/read/list behavior.

  ———

  ### Phase 7 — CLI Integration

  Replace legacy CLI with canonical Typer commands.

  Recommended commands:

  polaris backtest run --scenario path/to/scenario.yaml
  polaris backtest list
  polaris backtest show <backtest_run_id>
  polaris backtest report <backtest_run_id> --format markdown

  CLI rules:

  - CLI remains thin.
  - CLI delegates to BacktestApplicationService.
  - CLI does not instantiate runtime components directly.
  - CLI does not access simulated providers directly.

  Success criteria:

  - polaris backtest run executes through WorkflowFacade.
  - CLI output is human-readable.
  - JSON output remains available for automation.

  ———

  ### Phase 8 — Legacy Cleanup

  Remove or replace incompatible legacy files.

  Cleanup targets:

  - standalone BacktestEngine
  - legacy argparse CLI
  - empty stub files that are not part of the new design
  - duplicated metrics modules if canonical analytics are added elsewhere

  Success criteria:

  - No backtesting code imports legacy pipeline/runtime components.
  - No parallel runtime remains under backtesting/runtime.
  - Tests confirm the canonical path is CLI/API → BacktestApplicationService → WorkflowFacade.

  ———

  ### Phase 9 — PostgreSQL Historical Provider

  Add PostgreSQL-backed historical data after the runtime-native foundation is in place.

  Purpose:

  - Move beyond synthetic backtests.
  - Use curated platform records as the source of truth.
  - Prepare future RAG ingestion from trusted backtest and market records.

  Changes:

  - Add historical market data read repository.
  - Add backtest provider implementation that reads from PostgreSQL.
  - Add scenario validation for data coverage.
  - Add missing-data handling policy:
      - fail fast by default
      - optionally allow explicit forward-fill in scenario config

  Success criteria:

  - Backtests can run from curated PostgreSQL records.
  - Missing data is reported clearly.
  - Synthetic provider remains useful for tests/dev.

  ———

  ## Testing Plan

  Cover:

  - backtest scenario validation
  - request/result models
  - timeline generation
  - simulated fill logic
  - portfolio snapshot updates
  - metrics calculations
  - report rendering
  - provider profile selection

  ### Integration Tests

  Cover:

  - backtest service executing through WorkflowFacade
  - existing workflow running in mode="backtest"
  - simulated providers wired through Dishka/bootstrap
  - persisted backtest result records
  - CLI polaris backtest run

  ### Regression Tests

  Cover:

  - runtime nodes do not need to know live vs simulated mode
  - no direct vendor SDK access from backtesting/intelligence
  - no imports from legacy standalone backtest runtime
  - telemetry events emitted for backtest start/progress/completion/failure

  ### Verification

  Run after implementation milestones:

  uv run pytest tests/unit/backtesting
  uv run pytest tests/integration/backtesting
  uv run pytest tests/unit/integration/providers
  uv run pytest tests/integration/workflow
  uv run ruff check .
  uv run mypy .

  ———

  ## Assumptions and Defaults

  - Backtesting is an application-layer capability, not a core runtime subsystem.
  - The existing workflow runtime already has the necessary generic hooks: mode, simulation_time, runtime_state, persistence, checkpointing, telemetry, and EventBus.
  - The first runnable implementation should use existing synthetic simulated providers.
  - PostgreSQL-backed historical data should become the canonical production-grade data source after the runtime-native backtest path is working.
  - Existing legacy backtesting code is not sacred and may be deleted or rewritten.
  - No autonomous live trade execution should be added as part of backtesting.
  - Simulated execution is analytical only and must remain isolated from broker execution paths.

  ———

  ## Step Results

  ### Step 1 — Backtesting Boundary and Contracts

  Completed: Added canonical backtesting application-service contracts and a validation-only service boundary.

  Files added:

  - `application/services/backtesting/backtest_request.py`
  - `application/services/backtesting/backtest_result.py`
  - `application/services/backtesting/scenario_loader.py`
  - `application/services/backtesting/backtest_service.py`
  - `application/services/backtesting/__init__.py`
  - `tests/unit/application/services/backtesting/test_backtest_contracts.py`

  Key outcomes:

  - Added typed scenario, request, initial-position, deterministic expected-outcome, result, step-result, portfolio-snapshot, fill, and metrics models.
  - Added YAML/JSON scenario loading at the boundary, converting untrusted mappings into typed contracts.
  - Added `BacktestApplicationService` as the canonical application boundary for backtest validation/preparation. Runtime execution through `WorkflowFacade` remains deferred to the next step.
  - Added deterministic expected-outcome assertions to the scenario contract so future steps can verify calculations, risk assessments, and trade recommendations against known deterministic input data.

  Verification:

  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/backtesting/test_backtest_contracts.py` → passed, 5 tests.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/services/backtesting tests/unit/application/services/backtesting/test_backtest_contracts.py` → passed.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy application/services/backtesting tests/unit/application/services/backtesting/test_backtest_contracts.py --explicit-package-bases` → passed.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` → passed; graph metadata refreshed.

  ### Step 2 — Runtime-Native Backtest Execution

  Completed: Added runtime-native backtest orchestration through the existing workflow facade contract.

  Files changed:

  - `application/services/backtesting/backtest_service.py`
  - `application/services/backtesting/__init__.py`
  - `tests/unit/application/services/backtesting/test_backtest_contracts.py`

  Key outcomes:

  - Added a minimal typed `BacktestWorkflowFacade` protocol matching `WorkflowFacade.run_workflow`.
  - Updated `BacktestApplicationService` so a configured workflow facade executes one workflow run per deterministic simulation timestamp.
  - Each workflow call uses `mode="backtest"`, passes `simulation_time`, passes a step-specific `RuntimeState`, and forwards persistence/checkpoint options from `BacktestRunRequest`.
  - Backtest runtime state now carries `backtest_run_id`, `scenario_id`, provider profile, symbol universe, parameters, and deterministic expected outcomes in `shared_state`.
  - Added step result collection from workflow final context node outputs without changing the core runtime.
  - Kept the no-facade path as validation/preparation only so Step 1 contract tests remain useful before bootstrap wiring is added.

  Verification:

  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/backtesting/test_backtest_contracts.py` → passed, 6 tests.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/services/backtesting tests/unit/application/services/backtesting/test_backtest_contracts.py` → passed.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format application/services/backtesting tests/unit/application/services/backtesting/test_backtest_contracts.py --check` → required formatting before final verification.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format application/services/backtesting tests/unit/application/services/backtesting/test_backtest_contracts.py` → formatted 3 files.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy application/services/backtesting tests/unit/application/services/backtesting/test_backtest_contracts.py --explicit-package-bases` → passed.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` → passed; graph metadata refreshed.


  ### Step 3 — Provider Profile Integration

  Completed: Added named provider profiles and wired CLI/bootstrap provider selection through the existing settings-driven DI path.

  Files added:

  - `config/provider_profiles.py`
  - `tests/unit/config/test_provider_profiles.py`
  - `tests/unit/interfaces/cli/test_cli_provider_profiles.py`

  Files changed:

  - `config/settings.py`
  - `interfaces/cli/bootstrap/container.py`
  - `interfaces/cli/commands/inspect_command.py`
  - `tests/unit/interfaces/cli/test_cli.py`

  Key outcomes:

  - Added a typed `ProviderProfile` configuration model for selecting provider sets without changing runtime behavior.
  - Added supported provider profiles:
      - `live`
      - `backtest_synthetic`
  - Reserved `backtest_postgres` explicitly until PostgreSQL-backed historical backtest providers exist, avoiding a misleading profile that silently maps to synthetic data.
  - Added `PROVIDER_PROFILE` to `Settings` as an optional configuration shortcut.
  - Updated CLI bootstrap so `build_cli_runtime(...)` and `build_cli_runtime_async(...)` can accept `provider_profile`, or use `PROVIDER_PROFILE` from environment, then continue selecting Dishka providers through the existing provider setting fields.
  - Updated `inspect config` so rendered provider configuration reflects an active provider profile.
  - Kept provider selection out of runtime nodes, intelligence agents, and application-service business logic.

  Verification:

  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/config/test_provider_profiles.py tests/unit/interfaces/cli/test_cli.py tests/unit/interfaces/cli/test_cli_provider_profiles.py tests/unit/application/services/backtesting/test_backtest_contracts.py` → passed, 19 tests; one existing `websockets.legacy` deprecation warning.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format config/provider_profiles.py config/settings.py interfaces/cli/bootstrap/container.py interfaces/cli/commands/inspect_command.py tests/unit/config/test_provider_profiles.py tests/unit/interfaces/cli/test_cli.py tests/unit/interfaces/cli/test_cli_provider_profiles.py application/services/backtesting tests/unit/application/services/backtesting/test_backtest_contracts.py` → formatted 1 file, then clean.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check config/provider_profiles.py config/settings.py interfaces/cli/bootstrap/container.py interfaces/cli/commands/inspect_command.py tests/unit/config/test_provider_profiles.py tests/unit/interfaces/cli/test_cli.py tests/unit/interfaces/cli/test_cli_provider_profiles.py application/services/backtesting tests/unit/application/services/backtesting/test_backtest_contracts.py` → passed.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy config/provider_profiles.py config/settings.py interfaces/cli/bootstrap/container.py interfaces/cli/commands/inspect_command.py tests/unit/config/test_provider_profiles.py tests/unit/interfaces/cli/test_cli.py tests/unit/interfaces/cli/test_cli_provider_profiles.py application/services/backtesting tests/unit/application/services/backtesting/test_backtest_contracts.py --explicit-package-bases` → passed.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` → passed; graph metadata refreshed.

  ### Step 4 — Simulated Portfolio and Fill Engine

  Completed: Added a deterministic simulated portfolio ledger and wired it into runtime-native backtest step collection.

  Files added:

  - `application/services/backtesting/simulated_portfolio_ledger.py`
  - `tests/unit/application/services/backtesting/test_simulated_portfolio_ledger.py`

  Files changed:

  - `application/services/backtesting/backtest_service.py`
  - `application/services/backtesting/__init__.py`
  - `tests/unit/application/services/backtesting/test_backtest_contracts.py`

  Key outcomes:

  - Added typed ledger contracts for simulated analytical execution:
      - `BacktestLedgerPosition`
      - `SimulatedTradeInstruction`
      - `BacktestPortfolioLedger`
  - Backtest execution now keeps one portfolio ledger across all simulation timestamps and updates it after each workflow run using runtime node outputs.
  - The ledger consumes trade-package outputs from `trade_packager.outputs.features.trade_intent` and execution-risk decisions from `execution_risk_guard.outputs.features.execution_guard`.
  - Deterministic prices are resolved from scenario `parameters["prices"]` first, then from technical node snapshot outputs such as `close`, `price`, or `adj_close`.
  - Added deterministic simulated fill behavior for analytical backtests only:
      - market fill at simulated price
      - cash validation for buys
      - position updates
      - realized and unrealized PnL updates
      - rejected fill records for invalid or blocked fills
  - Backtest result metadata now includes `simulated_fill_count`.
  - No broker client, live execution path, or core runtime change was introduced.

  Verification:

  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/backtesting/test_backtest_contracts.py tests/unit/application/services/backtesting/test_simulated_portfolio_ledger.py` → passed, 11 tests.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format application/services/backtesting tests/unit/application/services/backtesting/test_backtest_contracts.py tests/unit/application/services/backtesting/test_simulated_portfolio_ledger.py` → formatted 1 file.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/services/backtesting tests/unit/application/services/backtesting/test_backtest_contracts.py tests/unit/application/services/backtesting/test_simulated_portfolio_ledger.py` → passed.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy application/services/backtesting tests/unit/application/services/backtesting/test_backtest_contracts.py tests/unit/application/services/backtesting/test_simulated_portfolio_ledger.py --explicit-package-bases` → passed.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` → passed; graph metadata refreshed.

  ### Step 5 — Backtest Metrics and Reports

  Completed: Added canonical backtest metrics calculation and generated report artifacts from completed runtime-native backtest runs.

  Files added:

  - `application/services/backtesting/backtest_metrics.py`
  - `application/services/backtesting/backtest_reporting.py`
  - `tests/unit/application/services/backtesting/test_backtest_metrics_reporting.py`

  Files changed:

  - `application/services/backtesting/backtest_result.py`
  - `application/services/backtesting/backtest_service.py`
  - `application/services/backtesting/__init__.py`
  - `application/services/backtesting/simulated_portfolio_ledger.py`
  - `tests/unit/application/services/backtesting/test_backtest_contracts.py`

  Key outcomes:

  - Added deterministic `compute_backtest_metrics(...)` for:
      - total return
      - annualized return
      - volatility
      - max drawdown
      - Sharpe ratio
      - Sortino ratio
      - win rate
      - profit factor
      - exposure
      - turnover
      - benchmark-relative return
  - Added `realized_pnl` to `BacktestFill` so metrics do not need to parse free-form fill reasons.
  - Added report artifact generation for:
      - console summary
      - markdown report
      - JSON artifact
  - `BacktestApplicationService` now computes metrics and artifacts after the simulation loop completes.
  - Internal metrics preserve `Decimal` precision; formatting/rounding is isolated to report renderers only.
  - The platform remains recommendation-only; report artifacts describe simulated analytical fills and never trigger broker execution.

  Verification:

  - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/backtesting` → passed, 14 tests.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format application/services/backtesting tests/unit/application/services/backtesting` → formatted 3 files.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/services/backtesting tests/unit/application/services/backtesting` → passed.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run mypy application/services/backtesting tests/unit/application/services/backtesting --explicit-package-bases` → passed.
  - `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` → passed; graph metadata refreshed.

### Step 6 — Persistence

Completed: Added first-class PostgreSQL persistence contracts and repository support for curated backtest results.

Files added:

- `core/database/models/backtesting.py`
- `core/storage/persistence/backtesting/__init__.py`
- `core/storage/persistence/backtesting/backtest_persistence_models.py`
- `core/storage/persistence/backtesting/backtest_persistence_repository.py`
- `core/storage/persistence/repositories/postgres_backtest_persistence_repository.py`
- `core/storage/persistence/serializers/backtest_persistence_serializer.py`
- `application/persistence/backtesting/__init__.py`
- `application/persistence/backtesting/backtest_persistence_service.py`
- `application/persistence/backtesting/backtest_result_persistence_mapper.py`
- `migrations/versions/20260614_153000_b7c2d4e6f8a1_add_backtest_persistence.py`
- `tests/unit/application/persistence/backtesting/test_backtest_persistence_service.py`
- `tests/unit/core/storage/persistence/test_postgres_backtest_persistence_repository.py`

Files changed:

- `core/database/models/__init__.py`
- `core/storage/persistence/repositories/__init__.py`
- `application/persistence/__init__.py`

Key outcomes:

- Added SQLAlchemy models and Alembic migration for:
  - `backtest_scenarios`
  - `backtest_runs`
  - `backtest_steps`
  - `backtest_portfolio_snapshots`
  - `backtest_fills`
  - `backtest_metrics`
  - `backtest_artifacts`
- Added typed persistence-boundary records and repository protocol for backtest persistence.
- Added a PostgreSQL repository with idempotent upserts, create/read/list behavior, rollback-on-error handling, and deterministic ordering for list methods.
- Added application persistence service and mapper from `BacktestResult` into curated records.
- Preserved raw runtime node outputs in runtime persistence by storing only step-level workflow run ids, node output keys, and compact summaries in backtest persistence.
- Linked each persisted backtest step to the underlying runtime workflow execution through `workflow_run_id`.
- Stored metrics both as a run-level JSON summary and as queryable `backtest_metrics` rows for future reporting/RAG curation.

Verification:

- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format core/database/models/backtesting.py core/database/models/__init__.py core/storage/persistence/backtesting core/storage/persistence/serializers/backtest_persistence_serializer.py core/storage/persistence/repositories/postgres_backtest_persistence_repository.py core/storage/persistence/repositories/__init__.py application/persistence/backtesting application/persistence/__init__.py migrations/versions/20260614_153000_b7c2d4e6f8a1_add_backtest_persistence.py tests/unit/application/persistence/backtesting/test_backtest_persistence_service.py tests/unit/core/storage/persistence/test_postgres_backtest_persistence_repository.py` → formatted 3 files.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check core/database/models/backtesting.py core/database/models/__init__.py core/storage/persistence/backtesting core/storage/persistence/serializers/backtest_persistence_serializer.py core/storage/persistence/repositories/postgres_backtest_persistence_repository.py core/storage/persistence/repositories/__init__.py application/persistence/backtesting application/persistence/__init__.py migrations/versions/20260614_153000_b7c2d4e6f8a1_add_backtest_persistence.py tests/unit/application/persistence/backtesting/test_backtest_persistence_service.py tests/unit/core/storage/persistence/test_postgres_backtest_persistence_repository.py` → passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/persistence/backtesting/test_backtest_persistence_service.py tests/unit/core/storage/persistence/test_postgres_backtest_persistence_repository.py` → passed, 7 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/backtesting tests/unit/application/persistence/backtesting tests/unit/core/storage/persistence/test_postgres_backtest_persistence_repository.py` → passed, 21 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/database/models/backtesting.py core/database/models/__init__.py core/storage/persistence/backtesting core/storage/persistence/serializers/backtest_persistence_serializer.py core/storage/persistence/repositories/postgres_backtest_persistence_repository.py core/storage/persistence/repositories/__init__.py application/persistence/backtesting application/persistence/__init__.py tests/unit/application/persistence/backtesting/test_backtest_persistence_service.py tests/unit/core/storage/persistence/test_postgres_backtest_persistence_repository.py --explicit-package-bases` → passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -m py_compile migrations/versions/20260614_153000_b7c2d4e6f8a1_add_backtest_persistence.py` → passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run alembic heads` → reported `b7c2d4e6f8a1 (head)`.
- `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` → passed; graph metadata refreshed.

### Step 7 — CLI Integration

Completed: Added canonical Typer backtest commands that remain thin CLI boundaries and delegate execution to the application backtesting service.

Files added:

- `interfaces/cli/services/backtest_command_service.py`
- `tests/unit/interfaces/cli/test_backtest_command.py`

Files changed:

- `interfaces/cli/commands/backtest_command.py`

Key outcomes:

- Added `polaris backtest run --scenario <path>` using `BacktestApplicationService` and `WorkflowFacade` via `build_cli_runtime_async(...)`.
- Added persisted PostgreSQL inspection commands:
  - `polaris backtest list`
  - `polaris backtest show <backtest_run_id>`
  - `polaris backtest report <backtest_run_id> --format markdown`
- Preserved CLI thinness by moving runtime/service orchestration into `BacktestCommandService`.
- Scenario `provider_profile` now flows into CLI runtime bootstrap so backtests can run against the simulated provider profile without special runtime changes.
- CLI never instantiates simulated providers or a parallel backtesting runtime.
- Backtest run output is rendered before returning a non-zero exit for requested persistence failures, so completed simulation results remain visible even when PostgreSQL persistence is unavailable.
- Console, JSON, and Markdown output remain available for backtest runs; persisted list/show support console and JSON output.
- Added tests proving the CLI service executes each scenario through `WorkflowFacade` with `mode="backtest"` and renders command output through the Typer command boundary.

Verification:

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/interfaces/cli/test_backtest_command.py tests/unit/application/services/backtesting/test_backtest_contracts.py` → passed, 10 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check interfaces/cli/commands/backtest_command.py interfaces/cli/services/backtest_command_service.py tests/unit/interfaces/cli/test_backtest_command.py --fix` → passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format interfaces/cli/commands/backtest_command.py interfaces/cli/services/backtest_command_service.py tests/unit/interfaces/cli/test_backtest_command.py` → formatted 2 files.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/interfaces/cli/test_backtest_command.py tests/unit/application/services/backtesting/test_backtest_contracts.py` → passed, 10 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy interfaces/cli/commands/backtest_command.py interfaces/cli/services/backtest_command_service.py tests/unit/interfaces/cli/test_backtest_command.py --explicit-package-bases` → passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/interfaces/cli/test_cli.py tests/unit/interfaces/cli/test_backtest_command.py` → passed, 11 tests.
- `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` → passed; graph metadata refreshed.

### Step 8 — Legacy Cleanup

Completed: Removed the legacy standalone backtesting runtime, legacy argparse CLI, empty stub packages, and duplicated/empty analytics and metrics modules so the only remaining backtesting execution path is the canonical CLI/API → `BacktestApplicationService` → `WorkflowFacade` path.

Directories/files removed:

- `backtesting/runtime/`
- `backtesting/cli/`
- `backtesting/execution/`
- `backtesting/replay/`
- `backtesting/metrics/`
- `backtesting/analytics/`
- `backtesting/simulation/`
- `backtesting/state/`
- `backtesting/storage/`
- `backtesting/portfolio/`
- `backtesting/scenarios/`
- `backtesting/configs/`
- Generated `__pycache__` folders under backtesting and touched tests

Files changed:

- `tests/unit/interfaces/cli/test_backtest_command.py`

Key outcomes:

- Removed `BacktestEngine`, `ExecutionClock`, and the legacy `argparse` backtest CLI.
- Removed empty/stub legacy packages that were not part of the runtime-native backtesting design.
- Kept active simulated provider packages and DI wiring used by provider profiles and runtime bootstrap.
- Added a regression test asserting legacy parallel runtime/CLI/stub paths do not exist.
- Verified repository search no longer finds imports or references to the removed legacy runtime/CLI classes outside generated graph artifacts.

Verification:

- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/unit/interfaces/cli/test_backtest_command.py interfaces/cli/commands/backtest_command.py interfaces/cli/services/backtest_command_service.py backtesting/providers backtesting/di.py --fix` → passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format tests/unit/interfaces/cli/test_backtest_command.py interfaces/cli/commands/backtest_command.py interfaces/cli/services/backtest_command_service.py backtesting/providers backtesting/di.py` → no changes required.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/interfaces/cli/test_backtest_command.py tests/unit/backtesting/providers/market_data/test_simulated_data_provider.py tests/unit/backtesting/providers/portfolio/test_simulated_portfolio_provider.py tests/unit/integration/providers/portfolio/test_backtest_portfolio_provider.py` → passed, 12 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy tests/unit/interfaces/cli/test_backtest_command.py interfaces/cli/commands/backtest_command.py interfaces/cli/services/backtest_command_service.py backtesting/providers backtesting/di.py --explicit-package-bases` → passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/backtesting tests/unit/interfaces/cli/test_backtest_command.py tests/unit/backtesting/providers tests/unit/integration/providers/portfolio/test_backtest_portfolio_provider.py` → passed, 26 tests.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/unit/interfaces/cli/test_backtest_command.py --fix && UV_CACHE_DIR=/tmp/uv-cache uv run ruff format tests/unit/interfaces/cli/test_backtest_command.py && UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/interfaces/cli/test_backtest_command.py tests/unit/application/services/backtesting tests/unit/backtesting/providers tests/unit/integration/providers/portfolio/test_backtest_portfolio_provider.py && UV_CACHE_DIR=/tmp/uv-cache uv run mypy tests/unit/interfaces/cli/test_backtest_command.py --explicit-package-bases` → passed after correcting the legacy-path regression test to resolve the actual repository root; 26 tests passed, 1 warning.
- `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` → passed; no code-graph topology changes detected after the test-only correction.

### Step 9 — PostgreSQL Historical Provider

Completed: Added PostgreSQL-backed historical market-data support for backtests while preserving the runtime-native provider-substitution architecture.

Files added:

- `backtesting/providers/market_data/postgres_historical_data_provider.py`
- `tests/unit/backtesting/providers/market_data/test_postgres_historical_data_provider.py`

Files changed:

- `backtesting/providers/market_data/__init__.py`
- `integration/providers/market_data/backtest_data_provider.py`
- `integration/providers/di.py`
- `interfaces/cli/bootstrap/container.py`
- `core/bootstrap/di_providers.py`
- `config/settings.py`
- `config/provider_profiles.py`
- `application/services/backtesting/backtest_request.py`
- `tests/unit/config/test_provider_profiles.py`
- `tests/unit/interfaces/cli/test_cli_provider_profiles.py`
- `tests/unit/application/services/backtesting/test_backtest_contracts.py`

Key outcomes:

- Added `PostgresHistoricalDataProvider`, a canonical `MarketDataProvider` implementation backed by curated PostgreSQL market persistence records.
- Added `PostgresHistoricalDataProviderConfig` with source filtering, S&P 500 universe selection, and explicit missing-data policy support.
- Added fail-fast missing historical data errors by default, with optional explicit `forward_fill` behavior for controlled backtest scenarios.
- Added a PostgreSQL market repository context factory that uses `AsyncSessionLocal` and `PostgresMarketPersistenceRepository` without changing core runtime contracts.
- Refactored `BacktestDataProvider` to wrap any `MarketDataProvider`, allowing the same telemetry wrapper to support both synthetic and PostgreSQL-backed historical providers.
- Promoted the `backtest_postgres` provider profile from reserved to executable, mapping only market data to PostgreSQL history while keeping macro, market events, news, portfolio, and sentiment on synthetic backtest providers.
- Wired `BacktestPostgresDataDIProvider` through both CLI bootstrap and the existing core DI provider selection path.
- Added scenario validation for `parameters["missing_data_policy"]` so invalid missing-data behavior is rejected at the application contract boundary.
- Kept synthetic providers intact for deterministic tests and local development.

Verification:

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/backtesting/providers/market_data tests/unit/config/test_provider_profiles.py tests/unit/interfaces/cli/test_cli_provider_profiles.py tests/unit/application/services/backtesting/test_backtest_contracts.py` → passed, 22 tests, 1 external dependency warning from `websockets.legacy`.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check backtesting/providers/market_data integration/providers/market_data/backtest_data_provider.py integration/providers/di.py config/settings.py config/provider_profiles.py interfaces/cli/bootstrap/container.py core/bootstrap/di_providers.py application/services/backtesting/backtest_request.py tests/unit/backtesting/providers/market_data tests/unit/config/test_provider_profiles.py tests/unit/interfaces/cli/test_cli_provider_profiles.py tests/unit/application/services/backtesting/test_backtest_contracts.py` → passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format backtesting/providers/market_data integration/providers/market_data/backtest_data_provider.py integration/providers/di.py config/settings.py config/provider_profiles.py interfaces/cli/bootstrap/container.py core/bootstrap/di_providers.py application/services/backtesting/backtest_request.py tests/unit/backtesting/providers/market_data tests/unit/config/test_provider_profiles.py tests/unit/interfaces/cli/test_cli_provider_profiles.py tests/unit/application/services/backtesting/test_backtest_contracts.py --check` → passed; 15 files already formatted.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy backtesting/providers/market_data integration/providers/market_data/backtest_data_provider.py integration/providers/di.py config/settings.py config/provider_profiles.py interfaces/cli/bootstrap/container.py core/bootstrap/di_providers.py application/services/backtesting/backtest_request.py tests/unit/backtesting/providers/market_data tests/unit/config/test_provider_profiles.py tests/unit/interfaces/cli/test_cli_provider_profiles.py tests/unit/application/services/backtesting/test_backtest_contracts.py --explicit-package-bases` → passed.
- `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` → passed; graph metadata refreshed.

### Step 10 — Final Backtesting Plan Verification and Closure

Completed: Performed final targeted verification for the runtime-native backtesting implementation after Phases 1–9. The original plan ends at Phase 9, so this step was treated as plan closure and regression validation rather than a new feature phase.

Files changed:

- `.agent/plans/plan_platform_backtesting_system.md`

Key outcomes:

- Confirmed no additional Step 10 code changes were required after PostgreSQL historical provider wiring.
- Verified the backtesting path remains CLI/API → `BacktestApplicationService` → `WorkflowFacade`, with no restored standalone backtesting runtime.
- Verified synthetic and PostgreSQL-backed market-data provider profiles remain available through existing DI/settings composition.
- Verified backtest service, persistence, CLI, provider profile, simulated provider, and PostgreSQL historical provider tests together.
- Ran Repowise health/risk checks for the main backtesting service, CLI service, PostgreSQL historical provider, and persistence service. Current health scores are acceptable; noted non-blocking future cleanup candidates include `BacktestApplicationService` method size/cohesion and parameter-count warnings around facade-like protocol methods.

Verification:

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/backtesting tests/unit/application/persistence/backtesting tests/unit/core/storage/persistence/test_postgres_backtest_persistence_repository.py tests/unit/interfaces/cli/test_backtest_command.py tests/unit/interfaces/cli/test_cli_provider_profiles.py tests/unit/backtesting/providers tests/unit/integration/providers/portfolio/test_backtest_portfolio_provider.py` → passed, 40 tests, 1 external dependency warning from `websockets.legacy`.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/services/backtesting application/persistence/backtesting core/storage/persistence/backtesting core/storage/persistence/repositories/postgres_backtest_persistence_repository.py core/storage/persistence/serializers/backtest_persistence_serializer.py core/database/models/backtesting.py interfaces/cli/commands/backtest_command.py interfaces/cli/services/backtest_command_service.py backtesting/providers backtesting/di.py integration/providers/market_data/backtest_data_provider.py integration/providers/di.py config/provider_profiles.py config/settings.py tests/unit/application/services/backtesting tests/unit/application/persistence/backtesting tests/unit/core/storage/persistence/test_postgres_backtest_persistence_repository.py tests/unit/interfaces/cli/test_backtest_command.py tests/unit/interfaces/cli/test_cli_provider_profiles.py tests/unit/backtesting/providers tests/unit/integration/providers/portfolio/test_backtest_portfolio_provider.py` → passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format application/services/backtesting application/persistence/backtesting core/storage/persistence/backtesting core/storage/persistence/repositories/postgres_backtest_persistence_repository.py core/storage/persistence/serializers/backtest_persistence_serializer.py core/database/models/backtesting.py interfaces/cli/commands/backtest_command.py interfaces/cli/services/backtest_command_service.py backtesting/providers backtesting/di.py integration/providers/market_data/backtest_data_provider.py integration/providers/di.py config/provider_profiles.py config/settings.py tests/unit/application/services/backtesting tests/unit/application/persistence/backtesting tests/unit/core/storage/persistence/test_postgres_backtest_persistence_repository.py tests/unit/interfaces/cli/test_backtest_command.py tests/unit/interfaces/cli/test_cli_provider_profiles.py tests/unit/backtesting/providers tests/unit/integration/providers/portfolio/test_backtest_portfolio_provider.py --check` → passed; 50 files already formatted.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy application/services/backtesting application/persistence/backtesting core/storage/persistence/backtesting core/storage/persistence/repositories/postgres_backtest_persistence_repository.py core/storage/persistence/serializers/backtest_persistence_serializer.py core/database/models/backtesting.py interfaces/cli/commands/backtest_command.py interfaces/cli/services/backtest_command_service.py backtesting/providers backtesting/di.py integration/providers/market_data/backtest_data_provider.py integration/providers/di.py config/provider_profiles.py config/settings.py tests/unit/application/services/backtesting tests/unit/application/persistence/backtesting tests/unit/core/storage/persistence/test_postgres_backtest_persistence_repository.py tests/unit/interfaces/cli/test_backtest_command.py tests/unit/interfaces/cli/test_cli_provider_profiles.py tests/unit/backtesting/providers tests/unit/integration/providers/portfolio/test_backtest_portfolio_provider.py --explicit-package-bases` → passed.
- `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` → passed; no code-graph topology changes detected.
