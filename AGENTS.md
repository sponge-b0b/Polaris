# AGENTS.md

## Purpose and Authority

These are the operating rules for coding agents working on Polaris.

At the start of a session:

1. Read `CONTEXT.md` for the current platform map and architectural status.
2. Read `.claude/CLAUDE.md` for the Repowise-generated system map.
3. Verify implementation claims against current source and tests; generated maps may lag the repository.
4. Merge these rules with any narrower user instruction for the active task.

`AGENTS.md` is prescriptive. `CONTEXT.md` is descriptive. Avoid duplicating detailed architecture between them.

## Architectural Investigation

Before modifying any state, execution result, database schema, or persistence layer, you must invoke the `.agents/skills/architectural-investigation` skill. This ensures a surgical implementation scope, traces complete data lifecycles, and strictly protects single-source-of-truth invariants across the platform.

## Non-Negotiable Architecture

### Inside-out design

The runtime is the trunk; application, integration, intelligence, portfolio, strategy, recommendation, and interface code are branches.

- Protect stable core contracts.
- Refactor edge code directly to current contracts.
- Do not add compatibility wrappers or legacy adapters unless explicitly approved with a removal plan.
- Do not modify `core/` without user authorization. If a core change is architecturally necessary, explain why and obtain approval first.

### Runtime and workflow boundaries

- `RuntimeEngine` owns execution.
- `WorkflowFacade` is the application workflow boundary.
- `WorkflowBootstrap` is the workflow composition root.
- New workflow capabilities must use `RuntimeNode` and the canonical graph/runtime path.
- Do not create parallel runtimes or bypass the facade/bootstrap.
- `RuntimeContext` and `RuntimeNodeOutput` contain workflow evidence; do not recreate competing runtime business-state aggregates.

### Workflow control and events

- `WorkflowControlManager` owns pause, resume, and cancel state.
- The runtime checks control state cooperatively at safe boundaries.
- `WorkflowFacade` exposes control APIs.
- `EventBus` and typed `RuntimeEvent` objects are the canonical notification path.
- Telemetry maps runtime events at the boundary.
- Do not mutate runtime state directly from CLI or application code.

### Dependency injection

Use Dishka with explicit constructor dependencies.

- Long-lived infrastructure belongs in application scope.
- Each command, request, or future MCP invocation owns a request scope.
- Do not use globals, service locators, hidden dependencies, or split-brain `EventBus`, control, telemetry, persistence, or facade instances.

### Layering

External access must follow:

```text
Application service
→ provider
→ vendor-specific async client
→ external system
```

- Clients own transport, authentication, retries, pagination, rate limits, timeouts, and raw parsing.
- Providers normalize vendor data into stable platform contracts.
- Application services coordinate use cases.
- Intelligence consumes typed service results.
- Agents must never call vendor SDKs directly.
- Intelligence components must not contain transport logic.

### Persistence and projections

- PostgreSQL is the authoritative durable system of record.
- SQLAlchemy models and Alembic migrations govern schema.
- Typed repositories and application persistence services own database access.
- Qdrant, Neo4j, files, caches, and rendered reports are projections or artifacts, not competing authorities.
- Projection rebuilds must not delete canonical PostgreSQL records.
- Workflow outputs become curated records only through an explicit typed eligibility and projection policy.
- Do not promote arbitrary metadata into durable schema; add first-class typed fields when the concept is canonical.

### RAG and MCP

- RAG orchestration belongs in canonical application services.
- PostgreSQL owns curated RAG records; Qdrant and Neo4j are rebuildable retrieval projections.
- Do not implement a second retrieval, ranking, graph, ingestion, or persistence stack in an interface.
- A future MCP server must be a thin external transport over Dishka-resolved application services. If behavior is missing, add it to the canonical service first.

### Backtesting

- Backtests use the production runtime, workflows, services, and contracts.
- Live versus simulated behavior is selected through provider composition.
- The runtime must remain unaware of execution mode.
- Deterministic scenarios require fixed inputs, time, seeds, and independently derived expected outcomes.

