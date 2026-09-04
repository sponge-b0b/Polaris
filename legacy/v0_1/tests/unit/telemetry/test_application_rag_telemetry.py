from __future__ import annotations

import pytest

from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink


@pytest.mark.asyncio
async def test_application_rag_telemetry_emits_operation_started() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    telemetry = ApplicationRagTelemetry(observability_manager=observability_manager)

    await telemetry.emit_operation_started(
        component_name="RagRetriever",
        operation="rag.retrieval.hybrid",
        correlation_id="rag-request-1",
        attributes={"top_k": 8},
        payload={"route": "hybrid"},
    )

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "application.rag.operation.started"
    assert event.source == "application.rag"
    assert event.level == TelemetryEventLevel.INFO
    assert event.success is None
    assert event.correlation_id == "rag-request-1"
    assert event.attributes["component_name"] == "RagRetriever"
    assert event.attributes["operation"] == "rag.retrieval.hybrid"
    assert event.attributes["top_k"] == 8
    assert event.payload["component_name"] == "RagRetriever"
    assert event.payload["operation"] == "rag.retrieval.hybrid"
    assert event.payload["route"] == "hybrid"


@pytest.mark.asyncio
async def test_application_rag_telemetry_emits_operation_completed() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    telemetry = ApplicationRagTelemetry(observability_manager=observability_manager)

    await telemetry.emit_operation_completed(
        component_name="CuratedRagIngestionService",
        operation="rag.ingestion.persist_bundle",
        duration_seconds=0.25,
        attributes={"records_persisted": 3},
    )

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "application.rag.operation.completed"
    assert event.level == TelemetryEventLevel.INFO
    assert event.success is True
    assert event.error_count == 0
    assert event.duration_seconds == 0.25
    assert event.attributes["component_name"] == "CuratedRagIngestionService"
    assert event.attributes["operation"] == "rag.ingestion.persist_bundle"
    assert event.attributes["records_persisted"] == 3


@pytest.mark.asyncio
async def test_application_rag_telemetry_emits_operation_failed() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    telemetry = ApplicationRagTelemetry(observability_manager=observability_manager)

    error = RuntimeError("vector store unavailable")
    await telemetry.emit_operation_failed(
        component_name="EmbeddingJobProcessor",
        operation="rag.embedding.job",
        error=error,
        duration_seconds=0.75,
    )

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "application.rag.operation.failed"
    assert event.level == TelemetryEventLevel.ERROR
    assert event.success is False
    assert event.error_count == 1
    assert event.duration_seconds == 0.75
    assert event.payload["error_type"] == "RuntimeError"
    assert event.payload["error_message"] == "vector store unavailable"


@pytest.mark.asyncio
async def test_application_rag_telemetry_emits_trace_context_attributes() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    telemetry = ApplicationRagTelemetry(observability_manager=observability_manager)
    context = TelemetryContext(
        workflow_id="workflow-1",
        execution_id="execution-1",
        runtime_id="runtime-1",
        node_name="rag_node",
        correlation_id="correlation-1",
        trace_id="trace-1",
        span_id="node-span-1",
        parent_span_id="workflow-span-1",
        tags=("rag",),
    )

    await telemetry.emit_operation_completed(
        component_name="RagAnswerGenerator",
        operation="rag.generation.answer",
        duration_seconds=1.25,
        context=context,
    )

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "application.rag.operation.completed"
    assert event.workflow_id == "workflow-1"
    assert event.execution_id == "execution-1"
    assert event.runtime_id == "runtime-1"
    assert event.node_name == "rag_node"
    assert event.correlation_id == "correlation-1"
    assert event.tags == ("rag",)
    assert event.trace_id == "trace-1"
    assert event.span_id == "node-span-1"
    assert event.parent_span_id == "workflow-span-1"
    assert event.attributes["trace_id"] == "trace-1"
    assert event.attributes["span_id"] == "node-span-1"
    assert event.attributes["parent_span_id"] == "workflow-span-1"


@pytest.mark.asyncio
async def test_application_rag_telemetry_emits_degraded_warning() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    telemetry = ApplicationRagTelemetry(observability_manager=observability_manager)

    error = RuntimeError("qdrant unavailable")
    await telemetry.emit_operation_degraded(
        component_name="RagStatusOperationsService",
        operation="rag.status",
        error=error,
        attributes={"ready": False},
    )

    event = sink.events[0]
    assert event.event_type == "application.rag.operation.degraded"
    assert event.level == TelemetryEventLevel.WARNING
    assert event.success is True
    assert event.attributes["ready"] is False
    assert event.exception_details is not None
    assert event.exception_details.exception_type == "RuntimeError"


@pytest.mark.asyncio
async def test_application_rag_failure_preserves_exception_details() -> None:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    telemetry = ApplicationRagTelemetry(observability_manager=observability_manager)

    await telemetry.emit_operation_failed(
        component_name="RagRetriever",
        operation="rag.retrieval",
        error=RuntimeError("retrieval failed"),
    )

    event = sink.events[0]
    assert event.exception_details is not None
    assert event.exception_details.exception_type == "RuntimeError"
    assert event.exception_details.message == "retrieval failed"
