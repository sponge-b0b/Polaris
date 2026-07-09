# Platform Persistence Plan

## Core Principle

PostgreSQL is the system-of-record.

RAG stores such as Qdrant or Neo4j should not be the primary source of truth. They should be populated from curated PostgreSQL records.

```text
Runtime / Services / Agents
    -> PostgreSQL canonical records
        -> embedding jobs
            -> Qdrant / Neo4j
```
Persistence Layers

1. Runtime Persistence

Persist every workflow execution.

Tables:

workflow_runs
workflow_node_runs
workflow_events
workflow_artifacts
workflow_checkpoints
workflow_control_events

Purpose:

replay
audit
debugging
CLI history
progress history
workflow state

Persist:

Persist:

workflow_name
execution_id
runtime_id
status
started_at
completed_at
duration
node outputs
node metadata
errors
artifacts
checkpoint references
pause/resume/cancel events

2. Telemetry Persistence

Keep JSONL for local debugging, but add PostgreSQL telemetry.

Tables:

telemetry_events
telemetry_metrics
telemetry_traces

Purpose:

observability
reporting
agent performance
provider latency
confidence tracking
failure analysis

Persist:

event_type
source
level
workflow_id
execution_id
node_name
correlation_id
duration_seconds
success
error_count
attributes
payload
timestamp

3. Portfolio Persistence

Existing PortfolioState is correct, but expand around it.

Recommended adjustments:

Keep:
- portfolio_state_history
- portfolio_state_latest
- account_id index
- timestamp index
- schema_version
- risk_signals JSON/JSONB

Improve:
- Use JSONB if PostgreSQL-specific
- Add created_at / updated_at
- Add source_run_id or execution_id
- Add workflow_name if snapshot came from workflow
- Add symbol/universe if relevant
- Add unique constraint on latest.account_id

I would treat these as the portfolio persistence foundation, then add related tables around them:

Tables:

portfolio_positions_history
portfolio_positions_latest
portfolio_exposure_snapshots
portfolio_risk_snapshots
portfolio_recommendations
portfolio_attribution

Persist:

account state
positions
cash
exposure
drawdown
risk signals
allocation intent
recommendations
attribution

Your PortfolioState should remain the canonical account-level snapshot.

4. Market Data Persistence

Persist normalized provider data used by analysis.

Tables:

market_ohlcv
market_indicators
market_context_snapshots
technical_analysis_snapshots

Persist:

symbol
timestamp
open/high/low/close/volume
EMA
RSI
MACD
ATR
HV
VIX
VVIX
AD-line proxy
technical score
trend score
volatility score
breadth score

Important:

Alpha Vantage TOP_GAINERS_LOSERS should be stored as a breadth proxy snapshot, not true historical AD Line.

Suggested table:

market_breadth_snapshots

Fields:

source
snapshot_date
advancers
decliners
net_advancers
cumulative_proxy_value
is_proxy
raw_payload

5. Macro Persistence

Tables:

macro_observations
macro_regime_snapshots
economic_calendar_events

Persist:

CPI
core CPI
PCE
Fed funds
2Y
10Y
yield curve slope
M2
unemployment
VIX macro
macro regime
fed stance
inflation regime
liquidity regime

This feeds:

FundamentalAgent
MacroAgent
MorningReport
RAG
historical regime analysis

6. News and Sentiment Persistence

Tables:

news_articles
news_analysis_snapshots
sentiment_snapshots
sentiment_articles

Persist:

title
summary
url
source
published_at
symbols
relevance_score
sentiment_score
themes
LLM summary
risks
recommendations

Use deduplication key:

source + url

or:

source + external_id

7. Agent Signal Persistence

This is critical for RAG and attribution.

Tables:

agent_signals
agent_signal_features
agent_recommendations
agent_risks
agent_reasoning

Persist each agent output:

agent_name
agent_type
workflow_name
execution_id
symbol
directional_score
confidence
regime
signals
risks
recommendations
features
llm_response
timestamp

This should become the canonical source for later RAG ingestion.

8. Reports Persistence

Tables:

reports
report_sections
report_artifacts

Persist:

report_type
workflow_name
execution_id
symbol
title
markdown
json_path
pdf_path
summary
generated_at

For morning reports:

morning_report.md
morning_report.pdf
morning_report.json

should be artifacts, while the report metadata and text are stored in PostgreSQL.

9. Recommendation Persistence

Tables:

recommendations
recommendation_rationales
recommendation_outcomes
watchlist_items
trade_setups

Persist:

recommendation_type
symbol
bias
confidence
risk_score
time_horizon
setup_quality
entry_context
invalidations
risk_notes
human_action
outcome

