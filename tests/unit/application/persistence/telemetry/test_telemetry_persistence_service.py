from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone

import pytest

from application.persistence.telemetry import AgentMetricPersistenceFilters
from application.persistence.telemetry import ProviderMetricPersistenceFilters
from application.persistence.telemetry import TelemetryEventPersistenceFilters
from application.persistence.telemetry import TelemetryMetricPersistenceFilters
from application.persistence.telemetry import TelemetryPersistenceService
from application.persistence.telemetry import TelemetryTracePersistenceFilters
from application.persistence.telemetry import WorkflowMetricPersistenceFilters
from core.storage.persistence.telemetry import AgentMetricRecord
from core.storage.persistence.telemetry import ProviderMetricRecord
from core.storage.persistence.telemetry import TelemetryEventRecord
from core.storage.persistence.telemetry import TelemetryMetricRecord
from core.storage.persistence.telemetry import TelemetryPersistenceBundle
from core.storage.persistence.telemetry import TelemetryPersistenceResult
from core.storage.persistence.telemetry import TelemetryTraceRecord
from core.storage.persistence.telemetry import WorkflowMetricRecord


class FakeTelemetryRepository:
    def __init__(
        self,
        *,
        event: TelemetryEventRecord | None = None,
        metric: TelemetryMetricRecord | None = None,
        trace: TelemetryTraceRecord | None = None,
        workflow_metric: WorkflowMetricRecord | None = None,
        agent_metric: AgentMetricRecord | None = None,
        provider_metric: ProviderMetricRecord | None = None,
    ) -> None:
        self.bundle: TelemetryPersistenceBundle | None = None
        self.persisted_event: TelemetryEventRecord | None = None
        self.persisted_metric: TelemetryMetricRecord | None = None
        self.persisted_trace: TelemetryTraceRecord | None = None
        self.persisted_workflow_metric: WorkflowMetricRecord | None = None
        self.persisted_agent_metric: AgentMetricRecord | None = None
        self.persisted_provider_metric: ProviderMetricRecord | None = None
        self.event = event
        self.metric = metric
        self.trace = trace
        self.workflow_metric = workflow_metric
        self.agent_metric = agent_metric
        self.provider_metric = provider_metric
        self.event_filters: dict[str, object] | None = None
        self.metric_filters: dict[str, object] | None = None
        self.trace_filters: dict[str, object] | None = None
        self.workflow_metric_filters: dict[str, object] | None = None
        self.agent_metric_filters: dict[str, object] | None = None
        self.provider_metric_filters: dict[str, object] | None = None

    async def persist_telemetry_bundle(
        self,
        bundle: TelemetryPersistenceBundle,
    ) -> TelemetryPersistenceResult:
        self.bundle = bundle
        return TelemetryPersistenceResult.succeeded(
            primary_record_id=_primary_record_id(bundle),
            records_persisted=(
                len(bundle.events)
                + len(bundle.metrics)
                + len(bundle.traces)
                + len(bundle.workflow_metrics)
                + len(bundle.agent_metrics)
                + len(bundle.provider_metrics)
            ),
        )

    async def persist_event(
        self,
        event: TelemetryEventRecord,
    ) -> TelemetryPersistenceResult:
        self.persisted_event = event
        return TelemetryPersistenceResult.succeeded(
            primary_record_id=event.telemetry_event_id,
        )

    async def persist_metric(
        self,
        metric: TelemetryMetricRecord,
    ) -> TelemetryPersistenceResult:
        self.persisted_metric = metric
        return TelemetryPersistenceResult.succeeded(
            primary_record_id=metric.metric_id,
        )

    async def persist_trace(
        self,
        trace: TelemetryTraceRecord,
    ) -> TelemetryPersistenceResult:
        self.persisted_trace = trace
        return TelemetryPersistenceResult.succeeded(
            primary_record_id=trace.trace_record_id,
        )

    async def persist_workflow_metric(
        self,
        metric: WorkflowMetricRecord,
    ) -> TelemetryPersistenceResult:
        self.persisted_workflow_metric = metric
        return TelemetryPersistenceResult.succeeded(
            primary_record_id=metric.workflow_metric_id,
        )

    async def persist_agent_metric(
        self,
        metric: AgentMetricRecord,
    ) -> TelemetryPersistenceResult:
        self.persisted_agent_metric = metric
        return TelemetryPersistenceResult.succeeded(
            primary_record_id=metric.agent_metric_id,
        )

    async def persist_provider_metric(
        self,
        metric: ProviderMetricRecord,
    ) -> TelemetryPersistenceResult:
        self.persisted_provider_metric = metric
        return TelemetryPersistenceResult.succeeded(
            primary_record_id=metric.provider_metric_id,
        )

    async def get_event(
        self,
        telemetry_event_id: str,
    ) -> TelemetryEventRecord | None:
        if self.event and self.event.telemetry_event_id == telemetry_event_id:
            return self.event
        return None

    async def get_metric(
        self,
        metric_id: str,
    ) -> TelemetryMetricRecord | None:
        if self.metric and self.metric.metric_id == metric_id:
            return self.metric
        return None

    async def get_trace(
        self,
        trace_record_id: str,
    ) -> TelemetryTraceRecord | None:
        if self.trace and self.trace.trace_record_id == trace_record_id:
            return self.trace
        return None

    async def get_workflow_metric(
        self,
        workflow_metric_id: str,
    ) -> WorkflowMetricRecord | None:
        if (
            self.workflow_metric
            and self.workflow_metric.workflow_metric_id == workflow_metric_id
        ):
            return self.workflow_metric
        return None

    async def get_agent_metric(
        self,
        agent_metric_id: str,
    ) -> AgentMetricRecord | None:
        if self.agent_metric and self.agent_metric.agent_metric_id == agent_metric_id:
            return self.agent_metric
        return None

    async def get_provider_metric(
        self,
        provider_metric_id: str,
    ) -> ProviderMetricRecord | None:
        if (
            self.provider_metric
            and self.provider_metric.provider_metric_id == provider_metric_id
        ):
            return self.provider_metric
        return None

    async def list_events(
        self,
        *,
        event_type: str | None = None,
        source: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        correlation_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[TelemetryEventRecord]:
        self.event_filters = {
            "event_type": event_type,
            "source": source,
            "workflow_name": workflow_name,
            "execution_id": execution_id,
            "correlation_id": correlation_id,
            "start": start,
            "end": end,
        }
        return (self.event,) if self.event else ()

    async def list_metrics(
        self,
        *,
        metric_name: str | None = None,
        source: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        correlation_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[TelemetryMetricRecord]:
        self.metric_filters = {
            "metric_name": metric_name,
            "source": source,
            "workflow_name": workflow_name,
            "execution_id": execution_id,
            "correlation_id": correlation_id,
            "start": start,
            "end": end,
        }
        return (self.metric,) if self.metric else ()

    async def list_traces(
        self,
        *,
        trace_id: str | None = None,
        operation_name: str | None = None,
        source: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        correlation_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[TelemetryTraceRecord]:
        self.trace_filters = {
            "trace_id": trace_id,
            "operation_name": operation_name,
            "source": source,
            "workflow_name": workflow_name,
            "execution_id": execution_id,
            "correlation_id": correlation_id,
            "start": start,
            "end": end,
        }
        return (self.trace,) if self.trace else ()

    async def list_workflow_metrics(
        self,
        *,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        metric_name: str | None = None,
        status: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[WorkflowMetricRecord]:
        self.workflow_metric_filters = {
            "workflow_name": workflow_name,
            "execution_id": execution_id,
            "metric_name": metric_name,
            "status": status,
            "start": start,
            "end": end,
        }
        return (self.workflow_metric,) if self.workflow_metric else ()

    async def list_agent_metrics(
        self,
        *,
        agent_name: str | None = None,
        agent_type: str | None = None,
        metric_name: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        correlation_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[AgentMetricRecord]:
        self.agent_metric_filters = {
            "agent_name": agent_name,
            "agent_type": agent_type,
            "metric_name": metric_name,
            "workflow_name": workflow_name,
            "execution_id": execution_id,
            "symbol": symbol,
            "universe": universe,
            "correlation_id": correlation_id,
            "start": start,
            "end": end,
        }
        return (self.agent_metric,) if self.agent_metric else ()

    async def list_provider_metrics(
        self,
        *,
        provider_name: str | None = None,
        provider_type: str | None = None,
        metric_name: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        endpoint: str | None = None,
        success: bool | None = None,
        correlation_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[ProviderMetricRecord]:
        self.provider_metric_filters = {
            "provider_name": provider_name,
            "provider_type": provider_type,
            "metric_name": metric_name,
            "workflow_name": workflow_name,
            "execution_id": execution_id,
            "endpoint": endpoint,
            "success": success,
            "correlation_id": correlation_id,
            "start": start,
            "end": end,
        }
        return (self.provider_metric,) if self.provider_metric else ()


@pytest.mark.asyncio
async def test_telemetry_persistence_service_persists_existing_bundle() -> None:
    repository = FakeTelemetryRepository()
    service = TelemetryPersistenceService(repository)
    bundle = _bundle()

    result = await service.persist_telemetry_bundle(bundle)

    assert result.success is True
    assert result.records_persisted == 6
    assert repository.bundle == bundle


@pytest.mark.asyncio
async def test_telemetry_persistence_service_delegates_individual_persists() -> None:
    repository = FakeTelemetryRepository()
    service = TelemetryPersistenceService(repository)
    bundle = _bundle()

    event_result = await service.persist_event(bundle.events[0])
    metric_result = await service.persist_metric(bundle.metrics[0])
    trace_result = await service.persist_trace(bundle.traces[0])
    workflow_result = await service.persist_workflow_metric(bundle.workflow_metrics[0])
    agent_result = await service.persist_agent_metric(bundle.agent_metrics[0])
    provider_result = await service.persist_provider_metric(bundle.provider_metrics[0])

    assert event_result.primary_record_id == "telemetry-event-1"
    assert metric_result.primary_record_id == "telemetry-metric-1"
    assert trace_result.primary_record_id == "telemetry-trace-1"
    assert workflow_result.primary_record_id == "workflow-metric-1"
    assert agent_result.primary_record_id == "agent-metric-1"
    assert provider_result.primary_record_id == "provider-metric-1"
    assert repository.persisted_event == bundle.events[0]
    assert repository.persisted_metric == bundle.metrics[0]
    assert repository.persisted_trace == bundle.traces[0]
    assert repository.persisted_workflow_metric == bundle.workflow_metrics[0]
    assert repository.persisted_agent_metric == bundle.agent_metrics[0]
    assert repository.persisted_provider_metric == bundle.provider_metrics[0]


@pytest.mark.asyncio
async def test_telemetry_persistence_service_returns_typed_records_by_id() -> None:
    bundle = _bundle()
    repository = FakeTelemetryRepository(
        event=bundle.events[0],
        metric=bundle.metrics[0],
        trace=bundle.traces[0],
        workflow_metric=bundle.workflow_metrics[0],
        agent_metric=bundle.agent_metrics[0],
        provider_metric=bundle.provider_metrics[0],
    )
    service = TelemetryPersistenceService(repository)

    event = await service.get_event("telemetry-event-1")
    metric = await service.get_metric("telemetry-metric-1")
    trace = await service.get_trace("telemetry-trace-1")
    workflow_metric = await service.get_workflow_metric("workflow-metric-1")
    agent_metric = await service.get_agent_metric("agent-metric-1")
    provider_metric = await service.get_provider_metric("provider-metric-1")

    assert event == bundle.events[0]
    assert metric == bundle.metrics[0]
    assert trace == bundle.traces[0]
    assert workflow_metric == bundle.workflow_metrics[0]
    assert agent_metric == bundle.agent_metrics[0]
    assert provider_metric == bundle.provider_metrics[0]


@pytest.mark.asyncio
async def test_telemetry_persistence_service_uses_typed_filters() -> None:
    bundle = _bundle()
    repository = FakeTelemetryRepository(
        event=bundle.events[0],
        metric=bundle.metrics[0],
        trace=bundle.traces[0],
        workflow_metric=bundle.workflow_metrics[0],
        agent_metric=bundle.agent_metrics[0],
        provider_metric=bundle.provider_metrics[0],
    )
    service = TelemetryPersistenceService(repository)
    start = _timestamp()
    end = datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc)

    events = await service.list_events(
        TelemetryEventPersistenceFilters(
            event_type=" workflow.started ",
            source=" runtime ",
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
            correlation_id=" corr-1 ",
            start=start,
            end=end,
        )
    )
    metrics = await service.list_metrics(
        TelemetryMetricPersistenceFilters(
            metric_name=" duration_seconds ",
            source=" runtime ",
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
            correlation_id=" corr-1 ",
            start=start,
            end=end,
        )
    )
    traces = await service.list_traces(
        TelemetryTracePersistenceFilters(
            trace_id=" trace-1 ",
            operation_name=" execute_workflow ",
            source=" runtime ",
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
            correlation_id=" corr-1 ",
            start=start,
            end=end,
        )
    )
    workflow_metrics = await service.list_workflow_metrics(
        WorkflowMetricPersistenceFilters(
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
            metric_name=" duration_seconds ",
            status=" succeeded ",
            start=start,
            end=end,
        )
    )
    agent_metrics = await service.list_agent_metrics(
        AgentMetricPersistenceFilters(
            agent_name=" macro_agent ",
            agent_type=" macro ",
            metric_name=" confidence ",
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
            symbol=" spy ",
            universe=" us_equities ",
            correlation_id=" corr-1 ",
            start=start,
            end=end,
        )
    )
    provider_metrics = await service.list_provider_metrics(
        ProviderMetricPersistenceFilters(
            provider_name=" fmp ",
            provider_type=" market_data ",
            metric_name=" latency_seconds ",
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
            endpoint=" quote ",
            success=True,
            correlation_id=" corr-1 ",
            start=start,
            end=end,
        )
    )

    assert len(events) == 1
    assert len(metrics) == 1
    assert len(traces) == 1
    assert len(workflow_metrics) == 1
    assert len(agent_metrics) == 1
    assert len(provider_metrics) == 1
    assert repository.event_filters == {
        "event_type": "workflow.started",
        "source": "runtime",
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "correlation_id": "corr-1",
        "start": start,
        "end": end,
    }
    assert repository.metric_filters == {
        "metric_name": "duration_seconds",
        "source": "runtime",
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "correlation_id": "corr-1",
        "start": start,
        "end": end,
    }
    assert repository.trace_filters == {
        "trace_id": "trace-1",
        "operation_name": "execute_workflow",
        "source": "runtime",
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "correlation_id": "corr-1",
        "start": start,
        "end": end,
    }
    assert repository.workflow_metric_filters == {
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "metric_name": "duration_seconds",
        "status": "succeeded",
        "start": start,
        "end": end,
    }
    assert repository.agent_metric_filters == {
        "agent_name": "macro_agent",
        "agent_type": "macro",
        "metric_name": "confidence",
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "symbol": "SPY",
        "universe": "us_equities",
        "correlation_id": "corr-1",
        "start": start,
        "end": end,
    }
    assert repository.provider_metric_filters == {
        "provider_name": "fmp",
        "provider_type": "market_data",
        "metric_name": "latency_seconds",
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "endpoint": "quote",
        "success": True,
        "correlation_id": "corr-1",
        "start": start,
        "end": end,
    }


@pytest.mark.asyncio
async def test_telemetry_persistence_service_uses_default_filters() -> None:
    repository = FakeTelemetryRepository()
    service = TelemetryPersistenceService(repository)

    await service.list_events()
    await service.list_metrics()
    await service.list_traces()
    await service.list_workflow_metrics()
    await service.list_agent_metrics()
    await service.list_provider_metrics()

    assert repository.event_filters == {
        "event_type": None,
        "source": None,
        "workflow_name": None,
        "execution_id": None,
        "correlation_id": None,
        "start": None,
        "end": None,
    }
    assert repository.metric_filters == {
        "metric_name": None,
        "source": None,
        "workflow_name": None,
        "execution_id": None,
        "correlation_id": None,
        "start": None,
        "end": None,
    }
    assert repository.trace_filters == {
        "trace_id": None,
        "operation_name": None,
        "source": None,
        "workflow_name": None,
        "execution_id": None,
        "correlation_id": None,
        "start": None,
        "end": None,
    }
    assert repository.workflow_metric_filters == {
        "workflow_name": None,
        "execution_id": None,
        "metric_name": None,
        "status": None,
        "start": None,
        "end": None,
    }
    assert repository.agent_metric_filters == {
        "agent_name": None,
        "agent_type": None,
        "metric_name": None,
        "workflow_name": None,
        "execution_id": None,
        "symbol": None,
        "universe": None,
        "correlation_id": None,
        "start": None,
        "end": None,
    }
    assert repository.provider_metric_filters == {
        "provider_name": None,
        "provider_type": None,
        "metric_name": None,
        "workflow_name": None,
        "execution_id": None,
        "endpoint": None,
        "success": None,
        "correlation_id": None,
        "start": None,
        "end": None,
    }


@pytest.mark.parametrize(
    "filters",
    [
        TelemetryEventPersistenceFilters,
        TelemetryMetricPersistenceFilters,
        TelemetryTracePersistenceFilters,
        WorkflowMetricPersistenceFilters,
        AgentMetricPersistenceFilters,
        ProviderMetricPersistenceFilters,
    ],
)
def test_telemetry_time_window_filters_require_ordered_bounds(
    filters: type[
        TelemetryEventPersistenceFilters
        | TelemetryMetricPersistenceFilters
        | TelemetryTracePersistenceFilters
        | WorkflowMetricPersistenceFilters
        | AgentMetricPersistenceFilters
        | ProviderMetricPersistenceFilters
    ],
) -> None:
    start = datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc)
    end = _timestamp()

    with pytest.raises(ValueError, match="start must be less than or equal to end"):
        filters(
            start=start,
            end=end,
        )


def _bundle() -> TelemetryPersistenceBundle:
    return TelemetryPersistenceBundle(
        events=(_event(),),
        metrics=(_metric(),),
        traces=(_trace(),),
        workflow_metrics=(_workflow_metric(),),
        agent_metrics=(_agent_metric(),),
        provider_metrics=(_provider_metric(),),
    )


def _event() -> TelemetryEventRecord:
    return TelemetryEventRecord(
        telemetry_event_id="telemetry-event-1",
        event_type="workflow.started",
        source="runtime",
        timestamp=_timestamp(),
        severity="info",
        message="Workflow started.",
        correlation_id="corr-1",
        payload={"workflow_name": "morning_report"},
    )


def _metric() -> TelemetryMetricRecord:
    return TelemetryMetricRecord(
        metric_id="telemetry-metric-1",
        metric_name="duration_seconds",
        source="runtime",
        timestamp=_timestamp(),
        metric_value=1.25,
        metric_unit="seconds",
        metric_kind="gauge",
        correlation_id="corr-1",
        dimensions={"workflow_name": "morning_report"},
    )


def _trace() -> TelemetryTraceRecord:
    return TelemetryTraceRecord(
        trace_record_id="telemetry-trace-1",
        trace_id="trace-1",
        span_id="span-1",
        operation_name="execute_workflow",
        source="runtime",
        started_at=_timestamp(),
        ended_at=datetime(2026, 5, 31, 14, 1, tzinfo=timezone.utc),
        duration_seconds=60.0,
        status="succeeded",
        correlation_id="corr-1",
    )


def _workflow_metric() -> WorkflowMetricRecord:
    return WorkflowMetricRecord(
        workflow_metric_id="workflow-metric-1",
        workflow_name="morning_report",
        metric_name="duration_seconds",
        timestamp=_timestamp(),
        metric_value=60.0,
        execution_id="exec-1",
        runtime_id="runtime-1",
        status="succeeded",
    )


def _agent_metric() -> AgentMetricRecord:
    return AgentMetricRecord(
        agent_metric_id="agent-metric-1",
        agent_name="macro_agent",
        agent_type="macro",
        metric_name="confidence",
        timestamp=_timestamp(),
        metric_value=0.82,
        metric_unit="score",
        symbol="spy",
        universe="us_equities",
        correlation_id="corr-1",
    )


def _provider_metric() -> ProviderMetricRecord:
    return ProviderMetricRecord(
        provider_metric_id="provider-metric-1",
        provider_name="fmp",
        provider_type="market_data",
        metric_name="latency_seconds",
        timestamp=_timestamp(),
        metric_value=0.42,
        metric_unit="seconds",
        endpoint="quote",
        status_code=200,
        success=True,
        correlation_id="corr-1",
    )


def _primary_record_id(
    bundle: TelemetryPersistenceBundle,
) -> str:
    if bundle.events:
        return bundle.events[0].telemetry_event_id
    if bundle.metrics:
        return bundle.metrics[0].metric_id
    if bundle.traces:
        return bundle.traces[0].trace_record_id
    if bundle.workflow_metrics:
        return bundle.workflow_metrics[0].workflow_metric_id
    if bundle.agent_metrics:
        return bundle.agent_metrics[0].agent_metric_id
    if bundle.provider_metrics:
        return bundle.provider_metrics[0].provider_metric_id
    return "empty-telemetry-persistence-bundle"


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc)
