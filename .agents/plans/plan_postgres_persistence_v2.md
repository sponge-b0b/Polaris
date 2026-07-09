# Platform Persistence Plan V2 (Pre-RAG Completion)

## Purpose

Before introducing full RAG ingestion and embedding pipelines, the platform should complete the persistence foundation required for:

- historical analysis
- attribution
- recommendation auditing
- workflow replay
- report generation
- future web UI
- future API
- future customer portal
- future research assistant
- future RAG ingestion

PostgreSQL remains the canonical system-of-record.

```text
Runtime
    -> PostgreSQL
        -> Analytics
        -> Reporting
        -> Attribution
        -> Recommendations
        -> RAG
```

Vector stores remain downstream projections.

---

# V2 Objectives

Complete persistence for:

```text
runtime history
agent intelligence
recommendation history
portfolio history
market history
macro history
news history
sentiment history
report history
workflow lineage
auditability
```

before embedding anything.

---

# Phase 6: Recommendation Persistence

## Why

The platform is fundamentally a recommendation platform.

Recommendations are one of the highest-value datasets.

Without recommendation persistence:

```text
no attribution
no outcome analysis
no recommendation auditing
no recommendation RAG
```

## Tables

```text
recommendations
recommendation_rationales
recommendation_outcomes
watchlist_items
trade_setups
```

## Persist

```text
recommendation_id
workflow_id
execution_id

symbol
bias
confidence
setup_quality

risk_score
risk_level

time_horizon

entry_context
stop_context
target_context

rationale
supporting_signals

human_action

outcome
created_at
```

---

# Phase 7: Portfolio Persistence Expansion

## Why

Current PortfolioState only captures account-level state.

Future attribution requires position-level history.

## Existing

```text
portfolio_state_history
portfolio_state_latest
```

Keep both.

## Add

```text
portfolio_positions_history
portfolio_positions_latest

portfolio_exposure_snapshots
portfolio_risk_snapshots

portfolio_allocation_snapshots
```

## Persist

```text
symbol
quantity
market_value
cost_basis
weight

sector
theme

exposure
beta
risk_weight

timestamp
```

---

# Phase 8: Market Persistence

## Why

Many future analyses depend on historical technical context.

## Tables

```text
market_ohlcv
market_indicators

market_context_snapshots
technical_analysis_snapshots

market_breadth_snapshots
```

## Persist

```text
OHLCV

EMA
RSI
MACD
ATR

VIX
VVIX

breadth metrics

trend score
volatility score
breadth score

technical regime
```

## Important

Persist final analysis outputs, not just raw indicators.

Store:

```text
inputs
outputs
scores
```

---

# Phase 9: Macro Persistence

## Tables

```text
macro_observations
macro_regime_snapshots
economic_calendar_events
```

## Persist

```text
inflation regime
liquidity regime
growth regime

yield curve

fed stance

economic regime classification

macro scores
```

## Why

Future:

```text
regime attribution
historical regime studies
macro RAG
```

---

# Phase 10: News Persistence

## Tables

```text
news_articles
news_analysis_snapshots
```

## Persist

```text
source
title
summary
url

published_at

symbols

themes

importance_score
sentiment_score

llm_summary
```

## Add

Deduplication:

```text
source + url
```

or:

```text
source + external_id
```

---

# Phase 11: Sentiment Persistence

## Tables

```text
sentiment_snapshots
sentiment_sources
```

## Persist

```text
fear_greed

news sentiment

market sentiment

composite sentiment

component scores

timestamp
```

---

# Phase 12: Agent Intelligence Persistence

## Existing

```text
agent_signals
```

## Expand

```text
agent_decisions
agent_reasoning
agent_risk_assessments
agent_recommendations
```

## Persist

```text
agent_name
agent_type

inputs
outputs

confidence

reasoning

recommendations

risks

execution lineage
```

## Why

This becomes:

```text
attribution source
RAG source
explainability source
```

---

# Phase 13: Attribution Persistence

## Why

Eventually the platform must answer:

```text
Why did we recommend this?

Was it correct?

Which agent contributed?

Which signal mattered?
```

## Tables

```text
attribution_records
signal_attribution
recommendation_attribution
```

## Persist

```text
signal contribution

agent contribution

strategy contribution

risk contribution

outcome contribution
```

---

# Phase 14: Workflow Audit Persistence

## Expand Runtime

Current:

```text
workflow_runs
workflow_node_runs
workflow_events
```

Add:

```text
workflow_state_snapshots
workflow_lineage
workflow_decisions
```

## Purpose

```text
replay
audit
explainability
debugging
```

---

# Phase 15: Report Persistence Expansion

## Existing

```text
reports
report_sections
report_artifacts
```

## Add

```text
report_versions
report_publications
```

## Why

Support:

```text
email delivery
portal delivery
customer history
report revisions
```

---

# Phase 16: Telemetry Persistence Expansion

## Existing

```text
telemetry_events
telemetry_metrics
telemetry_traces
```

## Add

```text
agent_metrics
provider_metrics
workflow_metrics
```

## Persist

```text
latency

token usage

provider failures

agent duration

workflow duration

confidence distributions
```

---

# Phase 17: Persistence Service Layer

Before RAG:

Build application-level persistence services.

## New Package

```text
application/persistence/
```

Structure:

```text
application/persistence/
├── runtime/
├── portfolio/
├── market/
├── macro/
├── news/
├── sentiment/
├── intelligence/
├── recommendations/
├── reports/
└── telemetry/
```

These services coordinate repositories.

Repositories remain infrastructure concerns.

---

# Phase 18: Unified Lineage System

Introduce canonical lineage.

## Every persisted record should support:

```text
workflow_id
execution_id
runtime_id

source_type
source_id

created_at
```

## Benefits

Allows:

```text
report
    -> recommendation
        -> signal
            -> workflow
                -> runtime event
```

tracing.

---

# Phase 19: Canonical Persistence Contracts

Before RAG:

Eliminate persistence ambiguity.

All persisted objects should use:

```text
Typed DTOs

Typed Records

Typed Serializers
```

Avoid:

```python
dict[str, Any]
```

at persistence boundaries.

---

# Phase 20: RAG Readiness Review

Only begin RAG after these exist:

## Required

```text
reports

agent_signals

recommendations

portfolio snapshots

technical snapshots

macro snapshots

news summaries

sentiment snapshots
```

## Required Metadata

```text
workflow lineage

timestamps

source references

attribution references
```

## Required Quality

```text
human-readable

curated

summarized

explainable
```

Never embed:

```text
raw runtime dumps
raw telemetry
raw event streams
raw provider payloads
```

---

# Final V2 Completion Criteria

Before RAG starts, the platform should have:

## Runtime

```text
workflow_runs
workflow_node_runs
workflow_events
workflow_state_snapshots
```

## Portfolio

```text
portfolio_state_history
portfolio_state_latest

portfolio_positions_history
portfolio_positions_latest

portfolio_exposure_snapshots
portfolio_risk_snapshots
```

## Market

```text
market_ohlcv
market_indicators
technical_analysis_snapshots
market_context_snapshots
market_breadth_snapshots
```

## Macro

```text
macro_observations
macro_regime_snapshots
economic_calendar_events
```

