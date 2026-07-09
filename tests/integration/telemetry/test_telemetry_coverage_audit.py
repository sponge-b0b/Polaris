from __future__ import annotations

import asyncio
import logging
from typing import Any

import pytest

from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from application.persistence.telemetry.telemetry_event_mapper import (
    TelemetryPersistenceMapper,
)
from application.services.base import ApplicationService
from application.services.base import ServiceRequest
from application.services.base import ServiceResult
from application.services.base import ServiceRunner

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.control import WorkflowControlManager
from core.runtime.events import EventBus
from core.runtime.execution.runtime_engine import RuntimeEngine
from core.runtime.lifecycle.runtime_lifecycle_manager import RuntimeLifecycleManager
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.runtime.telemetry.runtime_telemetry import RuntimeTelemetry
from core.runtime.telemetry.runtime_telemetry_hook import RuntimeTelemetryHook
from core.telemetry.context import get_active_telemetry_context
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.integrations.opentelemetry.opentelemetry_config import (
    OpenTelemetryConfig,
)
from core.telemetry.integrations.opentelemetry.opentelemetry_sink import (
    OpenTelemetrySink,
)
from core.telemetry.logging import TelemetryLogger
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.runtime_telemetry_sink import CoreTelemetryRuntimeSink
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.telemetry.tracing.trace_context import TraceContext
from core.workflow.models.workflow_execution_plan import ExecutionPlanNode
from core.workflow.models.workflow_execution_plan import ExecutionWave
from core.workflow.models.workflow_execution_plan import WorkflowExecutionPlan
from integration.providers.provider_telemetry import record_provider_call
from intelligence.telemetry.runtime_context import telemetry_context_from_runtime


