# Polaris Platform Architecture and Operations

This guide is the canonical non-RAG overview of Polaris's current platform
architecture and local operating model. It consolidates the stabilized runtime,
composition, telemetry, persistence, integration, and backtesting boundaries.
RAG-specific architecture and operations remain documented in
[`platform-native-rag-retrieval-pipeline.md`](platform-native-rag-retrieval-pipeline.md).

## Platform scope and goals

Polaris is a Python AI intelligence and workflow-orchestration platform for
portfolio analysis, risk assessment, strategy synthesis, reporting, replay, and
deterministic backtesting.

The platform is recommendation-driven rather than an autonomous trading system.
It can produce portfolio intent, trade proposals, and execution-safety decisions,
but broker execution is outside the current platform boundary.

The architecture exists to support replayable and resumable workflows,
deterministic analysis and backtesting, strongly typed internal contracts,
observable and attributable decisions, policy and governance enforcement, capital
preservation, and production-grade persistence and operations.

## Architectural invariants

Polaris follows an inside-out architecture. Lower-level runtime contracts define
the execution trunk; application, integration, intelligence, portfolio, strategy,
recommendation, reporting, and interface code conform to that trunk rather than
forcing compatibility behavior into the runtime.

The intended dependency direction is:

```text
Runtime
  -> replay and persistence
  -> telemetry
  -> plugins
  -> policy and governance
  -> capabilities
  -> application services
  -> intelligence
  -> portfolio and strategy
  -> trade proposals and execution safety
  -> external interfaces
```

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

Accepted architectural decisions are recorded under
[`docs/adr/`](../adr/).
Canonical responsibility, data ownership, single-writer, and projection
assignments are maintained in
[`platform-architecture-ownership-ledger.md`](platform-architecture-ownership-ledger.md).

## Domain flow and authority rules

Capital-relevant decision support follows one authority sequence rather than a
flat collection of agent outputs:

```text
typed provider/service facts
  -> intelligence assessments and specialized risk signals
  -> aggregate risk and strategy evidence
  -> strategy synthesis
  -> portfolio allocation or rebalance intent
  -> broker-neutral trade proposal
  -> execution-risk decision
  -> governed release or future execution request
```

Signals, scores, and recommendations retain their typed family and authority as
they move through this sequence. Downstream components may reference upstream
facts, but they must not copy those facts into a competing source of truth,
reinterpret score polarity, or collapse risk, strategy, portfolio intent, trade
proposal, and execution decision into one record.

Risk agents produce decision-support evidence: specialized risk assessments,
aggregate risk, constraints, mitigations, sizing pressure, and risk context. They
do not select trades, approve execution, create orders, or bypass strategy,
portfolio-intent, trade-packaging, policy, governance, or approval boundaries.

`PortfolioManagerAgent` produces portfolio allocation or rebalance intent. That
intent is not an executable broker order and must be converted into a distinct
broker-neutral proposal before execution-risk review. `ExecutionRiskGuard` is the
required execution-safety decision boundary for trade proposals; interfaces,
brokers, future execution transports, and capital-relevant publication paths
that expose trade proposals must not bypass it.

Controlled boundary crossings follow the policy, governance, approval, and
release sequence before any future execution-capable boundary. Policy answers
whether an operation or boundary crossing may occur. Governance answers whether
it should proceed, warn, deny, skip, require approval, require residual-risk
acceptance, or block release. Human or organizational approval and residual-risk
acceptance are attributable governance lifecycle outcomes, not model text,
report metadata, telemetry, or local interface state. Execution, if a future
architecture introduces it, remains downstream of policy, governance, approval,
release, and execution-risk decisioning.

Material recommendation explanations require attribution through decision
evidence: claim references, durable packet support, reconstruction references,
and source records where the producing contract marks the claim as
readiness-gating. Recommendation prose, RAG answers, report renderings, and tool
responses may present those explanations only by preserving the underlying
evidence bindings.

## Canonical runtime flow

Every workflow-capable interface follows the same canonical execution path:

```text
Interface
  -> Dishka request scope
  -> WorkflowFacade
  -> WorkflowBootstrap composition
  -> workflow definition and compiler
  -> RuntimeEngine
  -> RuntimeNode graph
  -> RuntimeNodeOutput values
  -> RuntimeContext snapshot
  -> PostgreSQL persistence for completed-run evidence
```

