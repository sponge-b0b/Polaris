from __future__ import annotations

import pytest

from core.telemetry.events.telemetry_event import TelemetryEvent, TelemetryEventLevel
from core.telemetry.observability.observability_manager import ObservabilityManager


def metric_names(
    observability_manager: ObservabilityManager,
) -> list[str]:
    return [point.name for point in observability_manager.metrics_store.points()]


@pytest.mark.asyncio
async def test_observability_records_workflow_and_node_domain_metrics() -> None:
    observability_manager = ObservabilityManager()

    await observability_manager.emit(
        TelemetryEvent(
            event_type="runtime.workflow.started",
            source="runtime",
            workflow_id="morning_report",
            execution_id="execution-1",
        )
    )
    await observability_manager.emit(
        TelemetryEvent(
            event_type="runtime.workflow.failed",
            source="runtime",
            level=TelemetryEventLevel.ERROR,
            workflow_id="morning_report",
            execution_id="execution-1",
            duration_seconds=3.5,
            success=False,
            error_count=1,
        )
    )
    await observability_manager.emit(
        TelemetryEvent(
            event_type="runtime.node.started",
            source="runtime",
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            node_name="technical_node",
        )
    )
    await observability_manager.emit(
        TelemetryEvent(
            event_type="runtime.node.failed",
            source="runtime",
            level=TelemetryEventLevel.ERROR,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            node_name="technical_node",
            duration_seconds=0.25,
            success=False,
            error_count=1,
        )
    )
    await observability_manager.emit(
        TelemetryEvent(
            event_type="runtime.node.skipped",
            source="runtime",
            level=TelemetryEventLevel.WARNING,
            workflow_id="morning_report",
            execution_id="execution-1",
            runtime_id="runtime-1",
            node_name="strategy_node",
        )
    )

    names = metric_names(
        observability_manager,
    )

    assert "telemetry.events.total" in names
    assert "telemetry.events.errors" in names
    assert "telemetry.event.duration_seconds" in names
    assert "workflow.executions.total" in names
    assert "workflow.executions.failed" in names
    assert "workflow.duration_seconds" in names
    assert "runtime.nodes.total" in names
    assert "runtime.nodes.failed" in names
    assert "runtime.nodes.skipped" in names
    assert "runtime.node.duration_seconds" in names

    workflow_duration_points = [
        point
        for point in observability_manager.metrics_store.points()
        if point.name == "workflow.duration_seconds"
    ]
    node_duration_points = [
        point
        for point in observability_manager.metrics_store.points()
        if point.name == "runtime.node.duration_seconds"
    ]

    assert workflow_duration_points[-1].value == 3.5
    assert node_duration_points[-1].value == 0.25
    assert node_duration_points[-1].attributes["node_name"] == "technical_node"


@pytest.mark.asyncio
async def test_observability_records_application_provider_and_intelligence_domain_metrics() -> (  # noqa: E501
    None
):
    observability_manager = ObservabilityManager()

    await observability_manager.emit(
        TelemetryEvent(
            event_type="application.service.started",
            source="application",
            attributes={
                "service_name": "TechnicalAnalysisService",
            },
        )
    )
    await observability_manager.emit(
        TelemetryEvent(
            event_type="application.service.failed",
            source="application",
            level=TelemetryEventLevel.ERROR,
            duration_seconds=1.2,
            success=False,
            error_count=1,
            attributes={
                "service_name": "TechnicalAnalysisService",
            },
        )
    )
    await observability_manager.emit(
        TelemetryEvent(
            event_type="application.rag.operation.started",
            source="application.rag",
            attributes={
                "component_name": "RagRetriever",
                "operation": "rag.retrieval.hybrid",
            },
        )
    )
    await observability_manager.emit(
        TelemetryEvent(
            event_type="application.rag.operation.completed",
            source="application.rag",
            duration_seconds=0.33,
            success=True,
            attributes={
                "component_name": "RagRetriever",
                "operation": "rag.retrieval.hybrid",
            },
        )
    )
    await observability_manager.emit(
        TelemetryEvent(
            event_type="integration.provider.call",
            source="integration",
            level=TelemetryEventLevel.ERROR,
            duration_seconds=0.75,
            success=False,
            error_count=1,
            attributes={
                "provider_name": "MarketDataProvider",
                "operation": "get_sp500_data",
            },
        )
    )
    await observability_manager.emit(
        TelemetryEvent(
            event_type="intelligence.agent.signal",
            source="intelligence",
            success=True,
            attributes={
                "agent_name": "TechnicalAgent",
                "signal_name": "technical.signal",
            },
        )
    )

    names = metric_names(
        observability_manager,
    )

    assert "application.service.calls.total" in names
    assert "application.service.calls.failed" in names
    assert "application.service.duration_seconds" in names
    assert "application.rag.operations.total" in names
    assert "application.rag.operation.duration_seconds" in names
    assert "integration.provider.calls.total" in names
    assert "integration.provider.calls.failed" in names
    assert "integration.provider.duration_seconds" in names
    assert "intelligence.agent.signals.total" in names

    rag_duration_points = [
        point
        for point in observability_manager.metrics_store.points()
        if point.name == "application.rag.operation.duration_seconds"
    ]
    assert rag_duration_points[-1].value == 0.33
    assert rag_duration_points[-1].attributes["component_name"] == "RagRetriever"
    assert rag_duration_points[-1].attributes["operation"] == "rag.retrieval.hybrid"

    provider_duration_points = [
        point
        for point in observability_manager.metrics_store.points()
        if point.name == "integration.provider.duration_seconds"
    ]

    assert provider_duration_points[-1].value == 0.75
    assert (
        provider_duration_points[-1].attributes["provider_name"] == "MarketDataProvider"
    )
    assert provider_duration_points[-1].attributes["operation"] == "get_sp500_data"


