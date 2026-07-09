# Polaris Platform Architecture and Operations

This guide is the canonical non-RAG overview of Polaris's current platform
architecture and local operating model. It consolidates the stabilized runtime,
composition, telemetry, persistence, integration, and backtesting boundaries.
RAG-specific architecture and operations remain documented in
[`platform_rag_pipeline.md`](platform_rag_pipeline.md).

## Architectural invariants

Polaris follows an inside-out architecture. Lower-level runtime contracts define
the execution trunk; application, integration, intelligence, reporting, and
interface code conform to that trunk.

The following rules are non-negotiable:

- `WorkflowFacade` is the application boundary for workflow registration,
  execution, replay, inspection, control, and completed-run access.
- `WorkflowBootstrap` and Dishka providers are the composition roots. Interface
  code must not recreate the runtime object graph.
- `RuntimeEngine` owns graph execution. Backtests and live workflows use the
  same runtime path.
- `RuntimeContext` is the sole canonical workflow execution snapshot.
- Internal application and intelligence contracts are typed. Dictionaries are
  reserved for external and serialization boundaries.
- PostgreSQL is the durable system of record. Qdrant and Neo4j are rebuildable
  RAG projections; local files are reports, exports, or development artifacts.
- `EventBus` and typed `RuntimeEvent` values are the runtime notification path.
- Policy answers whether an operation may occur; governance determines whether
  it should occur or requires approval.
- Internal calculations and persistence preserve full numeric precision.
  Rounding belongs only in human-facing renderers.

The accepted architectural decisions are recorded under
[`.docs/decisions/`](decisions/).
Canonical responsibility, data ownership, single-writer, and projection
assignments are maintained in
[`platform_architecture_ownership_ledger.md`](platform_architecture_ownership_ledger.md).

## Canonical runtime flow

A CLI workflow run follows one execution path:

```text
Typer command
  -> CLI runtime/request scope
  -> Dishka request-scoped command service
  -> WorkflowFacade
  -> WorkflowEngine
  -> RuntimeEngine
  -> RuntimeNode graph
  -> RuntimeNodeOutput values
  -> RuntimeContext snapshot
  -> events, checkpoints, completed-run persistence, and report rendering
```

Interfaces parse input and render output. They do not execute nodes, mutate the
runtime, or call vendor SDKs. `WorkflowFacade` applies the canonical workflow,
control, replay, policy, governance, telemetry, and lifecycle boundaries before
delegating execution to the runtime.

### RuntimeContext ownership

`RuntimeContext` schema version 2 owns the replayable execution snapshot:

- immutable workflow inputs supplied at the invocation boundary;
- node outputs and node execution evidence;
- artifacts and attributable errors;
- trace context and runtime execution metadata.

Workflow nodes read prior results from the context's node outputs and read
invocation data from workflow inputs. Polaris no longer maintains a parallel
`RuntimeState` business-state aggregate or `market`, `portfolio`, `risk`, and
`strategy` runtime namespaces. Business models such as the domain
`PortfolioState` remain owned by their domain layer and are serialized only when
crossing a runtime or persistence boundary. This avoids two competing sources of
truth inside one workflow.

Completed-run history and runtime checkpoints are intentionally different:

- checkpoints are runtime-owned resume and replay inputs;
- completed runs are PostgreSQL-backed audit, history, inspection, report, and
  curation records after execution has finished.

A completed run is not a substitute for a checkpoint.

## Composition and dependency ownership

Dishka owns dependency construction and lifecycle management.

- Application scope owns long-lived infrastructure and shared runtime
  components.
- Each command, request, or tool invocation opens a request scope and resolves
  request-scoped services from it.
- `get_async_di_container()` is the canonical asynchronous container entry
  point. Synchronous composition is used only by boundaries that require it,
  including deterministic backtesting, while preserving the same provider and
  runtime contracts.
- The owning boundary closes the request scope and any external resources.
- `EventBus`, `WorkflowControlManager`, telemetry, policy, governance, and the
  workflow facade must resolve as the intended shared instances; interfaces do
  not hand-construct substitutes.

CLI execution uses its runtime-scope helper and request-scoped command services.
MCP and future interfaces must follow the same pattern rather than becoming
service locators or alternative composition roots.

## Service, provider, and client boundary

External information enters the platform through one dependency-inverted path:

```text
Runtime node or intelligence agent
  -> typed application service request/result
  -> provider protocol
  -> vendor-specific client
  -> external system
```

Responsibilities are separated as follows:

| Layer | Responsibility |
| --- | --- |
| Application service | Coordinate a use case, validate typed inputs, combine provider results, and return a typed result. |
| Provider | Present a stable platform-facing protocol and normalize vendor data into typed platform DTOs. |
| Client | Own HTTP/SDK transport, authentication, retry/backoff, pagination, timeout, rate limiting, and raw response parsing. |

For example, macro analysis coordinates independent provider requests
concurrently, while the provider/client boundary owns external HTTP access.
Market and portfolio services follow the same rule. Agents never import or call
vendor SDKs directly.

Concurrent provider work uses bounded `asyncio` tasks or gathers, preserves
trace context, propagates cancellation, and records provider latency and failure
telemetry. Concurrency is an application orchestration detail, not a reason to
collapse the service, provider, and client layers.

## Telemetry, events, and trace propagation

Observability is part of execution rather than a post-processing feature.

1. A canonical operation entry point creates or resumes trace context.
2. The context is carried by `RuntimeContext`, runtime events, asynchronous
   tasks, provider calls, and datastore operations.
3. Runtime components publish typed events through the shared `EventBus`.
4. Telemetry adapters translate those events into structured logs, counters,
   histograms, and spans.