The CLI specializes the first two steps as a Typer command and CLI
runtime/request scope. Other transports, including MCP and future HTTP/API
surfaces, must enter through their own request scope and then delegate to the
same facade and runtime path.

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

### Runtime and workflow capabilities

The runtime capability set includes workflow graph compilation and execution,
checkpointing, replay, resume, completed-run retrieval, cooperative
pause/resume/cancel control, progress notifications, typed lifecycle events,
event dispatch, policy and governance evaluation, plugin loading and lifecycle
management, telemetry and trace-context propagation, artifact handling,
validation, and runtime state management.

`RuntimeContext` and `RuntimeNodeOutput` are the canonical workflow evidence
contracts. Workflow evidence can later become curated domain records only through
an explicit typed eligibility and projection policy; it is not automatically a
business system-of-record update or RAG source.

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

## Governance approval, residual risk, and contestability

Policy and governance remain separate even when they are audited together:

- policy answers **“May this happen?”** and persists `ALLOW` or `DENY` automated
  policy audit outcomes;
- governance answers **“Should this happen?”** and persists `ALLOW`, `WARN`,
  `DENY`, `REQUIRE_APPROVAL`, or `SKIP` automated governance audit outcomes.

`PolicyEngine` and `GovernanceEngine` compute automated decisions in the
canonical runtime/facade path. They are not approval stores. The canonical
application owner for approval lifecycle behavior is
`AutomatedDecisionAuditService`, backed by `AutomatedDecisionAuditRepository` and
its PostgreSQL implementation. The service records automated governance audit
records, creates evidence-scoped review tasks when `REQUIRE_APPROVAL` supplies
decision evidence, resolves review tasks, writes immutable review decisions,
updates task status, writes scoped residual-risk acceptances, exposes review
state queries, and evaluates governed-output release requests.

The implemented governance decision flow is:

1. Automated governance records the platform-computed outcome and authority
   metadata as durable audit evidence.
2. `ALLOW` and `WARN` remain durable automated governance recommendations in
   the current source path and do not create human review tasks by themselves.
3. `DENY` and `SKIP` are durable and observable automated outcomes; they are not
   converted into pending human approvals.
4. `REQUIRE_APPROVAL` creates at most one scoped review task for the subject,
   evidence packet, evidence version, review scope, requested action, and sink
   represented in the governance audit record.
5. A human or organizational reviewer resolves the task with an immutable
   outcome: `approved`, `denied`, `contested`, `changes_requested`, or
   `overridden`.
6. The externally visible approval state is derived from the durable task status:
   `pending_review`, `review_approved`, `review_denied`, `review_contested`,
   `changes_requested`, `review_overridden`, or
   `residual_risk_acceptance_required`.

Residual-risk acceptance is intentionally human and organizational. It is not a
model assertion and not a hidden metadata flag. When a Vigilant task is approved
or overridden while residual risk remains, the reviewer must supply an explicit
acceptance containing the reviewer identity, rationale, residual-risk scope,
review scope, subject, risk tier, and evidence packet/version. The acceptance is
persisted as a first-class record with the reviewed subject, evidence packet,
evidence version, review scope, and residual-risk scope. A new evidence version
or broader residual-risk scope must be represented by a new explicit acceptance,
not by mutating or reinterpreting an old record.

Contestability is also a durable audit concept. A contested decision, requested
changes, denial, or override does not delete or rewrite the automated governance
audit record that caused the review. The review decision records who acted, why,
which evidence version was reviewed, the requested remediation when applicable,
and the resulting task status. `changes_requested`, `review_denied`,
`review_contested`, pending, and cancelled states remain blocking for governed
publication or durable promotion until a later canonical review outcome permits
release.

Capital-relevant publication and durable promotion are checked through the
application release boundary, not by renderers or projectors inventing local
state. `AutomatedDecisionAuditService.evaluate_governed_output_release()` allows
release only when the output's authority tier does not require release review or
when an approved/overridden review task matches the subject, scope, action, sink,
and evidence version; if residual-risk acceptance is required, the matching
acceptance must also exist. Morning-report persistence and workflow-output
projection call this service and return a blocked/skip outcome instead of
publishing or promoting unresolved governed outputs.

Audit reconstruction starts from PostgreSQL, not telemetry: automated governance
audit records, review tasks, immutable review decisions, residual-risk
acceptance records, and the evidence packet identifiers they reference are the
canonical trail. Approval lifecycle logs, metrics, traces, and runtime events are
observability for diagnosis and operations; they must not become an alternate
approval ledger.

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
[`telemetry-observability-trace-lifecycle-local-observability.md`](telemetry-observability-trace-lifecycle-local-observability.md).

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

