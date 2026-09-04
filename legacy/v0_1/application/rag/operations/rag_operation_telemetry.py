from __future__ import annotations

from application.rag.contracts.rag_operation_models import (
    RagOperationDetail,
    RagOperationResult,
)
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry


class RagOperationTelemetry:
    """Shared telemetry boundary for focused RAG operational services."""

    def __init__(
        self,
        component: str,
        telemetry: ApplicationRagTelemetry | None,
    ) -> None:
        self._component = component
        self._telemetry = telemetry

    async def emit_started(
        self,
        operation: str,
        *,
        details: tuple[RagOperationDetail, ...] = (),
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_started(
            self._component,
            operation,
            attributes=details_to_attributes(details),
        )

    async def emit_completed(
        self,
        operation: str,
        *,
        result: RagOperationResult,
        duration_seconds: float,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_completed(
            self._component,
            operation,
            duration_seconds=duration_seconds,
            attributes={
                "records_processed": result.records_processed,
                "dry_run": result.dry_run,
                **details_to_attributes(result.details),
            },
        )

    async def emit_failed(
        self,
        operation: str,
        *,
        error: BaseException,
        duration_seconds: float,
        details: tuple[RagOperationDetail, ...] = (),
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_failed(
            self._component,
            operation,
            error=error,
            duration_seconds=duration_seconds,
            attributes=details_to_attributes(details),
        )

    async def emit_event(
        self,
        operation: str,
        *,
        attributes: dict[str, str | bool],
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_completed(
            self._component,
            operation,
            attributes=attributes,
        )


def details_to_attributes(
    details: tuple[RagOperationDetail, ...],
) -> dict[str, str]:
    return {detail.name: detail.value for detail in details}
