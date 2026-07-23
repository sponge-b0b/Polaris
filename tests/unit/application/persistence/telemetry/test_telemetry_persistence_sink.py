from __future__ import annotations

from datetime import UTC, datetime

import pytest

from application.persistence.telemetry import TelemetryPersistenceService
from application.persistence.telemetry.telemetry_persistence_sink import (
    TelemetryPersistenceSink,
    TelemetryPersistenceSinkConfig,
)
from core.storage.persistence.telemetry import (
    TelemetryPersistenceBundle,
    TelemetryPersistenceResult,
)
from core.telemetry.events.telemetry_event import TelemetryEvent


class RecordingTelemetryPersistenceService(TelemetryPersistenceService):
    def __init__(
        self,
        *,
        result: TelemetryPersistenceResult | None = None,
        should_raise: bool = False,
    ) -> None:
        self.bundle: TelemetryPersistenceBundle | None = None
        self.persist_count = 0
        self.result = result
        self.should_raise = should_raise

    async def persist_telemetry_bundle(
        self,
        bundle: TelemetryPersistenceBundle,
    ) -> TelemetryPersistenceResult:
        self.persist_count += 1
        self.bundle = bundle
        if self.should_raise:
            raise RuntimeError("repository unavailable")
        if self.result is not None:
            return self.result
        return TelemetryPersistenceResult.succeeded(
            primary_record_id=bundle.events[0].telemetry_event_id,
            records_persisted=len(bundle.events),
        )


@pytest.mark.asyncio
async def test_sink_does_not_persist_when_disabled() -> None:
    service = RecordingTelemetryPersistenceService()
    sink = TelemetryPersistenceSink(
        service,
    )

    await sink.emit(
        _event(),
    )

    assert service.persist_count == 0
    assert service.bundle is None


@pytest.mark.asyncio
async def test_sink_persists_mapped_bundle_when_enabled() -> None:
    service = RecordingTelemetryPersistenceService()
    sink = TelemetryPersistenceSink(
        service,
        config=TelemetryPersistenceSinkConfig(
            enabled=True,
        ),
    )

    await sink.emit(
        _event(),
    )

    assert service.persist_count == 1
    assert service.bundle is not None
    assert len(service.bundle.events) == 1
    assert service.bundle.events[0].event_type == "runtime.workflow.started"


@pytest.mark.asyncio
async def test_sink_swallows_persistence_failure_when_not_fail_fast() -> None:
    service = RecordingTelemetryPersistenceService(
        result=TelemetryPersistenceResult.failed(
            "repository unavailable",
        ),
    )
    sink = TelemetryPersistenceSink(
        service,
        config=TelemetryPersistenceSinkConfig(
            enabled=True,
        ),
    )

    await sink.emit(
        _event(),
    )

    assert service.persist_count == 1


@pytest.mark.asyncio
async def test_sink_raises_persistence_failure_when_fail_fast() -> None:
    service = RecordingTelemetryPersistenceService(
        result=TelemetryPersistenceResult.failed(
            "repository unavailable",
        ),
    )
    sink = TelemetryPersistenceSink(
        service,
        config=TelemetryPersistenceSinkConfig(
            enabled=True,
            fail_fast=True,
        ),
    )

    with pytest.raises(RuntimeError, match="repository unavailable"):
        await sink.emit(
            _event(),
        )


@pytest.mark.asyncio
async def test_sink_swallows_exception_when_not_fail_fast() -> None:
    service = RecordingTelemetryPersistenceService(
        should_raise=True,
    )
    sink = TelemetryPersistenceSink(
        service,
        config=TelemetryPersistenceSinkConfig(
            enabled=True,
        ),
    )

    await sink.emit(
        _event(),
    )

    assert service.persist_count == 1


def _event() -> TelemetryEvent:
    return TelemetryEvent(
        event_type="runtime.workflow.started",
        source="runtime.engine",
        timestamp=datetime(2026, 1, 2, 14, 30, tzinfo=UTC),
        workflow_id="morning_report",
        execution_id="exec-123",
        runtime_id="runtime-456",
        node_name="start",
        correlation_id="corr-789",
        success=True,
    )
