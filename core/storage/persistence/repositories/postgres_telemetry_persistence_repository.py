from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy import case
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.telemetry import AgentMetricModel
from core.database.models.telemetry import ProviderMetricModel
from core.database.models.telemetry import TelemetryEventModel
from core.database.models.telemetry import TelemetryMetricModel
from core.database.models.telemetry import TelemetryTraceModel
from core.database.models.telemetry import WorkflowMetricModel
from core.storage.persistence.serializers.telemetry_persistence_serializer import (
    TelemetryPersistenceSerializer,
)
from core.storage.persistence.telemetry import AgentMetricRecord
from core.storage.persistence.telemetry import ProviderMetricRecord
from core.storage.persistence.telemetry import TelemetryEventRecord
from core.storage.persistence.telemetry import TelemetryMetricRecord
from core.storage.persistence.telemetry import TelemetryPersistenceBundle
from core.storage.persistence.telemetry import TelemetryPersistenceRepository
from core.storage.persistence.telemetry import TelemetryPersistenceResult
from core.storage.persistence.telemetry import TelemetryTraceRecord
from core.storage.persistence.telemetry import WorkflowMetricRecord


class PostgresTelemetryPersistenceRepository(TelemetryPersistenceRepository):
    """
    PostgreSQL adapter for durable operational telemetry persistence.

    Events are immutable records keyed by canonical event id. Trace lifecycle
    observations assemble into one row per canonical trace/span pair. Metric
    families use upserts by stable metric id, so a caller can append by
    generating timestamped IDs or overwrite one logical sample by reusing the
    same metric identity.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_telemetry_bundle(
        self,
        bundle: TelemetryPersistenceBundle,
    ) -> TelemetryPersistenceResult:
        try:
            for event in bundle.events:
                await self._session.execute(_insert_event_statement(event))
            for telemetry_metric in bundle.metrics:
                await self._session.execute(_upsert_metric_statement(telemetry_metric))
            for trace in bundle.traces:
                await self._session.execute(_insert_trace_statement(trace))
            for workflow_metric in bundle.workflow_metrics:
                await self._session.execute(
                    _upsert_workflow_metric_statement(workflow_metric)
                )
            for agent_metric in bundle.agent_metrics:
                await self._session.execute(
                    _upsert_agent_metric_statement(agent_metric)
                )
            for provider_metric in bundle.provider_metrics:
                await self._session.execute(
                    _upsert_provider_metric_statement(provider_metric)
                )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return TelemetryPersistenceResult.failed(str(exc))

        return TelemetryPersistenceResult.succeeded(
            primary_record_id=_bundle_primary_record_id(bundle),
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
        return await self.persist_telemetry_bundle(
            TelemetryPersistenceBundle(events=(event,))
        )

    async def persist_metric(
        self,
        metric: TelemetryMetricRecord,
    ) -> TelemetryPersistenceResult:
        return await self.persist_telemetry_bundle(
            TelemetryPersistenceBundle(metrics=(metric,))
        )

    async def persist_trace(
        self,
        trace: TelemetryTraceRecord,
    ) -> TelemetryPersistenceResult:
        return await self.persist_telemetry_bundle(
            TelemetryPersistenceBundle(traces=(trace,))
        )

    async def persist_workflow_metric(
        self,
        metric: WorkflowMetricRecord,
    ) -> TelemetryPersistenceResult:
        return await self.persist_telemetry_bundle(
            TelemetryPersistenceBundle(workflow_metrics=(metric,))
        )

    async def persist_agent_metric(
        self,
        metric: AgentMetricRecord,
    ) -> TelemetryPersistenceResult:
        return await self.persist_telemetry_bundle(
            TelemetryPersistenceBundle(agent_metrics=(metric,))
        )

    async def persist_provider_metric(
        self,
        metric: ProviderMetricRecord,
    ) -> TelemetryPersistenceResult:
        return await self.persist_telemetry_bundle(
            TelemetryPersistenceBundle(provider_metrics=(metric,))
        )

    async def get_event(
        self,
        telemetry_event_id: str,
    ) -> TelemetryEventRecord | None:
        stmt = select(TelemetryEventModel).where(
            TelemetryEventModel.telemetry_event_id == telemetry_event_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return TelemetryPersistenceSerializer.event_from_model(model)

    async def get_metric(
        self,
        metric_id: str,
    ) -> TelemetryMetricRecord | None:
        stmt = select(TelemetryMetricModel).where(
            TelemetryMetricModel.metric_id == metric_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return TelemetryPersistenceSerializer.metric_from_model(model)

    async def get_trace(
        self,
        trace_record_id: str,
    ) -> TelemetryTraceRecord | None:
        stmt = select(TelemetryTraceModel).where(
            TelemetryTraceModel.trace_record_id == trace_record_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return TelemetryPersistenceSerializer.trace_from_model(model)

    async def get_workflow_metric(
        self,
        workflow_metric_id: str,
    ) -> WorkflowMetricRecord | None:
        stmt = select(WorkflowMetricModel).where(
            WorkflowMetricModel.workflow_metric_id == workflow_metric_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return TelemetryPersistenceSerializer.workflow_metric_from_model(model)

    async def get_agent_metric(
        self,
        agent_metric_id: str,
    ) -> AgentMetricRecord | None:
        stmt = select(AgentMetricModel).where(
            AgentMetricModel.agent_metric_id == agent_metric_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return TelemetryPersistenceSerializer.agent_metric_from_model(model)

    async def get_provider_metric(
        self,
        provider_metric_id: str,
    ) -> ProviderMetricRecord | None:
        stmt = select(ProviderMetricModel).where(
            ProviderMetricModel.provider_metric_id == provider_metric_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return TelemetryPersistenceSerializer.provider_metric_from_model(model)

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
        stmt = select(TelemetryEventModel)
        stmt = _where_if_not_none(stmt, TelemetryEventModel.event_type, event_type)
        stmt = _where_if_not_none(stmt, TelemetryEventModel.source, source)
        stmt = _where_if_not_none(
            stmt, TelemetryEventModel.workflow_name, workflow_name
        )
        stmt = _where_if_not_none(stmt, TelemetryEventModel.execution_id, execution_id)
        stmt = _where_if_not_none(
            stmt, TelemetryEventModel.correlation_id, correlation_id
        )
        stmt = _where_timestamp_window(stmt, TelemetryEventModel.timestamp, start, end)
        stmt = stmt.order_by(
            TelemetryEventModel.timestamp, TelemetryEventModel.event_type
        )
        result = await self._session.execute(stmt)

        return tuple(
            TelemetryPersistenceSerializer.event_from_model(model)
            for model in result.scalars().all()
        )

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
        stmt = select(TelemetryMetricModel)
        stmt = _where_if_not_none(stmt, TelemetryMetricModel.metric_name, metric_name)
        stmt = _where_if_not_none(stmt, TelemetryMetricModel.source, source)
        stmt = _where_if_not_none(
            stmt, TelemetryMetricModel.workflow_name, workflow_name
        )
        stmt = _where_if_not_none(stmt, TelemetryMetricModel.execution_id, execution_id)
        stmt = _where_if_not_none(
            stmt, TelemetryMetricModel.correlation_id, correlation_id
        )
        stmt = _where_timestamp_window(stmt, TelemetryMetricModel.timestamp, start, end)
        stmt = stmt.order_by(
            TelemetryMetricModel.timestamp, TelemetryMetricModel.metric_name
        )
        result = await self._session.execute(stmt)

        return tuple(
            TelemetryPersistenceSerializer.metric_from_model(model)
            for model in result.scalars().all()
        )

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
        stmt = select(TelemetryTraceModel)
        stmt = _where_if_not_none(stmt, TelemetryTraceModel.trace_id, trace_id)
        stmt = _where_if_not_none(
            stmt, TelemetryTraceModel.operation_name, operation_name
        )
        stmt = _where_if_not_none(stmt, TelemetryTraceModel.source, source)
        stmt = _where_if_not_none(
            stmt, TelemetryTraceModel.workflow_name, workflow_name
        )
        stmt = _where_if_not_none(stmt, TelemetryTraceModel.execution_id, execution_id)
        stmt = _where_if_not_none(
            stmt, TelemetryTraceModel.correlation_id, correlation_id
        )
        stmt = _where_timestamp_window(stmt, TelemetryTraceModel.started_at, start, end)
        stmt = stmt.order_by(
            TelemetryTraceModel.started_at, TelemetryTraceModel.operation_name
        )
        result = await self._session.execute(stmt)

        return tuple(
            TelemetryPersistenceSerializer.trace_from_model(model)
            for model in result.scalars().all()
        )

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
        stmt = select(WorkflowMetricModel)
        stmt = _where_if_not_none(
            stmt, WorkflowMetricModel.workflow_name, workflow_name
        )
        stmt = _where_if_not_none(stmt, WorkflowMetricModel.execution_id, execution_id)
        stmt = _where_if_not_none(stmt, WorkflowMetricModel.metric_name, metric_name)
        stmt = _where_if_not_none(stmt, WorkflowMetricModel.status, status)
        stmt = _where_timestamp_window(stmt, WorkflowMetricModel.timestamp, start, end)
        stmt = stmt.order_by(
            WorkflowMetricModel.timestamp, WorkflowMetricModel.metric_name
        )
        result = await self._session.execute(stmt)

        return tuple(
            TelemetryPersistenceSerializer.workflow_metric_from_model(model)
            for model in result.scalars().all()
        )

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
        stmt = select(AgentMetricModel)
        stmt = _where_if_not_none(stmt, AgentMetricModel.agent_name, agent_name)
        stmt = _where_if_not_none(stmt, AgentMetricModel.agent_type, agent_type)
        stmt = _where_if_not_none(stmt, AgentMetricModel.metric_name, metric_name)
        stmt = _where_if_not_none(stmt, AgentMetricModel.workflow_name, workflow_name)
        stmt = _where_if_not_none(stmt, AgentMetricModel.execution_id, execution_id)
        stmt = _where_if_not_none(stmt, AgentMetricModel.symbol, symbol)
        stmt = _where_if_not_none(stmt, AgentMetricModel.universe, universe)
        stmt = _where_if_not_none(stmt, AgentMetricModel.correlation_id, correlation_id)
        stmt = _where_timestamp_window(stmt, AgentMetricModel.timestamp, start, end)
        stmt = stmt.order_by(AgentMetricModel.timestamp, AgentMetricModel.agent_name)
        result = await self._session.execute(stmt)

        return tuple(
            TelemetryPersistenceSerializer.agent_metric_from_model(model)
            for model in result.scalars().all()
        )

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
        stmt = select(ProviderMetricModel)
        stmt = _where_if_not_none(
            stmt, ProviderMetricModel.provider_name, provider_name
        )
        stmt = _where_if_not_none(
            stmt, ProviderMetricModel.provider_type, provider_type
        )
        stmt = _where_if_not_none(stmt, ProviderMetricModel.metric_name, metric_name)
        stmt = _where_if_not_none(
            stmt, ProviderMetricModel.workflow_name, workflow_name
        )
        stmt = _where_if_not_none(stmt, ProviderMetricModel.execution_id, execution_id)
        stmt = _where_if_not_none(stmt, ProviderMetricModel.endpoint, endpoint)
        stmt = _where_if_not_none(stmt, ProviderMetricModel.success, success)
        stmt = _where_if_not_none(
            stmt, ProviderMetricModel.correlation_id, correlation_id
        )
        stmt = _where_timestamp_window(stmt, ProviderMetricModel.timestamp, start, end)
        stmt = stmt.order_by(
            ProviderMetricModel.timestamp, ProviderMetricModel.provider_name
        )
        result = await self._session.execute(stmt)

        return tuple(
            TelemetryPersistenceSerializer.provider_metric_from_model(model)
            for model in result.scalars().all()
        )


def _insert_event_statement(
    event: TelemetryEventRecord,
) -> Any:
    stmt = insert(TelemetryEventModel).values(
        **TelemetryPersistenceSerializer.event_values(event)
    )

    return stmt.on_conflict_do_nothing(
        index_elements=["telemetry_event_id"],
    )


def _upsert_metric_statement(
    metric: TelemetryMetricRecord,
) -> Any:
    stmt = insert(TelemetryMetricModel).values(
        **TelemetryPersistenceSerializer.metric_values(metric)
    )
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["metric_id"],
        set_={
            "metric_name": excluded.metric_name,
            "source": excluded.source,
            "timestamp": excluded.timestamp,
            "metric_value": excluded.metric_value,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metric_unit": excluded.metric_unit,
            "metric_kind": excluded.metric_kind,
            "correlation_id": excluded.correlation_id,
            "dimensions": excluded.dimensions,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _insert_trace_statement(
    trace: TelemetryTraceRecord,
) -> Any:
    stmt = insert(TelemetryTraceModel).values(
        **TelemetryPersistenceSerializer.trace_values(trace)
    )

    excluded = stmt.excluded
    terminal_update_wins = _terminal_trace_update_wins(excluded)

    return stmt.on_conflict_do_update(
        index_elements=["trace_id", "span_id"],
        set_={
            "operation_name": excluded.operation_name,
            "source": excluded.source,
            "started_at": func.least(
                TelemetryTraceModel.started_at,
                excluded.started_at,
            ),
            "workflow_name": func.coalesce(
                TelemetryTraceModel.workflow_name,
                excluded.workflow_name,
            ),
            "execution_id": func.coalesce(
                TelemetryTraceModel.execution_id,
                excluded.execution_id,
            ),
            "runtime_id": func.coalesce(
                TelemetryTraceModel.runtime_id,
                excluded.runtime_id,
            ),
            "node_name": func.coalesce(
                TelemetryTraceModel.node_name,
                excluded.node_name,
            ),
            "parent_span_id": func.coalesce(
                TelemetryTraceModel.parent_span_id,
                excluded.parent_span_id,
            ),
            "ended_at": case(
                (terminal_update_wins, excluded.ended_at),
                else_=TelemetryTraceModel.ended_at,
            ),
            "duration_seconds": case(
                (terminal_update_wins, excluded.duration_seconds),
                else_=TelemetryTraceModel.duration_seconds,
            ),
            "status": case(
                (terminal_update_wins, excluded.status),
                else_=TelemetryTraceModel.status,
            ),
            "correlation_id": func.coalesce(
                TelemetryTraceModel.correlation_id,
                excluded.correlation_id,
            ),
            "terminal_event_id": case(
                (terminal_update_wins, excluded.terminal_event_id),
                else_=TelemetryTraceModel.terminal_event_id,
            ),
            "exception_type": case(
                (terminal_update_wins, excluded.exception_type),
                else_=TelemetryTraceModel.exception_type,
            ),
            "exception_message": case(
                (terminal_update_wins, excluded.exception_message),
                else_=TelemetryTraceModel.exception_message,
            ),
            "exception_stack_trace": case(
                (terminal_update_wins, excluded.exception_stack_trace),
                else_=TelemetryTraceModel.exception_stack_trace,
            ),
            "exception_stack_trace_truncated": case(
                (
                    terminal_update_wins,
                    excluded.exception_stack_trace_truncated,
                ),
                else_=TelemetryTraceModel.exception_stack_trace_truncated,
            ),
            "attributes": TelemetryTraceModel.attributes.op("||")(excluded.attributes),
            "metadata": TelemetryTraceModel.metadata_payload.op("||")(
                excluded.metadata
            ),
            "row_updated_at": func.now(),
        },
    )


def _terminal_trace_update_wins(excluded: Any) -> Any:
    existing_rank = _trace_status_rank(TelemetryTraceModel.status)
    incoming_rank = _trace_status_rank(excluded.status)

    return (excluded.ended_at.is_not(None)) & (
        (TelemetryTraceModel.ended_at.is_(None))
        | (incoming_rank > existing_rank)
        | (
            (incoming_rank == existing_rank)
            & (excluded.ended_at >= TelemetryTraceModel.ended_at)
        )
    )


def _trace_status_rank(status: Any) -> Any:
    return case(
        (status == "failed", 4),
        (status == "cancelled", 3),
        (status == "succeeded", 2),
        (status == "running", 1),
        else_=0,
    )


def _upsert_workflow_metric_statement(
    metric: WorkflowMetricRecord,
) -> Any:
    stmt = insert(WorkflowMetricModel).values(
        **TelemetryPersistenceSerializer.workflow_metric_values(metric)
    )
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["workflow_metric_id"],
        set_={
            "workflow_name": excluded.workflow_name,
            "metric_name": excluded.metric_name,
            "timestamp": excluded.timestamp,
            "metric_value": excluded.metric_value,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metric_unit": excluded.metric_unit,
            "status": excluded.status,
            "duration_seconds": excluded.duration_seconds,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_agent_metric_statement(
    metric: AgentMetricRecord,
) -> Any:
    stmt = insert(AgentMetricModel).values(
        **TelemetryPersistenceSerializer.agent_metric_values(metric)
    )
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["agent_metric_id"],
        set_={
            "agent_name": excluded.agent_name,
            "agent_type": excluded.agent_type,
            "metric_name": excluded.metric_name,
            "timestamp": excluded.timestamp,
            "metric_value": excluded.metric_value,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metric_unit": excluded.metric_unit,
            "model_name": excluded.model_name,
            "symbol": excluded.symbol,
            "universe": excluded.universe,
            "correlation_id": excluded.correlation_id,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _upsert_provider_metric_statement(
    metric: ProviderMetricRecord,
) -> Any:
    stmt = insert(ProviderMetricModel).values(
        **TelemetryPersistenceSerializer.provider_metric_values(metric)
    )
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["provider_metric_id"],
        set_={
            "provider_name": excluded.provider_name,
            "provider_type": excluded.provider_type,
            "metric_name": excluded.metric_name,
            "timestamp": excluded.timestamp,
            "metric_value": excluded.metric_value,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metric_unit": excluded.metric_unit,
            "endpoint": excluded.endpoint,
            "status_code": excluded.status_code,
            "success": excluded.success,
            "correlation_id": excluded.correlation_id,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _bundle_primary_record_id(
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

    return "telemetry_bundle:empty"


def _where_if_not_none(
    stmt: Any,
    column: Any,
    value: object | None,
) -> Any:
    if value is None:
        return stmt

    return stmt.where(column == value)


def _where_timestamp_window(
    stmt: Any,
    column: Any,
    start: datetime | None,
    end: datetime | None,
) -> Any:
    if start is not None:
        stmt = stmt.where(column >= start)
    if end is not None:
        stmt = stmt.where(column <= end)

    return stmt
