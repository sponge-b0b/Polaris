from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from application.persistence.telemetry import TelemetryPersistenceService
from application.persistence.telemetry import TelemetryTracePersistenceFilters
from application.persistence.telemetry.telemetry_persistence_sink import (
    TelemetryPersistenceSink,
)
from application.persistence.telemetry.telemetry_persistence_sink import (
    TelemetryPersistenceSinkConfig,
)
from core.database.models.telemetry import TelemetryEventModel
from core.database.models.telemetry import TelemetryTraceModel
from core.storage.persistence.repositories import (
    PostgresTelemetryPersistenceRepository,
)
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.integrations.opentelemetry.opentelemetry_config import (
    OpenTelemetryConfig,
)
from core.telemetry.integrations.opentelemetry.opentelemetry_sink import (
    OpenTelemetrySink,
)

TEST_DATABASE_URL = os.environ.get("POLARIS_TEST_DATABASE_URL")
TEST_JAEGER_URL = os.environ.get("POLARIS_TEST_JAEGER_URL")
TEST_OTEL_ENDPOINT = os.environ.get("POLARIS_TEST_OTEL_ENDPOINT")

pytestmark = pytest.mark.skipif(
    not all((TEST_DATABASE_URL, TEST_JAEGER_URL, TEST_OTEL_ENDPOINT)),
    reason=(
        "POLARIS_TEST_DATABASE_URL, POLARIS_TEST_JAEGER_URL, and "
        "POLARIS_TEST_OTEL_ENDPOINT are required for live trace-topology tests."
    ),
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


@pytest.mark.asyncio
async def test_postgres_and_jaeger_expose_the_same_canonical_trace_hierarchy(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    assert TEST_JAEGER_URL is not None
    assert TEST_OTEL_ENDPOINT is not None
    correlation_id = f"live-trace-topology-{uuid4().hex}"
    trace_id = uuid4().hex
    span_ids = {
        "runtime.workflow": uuid4().hex[:16],
        "runtime.node": uuid4().hex[:16],
        "application.service": uuid4().hex[:16],
        "integration.provider.call": uuid4().hex[:16],
    }
    expected_parent_by_span = {
        span_ids["runtime.workflow"]: None,
        span_ids["runtime.node"]: span_ids["runtime.workflow"],
        span_ids["application.service"]: span_ids["runtime.node"],
        span_ids["integration.provider.call"]: span_ids["application.service"],
    }
    events = _trace_events(
        correlation_id=correlation_id,
        trace_id=trace_id,
        span_ids=span_ids,
    )
    await _delete_test_records(postgres_session_factory, correlation_id)

    otel_sink = OpenTelemetrySink(
        config=OpenTelemetryConfig(
            service_name="polaris-live-trace-topology-test",
            service_version="test",
            environment="test",
            otlp_endpoint=TEST_OTEL_ENDPOINT,
            enable_tracing=True,
            enable_metrics=False,
            enable_console_export=False,
            insecure=True,
        )
    )

    try:
        async with postgres_session_factory() as session:
            persistence_sink = TelemetryPersistenceSink(
                TelemetryPersistenceService(
                    PostgresTelemetryPersistenceRepository(session)
                ),
                config=TelemetryPersistenceSinkConfig(
                    enabled=True,
                    fail_fast=True,
                ),
            )
            for event in events:
                await persistence_sink.emit(event)
                await otel_sink.emit(event)

        otel_sink.force_flush()

        async with postgres_session_factory() as session:
            traces = await TelemetryPersistenceService(
                PostgresTelemetryPersistenceRepository(session)
            ).list_traces(
                TelemetryTracePersistenceFilters(correlation_id=correlation_id)
            )

        postgres_parent_by_span = {
            trace.span_id: trace.parent_span_id
            for trace in traces
            if trace.trace_id == trace_id and trace.span_id is not None
        }
        assert postgres_parent_by_span == expected_parent_by_span
        assert all(trace.status == "succeeded" for trace in traces)

        jaeger_parent_by_span = await _wait_for_jaeger_trace(
            jaeger_url=TEST_JAEGER_URL,
            trace_id=trace_id,
            expected_span_ids=set(expected_parent_by_span),
        )
        assert jaeger_parent_by_span == expected_parent_by_span
    finally:
        otel_sink.shutdown()
        await _delete_test_records(postgres_session_factory, correlation_id)


def _trace_events(
    *,
    correlation_id: str,
    trace_id: str,
    span_ids: dict[str, str],
) -> tuple[TelemetryEvent, ...]:
    started_at = datetime.now(timezone.utc)
    workflow_span_id = span_ids["runtime.workflow"]
    node_span_id = span_ids["runtime.node"]
    service_span_id = span_ids["application.service"]
    provider_span_id = span_ids["integration.provider.call"]

    def event(
        *,
        event_type: str,
        source: str,
        timestamp: datetime,
        span_id: str,
        operation_kind: str,
        parent_span_id: str | None = None,
        duration_seconds: float | None = None,
        success: bool | None = None,
    ) -> TelemetryEvent:
        return TelemetryEvent(
            event_type=event_type,
            source=source,
            timestamp=timestamp,
            workflow_id="live_trace_topology",
            execution_id=f"execution-{correlation_id}",
            runtime_id=f"runtime-{correlation_id}",
            node_name="live_trace_topology_node",
            correlation_id=correlation_id,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            duration_seconds=duration_seconds,
            success=success,
            attributes={"operation_kind": operation_kind},
        )

    return (
        event(
            event_type="runtime.workflow.started",
            source="runtime",
            timestamp=started_at,
            span_id=workflow_span_id,
            operation_kind="workflow_execution",
        ),
        event(
            event_type="runtime.node.started",
            source="runtime",
            timestamp=started_at + timedelta(milliseconds=10),
            span_id=node_span_id,
            parent_span_id=workflow_span_id,
            operation_kind="runtime_node_attempt",
        ),
        event(
            event_type="application.service.started",
            source="application.service",
            timestamp=started_at + timedelta(milliseconds=20),
            span_id=service_span_id,
            parent_span_id=node_span_id,
            operation_kind="application_service_attempt",
        ),
        event(
            event_type="integration.client.retry_scheduled",
            source="integration",
            timestamp=started_at + timedelta(milliseconds=30),
            span_id=provider_span_id,
            parent_span_id=service_span_id,
            operation_kind="provider_call",
        ),
        event(
            event_type="integration.provider.call",
            source="integration",
            timestamp=started_at + timedelta(milliseconds=40),
            span_id=provider_span_id,
            parent_span_id=service_span_id,
            duration_seconds=0.01,
            success=True,
            operation_kind="provider_call",
        ),
        event(
            event_type="application.service.completed",
            source="application.service",
            timestamp=started_at + timedelta(milliseconds=50),
            span_id=service_span_id,
            parent_span_id=node_span_id,
            duration_seconds=0.03,
            success=True,
            operation_kind="application_service_attempt",
        ),
        event(
            event_type="runtime.node.completed",
            source="runtime",
            timestamp=started_at + timedelta(milliseconds=60),
            span_id=node_span_id,
            parent_span_id=workflow_span_id,
            duration_seconds=0.05,
            success=True,
            operation_kind="runtime_node_attempt",
        ),
        event(
            event_type="runtime.workflow.completed",
            source="runtime",
            timestamp=started_at + timedelta(milliseconds=70),
            span_id=workflow_span_id,
            duration_seconds=0.07,
            success=True,
            operation_kind="workflow_execution",
        ),
    )


async def _wait_for_jaeger_trace(
    *,
    jaeger_url: str,
    trace_id: str,
    expected_span_ids: set[str],
) -> dict[str, str | None]:
    deadline = asyncio.get_running_loop().time() + 10.0
    async with httpx.AsyncClient(
        base_url=jaeger_url.rstrip("/"),
        timeout=2.0,
    ) as client:
        while asyncio.get_running_loop().time() < deadline:
            response = await client.get(f"/api/traces/{trace_id}")
            if response.status_code == httpx.codes.OK:
                trace_data = response.json().get("data", [])
                if trace_data:
                    parent_by_span = _jaeger_parent_map(trace_data[0]["spans"])
                    if expected_span_ids.issubset(parent_by_span):
                        return parent_by_span
            await asyncio.sleep(0.25)

    raise AssertionError(f"Jaeger did not expose trace {trace_id} within 10 seconds.")


def _jaeger_parent_map(spans: list[dict[str, object]]) -> dict[str, str | None]:
    parent_by_span: dict[str, str | None] = {}
    for span in spans:
        span_id = str(span["spanID"])
        parent_span_id = None
        references = span.get("references", [])
        if isinstance(references, list):
            child_of = next(
                (
                    reference
                    for reference in references
                    if isinstance(reference, dict)
                    and reference.get("refType") == "CHILD_OF"
                ),
                None,
            )
            if child_of is not None:
                parent_span_id = str(child_of["spanID"])
        parent_by_span[span_id] = parent_span_id
    return parent_by_span


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
