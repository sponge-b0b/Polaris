from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import perf_counter
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.telemetry import (
    AgentMetricModel,
    ProviderMetricModel,
    TelemetryEventModel,
    TelemetryMetricModel,
    TelemetryTraceModel,
    WorkflowMetricModel,
)
from core.telemetry.observability.observability_manager import ObservabilityManager

DEFAULT_TELEMETRY_RETENTION_DAYS = 30
DEFAULT_TELEMETRY_RETENTION_BATCH_SIZE = 5_000
DEFAULT_TELEMETRY_RETENTION_MAX_BATCHES = 1


@dataclass(frozen=True, slots=True)
class TelemetryRetentionConfig:
    """
    Typed PostgreSQL telemetry retention policy.

    Deletion is intentionally bounded. A single purge invocation can delete at
    most ``batch_size * max_batches`` rows per telemetry table and dry-run is the
    default behavior.
    """

    retention_days: int = DEFAULT_TELEMETRY_RETENTION_DAYS
    batch_size: int = DEFAULT_TELEMETRY_RETENTION_BATCH_SIZE
    max_batches: int = DEFAULT_TELEMETRY_RETENTION_MAX_BATCHES

    def __post_init__(
        self,
    ) -> None:
        if isinstance(self.retention_days, bool) or self.retention_days <= 0:
            raise ValueError("telemetry retention_days must be positive.")
        if isinstance(self.batch_size, bool) or self.batch_size <= 0:
            raise ValueError("telemetry retention batch_size must be positive.")
        if isinstance(self.max_batches, bool) or self.max_batches <= 0:
            raise ValueError("telemetry retention max_batches must be positive.")

    @property
    def retention_period(
        self,
    ) -> timedelta:
        return timedelta(days=self.retention_days)


@dataclass(frozen=True, slots=True)
class TelemetryRetentionTableSummary:
    """
    Per-table telemetry retention outcome.
    """

    table_name: str
    timestamp_column: str
    cutoff: datetime
    expired_records: int
    deleted_records: int
    dry_run: bool
    batch_size: int
    max_batches: int

    def as_dict(
        self,
    ) -> dict[str, object]:
        return {
            "table_name": self.table_name,
            "timestamp_column": self.timestamp_column,
            "cutoff": self.cutoff.isoformat(),
            "expired_records": self.expired_records,
            "deleted_records": self.deleted_records,
            "dry_run": self.dry_run,
            "batch_size": self.batch_size,
            "max_batches": self.max_batches,
        }


@dataclass(frozen=True, slots=True)
class TelemetryRetentionRunResult:
    """
    Bounded telemetry retention run result.
    """

    as_of: datetime
    cutoff: datetime
    dry_run: bool
    summaries: tuple[TelemetryRetentionTableSummary, ...]
    duration_seconds: float
    errors: tuple[str, ...] = ()

    @property
    def success(
        self,
    ) -> bool:
        return not self.errors

    @property
    def total_expired_records(
        self,
    ) -> int:
        return sum(summary.expired_records for summary in self.summaries)

    @property
    def total_deleted_records(
        self,
    ) -> int:
        return sum(summary.deleted_records for summary in self.summaries)

    def as_dict(
        self,
    ) -> dict[str, object]:
        return {
            "as_of": self.as_of.isoformat(),
            "cutoff": self.cutoff.isoformat(),
            "dry_run": self.dry_run,
            "success": self.success,
            "total_expired_records": self.total_expired_records,
            "total_deleted_records": self.total_deleted_records,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
            "summaries": tuple(summary.as_dict() for summary in self.summaries),
        }


@dataclass(frozen=True, slots=True)
class _TelemetryRetentionTable:
    table_name: str
    model: Any
    id_column_name: str
    timestamp_column_name: str

    @property
    def id_column(
        self,
    ) -> Any:
        return getattr(self.model, self.id_column_name)

    @property
    def timestamp_column(
        self,
    ) -> Any:
        return getattr(self.model, self.timestamp_column_name)


TELEMETRY_RETENTION_TABLES: tuple[_TelemetryRetentionTable, ...] = (
    _TelemetryRetentionTable(
        table_name="telemetry_events",
        model=TelemetryEventModel,
        id_column_name="telemetry_event_id",
        timestamp_column_name="timestamp",
    ),
    _TelemetryRetentionTable(
        table_name="telemetry_metrics",
        model=TelemetryMetricModel,
        id_column_name="metric_id",
        timestamp_column_name="timestamp",
    ),
    _TelemetryRetentionTable(
        table_name="telemetry_traces",
        model=TelemetryTraceModel,
        id_column_name="trace_record_id",
        timestamp_column_name="started_at",
    ),
    _TelemetryRetentionTable(
        table_name="workflow_metrics",
        model=WorkflowMetricModel,
        id_column_name="workflow_metric_id",
        timestamp_column_name="timestamp",
    ),
    _TelemetryRetentionTable(
        table_name="agent_metrics",
        model=AgentMetricModel,
        id_column_name="agent_metric_id",
        timestamp_column_name="timestamp",
    ),
    _TelemetryRetentionTable(
        table_name="provider_metrics",
        model=ProviderMetricModel,
        id_column_name="provider_metric_id",
        timestamp_column_name="timestamp",
    ),
)


