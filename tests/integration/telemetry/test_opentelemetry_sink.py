from __future__ import annotations

import asyncio

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import StatusCode

from core.telemetry.context import get_active_telemetry_context, telemetry_context_scope
from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.events.telemetry_event import (
    TelemetryEvent,
    TelemetryEventLevel,
)
from core.telemetry.events.telemetry_exception_details import (
    TelemetryExceptionDetails,
)
from core.telemetry.integrations.opentelemetry.opentelemetry_config import (
    OpenTelemetryConfig,
)
from core.telemetry.integrations.opentelemetry.opentelemetry_sink import (
    OpenTelemetrySink,
)
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)


@pytest.mark.asyncio
async def test_opentelemetry_sink_exports_one_span_with_canonical_event_fields() -> (
    None
):
    span_exporter = InMemorySpanExporter()
    sink = _build_sink(span_exporter)
    trace_id = "0123456789abcdef0123456789abcdef"
    span_id = "0123456789abcdef"
    parent_span_id = "fedcba9876543210"

    try:
        await sink.emit(
            TelemetryEvent(
                event_id="canonical-start-event-id",
                event_type="application.service.started",
                source="test",
                level=TelemetryEventLevel.INFO,
                workflow_id="test_workflow",
                execution_id="test_execution",
                runtime_id="test_runtime",
                node_name="test_node",
                correlation_id="test_correlation",
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                tags=("otel", "test"),
                attributes={
                    "component": "telemetry",
                    "provider_name": "test_provider",
                    "operation": "get_prices",
                },
                payload={
                    "message": "hello opentelemetry",
                    "value": 123,
                    "api_key": "secret-key",
                    "nested": {"authorization": "Bearer secret"},
                },
            )
        )
        assert span_exporter.get_finished_spans() == ()

        await sink.emit(
            TelemetryEvent(
                event_id="canonical-complete-event-id",
                event_type="application.service.completed",
                source="test",
                level=TelemetryEventLevel.INFO,
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                success=True,
                duration_seconds=0.25,
            )
        )

        spans = span_exporter.get_finished_spans()
        assert len(spans) == 1
        span = spans[0]

        assert span.name == "application.service"
        assert span.context is not None
        assert span.context.trace_id == int(trace_id, 16)
        assert span.context.span_id == int(span_id, 16)
        assert span.parent is not None
        assert span.parent.span_id == int(parent_span_id, 16)
        assert span.attributes["workflow.id"] == "test_workflow"
        assert span.attributes["execution.id"] == "test_execution"
        assert span.attributes["runtime.id"] == "test_runtime"
        assert span.attributes["node.name"] == "test_node"
        assert span.attributes["correlation.id"] == "test_correlation"
        assert span.attributes["trace.id"] == trace_id
        assert span.attributes["span.id"] == span_id
        assert span.attributes["parent_span.id"] == parent_span_id
        assert span.attributes["provider.name"] == "test_provider"
        assert span.attributes["provider.operation"] == "get_prices"
        assert span.attributes["success"] is True
        assert span.attributes["telemetry.event_count"] == 2
        assert span.attributes["attr.component"] == "telemetry"
        assert span.attributes["message"] == "hello opentelemetry"
        assert span.attributes["value"] == 123
        assert span.attributes["api_key"] == "[REDACTED]"
        assert "Bearer secret" not in str(span.attributes["nested"])
        assert [event.name for event in span.events] == [
            "application.service.started",
            "application.service.completed",
        ]
        assert span.events[0].attributes["telemetry.event_id"] == (
            "canonical-start-event-id"
        )
        assert span.events[1].attributes["telemetry.event_id"] == (
            "canonical-complete-event-id"
        )
    finally:
        sink.shutdown()


@pytest.mark.asyncio
async def test_observability_manager_flushes_and_shutdowns_opentelemetry_sink() -> None:
    span_exporter = InMemorySpanExporter()
    sink = _build_sink(span_exporter)
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    trace_id = "0123456789abcdef0123456789abcdef"
    span_id = "0123456789abcdef"

    await observability_manager.emit(
        TelemetryEvent(
            event_type="runtime.workflow.started",
            source="test",
            trace_id=trace_id,
            span_id=span_id,
        )
    )
    observability_manager.force_flush()
    assert span_exporter.get_finished_spans() == ()

    await observability_manager.emit(
        TelemetryEvent(
            event_type="runtime.workflow.completed",
            source="test",
            trace_id=trace_id,
            span_id=span_id,
            success=True,
        )
    )
    observability_manager.force_flush()

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "runtime.workflow"

    observability_manager.shutdown()
    observability_manager.force_flush()
    observability_manager.shutdown()

    assert sink.to_dict()["shutdown"] is True