## News

```text
news_articles
news_analysis_snapshots
```

## Sentiment

```text
sentiment_snapshots
```

## Intelligence

```text
agent_signals
agent_reasoning
agent_recommendations
agent_risk_assessments
```

## Recommendations

```text
recommendations
recommendation_rationales
recommendation_outcomes
trade_setups
watchlist_items
```

## Reports

```text
reports
report_sections
report_artifacts
report_versions
```

## Telemetry

```text
telemetry_events
telemetry_metrics
telemetry_traces
workflow_metrics
agent_metrics
provider_metrics
```

## Attribution

```text
attribution_records
signal_attribution
recommendation_attribution
```

Once these persistence foundations are complete, the platform will have sufficient historical intelligence to support a high-quality RAG layer without embedding low-value operational data.

---

# Codex Recommended Plan V2

## Summary

Continue from Persistence V1 by completing PostgreSQL system-of-record coverage for business-domain history before any full RAG ingestion or embedding pipeline work. V2 should build **typed persistence foundations plus thin application persistence services** for each domain, then leave workflow/service auto-wiring for explicit later steps unless a slice already has a safe integration point.

PostgreSQL remains canonical. Vector stores remain rebuildable downstream projections.

Execution protocol:

- Implement one step at a time.
- After each step, update this plan file with `- [x]` and a short step result.
- Run the targeted tests/checks for that step.
- Stop and prompt before the next step.

## Key Architecture Decisions

- Use canonical lineage fields consistently:
  - `workflow_name`
  - `execution_id`
  - `runtime_id`
  - `node_name` when relevant
  - `source_type`
  - `source_id`
  - `created_at`
  - `updated_at`
- Prefer `workflow_name` over a new `workflow_id` because V1 runtime persistence already uses `workflow_name`.
- Use typed persistence records internally; serialize to `JSONB` only at the persistence boundary.
- Do not persist raw provider payloads as primary records.
- Do not embed raw runtime events, telemetry streams, or provider dumps.
- Do not add vector-store writes in V2.
- Build repository foundations and application persistence services before broad workflow wiring.
- Include telemetry persistence late in V2 after business-domain records are stable.
- Omit `agent_decisions` from V2 unless a canonical agent decision object already exists; persist agent reasoning, recommendations, and risk assessments instead.

## Public Interfaces / Types to Add

For each new persistence domain, add the same V1-style pattern:

```text
Typed Record dataclasses
PersistenceResult dataclass
Repository Protocol
Serializer
Postgres repository
SQLAlchemy models
Alembic migration
Application persistence service
Focused tests
```

Recommended package shape:

```text
core/storage/persistence/
├── recommendations/
├── portfolio/
├── market/
├── macro/
├── news/
├── sentiment/
├── intelligence/
├── attribution/
├── telemetry/
└── lineage/
```

Application-level coordination services:

```text
application/persistence/
├── recommendations/
├── portfolio/
├── market/
├── macro/
├── news/
├── sentiment/
├── intelligence/
├── attribution/
├── reports/
└── telemetry/
```

## Implementation Steps

### Plan Setup

- [x] Step 1 — Append Codex recommended V2 plan
  - Add this recommended plan under a separate section in `.agent/plans/plan_postgres_persistence_v2.md`.
  - Preserve the original V2 plan.
  - Add a `Step Results` section if missing.
  - Step 1 completed: appended the Codex recommended V2 plan as a separate section and preserved the original plan content.

- [x] Step 2 — Add shared persistence lineage contracts
  - Add typed lineage/source reference records and validation helpers.
  - Standardize `workflow_name`, `execution_id`, `runtime_id`, `node_name`, `source_type`, `source_id`.
  - Keep these as reusable persistence-boundary helpers, not runtime-core replacements.
  - Step 2 completed: added shared lineage, source reference, record identity, record context, and validation helpers under `core/storage/persistence/lineage`; added focused contract tests and validation coverage.

- [x] Step 3 — Add generic lineage link foundation
  - Add `persistence_lineage_links` for cross-record relationships.
  - Support relationships like report → recommendation, recommendation → signal, signal → workflow.
  - Add model, migration, repository, serializer, and tests.
  - Step 3 completed: added generic lineage-link typed records/results, SQLAlchemy model, Alembic migration, serializer, async Postgres repository, exports, and focused model/migration/serializer/repository tests.

### Recommendation Persistence

- [x] Step 4 — Add recommendation persistence contracts
  - Add typed records for recommendations, rationales, outcomes, trade setups, and watchlist items.
  - Include symbol, bias, confidence, setup quality, risk score, time horizon, rationale, supporting signals, human action, and outcome fields.
  - Step 4 completed: added recommendation persistence typed records, bundle/result contracts, stable id helpers, exports, and focused validation tests while preserving full rationale text without truncation.

- [x] Step 5 — Add recommendation SQLAlchemy models and migration
  - Add `recommendations`, `recommendation_rationales`, `recommendation_outcomes`, `trade_setups`, `watchlist_items`.
  - Use JSONB for serialized supporting signals/context.
  - Add indexes for symbol, execution lineage, status/bias, and timestamps.
  - Step 5 completed: added recommendation SQLAlchemy models, the chained Alembic migration `20260530_0006`, metadata imports, and focused model/migration tests for recommendation, rationale, outcome, trade setup, and watchlist persistence tables.

- [x] Step 6 — Add recommendation serializer and repository
  - Add async Postgres upsert/list/read methods.
  - Keep rationales/outcomes append-friendly where history matters.
  - Add unit tests for serializer round trips and repository statements/fakes.
  - Step 6 completed: added the recommendation repository protocol, serializer, async Postgres repository, exports, and focused serializer/repository tests with idempotent parent/child upserts and append-friendly rationale/outcome history.

- [x] Step 7 — Add recommendation application persistence service
  - Add `application/persistence/recommendations`.
  - Coordinate recommendation bundle persistence through repository protocol.
  - Do not wire automatic workflow capture yet.
  - Step 7 completed: added the typed recommendation application persistence service and filters, coordinated bundle persistence/rehydration through the repository protocol, and kept workflow capture explicit rather than automatic.

### Portfolio Persistence Expansion

- [x] Step 8 — Add portfolio expansion contracts
  - Add typed records for position history/latest, exposure snapshots, risk snapshots, and allocation snapshots.
  - Align with existing `PortfolioState` and V1 portfolio state persistence.
  - Step 8 completed: added `core/storage/persistence/portfolio` typed portfolio expansion contracts for position history/latest, exposure snapshots, risk snapshots, allocation snapshots, atomic bundles, typed results, and stable id helpers; V1 `PortfolioState` persistence remains unchanged.

- [x] Step 9 — Add portfolio expansion models and migration
  - Add `portfolio_positions_history`, `portfolio_positions_latest`, `portfolio_exposure_snapshots`, `portfolio_risk_snapshots`, `portfolio_allocation_snapshots`.
  - Include account, symbol, timestamp, quantity, market value, cost basis, weight, sector/theme, beta, and risk fields.
  - Step 9 completed: added portfolio expansion SQLAlchemy models, metadata imports, Alembic migration `20260530_0007_add_portfolio_expansion_persistence_tables.py`, account/symbol/timestamp/workflow indexes, latest-position account/symbol uniqueness, and optional V1 portfolio-state snapshot relationships.