class TelemetryRetentionService:
    """
    PostgreSQL telemetry retention and volume control service.

    The service is explicit and bounded: dry-run planning is the default, and
    physical deletion happens only when callers invoke ``purge_expired`` with
    ``dry_run=False``.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        config: TelemetryRetentionConfig | None = None,
        observability_manager: ObservabilityManager | None = None,
        tables: Sequence[_TelemetryRetentionTable] = TELEMETRY_RETENTION_TABLES,
    ) -> None:
        self._session = session
        self._config = config or TelemetryRetentionConfig()
        self._observability_manager = observability_manager
        self._tables = tuple(tables)

    async def plan_expired(
        self,
        *,
        as_of: datetime,
    ) -> TelemetryRetentionRunResult:
        return await self.purge_expired(as_of=as_of, dry_run=True)

    async def purge_expired(
        self,
        *,
        as_of: datetime,
        dry_run: bool = True,
    ) -> TelemetryRetentionRunResult:
        started_at = perf_counter()
        cutoff = as_of - self._config.retention_period
        summaries: list[TelemetryRetentionTableSummary] = []
        errors: list[str] = []

        try:
            for table in self._tables:
                expired_records = await self._count_expired(
                    table=table,
                    cutoff=cutoff,
                )
                deleted_records = 0
                if not dry_run:
                    deleted_records = await self._delete_expired_batches(
                        table=table,
                        cutoff=cutoff,
                    )

                summaries.append(
                    TelemetryRetentionTableSummary(
                        table_name=table.table_name,
                        timestamp_column=table.timestamp_column_name,
                        cutoff=cutoff,
                        expired_records=expired_records,
                        deleted_records=deleted_records,
                        dry_run=dry_run,
                        batch_size=self._config.batch_size,
                        max_batches=self._config.max_batches,
                    )
                )

            if not dry_run:
                await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            errors.append(str(exc))

        result = TelemetryRetentionRunResult(
            as_of=as_of,
            cutoff=cutoff,
            dry_run=dry_run,
            summaries=tuple(summaries),
            duration_seconds=perf_counter() - started_at,
            errors=tuple(errors),
        )
        await self._record_retention_telemetry(result)

        return result

    async def _count_expired(
        self,
        *,
        table: _TelemetryRetentionTable,
        cutoff: datetime,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(table.model)
            .where(table.timestamp_column < cutoff)
        )
        result = await self._session.execute(statement)

        return int(result.scalar_one())

    async def _delete_expired_batches(
        self,
        *,
        table: _TelemetryRetentionTable,
        cutoff: datetime,
    ) -> int:
        deleted_records = 0
        for _ in range(self._config.max_batches):
            candidate_ids = (
                select(table.id_column)
                .where(table.timestamp_column < cutoff)
                .order_by(table.timestamp_column)
                .limit(self._config.batch_size)
                .subquery()
            )
            id_column = getattr(candidate_ids.c, self._candidate_id_column_key(table))
            statement = delete(table.model).where(
                table.id_column.in_(select(id_column))
            )
            result = await self._session.execute(statement)
            batch_deleted = int(getattr(result, "rowcount", 0) or 0)
            deleted_records += batch_deleted

            if batch_deleted < self._config.batch_size:
                break

        return deleted_records

    def _candidate_id_column_key(
        self,
        table: _TelemetryRetentionTable,
    ) -> str:
        column_key = getattr(table.id_column, "key", None)
        if isinstance(column_key, str) and column_key:
            return column_key

        return table.id_column_name

    async def _record_retention_telemetry(
        self,
        result: TelemetryRetentionRunResult,
    ) -> None:
        if self._observability_manager is None:
            return

        attributes = {
            "dry_run": result.dry_run,
            "success": result.success,
        }
        self._observability_manager.increment(
            "telemetry.retention.records_scanned",
            value=float(result.total_expired_records),
            attributes=attributes,
        )
        self._observability_manager.increment(
            "telemetry.retention.records_deleted",
            value=float(result.total_deleted_records),
            attributes=attributes,
        )
        self._observability_manager.observe(
            "telemetry.retention.duration_seconds",
            result.duration_seconds,
            attributes=attributes,
        )
        if result.errors:
            self._observability_manager.increment(
                "telemetry.retention.errors",
                value=float(len(result.errors)),
                attributes=attributes,
            )
            await self._observability_manager.error(
                event_type="telemetry.retention.failed",
                source="application.persistence.retention",
                payload=result.as_dict(),
            )
            return

        await self._observability_manager.info(
            event_type="telemetry.retention.completed",
            source="application.persistence.retention",
            payload=result.as_dict(),
        )