@pytest.mark.asyncio
async def test_opentelemetry_sink_creates_real_canonical_parent_relationships() -> None:
    span_exporter = InMemorySpanExporter()
    sink = _build_sink(span_exporter)
    trace_id = "0123456789abcdef0123456789abcdef"
    root_span_id = "0123456789abcdef"
    child_span_id = "fedcba9876543210"

    try:
        await sink.emit(
            TelemetryEvent(
                event_type="runtime.workflow.started",
                source="runtime",
                trace_id=trace_id,
                span_id=root_span_id,
            )
        )
        await sink.emit(
            TelemetryEvent(
                event_type="runtime.workflow.progress",
                source="runtime",
                trace_id=trace_id,
                span_id=root_span_id,
            )
        )
        await sink.emit(
            TelemetryEvent(
                event_type="runtime.node.started",
                source="runtime",
                trace_id=trace_id,
                span_id=child_span_id,
                parent_span_id=root_span_id,
            )
        )
        await sink.emit(
            TelemetryEvent(
                event_type="runtime.node.completed",
                source="runtime",
                trace_id=trace_id,
                span_id=child_span_id,
                parent_span_id=root_span_id,
                success=True,
            )
        )
        await sink.emit(
            TelemetryEvent(
                event_type="runtime.workflow.completed",
                source="runtime",
                trace_id=trace_id,
                span_id=root_span_id,
                success=True,
            )
        )

        spans = span_exporter.get_finished_spans()
        assert len(spans) == 2
        spans_by_name = {span.name: span for span in spans}
        root_span = spans_by_name["runtime.workflow"]
        child_span = spans_by_name["runtime.node"]

        assert root_span.context is not None
        assert child_span.context is not None
        assert root_span.context.trace_id == int(trace_id, 16)
        assert root_span.context.span_id == int(root_span_id, 16)
        assert child_span.context.trace_id == int(trace_id, 16)
        assert child_span.context.span_id == int(child_span_id, 16)
        assert root_span.parent is None
        assert child_span.parent is not None
        assert child_span.parent.span_id == int(root_span_id, 16)
        assert [event.name for event in root_span.events] == [
            "runtime.workflow.started",
            "runtime.workflow.progress",
            "runtime.workflow.completed",
        ]
    finally:
        sink.shutdown()


@pytest.mark.asyncio
async def test_opentelemetry_sink_records_events_exception_and_error_status() -> None:
    span_exporter = InMemorySpanExporter()
    sink = _build_sink(span_exporter)
    trace_id = "0123456789abcdef0123456789abcdef"
    provider_span_id = "0123456789abcdef"
    service_span_id = "fedcba9876543210"
    details = TelemetryExceptionDetails(
        exception_type="RuntimeError",
        message="provider failed",
        stack_trace="Traceback: provider failed",
    )

    try:
        await sink.emit(
            TelemetryEvent(
                event_type="integration.provider.call",
                source="integration",
                level=TelemetryEventLevel.ERROR,
                trace_id=trace_id,
                span_id=provider_span_id,
                success=False,
                error_count=1,
                exception_details=details,
            )
        )
        await sink.emit(
            TelemetryEvent(
                event_type="application.service.started",
                source="application",
                trace_id=trace_id,
                span_id=service_span_id,
            )
        )
        await sink.emit(
            TelemetryEvent(
                event_type="application.service.retry_scheduled",
                source="application",
                level=TelemetryEventLevel.WARNING,
                trace_id=trace_id,
                span_id=service_span_id,
            )
        )
        await sink.emit(
            TelemetryEvent(
                event_type="application.service.degraded",
                source="application",
                level=TelemetryEventLevel.WARNING,
                trace_id=trace_id,
                span_id=service_span_id,
                success=True,
            )
        )
        await sink.emit(
            TelemetryEvent(
                event_type="application.service.completed",
                source="application",
                trace_id=trace_id,
                span_id=service_span_id,
                success=True,
            )
        )

        spans_by_name = {span.name: span for span in span_exporter.get_finished_spans()}
        failed_span = spans_by_name["integration.provider.call"]
        service_span = spans_by_name["application.service"]
        assert failed_span.status.status_code is StatusCode.ERROR
        assert failed_span.status.description == "provider failed"
        exception_events = [
            event for event in failed_span.events if event.name == "exception"
        ]
        assert len(exception_events) == 1
        assert exception_events[0].attributes == {
            "exception.type": "RuntimeError",
            "exception.message": "provider failed",
            "exception.stacktrace": "Traceback: provider failed",
        }
        assert service_span.status.status_code is StatusCode.UNSET
        assert [event.name for event in service_span.events] == [
            "application.service.started",
            "application.service.retry_scheduled",
            "application.service.degraded",
            "application.service.completed",
        ]
    finally:
        sink.shutdown()