- [x] Step 10 — Add portfolio expansion serializer and repository
  - Add upsert behavior for latest tables.
  - Add append-only behavior for history/snapshot tables.
  - Add focused unit tests.
  - Step 10 completed: added portfolio expansion serializer, async repository protocol, and Postgres repository with insert-only history/snapshot persistence plus account/symbol latest-position upsert behavior.

- [x] Step 11 — Add portfolio persistence service
  - Add service methods for persisting portfolio expansion bundles.
  - Keep the existing portfolio state repository intact.
  - Step 11 completed: added the typed portfolio application persistence service and filters, coordinated explicit portfolio expansion bundle/record persistence through the expansion repository protocol, and preserved V1 PortfolioState snapshot operations through the existing state repository without changing that repository contract.

### Market / Technical Persistence

- [x] Step 12 — Add market persistence contracts
  - Add typed records for OHLCV, indicators, market context snapshots, technical analysis snapshots, and breadth snapshots.
  - Persist final analysis inputs, outputs, scores, and regimes.
  - Step 12 completed: added typed market persistence contracts for OHLCV, indicators, market context snapshots, technical analysis snapshots, and breadth snapshots, including final analysis input/output JSON boundary fields, score/regime validation, bundle/result records, stable id helpers, exports, and focused contract tests.

- [x] Step 13 — Add market models and migration
  - Add `market_ohlcv`, `market_indicators`, `market_context_snapshots`, `technical_analysis_snapshots`, `market_breadth_snapshots`.
  - Add indexes for symbol, timestamp, source, and workflow lineage.
  - Step 13 completed: added market SQLAlchemy models, metadata imports, chained Alembic migration `20260530_0008_add_market_persistence_tables.py`, JSONB boundary columns for final inputs/outputs, natural-key uniqueness for OHLCV/indicator fact upserts, and symbol/timestamp/source/regime/workflow lineage indexes.

- [x] Step 14 — Add market serializer and repository
  - Add idempotent upserts for symbol/timestamp/source records.
  - Add append-only technical/context snapshots.
  - Add tests.
  - Step 14 completed: added the market persistence serializer, async repository protocol, and Postgres repository with idempotent OHLCV/indicator fact upserts plus append-only market context, technical analysis, and breadth snapshots.

- [x] Step 15 — Add market persistence service
  - Add application service for persisting curated market/technical outputs.
  - Do not persist raw provider payloads as canonical records.
  - Step 15 completed: added the typed market application persistence service and filters, coordinating explicit curated market/technical bundle and record persistence through the market repository protocol without accepting raw provider payloads as canonical records.

### Macro Persistence

- [x] Step 16 — Add macro persistence contracts
  - Add typed records for macro observations, regime snapshots, and economic calendar events.
  - Include inflation, liquidity, growth, Fed stance, yield curve, macro scores, and regime classification.
  - Step 16 completed: added typed macro persistence contracts for observations, regime snapshots, and economic calendar events, including inflation/liquidity/growth/fed/yield-curve regime fields, macro scores, bundle/result records, stable id helpers, exports, and focused contract tests.

- [x] Step 17 — Add macro models and migration
  - Add `macro_observations`, `macro_regime_snapshots`, `economic_calendar_events`.
  - Add indexes for indicator/event name, observation timestamp, regime timestamp, and lineage.
  - Step 17 completed: added macro SQLAlchemy models, metadata imports, chained Alembic migration `20260530_0009_add_macro_persistence_tables.py`, JSONB boundary columns for macro inputs/outputs/metadata, natural-key uniqueness for observation/calendar fact upserts, and indicator/event/regime/timestamp/workflow lineage indexes.

- [x] Step 18 — Add macro serializer and repository
  - Add upsert behavior for observations and calendar events.
  - Add append-only behavior for regime snapshots.
  - Add tests.
  - Step 18 completed: added the macro persistence serializer, async repository protocol, and Postgres repository with idempotent macro observation/calendar event fact upserts plus append-only macro regime snapshots.

- [x] Step 19 — Add macro persistence service
  - Add application service for persisting curated macro outputs.
  - Step 19 completed: added the typed macro application persistence service and filters, coordinating explicit curated macro bundle and record persistence through the macro repository protocol without accepting raw provider payloads as canonical records.

### News Persistence

- [x] Step 20 — Add news persistence contracts
  - Add typed records for articles and news analysis snapshots.
  - Include source, external id, title, summary, URL, published timestamp, symbols, themes, importance score, sentiment score, and LLM summary.
  - Step 20 completed: added typed news persistence contracts for curated articles and append-only analysis snapshots, including source/external-id/URL identity, symbols, themes, importance and sentiment scores, full untruncated LLM response preservation, bundle/result records, stable id helpers, exports, and focused contract tests.

- [x] Step 21 — Add news models and migration
  - Add `news_articles` and `news_analysis_snapshots`.
  - Add dedupe support using `source + url` and/or `source + external_id`.
  - Add indexes for source, published timestamp, symbols, and lineage.
  - Step 21 completed: added news SQLAlchemy models, metadata imports, chained Alembic migration `20260530_0010_add_news_persistence_tables.py`, JSONB boundary columns for symbols/themes/article ids/inputs/outputs/metadata, Text columns for full article/LLM output preservation, source identity checks, source+external-id/source+URL dedupe constraints, and source/published/symbol/theme/workflow lineage indexes.

- [x] Step 22 — Add news serializer and repository
  - Add idempotent article upserts.
  - Add append-only analysis snapshots.
  - Add tests.
  - Step 22 completed: added `NewsPersistenceSerializer`, `NewsPersistenceRepository`, and `PostgresNewsPersistenceRepository`; article facts are idempotently upserted by source identity key (`source + external_id` when available, otherwise `source + url`), while news analysis snapshots remain append-only records preserving full untruncated LLM responses, curated inputs/outputs, metadata, and lineage.

- [x] Step 23 — Add news persistence service
  - Add application service for curated news persistence.
  - Step 23 completed: added `application/persistence/news` with typed article and analysis snapshot filters plus `NewsPersistenceService` for explicit curated news bundle/record persistence and retrieval through the news repository protocol only, preserving full LLM response records without accepting raw provider payloads as canonical persistence inputs.

### Sentiment Persistence

- [x] Step 24 — Add sentiment persistence contracts
  - Add typed records for sentiment snapshots and sentiment sources.
  - Include fear/greed, news sentiment, market sentiment, composite sentiment, component scores, and timestamp.
  - Step 24 completed: added `core/storage/persistence/sentiment` typed contracts for append-only sentiment snapshots and source contribution records, including fear/greed, news/market/social/composite sentiment scores, confidence, component scores, symbol/universe scope, source references, lineage, bundle/result records, stable id helpers, exports, and focused contract tests.