class TrackingObservabilityManager(ObservabilityManager):
    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.created_trace_contexts: list[TraceContext] = []

    def create_trace_context(
        self,
        workflow_id: str | None = None,
        execution_id: str | None = None,
        runtime_id: str | None = None,
        node_name: str | None = None,
        correlation_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TraceContext:
        trace_context = super().create_trace_context(
            workflow_id=workflow_id,
            execution_id=execution_id,
            runtime_id=runtime_id,
            node_name=node_name,
            correlation_id=correlation_id,
            attributes=attributes,
        )
        self.created_trace_contexts.append(
            trace_context,
        )
        return trace_context


class TraceAuditService(ApplicationService[dict[str, str], dict[str, Any]]):
    service_name = "trace_audit_service"

    def __init__(
        self,
        *,
        integration_telemetry: IntegrationTelemetry,
    ) -> None:
        self.integration_telemetry = integration_telemetry

    async def run(
        self,
        request: ServiceRequest[dict[str, str]],
    ) -> ServiceResult[dict[str, Any]]:
        async def provider_call() -> dict[str, str]:
            provider_context = get_active_telemetry_context()
            assert provider_context is not None
            await self.integration_telemetry.emit_client_retry_scheduled(
                provider_name="TraceAuditProvider",
                client_name="TraceAuditClient",
                operation="get_trace_audit_data",
                attempt=1,
                next_attempt=2,
                maximum_attempts=2,
                backoff_seconds=0.0,
                context=provider_context,
            )
            await asyncio.sleep(0)
            return {
                "symbol": "SPY",
                "source": "trace_audit_provider",
            }

        provider_result = await record_provider_call(
            telemetry=self.integration_telemetry,
            provider_name="TraceAuditProvider",
            operation="get_trace_audit_data",
            call=provider_call,
        )
        return ServiceResult.ok(
            request_id=request.request_id,
            request_name=request.request_name,
            result={
                **request.payload,
                **provider_result,
            },
        )

    async def _execute(
        self,
        request: dict[str, str],
    ) -> dict[str, str]:
        return request


class TraceAuditRuntimeNode(RuntimeNode):
    node_name = "trace_audit_node"
    node_type = "trace_audit"

    def __init__(
        self,
        *,
        observability: ObservabilityManager,
    ) -> None:
        self.service_runner: ServiceRunner[dict[str, str], dict[str, Any]] = (
            ServiceRunner(
                telemetry=ApplicationServiceTelemetry(
                    observability_manager=observability,
                ),
            )
        )
        self.integration_telemetry = IntegrationTelemetry(
            observability_manager=observability,
        )
        self.service = TraceAuditService(
            integration_telemetry=self.integration_telemetry,
        )
        self.intelligence_telemetry = IntelligenceTelemetry(
            observability_manager=observability,
        )

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        assert context.trace_context is not None
        telemetry_context = telemetry_context_from_runtime(
            context,
            node_name=self.node_name,
            attributes={
                "audit_scope": "trace_propagation",
            },
        )

        service_result = await self.service_runner.run(
            service=self.service,
            request=ServiceRequest(
                payload={
                    "symbol": "SPY",
                },
                correlation_id=telemetry_context.correlation_id,
                telemetry_context=telemetry_context,
            ),
        )

        await self.intelligence_telemetry.emit_agent_signal(
            agent_name="trace_audit_agent",
            signal_name="trace.audit",
            confidence=0.987654,
            context=telemetry_context,
        )

        return RuntimeNodeOutput.success_output(
            outputs={
                "service_success": service_result.success,
                "provider_symbol": (service_result.result or {})["symbol"],
                "trace_id": telemetry_context.trace_id,
                "span_id": telemetry_context.span_id,
                "parent_span_id": telemetry_context.parent_span_id,
            },
        )


class AuditRuntimeNode(RuntimeNode):
    node_name = "audit_node"
    node_type = "telemetry_audit"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput.success_output(
            outputs={
                "audited": True,
            },
        )


@pytest.mark.asyncio
async def test_core_telemetry_paths_remain_registered(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger_name = "polaris.telemetry.coverage_audit"
    observability, sink = _build_observability(
        logger_name=logger_name,
    )
    event_bus = EventBus()
    engine = _build_runtime_engine(
        observability=observability,
        event_bus=event_bus,
    )

    with caplog.at_level(
        logging.INFO,
        logger=logger_name,
    ):
        await engine.execute(
            context=RuntimeContext(
                runtime_id="telemetry-audit-runtime",
                workflow_id="telemetry_audit_workflow",
                execution_id="telemetry-audit-execution",
            ),
            execution_plan=_build_plan(),
        )
        await _emit_control_events(
            event_bus,
        )
        await IntegrationTelemetry(
            observability_manager=observability,
        ).emit_provider_call(
            provider_name="AuditProvider",
            operation="get_audit_data",
            duration_seconds=0.123456,
            success=True,
        )
        await IntelligenceTelemetry(
            observability_manager=observability,
        ).emit_agent_signal(
            agent_name="audit_agent",
            signal_name="audit.signal",
            confidence=0.987654,
        )

    event_types = {event.event_type for event in sink.events}
    metric_names = {point.name for point in observability.metrics_store.points()}
    logged_telemetry_types = {
        telemetry["event_type"]
        for telemetry in (
            getattr(record, "telemetry", None)
            for record in caplog.records
            if record.name == logger_name
        )
        if isinstance(telemetry, dict)
    }

    assert "runtime.workflow.started" in event_types
    assert "runtime.workflow.completed" in event_types
    assert "workflow_progress.workflow_started" in event_types
    assert "workflow_progress.workflow_completed" in event_types
    assert "workflow_control.pause_requested" in event_types
    assert "workflow_control.resume_requested" in event_types
    assert "workflow_control.cancel_requested" in event_types
    assert "integration.provider.call" in event_types
    assert "intelligence.agent.signal" in event_types

    assert "runtime.workflow.completed" in logged_telemetry_types
    assert "integration.provider.call" in logged_telemetry_types
    assert "intelligence.agent.signal" in logged_telemetry_types

    assert "telemetry.events.total" in metric_names
    assert "workflow.executions.total" in metric_names
    assert "workflow.duration_seconds" in metric_names
    assert "integration.provider.calls.total" in metric_names
    assert "integration.provider.duration_seconds" in metric_names
    assert "intelligence.agent.signals.total" in metric_names


@pytest.mark.asyncio
async def test_trace_identity_is_auditable_across_runtime_boundaries() -> None:
    observability, telemetry_sink, otel_sink, span_exporter = (
        _build_trace_audit_observability()
    )
    event_bus = EventBus()
    engine = _build_trace_audit_runtime_engine(
        observability=observability,
        event_bus=event_bus,
    )

    try:
        result = await engine.execute(
            context=RuntimeContext(
                runtime_id="trace-audit-runtime",
                workflow_id="trace_audit_workflow",
                execution_id="trace-audit-execution",
            ),
            execution_plan=_build_trace_audit_plan(),
        )
        otel_sink.force_flush()

        assert len(observability.created_trace_contexts) == 1
        workflow_trace = observability.created_trace_contexts[0]
        assert result.trace_context is not None
        assert result.trace_context.trace_id == workflow_trace.trace_id
        assert result.trace_context.span_id == workflow_trace.span_id

        node_outputs = result.node_outputs["trace_audit_node"]["outputs"]
        node_trace_id = str(node_outputs["trace_id"])
        node_span_id = str(node_outputs["span_id"])
        node_parent_span_id = str(node_outputs["parent_span_id"])
        assert node_trace_id == workflow_trace.trace_id
        assert node_span_id != workflow_trace.span_id
        assert node_parent_span_id == workflow_trace.span_id

        events_by_type = _events_by_type(
            telemetry_sink.events,
        )
        workflow_started = events_by_type["runtime.workflow.started"]
        node_completed = events_by_type["runtime.node.completed"]
        service_completed = events_by_type["application.service.completed"]
        provider_call = events_by_type["integration.provider.call"]
        client_retry = events_by_type["integration.client.retry_scheduled"]
        agent_signal = events_by_type["intelligence.agent.signal"]

        assert workflow_started.payload["trace_id"] == workflow_trace.trace_id
        assert workflow_started.payload["span_id"] == workflow_trace.span_id

        _assert_node_trace_event(
            node_completed,
            trace_id=node_trace_id,
            span_id=node_span_id,
            parent_span_id=node_parent_span_id,
        )
        service_span_id = str(_event_value(service_completed, "span_id"))
        provider_span_id = str(_event_value(provider_call, "span_id"))
        client_retry_span_id = str(_event_value(client_retry, "span_id"))
        assert service_span_id != node_span_id
        assert provider_span_id != node_span_id
        assert provider_span_id != service_span_id
        _assert_node_trace_event(
            service_completed,
            trace_id=node_trace_id,
            span_id=service_span_id,
            parent_span_id=node_span_id,
        )
        _assert_node_trace_event(
            provider_call,
            trace_id=node_trace_id,
            span_id=provider_span_id,
            parent_span_id=service_span_id,
        )
        _assert_node_trace_event(
            client_retry,
            trace_id=node_trace_id,
            span_id=client_retry_span_id,
            parent_span_id=service_span_id,
        )
        assert client_retry_span_id == provider_span_id
        _assert_node_trace_event(
            agent_signal,
            trace_id=node_trace_id,
            span_id=node_span_id,
            parent_span_id=node_parent_span_id,
        )

        spans_by_name = {span.name: span for span in span_exporter.get_finished_spans()}
        assert set(spans_by_name) == {
            "runtime.workflow",
            "runtime.node",
            "application.service",
            "integration.provider.call",
        }
        correlated_spans = tuple(spans_by_name.values())
        assert {span.context.trace_id for span in correlated_spans} == {
            int(workflow_trace.trace_id, 16),
        }

        workflow_span = spans_by_name["runtime.workflow"]
        node_span = spans_by_name["runtime.node"]
        service_span = spans_by_name["application.service"]
        provider_span = spans_by_name["integration.provider.call"]
        assert workflow_span.context.span_id == int(workflow_trace.span_id, 16)
        assert node_span.context.span_id == int(node_span_id, 16)
        assert service_span.context.span_id == int(service_span_id, 16)
        assert provider_span.context.span_id == int(provider_span_id, 16)
        assert workflow_span.parent is None
        assert node_span.parent is not None
        assert node_span.parent.span_id == workflow_span.context.span_id
        assert service_span.parent is not None
        assert service_span.parent.span_id == node_span.context.span_id
        assert provider_span.parent is not None
        assert provider_span.parent.span_id == service_span.context.span_id

        assert workflow_span.attributes["trace.id"] == workflow_trace.trace_id
        assert workflow_span.attributes["span.id"] == workflow_trace.span_id
        assert service_span.attributes["trace.id"] == node_trace_id
        assert service_span.attributes["span.id"] == service_span_id
        assert service_span.attributes["parent_span.id"] == node_span_id
        assert provider_span.attributes["trace.id"] == node_trace_id
        assert provider_span.attributes["parent_span.id"] == service_span_id
        assert "integration.client.retry_scheduled" in {
            event.name for event in provider_span.events
        }
        assert "intelligence.agent.signal" in {event.name for event in node_span.events}

        mapper = TelemetryPersistenceMapper()
        for event in (
            workflow_started,
            node_completed,
            service_completed,
            provider_call,
            client_retry,
            agent_signal,
        ):
            bundle = mapper.map_event(
                event,
            )
            assert len(bundle.traces) == 1
            trace_record = bundle.traces[0]
            assert trace_record.trace_id == workflow_trace.trace_id
            assert trace_record.span_id is not None

        service_trace = mapper.map_event(
            service_completed,
        ).traces[0]
        assert service_trace.span_id == service_span_id
        assert service_trace.parent_span_id == node_span_id
        provider_trace = mapper.map_event(
            provider_call,
        ).traces[0]
        retry_trace = mapper.map_event(
            client_retry,
        ).traces[0]
        assert provider_trace.span_id == provider_span_id
        assert provider_trace.parent_span_id == service_span_id
        assert retry_trace.span_id == provider_span_id
        assert retry_trace.parent_span_id == service_span_id

    finally:
        otel_sink.shutdown()


def _build_trace_audit_observability() -> tuple[
    TrackingObservabilityManager,
    InMemoryTelemetrySink,
    OpenTelemetrySink,
    InMemorySpanExporter,
]:
    telemetry_sink = InMemoryTelemetrySink()
    span_exporter = InMemorySpanExporter()
    otel_sink = OpenTelemetrySink(
        config=OpenTelemetryConfig(
            service_name="polaris-trace-audit-test",
            service_version="test",
            environment="test",
            enable_tracing=True,
            enable_metrics=False,
            enable_console_export=False,
        ),
        span_exporter=span_exporter,
    )
    observability = TrackingObservabilityManager()
    observability.add_sink(
        telemetry_sink,
    )
    observability.add_sink(
        otel_sink,
    )

    return observability, telemetry_sink, otel_sink, span_exporter


def _build_trace_audit_runtime_engine(
    *,
    observability: ObservabilityManager,
    event_bus: EventBus,
) -> RuntimeEngine:
    runtime_telemetry = RuntimeTelemetry(
        sinks=[
            CoreTelemetryRuntimeSink(
                sink=observability,
            ),
        ],
    )
    lifecycle_manager = RuntimeLifecycleManager(
        hooks=[
            RuntimeTelemetryHook(
                telemetry=runtime_telemetry,
            ),
        ],
    )
    event_bus.subscribe_lifecycle_manager(
        lifecycle_manager,
    )

    engine = RuntimeEngine(
        lifecycle_manager=lifecycle_manager,
        event_bus=event_bus,
        observability_manager=observability,
    )
    engine.register(
        "trace_audit_node",
        TraceAuditRuntimeNode(
            observability=observability,
        ),
    )

    return engine


def _build_trace_audit_plan() -> WorkflowExecutionPlan:
    return WorkflowExecutionPlan(
        workflow_name="trace_audit_workflow",
        execution_id="trace-audit-execution",
        nodes={
            "trace_audit_node": ExecutionPlanNode(
                name="trace_audit_node",
                node_type="trace_audit",
                max_retries=0,
            ),
        },
        waves=(
            ExecutionWave(
                index=0,
                nodes=("trace_audit_node",),
            ),
        ),
    )


def _events_by_type(
    events: list[TelemetryEvent],
) -> dict[str, TelemetryEvent]:
    return {event.event_type: event for event in events}


def _assert_node_trace_event(
    event: TelemetryEvent,
    *,
    trace_id: str,
    span_id: str,
    parent_span_id: str,
) -> None:
    assert event.workflow_id == "trace_audit_workflow"
    assert event.execution_id == "trace-audit-execution"
    assert event.runtime_id == "trace-audit-runtime"
    assert event.node_name == "trace_audit_node"
    assert _event_value(event, "trace_id") == trace_id
    assert _event_value(event, "span_id") == span_id
    assert _event_value(event, "parent_span_id") == parent_span_id


def _event_value(
    event: TelemetryEvent,
    key: str,
) -> object | None:
    if key in event.attributes:
        return event.attributes[key]
    return event.payload.get(key)


def _build_observability(
    *,
    logger_name: str,
) -> tuple[ObservabilityManager, InMemoryTelemetrySink]:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(
        sink,
    )
    observability.add_sink(
        TelemetryLogger(
            logger_name=logger_name,
        )
    )

    return observability, sink


def _build_runtime_engine(
    *,
    observability: ObservabilityManager,
    event_bus: EventBus,
) -> RuntimeEngine:
    runtime_telemetry = RuntimeTelemetry(
        sinks=[
            CoreTelemetryRuntimeSink(
                sink=observability,
            ),
        ],
    )
    lifecycle_manager = RuntimeLifecycleManager(
        hooks=[
            RuntimeTelemetryHook(
                telemetry=runtime_telemetry,
            ),
        ],
    )
    event_bus.subscribe_lifecycle_manager(
        lifecycle_manager,
    )

    engine = RuntimeEngine(
        lifecycle_manager=lifecycle_manager,
        event_bus=event_bus,
    )
    engine.register(
        "audit_node",
        AuditRuntimeNode(),
    )

    return engine


def _build_plan() -> WorkflowExecutionPlan:
    return WorkflowExecutionPlan(
        workflow_name="telemetry_audit_workflow",
        execution_id="telemetry-audit-execution",
        nodes={
            "audit_node": ExecutionPlanNode(
                name="audit_node",
                node_type="telemetry_audit",
                max_retries=0,
            ),
        },
        waves=(
            ExecutionWave(
                index=0,
                nodes=("audit_node",),
            ),
        ),
    )


async def _emit_control_events(
    event_bus: EventBus,
) -> None:
    control_manager = WorkflowControlManager(
        event_bus=event_bus,
    )
    execution_id = "telemetry-audit-control-execution"
    await control_manager.mark_running(
        execution_id,
        metadata={
            "workflow_id": "telemetry_audit_control_workflow",
            "runtime_id": "telemetry-audit-control-runtime",
        },
    )
    await control_manager.request_pause(
        execution_id,
        reason="coverage audit pause",
        requested_by="test",
    )
    wait_task = asyncio.create_task(
        control_manager.wait_if_paused(
            execution_id,
        ),
    )
    await asyncio.sleep(
        0,
    )
    await control_manager.request_resume(
        execution_id,
        reason="coverage audit resume",
        requested_by="test",
    )
    await asyncio.wait_for(
        wait_task,
        timeout=1.0,
    )
    await control_manager.request_cancel(
        execution_id,
        reason="coverage audit cancel",
        requested_by="test",
    )