Because the platform is recommendation-based, this becomes one of the most important datasets.

10. RAG Document Persistence

Before embedding into Qdrant/Neo4j, store canonical documents in PostgreSQL.

Tables:

rag_documents
rag_chunks
rag_embeddings_jobs
rag_sources

Persist documents from:

morning reports
agent signals
macro regimes
news summaries
technical snapshots
risk snapshots
recommendations
backtest reports
research notes

Recommended flow:

PostgreSQL source records
    -> RAG document builder
        -> chunks
            -> embedding job
                -> vector store
                -> graph store

Do not embed raw runtime dumps.
Embed curated human-readable records.

Recommended Schema Groups

# Runtime
workflow_runs
workflow_node_runs
workflow_events
workflow_artifacts
workflow_checkpoints

# Observability
telemetry_events
telemetry_metrics

# Portfolio
portfolio_states
portfolio_positions
portfolio_risk_snapshots
portfolio_exposures

# Market
market_ohlcv
market_indicators
market_context_snapshots
market_breadth_snapshots
technical_analysis_snapshots

# Macro
macro_observations
macro_regime_snapshots
economic_calendar_events

# Intelligence
agent_signals
agent_recommendations
agent_risks
agent_reasoning

# News/Sentiment
news_articles
news_analysis_snapshots
sentiment_snapshots

# Reports
reports
report_sections
report_artifacts

# RAG
rag_documents
rag_chunks
rag_embedding_jobs

Implementation Order

Phase 1: Persistence Foundation

core
├── database
│   ├── __init__.py
│   ├── base.py
│   ├── models
│   │   ├── __init__.py
│   │   └── portfolio.py
│   └── postgres.py
├── storage
│   └── persistence
│       ├── __init__.py
│       ├── repositories
│       │   ├── __init__.py
│       │   ├── portfolio_state_repository.py
│       │   └── postgres_portfolio_state_repository.py
│       └── serializers
│           ├── __init__.py
│           └── portfolio_state_serializer.py

Use:

SQLAlchemy 2.x
Alembic
PostgreSQL JSONB

Create base repository pattern.

Phase 2: Runtime Persistence

Persist:

workflow_runs
workflow_node_runs
workflow_events
workflow_artifacts

This lets every workflow execution become queryable.

Phase 3: Intelligence Persistence

Persist:

agent_signals
reports
recommendations

This gives RAG meaningful material.

Phase 4: Market/Macro Persistence

Persist:

market_ohlcv
technical_analysis_snapshots
macro_regime_snapshots
news_articles
sentiment_snapshots

This gives analysis history.

Phase 5: RAG Ingestion Pipeline

Build:
```
application/rag/
├── rag_document_builder.py
├── rag_chunker.py
├── rag_ingestion_service.py
└── rag_repository.py
```
Start with embedding:

morning reports
agent signals
macro summaries
recommendations

First schemas/tables:

workflow_runs
workflow_node_runs
reports
agent_signals
rag_documents

That gives the platform enough persistence to support:

workflow history
report history
agent signal history
RAG ingestion
future API/Web UI

---

# Codex Recommended Implementation Plan

## Summary

Implement PostgreSQL as the canonical system-of-record for the platform, with RAG vector/graph stores populated only from curated PostgreSQL records.

Planning decisions:

- V1 scope: Runtime + RAG foundation.
- Core changes: authorized, limited to persistence/storage/bootstrap/runtime integration.
- Local DB setup: keep current docker-compose values as canonical.
- Implementation cadence: one step at a time, each intended to be about 3-5 minutes, with review before the next step.
- Preserve this original plan content and append implementation results incrementally below this section.

## Key Architecture Changes

- Make PostgreSQL primary persistence when configured through WorkflowBootstrap.
- Keep WorkflowFacade and WorkflowBootstrap as the application/runtime boundaries.
- Use SQLAlchemy 2.x async models/repositories and Alembic migrations.
- Replace hardcoded database connection behavior with typed/env-driven configuration using the existing compose defaults:
  - host: localhost
  - port: 5432
  - database: polaris
  - user: polaris
- Keep local disk run persistence available only as an optional local/debug adapter.
- Use PostgreSQL JSONB only at persistence/serialization boundaries.
- Preserve typed domain/runtime objects internally.
- Do not embed raw runtime dumps into RAG stores.
- Create curated PostgreSQL records first, then build RAG documents/chunks from those records.

## V1 Persistence Targets

V1 should implement the minimum durable foundation needed for workflow history, reports, agent intelligence, and RAG ingestion:

- Runtime:
  - workflow_runs
  - workflow_node_runs
  - workflow_events
- Reports:
  - reports
  - report_sections
  - report_artifacts
- Intelligence:
  - agent_signals
- RAG source records:
  - rag_documents
  - rag_chunks
  - rag_embedding_jobs

Portfolio, market, macro, news, sentiment, recommendation, and telemetry expansion should follow after this foundation is stable.

## Implementation Steps

- [x] Step 1 - Append implementation plan
  - Append this recommended plan to `.agent/plans/plan_postgres_persistence.md` under a separate Codex/recommended-plan section.
  - Preserve the original plan content.
  - Confirm existing uncommitted persistence edits before changing implementation files.

- [x] Step 2 - Normalize database configuration
  - Replace hardcoded Postgres connection construction with typed database settings.
  - Prefer `POLARIS_DATABASE_URL` when present.
  - Otherwise derive the URL from compose-aligned defaults.
  - Add unit tests for URL resolution and defaults.

- [x] Step 3 - Add Alembic migration foundation
  - Add Alembic config/env wiring against `core.database.base.Base.metadata`.
  - Ensure all SQLAlchemy models are imported by migration metadata.
  - Do not rely on `Base.metadata.create_all` as the production path.
  - Keep `scripts/initialize_database.py` only as a local/dev helper if still useful.

- [x] Step 4 - Reconcile existing portfolio persistence edits
  - Review current `portfolio_state` model/repository changes.
  - Preserve the portfolio state foundation.
  - Convert Postgres-specific JSON fields to JSONB.
  - Add timestamps/source metadata only where low-risk.
  - Avoid broad portfolio schema expansion in V1.

- [x] Step 5 - Add runtime persistence contracts
  - Add typed persistence DTOs/results for workflow run, node run, and runtime event persistence.
  - Keep dictionaries only at the serialization boundary.
  - Avoid replacing runtime domain objects with raw dict contracts.

- [x] Step 6 - Add runtime SQLAlchemy models
  - Add models for `workflow_runs`, `workflow_node_runs`, and `workflow_events`.
  - Include execution/workflow/runtime identifiers, status, timestamps, duration, node metadata, output payloads, errors, and lineage fields.
  - Use JSONB for serialized runtime payloads.

- [x] Step 7 - Add runtime migration
  - Create the Alembic migration for runtime tables and indexes.
  - Index by workflow_name, execution_id, runtime_id, status, and timestamps.

- [x] Step 8 - Add runtime repository
  - Implement async Postgres repository methods for saving workflow runs, node runs, and runtime events.
  - Add idempotent upsert behavior for workflow run summaries.
  - Keep event inserts append-only.

- [x] Step 9 - Wire runtime persistence through bootstrap
  - Add bootstrap config flags for Postgres persistence.
  - Compose the Postgres repository/session through WorkflowBootstrap/DI.
  - Subscribe persistence to canonical runtime events via EventBus.
  - Do not introduce parallel runtime execution paths.

- [x] Step 10 - Add runtime persistence tests
  - Unit test serializers and repository behavior using fakes where possible.
  - Add integration tests guarded by `POLARIS_TEST_DATABASE_URL`.
  - Confirm workflows still run without Postgres when persistence is disabled.
  - Step 10 completed: added explicit runtime persistence serializer round-trip tests, expanded fake-backed repository/subscriber coverage, added a disabled-persistence workflow regression test proving workflows still execute without Postgres, and added guarded Postgres integration tests for repository round-trips plus EventBus subscriber projection when `POLARIS_TEST_DATABASE_URL` is provided.

- [x] Step 11 - Add report persistence models
  - Add `reports`, `report_sections`, and `report_artifacts`.
  - Persist report title, type, workflow/execution lineage, markdown body, structured metadata, generated timestamp, and artifact references.
  - Step 11 completed: added SQLAlchemy report persistence models for human-readable report documents, ordered report sections, and artifact references; imported them into Alembic metadata; added a chained Alembic migration with JSONB persistence-boundary fields, lineage indexes, section uniqueness, and report/artifact relationships; and added unit tests for model shape, JSONB usage, migration coverage, and metadata import.

- [x] Step 12 - Wire morning report persistence
  - Persist the curated morning report output after successful report assembly.
  - Store full human-readable report content.
  - Do not truncate LLM/report text.
  - Keep file artifacts as artifacts, not the only system-of-record.
  - Step 12 completed: added typed report persistence boundary records, a report repository contract, serializers, and an async PostgreSQL report repository; added a morning-report persistence mapper/service that stores the full rendered markdown plus full structured typed document payloads without truncation; wired the CLI morning-report command to optionally persist curated reports to PostgreSQL when `POLARIS_ENABLE_POSTGRES_REPORT_PERSISTENCE=1`; and records written CLI files as report artifacts rather than treating artifacts as the source of truth.