- [x] Step 25 — Add sentiment models and migration
  - Add `sentiment_snapshots` and `sentiment_sources`.
  - Add indexes for timestamp, source, symbol/universe where applicable, and lineage.
  - Step 25 completed: added sentiment SQLAlchemy models, metadata imports, and chained Alembic migration `20260530_0011_add_sentiment_persistence_tables.py`, including JSONB boundary columns for component scores/inputs/outputs/metadata, append-only sentiment snapshot/source table design, source/symbol/universe/timestamp/workflow lineage indexes, and row timestamps.

- [x] Step 26 — Add sentiment serializer and repository
  - Add append-only snapshots and source records.
  - Add tests.
  - Step 26 completed: added `SentimentPersistenceSerializer`, `SentimentPersistenceRepository`, and `PostgresSentimentPersistenceRepository`; sentiment snapshots and source contribution records are append-only inserts preserving curated component scores, inputs/outputs, source references, metadata, and lineage, with typed filtered retrieval for snapshots and sources.

- [x] Step 27 — Add sentiment persistence service
  - Add application service for curated sentiment persistence.
  - Step 27 completed: added `application/persistence/sentiment` with typed snapshot/source filters plus `SentimentPersistenceService` for explicit curated sentiment bundle/record persistence and filtered retrieval through the sentiment repository protocol only, without accepting raw provider payloads as canonical persistence inputs.

### Agent Intelligence Expansion

- [x] Step 28 — Add agent intelligence expansion contracts
  - Add typed records for `agent_reasoning`, `agent_recommendations`, and `agent_risk_assessments`.
  - Link records to existing `agent_signals`.
  - Preserve full reasoning and LLM text without truncation.
  - Step 28 completed: added `core/storage/persistence/agent_intelligence` typed contracts for agent reasoning, agent recommendations, and agent risk assessments, all linked to existing `agent_signals` through `agent_signal_id`, with full untruncated reasoning/rationale/assessment/LLM text preservation, bundle/result records, stable id helpers, exports, and focused contract tests.

- [x] Step 29 — Add agent intelligence models and migration
  - Add `agent_reasoning`, `agent_recommendations`, `agent_risk_assessments`.
  - Index by agent name/type, signal id, execution lineage, timestamp, and symbol/universe.
  - Step 29 completed: added SQLAlchemy models and chained Alembic migration for `agent_reasoning`, `agent_recommendations`, and `agent_risk_assessments`, linked to `agent_signals` via cascading foreign keys, using Text columns for full untruncated reasoning/rationale/assessment/LLM content, JSONB persistence-boundary payload columns, lineage fields, row timestamps, and query indexes for signal id, agent name/type, execution lineage, timestamp, symbol, and universe.

- [x] Step 30 — Add agent intelligence serializer and repository
  - Add upsert/read/list methods.
  - Keep `agent_signals` as the primary signal table.
  - Add tests.
  - Step 30 completed: added `AgentIntelligencePersistenceSerializer`, `AgentIntelligencePersistenceRepository`, and `PostgresAgentIntelligencePersistenceRepository` with idempotent upsert, read, and filtered list methods for reasoning, recommendations, and risk assessments while preserving `agent_signals` as the primary signal table; full untruncated reasoning/rationale/assessment/LLM text and supporting persisted identities round-trip through persistence-boundary serializers.

- [x] Step 31 — Add agent intelligence persistence service
  - Add application service that persists enriched intelligence bundles.
  - Step 31 completed: added `application/persistence/agent_intelligence` with typed filters and `AgentIntelligencePersistenceService` for enriched agent reasoning, recommendation, and risk-assessment bundle/record persistence plus filtered retrieval through the agent-intelligence repository protocol only; `agent_signals` remains the primary signal table and enriched records are persisted explicitly through typed application-service methods.

### Attribution Persistence

- [x] Step 32 — Add attribution persistence contracts
  - Add typed records for attribution records, signal attribution, and recommendation attribution.
  - Include contribution type, contribution score, confidence, explanation, and linked source records.
  - Step 32 completed: added `core/storage/persistence/attribution` typed contracts for generic attribution records, signal attributions, and recommendation attributions, including signed contribution scores, confidence, full untruncated explanations, lineage, agent/scope metadata, linked persisted source records, bundle/result records, stable id helpers, exports, and focused contract tests.

- [x] Step 33 — Add attribution models and migration
  - Add `attribution_records`, `signal_attribution`, `recommendation_attribution`.
  - Index by recommendation id, signal id, agent name, execution lineage, and timestamp.
  - Step 33 completed: added attribution SQLAlchemy models and chained Alembic migration for `attribution_records`, `signal_attribution`, and `recommendation_attribution`, including full untruncated explanation `Text` columns, JSONB persistence-boundary source-record/metadata columns, contribution/confidence checks, lineage and row timestamps, recommendation/signal foreign keys, and query indexes for recommendation id, signal id, agent name/type, execution lineage, timestamp, symbol, and universe.

- [x] Step 34 — Add attribution serializer and repository
  - Add append-friendly attribution persistence.
  - Add tests.
  - Step 34 completed: added `AttributionPersistenceSerializer`, `AttributionPersistenceRepository`, and `PostgresAttributionPersistenceRepository` with stable-id upsert persistence for generic attribution, signal attribution, and recommendation attribution records; persistence remains append-friendly because rows are upserted by their own attribution ids without deleting sibling attribution rows for the same target, signal, or recommendation, while full explanations, linked source record identities, metadata, and lineage round-trip through typed serializers.

- [x] Step 35 — Add attribution persistence service
  - Add application service for storing attribution bundles.
  - Step 35 completed: added `application/persistence/attribution` with typed filters and `AttributionPersistenceService` for explicit generic attribution, signal attribution, and recommendation attribution bundle/record persistence plus get/list retrieval through the attribution repository protocol only; the service accepts curated typed attribution records, preserves full explanations/source-record lineage through lower persistence layers, and does not auto-capture raw runtime or provider payloads.

### Workflow Audit Expansion

- [x] Step 36 — Add workflow state snapshot contracts
  - Add typed record for workflow state snapshots.
  - Include workflow status, serialized state payload, checkpoint reference, wave index, and lineage.
  - Step 36 completed: extended runtime persistence contracts with `WorkflowStateSnapshotRecord` plus stable/random snapshot id helpers for persisted workflow audit snapshots; snapshots carry workflow status, timestamp, runtime id, optional checkpoint reference, wave index, serialized state payload, lineage, and metadata without changing runtime execution semantics.

- [x] Step 37 — Add workflow state snapshot model and migration
  - Add `workflow_state_snapshots`.
  - Index by workflow name, execution id, runtime id, timestamp, and wave index.
  - Step 37 completed: added `WorkflowStateSnapshotModel` and migration `20260530_0014_add_workflow_state_snapshot_persistence_table.py` for append-friendly workflow audit snapshots with workflow/execution/status/timestamp/runtime/node/wave/checkpoint fields, JSONB state/metadata boundary columns, row timestamps, non-negative wave-index constraint, and indexes for workflow, execution, runtime, timestamp, and wave-based retrieval.

- [x] Step 38 — Add workflow state snapshot repository/service
  - Add repository and application service.
  - Do not change runtime execution semantics.
  - Add tests.
  - Step 38 completed: added runtime persistence serializer/repository support and `application/persistence/workflow_audit` service for explicit workflow state snapshot persistence/retrieval; snapshots are persisted by stable snapshot id without mutating runtime execution semantics.

