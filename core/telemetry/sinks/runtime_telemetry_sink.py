from __future__ import annotations

from typing import Any, Protocol

from core.runtime.telemetry.runtime_telemetry import (
    RuntimeTelemetryEvent,
    RuntimeTelemetrySink,
)
from core.telemetry.events.telemetry_event import (
    TelemetryEvent,
    TelemetryEventLevel,
)


class TelemetryEventEmitter(Protocol):
    """
    Minimal emitter protocol.

    Supported implementations:
    - TelemetryCollector
    - ObservabilityManager
    - any sink-like object with async emit(TelemetryEvent)
    """

    async def emit(
        self,
        event: TelemetryEvent,
    ) -> None: ...


class CoreTelemetryRuntimeSink(RuntimeTelemetrySink):
    """
    Runtime telemetry sink adapter.

    Bridges:

        RuntimeTelemetryEvent
            -> TelemetryEvent
            -> ObservabilityManager / TelemetryCollector / TelemetrySink

    Prefer passing ObservabilityManager so metrics are recorded.
    """

    def __init__(
        self,
        sink: TelemetryEventEmitter,
        source: str = "runtime",
    ) -> None:
        self.sink = sink
        self.source = source

    async def emit(
        self,
        event: RuntimeTelemetryEvent,
    ) -> None:
        await self.sink.emit(
            self._convert_event(
                event,
            )
        )

    def _convert_event(
        self,
        event: RuntimeTelemetryEvent,
    ) -> TelemetryEvent:
        payload = dict(event.payload)

        nested_runtime_event = payload.get(
            "runtime_event",
        )

        nested_payload = (
            nested_runtime_event.get("payload", {})
            if isinstance(nested_runtime_event, dict)
            else {}
        )

        success = event.success

        if success is None and isinstance(nested_payload, dict):
            nested_success = nested_payload.get(
                "success",
            )

            if isinstance(nested_success, bool):
                success = nested_success

        error_count = event.error_count

        if error_count == 0 and isinstance(nested_payload, dict):
            nested_error_count = nested_payload.get(
                "error_count",
            )

            if isinstance(nested_error_count, int):
                error_count = nested_error_count

        trace_payload = nested_payload if isinstance(nested_payload, dict) else {}

        return TelemetryEvent(
            event_type=event.event_type.value,
            source=self.source,
            timestamp=event.timestamp,
            level=self._level_from_runtime_event(
                event=event,
                success=success,
                error_count=error_count,
            ),
            workflow_id=event.workflow_id,
            execution_id=event.execution_id,
            runtime_id=event.runtime_id,
            node_name=event.node_name,
            correlation_id=_payload_text(payload, "correlation_id", trace_payload),
            trace_id=_payload_text(payload, "trace_id", trace_payload),
            span_id=_payload_text(payload, "span_id", trace_payload),
            parent_span_id=_payload_text(
                payload,
                "parent_span_id",
                trace_payload,
            ),
            duration_seconds=event.duration_seconds,
            success=success,
            error_count=error_count,
            tags=event.tags,
            attributes={
                "wave_index": event.wave_index,
            },
            payload=payload,
        )

    def _level_from_runtime_event(
        self,
        event: RuntimeTelemetryEvent,
        success: bool | None,
        error_count: int,
    ) -> TelemetryEventLevel:
        if success is False or error_count > 0:
            return TelemetryEventLevel.ERROR

        if "failed" in event.event_type.value:
            return TelemetryEventLevel.ERROR

        if "skipped" in event.event_type.value:
            return TelemetryEventLevel.WARNING

        return TelemetryEventLevel.INFO

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "sink": self.__class__.__name__,
            "source": self.source,
            "target_sink": self.sink.__class__.__name__,
        }


def _payload_text(
    payload: dict[str, Any],
    key: str,
    fallback: dict[str, Any] | None = None,
) -> str | None:
    value = payload.get(key)
    if value is None and fallback is not None:
        value = fallback.get(key)
    if value is None:
        return None
    return str(value)