### Policy and governance

- Policy answers “May this happen?” with `ALLOW` or `DENY`.
- Governance answers “Should this happen?” with `ALLOW`, `WARN`, `DENY`, `REQUIRE_APPROVAL`, or `SKIP`.
- Governance operates above policy.
- Workflow and capability code must not bypass policy or governance evaluation.
- Do not claim a complete approval subsystem exists unless its contracts, persistence, interfaces, and tests are implemented.

## Data Contracts

### Typed internals

Prefer immutable typed models:

```python
@dataclass(frozen=True, slots=True)
class ExampleSignal:
    ...
```

Use typed requests, results, DTOs, domain records, signals, and runtime contracts inside the platform.

`dict[str, Any]` is acceptable only at boundaries such as:

- external APIs and vendor SDKs
- JSON and transport serialization
- telemetry and event serialization
- persistence, checkpoints, and replay serialization

Serialize typed objects only when crossing a boundary.

### Numeric precision

Never use `round()` in application, intelligence, analysis, regime, calibration, or persistence logic. Preserve full precision internally. Round only in CLI, Markdown, PDF, web, or other human-facing renderers.

### Python conventions

- Type all public interfaces.
- Prefer `@dataclass(frozen=True, slots=True)` for immutable models.
- Workflow definitions expose `workflow_name` and `workflow_description` as `@property` methods, not class attributes.
- Use async provider/client calls consistently; do not add sync/async compatibility branches without a real boundary requirement.

## Observability

Every meaningful operational boundary must be observable once, at its canonical owner.

Verify:

- structured logs for entry failures, retries, degradation, and caught exceptions
- active trace spans for external calls, datastore operations, LLM flows, and long-running work
- counters or histograms for latency, volume, success, and failure
- trace-context propagation through `asyncio` tasks, providers, runtime events, and persistence

Rules:

- External provider calls use the established telemetry wrapper, such as `record_provider_call()`.
- PostgreSQL, Qdrant, and Neo4j operations record latency and defensively log failures.
- Exception logs that diagnose failures include tracebacks.
- Telemetry failures remain non-fatal to valid domain results but must be visible.
- Do not emit duplicate lifecycle events from multiple layers.
- Reuse established emitter and span conventions; do not invent parallel telemetry systems.

## Secrets and Live Services

- Never place credentials, passwords, tokens, or full authenticated connection strings in source, tests, plans, or documentation.
- Tests use environment variables or redacted placeholders.
- Before running live-service tests, identify required services and notify the user.
- Do not wait for unavailable services to time out when the test is unnecessary.

## Authorized Docker Operations

These Docker operations are authorized when a required service must be managed:

```text
docker compose up -d [service ...]
docker compose stop [service ...]
docker compose restart [service ...]
docker compose down
```

Current local services may include PostgreSQL, Qdrant, Neo4j, BGE reranker, Prometheus, Jaeger, Grafana et-all.

## Dependencies and shell

Use:

- `uv run`
- `uv add`
- `uv remove`
- `uv sync`

Standard read-only discovery and diagnostic shell commands are allowed.

## Repository Analysis Tools

For structural dependency lookups or codebase architecture questions, invoke the `.agents/skills/using-graphify` skill. Do not attempt to manually open, read, or parse raw files inside `graphify-out/` during a standard session.

## Repository Analysis Tools

Before editing any Python files or changing code patterns, you must leverage the project's native discovery tool belt to map context, enforce safety guards, and isolate change blast radiuses.

- **For Structural Invariants & Code Dependency Maps:** Invoke the `.agents/skills/using-graphify` skill. Do not attempt to manually open, read, or parse raw files inside `graphify-out/` during a standard session.
- **For Behavioral Location, Code Health, and File Risk Auditing:** Invoke the `.agents/skills/using-repowise` skill. You must explicitly alert the user if Repowise flags a target implementation destination as a highly brittle or high-risk file hotspot before code edits begin.
