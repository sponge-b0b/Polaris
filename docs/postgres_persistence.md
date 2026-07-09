# PostgreSQL Persistence

PostgreSQL is Polaris's canonical system-of-record for persisted platform data.
Runtime artifacts, JSONL telemetry, Markdown reports, and vector indexes are
secondary outputs used for local debugging, exports, search, replay support, or
downstream projections. They are not the source of truth.

## Local Postgres service

The repository already includes a compose-managed PostgreSQL service named
`postgres`.

Start it from the repository root:

```bash
docker compose up -d postgres
```

Check service status:

```bash
docker compose ps postgres
```

The compose defaults are:

```text
host: localhost
port: 5432
database: polaris
user: polaris
password: <required; load from the untracked .env file>
```

Polaris derives the async SQLAlchemy URL at runtime from environment settings. Credentials must not be written into tracked documentation or source files.

## Environment variables

Copy `.env.example` to the ignored `.env` file and set the required local service secrets before starting Docker Compose. Never commit `.env`.

Database configuration is owned by `core.database.settings.PostgresSettings`.
Use `POLARIS_DATABASE_URL` when a full connection string is available. If it is
not set, Polaris derives the URL from the `POLARIS_POSTGRES_*` variables below.

| Variable                                   | Default       | Notes                                                                                  |
| ------------------------------------------ | ------------- | -------------------------------------------------------------------------------------- |
| `POLARIS_DATABASE_URL`                       | unset         | Preferred full URL override. `postgresql://...` is normalized to the async driver form. |
| `POLARIS_POSTGRES_HOST`                      | `localhost`   | Compose-compatible local host.                                                         |
| `POLARIS_POSTGRES_PORT`                      | `5432`        | Must be an integer.                                                                    |
| `POLARIS_POSTGRES_DB`                        | `polaris`       | Database name.                                                                         |
| `POLARIS_POSTGRES_USER`                      | `polaris`       | Database user.                                                                         |
| `POLARIS_POSTGRES_PASSWORD`                  | required      | Database password; store it only in the untracked `.env` file or a secret manager.     |
| `POLARIS_POSTGRES_DRIVER`                    | `asyncpg`     | SQLAlchemy async driver suffix.                                                        |
| `POLARIS_POSTGRES_ECHO`                      | `false`       | Enables SQLAlchemy SQL logging when truthy.                                            |
| `POLARIS_POSTGRES_POOL_PRE_PING`             | `true`        | Enables SQLAlchemy pool pre-ping.                                                      |
| `POLARIS_TEST_DATABASE_URL`                  | unset         | Required only for guarded PostgreSQL integration tests.                                |
| `POLARIS_ENABLE_POSTGRES_REPORT_PERSISTENCE` | unset / false | Enables morning-report persistence from the CLI when truthy.                           |

Runtime workflow persistence is enabled through `WorkflowBootstrapConfig`:

```python
WorkflowBootstrapConfig(
    enable_postgres_runtime_persistence=True,
    postgres_runtime_persistence_fail_fast=False,
)
```

Keep it disabled for local workflows unless PostgreSQL is running and migrations
have been applied.

## Migrations

Install or synchronize dependencies with uv:

```bash
uv sync
```

Apply all migrations to the configured database:

```bash
uv run alembic upgrade head
```

Inspect the current database revision:

```bash
uv run alembic current
```

Inspect migration heads and history:

```bash
uv run alembic heads
uv run alembic history
```

Generate a new migration only after updating SQLAlchemy models:

```bash
uv run alembic revision --autogenerate -m "describe schema change"
```

Development-only rollback of one revision:

```bash
uv run alembic downgrade -1
```

Do not use `Base.metadata.create_all()` as the production schema path. Alembic is
the canonical schema migration mechanism.

## Persistence data contract convention

PostgreSQL is the platform system-of-record for curated persisted data. ORM
models should expose stable, canonical query fields as relational columns while
preserving complete nested service, agent, and report outputs in explicit JSON or
JSONB payload columns. This keeps common filters, joins, and lineage queries
first-class without discarding the full source output needed for replay, audit,
attribution, future RAG curation, and report reconstruction.

Rules:

- Use canonical column names in ORM models and Alembic migrations.
- Do not preserve legacy schema names after a canonical replacement is approved.
- Store full nested service/agent outputs in purpose-named payload columns when
  the data is not a stable query dimension.
