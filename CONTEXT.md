# Polaris Project Context

## Purpose

Polaris is a Python-based AI intelligence and workflow-orchestration platform for portfolio analysis, risk assessment, strategy synthesis, reporting, replay, and deterministic backtesting.

The platform is **recommendation-driven**, not an autonomous trading system. It may produce portfolio intent, trade proposals, and execution-safety decisions, but broker execution remains outside the current platform boundary.

Primary goals:

- replayable and resumable workflows
- deterministic analysis and backtesting
- strongly typed internal contracts
- observable and attributable decisions
- policy and governance enforcement
- capital preservation
- production-grade persistence and operations

## Architectural Direction

Polaris follows an inside-out architecture:

```text
Runtime
→ Replay and persistence
→ Telemetry
→ Plugins
→ Policy and governance
→ Capabilities
→ Application services
→ Intelligence
→ Portfolio and strategy
→ Trade proposals and execution safety
→ External interfaces
```

Lower layers define stable contracts. Higher-level code must conform to them through dependency inversion; edge code must not distort the runtime to preserve obsolete behavior.

## Canonical Execution Path

```text
Interface
→ WorkflowFacade
→ WorkflowBootstrap composition
→ Workflow definition and compiler
→ RuntimeEngine
→ RuntimeNode
→ RuntimeNodeOutput
→ RuntimeContext
→ PostgreSQL persistence
```

Canonical ownership:

- `RuntimeEngine` owns node execution.
- `WorkflowFacade` is the application-facing workflow boundary.
- `WorkflowBootstrap` is the workflow composition root.
- Dishka is the dependency-injection framework.
- `EventBus` and typed `RuntimeEvent` objects are the runtime notification path.
- `RuntimeContext` contains execution context and accumulated node outputs.
- Completed workflow runs and runtime evidence are persisted in PostgreSQL.

The runtime is intentionally unaware of whether providers are live, historical, or simulated.

## Current Platform Map

### Runtime and workflows

Implemented runtime capabilities include:

- workflow graph compilation and execution
- checkpoints, replay, resume, and completed-run retrieval
- pause, resume, cancel, and progress notifications
- lifecycle events and event dispatch
- policy and governance evaluation
- plugin loading and lifecycle management
- runtime telemetry and trace-context propagation
- artifact, validation, and state-management support

Current workflow definitions:

- morning report
- momentum strategy
- strategy review

`RuntimeContext` and `RuntimeNodeOutput` are the canonical workflow evidence contracts. The former `MarketState`, `RiskState`, `StrategyState`, and runtime `PortfolioState` aggregate has been removed; domain state belongs in typed domain records or node outputs rather than a competing runtime source of truth.

### Application and integration layers

External data follows this path:

```text
External system
→ vendor-specific async client
→ provider normalization
→ typed application request/result
→ intelligence or workflow node
```

Responsibilities:

- **Clients:** authentication, HTTP/SDK calls, retries, pagination, rate limits, timeouts, and raw parsing.
- **Providers:** vendor abstraction and translation into stable platform-facing contracts.
- **Application services:** use-case orchestration across providers, persistence, and domain operations.
- **Intelligence components:** transform typed normalized inputs into signals, assessments, recommendations, and explanations.

Agents and intelligence components do not call vendor SDKs directly.

### Intelligence flow

The principal analysis flow is:

```text
Application service results
→ PortfolioStateBuilder and analyst agents
→ typed fundamental, technical, news, and sentiment signals
→ risk agents and risk aggregation
→ regime perspectives
→ strategy synthesis
→ portfolio intent
→ trade packaging
→ execution risk guard
```

The exact workflow graph may use only a subset of this flow. Each component produces typed domain output and does not directly place trades.

Technical analysis is organized as a typed service pipeline covering snapshots, indicators, trend, volatility, breadth, raw regime classification, and calibration. Detailed field contracts are defined by the current request/result and domain model classes, not by duplicated documentation lists.

### Persistence

PostgreSQL is the platform system of record. SQLAlchemy models and Alembic migrations govern its schema.

Canonical durable categories include:

- workflow runs, node runs, events, checkpoints, and completed-run context
- market, macro, news, sentiment, portfolio, and intelligence records
- reports, recommendations, attribution, lineage, audit, and retention records
- telemetry records
- backtest runs, metrics, and artifacts
- curated RAG documents, chunks, and projection jobs

Persistence access belongs in typed repositories and application persistence services. Analytical services return typed results and must not persist workflow-derived analysis unless persistence is the explicit use case.

### Workflow-output curation

Workflow outputs are runtime evidence; they do not automatically become canonical domain records or RAG content.

The canonical lifecycle is:

```text
Typed node output
→ persisted workflow evidence
→ explicit typed projection policy
→ canonical curated domain record
→ RAG document and chunk creation
→ Qdrant and Neo4j projections
```

Only explicitly supported, eligible, attributable, and useful records are curated. This prevents every transient node field or metadata value from becoming a permanent knowledge contract.

### RAG pipeline

