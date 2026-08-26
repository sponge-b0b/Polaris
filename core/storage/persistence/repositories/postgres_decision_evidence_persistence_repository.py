from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Executable

from core.database.models.decision_evidence import DecisionEvidencePacketModel
from core.storage.persistence.decision_evidence import (
    DecisionEvidencePacketPersistenceRepository,
    DecisionEvidencePacketPersistenceResult,
    DecisionEvidencePacketRecord,
)
from core.storage.persistence.serializers import (
    DecisionEvidencePacketPersistenceSerializer,
)
from core.telemetry.context import get_active_telemetry_context
from core.telemetry.contracts import TelemetryContext
from core.telemetry.events import TelemetryEventLevel, TelemetryExceptionDetails
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.observability import ObservabilityManager

logger = logging.getLogger(__name__)

_DATASTORE_EVENT_TYPE = "storage.postgres.operation"
_SOURCE = "core.storage.persistence"
_COMPONENT_NAME = "PostgresDecisionEvidencePacketRepository"
_TABLE_NAME = "decision_evidence_packets"
_WRITE_OPERATION = "decision_evidence_packet_write"
_READ_OPERATION = "decision_evidence_packet_read"
_OPERATION_TOTAL_METRIC = "storage.postgres.decision_evidence_packet.operations.total"
_OPERATION_FAILURE_METRIC = (
    "storage.postgres.decision_evidence_packet.operations.failed"
)
_OPERATION_DURATION_METRIC = (
    "storage.postgres.decision_evidence_packet.duration_seconds"
)