- Treat persistence as a serialization boundary where JSON/JSONB payloads are
  acceptable.
- Keep internal application service and intelligence-agent contracts typed where
  feasible; do not let persistence payload dictionaries become internal platform
  contracts.
- Preserve full numeric precision and full LLM/report text at the persistence
  boundary. Rounding and truncation belong only in presentation renderers.

## Completed run archive

Completed workflow runs are PostgreSQL-backed historical records. They are
stored for audit, inspection, CLI history commands, report/RAG curation inputs,
and operational diagnostics after a workflow has finished.

Completed runs are not replay checkpoints. Replay and resume behavior remains
owned by the runtime checkpointing/replay systems; do not use completed-run
history as a workflow resume source.

The completed-run archive is PostgreSQL-only. Local-disk completed-run archival
has been removed, and existing local JSON completed-run files are not imported
automatically. If historical local JSON files need to be retained later, add an
explicit one-time import tool instead of reintroducing local-disk archive writes.

Completed-run archival uses these tables:

| Table | Purpose |
| --- | --- |
| `completed_workflow_runs` | One canonical historical record per completed workflow execution. |
| `completed_workflow_node_outputs` | Node-level output/error/status records for a completed workflow execution. |
| `completed_run_artifacts` | Artifact metadata associated with a completed workflow execution. |

Access completed-run history through the async `WorkflowFacade` completed-run
APIs or the `polaris runs` CLI commands. Application and CLI callers should not
query the archive tables directly.

## Migration inventory

Current PostgreSQL persistence migrations are:

| Revision file | Scope |
| --- | --- |
| `20260530_0001_add_runtime_persistence_tables.py` | Workflow runs, node runs, runtime events. |
| `20260530_0002_add_report_persistence_tables.py` | Reports, report sections, report artifacts. |
| `20260530_0003_add_agent_signal_persistence_table.py` | Agent signal records. |
| `20260530_0004_add_rag_source_persistence_tables.py` | RAG documents, chunks, embedding jobs. |
| `20260530_0005_add_persistence_lineage_links.py` | Cross-record lineage links. |
| `20260530_0006_add_recommendation_persistence_tables.py` | Recommendations, rationales, outcomes, trade setups, watchlist items. |
| `20260530_0007_add_portfolio_expansion_persistence_tables.py` | Position history/latest, exposure, risk, allocation snapshots. |
| `20260530_0008_add_market_persistence_tables.py` | OHLCV, indicators, market context, technical snapshots, breadth snapshots. |
| `20260530_0009_add_macro_persistence_tables.py` | Macro observations, macro regime snapshots, economic calendar events. |
| `20260530_0010_add_news_persistence_tables.py` | News articles and news analysis snapshots. |
| `20260530_0011_add_sentiment_persistence_tables.py` | Sentiment snapshots and sentiment sources. |
| `20260530_0012_add_agent_intelligence_persistence_tables.py` | Agent reasoning, recommendations, and risk assessments. |
| `20260530_0013_add_attribution_persistence_tables.py` | Attribution records, signal attribution, recommendation attribution. |
| `20260530_0014_add_workflow_state_snapshot_persistence_table.py` | Workflow state snapshots. |
| `20260530_0015_add_report_version_publication_tables.py` | Report versions and publications. |
| `20260530_0016_add_telemetry_persistence_tables.py` | Operational telemetry events, metrics, traces, workflow/agent/provider metrics. |
| `20260530_0017_add_persistence_audit_events.py` | Append-only audit events for persisted business records. |
| `20260530_0018_add_rag_source_eligibility.py` | Metadata-only RAG source eligibility markers for canonical PostgreSQL records. |
| `20260530_0019_add_persistence_retention_policies.py` | Retention policy metadata for dry-run lifecycle planning. |

## Persistence tables and services

Application persistence services expose typed use-case boundaries. Repository
implementations remain infrastructure concerns under `core.storage.persistence`
and should be injected rather than located dynamically. Existing application
persistence services are the canonical read/write boundaries; do not create
parallel query-service packages for the same domain.