The platform-native RAG pipeline includes:

- curated typed ingestion from PostgreSQL records
- parent-child and structure-aware chunking
- dense and sparse hybrid vector retrieval in Qdrant
- graph projection and retrieval in Neo4j
- retrieval fusion and cross-encoder reranking
- adaptive routing, CRAG, Self-RAG, context selection, and answer generation
- security validation, quality checks, lifecycle operations, and telemetry

PostgreSQL remains authoritative. Qdrant and Neo4j are rebuildable projections and must never become independent sources of truth.

### Backtesting

Backtesting uses the production workflow runtime and service contracts. Only provider composition changes:

```text
Canonical workflow
→ canonical services
→ deterministic historical or simulated providers
```

A deterministic scenario must be able to verify independently derived expected calculations, risk assessments, and recommendations. The runtime does not contain a special backtesting execution path.

### Telemetry and operations

The observability stack provides:

- structured logging
- Prometheus metrics
- OpenTelemetry traces exported to Jaeger
- PostgreSQL telemetry persistence and retention
- trace propagation across events, providers, async tasks, and storage operations

Runtime notifications flow through `EventBus`; telemetry observes and maps those events at the boundary. Telemetry failures must not replace valid domain results, but they must be visible through defensive logging.

Docker Compose currently defines PostgreSQL, Qdrant, Neo4j, BGE reranker, Prometheus, Jaeger, and Grafana services.

### Interfaces

The native implemented interface is the async Typer CLI exposed as:

```bash
polaris
```

It supports workflow execution and control, morning reports, completed runs, inspection, backtesting, and RAG operations.

The HTTP API tree currently contains empty scaffolding and is not an implemented interface. The `mcp_server/` package is also unimplemented. If MCP is added, it must be a thin external transport over canonical application services resolved through Dishka request scopes—not a second RAG, persistence, or workflow implementation.

## Domain Invariants

### Typed contracts

Internal layers use strongly typed requests, results, domain objects, signals, and runtime contracts. Dictionaries are limited to external, telemetry, event, serialization, persistence, checkpoint, replay, and transport boundaries.

### Numeric precision

Application, intelligence, analysis, calibration, regime, and persistence layers retain full precision. Rounding is permitted only at human-facing presentation boundaries.

### Score semantics

Canonical score ranges:

- stability: `0.0` to `1.0`, where higher is better
- risk: `0.0` to `1.0`, where higher is worse
- confidence: `0.0` to `1.0`, where higher is more certain

Convert stability to risk explicitly:

```python
risk = 1.0 - stability
```

Do not mix these semantics implicitly.

### Sources of truth

For each durable business concept there must be one authoritative model, owner, and canonical writer. Keep these categories distinct:

- runtime evidence
- canonical domain records
- derived projections
- telemetry
- presentation output

## Policy and Governance

Policy answers **“May this happen?”** with `ALLOW` or `DENY`.

Governance answers **“Should this happen?”** with outcomes such as `ALLOW`, `WARN`, `DENY`, `REQUIRE_APPROVAL`, or `SKIP`.

Governance may signal that approval is required, but a complete approval workflow subsystem is not currently implemented. Do not describe approval storage, human-review interfaces, or resume semantics as available until corresponding source and tests exist.

## Repository Layout

```text
application/       Use cases, persistence orchestration, reporting, and RAG services
automation/        Automation support
config/            Settings and configuration
core/              Runtime, workflow, database, storage, telemetry, plugins, policy, governance
domain/            Typed business models and contracts
integration/       External clients, providers, and simulated providers
intelligence/      Analyst, risk, strategy, portfolio, research, and execution-safety agents
interfaces/        CLI plus unimplemented API scaffolding
migrations/        Alembic database migrations
tests/             Unit, integration, database, architecture, contract, and coverage tests
web/               Web-layer scaffolding and assets
workflows/         Workflow definitions
mcp_server/        Reserved package; no current implementation
docs/              Maintained architecture and operations documentation
.agents/plans/     Feature-specific implementation plans
```

## Detailed Documentation

Use these documents for deeper, maintained detail:

- `docs/platform_architecture_and_operations.md`
- `docs/platform_architecture_ownership_ledger.md`
- `docs/platform_data_contract_inventory.md`
- `docs/postgres_persistence.md`
- `docs/platform_rag_pipeline.md`
- `docs/model_profile_policy.md`
- `docs/model_allocation_readiness.md`
- `docs/workflow_output_curation.md`
- `docs/backtesting_system.md`
- `docs/core_telemetry_observability.md`
- `docs/canonical_trace_lifecycle.md`
- `docs/observability_coverage_ledger.md`
- `docs/mcp_rag_server_analysis.md`

Source code and active tests remain authoritative when generated or historical documentation is stale.

## Development Environment

- Python `>=3.12`
- `uv` for dependency management and command execution
- `pytest` for tests
- Ruff for linting and formatting
- MyPy for static type checking
- Alembic and `pytest-alembic` for database schema management and verification
- Graphify and Repowise for scoped architecture and code-health analysis
