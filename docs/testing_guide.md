# Polaris Testing Guide

This guide summarizes the Polaris test suite, when to run each group, and which
checks require local Docker services. It intentionally describes test categories
and verification intent rather than listing every test file.

## Quick reference

| Goal | Recommended command | External services |
| --- | --- | --- |
| Fast local regression for most code changes | `uv run pytest -q tests/unit` | None |
| Runtime/workflow behavior with in-process fakes | `uv run pytest -q tests/integration/runtime tests/integration/workflow` | None for the default fake-backed tests |
| Persistence contracts without a live database | `uv run pytest -q tests/unit/core/storage/persistence tests/unit/application/persistence` | None |
| PostgreSQL repository and migration validation | `uv run pytest -q tests/database tests/integration/core/storage/persistence` | PostgreSQL and `POLARIS_TEST_DATABASE_URL` |
| RAG unit and boundary behavior | `uv run pytest -q tests/unit/application/rag tests/unit/integration/providers/rag tests/unit/integration/clients/rag` | None |
| Live RAG projection and reranker checks | `uv run pytest -q tests/integration/rag` | Qdrant, Neo4j, and/or BGE reranker depending on file |
| Observability contracts without live infrastructure | `uv run pytest -q tests/unit/telemetry tests/integration/telemetry/test_bootstrap_observability.py tests/integration/telemetry/test_opentelemetry_sink.py` | None |
| Live trace topology parity | `uv run pytest -q tests/integration/telemetry/test_live_trace_topology.py` | PostgreSQL, Jaeger/OTLP endpoint, and required env vars |
| CLI contract checks | `uv run pytest -q tests/unit/interfaces/cli` | None |
| MCP transport/tool boundary checks | `uv run pytest -q tests/unit/mcp_server tests/integration/mcp_server` | None for the current mocked transport contracts |
| Deterministic backtesting behavior | `uv run pytest -q tests/unit/application/services/backtesting tests/unit/integration/providers/backtesting tests/integration/backtesting` | None unless a future historical-provider test opts into PostgreSQL |
| Property-based runtime/model invariants | `uv run pytest -q tests/property` | None |
| End-to-end fake workflows | `uv run pytest -q tests/e2e` | None for the current fake/plugin workflow checks |
| Coverage gate | `uv run pytest --cov` | Depends on included tests; use service env vars only when intentionally running live checks |

## Standard verification workflow

For meaningful Python changes, use the project standard sequence:

```bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy . --explicit-package-bases
uv run pytest <focused-test-scope>
```

Then expand to broader test scopes when the blast radius warrants it. After
meaningful Python architecture changes, update the local code graph:

```bash
uv run graphify update .
```

The project currently selects tests by path rather than custom pytest markers.
Use focused paths to avoid accidentally waiting on live services that are not
needed for the change under review.

## Test suite structure

### Unit tests: `tests/unit/`

Unit tests validate one component or boundary at a time with fakes, in-memory
repositories, mocked clients, or deterministic fixtures. They should be the
first stop for most changes.

Important unit areas:

- `tests/unit/application/services/` — service-runner behavior, technical,
  portfolio, and backtesting service contracts.
- `tests/unit/application/persistence/` — application persistence services over
  repository protocols.
- `tests/unit/application/projections/` — workflow-output-to-curated-record
  projection eligibility, identity, projectors, registry, subscriber, and
  operations.
- `tests/unit/application/rag/` — RAG service graph, retrieval, routing,
  quality, security, chunk/source loading, projection, operations, and package
  boundary contracts.
- `tests/unit/core/database/` — SQLAlchemy model shape, settings, model coverage,
  and persistence table contracts. These are model-level tests and do not need a
  live database.
- `tests/unit/core/storage/persistence/` — repository contracts, serializers,
  idempotency, readiness, and in-memory/PostgreSQL repository construction
  behavior with fake sessions.
- `tests/unit/core/runtime/` and `tests/unit/runtime/` — runtime context,
  node-output, event-bus, control, policy, governance, and runtime-engine
  behavior.
- `tests/unit/integration/clients/` and `tests/unit/integration/providers/` —
  vendor client/provider boundary behavior with mocked transports.
- `tests/unit/intelligence/` — analyst, risk, portfolio, strategy hypothesis,
  recommendation, and execution-risk logic.
- `tests/unit/interfaces/cli/` — Typer command and renderer contracts with
  mocked command services.
- `tests/unit/mcp_server/` — MCP auth, settings, transport, tool allowlist, and
  typed tool contracts.
- `tests/unit/telemetry/` — telemetry emitters, context, sanitization, metrics,
  OpenTelemetry config, and Prometheus exporter behavior.

Run all unit tests with:

```bash
uv run pytest -q tests/unit
```

### Integration tests: `tests/integration/`

Integration tests validate collaboration between real in-process platform
components. Most are still fake-backed and do not require Docker, but persistence
and live RAG tests intentionally cross process boundaries.

Key groups:

- `tests/integration/application/persistence/` — application persistence services
  using fake repositories; no Docker required.