| Domain | Canonical PostgreSQL tables | Application service |
| --- | --- | --- |
| Runtime audit | `workflow_runs`, `workflow_node_runs`, `workflow_events`, `workflow_state_snapshots` | `WorkflowStateSnapshotPersistenceService` plus runtime event subscriber wiring. |
| Reports | `reports`, `report_sections`, `report_artifacts`, `report_versions`, `report_publications` | `ReportPersistenceService` |
| Agent signals | `agent_signals` | repository-level source for typed signal records |
| Agent intelligence | `agent_reasoning`, `agent_recommendations`, `agent_risk_assessments` | `AgentIntelligencePersistenceService` |
| Recommendations | `recommendations`, `recommendation_rationales`, `recommendation_outcomes`, `trade_setups`, `watchlist_items` | `RecommendationPersistenceService` |
| Portfolio | `portfolio_state_history`, `portfolio_state_latest`, `portfolio_positions_history`, `portfolio_positions_latest`, `portfolio_exposure_snapshots`, `portfolio_risk_snapshots`, `portfolio_allocation_snapshots` | `PortfolioPersistenceService` |
| Market and technical | `market_ohlcv`, `market_indicators`, `market_context_snapshots`, `technical_analysis_snapshots`, `market_breadth_snapshots` | `MarketPersistenceService` |
| Macro | `macro_observations`, `macro_regime_snapshots`, `economic_calendar_events` | `MacroPersistenceService` |
| News | `news_articles`, `news_analysis_snapshots` | `NewsPersistenceService` |
| Sentiment | `sentiment_snapshots`, `sentiment_sources` | `SentimentPersistenceService` |
| Attribution | `attribution_records`, `signal_attribution`, `recommendation_attribution` | `AttributionPersistenceService` |
| RAG source queue | `rag_documents`, `rag_chunks`, `rag_embedding_jobs` | `PostgresRagPersistenceRepository` and curated RAG application services |
| RAG eligibility | `rag_source_eligibility` | `RagEligibilityPersistenceService` |
| Operational telemetry | `telemetry_events`, `telemetry_metrics`, `telemetry_traces`, `workflow_metrics`, `agent_metrics`, `provider_metrics` | `TelemetryPersistenceService` |
| Lineage | `persistence_lineage_links` | `LineagePersistenceService` |
| Audit | `persistence_audit_events` | `AuditPersistenceService` |
| Retention policy metadata | `persistence_retention_policies` | `RetentionPersistenceService` |
| Health and diagnostics | database connectivity, Alembic revision state, `Base.metadata`, required table availability | `HealthPersistenceService`, `DiagnosticsPersistenceService` |

## V3 pre-RAG persistence architecture

V3 completes the PostgreSQL foundation before full RAG ingestion or embedding
work begins. It hardens the existing persistence layer rather than introducing a
new execution path.

V3 adds:

- shared query primitives and result envelopes;
- relational lineage traversal over `persistence_lineage_links`;
- non-destructive validation services for timestamps, scores, lineage, source
  identity, and dedupe keys;
- append-only audit event persistence;
- idempotency review coverage and shared idempotency key helpers;
- metadata-only RAG eligibility marking and optional curated RAG gating;
- JSON-compatible export boundaries for selected typed records;
- dry-run retention planning and advisory archive markers;
- persistence health and diagnostics services;
- aggregate migration coverage for all V3 tables.

V3 does not add:

- vector-store writes;
- graph-store writes;
- embedding workers;
- full RAG ingestion workflows;
- FastAPI endpoints;
- destructive retention execution;
- direct provider-payload ingestion into RAG.

## Query primitives and result envelopes

Shared query contracts live under `core.storage.persistence.query` and provide
reusable typed filters for pagination, sorting, timestamp ranges, workflow
lineage, source identity, symbols, accounts, and common cross-domain query
metadata.

Application services may expose `PersistenceListResult[T]` and
`PersistenceReadResult[T]` siblings for result-envelope use cases while
preserving existing typed sequence-returning read/list APIs. Envelopes preserve
typed records internally and serialize only query metadata at the boundary.

## Lineage traversal

Lineage remains relational and PostgreSQL-backed. `LineagePersistenceService`
uses existing `persistence_lineage_links` records to trace upstream and
downstream paths such as:

```text
report -> recommendation -> signal -> workflow/runtime lineage
```

Traversal is bounded by typed request contracts with direction, depth, edge
limits, and relationship filters. It does not introduce graph-store or vector
abstractions.

## Validation and data quality

`ValidationPersistenceService` coordinates non-mutating validation checks over
typed persistence records. Current checks cover:

- generated, observed, published, and evaluated timestamp quality;
- score ranges for confidence, risk, sentiment, directional, attribution, and
  setup-quality scores;
- expected lineage presence and outside-workflow warnings;
- source identity and dedupe key availability.

Validation returns typed issue/result records. It should warn rather than fail
for records that are legitimately created outside workflow execution.

## Audit events

`AuditPersistenceService` persists append-only `PersistenceAuditEventRecord`
entries in `persistence_audit_events`. Audit records identify the entity,
action, actor/system source, timestamp, workflow/runtime lineage, and metadata.

Audit emission from application persistence services is optional and non-fatal by
default. Audit failures should not make a successful primary persistence write
fail unless a future stricter policy explicitly requires that behavior.

## Idempotency and deduplication

Domain repositories should remain duplicate-safe by deterministic identifiers,
natural keys, or upsert behavior where appropriate. Shared idempotency helpers
under `core.storage.persistence.idempotency` provide reusable key construction
for future domains.

Current guidance:

- recommendation parent/rationale/outcome/setup/watchlist writes use stable IDs
  and duplicate-safe upserts;
- latest portfolio rows upsert by account/symbol while history and snapshots
  remain append/insert oriented;
- market and macro fact records use source/symbol/timestamp-style keys;
- news articles dedupe by source plus external id or URL;
- sentiment snapshot IDs include source-aware context when available.

## Export boundary

`JsonPersistenceExportService` is the application boundary for JSON-compatible
exports of selected typed persistence records. It serializes dataclasses and
`as_dict()` records only at the explicit export boundary.

Exports are not internal contracts. They should not replace typed application
service inputs/outputs, and they should not write files unless a future explicit
export destination implementation is added.

Report-history export can combine a report bundle with linked recommendations,
agent signals, agent-intelligence records, attribution records, and lineage paths
when those services are supplied.

## Retention and lifecycle planning

Retention support is advisory in V3. `persistence_retention_policies` stores
policy metadata only, and `RetentionPersistenceService` produces dry-run plans
for candidate records.

Rules:

- Do not physically delete canonical PostgreSQL records in V3.
- Do not archive records automatically in V3.
- Treat archive markers as advisory/audit-ready metadata only.
- Any future destructive lifecycle action must go through policy, governance,
  approval, telemetry, and audit boundaries.

## Health and diagnostics

`HealthPersistenceService` reports non-mutating persistence health across:

- database connectivity;
- Alembic current/head revision state;
- SQLAlchemy `Base.metadata` model imports;
- required table availability;
- optional repository/service readiness probes.

`DiagnosticsPersistenceService` is a thin application boundary over health
checks. It currently provides service-level diagnostics only; CLI/API rendering
is a future boundary concern.

## CLI/report persistence

Morning report file output remains useful as a human artifact, but the curated
report record in PostgreSQL is the canonical persisted report when persistence
is enabled.

Example:

```bash
POLARIS_ENABLE_POSTGRES_REPORT_PERSISTENCE=1 polaris morning-report
```

The CLI persists:

- the full rendered Markdown report body;
- structured report sections and metadata;
- generated file artifact references.

Generated files are stored as report artifacts. They should not be treated as the
only system-of-record.

## Runtime persistence

When enabled via `WorkflowBootstrapConfig`, runtime persistence subscribes to the
canonical runtime `EventBus` and projects workflow run, node run, and runtime
event records into PostgreSQL. It does not introduce a parallel execution path
and should not bypass `WorkflowFacade` or `WorkflowBootstrap`.

Persisted runtime data supports replay, audit, CLI history, workflow status, and
progress history. Raw runtime dumps are not valid RAG source documents.

## Telemetry persistence

Telemetry persistence is operational observability storage. It is intentionally
separate from curated intelligence/reporting records.

Telemetry tables include:

- `telemetry_events`
- `telemetry_metrics`
- `telemetry_traces`
- `workflow_metrics`
- `agent_metrics`
- `provider_metrics`

Rules:

- Keep existing JSONL runtime telemetry intact until explicitly replaced.
- Use `TelemetryPersistenceService` only as an opt-in application layer over
  `TelemetryPersistenceRepository`.
- Treat telemetry and raw runtime events as operational audit/observability
  records, not curated RAG source documents.
- Do not ingest raw telemetry payloads directly into vector stores.

## RAG source records, eligibility, and vector stores

