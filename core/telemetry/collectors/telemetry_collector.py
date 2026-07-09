from __future__ import annotations

import asyncio
import logging
from typing import Any
from typing import Iterable

from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.metrics.metrics_store import MetricsStore
from core.telemetry.sinks.telemetry_sink import TelemetrySink

logger = logging.getLogger(__name__)


class TelemetryCollector:
    """
    Central telemetry fan-out collector.

    Receives generic TelemetryEvent objects and forwards them to one or
    more configured telemetry sinks.

    This is intentionally infrastructure-only:
    - no runtime logic
    - no workflow logic
    - no business logic
    """

    def __init__(
        self,
        sinks: Iterable[TelemetrySink] | None = None,
        fail_fast: bool = False,
        metrics_store: MetricsStore | None = None,
    ) -> None:
        self._sinks: list[TelemetrySink] = list(
            sinks or [],
        )

        self.fail_fast = fail_fast
        self.metrics_store = metrics_store or MetricsStore()

    # ========================================================
    # SINK REGISTRATION
    # ========================================================

    def add_sink(
        self,
        sink: TelemetrySink,
    ) -> None:
        self._sinks.append(
            sink,
        )

    def register_sink(
        self,
        sink: TelemetrySink,
    ) -> None:
        self.add_sink(
            sink,
        )

    def add_sinks(
        self,
        sinks: Iterable[TelemetrySink],
    ) -> None:
        for sink in sinks:
            self.add_sink(
                sink,
            )

    def clear_sinks(
        self,
    ) -> None:
        self._sinks.clear()

    # ========================================================
    # LIFECYCLE
    # ========================================================

    def force_flush(
        self,
    ) -> None:
        for sink in self._sinks:
            force_flush = getattr(
                sink,
                "force_flush",
                None,
            )
            if not callable(force_flush):
                continue
            try:
                force_flush()
            except Exception as error:
                self._report_sink_failure(
                    sink=sink,
                    operation="force_flush",
                    error=error,
                )
                if self.fail_fast:
                    raise

    def shutdown(
        self,
    ) -> None:
        for sink in reversed(self._sinks):
            shutdown = getattr(
                sink,
                "shutdown",
                None,
            )
            if not callable(shutdown):
                continue
            try:
                shutdown()
            except Exception as error:
                self._report_sink_failure(
                    sink=sink,
                    operation="shutdown",
                    error=error,
                )
                if self.fail_fast:
                    raise

    # ========================================================
    # EMIT
    # ========================================================

    async def emit(
        self,
        event: TelemetryEvent,
    ) -> None:
        sinks = tuple(self._sinks)
        if not sinks:
            return

        if self.fail_fast:
            for sink in sinks:
                try:
                    await sink.emit(
                        event,
                    )
                except Exception as error:
                    self._report_sink_failure(
                        sink=sink,
                        operation="emit",
                        error=error,
                        event=event,
                    )
                    raise
            return

        results = await asyncio.gather(
            *[
                sink.emit(
                    event,
                )
                for sink in sinks
            ],
            return_exceptions=True,
        )
        for sink, result in zip(sinks, results, strict=True):
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, Exception):
                self._report_sink_failure(
                    sink=sink,
                    operation="emit",
                    error=result,
                    event=event,
                )

    async def emit_many(
        self,
        events: Iterable[TelemetryEvent],
    ) -> None:
        for event in events:
            await self.emit(
                event,
            )

    # ========================================================
    # INSPECTION
    # ========================================================

    @property
    def sinks(
        self,
    ) -> tuple[TelemetrySink, ...]:
        return tuple(
            self._sinks,
        )

    def sink_count(
        self,
    ) -> int:
        return len(
            self._sinks,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "collector": self.__class__.__name__,
            "sink_count": len(self._sinks),
            "sinks": [sink.__class__.__name__ for sink in self._sinks],
            "fail_fast": self.fail_fast,
        }

    def _report_sink_failure(
        self,
        *,
        sink: TelemetrySink,
        operation: str,
        error: Exception,
        event: TelemetryEvent | None = None,
    ) -> None:
        sink_name = sink.__class__.__name__
        event_id = event.event_id if event is not None else None
        event_type = event.event_type if event is not None else None
        trace_id = event.trace_id if event is not None else None
        span_id = event.span_id if event is not None else None
        correlation_id = event.correlation_id if event is not None else None

        logger.error(
            "Telemetry sink failure: sink=%s operation=%s event_id=%s "
            "event_type=%s trace_id=%s span_id=%s correlation_id=%s",
            sink_name,
            operation,
            event_id,
            event_type,
            trace_id,
            span_id,
            correlation_id,
            exc_info=(type(error), error, error.__traceback__),
            extra={
                "telemetry_sink": sink_name,
                "telemetry_operation": operation,
                "event_id": event_id,
                "event_type": event_type,
                "trace_id": trace_id,
                "span_id": span_id,
                "correlation_id": correlation_id,
            },
        )
        self.metrics_store.increment(
            name="telemetry.sink.failures",
            attributes={
                "component_name": sink_name,
                "operation": operation,
                "outcome": "failed",
            },
        )
