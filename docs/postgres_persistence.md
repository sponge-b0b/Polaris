# PostgreSQL Persistence

PostgreSQL is Polaris's authoritative durable system of record. Runtime evidence,
curated business records, projection queues, telemetry records, and operational
history are persisted in PostgreSQL first. Qdrant, Neo4j, rendered reports,
files, caches, dashboards, and local debug artifacts are downstream projections
or artifacts and must not become competing authorities.

## Canonical persistence architecture

The canonical persistence lifecycle is:

```text
Interface / workflow command
    -> WorkflowFacade and WorkflowBootstrap
    -> RuntimeEngine
    -> RuntimeNodeOutput in RuntimeContext
    -> completed-run archive in PostgreSQL
    -> workflow-output projection policy
    -> typed curated domain record
    -> owning application persistence service
    -> PostgreSQL domain table
    -> optional RAG document/chunk records
    -> optional Qdrant and Neo4j projections
```

Important ownership rules:

- `RuntimeContext` and `RuntimeNodeOutput` are runtime evidence contracts, not
  domain-record storage abstractions.
- Completed runs preserve broad workflow evidence after execution.
- Curated domain records are narrow, typed, queryable business memory.
- Workflow outputs become curated records only through explicit registered
  projectors.
- Application services and intelligence nodes return typed results. They should
  not persist workflow-derived facts directly unless persistence is the explicit
  use case for that service.
- PostgreSQL records are written through typed repositories and application
  persistence services.
- Qdrant and Neo4j are rebuildable retrieval projections from PostgreSQL RAG
  records.

## Local PostgreSQL service

The repository includes a compose-managed PostgreSQL service named `postgres`.

Start it from the repository root:

```bash
docker compose up -d postgres
```

Check service status:

```bash
docker compose ps postgres
```

The compose-aligned local defaults are:

```text
host: localhost
port: 5432
database: polaris
user: polaris
password: <required; load from an untracked .env file or secret manager>
```

Credentials must not be written into tracked documentation, tests, plans, or
source files.

## Environment variables

Database configuration is owned by `core.database.settings.PostgresSettings`.
`POLARIS_DATABASE_URL` is the preferred full URL override. When it is not set,
Polaris derives the async SQLAlchemy URL from `POLARIS_POSTGRES_*` variables.

| Variable | Default | Notes |
| --- | --- | --- |
| `POLARIS_DATABASE_URL` | unset | Preferred full URL override. `postgresql://...` is normalized to the async driver form. |
| `POLARIS_POSTGRES_HOST` | `localhost` | Compose-compatible local host. |
| `POLARIS_POSTGRES_PORT` | `5432` | Must be an integer. |
| `POLARIS_POSTGRES_DB` | `polaris` | Database name. |
| `POLARIS_POSTGRES_USER` | `polaris` | Database user. |
| `POLARIS_POSTGRES_PASSWORD` | required | Required when `POLARIS_DATABASE_URL` is not set. Store only in ignored local config or a secret manager. |
| `POLARIS_POSTGRES_DRIVER` | `asyncpg` | SQLAlchemy async driver suffix. |
| `POLARIS_POSTGRES_ECHO` | `false` | Enables SQLAlchemy SQL logging when truthy. |
| `POLARIS_POSTGRES_POOL_PRE_PING` | `true` | Enables SQLAlchemy pool pre-ping. |
| `POLARIS_TEST_DATABASE_URL` | unset | Required only for guarded PostgreSQL integration and migration tests. |
| `POLARIS_ENABLE_POSTGRES_REPORT_PERSISTENCE` | unset / false | Enables CLI morning-report persistence as a report artifact path when truthy. |

Runtime workflow persistence is enabled by `WorkflowBootstrapConfig`:

```python
WorkflowBootstrapConfig(
    enable_postgres_runtime_persistence=True,
    postgres_runtime_persistence_fail_fast=False,
)
```

Keep runtime persistence disabled for local workflow experiments unless
PostgreSQL is running and migrations have been applied.

## Migrations

Alembic is the canonical schema migration mechanism. Do not use
`Base.metadata.create_all()` as the production schema path.

Install or synchronize dependencies:

```bash
uv sync
```

Apply all migrations to the configured database:

```bash
uv run alembic upgrade head
```

Inspect current and target revisions:

```bash
uv run alembic current
uv run alembic heads
```

