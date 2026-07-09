from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Any

from core.telemetry.events.telemetry_event import (
    TelemetryEvent,
    TelemetryEventLevel,
)
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from core.telemetry.tracing.trace_context import TraceContext


@dataclass(frozen=True, slots=True)
class TelemetryLifecycleEvent:
    """
    Immutable lifecycle event descriptor.
    """

    name: str

    source: str

    level: TelemetryEventLevel = TelemetryEventLevel.INFO

    timestamp: datetime = datetime.now(timezone.utc)

    payload: dict[str, Any] | None = None

    attributes: dict[str, Any] | None = None

    trace_context: TraceContext | None = None

    success: bool | None = None

    error_count: int = 0

    def to_telemetry_event(
        self,
    ) -> TelemetryEvent:
        return TelemetryEvent(
            event_type=self.name,
            source=self.source,
            timestamp=self.timestamp,
            level=self.level,
            workflow_id=(
                self.trace_context.workflow_id
                if self.trace_context is not None
                else None
            ),
            execution_id=(
                self.trace_context.execution_id
                if self.trace_context is not None
                else None
            ),
            runtime_id=(
                self.trace_context.runtime_id
                if self.trace_context is not None
                else None
            ),
            node_name=(
                self.trace_context.node_name if self.trace_context is not None else None
            ),
            correlation_id=(
                self.trace_context.correlation_id
                if self.trace_context is not None
                else None
            ),
            trace_id=(
                self.trace_context.trace_id if self.trace_context is not None else None
            ),
            span_id=(
                self.trace_context.span_id if self.trace_context is not None else None
            ),
            parent_span_id=(
                self.trace_context.parent_span_id
                if self.trace_context is not None
                else None
            ),
            success=self.success,
            error_count=self.error_count,
            attributes={
                **dict(self.attributes or {}),
                **(
                    self.trace_context.attributes
                    if self.trace_context is not None
                    else {}
                ),
                **(
                    self.trace_context.telemetry_attributes()
                    if self.trace_context is not None
                    else {}
                ),
            },
            payload=dict(self.payload or {}),
        )


class TelemetryLifecycle:
    """
    Generic telemetry lifecycle helper.

    Provides a small reusable layer for emitting lifecycle-style telemetry
    events without coupling callers directly to sinks or collectors.
    """

    def __init__(
        self,
        observability_manager: ObservabilityManager,
        source: str,
    ) -> None:
        self.observability_manager = observability_manager
        self.source = source

    async def started(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        attributes: dict[str, Any] | None = None,
        trace_context: TraceContext | None = None,
    ) -> None:
        await self.emit(
            name=f"{name}.started",
            level=TelemetryEventLevel.INFO,
            payload=payload,
            attributes=attributes,
            trace_context=trace_context,
            success=None,
        )

    async def completed(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        attributes: dict[str, Any] | None = None,
        trace_context: TraceContext | None = None,
        success: bool = True,
    ) -> None:
        await self.emit(
            name=f"{name}.completed",
            level=(TelemetryEventLevel.INFO if success else TelemetryEventLevel.ERROR),
            payload=payload,
            attributes=attributes,
            trace_context=trace_context,
            success=success,
            error_count=0 if success else 1,
        )

    async def failed(
        self,
        name: str,
        error: Exception,
        payload: dict[str, Any] | None = None,
        attributes: dict[str, Any] | None = None,
        trace_context: TraceContext | None = None,
    ) -> None:
        await self.emit(
            name=f"{name}.failed",
            level=TelemetryEventLevel.ERROR,
            payload={
                **dict(payload or {}),
                "error_type": type(error).__name__,
                "message": str(error),
            },
            attributes=attributes,
            trace_context=trace_context,
            success=False,
            error_count=1,
        )

    async def skipped(
        self,
        name: str,
        reason: str,
        payload: dict[str, Any] | None = None,
        attributes: dict[str, Any] | None = None,
        trace_context: TraceContext | None = None,
    ) -> None:
        await self.emit(
            name=f"{name}.skipped",
            level=TelemetryEventLevel.WARNING,
            payload={
                **dict(payload or {}),
                "reason": reason,
            },
            attributes=attributes,
            trace_context=trace_context,
            success=None,
        )

    async def emit(
        self,
        name: str,
        level: TelemetryEventLevel = TelemetryEventLevel.INFO,
        payload: dict[str, Any] | None = None,
        attributes: dict[str, Any] | None = None,
        trace_context: TraceContext | None = None,
        success: bool | None = None,
        error_count: int = 0,
    ) -> None:
        lifecycle_event = TelemetryLifecycleEvent(
            name=name,
            source=self.source,
            level=level,
            payload=payload,
            attributes=attributes,
            trace_context=trace_context,
            success=success,
            error_count=error_count,
        )

        await self.observability_manager.emit(
            lifecycle_event.to_telemetry_event(),
        )