RAG/vector/graph stores are downstream projections derived from curated,
eligible PostgreSQL records.

Pre-RAG V3 canonical flow:

```text
curated PostgreSQL records
    -> metadata-only eligibility decision
    -> rag_source_eligibility
    -> optional curated document build when eligibility is required
    -> rag_documents / rag_chunks in PostgreSQL
    -> optional rag_embedding_jobs only when explicitly enabled
    -> future embedding worker
    -> Qdrant / Chroma / Neo4j derived indexes
```

Embedding job creation is opt-in during V3. The curated builder's default is to
avoid queuing embedding jobs unless explicitly requested.

Canonical RAG source categories are:

| RAG source category | PostgreSQL sources |
| --- | --- |
| Reports | `reports`, `report_sections` |
| Agent signals/intelligence | `agent_signals`, `agent_reasoning`, `agent_recommendations`, `agent_risk_assessments` |
| Recommendations | `recommendations`, `trade_setups`, `watchlist_items`, `recommendation_rationales`, `recommendation_outcomes` |
| Portfolio snapshots | `portfolio_state_history`, `portfolio_positions_history`, `portfolio_positions_latest`, `portfolio_exposure_snapshots`, `portfolio_risk_snapshots`, `portfolio_allocation_snapshots` |
| Technical snapshots | `technical_analysis_snapshots` plus supporting market context/indicator records when needed |
| Macro snapshots | `macro_regime_snapshots` plus supporting macro observations/calendar records when needed |
| News summaries | `news_analysis_snapshots` with article references from `news_articles` |
| Sentiment snapshots | `sentiment_snapshots` with supporting `sentiment_sources` |
| Attribution references | `attribution_records`, `signal_attribution`, `recommendation_attribution` |

Rules:

- Build RAG documents from persisted curated source records, not provider
  payloads, runtime dumps, CLI console output, JSONL telemetry, or vector-store
  state.
- Preserve full report text, LLM reasoning, recommendation rationale, and source
  attribution; do not truncate at the persistence boundary.
- Mark source eligibility in `rag_source_eligibility` before requiring gated
  curated RAG builds.
- Store document text, chunks, metadata, source table, source id, and source type
  in PostgreSQL before any future vector-store write.
- Treat `rag_documents`, `rag_chunks`, and explicitly queued
  `rag_embedding_jobs` as the durable source/queue layer for downstream
  embedding projection.
- Treat Qdrant, Chroma, and Neo4j as rebuildable projections, not canonical
  records.
- Keep vector-store writes out of PostgreSQL persistence services. Embedding
  workers should read curated RAG records and write derived indexes separately.
- Raw workflow events, node runs, telemetry events, telemetry metrics, and traces
  are excluded from canonical RAG sources unless a future curated summarization
  service transforms them into typed domain records first.

## Final pre-RAG readiness checklist

Full RAG ingestion, embedding workers, vector-store writes, graph-store writes,
retrieval APIs, or RAG orchestration workflows may begin only after every item
below is satisfied.

### Required PostgreSQL foundation

- [ ] Alembic is at head and includes all persistence revisions through
  `20260530_0019`.
- [ ] `Base.metadata` imports all persistence models, including
  `persistence_audit_events`, `rag_source_eligibility`, and
  `persistence_retention_policies`.
- [ ] Required V1, V2, and V3 PostgreSQL persistence tables exist in the target
  database.
- [ ] Application persistence services remain the canonical typed read/write
  boundaries.
- [ ] Repositories remain infrastructure concerns and are not queried directly
  by future RAG workflows.

### Canonical eligible source tables

- [ ] Curated reports: `reports`, `report_sections`, `report_versions`, and
  `report_artifacts`.
- [ ] Recommendations: `recommendations`, `recommendation_rationales`,
  `recommendation_outcomes`, `trade_setups`, and `watchlist_items`.
- [ ] Agent intelligence: `agent_signals`, `agent_reasoning`,
  `agent_recommendations`, and `agent_risk_assessments`.
- [ ] Attribution: `attribution_records`, `signal_attribution`, and
  `recommendation_attribution`.
- [ ] Portfolio snapshots: `portfolio_state_history`,
  `portfolio_positions_history`, `portfolio_positions_latest`,
  `portfolio_exposure_snapshots`, `portfolio_risk_snapshots`, and
  `portfolio_allocation_snapshots`.