Generate a new migration only after updating SQLAlchemy models:

```bash
uv run alembic revision --autogenerate -m "describe schema change"
```

Development-only rollback of one revision:

```bash
uv run alembic downgrade -1
```

Migration files may be squashed during development. Documentation must describe
schema ownership and validation contracts rather than maintaining migration-file
inventories, which become stale after squashes.

## Data contract convention

PostgreSQL is a serialization boundary. It may store JSON/JSONB payloads, but
those payloads must not become the primary internal platform contract.

Rules:

- Use canonical first-class columns for stable query dimensions, identity,
  timestamps, status, lineage, and operational state.
- Store complete nested source outputs in purpose-named JSON/JSONB payload
  columns when the data is needed for replay, audit, attribution, report
  reconstruction, or future curation but is not a stable relational dimension.
- Do not promote arbitrary metadata into durable schema. Add typed fields when a
  concept becomes canonical.
- Do not preserve legacy schema names after a canonical replacement is approved.
- Preserve full numeric precision and full LLM/report text at persistence
  boundaries. Rounding and truncation belong only in presentation renderers.
- Keep internal service, intelligence, and runtime contracts typed. Do not let
  persistence dictionaries leak back into core platform internals.

## Core table families and owners

Application persistence services expose typed use-case boundaries. Repository
implementations live under `core.storage.persistence` and remain infrastructure
concerns injected through DI. Callers should use the owning application service
or canonical runtime/application boundary rather than ad hoc SQL.

| Domain | Canonical PostgreSQL tables | Owning boundary |
| --- | --- | --- |
| Runtime execution | `workflow_runs`, `workflow_node_runs`, `workflow_events`, `workflow_state_snapshots` | Runtime persistence subscriber and `WorkflowStateSnapshotPersistenceService` |
| Completed runs | `completed_workflow_runs`, `completed_workflow_node_outputs`, `completed_run_artifacts` | Completed-run archive accessed through `WorkflowFacade` and `polaris runs` |
| Workflow-output projection queue | `workflow_output_projection_jobs` | Workflow-output projection operations, subscriber, and projectors |
| Reports | `reports`, `report_sections`, `report_artifacts`, `report_versions`, `report_publications` | `ReportPersistenceService` and report-specific application services |
| Agent signals | `agent_signals` | `AgentSignalPersistenceService` |
| Agent intelligence | `agent_reasoning`, `agent_recommendations`, `agent_risk_assessments` | `AgentIntelligencePersistenceService` |
| Recommendations | `recommendations`, `recommendation_rationales`, `recommendation_outcomes`, `trade_setups`, `watchlist_items` | `RecommendationPersistenceService` |
| Portfolio | `portfolio_state_history`, `portfolio_state_latest`, `portfolio_positions_history`, `portfolio_positions_latest`, `portfolio_exposure_snapshots`, `portfolio_risk_snapshots`, `portfolio_allocation_snapshots`, `portfolio_equity_history_points` | `PortfolioPersistenceService` |
| Market, technical, and events | `market_ohlcv`, `market_indicators`, `market_context_snapshots`, `technical_analysis_snapshots`, `market_breadth_snapshots`, `market_event_snapshots` | `MarketPersistenceService` |
| Macro | `macro_observations`, `macro_regime_snapshots`, `economic_calendar_events` | `MacroPersistenceService` |
| News | `news_articles`, `news_analysis_snapshots` | `NewsPersistenceService` |
| Sentiment | `sentiment_snapshots`, `sentiment_sources` | `SentimentPersistenceService` |
| Strategy synthesis | `strategy_hypotheses`, `strategy_synthesis_decisions`, `strategy_hypothesis_evaluations` | `StrategyPersistenceService` |
| Attribution | `attribution_records`, `signal_attribution`, `recommendation_attribution` | `AttributionPersistenceService` |
| Lineage | `persistence_lineage_links` | `LineagePersistenceService` |
| Audit | `persistence_audit_events` | `AuditPersistenceService` |
| Retention policy metadata | `persistence_retention_policies` | `RetentionPersistenceService` |
| Telemetry | `telemetry_events`, `telemetry_metrics`, `telemetry_traces`, `workflow_metrics`, `agent_metrics`, `provider_metrics` | `TelemetryPersistenceService` and telemetry persistence sink |
| Backtesting | `backtest_scenarios`, `backtest_runs`, `backtest_steps`, `backtest_portfolio_snapshots`, `backtest_fills`, `backtest_metrics`, `backtest_artifacts` | `BacktestPersistenceService` |
| RAG source eligibility and records | `rag_source_eligibility`, `rag_documents`, `rag_chunks`, `rag_embedding_jobs`, `rag_graph_jobs`, `rag_query_logs`, `rag_answer_logs` | RAG eligibility persistence, curated RAG services, and RAG operation services |
| Health and diagnostics | Database connectivity, Alembic state, `Base.metadata`, and required table availability | `HealthPersistenceService`, `DiagnosticsPersistenceService` |

