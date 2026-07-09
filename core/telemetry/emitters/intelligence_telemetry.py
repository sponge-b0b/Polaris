from __future__ import annotations

from typing import Any

from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.contracts.telemetry_severity import TelemetrySeverity
from core.telemetry.emitters.telemetry_emitter import TelemetryEmitter
from core.telemetry.events.telemetry_exception_details import TelemetryExceptionDetails
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)


class IntelligenceTelemetry(TelemetryEmitter):
    """
    Telemetry emitter for intelligence-layer agent outputs.
    """

    def __init__(
        self,
        observability_manager: ObservabilityManager,
        source: str = "intelligence",
    ) -> None:
        super().__init__(
            observability_manager=observability_manager,
            source=source,
        )

    async def emit_agent_signal(
        self,
        agent_name: str,
        signal_name: str,
        *,
        confidence: float | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self.emit(
            "intelligence.agent.signal",
            severity=TelemetrySeverity.INFO,
            context=context,
            success=True,
            attributes={
                "agent_name": agent_name,
                "signal_name": signal_name,
                "confidence": confidence,
                **dict(attributes or {}),
            },
            payload=payload,
        )

    async def emit_agent_degraded(
        self,
        agent_name: str,
        reason: str,
        *,
        error: BaseException | str | None = None,
        context: TelemetryContext | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        exception_details = (
            TelemetryExceptionDetails.from_exception(error)
            if isinstance(error, BaseException)
            else None
        )
        await self.emit(
            "intelligence.agent.degraded",
            severity=TelemetrySeverity.WARNING,
            context=context,
            success=True,
            exception_details=exception_details,
            attributes={
                "agent_name": agent_name,
                "reason": reason,
                **dict(attributes or {}),
            },
            payload={
                **({"error_message": str(error)} if error is not None else {}),
                **dict(payload or {}),
            },
        )
