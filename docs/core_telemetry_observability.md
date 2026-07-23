# Core Telemetry V2 Local Observability

This guide validates the local Core Telemetry V2 stack:

- Prometheus scrapes Polaris's native `/metrics` endpoint.
- Jaeger receives OpenTelemetry spans through OTLP gRPC.
- Grafana loads repo-owned Prometheus and Jaeger datasources plus the initial Polaris dashboard.
- PostgreSQL remains the curated telemetry system-of-record; retention cleanup is explicit and bounded.

V2 is local-first. Production and Kubernetes manifests are intentionally deferred.

## PostgreSQL event and exception contract

PostgreSQL preserves each canonical telemetry event under its original `event_id`
and stores `trace_id` and `span_id` in first-class columns. Exception-bearing events
carry the sanitized typed exception snapshot in `payload.exception_details`; the
event message uses the explicit canonical event message when one exists and otherwise
falls back to the exception message. Before persistence or export, exception type,
message, and stack trace are bounded to 256, 4096, and 32768 characters respectively.
The same terminal exception is also promoted to first-class trace fields for querying
the assembled operation lifecycle.

## Risk and authority boundary observability

Risk and authority metadata is observed at the same owner boundary that makes or
persists the operational decision. Lower layers must attach to the existing
lifecycle event, trace, log, or metric from that owner instead of emitting a
second lifecycle event or reconstructing a parallel telemetry stream.

Canonical owner boundaries are:

- `WorkflowOutputProjectionService` / `WorkflowOutputProjectionTelemetry` for
  workflow-output curation eligibility, projector lifecycle, validation failures,
  and `prohibited_outside_authority` denials.
- Recommendation, RAG, and report application services for authority metadata
  persisted on their typed records, answers, report artifacts, and projection
  payloads.
- Governance services for policy/governance blocks and fail-closed decisions.
- `EvaluationRunService` / `EvaluationTelemetry` for evaluation gate profile
  selection, gate failures, and selected gate evidence.

At these boundaries, observable attributes use the shared flattened authority
vocabulary: risk tier, authority effect, owner, sink, source-of-truth category,
gate profile, stable observable reason, and correlation identifiers when the
boundary has them. Event payloads may include the nested `risk_authority` object
for diagnostics, while metric labels stay scalar and bounded. Telemetry remains
non-fatal; if emission or metric recording fails, the canonical telemetry owner
logs the diagnostic failure with a traceback and returns the valid domain result.

## 1. Start local observability services

From the repository root:

```bash
docker compose up -d jaeger prometheus grafana
```

Confirm the services are running:

```bash
docker compose ps jaeger prometheus grafana
```

Optional, when validating PostgreSQL telemetry persistence or retention locally:

```bash
docker compose up -d postgres
uv run alembic upgrade head
```

## 2. Enable telemetry for a Polaris workflow run

External observability is disabled by default. Enable it only for runs that should publish to local observability infrastructure:

```bash
export POLARIS_ENABLE_OBSERVABILITY=true
export POLARIS_ENABLE_OPENTELEMETRY=true
export POLARIS_ENABLE_PROMETHEUS_METRICS=true

export POLARIS_OTEL_SERVICE_NAME=polaris-runtime
export POLARIS_OTEL_SERVICE_VERSION=local
export POLARIS_OTEL_ENVIRONMENT=development
export POLARIS_OTEL_OTLP_ENDPOINT=http://localhost:4317
export POLARIS_OTEL_INSECURE=true

export POLARIS_PROMETHEUS_METRICS_HOST=0.0.0.0
export POLARIS_PROMETHEUS_METRICS_PORT=9464
export POLARIS_PROMETHEUS_METRICS_PATH=/metrics
```

Run a workflow through the CLI:

```bash
uv run polaris morning-report
```

Equivalent workflow command:

```bash
uv run polaris workflow run morning_report
```

Notes:

- The Prometheus exporter is process-local and is available only while the Polaris process is running.
- Prometheus scrapes `host.docker.internal:9464/metrics` from the Compose network.
- Jaeger receives spans at `http://localhost:4317` when Polaris runs on the host.
- If Polaris runs inside Docker, set `POLARIS_OTEL_OTLP_ENDPOINT=http://jaeger:4317` instead.

## 3. Keep the metrics endpoint alive for manual validation

For a fast smoke test, run this local validation process. It starts the same bootstrap-level telemetry components, emits representative workflow/runtime/provider metrics, and keeps `/metrics` alive long enough for Prometheus to scrape it.