### Report Persistence Expansion

- [x] Step 39 — Add report version/publication contracts
  - Add typed records for report versions and report publications.
  - Link versions/publications to existing `reports`.
  - Step 39 completed: added typed `ReportVersionRecord` and `ReportPublicationRecord` contracts linked by `report_id` to existing reports, stable id helpers for versions/publications, and expanded `ReportPersistenceBundle` to carry versions/publications without changing existing report repository behavior.

- [x] Step 40 — Add report version/publication models and migration
  - Add `report_versions` and `report_publications`.
  - Include report id, version number, publication target, publication status, timestamps, and metadata.
  - Step 40 completed: added `ReportVersionModel` and `ReportPublicationModel` plus migration `20260530_0015_add_report_version_publication_tables.py`; versions link to existing reports with positive version numbers and per-report uniqueness while preserving full markdown, structured payload, metadata, lineage timestamps, and query indexes; publications link to reports plus optional versions with target/status/requested/published timestamps, artifact/error fields, metadata, published-after-requested validation, and query indexes.

- [x] Step 41 — Add report version/publication repository/service
  - Extend report persistence without breaking existing report records.
  - Add tests.
  - Step 41 completed: extended report persistence serializers, repository protocol, and `PostgresReportPersistenceRepository` to persist and retrieve report bundles containing sections, artifacts, versions, and publications while preserving the existing `persist_report`/`get_report` behavior; added `application/persistence/reports` with typed report artifact/publication filters and `ReportPersistenceService` for explicit curated report persistence and retrieval through the repository protocol only.

### Telemetry Persistence

- [x] Step 42 — Add telemetry persistence contracts
  - Add typed records for telemetry events, metrics, traces, workflow metrics, agent metrics, and provider metrics.
  - Keep telemetry as operational observability data, not RAG source data.
  - Step 42 completed: added `core/storage/persistence/telemetry` typed operational persistence contracts for telemetry events, generic metrics, traces/spans, workflow metrics, agent metrics, and provider metrics, including lineage/correlation fields, JSON boundary payload/metadata fields, validation rules, bundle/result records, stable id helpers, and exports; telemetry is explicitly documented as operational observability/audit data and not curated RAG source data.

- [x] Step 43 — Add telemetry models and migration
  - Add `telemetry_events`, `telemetry_metrics`, `telemetry_traces`, `workflow_metrics`, `agent_metrics`, `provider_metrics`.
  - Index by timestamp, event type, source, workflow lineage, agent/provider, and correlation id.
  - Step 43 completed: added SQLAlchemy models and chained migration `20260530_0016_add_telemetry_persistence_tables.py` for telemetry events, generic metrics, traces, workflow metrics, agent metrics, and provider metrics, including JSONB boundary fields, row timestamps, lineage/correlation columns, metric/trace validation checks, and indexes for timestamp, event type, source, workflow lineage, agent/provider identity, endpoint, symbol, status, trace/span, and correlation id.

- [x] Step 44 — Add telemetry serializer and repository
  - Add append-only event/trace persistence.
  - Add metric upsert or append behavior based on metric identity and timestamp.
  - Add tests.
  - Step 44 completed: added `TelemetryPersistenceSerializer`, `TelemetryPersistenceRepository`, and `PostgresTelemetryPersistenceRepository`; events and traces persist with append-friendly conflict-do-nothing semantics, metric families persist with stable-id upserts so callers can append by timestamped IDs or update by reused identities, typed get/list APIs preserve lineage/correlation filters, and focused serializer/repository tests verify round trips, PostgreSQL conflict semantics, rollback behavior, and filtered retrieval.

- [x] Step 45 — Add telemetry persistence service
  - Add application service for telemetry persistence.
  - Do not replace existing JSONL telemetry yet.
  - Add tests.
  - Step 45 completed: added `application/persistence/telemetry` with `TelemetryPersistenceService` and typed filter contracts for telemetry events, generic metrics, traces, workflow metrics, agent metrics, and provider metrics; the service remains an explicit opt-in application persistence layer and does not replace or auto-wire existing JSONL telemetry, delegates persistence/retrieval only through `TelemetryPersistenceRepository`, normalizes optional identifiers and symbols, validates ordered time windows, wires package/root exports, and validation passed with focused telemetry application pytest, full application persistence pytest, ruff, scoped mypy, and graphify update.

### Persistence Service Layer Review

- [x] Step 46 — Normalize application persistence package exports
  - Ensure `application/persistence/` exposes domain services consistently.
  - Ensure repositories remain infrastructure concerns.
  - Avoid service locator patterns.
  - Step 46 completed: normalized `application/persistence/__init__.py` as a service/filter-only application boundary with sorted exports across all persistence domains, documented that repositories remain infrastructure concerns under `core.storage.persistence`, avoided service-locator registries or dynamic lookup helpers, and added export contract tests that verify root exports match domain package exports, remain sorted/bound, and exclude repository contracts.

- [x] Step 47 — Add persistence service integration tests with fakes
  - Test each application persistence service against repository protocols/fakes.
  - Confirm service methods return typed results.
  - Step 47 completed: added a cross-domain application persistence integration test that instantiates every persistence service with repository protocol fakes, exercises representative persist paths for agent intelligence, attribution, macro, market, news, portfolio, recommendations, reports, sentiment, telemetry, and workflow audit, verifies typed result success/counts, and confirms services remain dependency-injected without service locators or repository exports from the application boundary.

### RAG Readiness Review

- [x] Step 48 — Add RAG readiness checklist/test
  - Add a lightweight validation test or documented checklist proving V2 canonical sources exist:
    - reports
    - agent signals/intelligence
    - recommendations
    - portfolio snapshots
    - technical snapshots
    - macro snapshots
    - news summaries
    - sentiment snapshots
    - attribution references
  - Confirm vector-store writes remain out of scope.
  - Step 48 completed: added `test_rag_readiness.py` as an executable RAG readiness checklist that verifies all V2 canonical source categories have PostgreSQL-backed tables and typed application services, constructs `RagDocumentRecord` references from curated source tables before projection, explicitly excludes raw workflow/telemetry operational tables as RAG canonical sources, and asserts the RAG repository scope is limited to document/chunk/embedding-job persistence without vector-store write APIs.

- [x] Step 49 — Update PostgreSQL docs
  - Extend `docs/postgres_persistence.md` with V2 tables, services, migration commands, and RAG readiness rules.
  - Document that telemetry/raw events are not RAG sources.
  - Step 49 completed: expanded `docs/postgres_persistence.md` with the full V2 migration inventory, domain table/service matrix, telemetry persistence rules, RAG source categories, migration/validation commands, and explicit guidance that raw workflow events, node runs, telemetry events, metrics, and traces are operational observability records rather than canonical RAG sources; vector-store writes remain downstream projection work outside PostgreSQL persistence services.