- `tests/integration/core/storage/persistence/` — live PostgreSQL repository and
  persistence integration; requires PostgreSQL and `POLARIS_TEST_DATABASE_URL`.
- `tests/integration/dishka/` — request/session scope behavior and scoped runtime
  node composition; no Docker required.
- `tests/integration/governance/` and `tests/integration/policies/` — workflow,
  plugin, governance, policy, and telemetry interactions; no Docker required.
- `tests/integration/plugins/` — plugin discovery, lifecycle, telemetry, and
  workflow loading; no Docker required.
- `tests/integration/rag/` — live Qdrant, Neo4j, and BGE reranker checks; see the
  Docker matrix below.
- `tests/integration/runtime/` — runtime artifacts, checkpoint/replay, lifecycle
  telemetry, control, cancel, pause/resume, and progress events; no Docker
  required unless a future test explicitly opts into PostgreSQL.
- `tests/integration/telemetry/` — observability integration; most use in-memory
  sinks/fakes, while `test_live_trace_topology.py` requires PostgreSQL and
  Jaeger/OTLP.
- `tests/integration/workflow/` — workflow bootstrap, provider control, disabled
  persistence behavior, and real-node morning-report wiring. These tests are
  written to avoid live vendor services by using test providers/fakes.
- `tests/integration/mcp_server/` — MCP transport contract behavior with mocked
  application services; no Docker required.

### Database migration tests: `tests/database/`

Database tests validate the Alembic migration timeline as a black box. They are
not filename-count tests. They verify that the upgraded schema matches SQLAlchemy
metadata and that targeted data migrations preserve expected state.

Requirements:

- PostgreSQL running.
- `POLARIS_TEST_DATABASE_URL` set to a local test database URL.
- Do not commit full authenticated connection strings; keep them in your shell or
  local `.env` only.

Run:

```bash
uv run pytest -q tests/database
```

### Property tests: `tests/property/`

Property tests validate broad invariants for checkpoint serialization, plugin
manifests, runtime context behavior, and workflow plans. They do not require
Docker.

Run:

```bash
uv run pytest -q tests/property
```

### End-to-end tests: `tests/e2e/`

Current end-to-end tests exercise fake/plugin workflows, replay, and resume
through the canonical runtime path. They are intended to validate that the
runtime and workflow layers cooperate correctly without depending on external
services.

Run:

```bash
uv run pytest -q tests/e2e
```

## Docker service matrix

Use Docker only when the selected test path needs a live service. Avoid running
live-service tests as part of a routine unit-test loop.

| Service | Compose service | Typical local endpoint | Required by |
| --- | --- | --- | --- |
| PostgreSQL | `postgres` | configured by `POLARIS_TEST_DATABASE_URL` | `tests/database`, `tests/integration/core/storage/persistence`, and live trace topology |
| Qdrant | `qdrant` | `http://localhost:6333` | `tests/integration/rag/test_qdrant_collection_lifecycle.py` |
| Neo4j | `neo4j` | Bolt on `localhost:7687`; browser on `http://localhost:7474` | `tests/integration/rag/test_neo4j_graph_projection.py` |
| BGE reranker | `bge-reranker` | `http://localhost:8080/rerank` by default | `tests/integration/rag/test_bge_reranker.py` |
| Jaeger / OTLP | `jaeger` | UI `http://localhost:16686`; OTLP endpoint from env | `tests/integration/telemetry/test_live_trace_topology.py` |
| Prometheus | `prometheus` | `http://localhost:9090` | Manual scrape/dashboard validation; current automated tests mostly use fakes/local exporters |
| Grafana | `grafana` | `http://localhost:3000` | Manual dashboard validation; not required by the current automated tests |

Start only the services you need:

```bash
# PostgreSQL persistence and migration tests
docker compose up -d postgres

# Live RAG projection checks
docker compose up -d qdrant neo4j bge-reranker

# Live trace topology and manual observability checks
docker compose up -d jaeger prometheus grafana
```

Confirm service status before running live tests:

```bash
docker compose ps postgres qdrant neo4j bge-reranker jaeger prometheus grafana
```

## Environment variables for guarded live tests

Some tests skip unless explicit environment variables are set. This is
intentional: live-service checks should be opt-in.

| Variable | Used by | Notes |
| --- | --- | --- |
| `POLARIS_TEST_DATABASE_URL` | `tests/database`, PostgreSQL persistence integration, live trace topology | Use a local test database. Keep credentials out of source, tests, docs, and plans. |
| `POLARIS_TEST_JAEGER_URL` | `tests/integration/telemetry/test_live_trace_topology.py` | Usually the Jaeger query/UI base URL, for example `http://localhost:16686`. |
| `POLARIS_TEST_OTEL_ENDPOINT` | `tests/integration/telemetry/test_live_trace_topology.py` | OTLP endpoint used by the test exporter. |

Example with redacted placeholders:

```bash
export POLARIS_TEST_DATABASE_URL="<async-postgresql-test-url>"
export POLARIS_TEST_JAEGER_URL="http://localhost:16686"
export POLARIS_TEST_OTEL_ENDPOINT="http://localhost:4317"
```

Do not paste real passwords or tokens into tracked files or shared command logs.

