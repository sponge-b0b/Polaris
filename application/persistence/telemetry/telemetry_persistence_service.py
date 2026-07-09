from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.telemetry import AgentMetricRecord
from core.storage.persistence.telemetry import ProviderMetricRecord
from core.storage.persistence.telemetry import TelemetryEventRecord
from core.storage.persistence.telemetry import TelemetryMetricRecord
from core.storage.persistence.telemetry import TelemetryPersistenceBundle
from core.storage.persistence.telemetry import TelemetryPersistenceRepository
from core.storage.persistence.telemetry import TelemetryPersistenceResult
from core.storage.persistence.telemetry import TelemetryTraceRecord
from core.storage.persistence.telemetry import WorkflowMetricRecord
from core.storage.persistence.query import PersistenceCommonQuery
from core.storage.persistence.query import PersistenceListResult

from application.persistence.query_result_helpers import build_common_query
from application.persistence.query_result_helpers import build_list_result


@dataclass(
    frozen=True,
    slots=True,
)
class TelemetryEventPersistenceFilters:
    """
    Typed application-layer filters for operational telemetry events.
    """

    event_type: str | None = None
    source: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    correlation_id: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        _set_optional_identifier(self, "event_type", self.event_type)
        _set_optional_identifier(self, "source", self.source)
        _set_optional_identifier(self, "workflow_name", self.workflow_name)
        _set_optional_identifier(self, "execution_id", self.execution_id)
        _set_optional_identifier(self, "correlation_id", self.correlation_id)
        _require_ordered_time_window(self.start, self.end)


@dataclass(
    frozen=True,
    slots=True,
)
class TelemetryMetricPersistenceFilters:
    """
    Typed application-layer filters for generic telemetry metrics.
    """

    metric_name: str | None = None
    source: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    correlation_id: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        _set_optional_identifier(self, "metric_name", self.metric_name)
        _set_optional_identifier(self, "source", self.source)
        _set_optional_identifier(self, "workflow_name", self.workflow_name)
        _set_optional_identifier(self, "execution_id", self.execution_id)
        _set_optional_identifier(self, "correlation_id", self.correlation_id)
        _require_ordered_time_window(self.start, self.end)


@dataclass(
    frozen=True,
    slots=True,
)
class TelemetryTracePersistenceFilters:
    """
    Typed application-layer filters for persisted telemetry traces.
    """

    trace_id: str | None = None
    operation_name: str | None = None
    source: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    correlation_id: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        _set_optional_identifier(self, "trace_id", self.trace_id)
        _set_optional_identifier(self, "operation_name", self.operation_name)
        _set_optional_identifier(self, "source", self.source)
        _set_optional_identifier(self, "workflow_name", self.workflow_name)
        _set_optional_identifier(self, "execution_id", self.execution_id)
        _set_optional_identifier(self, "correlation_id", self.correlation_id)
        _require_ordered_time_window(self.start, self.end)


@dataclass(
    frozen=True,
    slots=True,
)
class WorkflowMetricPersistenceFilters:
    """
    Typed application-layer filters for workflow-scoped telemetry metrics.
    """

    workflow_name: str | None = None
    execution_id: str | None = None
    metric_name: str | None = None
    status: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        _set_optional_identifier(self, "workflow_name", self.workflow_name)
        _set_optional_identifier(self, "execution_id", self.execution_id)
        _set_optional_identifier(self, "metric_name", self.metric_name)
        _set_optional_identifier(self, "status", self.status)
        _require_ordered_time_window(self.start, self.end)


@dataclass(
    frozen=True,
    slots=True,
)
class AgentMetricPersistenceFilters:
    """
    Typed application-layer filters for agent-scoped telemetry metrics.
    """

    agent_name: str | None = None
    agent_type: str | None = None
    metric_name: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    symbol: str | None = None
    universe: str | None = None
    correlation_id: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        _set_optional_identifier(self, "agent_name", self.agent_name)
        _set_optional_identifier(self, "agent_type", self.agent_type)
        _set_optional_identifier(self, "metric_name", self.metric_name)
        _set_optional_identifier(self, "workflow_name", self.workflow_name)
        _set_optional_identifier(self, "execution_id", self.execution_id)
        object.__setattr__(
            self,
            "symbol",
            _clean_optional_symbol(self.symbol),
        )
        _set_optional_identifier(self, "universe", self.universe)
        _set_optional_identifier(self, "correlation_id", self.correlation_id)
        _require_ordered_time_window(self.start, self.end)


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderMetricPersistenceFilters:
    """
    Typed application-layer filters for provider-scoped telemetry metrics.
    """

    provider_name: str | None = None
    provider_type: str | None = None
    metric_name: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    endpoint: str | None = None
    success: bool | None = None
    correlation_id: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        _set_optional_identifier(self, "provider_name", self.provider_name)
        _set_optional_identifier(self, "provider_type", self.provider_type)
        _set_optional_identifier(self, "metric_name", self.metric_name)
        _set_optional_identifier(self, "workflow_name", self.workflow_name)
        _set_optional_identifier(self, "execution_id", self.execution_id)
        _set_optional_identifier(self, "endpoint", self.endpoint)
        _set_optional_identifier(self, "correlation_id", self.correlation_id)
        _require_ordered_time_window(self.start, self.end)