- [x] Step 50 — Final V2 validation
  - Run targeted pytest suites.
  - Run ruff.
  - Run scoped mypy with explicit package bases if needed.
  - Run Alembic heads/history and metadata import checks.
  - Run `graphify update .` after code changes.
  - Stop for review before commit/push.
  - Step 50 completed: ran final V2 validation across targeted core database, core storage persistence, application persistence, and application persistence integration suites; fixed the runtime persistence event subscriber fake to satisfy the expanded runtime repository workflow-state snapshot contract for scoped mypy; pytest, ruff, scoped mypy, Alembic heads/history, database model import, and graphify update all passed. V2 is ready for review before commit/push.

## Test Plan

Run focused checks after each slice:

```bash
uv run pytest -q tests/unit/core/database tests/unit/core/storage/persistence
uv run pytest -q tests/unit/application/persistence
uv run ruff check core/database core/storage/persistence application/persistence tests/unit/core/database tests/unit/core/storage/persistence tests/unit/application/persistence
uv run mypy --explicit-package-bases core/database core/storage/persistence application/persistence tests/unit/core/database tests/unit/core/storage/persistence tests/unit/application/persistence
```

Migration checks:

```bash
uv run alembic heads
uv run alembic history
uv run python -c "import core.database.models; from core.database.base import Base; print(sorted(Base.metadata.tables))"
```

Guarded integration checks, when `POLARIS_TEST_DATABASE_URL` is set:

```bash
uv run pytest -q tests/integration/core/storage/persistence
```

## Assumptions and Defaults

- User-selected implementation depth: typed foundations plus thin application persistence services per domain.
- User-selected telemetry scope: include telemetry late in V2.
- No full RAG ingestion, embedding worker, or vector-store writes in V2.
- Existing V1 tables remain stable and are extended, not rewritten.
- Compatibility shims should be avoided; edge/application persistence code should conform directly to the current architecture.
- `workflow_name` is the canonical workflow identifier for V2 persistence because it matches V1 runtime persistence.
- JSONB is acceptable at the PostgreSQL boundary; internal services should prefer typed records.
- Raw provider payloads, raw telemetry, and raw runtime dumps are excluded from curated RAG source creation.

