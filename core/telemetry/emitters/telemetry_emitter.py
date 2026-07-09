from __future__ import annotations

from typing import Any

from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.contracts.telemetry_severity import TelemetrySeverity
from core.telemetry.events.telemetry_event import (
    TelemetryEvent,
    TelemetryEventLevel,
)
from core.telemetry.events.telemetry_exception_details import (
    TelemetryExceptionDetails,
)
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)


class TelemetryEmitter:
    """
    Base emitter that routes telemetry through ObservabilityManager.
    """

    def __init__(
        self,
        observability_manager: ObservabilityManager,
        source: str,
    ) -> None:
        self.observability_manager = observability_manager
        self.source = source

    async def emit(
        self,
        event_type: str,
        *,
        severity: TelemetrySeverity = TelemetrySeverity.INFO,
        context: TelemetryContext | None = None,
        duration_seconds: float | None = None,
        success: bool | None = None,
        error_count: int = 0,
        exception_details: TelemetryExceptionDetails | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        telemetry_context = context or TelemetryContext()

        await self.observability_manager.emit(
            TelemetryEvent(
                event_type=event_type,
                source=self.source,
                level=TelemetryEventLevel(severity.value),
                workflow_id=telemetry_context.workflow_id,
                execution_id=telemetry_context.execution_id,
                runtime_id=telemetry_context.runtime_id,
                node_name=telemetry_context.node_name,
                correlation_id=telemetry_context.correlation_id,
                trace_id=telemetry_context.trace_id,
                span_id=telemetry_context.span_id,
                parent_span_id=telemetry_context.parent_span_id,
                duration_seconds=duration_seconds,
                success=success,
                error_count=error_count,
                exception_details=exception_details,
                tags=telemetry_context.tags,
                attributes=telemetry_context.merged_attributes(attributes),
                payload=dict(payload or {}),
            )
        )