5. OpenTelemetry, Prometheus, Jaeger, PostgreSQL telemetry persistence, and local
   logs act as sinks; none of them owns domain execution.

Provider and datastore calls record operation identity, duration, success or
failure, and trace correlation. Caught telemetry failures are logged defensively
but do not replace a valid domain result. Secrets are redacted at telemetry,
checkpoint, and persistence serialization boundaries without mutating the
in-memory source object.

Local Prometheus, Jaeger, and Grafana setup is documented in
[`core_telemetry_observability.md`](core_telemetry_observability.md).

## Persistence classification

Every persisted or transported value should be classified before a schema is
chosen.

| Class | Examples | Storage rule |
| --- | --- | --- |
| Canonical business state | Market observations, portfolio state, signals, recommendations, decisions, completed-run history | Persist in PostgreSQL with typed ownership. Stable query dimensions receive first-class columns. |
| Reproducible derived data | Indicators, calibrated scores, attribution, deterministic metrics | Recompute when practical; persist when audit, historical comparison, or performance requires it, with algorithm/model version. |
| Transient runtime or presentation data | Scheduling state, CLI progress, renderer formatting, temporary aggregates | Keep in runtime context, events, checkpoints, or artifacts; do not promote to business system-of-record data. |
| Telemetry and diagnostics | Durations, retries, trace IDs, provider health, failure provenance | Send through telemetry/runtime observability stores unless the same value is also a business decision. |

Purpose-named JSON/JSONB fields are acceptable persistence boundaries for
complete nested payloads. Planned canonical fields must not be hidden in generic
`metadata`. New first-class fields require SQLAlchemy model changes, an Alembic
migration, and migration/metadata-divergence tests.

See [`postgres_persistence.md`](postgres_persistence.md) for the schema,
migration, retention, and completed-run conventions. The historical contract
audit and its superseding resolutions are recorded in
[`platform_data_contract_inventory.md`](platform_data_contract_inventory.md).

## Deterministic backtesting

Backtesting selects simulated or historical providers through DI and invokes the
same `WorkflowFacade`, workflow graph, services, nodes, policies, governance,
telemetry, and persistence contracts as a live run. The runtime is unaware of
whether data is live or simulated.

Deterministic scenarios fix their data, time, identifiers, ordering, and
expectations. Verification compares platform results with independently derived
expected calculations rather than merely comparing against a previous Polaris
output. Full details and CLI examples are in
[`backtesting_system.md`](backtesting_system.md).

## Common local commands

Synchronize the environment and inspect the CLI:

```bash
uv sync
uv run polaris --help
uv run polaris workflow list
uv run polaris workflow describe morning_report
uv run polaris inspect config
uv run polaris inspect runtime
```

Run a workflow:

```bash
uv run polaris morning-report
uv run polaris workflow run morning_report
```

Terminal output, progress notifications, and interactive pause/resume/cancel
control are enabled for workflow runs. `--format` adds an HTML, JSON, Markdown,
or PDF artifact; it does not suppress terminal output.

Start PostgreSQL and apply/inspect migrations:

```bash
docker compose up -d postgres
docker compose ps postgres
uv run alembic upgrade head
uv run alembic current
uv run alembic check
```

Inspect completed-run and backtest command surfaces before destructive or
persisted operations:

```bash
uv run polaris runs --help
uv run polaris runs list --help
uv run polaris runs show --help
uv run polaris runs delete --help
uv run polaris runs cleanup --help
uv run polaris backtest --help
uv run polaris backtest run --help
```

Completed-run deletion and cleanup require the CLI confirmation and the typed
policy/governance confirmation path. Use `--yes` only in a controlled,
pre-authorized automation boundary.

Run the standard static verification sequence:

```bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy . --explicit-package-bases
uv run pytest -q
uv run graphify update .
```

## Local service dependencies

Start only the infrastructure needed by the operation under test.

| Operation | Required local services |
| --- | --- |
| Static checks and unit tests | None |
| Alembic migration and live PostgreSQL persistence tests | PostgreSQL |
| Synthetic deterministic backtest without persistence | None |
| PostgreSQL-backed backtest history or persistence | PostgreSQL |
| External metrics/traces validation | Prometheus and Jaeger; Grafana for dashboards; PostgreSQL when validating telemetry persistence/retention |
| Live provider workflow | The configured vendor credentials/network plus PostgreSQL when durable runtime/report persistence is enabled |
| RAG ingestion, retrieval, or projection rebuild | See `platform_rag_pipeline.md`; service requirements may include PostgreSQL, Qdrant, Neo4j, BGE reranker, and configured model/provider endpoints |

Use a timeout that reflects the expected operation duration. If an operation
times out, investigate service readiness or a blocked dependency before simply
raising the limit.

## Operational safety and known boundaries

- Apply migrations before enabling PostgreSQL-backed runtime or report
  persistence. Never use `Base.metadata.create_all()` as the production schema
  path.
- Do not bypass `WorkflowFacade`, policy, governance, or typed destructive
  confirmation for control, replay, registry mutation, or deletion.
- API, scheduler, and UI packages remain non-production scaffolding until their
  transport and lifecycle contracts are intentionally implemented.
- Repository health tools can report false-positive dead code for protocol,
  plugin, DI, or reflection-based consumers. Verify exact references,
  composition, tests, and history before deleting production code.
- Churn and bus-factor risk on central runtime/composition files is an
  organizational and review concern even when tests and static checks pass.
- Repowise indexes committed repository knowledge and may lag uncommitted
  working-tree refactors. Use source, tests, and the refreshed Graphify map as
  the authority for the current working tree, then re-index Repowise after the
  changes are committed.