## Completed run archive

Completed workflow runs are PostgreSQL-backed historical records. They are used
for audit, inspection, CLI history commands, report/RAG curation inputs, and
operational diagnostics after a workflow has finished.

Completed runs are not replay checkpoints. Replay and resume remain owned by the
runtime checkpointing and replay systems.

The completed-run archive is PostgreSQL-only. Local-disk completed-run archival
has been removed. Existing local JSON completed-run files are not imported
automatically; if they need retention later, add an explicit one-time import tool
rather than reintroducing local-disk archive writes.

Completed-run access belongs behind the async `WorkflowFacade` completed-run APIs
or `polaris runs` CLI commands. Application and CLI callers should not query
archive tables directly.

## Workflow-output projection to curated records

The workflow-output projection layer converts selected completed-run node outputs
into canonical typed records. It is the boundary that prevents every serialized
node field from becoming permanent business memory.

Projection requirements:

- explicit projector registration;
- supported `output_contract` and `output_schema_version`;
- authoritative source node;
- deterministic record identity;
- required fields and timestamp policy;
- execution-mode handling;
- lineage and attribution policy;
- idempotent write behavior through the owning application persistence service;
- retry/reconciliation through `workflow_output_projection_jobs`.

A node output is not a curated record merely because it was produced by a
successful workflow. Unsupported outputs remain completed-run evidence only.
Projectors may reject, skip, or quarantine outputs whose schema, execution mode,
or required fields are unsuitable for the target record family.

See `docs/platform_architecture_ownership_ledger.md` and
`docs/workflow_output_curation.md` for the ownership and curation rules.

## RAG persistence and projections

RAG is downstream of curated PostgreSQL records. PostgreSQL stores source
eligibility, curated RAG documents, chunks, queue records, and query/answer audit
logs. Qdrant and Neo4j are rebuildable retrieval projections.

Canonical RAG flow:

```text
curated PostgreSQL record
    -> eligibility decision in rag_source_eligibility
    -> curated RAG document and chunks in PostgreSQL
    -> rag_embedding_jobs and rag_graph_jobs
    -> Qdrant dense/sparse vector projection
    -> Neo4j graph projection
    -> query and answer logs in PostgreSQL
```

Current RAG source categories include reports, agent signals/intelligence,
recommendations, strategy synthesis records, portfolio records, market/technical
snapshots, macro snapshots, news summaries, sentiment summaries, attribution
records, and backtest records when explicitly supported by source loaders and
eligibility rules.

Rules:

- Build RAG documents from persisted curated source records, not provider
  payloads, raw runtime dumps, CLI output, JSONL telemetry, operational logs, or
  vector-store state.
- Preserve full report text, LLM reasoning, recommendation rationale, strategy
  rationale, and attribution at the PostgreSQL boundary.
- Store document text, chunks, metadata, source table, source id, source type,
  and source content hash in PostgreSQL before projection.
- Treat `rag_embedding_jobs` and `rag_graph_jobs` as durable PostgreSQL queue
  records for downstream projection processors.
- Treat Qdrant and Neo4j as rebuildable projections. Projection rebuilds must not
  delete canonical PostgreSQL records.
- Do not implement a second RAG ingestion, retrieval, ranking, graph, or
  persistence stack in interfaces such as CLI or MCP.

Current RAG operations are exposed through `polaris rag ...` and canonical RAG
application services. Background queue automation may be added later, but manual
commands remain useful for local development, backfills, rebuilds, and recovery.

## Runtime persistence

Runtime persistence subscribes to the canonical runtime `EventBus` when enabled
by `WorkflowBootstrapConfig`. It writes workflow run, node run, and runtime event
records into PostgreSQL without introducing a parallel execution path.