@pytest.mark.asyncio
async def test_observability_can_disable_domain_metrics() -> None:
    observability_manager = ObservabilityManager(
        enable_domain_metrics=False,
    )

    await observability_manager.emit(
        TelemetryEvent(
            event_type="runtime.workflow.started",
            source="runtime",
            workflow_id="morning_report",
            execution_id="execution-1",
        )
    )

    names = metric_names(
        observability_manager,
    )

    assert "telemetry.events.total" in names
    assert "workflow.executions.total" not in names


@pytest.mark.asyncio
async def test_observability_records_operational_boundary_metrics() -> None:
    observability_manager = ObservabilityManager()
    events = (
        TelemetryEvent(
            event_type="application.service.configuration_failed",
            source="application",
            success=False,
            attributes={"service_name": "TechnicalAnalysisService"},
        ),
        TelemetryEvent(
            event_type="application.service.retry_scheduled",
            source="application",
            level=TelemetryEventLevel.WARNING,
            attributes={"service_name": "TechnicalAnalysisService"},
        ),
        TelemetryEvent(
            event_type="application.service.degraded",
            source="application",
            level=TelemetryEventLevel.WARNING,
            success=True,
            attributes={"service_name": "NewsService"},
        ),
        TelemetryEvent(
            event_type="integration.client.retry_scheduled",
            source="integration",
            level=TelemetryEventLevel.WARNING,
            attributes={
                "provider_name": "MarketDataProvider",
                "client_name": "YFinanceDataClient",
                "operation": "get_sp500_data",
                "url": "https://example.invalid/private",
            },
        ),
        TelemetryEvent(
            event_type="plugin.lifecycle.hook_failed",
            source="plugin.runtime",
            success=False,
            payload={
                "lifecycle_event": "before_plugin_load",
                "hook": "FailingPluginHook",
            },
        ),
        TelemetryEvent(
            event_type="runtime.lifecycle.hook_failed",
            source="runtime.lifecycle",
            success=False,
            payload={
                "lifecycle_event": "before_node_execute",
                "hook": "FailingRuntimeHook",
            },
        ),
        TelemetryEvent(
            event_type="platform.bootstrap.configuration_failed",
            source="core.workflow.bootstrap",
            success=False,
            attributes={"component_name": "OpenTelemetry"},
            payload={"startup_action": "continued_degraded"},
        ),
        TelemetryEvent(
            event_type="runtime.event",
            source="runtime",
            success=False,
            payload={
                "runtime_event": {
                    "event_type": "system_warning",
                    "payload": {
                        "warning_type": "EventBusSubscriberFailure",
                        "failed_event_type": "node_completed",
                    },
                }
            },
        ),
    )

    for event in events:
        await observability_manager.emit(event)

    points = observability_manager.metrics_store.points()
    points_by_name = {point.name: point for point in points}
    expected_names = {
        "application.service.configuration_failures",
        "application.service.retries",
        "application.service.degraded",
        "integration.client.retries",
        "plugin.lifecycle.callback_failures",
        "runtime.lifecycle.callback_failures",
        "runtime.event_bus.subscriber_failures",
        "platform.bootstrap.configuration_failures",
    }

    assert expected_names <= points_by_name.keys()
    assert points_by_name["application.service.retries"].attributes == {
        "event_type": "application.service.retry_scheduled",
        "service_name": "TechnicalAnalysisService",
        "outcome": "retry_scheduled",
    }
    assert points_by_name["integration.client.retries"].attributes == {
        "event_type": "integration.client.retry_scheduled",
        "provider_name": "MarketDataProvider",
        "operation": "get_sp500_data",
        "component_name": "YFinanceDataClient",
        "outcome": "retry_scheduled",
    }
    assert points_by_name["plugin.lifecycle.callback_failures"].attributes == {
        "event_type": "plugin.lifecycle.hook_failed",
        "component_name": "FailingPluginHook",
        "operation": "before_plugin_load",
        "outcome": "failed",
        "success": False,
    }
    assert points_by_name["runtime.event_bus.subscriber_failures"].attributes == {
        "event_type": "runtime.event",
        "component_name": "EventBus",
        "operation": "node_completed",
        "outcome": "failed",
        "success": False,
    }
    assert points_by_name["platform.bootstrap.configuration_failures"].attributes == {
        "event_type": "platform.bootstrap.configuration_failed",
        "component_name": "OpenTelemetry",
        "operation": "configuration",
        "outcome": "continued_degraded",
        "success": False,
    }
    assert all("url" not in point.attributes for point in points)
