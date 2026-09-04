from __future__ import annotations

from typing import Any

from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.contracts.telemetry_severity import TelemetrySeverity
from core.telemetry.emitters.telemetry_emitter import TelemetryEmitter
from core.telemetry.events.telemetry_exception_details import (
    TelemetryExceptionDetails,
)
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)


class IntegrationTelemetry(TelemetryEmitter):
    """
    Telemetry emitter for provider/client integration boundaries.
    """

    def __init__(
        self,
        observability_manager: ObservabilityManager,
        source: str = "integration",
    ) -> None:
        super().__init__(
            observability_manager=observability_manager,
            source=source,
        )

    async def emit_provider_call(
        self,
        provider_name: str,
        operation: str,
        *,
        context: TelemetryContext | None = None,
        duration_seconds: float | None = None,
        success: bool | None = None,
        error: BaseException | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        merged_payload = {
            "provider_name": provider_name,
            "operation": operation,
            "success": success,
            **dict(payload or {}),
        }
        if duration_seconds is not None:
            merged_payload["duration_seconds"] = duration_seconds

        await self.emit(
            "integration.provider.call",
            severity=(
                TelemetrySeverity.INFO
                if success is not False
                else TelemetrySeverity.ERROR
            ),
            context=context,
            duration_seconds=duration_seconds,
            success=success,
            error_count=0 if success is not False else 1,
            exception_details=(
                TelemetryExceptionDetails.from_exception(error)
                if error is not None
                else None
            ),
            attributes={
                "provider_name": provider_name,
                "operation": operation,
                **dict(attributes or {}),
            },
            payload=merged_payload,
        )

    async def emit_client_retry_scheduled(
        self,
        provider_name: str,
        client_name: str,
        operation: str,
        *,
        attempt: int,
        next_attempt: int,
        maximum_attempts: int,
        backoff_seconds: float,
        status_code: int | None = None,
        error_type: str | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        retry_details: dict[str, Any] = {
            "provider_name": provider_name,
            "client_name": client_name,
            "operation": operation,
            "attempt": attempt,
            "next_attempt": next_attempt,
            "maximum_attempts": maximum_attempts,
            "backoff_seconds": backoff_seconds,
        }
        if status_code is not None:
            retry_details["status_code"] = status_code
        if error_type is not None:
            retry_details["error_type"] = error_type

        await self.emit(
            "integration.client.retry_scheduled",
            severity=TelemetrySeverity.WARNING,
            context=context,
            success=None,
            attributes={
                **retry_details,
                **dict(attributes or {}),
            },
            payload={
                **retry_details,
                **dict(payload or {}),
            },
        )

    async def emit_provider_cancelled(
        self,
        provider_name: str,
        operation: str,
        *,
        context: TelemetryContext | None = None,
        duration_seconds: float | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self.emit(
            "integration.provider.cancelled",
            severity=TelemetrySeverity.WARNING,
            context=context,
            duration_seconds=duration_seconds,
            success=False,
            attributes={
                "provider_name": provider_name,
                "operation": operation,
                "outcome": "cancelled",
                **dict(attributes or {}),
            },
            payload={
                "provider_name": provider_name,
                "operation": operation,
                "outcome": "cancelled",
                **dict(payload or {}),
            },
        )
