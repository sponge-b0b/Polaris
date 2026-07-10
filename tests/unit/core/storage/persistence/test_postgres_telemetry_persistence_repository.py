from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.telemetry import AgentMetricModel
from core.database.models.telemetry import ProviderMetricModel
from core.database.models.telemetry import TelemetryEventModel
from core.database.models.telemetry import TelemetryMetricModel
from core.database.models.telemetry import TelemetryTraceModel
from core.database.models.telemetry import WorkflowMetricModel
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.repositories.postgres_telemetry_persistence_repository import (
    PostgresTelemetryPersistenceRepository,
)
from core.storage.persistence.serializers.telemetry_persistence_serializer import (
    TelemetryPersistenceSerializer,
)
from core.storage.persistence.telemetry import AgentMetricRecord
from core.storage.persistence.telemetry import ProviderMetricRecord
from core.storage.persistence.telemetry import TelemetryEventRecord
from core.storage.persistence.telemetry import TelemetryMetricRecord
from core.storage.persistence.telemetry import TelemetryPersistenceBundle
from core.storage.persistence.telemetry import TelemetryTraceRecord
from core.storage.persistence.telemetry import WorkflowMetricRecord


class FakeScalarResult:
    def __init__(
        self,
        rows: Sequence[object],
    ) -> None:
        self._rows = list(rows)

    def all(
        self,
    ) -> list[object]:
        return self._rows


class FakeExecuteResult:
    def __init__(
        self,
        rows: Sequence[object] | None = None,
    ) -> None:
        self._rows = list(rows or [])

    def scalar_one_or_none(
        self,
    ) -> object | None:
        if not self._rows:
            return None

        return self._rows[0]

    def scalars(
        self,
    ) -> FakeScalarResult:
        return FakeScalarResult(self._rows)


class FakeAsyncSession:
    def __init__(
        self,
        result: FakeExecuteResult | None = None,
        error: SQLAlchemyError | None = None,
    ) -> None:
        self.result = result or FakeExecuteResult()
        self.error = error
        self.executed: list[Any] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(
        self,
        statement: Any,
    ) -> FakeExecuteResult:
        self.executed.append(statement)

        if self.error is not None:
            raise self.error

        return self.result

    async def commit(
        self,
    ) -> None:
        self.commits += 1

    async def rollback(
        self,
    ) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_persist_telemetry_bundle_appends_events_and_assembles_trace_state() -> (
    None
):
    session = FakeAsyncSession()
    repository = PostgresTelemetryPersistenceRepository(cast(AsyncSession, session))

    result = await repository.persist_telemetry_bundle(_bundle())

    compiled = [
        str(statement.compile(dialect=postgresql.dialect()))
        for statement in session.executed
    ]

    assert result.success is True
    assert result.primary_record_id == "event-1"
    assert result.records_persisted == 6
    assert session.commits == 1
    assert len(session.executed) == 6
    assert "telemetry_events" in compiled[0]
    assert "ON CONFLICT (telemetry_event_id) DO NOTHING" in compiled[0]
    assert "telemetry_metrics" in compiled[1]
    assert "ON CONFLICT (metric_id) DO UPDATE" in compiled[1]
    assert "telemetry_traces" in compiled[2]
    assert "ON CONFLICT (trace_id, span_id) DO UPDATE" in compiled[2]
    assert "started_at = least" in compiled[2]
    assert "ended_at = CASE WHEN" in compiled[2]
    assert "status = CASE WHEN" in compiled[2]
    assert "terminal_event_id = CASE WHEN" in compiled[2]
    assert "workflow_metrics" in compiled[3]
    assert "ON CONFLICT (workflow_metric_id) DO UPDATE" in compiled[3]
    assert "agent_metrics" in compiled[4]
    assert "ON CONFLICT (agent_metric_id) DO UPDATE" in compiled[4]
    assert "provider_metrics" in compiled[5]
    assert "ON CONFLICT (provider_metric_id) DO UPDATE" in compiled[5]


