from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.events.telemetry_event import TelemetryEventLevel
from core.telemetry.events.telemetry_exception_details import (
    TelemetryExceptionDetails,
)
from core.telemetry.observability.observability_manager import ObservabilityManager


@dataclass(frozen=True, slots=True)
class _ServiceTelemetryEvent:
    event_type: str
    level: TelemetryEventLevel
    success: bool | None
    duration_seconds: float | None = None
    error_count: int = 0
    exception_details: TelemetryExceptionDetails | None = None


class ApplicationServiceTelemetry:
    """
    Telemetry emitter for canonical ServiceRunner-managed application services.

    This emitter is intentionally scoped to ServiceRequest/ServiceResult
    lifecycle events. RAG pipeline operation telemetry belongs to
    ApplicationRagTelemetry.
    """

    def __init__(
        self,
        observability_manager: ObservabilityManager,
        source: str = "application",
    ) -> None:
        self.observability_manager = observability_manager
        self.source = source

    async def emit_service_started(
        self,
        service_name: str,
        request_name: str,
        *,
        correlation_id: str | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self._emit(
            event=_ServiceTelemetryEvent(
                event_type="application.service.started",
                level=TelemetryEventLevel.INFO,
                success=None,
            ),
            service_name=service_name,
            request_name=request_name,
            correlation_id=correlation_id,
            context=context,
            attributes=attributes,
            payload=payload,
        )

    async def emit_service_completed(
        self,
        service_name: str,
        request_name: str,
        *,
        duration_seconds: float | None = None,
        correlation_id: str | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self._emit(
            event=_ServiceTelemetryEvent(
                event_type="application.service.completed",
                level=TelemetryEventLevel.INFO,
                success=True,
                duration_seconds=duration_seconds,
            ),
            service_name=service_name,
            request_name=request_name,
            correlation_id=correlation_id,
            context=context,
            attributes=attributes,
            payload=payload,
        )

    async def emit_service_failed(
        self,
        service_name: str,
        request_name: str,
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
            type(error).__name__
            if isinstance(error, BaseException)
            else "ApplicationServiceError"
        )
        merged_payload = {
            "error_type": error_type,
            "error_message": error_message,
            **dict(payload or {}),
        }
        await self._emit(
            event=_ServiceTelemetryEvent(
                event_type="application.service.failed",
                level=TelemetryEventLevel.ERROR,
                success=False,
                duration_seconds=duration_seconds,
                error_count=1,
                exception_details=(
                    TelemetryExceptionDetails.from_exception(error)
                    if isinstance(error, BaseException)
                    else None
                ),
            ),
            service_name=service_name,
            request_name=request_name,
            correlation_id=correlation_id,
            context=context,
            attributes=attributes,
            payload=merged_payload,
        )

    async def emit_service_configuration_failed(
        self,
        service_name: str,
        request_name: str,
        *,
        validation_errors: tuple[str, ...],
        correlation_id: str | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self._emit(
            event=_ServiceTelemetryEvent(
                event_type="application.service.configuration_failed",
                level=TelemetryEventLevel.ERROR,
                success=False,
                error_count=1,
            ),
            service_name=service_name,
            request_name=request_name,
            correlation_id=correlation_id,
            context=context,
            attributes=attributes,
            payload={
                "error_type": "ServiceRunnerConfigurationError",
                "error_message": "Invalid service runner configuration.",
                "validation_errors": list(validation_errors),
                **dict(payload or {}),
            },
        )

    async def emit_service_retry_scheduled(
        self,
        service_name: str,
        request_name: str,
        *,
        attempt: int,
        next_attempt: int,
        maximum_attempts: int,
        backoff_seconds: float,
        reason: str,
        error_type: str,
        correlation_id: str | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        retry_details = {
            "attempt": attempt,
            "next_attempt": next_attempt,
            "maximum_attempts": maximum_attempts,
            "backoff_seconds": backoff_seconds,
            "reason": reason,
            "error_type": error_type,
        }
        await self._emit(
            event=_ServiceTelemetryEvent(
                event_type="application.service.retry_scheduled",
                level=TelemetryEventLevel.WARNING,
                success=None,
            ),
            service_name=service_name,
            request_name=request_name,
            correlation_id=correlation_id,
            context=context,
            attributes={
                **retry_details,
                **dict(attributes or {}),
            },
            payload={
                **retry_details,
                **dict(payload or {}),
            },
        )

    async def emit_service_degraded(
        self,
        service_name: str,
        request_name: str,
        *,
        duration_seconds: float | None = None,
        correlation_id: str | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self._emit(
            event=_ServiceTelemetryEvent(
                event_type="application.service.degraded",
                level=TelemetryEventLevel.WARNING,
                success=True,
                duration_seconds=duration_seconds,
            ),
            service_name=service_name,
            request_name=request_name,
            correlation_id=correlation_id,
            context=context,
            attributes=attributes,
            payload=payload,
        )

    async def emit_service_cancelled(
        self,
        service_name: str,
        request_name: str,
        *,
        duration_seconds: float | None = None,
        correlation_id: str | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self._emit(
            event=_ServiceTelemetryEvent(
                event_type="application.service.cancelled",
                level=TelemetryEventLevel.WARNING,
                success=False,
                duration_seconds=duration_seconds,
            ),
            service_name=service_name,
            request_name=request_name,
            correlation_id=correlation_id,
            context=context,
            attributes={
                "outcome": "cancelled",
                **dict(attributes or {}),
            },
            payload={
                "outcome": "cancelled",
                **dict(payload or {}),
            },
        )

    async def _emit(
        self,
        event: _ServiceTelemetryEvent,
        service_name: str,
        request_name: str,
        *,
        correlation_id: str | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        telemetry_context = context or TelemetryContext()
        merged_attributes = telemetry_context.merged_attributes(
            {
                "service_name": service_name,
                "request_name": request_name,
                **dict(attributes or {}),
            }
        )
        merged_payload = {
            "service_name": service_name,
            "request_name": request_name,
            **dict(payload or {}),
        }
        await self.observability_manager.emit(
            TelemetryEvent(
                event_type=event.event_type,
                source=self.source,
                level=event.level,
                success=event.success,
                error_count=event.error_count,
                exception_details=event.exception_details,
                workflow_id=telemetry_context.workflow_id,
                execution_id=telemetry_context.execution_id,
                runtime_id=telemetry_context.runtime_id,
                node_name=telemetry_context.node_name,
                correlation_id=correlation_id or telemetry_context.correlation_id,
                trace_id=telemetry_context.trace_id,
                span_id=telemetry_context.span_id,
                parent_span_id=telemetry_context.parent_span_id,
                duration_seconds=event.duration_seconds,
                tags=telemetry_context.tags,
                attributes=merged_attributes,
                payload=merged_payload,
            )
        )