Persisted runtime records support audit, operational status, progress history,
and diagnostics. Raw runtime records are not curated RAG documents and should not
be used as a direct resume source.

## Report persistence

Morning report files are human-facing artifacts. The PostgreSQL report record is
the canonical persisted report when persistence is enabled.

Example:

```bash
POLARIS_ENABLE_POSTGRES_REPORT_PERSISTENCE=1 polaris morning-report
```

Report persistence stores:

- rendered Markdown body;
- structured report sections and metadata;
- generated artifact references.

Generated files should be linked as report artifacts rather than treated as the
only system of record.

## Telemetry persistence

Telemetry persistence is operational observability storage. It is intentionally
separate from curated intelligence, reports, and RAG source records.

Telemetry tables include:

- `telemetry_events`
- `telemetry_metrics`
- `telemetry_traces`
- `workflow_metrics`
- `agent_metrics`
- `provider_metrics`

Rules:

- Use telemetry persistence for observability, diagnostics, retention, and trace
  correlation.
- Telemetry persistence failures should be visible but non-fatal to otherwise
  valid domain results.
- Do not ingest raw telemetry records directly into RAG. If operational history
  is ever useful for retrieval, create a typed curated summary first.

## Backtesting persistence

Backtesting uses the production runtime and service contracts. Persistence stores
scenario definitions, run metadata, deterministic steps, portfolio snapshots,
fills, metrics, and artifacts. Backtest records are durable evidence and may
become RAG-eligible only through explicit typed source loaders and eligibility
rules.

The runtime remains unaware of live versus simulated execution mode. Execution
mode belongs in first-class lineage and completed-run/projection records, not in
parallel runtime state models.

## Query, lineage, validation, audit, and retention support

The persistence layer includes cross-domain support services:

- Query primitives and `PersistenceListResult[T]` / `PersistenceReadResult[T]`
  envelopes for typed pagination, sorting, filtering, and metadata.
- Relational lineage traversal over `persistence_lineage_links`.
- Non-mutating validation checks for timestamps, score ranges, lineage, source
  identity, and dedupe keys.
- Append-only audit events in `persistence_audit_events`.
- Dry-run retention planning through `persistence_retention_policies`.
- Health and diagnostics checks for connectivity, Alembic revision state,
  metadata import, and required table availability.

Retention support is advisory unless a future destructive lifecycle plan adds
policy, governance, approval, telemetry, and audit boundaries. Do not physically
delete canonical records through retention services without that explicit path.

## Excluded RAG and persistence sources

The following are not canonical curated records and should not be ingested into
RAG or treated as business system-of-record data without an explicit typed
curation layer:

- `workflow_runs`, `workflow_node_runs`, `workflow_events`, and raw
  `workflow_state_snapshots`;
- `completed_workflow_runs` and `completed_workflow_node_outputs` as raw dumps;
- `telemetry_events`, `telemetry_metrics`, `telemetry_traces`,
  `workflow_metrics`, `agent_metrics`, and `provider_metrics`;
- raw provider payloads and HTTP/SDK responses;
- raw CLI output;
- operational logs, caches, JSONL telemetry, and generated debug artifacts;
- Qdrant, Neo4j, or any vector/graph index state.

## Validation commands

Run focused persistence tests:

```bash
uv run pytest -q tests/unit/core/database tests/unit/core/storage/persistence tests/unit/application/persistence
```

Run application persistence integration tests with fakes:

```bash
uv run pytest -q tests/integration/application/persistence
```

Run guarded PostgreSQL integration tests after starting PostgreSQL and setting
`POLARIS_TEST_DATABASE_URL` in your shell:

```bash
uv run pytest -q tests/integration/core/storage/persistence
```

Run migration contract tests after starting PostgreSQL and setting
`POLARIS_TEST_DATABASE_URL`:

```bash
uv run pytest -q tests/database
```

Run migration and metadata checks:

```bash
uv run alembic heads
uv run alembic current
uv run python -c "import core.database.models; print('database models import ok')"
```

Run static checks for changed Python persistence code:

```bash
uv run ruff check core/database core/storage/persistence application/persistence tests/unit/core/database tests/unit/core/storage/persistence tests/unit/application/persistence tests/integration/application/persistence
uv run mypy --explicit-package-bases core/database core/storage/persistence application/persistence tests/unit/core/database tests/unit/core/storage/persistence tests/unit/application/persistence tests/integration/application/persistence
```