- [ ] Market and technical summaries: `technical_analysis_snapshots`,
  `market_context_snapshots`, `market_breadth_snapshots`, and selected
  `market_indicators` only when summarized or curated.
- [ ] Macro summaries: `macro_regime_snapshots`, selected
  `macro_observations`, and selected `economic_calendar_events`.
- [ ] News summaries: `news_analysis_snapshots` with supporting
  `news_articles` references.
- [ ] Sentiment summaries: `sentiment_snapshots` with supporting
  `sentiment_sources`.

### Eligibility and quality rules

- [ ] `rag_source_eligibility` marks each source by `source_table`,
  `source_id`, and `source_type`.
- [ ] Eligibility records include reviewed timestamp, reason, quality score,
  and metadata.
- [ ] Default rules keep curated reports, meaningful reasoning,
  recommendations with rationale, and macro/technical/news/sentiment summaries
  eligible by default.
- [ ] Default rules keep raw runtime records, raw telemetry records, raw
  provider payload/fact rows, operational errors, empty sources, and unknown
  sources ineligible by default.
- [ ] Validation checks have run for timestamps, score ranges, lineage, source
  identity, and dedupe keys.
- [ ] Lineage links exist where source records were created from workflows or
  derived from other persisted records.
- [ ] Export and report-history paths preserve full report text, LLM reasoning,
  rationales, and attribution without truncation.

### Excluded data types

- [ ] Do not ingest `workflow_runs`, `workflow_node_runs`, `workflow_events`,
  or `workflow_state_snapshots` as raw RAG documents.
- [ ] Do not ingest `telemetry_events`, `telemetry_metrics`,
  `telemetry_traces`, `workflow_metrics`, `agent_metrics`, or
  `provider_metrics` as raw RAG documents.
- [ ] Do not ingest raw provider payloads, HTTP/SDK responses, raw CLI output,
  operational logs, cache files, JSONL telemetry, or generated debug artifacts
  directly.
- [ ] Do not treat Qdrant, Chroma, Neo4j, or any vector/graph index as
  canonical source data.

### Pre-ingestion gates and no-vector/no-graph constraints

- [ ] Health and diagnostics reports are healthy, or degraded items are
  documented with an explicit remediation owner.
- [ ] V3 migration coverage tests pass for audit, RAG eligibility, and
  retention policy tables.
- [ ] Application persistence, export, and API-readiness tests pass.
- [ ] `queue_embedding_jobs` remains explicitly opt-in until a dedicated
  embedding-worker plan is approved.
- [ ] `require_source_eligibility` is explicitly enabled for curated RAG builds
  that must be gated.
- [ ] Future RAG pipelines read through typed application services or curated
  RAG builders, not ad hoc SQL.
- [ ] Future vector/graph write paths are downstream projections with replay,
  telemetry, audit, and rebuild-readiness criteria defined before
  implementation.
- [ ] No V3 persistence service writes directly to Qdrant, Chroma, Neo4j, or any
  embedding/vector/graph runtime.

If any checklist item fails, finish the persistence or data-quality gap before
starting RAG ingestion, embedding execution, vector-store writes, or graph-store
writes.

## Validation commands

Run focused persistence tests:

```bash
uv run pytest -q tests/unit/core/database tests/unit/core/storage/persistence tests/unit/application/persistence
```

Run focused V3 migration coverage:

```bash
uv run pytest -q tests/unit/core/database/test_postgres_persistence_v3_migration_coverage.py
```

Run application persistence integration tests with fakes:

```bash
uv run pytest -q tests/integration/application/persistence
```

Run guarded PostgreSQL integration tests after setting `POLARIS_TEST_DATABASE_URL`:

```bash
uv run pytest -q tests/integration/core/storage/persistence
```

Run static checks for changed Python persistence code:

```bash
uv run ruff check core/database core/storage/persistence application/persistence tests/unit/core/database tests/unit/core/storage/persistence tests/unit/application/persistence tests/integration/application/persistence
uv run mypy --explicit-package-bases core/database core/storage/persistence application/persistence tests/unit/core/database tests/unit/core/storage/persistence tests/unit/application/persistence tests/integration/application/persistence
```

Run migration metadata checks:

```bash
uv run alembic heads
uv run alembic history
uv run python -c "import core.database.models; print('database models import ok')"
```