See [`persistence-curated-records-postgresql-persistence.md`](persistence-curated-records-postgresql-persistence.md) for the schema,
migration, retention, and completed-run conventions. Current data-contract and
score semantics are defined in
[`domain-contracts-data-semantics-contract-semantics.md`](domain-contracts-data-semantics-contract-semantics.md).
The historical Step 5 contract inventory is preserved as reference material in
[`../reference/domain-contracts-data-semantics-step-5-data-contract-inventory.md`](../reference/domain-contracts-data-semantics-step-5-data-contract-inventory.md).

## Deterministic backtesting

Backtesting selects simulated or historical providers through DI and invokes the
same `WorkflowFacade`, workflow graph, services, nodes, policies, governance,
telemetry, and persistence contracts as a live run. The runtime is unaware of
whether data is live or simulated.

Deterministic scenarios fix their data, time, identifiers, ordering, and
expectations. Verification compares platform results with independently derived
expected calculations rather than merely comparing against a previous Polaris
output. Full details and CLI examples are in
[`backtesting-simulation-system.md`](backtesting-simulation-system.md).

## Current interface and workflow surface

The native implemented user interface is the async Typer CLI exposed as
`polaris`. It supports workflow execution and control, morning-report execution,
completed-run inspection, platform inspection, backtesting, RAG operations, AI
and evaluation operations, and observability commands through application
services and the workflow facade.

The built-in workflow catalog currently registers `morning_report` as the
canonical built-in workflow. Strategy workflow definition modules can exist in
the source tree without becoming catalog entries; a workflow is part of the
built-in operational surface only when it is registered through the canonical
workflow catalog/bootstrap path.

The MCP server is implemented as a thin read-only FastMCP transport for approved
agent hosts. It exposes grounded RAG questions, RAG readiness, workflow metadata,
and completed-run evidence by resolving canonical application services and
`WorkflowFacade` through Dishka request scopes. MCP must not become a second RAG,
persistence, workflow, provider, or approval implementation. Its detailed
transport contract is documented in
[`mcp-server-transport-boundary.md`](mcp-server-transport-boundary.md).

HTTP API and UI implementation trees are not part of the current repository
topology. API, scheduler, and UI surfaces are not production interfaces until
their transport, request-scope lifecycle, persistence, security, and governance
contracts are intentionally implemented.

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
uv run polaris inspect persistence
```

`alembic current` validates the version stamp only. If local development has
rewritten the pre-1.0 squashed baseline and the physical schema is disposable,
reset and reapply the schema with:

```bash
uv run python scripts/reset_local_postgres_schema.py --confirm-destroy-local-db
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
| RAG ingestion, retrieval, or projection rebuild | See `platform-native-rag-retrieval-pipeline.md`; service requirements may include PostgreSQL, Qdrant, Neo4j, BGE reranker, and configured model/provider endpoints |

Use a timeout that reflects the expected operation duration. If an operation
times out, investigate service readiness or a blocked dependency before simply
raising the limit.

## Repository structure and architectural ownership

The repository layout follows the same inside-out boundaries:

| Path | Architectural role |
| --- | --- |
| `application/` | Use-case services, persistence orchestration, reporting, and RAG application services. |
| `automation/` | Automation support around platform workflows and operations. |
| `config/` | Settings and configuration. |
| `core/` | Runtime, workflow, database, storage, telemetry, plugins, policy, and governance contracts. |
| `domain/` | Typed business models and domain contracts. |
| `integration/` | External clients, providers, and simulated providers. |
| `intelligence/` | Analyst, risk, strategy, portfolio, research, and execution-safety components. |
| `interfaces/` | CLI plus non-production API scaffolding. |
| `mcp_server/` | Implemented thin MCP transport over canonical services and workflow facade. |
| `migrations/` | Alembic database migrations. |
| `tests/` | Unit, integration, database, architecture, contract, and coverage tests. |
| `web/` | Web-layer scaffolding and assets. |
| `workflows/` | Workflow definitions and catalog/bootstrap registration. |
| `docs/` | Accepted ADRs, current/proposed architecture documents, process documents, research, and references. |

This structure is descriptive, not a license to infer authority from folders
alone. Authority follows accepted ADRs, current architecture documents, code,
configuration, executable checks, and relevant tests.

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
