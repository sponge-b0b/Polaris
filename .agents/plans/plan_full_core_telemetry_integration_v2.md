  # Core Telemetry Integration V2 Plan

  ## Summary

  Core Telemetry V2 will connect the now-internal telemetry/logging/metrics/tracing stack to local external observability infrastructure:

  - Prometheus for metrics scraping.
  - Jaeger for distributed traces via OTLP.
  - Grafana for dashboards backed by Prometheus and Jaeger.
  - PostgreSQL telemetry retention/volume controls with a default 30-day hot retention policy.

  The implementation should update .agent/plans/plan_full_core_telemetry_integration_v2.md first, then execute the plan one step at a time with step results appended.

  ## Implementation Changes

  ### 1. External observability infrastructure

  - Fix the existing docker-compose.yml telemetry services so they use repo-owned config files:
      - deployment/prometheus/prometheus.yml
      - deployment/grafana/provisioning/datasources/*.yml
      - deployment/grafana/provisioning/dashboards/*.yml
      - deployment/grafana/dashboards/*.json

  - Keep local developer defaults:
      - Prometheus: http://localhost:9090
      - Jaeger: http://localhost:16686
      - Grafana: http://localhost:3000
      - OTLP gRPC endpoint: http://localhost:4317

  - Add Grafana datasources for:
      - Prometheus
      - Jaeger

  - Add initial dashboards for:
      - workflow executions
      - runtime node success/failure counts
      - provider call latency/failure rate
      - telemetry event volume
      - PostgreSQL telemetry retention/deletion volume

  ### 2. Native Prometheus metrics exporter

  - Add a Prometheus integration under core/telemetry/integrations/prometheus/.
  - Add typed config, likely:
      - PrometheusMetricsConfig
      - PrometheusMetricsExporter

  - Add dependency only if needed:
      - prometheus-client

  - Extend WorkflowBootstrapConfig with:
      - enable_prometheus_metrics: bool = False
      - prometheus_metrics_host: str = "0.0.0.0"
      - prometheus_metrics_port: int = 9464
      - prometheus_metrics_path: str = "/metrics"

  - Wire the exporter through WorkflowBootstrap and Dishka provider wiring.
  - Export metrics from ObservabilityManager.metrics_store without using high-cardinality labels from raw payloads.
  - Label policy:
      - allow: source, event_type, level, workflow_name, node_name, provider_name, operation, success
      - avoid: raw payloads, symbols by default, full execution IDs as Prometheus labels unless explicitly allowlisted later

  ### 3. Jaeger/OpenTelemetry hardening

  - Keep the existing OpenTelemetrySink as the tracing bridge.
  - Add environment-backed config helpers for OTLP settings:
      - service name
      - service version
      - environment
      - OTLP endpoint
      - insecure flag

  - Ensure local Compose defaults work with Jaeger:
      - app outside Docker uses http://localhost:4317
      - app inside Docker can use http://jaeger:4317

  - Add shutdown/flush handling so spans are flushed during workflow teardown and tests.

  ### 4. PostgreSQL telemetry retention and volume policy

  - Reuse the existing retention architecture instead of creating a parallel lifecycle system.
  - Add telemetry-specific retention configuration:
      - default hot retention: 30 days
      - batch size: 5,000 rows
      - dry-run supported
      - deletion disabled unless explicitly invoked by the retention service/command

  - Add typed telemetry retention service behavior:
      - plan expired records by telemetry table and timestamp column
      - purge expired records in bounded batches
      - emit telemetry about retention runs
      - record summary counts by table/domain

  - Apply retention to:
      - telemetry_events
      - telemetry_metrics
      - telemetry_traces
      - workflow_metrics
      - agent_metrics
      - provider_metrics

  - Add retention metrics:
      - telemetry.retention.records_scanned
      - telemetry.retention.records_deleted
      - telemetry.retention.duration_seconds
      - telemetry.retention.errors

  ### 5. Developer validation workflow

  - Add or update docs with local run instructions:
      - start services with Docker Compose
      - run a workflow with OpenTelemetry and Prometheus enabled
      - open Prometheus, Jaeger, and Grafana
  - Keep V2 local-first; production/Kubernetes manifests are deferred.

  ## Public Interfaces / Config Additions

  - WorkflowBootstrapConfig
      - add Prometheus exporter flags and bind settings

  - OpenTelemetryConfig
      - add environment loading helper

  - New telemetry Prometheus integration package
      - exposes typed config and exporter

  - New PostgreSQL telemetry retention service/config
      - supports dry-run planning and bounded deletion

  ## Test Plan

  - Unit tests:
      - Prometheus config defaults and validation
      - metrics name/label normalization
      - high-cardinality label filtering
      - OpenTelemetry environment config loading
      - telemetry retention cutoff calculation
      - telemetry retention dry-run and bounded purge behavior

  - Integration tests:
      - WorkflowBootstrap wires Prometheus exporter only when enabled
      - WorkflowBootstrap still leaves Prometheus disabled by default
      - OpenTelemetry sink still emits spans with workflow/runtime trace attributes
      - retention service deletes only expired telemetry rows
      - retention service emits retention metrics/events

  - Infrastructure validation:
      - docker compose config
      - Prometheus config parse check if available
      - Grafana provisioning files are valid YAML/JSON

  - Standard verification:
      - uv run ruff check ... --fix
      - uv run ruff format ...
      - uv run mypy ... --explicit-package-bases
      - targeted pytest suites
      - uv run graphify update .

  ## Assumptions and Defaults

  - Optimize V2 for local Docker Compose observability first.
  - Use native /metrics Prometheus scraping in V2.
  - Default PostgreSQL telemetry retention is 30 days.
  - PostgreSQL remains the system-of-record for curated telemetry history, but high-volume operational metrics should be primarily observed through Prometheus/Grafana.
  - No automatic destructive retention job should run by default; deletion requires explicit retention service execution.
  - Production deployment manifests are out of scope for this V2 pass.

## Step Results

### Step 1 — External observability infrastructure

Completed.

Changes made:
- Updated `docker-compose.yml` so Prometheus uses `deployment/prometheus/prometheus.yml`.
- Added Prometheus `host.docker.internal:9464` scrape target for the upcoming native Polaris `/metrics` exporter.
- Added Grafana provisioning for Prometheus and Jaeger datasources.
- Added Grafana dashboard provisioning.
- Added initial `Polaris Core Telemetry Overview` dashboard covering workflow executions, runtime node results, provider latency/calls, telemetry event volume, and PostgreSQL telemetry retention volume.

Validation:
- Parsed `docker-compose.yml` as YAML successfully.
- Parsed Prometheus and Grafana provisioning YAML successfully.
- Parsed Grafana dashboard JSON successfully.
- Ran `docker compose config --quiet` successfully.


### Step 2 — Native Prometheus metrics exporter

Completed.

Changes made:
- Added native Prometheus integration package under `core/telemetry/integrations/prometheus/`.
- Added `PrometheusMetricsConfig` with typed defaults for host, port, scrape path, label allowlist, and histogram buckets.
- Added `PrometheusMetricsExporter` using the standard Prometheus text exposition format without adding a new dependency.
- Exporter renders metrics from `ObservabilityManager.metrics_store` / `MetricsStore`.
- Added metric-name normalization from dotted internal metric names to Prometheus-compatible names, for example `provider.call.duration_seconds` → `provider_call_duration_seconds`.
- Added constrained label allowlist for `source`, `event_type`, `level`, `workflow_name`, `node_name`, `provider_name`, `operation`, and `success`.
- Intentionally excluded high-cardinality labels such as raw payloads, symbols, and execution IDs.
- Added Prometheus histogram output with `_bucket`, `_count`, and `_sum` series.
- Extended `WorkflowBootstrapConfig` with Prometheus exporter flags and bind settings.
- Wired Prometheus exporter startup through `WorkflowBootstrap` when explicitly enabled.
- Wired Prometheus exporter startup through `WorkflowInfrastructureProvider` when explicitly enabled.
- Kept Prometheus exporter disabled by default.

Validation:
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/telemetry/test_prometheus_metrics_exporter.py tests/integration/telemetry/test_bootstrap_observability.py` — passed, `18 passed`.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check core/telemetry/integrations/prometheus core/workflow/bootstrap/workflow_bootstrap.py core/bootstrap/workflow_providers.py tests/unit/telemetry/test_prometheus_metrics_exporter.py tests/integration/telemetry/test_bootstrap_observability.py --fix` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format core/telemetry/integrations/prometheus core/workflow/bootstrap/workflow_bootstrap.py core/bootstrap/workflow_providers.py tests/unit/telemetry/test_prometheus_metrics_exporter.py tests/integration/telemetry/test_bootstrap_observability.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/telemetry/integrations/prometheus core/workflow/bootstrap/workflow_bootstrap.py core/bootstrap/workflow_providers.py tests/unit/telemetry/test_prometheus_metrics_exporter.py tests/integration/telemetry/test_bootstrap_observability.py --explicit-package-bases` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` — passed.

Notes:
- The first sandboxed pytest run failed because the sandbox blocked binding a local loopback socket. The same targeted test command passed after allowing the local ephemeral socket needed by the exporter HTTP test.

### Step 3 — Jaeger/OpenTelemetry hardening

Completed.

Changes made:
- Added environment-backed OpenTelemetry configuration via `OpenTelemetryConfig.from_env()`.
- Added local Compose endpoint helper via `OpenTelemetryConfig.for_local_compose(app_inside_docker=...)`.
- Supported Polaris-specific environment variables with standard OpenTelemetry fallbacks:
  - `POLARIS_OTEL_SERVICE_NAME` / `OTEL_SERVICE_NAME`
  - `POLARIS_OTEL_SERVICE_VERSION` / `OTEL_SERVICE_VERSION`
  - `POLARIS_OTEL_ENVIRONMENT` / `OTEL_ENVIRONMENT`
  - `POLARIS_OTEL_OTLP_ENDPOINT` / `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` / `OTEL_EXPORTER_OTLP_ENDPOINT`
  - `POLARIS_OTEL_INSECURE` / `OTEL_EXPORTER_OTLP_INSECURE`
  - `POLARIS_OTEL_ENABLE_TRACING`
  - `POLARIS_OTEL_ENABLE_METRICS`
  - `POLARIS_OTEL_ENABLE_CONSOLE_EXPORT`
- Updated `WorkflowBootstrap` and `WorkflowInfrastructureProvider` to use environment-backed OpenTelemetry config when no explicit config is injected.
- Added idempotent `OpenTelemetrySink.shutdown()` handling and safe no-op `force_flush()` after shutdown.
- Added telemetry lifecycle methods to `TelemetryCollector` and `ObservabilityManager`.
- Added `WorkflowBootstrapResult.force_flush_telemetry()` and `WorkflowBootstrapResult.shutdown_telemetry()` to flush/shutdown observability components from the bootstrap boundary.
- Ensured `shutdown_telemetry()` stops the native Prometheus exporter and shuts down OpenTelemetry sinks.
- Added unit tests for OpenTelemetry env config loading and local Compose endpoint defaults.
- Added integration tests for OpenTelemetry sink flush/shutdown lifecycle and bootstrap env-backed OpenTelemetry wiring.

Validation:
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/telemetry/test_opentelemetry_config.py tests/integration/telemetry/test_opentelemetry_sink.py tests/integration/telemetry/test_bootstrap_observability.py` — passed, `22 passed`.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check core/telemetry/integrations/opentelemetry core/telemetry/collectors/telemetry_collector.py core/telemetry/observability/observability_manager.py core/workflow/bootstrap/workflow_bootstrap.py core/bootstrap/workflow_providers.py tests/unit/telemetry/test_opentelemetry_config.py tests/integration/telemetry/test_opentelemetry_sink.py tests/integration/telemetry/test_bootstrap_observability.py --fix` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format core/telemetry/integrations/opentelemetry core/telemetry/collectors/telemetry_collector.py core/telemetry/observability/observability_manager.py core/workflow/bootstrap/workflow_bootstrap.py core/bootstrap/workflow_providers.py tests/unit/telemetry/test_opentelemetry_config.py tests/integration/telemetry/test_opentelemetry_sink.py tests/integration/telemetry/test_bootstrap_observability.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/telemetry/integrations/opentelemetry core/telemetry/collectors/telemetry_collector.py core/telemetry/observability/observability_manager.py core/workflow/bootstrap/workflow_bootstrap.py core/bootstrap/workflow_providers.py tests/unit/telemetry/test_opentelemetry_config.py tests/integration/telemetry/test_opentelemetry_sink.py tests/integration/telemetry/test_bootstrap_observability.py --explicit-package-bases` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` — passed.

Notes:
- Local Compose defaults are `http://localhost:4317` for the app running outside Docker and `http://jaeger:4317` for the app running inside Docker.
- Bootstrap tests exercise local loopback sockets for the Prometheus exporter and therefore required the already-approved sandbox escalation path.

### Step 4 — PostgreSQL telemetry retention and volume policy

Completed.

Changes made:
- Added `TelemetryRetentionConfig` with typed defaults:
  - `retention_days=30`
  - `batch_size=5000`
  - `max_batches=1`
- Added `TelemetryRetentionService` under the existing `application.persistence.retention` package instead of creating a parallel lifecycle system.
- Added dry-run planning through `TelemetryRetentionService.plan_expired()`.
- Added explicit bounded deletion through `TelemetryRetentionService.purge_expired(dry_run=False)`.
- Kept deletion disabled by default because `purge_expired()` defaults to `dry_run=True`.
- Added per-table typed summaries through `TelemetryRetentionTableSummary`.
- Added typed run result through `TelemetryRetentionRunResult`.
- Applied retention coverage to the canonical PostgreSQL telemetry tables:
  - `telemetry_events` using `timestamp`
  - `telemetry_metrics` using `timestamp`
  - `telemetry_traces` using `started_at`
  - `workflow_metrics` using `timestamp`
  - `agent_metrics` using `timestamp`
  - `provider_metrics` using `timestamp`
- Added rollback/error reporting behavior for SQLAlchemy failures.
- Added retention telemetry emission through `ObservabilityManager` metrics/events:
  - `telemetry.retention.records_scanned`
  - `telemetry.retention.records_deleted`
  - `telemetry.retention.duration_seconds`
  - `telemetry.retention.errors`
  - `telemetry.retention.completed`
  - `telemetry.retention.failed`
- Exported telemetry retention contracts from `application.persistence.retention` and `application.persistence`.
- Added unit tests for dry-run planning, explicit purge behavior, rollback handling, observability metrics, and config validation.

Validation:
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/persistence/retention/test_retention_persistence_service.py tests/unit/application/persistence/retention/test_telemetry_retention_service.py` — passed, `12 passed`.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/persistence/retention application/persistence/__init__.py tests/unit/application/persistence/retention/test_telemetry_retention_service.py --fix` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format application/persistence/retention application/persistence/__init__.py tests/unit/application/persistence/retention/test_telemetry_retention_service.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy application/persistence/retention application/persistence/__init__.py tests/unit/application/persistence/retention/test_telemetry_retention_service.py --explicit-package-bases` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` — passed.

Notes:
- This step intentionally does not schedule automatic deletion. The retention service must be invoked explicitly, and callers must pass `dry_run=False` before records are physically deleted.
- Each purge invocation is bounded by `batch_size * max_batches` per table to avoid unbounded telemetry deletion work.

### Step 5 — Developer validation workflow

Completed.

Changes made:
- Added local Core Telemetry V2 validation documentation in `.docs/core_telemetry_observability.md`.
- Documented how to start local Jaeger, Prometheus, and Grafana with Docker Compose.
- Documented CLI workflow execution with external observability enabled through environment-backed bootstrap flags:
  - `POLARIS_ENABLE_OBSERVABILITY`
  - `POLARIS_ENABLE_OPENTELEMETRY`
  - `POLARIS_ENABLE_PROMETHEUS_METRICS`
  - `POLARIS_PROMETHEUS_METRICS_HOST`
  - `POLARIS_PROMETHEUS_METRICS_PORT`
  - `POLARIS_PROMETHEUS_METRICS_PATH`
- Added a local telemetry smoke-test snippet that keeps Polaris's process-local `/metrics` exporter alive long enough for Prometheus scrapes and emits representative workflow/runtime/provider metrics.
- Documented Prometheus, Jaeger, and Grafana local URLs, useful Prometheus queries, and Grafana dashboard/datasource names.
- Documented the V2 telemetry retention policy reminder: 30-day default hot retention, no automatic deletion, and explicit `dry_run=False` required for destructive purges.
- Added a README pointer to `.docs/core_telemetry_observability.md`.
- Added CLI bootstrap environment wiring so `polaris morning-report` and `polaris workflow run morning_report` can run with OpenTelemetry and Prometheus enabled without adding new CLI flags.
- Added unit coverage for CLI telemetry environment settings and WorkflowBootstrapConfig mapping.

Validation:
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check interfaces/cli/bootstrap/settings.py interfaces/cli/bootstrap/container.py tests/unit/interfaces/cli/test_cli_bootstrap_settings.py --fix` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format interfaces/cli/bootstrap/settings.py interfaces/cli/bootstrap/container.py tests/unit/interfaces/cli/test_cli_bootstrap_settings.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/interfaces/cli/test_cli_bootstrap_settings.py` — passed, `5 passed`.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/interfaces/cli/test_workflow_command_service.py tests/unit/interfaces/cli/test_cli_bootstrap_settings.py` — passed, `10 passed`.
- `UV_CACHE_DIR=/tmp/uv-cache uv run mypy interfaces/cli/bootstrap/settings.py interfaces/cli/bootstrap/container.py tests/unit/interfaces/cli/test_cli_bootstrap_settings.py --explicit-package-bases` — passed.
- `docker compose config --quiet` — passed.
- Documentation smoke check verified the observability guide exists, is linked from README, and includes the required service startup, workflow execution, and UI instructions.
- `UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` — passed.

Notes:
- Prometheus metrics are process-local; the CLI exporter is available while the Polaris process is running. The documentation includes a developer validation snippet for short smoke tests where the exporter needs to stay alive for Prometheus scraping.
- Production deployment manifests remain intentionally out of scope for V2.
