from __future__ import annotations

import logging

import pytest

from core.telemetry.collectors.telemetry_collector import TelemetryCollector
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.metrics.metrics_store import MetricPoint, MetricsStore
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink


class FailingEmitSink:
    async def emit(self, event: TelemetryEvent) -> None:
        del event
        raise RuntimeError("sink emit failed")


class FailingLifecycleSink(InMemoryTelemetrySink):
    def force_flush(self) -> None:
        raise RuntimeError("sink flush failed")

    def shutdown(self) -> None:
        raise RuntimeError("sink shutdown failed")


class HealthyLifecycleSink(InMemoryTelemetrySink):
    def __init__(self) -> None:
        super().__init__()
        self.flush_count = 0
        self.shutdown_count = 0

    def force_flush(self) -> None:
        self.flush_count += 1

    def shutdown(self) -> None:
        self.shutdown_count += 1


def _failure_points(metrics_store: MetricsStore) -> list[MetricPoint]:
    return [
        point
        for point in metrics_store.points()
        if point.name == "telemetry.sink.failures"
    ]


@pytest.mark.asyncio
async def test_non_fail_fast_reports_failed_sink_and_delivers_to_healthy_sink(
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics_store = MetricsStore()
    healthy_sink = InMemoryTelemetrySink()
    collector = TelemetryCollector(
        sinks=(FailingEmitSink(), healthy_sink),
        metrics_store=metrics_store,
    )
    event = TelemetryEvent(
        event_id="event-1",
        event_type="workflow.failed",
        source="test",
        trace_id="trace-1",
        span_id="span-1",
        correlation_id="correlation-1",
    )

    with caplog.at_level(
        logging.ERROR,
        logger="core.telemetry.collectors.telemetry_collector",
    ):
        await collector.emit(event)

    assert healthy_sink.events == [event]
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.exc_info is not None
    assert record.telemetry_sink == "FailingEmitSink"
    assert record.telemetry_operation == "emit"
    assert record.event_id == "event-1"
    assert record.event_type == "workflow.failed"
    assert record.trace_id == "trace-1"
    assert record.span_id == "span-1"
    assert record.correlation_id == "correlation-1"
    assert "sink emit failed" in caplog.text

    failure_points = _failure_points(metrics_store)
    assert len(failure_points) == 1
    assert failure_points[0].value == 1.0
    assert failure_points[0].attributes == {
        "component_name": "FailingEmitSink",
        "operation": "emit",
        "outcome": "failed",
    }


@pytest.mark.asyncio
async def test_fail_fast_reports_failure_then_reraises(
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics_store = MetricsStore()
    healthy_sink = InMemoryTelemetrySink()
    collector = TelemetryCollector(
        sinks=(FailingEmitSink(), healthy_sink),
        fail_fast=True,
        metrics_store=metrics_store,
    )
    event = TelemetryEvent(
        event_id="event-2",
        event_type="workflow.failed",
        source="test",
    )

    with (
        caplog.at_level(
            logging.ERROR,
            logger="core.telemetry.collectors.telemetry_collector",
        ),
        pytest.raises(RuntimeError, match="sink emit failed"),
    ):
        await collector.emit(event)

    assert healthy_sink.events == []
    assert len(caplog.records) == 1
    assert len(_failure_points(metrics_store)) == 1


def test_lifecycle_failures_are_reported_without_blocking_healthy_sinks(
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics_store = MetricsStore()
    healthy_sink = HealthyLifecycleSink()
    collector = TelemetryCollector(
        sinks=(FailingLifecycleSink(), healthy_sink),
        metrics_store=metrics_store,
    )

    with caplog.at_level(
        logging.ERROR,
        logger="core.telemetry.collectors.telemetry_collector",
    ):
        collector.force_flush()
        collector.shutdown()

    assert healthy_sink.flush_count == 1
    assert healthy_sink.shutdown_count == 1
    assert len(caplog.records) == 2
    assert all(record.exc_info is not None for record in caplog.records)
    assert [point.attributes for point in _failure_points(metrics_store)] == [
        {
            "component_name": "FailingLifecycleSink",
            "operation": "force_flush",
            "outcome": "failed",
        },
        {
            "component_name": "FailingLifecycleSink",
            "operation": "shutdown",
            "outcome": "failed",
        },
    ]


def test_lifecycle_failure_reraises_when_fail_fast_enabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics_store = MetricsStore()
    collector = TelemetryCollector(
        sinks=(FailingLifecycleSink(),),
        fail_fast=True,
        metrics_store=metrics_store,
    )

    with (
        caplog.at_level(
            logging.ERROR,
            logger="core.telemetry.collectors.telemetry_collector",
        ),
        pytest.raises(RuntimeError, match="sink flush failed"),
    ):
        collector.force_flush()

    assert len(caplog.records) == 1
    assert len(_failure_points(metrics_store)) == 1
