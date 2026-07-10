from __future__ import annotations

from datetime import datetime
from typing import Protocol
from typing import Sequence

from core.storage.persistence.telemetry.telemetry_persistence_models import (
    AgentMetricRecord,
)
from core.storage.persistence.telemetry.telemetry_persistence_models import (
    ProviderMetricRecord,
)
from core.storage.persistence.telemetry.telemetry_persistence_models import (
    TelemetryEventRecord,
)
from core.storage.persistence.telemetry.telemetry_persistence_models import (
    TelemetryMetricRecord,
)
from core.storage.persistence.telemetry.telemetry_persistence_models import (
    TelemetryPersistenceBundle,
)
from core.storage.persistence.telemetry.telemetry_persistence_models import (
    TelemetryPersistenceResult,
)
from core.storage.persistence.telemetry.telemetry_persistence_models import (
    TelemetryTraceRecord,
)
from core.storage.persistence.telemetry.telemetry_persistence_models import (
    WorkflowMetricRecord,
)


class TelemetryPersistenceRepository(Protocol):
    """
    Async repository contract for durable operational telemetry persistence.

    Events and traces are append-friendly audit records. Metrics are persisted
    by stable metric identity, allowing caller-selected append or upsert behavior
    through metric IDs that include identity and timestamp when desired.
    """

    async def persist_telemetry_bundle(
        self,
        bundle: TelemetryPersistenceBundle,
    ) -> TelemetryPersistenceResult: ...

    async def persist_event(
        self,
        event: TelemetryEventRecord,
    ) -> TelemetryPersistenceResult: ...

    async def persist_metric(
        self,
        metric: TelemetryMetricRecord,
    ) -> TelemetryPersistenceResult: ...

    async def persist_trace(
        self,
        trace: TelemetryTraceRecord,
    ) -> TelemetryPersistenceResult: ...

    async def persist_workflow_metric(
        self,
        metric: WorkflowMetricRecord,
    ) -> TelemetryPersistenceResult: ...

    async def persist_agent_metric(
        self,
        metric: AgentMetricRecord,
    ) -> TelemetryPersistenceResult: ...

    async def persist_provider_metric(
        self,
        metric: ProviderMetricRecord,
    ) -> TelemetryPersistenceResult: ...

    async def get_event(
        self,
        telemetry_event_id: str,
    ) -> TelemetryEventRecord | None: ...

    async def get_metric(
        self,
        metric_id: str,
    ) -> TelemetryMetricRecord | None: ...

    async def get_trace(
        self,
        trace_record_id: str,
    ) -> TelemetryTraceRecord | None: ...

    async def get_workflow_metric(
        self,
        workflow_metric_id: str,
    ) -> WorkflowMetricRecord | None: ...

    async def get_agent_metric(
        self,
        agent_metric_id: str,
    ) -> AgentMetricRecord | None: ...

    async def get_provider_metric(
        self,
        provider_metric_id: str,
    ) -> ProviderMetricRecord | None: ...

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
    ) -> Sequence[TelemetryEventRecord]: ...

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
    ) -> Sequence[TelemetryMetricRecord]: ...

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
    ) -> Sequence[TelemetryTraceRecord]: ...

    async def list_workflow_metrics(
        self,
        *,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        metric_name: str | None = None,
        status: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[WorkflowMetricRecord]: ...

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
    ) -> Sequence[AgentMetricRecord]: ...

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
    ) -> Sequence[ProviderMetricRecord]: ...
