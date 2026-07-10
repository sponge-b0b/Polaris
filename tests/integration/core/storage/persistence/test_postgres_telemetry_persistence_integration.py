from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import datetime
from datetime import timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from application.persistence.telemetry import TelemetryEventPersistenceFilters
from application.persistence.telemetry import TelemetryPersistenceService
from application.persistence.telemetry.telemetry_persistence_sink import (
    TelemetryPersistenceSink,
)
from application.persistence.telemetry.telemetry_persistence_sink import (
    TelemetryPersistenceSinkConfig,
)
from application.persistence.telemetry import TelemetryTracePersistenceFilters
from core.database.models.telemetry import TelemetryEventModel
from core.database.models.telemetry import TelemetryTraceModel
from core.storage.persistence.repositories import (
    PostgresTelemetryPersistenceRepository,
)
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.events.telemetry_exception_details import (
    TelemetryExceptionDetails,
)

TEST_DATABASE_URL = os.environ.get("POLARIS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="POLARIS_TEST_DATABASE_URL is required for PostgreSQL telemetry integration tests.",
)


@pytest_asyncio.fixture
async def postgres_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    yield session_factory

    await engine.dispose()


async def _delete_test_records(
    session_factory: async_sessionmaker[AsyncSession],
    correlation_id: str,
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(TelemetryTraceModel).where(
                TelemetryTraceModel.correlation_id == correlation_id,
            )
        )
        await session.execute(
            delete(TelemetryEventModel).where(
                TelemetryEventModel.correlation_id == correlation_id,
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_telemetry_sink_persists_events_and_assembles_terminal_trace_state(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    correlation_id = f"telemetry-persistence-{uuid4().hex}"
    trace_id = uuid4().hex
    span_id = uuid4().hex[:16]
    parent_span_id = uuid4().hex[:16]
    execution_id = f"execution-{uuid4().hex}"
    started_at = datetime(2026, 6, 29, 12, tzinfo=timezone.utc)
    await _delete_test_records(postgres_session_factory, correlation_id)

    started_event = TelemetryEvent(
        event_id=f"started-{uuid4().hex}",
        event_type="application.service.started",
        source="application.service",
        timestamp=started_at,
        workflow_id="telemetry_validation",
        execution_id=execution_id,
        runtime_id="runtime-telemetry-validation",
        node_name="telemetry_validation_node",
        correlation_id=correlation_id,
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        payload={"request_name": "TelemetryValidationRequest"},
    )
    failed_event = TelemetryEvent(
        event_id=f"failed-{uuid4().hex}",
        event_type="application.service.failed",
        source="application.service",
        timestamp=started_at.replace(microsecond=125000),
        workflow_id="telemetry_validation",
        execution_id=execution_id,
        runtime_id="runtime-telemetry-validation",
        node_name="telemetry_validation_node",
        correlation_id=correlation_id,
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        duration_seconds=0.125,
        success=False,
        exception_details=TelemetryExceptionDetails(
            exception_type="RuntimeError",
            message="integration failure",
            stack_trace="traceback",
        ),
        payload={"request_name": "TelemetryValidationRequest"},
    )

    try:
        async with postgres_session_factory() as session:
            sink = TelemetryPersistenceSink(
                TelemetryPersistenceService(
                    PostgresTelemetryPersistenceRepository(session)
                ),
                config=TelemetryPersistenceSinkConfig(
                    enabled=True,
                    fail_fast=True,
                ),
            )
            await sink.emit(started_event)
            await sink.emit(failed_event)

        async with postgres_session_factory() as session:
            service = TelemetryPersistenceService(
                PostgresTelemetryPersistenceRepository(session)
            )
            events = await service.list_events(
                TelemetryEventPersistenceFilters(correlation_id=correlation_id)
            )
            traces = await service.list_traces(
                TelemetryTracePersistenceFilters(correlation_id=correlation_id)
            )

        assert {event.telemetry_event_id for event in events} == {
            started_event.event_id,
            failed_event.event_id,
        }
        assert all(event.trace_id == trace_id for event in events)
        assert all(event.span_id == span_id for event in events)
        assert len(traces) == 1
        trace = traces[0]
        assert trace.trace_id == trace_id
        assert trace.span_id == span_id
        assert trace.parent_span_id == parent_span_id
        assert trace.lineage.execution_id == execution_id
        assert trace.operation_name == "application.service"
        assert trace.started_at == started_at
        assert trace.ended_at == failed_event.timestamp
        assert trace.status == "failed"
        assert trace.duration_seconds == 0.125
        assert trace.terminal_event_id == failed_event.event_id
        assert trace.exception_type == "RuntimeError"
        assert trace.exception_message == "integration failure"
        assert trace.exception_stack_trace == "traceback"
    finally:
        await _delete_test_records(postgres_session_factory, correlation_id)