```bash
POLARIS_ENABLE_OBSERVABILITY=true \
POLARIS_ENABLE_OPENTELEMETRY=true \
POLARIS_ENABLE_PROMETHEUS_METRICS=true \
POLARIS_OTEL_OTLP_ENDPOINT=http://localhost:4317 \
uv run python - <<'PY'
import asyncio

from core.telemetry.integrations.opentelemetry import OpenTelemetryConfig
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrap
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapConfig


async def main() -> None:
    runtime = WorkflowBootstrap(
        config=WorkflowBootstrapConfig(
            enable_observability=True,
            enable_opentelemetry=True,
            enable_prometheus_metrics=True,
            prometheus_metrics_host="0.0.0.0",
            prometheus_metrics_port=9464,
            prometheus_metrics_path="/metrics",
        ),
        opentelemetry_config=OpenTelemetryConfig.from_env(),
    ).build()

    observability = runtime.observability_manager
    trace_context = observability.create_trace_context(
        workflow_id="developer_validation",
        execution_id="developer_validation",
        node_name="telemetry_validation",
        attributes={
            "workflow_name": "developer_validation",
            "node_name": "telemetry_validation",
        },
    )

    await observability.info(
        event_type="workflow.execution.started",
        source="developer.validation",
        payload={"message": "local observability validation started"},
        attributes={"workflow_name": "developer_validation"},
        trace_context=trace_context,
    )
    observability.increment(
        "workflow.executions.total",
        attributes={"workflow_name": "developer_validation", "success": True},
    )
    observability.increment(
        "runtime.node.executions.total",
        attributes={"node_name": "telemetry_validation", "success": True},
    )
    observability.observe(
        "provider.call.duration_seconds",
        0.05,
        attributes={
            "provider_name": "developer_validation",
            "operation": "noop",
            "success": True,
        },
    )

    print("Polaris metrics are available at http://localhost:9464/metrics")
    print("Waiting 90 seconds for Prometheus to scrape. Press Ctrl+C to stop early.")
    try:
        await asyncio.sleep(90)
    finally:
        runtime.force_flush_telemetry()
        runtime.shutdown_telemetry()


asyncio.run(main())
PY
```

## 4. Open the observability tools

Prometheus:

- UI: <http://localhost:9090>
- Targets: <http://localhost:9090/targets>
- Useful queries:
  - `polaris_prometheus_exporter_up`
  - `telemetry_events_total`
  - `workflow_executions_total`
  - `runtime_nodes_total`
  - `integration_provider_duration_seconds_count`
  - `application_service_retries`
  - `application_service_degraded`
  - `integration_client_retries`
  - `telemetry_sink_failures`
  - `telemetry_retention_records_scanned`
  - `telemetry_retention_records_deleted`

Jaeger:

- UI: <http://localhost:16686>
- Service: `polaris-runtime` unless `POLARIS_OTEL_SERVICE_NAME` overrides it.

Grafana:

- UI: <http://localhost:3000>
- Login: `admin` / `admin`
- Dashboard: `Polaris Core Telemetry Overview`
- Datasources are provisioned automatically:
  - Prometheus: `http://prometheus:9090`
  - Jaeger: `http://jaeger:16686`

The dashboard uses the canonical metric families emitted by `DomainMetricsRecorder`; it does not reconstruct operational facts from logs or PostgreSQL. It includes workflow and node outcomes, provider latency, service retries/degradation, configuration failures, client retries, telemetry sink failures, and callback failures.

### Prometheus alert rules

Prometheus loads repository-owned rules from `deployment/prometheus/alerts.yml`. The rules cover:

- application-service and integration-client retry spikes;
- materially degraded service results;
- service and bootstrap configuration failures;
- telemetry sink failures;
- plugin, runtime lifecycle, and EventBus callback failures.

Prometheus labels are deliberately bounded to stable names such as `service_name`, `component_name`, `provider_name`, `operation`, `event_type`, `outcome`, and `success`. Request, event, trace, and span IDs; exception messages; URLs; symbols; and user input remain available in logs, traces, and PostgreSQL telemetry, but are never exported as metric labels.

Validate the repository-owned configuration without starting services:

```bash
docker compose config --quiet
uv run pytest -q tests/unit/telemetry/test_observability_deployment_config.py
```

## 5. Retention and volume policy reminder

Telemetry retention cleanup is never automatic in V2. The default hot retention policy is 30 days, but deletion requires an explicit retention service invocation with `dry_run=False`.

Retention metrics emitted by the service are exported to Prometheus when the native metrics exporter is enabled:

- `telemetry_retention_records_scanned`
- `telemetry_retention_records_deleted`
- `telemetry_retention_duration_seconds`
- `telemetry_retention_errors`

## 6. Stop local observability services

```bash
docker compose stop grafana prometheus jaeger
```

To remove local observability containers while keeping named volumes:

```bash
docker compose down
```