class TelemetryPersistenceService:
    """
    Application service for optional PostgreSQL telemetry persistence.

    This service coordinates typed telemetry persistence through the repository
    protocol only. It intentionally does not replace or auto-wire the existing
    JSONL runtime telemetry path.
    """

    def __init__(
        self,
        repository: TelemetryPersistenceRepository,
    ) -> None:
        self._repository = repository

    async def persist_telemetry_bundle(
        self,
        bundle: TelemetryPersistenceBundle,
    ) -> TelemetryPersistenceResult:
        return await self._repository.persist_telemetry_bundle(
            bundle,
        )

    async def persist_event(
        self,
        event: TelemetryEventRecord,
    ) -> TelemetryPersistenceResult:
        return await self._repository.persist_event(
            event,
        )

    async def persist_metric(
        self,
        metric: TelemetryMetricRecord,
    ) -> TelemetryPersistenceResult:
        return await self._repository.persist_metric(
            metric,
        )

    async def persist_trace(
        self,
        trace: TelemetryTraceRecord,
    ) -> TelemetryPersistenceResult:
        return await self._repository.persist_trace(
            trace,
        )

    async def persist_workflow_metric(
        self,
        metric: WorkflowMetricRecord,
    ) -> TelemetryPersistenceResult:
        return await self._repository.persist_workflow_metric(
            metric,
        )

    async def persist_agent_metric(
        self,
        metric: AgentMetricRecord,
    ) -> TelemetryPersistenceResult:
        return await self._repository.persist_agent_metric(
            metric,
        )

    async def persist_provider_metric(
        self,
        metric: ProviderMetricRecord,
    ) -> TelemetryPersistenceResult:
        return await self._repository.persist_provider_metric(
            metric,
        )

    async def get_event(
        self,
        telemetry_event_id: str,
    ) -> TelemetryEventRecord | None:
        return await self._repository.get_event(
            telemetry_event_id,
        )

    async def get_metric(
        self,
        metric_id: str,
    ) -> TelemetryMetricRecord | None:
        return await self._repository.get_metric(
            metric_id,
        )

    async def get_trace(
        self,
        trace_record_id: str,
    ) -> TelemetryTraceRecord | None:
        return await self._repository.get_trace(
            trace_record_id,
        )

    async def get_workflow_metric(
        self,
        workflow_metric_id: str,
    ) -> WorkflowMetricRecord | None:
        return await self._repository.get_workflow_metric(
            workflow_metric_id,
        )

    async def get_agent_metric(
        self,
        agent_metric_id: str,
    ) -> AgentMetricRecord | None:
        return await self._repository.get_agent_metric(
            agent_metric_id,
        )

    async def get_provider_metric(
        self,
        provider_metric_id: str,
    ) -> ProviderMetricRecord | None:
        return await self._repository.get_provider_metric(
            provider_metric_id,
        )

    async def list_events(
        self,
        filters: TelemetryEventPersistenceFilters | None = None,
    ) -> Sequence[TelemetryEventRecord]:
        result = await self.list_events_result(
            filters,
        )
        return result.records

    async def list_events_result(
        self,
        filters: TelemetryEventPersistenceFilters | None = None,
    ) -> PersistenceListResult[TelemetryEventRecord]:
        active_filters = filters or TelemetryEventPersistenceFilters()
        records = await self._repository.list_events(
            event_type=active_filters.event_type,
            source=active_filters.source,
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            correlation_id=active_filters.correlation_id,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = _build_telemetry_query(
            record_type="telemetry_event",
            filters=active_filters,
            source=active_filters.source,
            metadata={
                "event_type": active_filters.event_type,
                "correlation_id": active_filters.correlation_id,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_metrics(
        self,
        filters: TelemetryMetricPersistenceFilters | None = None,
    ) -> Sequence[TelemetryMetricRecord]:
        result = await self.list_metrics_result(
            filters,
        )
        return result.records

    async def list_metrics_result(
        self,
        filters: TelemetryMetricPersistenceFilters | None = None,
    ) -> PersistenceListResult[TelemetryMetricRecord]:
        active_filters = filters or TelemetryMetricPersistenceFilters()
        records = await self._repository.list_metrics(
            metric_name=active_filters.metric_name,
            source=active_filters.source,
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            correlation_id=active_filters.correlation_id,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = _build_telemetry_query(
            record_type="telemetry_metric",
            filters=active_filters,
            source=active_filters.source,
            metadata={
                "metric_name": active_filters.metric_name,
                "correlation_id": active_filters.correlation_id,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_traces(
        self,
        filters: TelemetryTracePersistenceFilters | None = None,
    ) -> Sequence[TelemetryTraceRecord]:
        result = await self.list_traces_result(
            filters,
        )
        return result.records

    async def list_traces_result(
        self,
        filters: TelemetryTracePersistenceFilters | None = None,
    ) -> PersistenceListResult[TelemetryTraceRecord]:
        active_filters = filters or TelemetryTracePersistenceFilters()
        records = await self._repository.list_traces(
            trace_id=active_filters.trace_id,
            operation_name=active_filters.operation_name,
            source=active_filters.source,
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            correlation_id=active_filters.correlation_id,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = _build_telemetry_query(
            record_type="telemetry_trace",
            filters=active_filters,
            source=active_filters.source,
            metadata={
                "trace_id": active_filters.trace_id,
                "operation_name": active_filters.operation_name,
                "correlation_id": active_filters.correlation_id,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_workflow_metrics(
        self,
        filters: WorkflowMetricPersistenceFilters | None = None,
    ) -> Sequence[WorkflowMetricRecord]:
        result = await self.list_workflow_metrics_result(
            filters,
        )
        return result.records

    async def list_workflow_metrics_result(
        self,
        filters: WorkflowMetricPersistenceFilters | None = None,
    ) -> PersistenceListResult[WorkflowMetricRecord]:
        active_filters = filters or WorkflowMetricPersistenceFilters()
        records = await self._repository.list_workflow_metrics(
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            metric_name=active_filters.metric_name,
            status=active_filters.status,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = _build_telemetry_query(
            record_type="workflow_metric",
            filters=active_filters,
            metadata={
                "metric_name": active_filters.metric_name,
                "status": active_filters.status,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_agent_metrics(
        self,
        filters: AgentMetricPersistenceFilters | None = None,
    ) -> Sequence[AgentMetricRecord]:
        result = await self.list_agent_metrics_result(
            filters,
        )
        return result.records

    async def list_agent_metrics_result(
        self,
        filters: AgentMetricPersistenceFilters | None = None,
    ) -> PersistenceListResult[AgentMetricRecord]:
        active_filters = filters or AgentMetricPersistenceFilters()
        records = await self._repository.list_agent_metrics(
            agent_name=active_filters.agent_name,
            agent_type=active_filters.agent_type,
            metric_name=active_filters.metric_name,
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            symbol=active_filters.symbol,
            universe=active_filters.universe,
            correlation_id=active_filters.correlation_id,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = _build_telemetry_query(
            record_type="agent_metric",
            filters=active_filters,
            symbol=active_filters.symbol,
            metadata={
                "agent_name": active_filters.agent_name,
                "agent_type": active_filters.agent_type,
                "metric_name": active_filters.metric_name,
                "universe": active_filters.universe,
                "correlation_id": active_filters.correlation_id,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_provider_metrics(
        self,
        filters: ProviderMetricPersistenceFilters | None = None,
    ) -> Sequence[ProviderMetricRecord]:
        result = await self.list_provider_metrics_result(
            filters,
        )
        return result.records

    async def list_provider_metrics_result(
        self,
        filters: ProviderMetricPersistenceFilters | None = None,
    ) -> PersistenceListResult[ProviderMetricRecord]:
        active_filters = filters or ProviderMetricPersistenceFilters()
        records = await self._repository.list_provider_metrics(
            provider_name=active_filters.provider_name,
            provider_type=active_filters.provider_type,
            metric_name=active_filters.metric_name,
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            endpoint=active_filters.endpoint,
            success=active_filters.success,
            correlation_id=active_filters.correlation_id,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = _build_telemetry_query(
            record_type="provider_metric",
            filters=active_filters,
            metadata={
                "provider_name": active_filters.provider_name,
                "provider_type": active_filters.provider_type,
                "metric_name": active_filters.metric_name,
                "endpoint": active_filters.endpoint,
                "success": active_filters.success,
                "correlation_id": active_filters.correlation_id,
            },
        )
        return build_list_result(
            records,
            query=query,
        )


def _build_telemetry_query(
    *,
    record_type: str,
    filters: TelemetryEventPersistenceFilters
    | TelemetryMetricPersistenceFilters
    | TelemetryTracePersistenceFilters
    | WorkflowMetricPersistenceFilters
    | AgentMetricPersistenceFilters
    | ProviderMetricPersistenceFilters,
    source: str | None = None,
    symbol: str | None = None,
    metadata: dict[str, str | bool | None] | None = None,
) -> PersistenceCommonQuery:
    return build_common_query(
        record_type=record_type,
        source=source,
        workflow_name=filters.workflow_name,
        execution_id=filters.execution_id,
        symbol=symbol,
        start=filters.start,
        end=filters.end,
        metadata=metadata,
    )


def _set_optional_identifier(
    record: object,
    field_name: str,
    value: str | None,
) -> None:
    object.__setattr__(
        record,
        field_name,
        clean_optional_identifier(
            value,
            field_name,
        ),
    )


def _clean_optional_symbol(
    symbol: str | None,
) -> str | None:
    clean_symbol = clean_optional_identifier(
        symbol,
        "symbol",
    )
    if clean_symbol is None:
        return None

    return clean_symbol.upper()


def _require_ordered_time_window(
    start: datetime | None,
    end: datetime | None,
) -> None:
    if start is not None and end is not None and start > end:
        raise ValueError("start must be less than or equal to end.")