@pytest.mark.asyncio
async def test_persist_telemetry_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresTelemetryPersistenceRepository(cast(AsyncSession, session))

    result = await repository.persist_event(_event())

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_get_methods_return_typed_records() -> None:
    event_model = TelemetryEventModel(
        **TelemetryPersistenceSerializer.event_values(_event())
    )
    metric_model = TelemetryMetricModel(
        **TelemetryPersistenceSerializer.metric_values(_metric())
    )
    trace_model = TelemetryTraceModel(
        **TelemetryPersistenceSerializer.trace_values(_trace())
    )
    workflow_model = WorkflowMetricModel(
        **TelemetryPersistenceSerializer.workflow_metric_values(_workflow_metric())
    )
    agent_model = AgentMetricModel(
        **TelemetryPersistenceSerializer.agent_metric_values(_agent_metric())
    )
    provider_model = ProviderMetricModel(
        **TelemetryPersistenceSerializer.provider_metric_values(_provider_metric())
    )

    assert (
        await PostgresTelemetryPersistenceRepository(
            cast(AsyncSession, FakeAsyncSession(FakeExecuteResult([event_model])))
        ).get_event("event-1")
    ) == _event()
    assert (
        await PostgresTelemetryPersistenceRepository(
            cast(AsyncSession, FakeAsyncSession(FakeExecuteResult([metric_model])))
        ).get_metric("metric-1")
    ) == _metric()
    assert (
        await PostgresTelemetryPersistenceRepository(
            cast(AsyncSession, FakeAsyncSession(FakeExecuteResult([trace_model])))
        ).get_trace("trace-record-1")
    ) == _trace()
    assert (
        await PostgresTelemetryPersistenceRepository(
            cast(AsyncSession, FakeAsyncSession(FakeExecuteResult([workflow_model])))
        ).get_workflow_metric("workflow-metric-1")
    ) == _workflow_metric()
    assert (
        await PostgresTelemetryPersistenceRepository(
            cast(AsyncSession, FakeAsyncSession(FakeExecuteResult([agent_model])))
        ).get_agent_metric("agent-metric-1")
    ) == _agent_metric()
    assert (
        await PostgresTelemetryPersistenceRepository(
            cast(AsyncSession, FakeAsyncSession(FakeExecuteResult([provider_model])))
        ).get_provider_metric("provider-metric-1")
    ) == _provider_metric()


@pytest.mark.asyncio
async def test_list_methods_return_filtered_typed_records() -> None:
    event_model = TelemetryEventModel(
        **TelemetryPersistenceSerializer.event_values(_event())
    )
    metric_model = TelemetryMetricModel(
        **TelemetryPersistenceSerializer.metric_values(_metric())
    )
    trace_model = TelemetryTraceModel(
        **TelemetryPersistenceSerializer.trace_values(_trace())
    )
    workflow_model = WorkflowMetricModel(
        **TelemetryPersistenceSerializer.workflow_metric_values(_workflow_metric())
    )
    agent_model = AgentMetricModel(
        **TelemetryPersistenceSerializer.agent_metric_values(_agent_metric())
    )
    provider_model = ProviderMetricModel(
        **TelemetryPersistenceSerializer.provider_metric_values(_provider_metric())
    )

    events = await PostgresTelemetryPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(FakeExecuteResult([event_model])))
    ).list_events(
        event_type="workflow_control.pause_requested",
        source="runtime",
        workflow_name="morning_report",
        execution_id="exec-1",
        correlation_id="corr-1",
        start=_timestamp(),
        end=_timestamp(),
    )
    metrics = await PostgresTelemetryPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(FakeExecuteResult([metric_model])))
    ).list_metrics(
        metric_name="runtime.node.duration",
        source="runtime",
        workflow_name="morning_report",
        execution_id="exec-1",
        correlation_id="corr-1",
        start=_timestamp(),
        end=_timestamp(),
    )
    traces = await PostgresTelemetryPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(FakeExecuteResult([trace_model])))
    ).list_traces(
        trace_id="trace-1",
        operation_name="execute_node",
        source="runtime",
        workflow_name="morning_report",
        execution_id="exec-1",
        correlation_id="corr-1",
        start=_timestamp(),
        end=_timestamp(),
    )
    workflow_metrics = await PostgresTelemetryPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(FakeExecuteResult([workflow_model])))
    ).list_workflow_metrics(
        workflow_name="morning_report",
        execution_id="exec-1",
        metric_name="workflow.duration",
        status="succeeded",
        start=_timestamp(),
        end=_timestamp(),
    )
    agent_metrics = await PostgresTelemetryPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(FakeExecuteResult([agent_model])))
    ).list_agent_metrics(
        agent_name="MacroAgent",
        agent_type="macro",
        metric_name="agent.tokens",
        workflow_name="morning_report",
        execution_id="exec-1",
        symbol="SPY",
        universe="us_equities",
        correlation_id="corr-1",
        start=_timestamp(),
        end=_timestamp(),
    )
    provider_metrics = await PostgresTelemetryPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(FakeExecuteResult([provider_model])))
    ).list_provider_metrics(
        provider_name="fred",
        provider_type="macro",
        metric_name="provider.latency",
        workflow_name="morning_report",
        execution_id="exec-1",
        endpoint="series/observations",
        success=True,
        correlation_id="corr-1",
        start=_timestamp(),
        end=_timestamp(),
    )

    assert events == (_event(),)
    assert metrics == (_metric(),)
    assert traces == (_trace(),)
    assert workflow_metrics == (_workflow_metric(),)
    assert agent_metrics == (_agent_metric(),)
    assert provider_metrics == (_provider_metric(),)


