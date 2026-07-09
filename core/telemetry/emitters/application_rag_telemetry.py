from __future__ import annotations

from typing import Any

from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.events.telemetry_exception_details import TelemetryExceptionDetails
from core.telemetry.observability.observability_manager import ObservabilityManager


class ApplicationRagTelemetry:
    """
    Telemetry emitter for platform-native RAG pipeline operations.

    RAG telemetry is operation/stage-oriented and is intentionally separate
    from ServiceRunner request lifecycle telemetry.
    """

    def __init__(
        self,
        observability_manager: ObservabilityManager,
        source: str = "application.rag",
    ) -> None:
        self.observability_manager = observability_manager
        self.source = source

    async def emit_operation_started(
        self,
        component_name: str,
        operation: str,
        *,
        correlation_id: str | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self._emit(
            event_type="application.rag.operation.started",
            level=TelemetryEventLevel.INFO,
            component_name=component_name,
            operation=operation,
            success=None,
            correlation_id=correlation_id,
            context=context,
            attributes=attributes,
            payload=payload,
        )

    async def emit_operation_completed(
        self,
        component_name: str,
        operation: str,
        *,
        duration_seconds: float | None = None,
        correlation_id: str | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self._emit(
            event_type="application.rag.operation.completed",
            level=TelemetryEventLevel.INFO,
            component_name=component_name,
            operation=operation,
            success=True,
            duration_seconds=duration_seconds,
            correlation_id=correlation_id,
            context=context,
            attributes=attributes,
            payload=payload,
        )

    async def emit_operation_degraded(
        self,
        component_name: str,
        operation: str,
        *,
        error: BaseException | str | None = None,
        duration_seconds: float | None = None,
        correlation_id: str | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        merged_payload = dict(payload or {})
        exception_details = None
        if error is not None:
            merged_payload.update(
                {
                    "error_type": (
                        type(error).__name__
                        if isinstance(error, BaseException)
                        else "RagDegradation"
                    ),
                    "error_message": str(error),
                }
            )
            if isinstance(error, BaseException):
                exception_details = TelemetryExceptionDetails.from_exception(error)
        await self._emit(
            event_type="application.rag.operation.degraded",
            level=TelemetryEventLevel.WARNING,
            component_name=component_name,
            operation=operation,
            success=True,
            duration_seconds=duration_seconds,
            correlation_id=correlation_id,
            context=context,
            attributes=attributes,
            payload=merged_payload,
            exception_details=exception_details,
        )

    async def emit_operation_failed(
        self,
        component_name: str,
        operation: str,
        *,
        error: BaseException | str,
        duration_seconds: float | None = None,
        correlation_id: str | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        error_message = str(error) if isinstance(error, BaseException) else error
        error_type = (
            type(error).__name__ if isinstance(error, BaseException) else "RagError"
        )
        merged_payload = {
            "error_type": error_type,
            "error_message": error_message,
            **dict(payload or {}),
        }
        exception_details = (
            TelemetryExceptionDetails.from_exception(error)
            if isinstance(error, BaseException)
            else None
        )
        await self._emit(
            event_type="application.rag.operation.failed",
            level=TelemetryEventLevel.ERROR,
            component_name=component_name,
            operation=operation,
            success=False,
            duration_seconds=duration_seconds,
            error_count=1,
            correlation_id=correlation_id,
            context=context,
            attributes=attributes,
            payload=merged_payload,
            exception_details=exception_details,
        )

    async def _emit(
        self,
        event_type: str,
        level: TelemetryEventLevel,
        component_name: str,
        operation: str,
        *,
        success: bool | None,
        duration_seconds: float | None = None,
        error_count: int = 0,
        correlation_id: str | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        exception_details: TelemetryExceptionDetails | None = None,
    ) -> None:
        operation_name = operation.strip()
        if not operation_name:
            raise ValueError("operation cannot be empty.")

        telemetry_context = context or TelemetryContext()
        operation_attributes = {
            "component_name": component_name,
            "operation": operation_name,
            **dict(attributes or {}),
        }
        operation_payload = {
            "component_name": component_name,
            "operation": operation_name,
            **dict(payload or {}),
        }
        await self.observability_manager.emit(
            TelemetryEvent(
                event_type=event_type,
                source=self.source,
                level=level,
                success=success,
                error_count=error_count,
                exception_details=exception_details,
                workflow_id=telemetry_context.workflow_id,
                execution_id=telemetry_context.execution_id,
                runtime_id=telemetry_context.runtime_id,
                node_name=telemetry_context.node_name,
                correlation_id=correlation_id or telemetry_context.correlation_id,
                trace_id=telemetry_context.trace_id,
                span_id=telemetry_context.span_id,
                parent_span_id=telemetry_context.parent_span_id,
                duration_seconds=duration_seconds,
                tags=telemetry_context.tags,
                attributes=telemetry_context.merged_attributes(operation_attributes),
                payload=operation_payload,
            )
        )
