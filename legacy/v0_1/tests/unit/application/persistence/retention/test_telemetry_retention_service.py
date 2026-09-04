from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from application.persistence.retention import (
    TelemetryRetentionConfig,
    TelemetryRetentionService,
)
from core.telemetry.observability.observability_manager import ObservabilityManager


class FakeExecuteResult:
    def __init__(
        self,
        *,
        count: int | None = None,
        rowcount: int | None = None,
    ) -> None:
        self._count = count
        self.rowcount = rowcount

    def scalar_one(
        self,
    ) -> int:
        if self._count is None:
            raise AssertionError("scalar_one called on non-count result")

        return self._count


class FakeAsyncSession:
    def __init__(
        self,
        results: Sequence[FakeExecuteResult] = (),
        error: SQLAlchemyError | None = None,
    ) -> None:
        self._results = list(results)
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
        if not self._results:
            raise AssertionError("No fake execute result available")

        return self._results.pop(0)

    async def commit(
        self,
    ) -> None:
        self.commits += 1

    async def rollback(
        self,
    ) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_plan_expired_counts_telemetry_tables_without_deleting() -> None:
    session = FakeAsyncSession(
        results=tuple(FakeExecuteResult(count=count) for count in (2, 0, 1, 3, 4, 5))
    )
    service = TelemetryRetentionService(cast(AsyncSession, session))

    result = await service.plan_expired(as_of=_as_of())

    assert result.success is True
    assert result.dry_run is True
    assert result.cutoff == datetime(2026, 5, 2, 12, tzinfo=UTC)
    assert result.total_expired_records == 15
    assert result.total_deleted_records == 0
    assert [summary.table_name for summary in result.summaries] == [
        "telemetry_events",
        "telemetry_metrics",
        "telemetry_traces",
        "workflow_metrics",
        "agent_metrics",
        "provider_metrics",
    ]
    assert all(summary.dry_run is True for summary in result.summaries)
    assert session.commits == 0
    assert session.rollbacks == 0
    assert len(session.executed) == 6


@pytest.mark.asyncio
async def test_purge_expired_deletes_only_when_explicitly_invoked() -> None:
    session = FakeAsyncSession(
        results=tuple(
            result
            for _ in range(6)
            for result in (
                FakeExecuteResult(count=2),
                FakeExecuteResult(rowcount=2),
            )
        )
    )
    service = TelemetryRetentionService(
        cast(AsyncSession, session),
        config=TelemetryRetentionConfig(
            retention_days=7,
            batch_size=10,
            max_batches=1,
        ),
    )

    result = await service.purge_expired(as_of=_as_of(), dry_run=False)

    assert result.success is True
    assert result.dry_run is False
    assert result.cutoff == datetime(2026, 5, 25, 12, tzinfo=UTC)
    assert result.total_expired_records == 12
    assert result.total_deleted_records == 12
    assert all(summary.deleted_records == 2 for summary in result.summaries)
    assert session.commits == 1
    assert session.rollbacks == 0
    assert len(session.executed) == 12


@pytest.mark.asyncio
async def test_purge_expired_rolls_back_and_reports_sqlalchemy_errors() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    service = TelemetryRetentionService(cast(AsyncSession, session))

    result = await service.purge_expired(as_of=_as_of(), dry_run=False)

    assert result.success is False
    assert result.errors
    assert "database unavailable" in result.errors[0]
    assert result.total_deleted_records == 0
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_retention_service_records_observability_metrics() -> None:
    session = FakeAsyncSession(
        results=tuple(FakeExecuteResult(count=count) for count in (1, 2, 3, 4, 5, 6))
    )
    observability_manager = ObservabilityManager()
    service = TelemetryRetentionService(
        cast(AsyncSession, session),
        observability_manager=observability_manager,
    )

    result = await service.plan_expired(as_of=_as_of())

    assert result.success is True
    metric_names = [
        point.name for point in observability_manager.metrics_store.points()
    ]
    assert "telemetry.retention.records_scanned" in metric_names
    assert "telemetry.retention.records_deleted" in metric_names
    assert "telemetry.retention.duration_seconds" in metric_names
    assert "telemetry.events.total" in metric_names


def test_telemetry_retention_config_validates_bounds() -> None:
    with pytest.raises(ValueError, match="retention_days must be positive"):
        TelemetryRetentionConfig(retention_days=0)
    with pytest.raises(ValueError, match="batch_size must be positive"):
        TelemetryRetentionConfig(batch_size=0)
    with pytest.raises(ValueError, match="max_batches must be positive"):
        TelemetryRetentionConfig(max_batches=0)


def _as_of() -> datetime:
    return datetime(2026, 6, 1, 12, tzinfo=UTC)
