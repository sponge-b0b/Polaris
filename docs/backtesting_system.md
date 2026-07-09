# Backtesting System

Polaris's backtesting system is a runtime-native simulation capability for testing
how an existing workflow would have behaved over a deterministic historical or
synthetic timeline.

The system is recommendation-oriented. It simulates recommendations, portfolio
state, and analytical fills for validation and reporting. It does **not** place
live trades, call broker order APIs, or create a second workflow runtime.

## Core principle

Backtesting uses the same workflow runtime as every other Polaris execution:

```text
CLI / application caller
  -> BacktestApplicationService
  -> WorkflowFacade.run_workflow(..., mode="backtest")
  -> RuntimeEngine
  -> RuntimeNode graph
  -> application services
  -> provider interfaces
  -> backtest provider implementations
```

The runtime remains unaware of whether a run is live or simulated. Backtesting is
selected at the application/composition boundary by provider profile,
`simulation_time`, runtime state, and metadata.

Do not add a parallel backtest runtime. Backtest-specific logic belongs in the
application service, provider profile wiring, simulated providers, persistence,
or reporting layers.

## What the system does

A backtest run currently provides:

- typed scenario loading from YAML or JSON;
- runtime-native workflow execution through `WorkflowFacade`;
- deterministic daily simulation timestamps from `start_date` through `end_date`;
- provider substitution through `backtest_synthetic` or `backtest_postgres`;
- per-step runtime state containing backtest metadata, symbols, benchmark, and
  scenario parameters;
- simulated portfolio ledger state across workflow steps;
- analytical fill simulation from workflow node outputs;
- backtest metrics such as total return, annualized return, volatility, maximum
  drawdown, Sharpe ratio, Sortino ratio, win rate, profit factor, exposure,
  turnover, and benchmark-relative return;
- console, Markdown, and JSON report artifacts;
- optional PostgreSQL persistence of curated backtest scenarios, runs, steps,
  portfolio snapshots, fills, metrics, and artifacts.

## What the system does not do

The current system intentionally does not:

- execute live trades;
- call Alpaca order-placement APIs;
- introduce a special runtime execution path;
- let runtime nodes branch on backtest-specific behavior;
- persist full raw node outputs into backtest tables.

Raw runtime output remains available through normal workflow persistence. Backtest
persistence stores curated summaries and links each step to the underlying
`workflow_run_id`.

## Main components

| Layer | Component | Responsibility |
| --- | --- | --- |
| CLI | `polaris backtest ...` | Thin Typer boundary for running and inspecting backtests. |
| CLI service | `BacktestCommandService` | Loads scenarios, builds the runtime with the selected provider profile, delegates to the application service, and persists results when requested. |
| Application service | `BacktestApplicationService` | Owns runtime-native backtest orchestration and calls `WorkflowFacade.run_workflow` for each simulation timestamp. |
| Scenario loading | `load_backtest_scenario` | Converts YAML/JSON boundary payloads into typed scenario objects. |
| Portfolio simulation | `BacktestPortfolioLedger` | Maintains cash, positions, mark-to-market values, and analytical fills outside the runtime. |
| Metrics/reporting | `compute_backtest_metrics`, `build_backtest_artifacts` | Produces canonical metrics and console/Markdown/JSON artifacts. |
| Provider profile | `backtest_synthetic`, `backtest_postgres` | Selects simulated or PostgreSQL-backed historical providers without runtime changes. |
| Persistence | `BacktestPersistenceService` | Maps application results into curated PostgreSQL records. |

## Provider profiles

Backtesting depends on canonical provider interfaces. The selected provider
profile determines which implementations are injected.

| Profile | Purpose |
| --- | --- |
| `backtest_synthetic` | Uses deterministic simulated providers under `integration.providers.backtesting`. This is the preferred profile for deterministic tests and fixtures. |
| `backtest_postgres` | Uses PostgreSQL-backed historical market data for market data while keeping the backtest execution path runtime-native. |

Provider implementations live under:

```text
integration/providers/backtesting/
├── macro/
├── market_data/
├── market_events/
├── news/
├── portfolio/
└── sentiment/
```

Canonical provider wrappers remain under the normal provider domains, for
example `integration/providers/market_data/backtest_data_provider.py` and
`integration/providers/portfolio/backtest_portfolio_provider.py`.

## Scenario file format

Backtests are driven by a YAML or JSON scenario file. The boundary file is parsed
into a typed `BacktestScenario`.

Example YAML:

```yaml
scenario_id: deterministic-morning-report-smoke
name: Deterministic Morning Report Smoke Test
workflow_name: morning_report
start_date: 2024-01-02
end_date: 2024-01-05
symbols: SPY
benchmark_symbol: SPY
initial_cash: "100000"
provider_profile: backtest_synthetic
initial_positions:
  - symbol: SPY
    quantity: "10"
    average_price: "450"
parameters:
  benchmark_return: "0.015"
  missing_data_policy: fail_fast
expected_outcomes:
  - target: metrics.total_return
    expectation_type: min
    expected: "0"
```

Supported top-level fields:

| Field | Required | Notes |
| --- | --- | --- |
| `scenario_id` | Yes | Stable scenario identifier. |
| `name` | Yes | Human-readable scenario name. |
| `workflow_name` | Yes | Registered workflow name to execute. |
| `start_date` | Yes | ISO date. The timeline is inclusive. |
| `end_date` | Yes | ISO date. Must be on or after `start_date`. |
| `symbols` | Yes | Non-empty symbol universe. |
| `benchmark_symbol` | Yes | Benchmark symbol for reports and relative metrics. |
| `initial_cash` | Yes | Decimal-compatible string or number. |
| `provider_profile` | No | Defaults to `backtest_synthetic`. |
| `initial_positions` | No | Starting holdings with `symbol`, `quantity`, and `average_price`. |
| `parameters` | No | Scenario-specific parameters passed into runtime state. |
| `expected_outcomes` | No | Deterministic assertions evaluated against metrics, step outputs, and the final portfolio ledger. |

Supported `parameters.missing_data_policy` values are:

- `fail_fast`
- `forward_fill`

Supported expected-outcome assertion types are:

- `equals`
- `approx`
- `min`
- `max`
- `between`
- `contains`

`approx` expectations require a non-negative `tolerance`. Expected-outcome
targets use dotted paths. Canonical aliases expose the main financial decision
surfaces without coupling scenarios to report formatting:

- `technical` resolves the technical-analysis node output;
- `breadth` resolves the canonical `technical_agent.features.breadth_state`
  payload, with legacy `breadth` lookup retained only for serialized historical
  run inspection;
- `portfolio_state` resolves the portfolio-state builder output;
- `risk` resolves the aggregate risk assessment;
- `strategy` resolves the synthesized strategy;
- `trade` or `trade_recommendation` resolves the packaged trade intent;
- `execution_risk` resolves the final execution-risk decision;
- `portfolio` resolves the final simulated ledger state;
- `metrics` resolves calculated backtest metrics;
- `steps.<index>` and canonical runtime node names support explicit inspection.

Every declared expectation is evaluated after the simulation. A failed expectation
marks the backtest unsuccessful and records its expected value, actual value,
comparison type, tolerance, and failure detail in the typed result and report
artifacts. Scenarios without expectations retain normal workflow-success semantics.

## Running a backtest

Run from the repository root:

```bash
uv run polaris backtest run --scenario path/to/scenario.yaml
```

Render a specific output format:

```bash
uv run polaris backtest run \
  --scenario path/to/scenario.yaml \
  --format markdown
```

Write output to a file:

```bash
uv run polaris backtest run \
  --scenario path/to/scenario.yaml \
  --format markdown \
  --output reports/backtest_report.md
```

Disable curated PostgreSQL persistence for a local smoke run:

```bash
uv run polaris backtest run \
  --scenario path/to/scenario.yaml \
  --no-persist-results
```

Disable workflow checkpoints for each simulation step:

```bash
uv run polaris backtest run \
  --scenario path/to/scenario.yaml \
  --no-checkpoint-workflow-runs
```

Load plugins before executing the workflow:

```bash
uv run polaris backtest run \
  --scenario path/to/scenario.yaml \
  --plugin-dir path/to/plugin
```

## Inspecting persisted runs

Backtest persistence requires PostgreSQL and Alembic migrations.

Start PostgreSQL and apply migrations:

```bash
docker compose up -d postgres
uv run alembic upgrade head
```

List persisted runs:

```bash
uv run polaris backtest list
```

Filter persisted runs:

```bash
uv run polaris backtest list \
  --scenario-id deterministic-morning-report-smoke \
  --workflow-name morning_report \
  --status succeeded \
  --limit 10
```

Show a persisted run summary:

```bash
uv run polaris backtest show backtest-run-id
```

Render a persisted report artifact:

```bash
uv run polaris backtest report backtest-run-id --format markdown
```

Write a persisted report artifact to a file:

```bash
uv run polaris backtest report backtest-run-id \
  --format markdown \
  --output reports/backtest_report.md
```

## Output formats

`backtest run` supports:

| Format | Use case |
| --- | --- |
| `console` | Short human-readable summary. |
| `markdown` | Human-readable report with run summary, portfolio summary, metrics, equity curve, and simulated fills. |
| `json` | Machine-readable artifact containing scenario, status, steps, and metrics. |

`backtest list` and `backtest show` support:

| Format | Use case |
| --- | --- |
| `console` | Human-readable terminal summaries. |
| `json` | Machine-readable persisted records. |

`backtest report` supports `console`, `markdown`, and `json` when the matching
artifact was persisted for the run.

## Runtime context and data flow

For each date in the inclusive scenario timeline, `BacktestApplicationService`:

1. creates a typed `BacktestWorkflowStepRequest` containing the workflow name,
   deterministic execution identifier, simulation time, checkpoint/persistence
   policy, and scenario inputs;
2. projects the scenario into canonical `RuntimeContext.workflow_inputs`, with
   nested backtest metadata retained for attribution;
3. calls `WorkflowFacade.run_workflow` with the current `simulation_time`;
4. collects the stable projection of runtime node outputs from the workflow
   result;
5. updates the simulated portfolio ledger;
6. records a `BacktestStepResult` containing workflow success, verification
   evidence, node output keys, the portfolio snapshot, and simulated fills.

The platform no longer creates a parallel `RuntimeState` aggregate or
`shared_state` namespace. Backtests use the same schema-version-2
`RuntimeContext` as live workflows: invocation data enters through
`workflow_inputs`, and calculated evidence flows between nodes through canonical
node outputs.

After all steps complete, the service computes metrics and builds report
artifacts. If persistence is enabled from the CLI, the result is converted into a
curated persistence bundle and written to PostgreSQL.

## Simulated fills

The simulated ledger looks for trade intent in runtime node outputs, currently
under the trade-packager output shape:

```text
node_outputs["trade_packager"]["outputs"]["features"]["trade_intent"]
```

The execution-risk guard can block or resize the analytical fill through node
outputs named `execution_risk_guard` or `risk_guard`.

Fill simulation is intentionally outside the runtime. It is an analytical ledger
used to evaluate recommendations and risk controls, not an execution engine.

## Metrics

Backtest metrics are computed from the deterministic equity curve and simulated
fills. Decimal values preserve full internal precision. Human-readable renderers
may round values for presentation.

Current metric fields are:

- `total_return`
- `annualized_return`
- `volatility`
- `max_drawdown`
- `sharpe_ratio`
- `sortino_ratio`
- `win_rate`
- `profit_factor`
- `exposure`
- `turnover`
- `benchmark_relative_return`

`benchmark_relative_return` subtracts `parameters.benchmark_return` when present;
otherwise the benchmark return defaults to zero.

## Persistence model

Curated backtest persistence uses the following PostgreSQL tables:

- `backtest_scenarios`
- `backtest_runs`
- `backtest_steps`
- `backtest_portfolio_snapshots`
- `backtest_fills`
- `backtest_metrics`
- `backtest_artifacts`

The persistence mapper intentionally stores compact, queryable backtest records.
It does not duplicate full raw runtime node outputs in backtest tables. Step
records include `workflow_run_id` and `node_output_keys` so consumers can join to
runtime persistence when full workflow execution details are needed.

## Deterministic validation guidance

For deterministic validation, prefer:

1. `provider_profile: backtest_synthetic` for fully controlled inputs;
2. a narrow date range and small symbol universe;
3. explicit `initial_cash` and `initial_positions`;
4. known benchmark assumptions through `parameters.benchmark_return`;
5. expected outcomes for metrics, recommendations, or risk assessments;
6. unit tests that load the scenario file, execute the backtest service, and
   compare exact or tolerance-bounded outcomes.

This pattern lets deterministic input data confirm that platform calculations,
recommendations, and risk assessments are correct based on the data. The
application service also accepts injected clock and run-ID factories for tests, so
repeated execution of the same scenario can assert identical result payloads,
ordering, timestamps, metrics, verification evidence, and persisted artifacts. The
production default still uses the system UTC clock and generated run identifiers.

Backtest artifacts use a deterministic projection of runtime node outputs. Node
names are stored in stable sorted order, and volatile runtime
`execution_metadata` such as wall-clock durations is excluded from the backtest
projection so identical inputs produce byte-equivalent verification artifacts.
The complete execution telemetry remains available through canonical workflow
persistence; the deterministic projection is not a replacement for raw runtime
observability. A fixed clock and run-ID factory control backtest timestamps and
execution identifiers in deterministic tests.

## Developer notes

- Keep backtesting runtime-native. Do not add a backtest-specific runtime engine.
- Keep provider implementations behind canonical provider interfaces.
- Keep scenario files and persistence payloads as serialization boundaries;
  internal services should use typed models.
- Preserve numeric precision internally. Round only in CLI/report renderers.
- Add telemetry to new long-running backtest orchestration or provider work.
- Prefer extending `BacktestApplicationService`, provider profiles, or the
  simulated providers before touching core runtime contracts.