def _timestamp() -> datetime:
    return datetime(2026, 6, 1, 12, tzinfo=timezone.utc)


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="macro",
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
        telemetry_event_id="event-1",
        event_type="workflow_control.pause_requested",
        source="runtime",
        timestamp=_timestamp(),
        lineage=_lineage(),
        severity="info",
        message="Pause requested.",
        correlation_id="corr-1",
        trace_id="trace-1",
        span_id="span-1",
        payload={"status": "paused"},
        metadata={"source": "unit-test"},
    )


def _metric() -> TelemetryMetricRecord:
    return TelemetryMetricRecord(
        metric_id="metric-1",
        metric_name="runtime.node.duration",
        source="runtime",
        timestamp=_timestamp(),
        metric_value=1.25,
        lineage=_lineage(),
        metric_unit="seconds",
        metric_kind="duration",
        correlation_id="corr-1",
        dimensions={"phase": "node"},
        metadata={"source": "unit-test"},
    )


def _trace() -> TelemetryTraceRecord:
    return TelemetryTraceRecord(
        trace_record_id="trace-record-1",
        trace_id="trace-1",
        span_id="span-1",
        operation_name="execute_node",
        source="runtime",
        started_at=_timestamp(),
        lineage=_lineage(),
        parent_span_id="parent-span",
        ended_at=datetime(2026, 6, 1, 12, 0, 1, tzinfo=timezone.utc),
        duration_seconds=1.0,
        status="failed",
        correlation_id="corr-1",
        terminal_event_id="event-terminal-1",
        exception_type="RuntimeError",
        exception_message="provider failed",
        exception_stack_trace="traceback",
        exception_stack_trace_truncated=False,
        attributes={"node": "macro"},
        metadata={"source": "unit-test"},
    )


def _workflow_metric() -> WorkflowMetricRecord:
    return WorkflowMetricRecord(
        workflow_metric_id="workflow-metric-1",
        workflow_name="morning_report",
        metric_name="workflow.duration",
        timestamp=_timestamp(),
        metric_value=3.5,
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="macro",
        metric_unit="seconds",
        status="succeeded",
        duration_seconds=3.5,
        metadata={"source": "unit-test"},
    )


def _agent_metric() -> AgentMetricRecord:
    return AgentMetricRecord(
        agent_metric_id="agent-metric-1",
        agent_name="MacroAgent",
        agent_type="macro",
        metric_name="agent.tokens",
        timestamp=_timestamp(),
        metric_value=100.0,
        lineage=_lineage(),
        metric_unit="tokens",
        model_name="gpt-test",
        symbol="spy",
        universe="us_equities",
        correlation_id="corr-1",
        metadata={"source": "unit-test"},
    )


def _provider_metric() -> ProviderMetricRecord:
    return ProviderMetricRecord(
        provider_metric_id="provider-metric-1",
        provider_name="fred",
        provider_type="macro",
        metric_name="provider.latency",
        timestamp=_timestamp(),
        metric_value=0.25,
        lineage=_lineage(),
        metric_unit="seconds",
        endpoint="series/observations",
        status_code=200,
        success=True,
        correlation_id="corr-1",
        metadata={"source": "unit-test"},
    )
