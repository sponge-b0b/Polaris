from __future__ import annotations

import socket

from http import HTTPStatus
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from core.telemetry.integrations.prometheus import PrometheusMetricsConfig
from core.telemetry.integrations.prometheus import PrometheusMetricsExporter
from core.telemetry.metrics.metrics_store import MetricsStore


def _can_bind_loopback_socket() -> bool:
    try:
        with socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        ) as probe_socket:
            probe_socket.bind(
                (
                    "127.0.0.1",
                    0,
                )
            )
            return True
    except OSError:
        return False


def test_prometheus_metrics_config_defaults() -> None:
    config = PrometheusMetricsConfig()

    assert config.host == "0.0.0.0"
    assert config.port == 9464
    assert config.path == "/metrics"
    assert "source" in config.label_allowlist
    assert "execution_id" not in config.label_allowlist


def test_prometheus_metrics_config_validates_values() -> None:
    with pytest.raises(ValueError, match="host"):
        PrometheusMetricsConfig(host=" ")

    with pytest.raises(ValueError, match="port"):
        PrometheusMetricsConfig(port=70000)

    with pytest.raises(ValueError, match="path"):
        PrometheusMetricsConfig(path="metrics")

    with pytest.raises(ValueError, match="allowlist"):
        PrometheusMetricsConfig(label_allowlist=())

    with pytest.raises(ValueError, match="unsupported labels"):
        PrometheusMetricsConfig(label_allowlist=("source", "symbol"))

    with pytest.raises(ValueError, match="unsupported labels"):
        PrometheusMetricsConfig(label_allowlist=("source", "error_message"))

    with pytest.raises(ValueError, match="sorted"):
        PrometheusMetricsConfig(histogram_buckets=(1.0, 0.5))


def test_exporter_renders_metric_names_and_allowlisted_labels_only() -> None:
    store = MetricsStore()
    store.increment(
        name="telemetry.events.total",
        tags=("runtime", "info"),
        attributes={
            "event_type": "runtime.workflow.started",
            "execution_id": "high-cardinality-id",
            "symbol": "AAPL",
            "payload": {"raw": True},
        },
    )

    rendered = PrometheusMetricsExporter(metrics_store=store).render()

    assert "# TYPE telemetry_events_total counter" in rendered
    assert (
        'telemetry_events_total{event_type="runtime.workflow.started",'
        'level="info",source="runtime"} 1.0'
    ) in rendered
    assert "execution_id" not in rendered
    assert "symbol" not in rendered
    assert "payload" not in rendered


def test_exporter_renders_latest_gauge_value() -> None:
    store = MetricsStore()
    attributes = {
        "workflow_name": "morning_report",
    }
    store.gauge(
        name="workflow.active",
        value=1.0,
        attributes=attributes,
    )
    store.gauge(
        name="workflow.active",
        value=0.0,
        attributes=attributes,
    )

    rendered = PrometheusMetricsExporter(metrics_store=store).render()

    assert "# TYPE workflow_active gauge" in rendered
    assert 'workflow_active{workflow_name="morning_report"} 0.0' in rendered
    assert 'workflow_active{workflow_name="morning_report"} 1.0' not in rendered


def test_exporter_renders_histogram_buckets() -> None:
    store = MetricsStore()
    attributes = {
        "provider_name": "yfinance",
        "operation": "history",
        "success": True,
    }
    store.observe(
        name="provider.call.duration_seconds",
        value=0.03,
        attributes=attributes,
    )
    store.observe(
        name="provider.call.duration_seconds",
        value=0.2,
        attributes=attributes,
    )

    rendered = PrometheusMetricsExporter(metrics_store=store).render()

    assert "# TYPE provider_call_duration_seconds histogram" in rendered
    assert (
        'provider_call_duration_seconds_bucket{operation="history",'
        'provider_name="yfinance",success="true",le="0.05"} 1.0'
    ) in rendered
    assert (
        'provider_call_duration_seconds_bucket{operation="history",'
        'provider_name="yfinance",success="true",le="+Inf"} 2.0'
    ) in rendered
    assert (
        'provider_call_duration_seconds_count{operation="history",'
        'provider_name="yfinance",success="true"} 2.0'
    ) in rendered
    assert (
        'provider_call_duration_seconds_sum{operation="history",'
        'provider_name="yfinance",success="true"} 0.23'
    ) in rendered


def test_exporter_serves_metrics_over_http() -> None:
    if not _can_bind_loopback_socket():
        pytest.skip(
            "local socket binding is unavailable in this test environment",
        )

    store = MetricsStore()
    store.increment(
        name="telemetry.events.total",
        attributes={
            "event_type": "test.event",
        },
    )
    exporter = PrometheusMetricsExporter(
        metrics_store=store,
        config=PrometheusMetricsConfig(
            host="127.0.0.1",
            port=0,
            path="/custom-metrics",
        ),
    )

    exporter.start()

    try:
        server_address = exporter.server_address
        assert server_address is not None
        host, port = server_address

        with urlopen(  # noqa: S310 - local ephemeral test server.
            f"http://{host}:{port}/custom-metrics",
            timeout=5.0,
        ) as response:
            body = response.read().decode("utf-8")
            assert response.status == HTTPStatus.OK

        assert "telemetry_events_total" in body

        with pytest.raises(HTTPError) as error:
            urlopen(  # noqa: S310 - local ephemeral test server.
                f"http://{host}:{port}/wrong-path",
                timeout=5.0,
            )

        assert error.value.code == HTTPStatus.NOT_FOUND

    finally:
        exporter.stop()

    assert exporter.running is False


def test_exporter_exposes_operational_metrics_with_bounded_labels() -> None:
    store = MetricsStore()
    store.increment(
        name="application.service.retries",
        attributes={
            "event_type": "application.service.retry_scheduled",
            "service_name": "TechnicalAnalysisService",
            "component_name": "ServiceRunner",
            "operation": "execute",
            "outcome": "retry_scheduled",
            "request_id": "request-123",
            "trace_id": "trace-123",
            "error_message": "private failure detail",
            "url": "https://example.invalid/private",
            "symbol": "AAPL",
        },
    )

    rendered = PrometheusMetricsExporter(metrics_store=store).render()

    assert "# TYPE application_service_retries counter" in rendered
    assert (
        'application_service_retries{component_name="ServiceRunner",'
        'event_type="application.service.retry_scheduled",operation="execute",'
        'outcome="retry_scheduled",service_name="TechnicalAnalysisService"} 1.0'
    ) in rendered
    assert "request-123" not in rendered
    assert "trace-123" not in rendered
    assert "private failure detail" not in rendered
    assert "example.invalid" not in rendered
    assert "AAPL" not in rendered