@pytest.mark.asyncio
async def test_opentelemetry_sink_preserves_trace_context_across_async_tasks() -> None:
    span_exporter = InMemorySpanExporter()
    sink = _build_sink(span_exporter)
    root_context = TelemetryContext(
        trace_id="0123456789abcdef0123456789abcdef",
        span_id="0123456789abcdef",
        correlation_id="async-correlation",
    )

    async def emit_child(index: int) -> None:
        inherited = get_active_telemetry_context()
        assert inherited is root_context
        parent = inherited.to_trace_context()
        assert parent is not None
        child = parent.child(node_name=f"node-{index}")
        await sink.emit(
            TelemetryEvent(
                event_type="runtime.node.started",
                source="runtime",
                trace_id=child.trace_id,
                span_id=child.span_id,
                parent_span_id=child.parent_span_id,
                node_name=child.node_name,
            )
        )
        await sink.emit(
            TelemetryEvent(
                event_type="runtime.node.completed",
                source="runtime",
                trace_id=child.trace_id,
                span_id=child.span_id,
                parent_span_id=child.parent_span_id,
                node_name=child.node_name,
                success=True,
            )
        )

    try:
        with telemetry_context_scope(root_context):
            await sink.emit(
                TelemetryEvent(
                    event_type="runtime.workflow.started",
                    source="runtime",
                    trace_id=root_context.trace_id,
                    span_id=root_context.span_id,
                    correlation_id=root_context.correlation_id,
                )
            )
            tasks = [asyncio.create_task(emit_child(index)) for index in range(2)]
            await asyncio.gather(*tasks)
            await sink.emit(
                TelemetryEvent(
                    event_type="runtime.workflow.completed",
                    source="runtime",
                    trace_id=root_context.trace_id,
                    span_id=root_context.span_id,
                    success=True,
                )
            )

        spans = span_exporter.get_finished_spans()
        assert len(spans) == 3
        root_span = next(span for span in spans if span.name == "runtime.workflow")
        child_spans = [span for span in spans if span.name == "runtime.node"]
        assert len(child_spans) == 2
        assert all(span.parent is not None for span in child_spans)
        assert all(
            span.parent.span_id == root_span.context.span_id
            for span in child_spans
            if span.parent is not None
        )
        assert {span.context.trace_id for span in child_spans if span.context} == {
            root_span.context.trace_id
        }
        assert len({span.context.span_id for span in child_spans if span.context}) == 2
    finally:
        sink.shutdown()


@pytest.mark.asyncio
async def test_opentelemetry_sink_bounds_and_closes_incomplete_lifecycles() -> None:
    span_exporter = InMemorySpanExporter()
    sink = _build_sink(span_exporter)
    sink._max_open_spans = 2
    trace_id = "0123456789abcdef0123456789abcdef"

    for span_id in (
        "0000000000000001",
        "0000000000000002",
        "0000000000000003",
    ):
        await sink.emit(
            TelemetryEvent(
                event_type="runtime.node.started",
                source="runtime",
                trace_id=trace_id,
                span_id=span_id,
            )
        )

    evicted_spans = span_exporter.get_finished_spans()
    assert len(evicted_spans) == 1
    assert evicted_spans[0].attributes["telemetry.lifecycle.incomplete"] is True
    assert evicted_spans[0].attributes["telemetry.lifecycle.evicted"] is True
    assert sink.to_dict()["open_span_count"] == 2

    sink.shutdown()
    spans = span_exporter.get_finished_spans()
    assert len(spans) == 3
    assert all(
        span.attributes["telemetry.lifecycle.incomplete"] is True for span in spans
    )
    assert sink.to_dict()["open_span_count"] == 0


def _build_sink(span_exporter: InMemorySpanExporter) -> OpenTelemetrySink:
    return OpenTelemetrySink(
        config=OpenTelemetryConfig(
            service_name="polaris-test",
            service_version="test",
            environment="test",
            otlp_endpoint="http://localhost:4317",
            enable_tracing=True,
            enable_metrics=False,
            enable_console_export=False,
            insecure=True,
        ),
        span_exporter=span_exporter,
    )