class PostgresDecisionEvidencePacketRepository(
    DecisionEvidencePacketPersistenceRepository,
):
    """PostgreSQL repository for decision evidence packet audit records."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        observability_manager: ObservabilityManager | None = None,
    ) -> None:
        self._session = session
        self._observability_manager = observability_manager

    async def persist_packet_record(
        self,
        record: DecisionEvidencePacketRecord,
    ) -> DecisionEvidencePacketPersistenceResult:
        started_at = perf_counter()
        try:
            result = await self._session.execute(_upsert_packet_statement(record))
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            await self._record_postgres_operation(
                operation=_WRITE_OPERATION,
                packet_id=record.packet_id,
                started_at=started_at,
                success=False,
                error=exc,
            )
            return DecisionEvidencePacketPersistenceResult.failed(
                str(exc),
                packet_id=record.packet_id,
            )

        records_persisted = _rowcount(cast(Any, result).rowcount)
        await self._record_postgres_operation(
            operation=_WRITE_OPERATION,
            packet_id=record.packet_id,
            started_at=started_at,
            success=True,
            records_persisted=records_persisted,
        )
        return DecisionEvidencePacketPersistenceResult.succeeded(
            record.packet_id,
            records_persisted=records_persisted,
        )

    async def get_packet_record(
        self,
        packet_id: str,
    ) -> DecisionEvidencePacketRecord | None:
        started_at = perf_counter()
        try:
            result = await self._session.execute(
                select(DecisionEvidencePacketModel).where(
                    DecisionEvidencePacketModel.packet_id == packet_id,
                )
            )
            model = result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            await self._record_postgres_operation(
                operation=_READ_OPERATION,
                packet_id=packet_id,
                started_at=started_at,
                success=False,
                error=exc,
            )
            raise

        await self._record_postgres_operation(
            operation=_READ_OPERATION,
            packet_id=packet_id,
            started_at=started_at,
            success=True,
            found=model is not None,
        )
        if model is None:
            return None
        return DecisionEvidencePacketPersistenceSerializer.record_from_model(model)

    async def _record_postgres_operation(
        self,
        *,
        operation: str,
        packet_id: str,
        started_at: float,
        success: bool,
        error: BaseException | None = None,
        records_persisted: int | None = None,
        found: bool | None = None,
    ) -> None:
        if self._observability_manager is None:
            return

        duration_seconds = perf_counter() - started_at
        context = _operation_context(
            operation=operation,
            packet_id=packet_id,
            success=success,
        )
        attributes = _operation_attributes(
            operation=operation,
            packet_id=packet_id,
            success=success,
        )
        metric_attributes = _operation_metric_attributes(
            operation=operation,
            success=success,
        )
        payload: dict[str, Any] = {
            "component_name": _COMPONENT_NAME,
            "database_system": "postgresql",
            "duration_seconds": duration_seconds,
            "operation": operation,
            "outcome": "succeeded" if success else "failed",
            "packet_id": packet_id,
            "success": success,
            "table": _TABLE_NAME,
        }
        if records_persisted is not None:
            payload["records_persisted"] = records_persisted
        if found is not None:
            payload["found"] = found
        if error is not None:
            payload["error_message"] = str(error)
            payload["error_type"] = type(error).__name__

        try:
            self._observability_manager.increment(
                _OPERATION_TOTAL_METRIC,
                tags=("postgresql", operation),
                attributes=metric_attributes,
            )
            if not success:
                self._observability_manager.increment(
                    _OPERATION_FAILURE_METRIC,
                    tags=("postgresql", operation),
                    attributes=metric_attributes,
                )
            self._observability_manager.observe(
                _OPERATION_DURATION_METRIC,
                value=duration_seconds,
                tags=("postgresql", operation),
                attributes=metric_attributes,
            )
            await self._observability_manager.emit(
                TelemetryEvent(
                    event_type=_DATASTORE_EVENT_TYPE,
                    source=_SOURCE,
                    level=(
                        TelemetryEventLevel.INFO
                        if success
                        else TelemetryEventLevel.ERROR
                    ),
                    workflow_id=context.workflow_id,
                    execution_id=context.execution_id,
                    runtime_id=context.runtime_id,
                    node_name=context.node_name,
                    correlation_id=context.correlation_id,
                    trace_id=context.trace_id,
                    span_id=context.span_id,
                    parent_span_id=context.parent_span_id,
                    duration_seconds=duration_seconds,
                    success=success,
                    error_count=0 if success else 1,
                    exception_details=(
                        TelemetryExceptionDetails.from_exception(error)
                        if error is not None
                        else None
                    ),
                    tags=context.tags,
                    attributes=context.merged_attributes(attributes),
                    payload=payload,
                )
            )
        except (RuntimeError, OSError) as observability_error:
            logger.debug(
                "Decision evidence PostgreSQL observability recording failed.",
                extra=_log_context(
                    operation=operation,
                    packet_id=packet_id,
                ),
                exc_info=(
                    type(observability_error),
                    observability_error,
                    observability_error.__traceback__,
                ),
            )


def _operation_context(
    *,
    operation: str,
    packet_id: str,
    success: bool,
) -> TelemetryContext:
    active_context = get_active_telemetry_context() or TelemetryContext()
    return active_context.child_operation(
        attributes=_operation_attributes(
            operation=operation,
            packet_id=packet_id,
            success=success,
        ),
    )


def _operation_attributes(
    *,
    operation: str,
    packet_id: str,
    success: bool,
) -> dict[str, Any]:
    return {
        "component_name": _COMPONENT_NAME,
        "database_system": "postgresql",
        "operation": operation,
        "operation_kind": "datastore_operation",
        "outcome": "succeeded" if success else "failed",
        "packet_id": packet_id,
        "table": _TABLE_NAME,
    }


def _operation_metric_attributes(
    *,
    operation: str,
    success: bool,
) -> dict[str, Any]:
    return {
        "component_name": _COMPONENT_NAME,
        "database_system": "postgresql",
        "operation": operation,
        "operation_kind": "datastore_operation",
        "outcome": "succeeded" if success else "failed",
        "table": _TABLE_NAME,
    }


def _log_context(
    *,
    operation: str,
    packet_id: str,
) -> dict[str, Any]:
    return {
        "component_name": _COMPONENT_NAME,
        "database_system": "postgresql",
        "operation": operation,
        "packet_id": packet_id,
        "table": _TABLE_NAME,
    }


def _upsert_packet_statement(
    record: DecisionEvidencePacketRecord,
) -> Executable:
    values = DecisionEvidencePacketPersistenceSerializer.packet_values(record)
    stmt = insert(DecisionEvidencePacketModel).values(**values)
    update_values = {key: value for key, value in values.items() if key != "packet_id"}
    update_values["updated_at"] = func.now()
    return stmt.on_conflict_do_update(
        index_elements=["packet_id"],
        set_=update_values,
    )


def _rowcount(value: object) -> int:
    if isinstance(value, int):
        return value
    return 0


__all__ = ["PostgresDecisionEvidencePacketRepository"]