- [x] Step 13 - Add agent signal persistence
  - Add `agent_signals` model/repository.
  - Persist typed signal outputs after serialization at the boundary.
  - Include agent name/type, workflow lineage, symbol/universe context, confidence, directional score, regime, risks, recommendations, and full reasoning/LLM text where available.
  - Step 13 completed: added the `agent_signals` SQLAlchemy model and chained Alembic migration; added typed `AgentSignalRecord`/result contracts, serializer, repository protocol, and async PostgreSQL upsert repository; preserved full reasoning/LLM text without truncation; and added focused model, migration, contract, serializer, and repository tests. This step establishes typed signal persistence at the boundary and intentionally does not ingest raw runtime dumps for RAG.

- [x] Step 14 - Add RAG source document models
  - Add `rag_documents`, `rag_chunks`, and `rag_embedding_jobs`.
  - Store source table/source id/source type for lineage.
  - Store chunk text and metadata in Postgres before any vector-store write.
  - Step 14 completed: added SQLAlchemy models and chained Alembic migration for canonical RAG source documents, ordered chunks, and embedding projection jobs; added typed `RagDocumentRecord`, `RagChunkRecord`, `RagEmbeddingJobRecord`, bundle/result contracts, serializer, repository protocol, and async PostgreSQL upsert repository; preserved source table/id/type lineage and full chunk/document text in PostgreSQL before any vector-store write.

- [x] Step 15 - Add curated RAG document builder
  - Build RAG documents from persisted reports and agent signals only.
  - Explicitly avoid raw runtime dumps.
  - Keep vector-store integration out of this first pass except for queued embedding job records.
  - Step 15 completed: added an application-level curated RAG document builder and ingestion service that accept only persisted `ReportRecord` and `AgentSignalRecord` sources, preserve full report/LLM text, create canonical `RagPersistenceBundle` records with ordered chunks and queued embedding jobs, and explicitly reject raw runtime dump payloads. No vector-store writes were introduced.

- [x] Step 16 - Add CLI/dev docs
  - Document how to start the existing compose Postgres service.
  - Document migration commands.
  - Document env variables and defaults.
  - Explain that PostgreSQL is canonical and vector stores are derived.
  - Step 16 completed: added `docs/postgres_persistence.md` covering compose startup, typed Postgres environment variables/defaults, Alembic migration commands, CLI/report persistence, runtime persistence, RAG/vector-store derivation rules, and validation commands; linked it from `README.md` and `migrations/README.md`; validation passed with targeted persistence/RAG pytest.

- [x] Step 17 - Final validation
  - Run targeted pytest suites.
  - Run ruff.
  - Run mypy where practical.
  - Run migration metadata/import checks.
  - Run `graphify update .` after code changes.
  - Stop for review before commit/push.
  - Step 17 completed: final validation passed with targeted pytest (`123 passed, 2 skipped`), ruff, scoped mypy with explicit package bases, Alembic heads/history checks, SQLAlchemy metadata import checks, `graphify update .`, and graph HTML regeneration with the higher visualization node limit.

## Public Interfaces / Types

- Add database settings type for Postgres URL resolution.
- Add async Postgres repository contracts for runtime, reports, agent signals, and RAG source documents.
- Extend `WorkflowBootstrapConfig` with Postgres persistence settings.
- Preserve existing WorkflowFacade as the workflow execution boundary.
- Preserve runtime node output contracts.
- Keep typed internal models; serialize only at persistence/RAG boundaries.

## Test Plan

- Unit tests:
  - database settings URL resolution
  - runtime serializers
  - report persistence serializers
  - agent signal persistence serializers
  - RAG document builder behavior

- Integration tests:
  - Postgres-backed runtime persistence when `POLARIS_TEST_DATABASE_URL` is set
  - workflow execution persists run summary/events
  - morning report persists full report content
  - RAG documents are created from curated report/signal records

- Regression tests:
  - workflows still run with local disk persistence only
  - CLI output remains unaffected when Postgres persistence is disabled
  - no RAG document is created directly from raw runtime dump payloads

## Assumptions

- Existing docker-compose Postgres values are canonical for local development.
- V1 does not attempt to model the entire platform persistence universe.
- Existing uncommitted persistence work must be reconciled, not overwritten.
- PostgreSQL becomes the canonical configured system-of-record; local disk remains optional/debug.
- RAG vector/graph stores are downstream projections from curated PostgreSQL records.