## Step Results
- [x] Step 1 completed: appended Codex recommended V2 plan as a separate section and preserved the original V2 plan content.
- [x] Step 2 completed: added shared lineage/source/record identity persistence contracts and validation helpers under `core/storage/persistence/lineage`, with exports and focused contract tests; validation passed with pytest, ruff, scoped mypy, and graphify update.
- [x] Step 3 completed: added the `persistence_lineage_links` foundation for generic cross-record audit relationships, including typed records/results, model, migration, serializer, Postgres repository, exports, and focused tests; validation passed with pytest, ruff, scoped mypy, Alembic heads/history, metadata import, and graphify update.
- [x] Step 4 completed: added recommendation persistence contracts for recommendations, rationales, outcomes, trade setups, and watchlist items, including bundle/result models, stable id helpers, and focused contract tests; validation passed with pytest, ruff, scoped mypy, and graphify update.
- [x] Step 5 completed: added recommendation persistence SQLAlchemy models and Alembic migration for `recommendations`, `recommendation_rationales`, `recommendation_outcomes`, `trade_setups`, and `watchlist_items`; JSONB remains limited to persistence-boundary context/signal/metadata fields; validation passed with targeted database pytest, full `tests/unit/core/database`, ruff, scoped mypy, Alembic heads/history/metadata import, and graphify update.
- [x] Step 6 completed: added recommendation persistence serialization and async Postgres repository support for upserting recommendation bundles and listing/reading recommendations, rationales, outcomes, trade setups, and watchlist items; rationales/outcomes remain append-friendly because child rows are upserted by stable IDs without deleting siblings; validation passed with targeted pytest, full `tests/unit/core/storage/persistence`, ruff, scoped mypy, and graphify update.
- [x] Step 7 completed: added `application/persistence/recommendations` with typed filters and `RecommendationPersistenceService` for explicit bundle persistence, recommendation retrieval, full bundle rehydration, setup listing, and watchlist listing through the repository protocol only; validation passed with targeted application/core persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 8 completed: added typed portfolio expansion contracts and exports for position history/latest, exposure snapshots, risk snapshots, allocation snapshots, bundle/result records, and deterministic lineage-aware id helpers; validation passed with focused portfolio contract pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 9 completed: added portfolio expansion SQLAlchemy models and migration for `portfolio_positions_history`, `portfolio_positions_latest`, `portfolio_exposure_snapshots`, `portfolio_risk_snapshots`, and `portfolio_allocation_snapshots`; validation passed with targeted and full core database pytest, ruff, scoped mypy, Alembic heads/history, metadata import, and graphify update.
- [x] Step 10 completed: added `PortfolioPersistenceSerializer`, `PortfolioExpansionPersistenceRepository`, and `PostgresPortfolioExpansionPersistenceRepository`; latest positions upsert by account/symbol while position history and exposure/risk/allocation snapshots remain insert-only append records; validation passed with focused serializer/repository pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 11 completed: added `application/persistence/portfolio` with typed filters and `PortfolioPersistenceService` for explicit portfolio expansion bundle/record persistence, position/exposure/risk/allocation retrieval through the repository protocol, and optional V1 PortfolioState snapshot persistence via the existing state repository contract; validation passed with targeted and full application persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 12 completed: added `core/storage/persistence/market` typed market persistence contracts for OHLCV, indicators, market context snapshots, technical analysis snapshots, breadth snapshots, bundle/result records, and stable id helpers; final analysis inputs/outputs are preserved as JSON boundary fields while internal contracts remain typed; validation passed with focused and adjacent contract pytest, ruff, scoped mypy, and graphify update.
- [x] Step 13 completed: added market persistence SQLAlchemy models and Alembic migration for `market_ohlcv`, `market_indicators`, `market_context_snapshots`, `technical_analysis_snapshots`, and `market_breadth_snapshots`; validation passed with targeted and full core database pytest, ruff, scoped mypy, Alembic heads/history, metadata import, and graphify update.
- [x] Step 14 completed: added `MarketPersistenceSerializer`, `MarketPersistenceRepository`, and `PostgresMarketPersistenceRepository`; OHLCV and indicator facts are upserted by natural symbol/timestamp/source keys while market context, technical analysis, and breadth snapshots remain append-only curated records; validation passed with focused and full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 15 completed: added `application/persistence/market` with typed filters and `MarketPersistenceService` for explicit OHLCV, indicator, market context, technical analysis, and breadth persistence/retrieval through the repository protocol only; validation passed with targeted and full application persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 16 completed: added `core/storage/persistence/macro` typed macro persistence contracts for observations, regime snapshots, and economic calendar events, including inflation/liquidity/growth/fed/yield-curve regime fields, macro scores, bundle/result records, stable id helpers, exports, and focused contract tests; validation passed with focused and adjacent contract pytest, ruff, scoped mypy, and graphify update.
- [x] Step 17 completed: added macro SQLAlchemy models and chained migration for `macro_observations`, `macro_regime_snapshots`, and `economic_calendar_events`, including JSONB persistence-boundary columns, lineage fields, row timestamps, natural-key uniqueness for macro observations and calendar events, macro regime append-only table design, and indicator/event/regime/timestamp/workflow indexes; validation passed with focused and adjacent database pytest, ruff, scoped mypy, and graphify update.
- [x] Step 18 completed: added `MacroPersistenceSerializer`, `MacroPersistenceRepository`, and `PostgresMacroPersistenceRepository`; macro observations and economic calendar events are upserted by natural source keys while macro regime snapshots remain append-only curated records; validation passed with focused and adjacent core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 19 completed: added `application/persistence/macro` with typed filters and `MacroPersistenceService` for explicit macro observation, macro regime snapshot, and economic calendar event persistence/retrieval through the repository protocol only; validation passed with targeted and adjacent application persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 20 completed: added `core/storage/persistence/news` typed news persistence contracts for articles and analysis snapshots, including source/external-id/URL identity validation, normalized symbols/themes, importance/sentiment/impact/confidence score validation, full untruncated LLM response preservation, bundle/result records, stable id helpers, exports, and focused contract tests; validation passed with focused and adjacent core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 21 completed: added news SQLAlchemy models and chained migration for `news_articles` and `news_analysis_snapshots`, including JSONB persistence-boundary columns, Text columns for full article and untruncated LLM output preservation, source identity check constraint, source+external-id and source+URL dedupe constraints, GIN indexes for symbols/themes/article ids, and source/published/workflow lineage indexes; validation passed with targeted and full core database pytest, ruff, scoped mypy, Alembic heads/history, and graphify update.
- [x] Step 22 completed: added `NewsPersistenceSerializer`, `NewsPersistenceRepository`, and `PostgresNewsPersistenceRepository`; news article facts upsert idempotently by source identity key (`source + external_id` when present, otherwise `source + url`), news analysis snapshots are append-only inserts preserving full untruncated LLM responses plus curated inputs/outputs/metadata/lineage, repository and serializer exports were wired, and validation passed with focused and full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 23 completed: added `application/persistence/news` with typed `NewsArticlePersistenceFilters`, `NewsAnalysisSnapshotPersistenceFilters`, and `NewsPersistenceService` for explicit curated article and news analysis bundle/record persistence plus filtered retrieval through the news repository protocol only; validation passed with targeted and adjacent application/news/core persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 24 completed: added `core/storage/persistence/sentiment` typed sentiment persistence contracts for snapshots and source contribution records, including fear/greed score, news/market/social/composite sentiment scores, confidence, component scores, symbol/universe scope, source references, lineage, bundle/result records, stable id helpers, exports, and focused contract tests; validation passed with focused and adjacent core storage persistence contract pytest, ruff, scoped mypy, and graphify update.
- [x] Step 25 completed: added sentiment SQLAlchemy models and chained migration for `sentiment_snapshots` and `sentiment_sources`, including JSONB persistence-boundary columns, append-only table design, source/symbol/universe/timestamp/workflow lineage indexes, metadata payload support, and row timestamps; validation passed with targeted and full core database pytest, ruff, scoped mypy, Alembic heads/history, and graphify update.
- [x] Step 26 completed: added `SentimentPersistenceSerializer`, `SentimentPersistenceRepository`, and `PostgresSentimentPersistenceRepository`; sentiment snapshots and source contribution records are append-only inserts preserving curated component scores, inputs/outputs, source references, metadata, and lineage, repository and serializer exports were wired, and validation passed with focused and full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 27 completed: added `application/persistence/sentiment` with typed `SentimentSnapshotPersistenceFilters`, `SentimentSourcePersistenceFilters`, and `SentimentPersistenceService` for explicit curated sentiment snapshot/source bundle and record persistence plus filtered retrieval through the sentiment repository protocol only; validation passed with targeted and adjacent application/sentiment/core persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 28 completed: added `core/storage/persistence/agent_intelligence` typed contracts for agent reasoning, agent recommendations, and agent risk assessments linked to existing `agent_signals`, including full untruncated reasoning/rationale/assessment/LLM text preservation, symbol/universe scope, lineage, supporting persisted record identities, bundle/result records, stable id helpers, exports, and focused contract tests; validation passed with focused and adjacent core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 29 completed: added `AgentReasoningModel`, `AgentRecommendationModel`, and `AgentRiskAssessmentModel` plus migration `20260530_0012_add_agent_intelligence_persistence_tables.py`; the tables link to `agent_signals.signal_id` with cascading foreign keys, preserve full untruncated reasoning/rationale/assessment/LLM text in `Text` columns, store inputs/outputs/supporting identities/metadata in JSONB boundary columns, include lineage and row timestamps, and index signal id, agent name/type, execution lineage, timestamp, symbol, and universe; validation passed with focused and full core database pytest, ruff, scoped mypy, Alembic heads/history, and graphify update.
- [x] Step 30 completed: added `AgentIntelligencePersistenceSerializer`, `AgentIntelligencePersistenceRepository`, and `PostgresAgentIntelligencePersistenceRepository` with idempotent upsert, read, and filtered list methods for agent reasoning, recommendations, and risk assessments; `agent_signals` remains the primary signal table and enriched records only link back through `agent_signal_id`; serializer/repository exports and focused tests were added, and validation passed with focused and full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 31 completed: added `application/persistence/agent_intelligence` with typed `AgentReasoningPersistenceFilters`, `AgentRecommendationPersistenceFilters`, `AgentRiskAssessmentPersistenceFilters`, and `AgentIntelligencePersistenceService` for explicit enriched agent reasoning/recommendation/risk-assessment bundle and record persistence plus get/list retrieval through the repository protocol only; validation passed with targeted and adjacent application/agent-intelligence/core persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 32 completed: added `core/storage/persistence/attribution` typed contracts for generic attribution records, signal attributions, and recommendation attributions with signed contribution scores, confidence validation, full untruncated explanations, lineage, optional agent/symbol/universe scope, required linked persisted source records, bundle/result records, stable id helpers, and exports; validation passed with focused and adjacent core storage persistence pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 33 completed: added `AttributionRecordModel`, `SignalAttributionModel`, and `RecommendationAttributionModel` plus migration `20260530_0013_add_attribution_persistence_tables.py`; the tables preserve full untruncated explanations in `Text` columns, store linked persisted source records and metadata in JSONB boundary columns, enforce contribution/confidence score checks, include lineage and row timestamps, link signal/recommendation attributions to existing `agent_signals`/`recommendations` where appropriate, and index recommendation id, signal id, agent name/type, execution lineage, timestamp, symbol, and universe; validation passed with focused and full core database pytest, ruff, scoped mypy, Alembic heads/history, and graphify update.
- [x] Step 34 completed: added `AttributionPersistenceSerializer`, `AttributionPersistenceRepository`, and `PostgresAttributionPersistenceRepository`; generic attribution, signal attribution, and recommendation attribution records now flatten to PostgreSQL boundary values and round-trip back into typed domain records, full explanations remain untruncated, linked persisted source records and metadata remain JSONB-only boundary fields, lineage is preserved, repository persistence uses stable-id upserts without deleting sibling attribution rows, and get/list methods support target/signal/recommendation, agent, lineage, symbol/universe, and timestamp filters; validation passed with focused attribution serializer/repository pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 35 completed: added `application/persistence/attribution` with typed `AttributionPersistenceFilters`, `SignalAttributionPersistenceFilters`, `RecommendationAttributionPersistenceFilters`, and `AttributionPersistenceService` for explicit generic attribution, signal attribution, and recommendation attribution bundle/record persistence plus get/list retrieval through the repository protocol only; filters normalize identifiers/symbols and validate ordered time windows, service exports were wired, and validation passed with focused attribution application pytest, full application persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 36 completed: extended `core/storage/persistence/runtime` with typed `WorkflowStateSnapshotRecord` plus `new_workflow_state_snapshot_id` and `new_random_workflow_state_snapshot_id`; the contract captures workflow status, timestamp, runtime id, optional checkpoint reference, wave index, serialized state payload, lineage, and metadata as a persistence-boundary audit snapshot without changing runtime execution semantics, exports were wired, and validation passed with focused runtime contract pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 37 completed: added `WorkflowStateSnapshotModel` and migration `20260530_0014_add_workflow_state_snapshot_persistence_table.py` for `workflow_state_snapshots`; the table stores append-friendly workflow audit snapshots with workflow name, execution id, workflow status, timestamp, runtime id, optional node name, wave index, checkpoint reference, JSONB state payload/metadata boundary columns, row timestamps, a non-negative wave-index check, and indexes by workflow, execution, runtime, timestamp, and wave index; model exports and Alembic metadata expectations were wired, and validation passed with focused/full core database pytest, ruff, scoped mypy, Alembic heads/history, metadata import, and graphify update.
- [x] Step 38 completed: added `RuntimePersistenceSerializer` workflow-state snapshot mapping, extended `RuntimePersistenceRepository` and `PostgresRuntimePersistenceRepository` with stable-id upsert/get/list support for `WorkflowStateSnapshotRecord`, and added `application/persistence/workflow_audit` with typed filters plus `WorkflowStateSnapshotPersistenceService`; the service is explicit audit persistence only and does not auto-capture runtime state or change runtime execution semantics, exports were wired, and validation passed with focused serializer/repository/service pytest, full core storage/application persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 39 completed: added typed `ReportVersionRecord` and `ReportPublicationRecord` persistence-boundary contracts under `core/storage/persistence/reports`, including report/version linkage fields, publication target/status/timestamps, full untruncated version markdown and structured payload preservation, validation rules, stable `new_report_version_id` and `new_report_publication_id` helpers, expanded `ReportPersistenceBundle` defaults for future repository support, exports, and focused contract tests; validation passed with focused report contract/serializer/repository pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 40 completed: added `ReportVersionModel` and `ReportPublicationModel` plus migration `20260530_0015_add_report_version_publication_tables.py`; `report_versions` links to existing `reports` with positive version numbers and per-report uniqueness while preserving full markdown, structured payload, metadata, row timestamps, and retrieval indexes, and `report_publications` links to reports plus optional versions with target/status/requested/published timestamps, artifact/error fields, metadata, published-after-requested validation, row timestamps, foreign keys, and retrieval indexes; metadata exports and Alembic expectations were wired, and validation passed with focused/full core database pytest, ruff, scoped mypy, Alembic heads/history, metadata import, and graphify update.
- [x] Step 41 completed: extended report persistence with `version_values`/`publication_values` serializer mappings, version/publication model rehydration, `ReportPersistenceRepository.persist_report_bundle`, `get_report_bundle`, section/artifact/version/publication listing, version lookup, and `PostgresReportPersistenceRepository` upserts for versions/publications without breaking the existing report/section/artifact persistence path; added `application/persistence/reports` with `ReportPersistenceService`, typed artifact/publication filters, package/root exports, and focused serializer/repository/service tests; validation passed with focused report persistence pytest, full core storage persistence pytest, full application persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 42 completed: added `core/storage/persistence/telemetry` with typed `TelemetryEventRecord`, `TelemetryMetricRecord`, `TelemetryTraceRecord`, `WorkflowMetricRecord`, `AgentMetricRecord`, and `ProviderMetricRecord` contracts, plus `TelemetryPersistenceBundle`, `TelemetryPersistenceResult`, stable id helpers, validation for required identifiers, finite metric values, non-negative durations/status codes, trace timestamp ordering, lineage/correlation fields, JSONB-boundary payload/dimension/attribute/metadata fields, package exports, and focused contract tests; telemetry is explicitly scoped as operational observability/audit data and not a curated RAG ingestion source; validation passed with focused telemetry contract pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 43 completed: added `TelemetryEventModel`, `TelemetryMetricModel`, `TelemetryTraceModel`, `WorkflowMetricModel`, `AgentMetricModel`, and `ProviderMetricModel` plus migration `20260530_0016_add_telemetry_persistence_tables.py`; the tables preserve telemetry payloads/dimensions/attributes/metadata as JSONB boundary columns, include lineage/correlation/trace/span fields, enforce non-negative duration/status-code and trace timestamp ordering checks, add row timestamps, and index timestamp, event type, source, workflow lineage, agent/provider identity, endpoint, symbol, status, trace/span, and correlation id; model exports and Alembic metadata expectations were wired, and validation passed with focused/full core database pytest, ruff, scoped mypy, Alembic heads/history, metadata import, and graphify update.
- [x] Step 44 completed: added telemetry persistence serialization and repository support with typed mappings for events, generic metrics, traces, workflow metrics, agent metrics, and provider metrics; `PostgresTelemetryPersistenceRepository` keeps events/traces append-friendly through `ON CONFLICT DO NOTHING`, upserts metric families by stable identity through `ON CONFLICT DO UPDATE`, exposes typed single-record and filtered list retrieval APIs for timestamp/source/workflow/correlation/agent/provider dimensions, wires package exports, and validates with focused telemetry serializer/repository pytest, full core storage persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 45 completed: added `application/persistence/telemetry` with `TelemetryPersistenceService` and typed filter contracts for telemetry events, generic metrics, traces, workflow metrics, agent metrics, and provider metrics; the service remains explicit opt-in application persistence and delegates only through `TelemetryPersistenceRepository`; validation passed with focused/full application persistence pytest, ruff, scoped mypy, and graphify update.
- [x] Step 46 completed: normalized `application/persistence/__init__.py` as a service/filter-only application boundary, kept repositories under core storage persistence, avoided service locators, and added export contract tests; validation passed with pytest, ruff, scoped mypy, and graphify update.
- [x] Step 47 completed: added cross-domain application persistence integration tests with repository protocol fakes for every V2 service, verifying typed persistence results and dependency-injected service boundaries; validation passed with pytest, ruff, scoped mypy, and graphify update.
- [x] Step 48 completed: added executable RAG readiness checks proving canonical PostgreSQL source categories exist for downstream projection while excluding raw runtime and telemetry tables from curated RAG sources; validation passed with pytest, ruff, scoped mypy, and graphify update.
- [x] Step 49 completed: expanded `docs/postgres_persistence.md` with V2 table/service inventory, migration commands, telemetry persistence rules, RAG source categories, and explicit guidance that raw workflow/telemetry data is operational observability data rather than canonical RAG source data.
- [x] Step 50 completed: ran final V2 validation across targeted persistence test suites, ruff, scoped mypy, Alembic heads/history, database model import, and graphify update; fixed the runtime persistence event subscriber fake to satisfy the expanded workflow-state snapshot repository contract. V2 is ready for review before commit/push.
