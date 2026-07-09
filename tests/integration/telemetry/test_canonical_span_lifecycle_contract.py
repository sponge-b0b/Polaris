from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Any

from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
import pytest
from sqlalchemy.dialects import postgresql

from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.repositories import (
    postgres_telemetry_persistence_repository as repository_module,
)
from core.storage.persistence.telemetry import TelemetryTraceRecord
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.integrations.opentelemetry.opentelemetry_config import (
    OpenTelemetryConfig,
)
from core.telemetry.integrations.opentelemetry.opentelemetry_sink import (
    OpenTelemetrySink,
)


@pytest.mark.asyncio
async def test_lifecycle_events_export_one_canonical_operation_span() -> None:
    exporter = InMemorySpanExporter()
    sink = _build_sink(exporter)
    trace_id = "0123456789abcdef0123456789abcdef"
    span_id = "0123456789abcdef"

    try:
        await sink.emit(
            TelemetryEvent(
                event_type="application.service.started",
                source="application",
                level=TelemetryEventLevel.INFO,
                trace_id=trace_id,
                span_id=span_id,
            )
        )
        await sink.emit(
            TelemetryEvent(
                event_type="application.service.completed",
                source="application",
                level=TelemetryEventLevel.INFO,
                trace_id=trace_id,
                span_id=span_id,
                success=True,
                duration_seconds=0.25,
            )
        )

        sink.force_flush()
        spans = exporter.get_finished_spans()

        assert len(spans) == 1
        assert spans[0].context is not None
        assert spans[0].context.span_id == int(span_id, 16)
    finally:
        sink.shutdown()


def test_trace_persistence_updates_the_canonical_span_record() -> None:
    trace = TelemetryTraceRecord(
        trace_record_id=(
            "telemetry_trace:0123456789abcdef0123456789abcdef:0123456789abcdef"
        ),
        trace_id="0123456789abcdef0123456789abcdef",
        span_id="0123456789abcdef",
        operation_name="application.service",
        source="application",
        started_at=datetime.now(timezone.utc),
        lineage=PersistenceLineage(),
        ended_at=datetime.now(timezone.utc),
        duration_seconds=0.25,
        status="succeeded",
    )

    statement: Any = repository_module._insert_trace_statement(trace)
    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "ON CONFLICT (trace_id, span_id) DO UPDATE" in compiled
    assert "ended_at = CASE WHEN" in compiled
    assert "duration_seconds = CASE WHEN" in compiled
    assert "status = CASE WHEN" in compiled
    assert "terminal_event_id = CASE WHEN" in compiled
    assert "exception_type = CASE WHEN" in compiled


def _build_sink(exporter: InMemorySpanExporter) -> OpenTelemetrySink:
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
        span_exporter=exporter,
    )