## Step Results

- [x] Step 1 completed: appended Codex recommended implementation plan as a separate section and preserved the original plan content.
- [x] Step 2 completed: added typed Postgres settings, wired `core.database.postgres` to resolve `POLARIS_DATABASE_URL` or compose-aligned defaults, and added unit tests for URL resolution.
- [x] Step 3 completed: added Alembic scaffold, migration environment wiring to `Base.metadata`, model metadata imports, and metadata/config validation tests.
- [x] Step 4 completed: reconciled portfolio persistence models around `portfolio_state`, converted risk payloads to PostgreSQL JSONB, added nullable workflow/execution lineage plus timestamp metadata, cleaned repository formatting/upsert timestamp handling, and added focused model/serializer tests.
- [x] Step 5 completed: added typed runtime persistence boundary records/results and an async repository protocol for workflow runs, node runs, and runtime events without introducing raw `dict[str, Any]` internal contracts.
- [x] Step 6 completed: added SQLAlchemy runtime persistence models for `workflow_runs`, `workflow_node_runs`, and `workflow_events`, including execution lineage, statuses, timestamps, duration/error fields, JSONB serialized boundary payloads, and focused metadata/import tests.
- [x] Step 7 completed: added Alembic migration `20260530_0001_add_runtime_persistence_tables.py` for runtime tables and query indexes, aligned runtime model indexes for execution lookups, and validated Alembic history/offline SQL generation.
- [x] Step 8 completed: added the async PostgreSQL runtime persistence repository, typed record/model serializer, idempotent upserts for workflow and node summaries, append-only event inserts, read/list methods, and focused repository tests.
- [x] Step 9 completed: wired PostgreSQL runtime persistence through WorkflowBootstrap configuration and DI/EventBus composition, added an EventBus subscriber that projects canonical RuntimeEvent envelopes into typed workflow/event/node persistence records, preserved local runtime execution paths, and kept persistence disabled by default unless explicitly configured or injected.
- [x] Step 10 completed: added explicit runtime persistence serializer round-trip tests, expanded fake-backed repository/subscriber coverage, added a disabled-persistence workflow regression test proving workflows still execute without Postgres, and added guarded Postgres integration tests for repository round-trips plus EventBus subscriber projection when `POLARIS_TEST_DATABASE_URL` is provided.
- [x] Step 11 completed: added SQLAlchemy report persistence models for human-readable report documents, ordered report sections, and artifact references; imported them into Alembic metadata; added a chained Alembic migration with JSONB persistence-boundary fields, lineage indexes, section uniqueness, and report/artifact relationships; and added unit tests for model shape, JSONB usage, migration coverage, and metadata import.
- [x] Step 12 completed: added typed report persistence boundary records, a report repository contract, serializers, and an async PostgreSQL report repository; added a morning-report persistence mapper/service that stores the full rendered markdown plus full structured typed document payloads without truncation; wired the CLI morning-report command to optionally persist curated reports to PostgreSQL when `POLARIS_ENABLE_POSTGRES_REPORT_PERSISTENCE=1`; and records written CLI files as report artifacts rather than treating artifacts as the source of truth.
- [x] Step 13 completed: added typed agent signal persistence as a PostgreSQL system-of-record foundation for curated signal history, attribution, and future RAG source generation; validation passed with `pytest`, `ruff`, and scoped `mypy`.
- [x] Step 14 completed: added typed RAG source document persistence tables/contracts/repository for `rag_documents`, `rag_chunks`, and `rag_embedding_jobs`; validation passed with `pytest`, `ruff`, and scoped `mypy`.
- [x] Step 15 completed: added curated RAG document builder/service for persisted reports and agent signals only, with raw runtime dump rejection and queued embedding job record creation; validation passed with `pytest`, `ruff`, and scoped `mypy`.
- [x] Step 16 completed: added CLI/developer PostgreSQL persistence documentation for compose startup, migrations, environment variables/defaults, canonical system-of-record guidance, report/runtime persistence, and derived RAG/vector-store projections; validation passed with targeted persistence/RAG pytest.
- [x] Step 17 completed: final PostgreSQL persistence validation passed with targeted pytest (`123 passed, 2 skipped`), ruff, scoped mypy, Alembic heads/history checks, SQLAlchemy metadata import checks, `graphify update .`, and graph HTML regeneration.

# See Also:
.agent/plans/plan_postgres_persistence_v2.md
.agent/plans/plan_postgres_persistence_v3.md