## What to run for common platform questions

### Did a runtime or workflow change preserve execution semantics?

```bash
uv run pytest -q \
  tests/unit/runtime \
  tests/unit/core/runtime \
  tests/integration/runtime \
  tests/integration/workflow
```

Use this when changing `RuntimeEngine`, `RuntimeContext`, workflow definitions,
workflow control, runtime events, replay/resume, or workflow bootstrap.

### Did workflow outputs still project into curated records correctly?

```bash
uv run pytest -q \
  tests/unit/application/projections \
  tests/unit/application/rag/test_workflow_output_projection_rag_compatibility.py
```

With PostgreSQL running and `POLARIS_TEST_DATABASE_URL` set, add:

```bash
uv run pytest -q tests/integration/core/storage/persistence/test_postgres_workflow_output_projection_integration.py
```

### Did persistence models, repositories, or migrations remain valid?

```bash
uv run pytest -q \
  tests/unit/core/database \
  tests/unit/core/storage/persistence \
  tests/unit/application/persistence
```

With PostgreSQL running and `POLARIS_TEST_DATABASE_URL` set, add:

```bash
uv run pytest -q tests/database tests/integration/core/storage/persistence
```

### Did the RAG pipeline remain correct without live services?

```bash
uv run pytest -q \
  tests/unit/application/rag \
  tests/unit/integration/providers/rag \
  tests/unit/integration/clients/rag \
  tests/unit/interfaces/cli/test_rag_command.py \
  tests/unit/intelligence/research/test_rag_research_node.py
```

### Did live RAG infrastructure work?

Start the required services, then run only the relevant live check:

```bash
# Qdrant collection lifecycle
uv run pytest -q tests/integration/rag/test_qdrant_collection_lifecycle.py

# Neo4j graph projection
uv run pytest -q tests/integration/rag/test_neo4j_graph_projection.py

# BGE reranker ordering
uv run pytest -q tests/integration/rag/test_bge_reranker.py
```

`test_qdrant_collection_lifecycle.py` and `test_bge_reranker.py` skip when their
service is unavailable. The Neo4j projection test expects Neo4j to be available;
start Neo4j before running it.

### Did CLI output or command wiring remain stable?

```bash
uv run pytest -q tests/unit/interfaces/cli
```

For RAG CLI behavior specifically:

```bash
uv run pytest -q tests/unit/interfaces/cli/test_rag_command.py
```

### Did MCP transport remain a thin boundary over application services?

```bash
uv run pytest -q tests/unit/mcp_server tests/integration/mcp_server
```

These tests use mocked service boundaries and do not require a live MCP host or
RAG datastore.

### Did telemetry and observability remain correct?

```bash
uv run pytest -q \
  tests/unit/telemetry \
  tests/unit/core/telemetry \
  tests/integration/telemetry/test_bootstrap_observability.py \
  tests/integration/telemetry/test_canonical_span_lifecycle_contract.py \
  tests/integration/telemetry/test_core_telemetry_baseline.py \
  tests/integration/telemetry/test_observability_pipeline.py \
  tests/integration/telemetry/test_opentelemetry_sink.py \
  tests/integration/telemetry/test_telemetry_coverage_audit.py
```

For live Jaeger/PostgreSQL parity, start PostgreSQL and Jaeger, set the three
live trace env vars, then run:

```bash
uv run pytest -q tests/integration/telemetry/test_live_trace_topology.py
```

### Did deterministic backtesting remain valid?

```bash
uv run pytest -q \
  tests/unit/application/services/backtesting \
  tests/unit/integration/providers/backtesting \
  tests/integration/backtesting
```

Use this after touching simulated providers, ledger logic, backtest service
contracts, deterministic scenario verification, or backtest reporting.

### Did strategy, portfolio, risk, or analyst intelligence change correctly?

```bash
uv run pytest -q tests/unit/intelligence
```

For focused strategy-hypothesis changes:

```bash
uv run pytest -q tests/unit/intelligence/strategy
```

### Did provider/client boundary changes preserve contracts?

```bash
uv run pytest -q tests/unit/integration/clients tests/unit/integration/providers
```

Use this after touching vendor-specific clients, providers, provider telemetry,
rate-limit/retry behavior, or fake/simulated providers.

## Coverage

Coverage configuration lives in `pyproject.toml` under `[tool.coverage.*]`. The
current report target is 75 percent.

Run coverage locally with:

```bash
uv run pytest --cov
```

For a faster coverage signal while developing, run coverage against the affected
package and its tests first, then expand to the full suite before release or
large merges.

## Operational guidance

- Prefer focused test paths first; expand only after the focused contract passes.
- Notify collaborators before running live-service tests that require Docker.
- Confirm services are healthy before running tests that will otherwise wait on
  network timeouts.
- Use reasonable command timeouts based on expected duration.
- Keep live connection strings, passwords, and tokens in local shell state or
  ignored environment files only.
- If a live test is not required for the change, do not run it merely because a
  service might be available.
- Treat PostgreSQL as the authoritative system of record. Qdrant, Neo4j,
  rendered files, and dashboards are projections or artifacts.
