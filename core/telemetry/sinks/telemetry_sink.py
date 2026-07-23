from __future__ import annotations

from typing import Any, Protocol

from core.telemetry.events.telemetry_event import TelemetryEvent


class TelemetrySink(Protocol):
    """
    Generic telemetry sink contract.

    Implementations may forward telemetry events to:
    - local JSONL files
    - logs
    - metrics stores
    - OpenTelemetry
    - Datadog
    - Prometheus adapters
    - test buffers
    """

    async def emit(
        self,
        event: TelemetryEvent,
    ) -> None: ...


class InMemoryTelemetrySink:
    """
    Simple in-memory telemetry sink for tests and local debugging.
    """

    def __init__(
        self,
    ) -> None:
        self.events: list[TelemetryEvent] = []

    async def emit(
        self,
        event: TelemetryEvent,
    ) -> None:
        self.events.append(
            event,
        )

    def clear(
        self,
    ) -> None:
        self.events.clear()

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "sink": self.__class__.__name__,
            "event_count": len(self.events),
            "events": [event.to_dict() for event in self.events],
        }
