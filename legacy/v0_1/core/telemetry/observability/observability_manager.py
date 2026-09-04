from __future__ import annotations

from typing import Any

from core.telemetry.collectors.telemetry_collector import TelemetryCollector
from core.telemetry.events.telemetry_event import (
    TelemetryEvent,
    TelemetryEventLevel,
)
from core.telemetry.metrics.metrics_store import MetricsStore
from core.telemetry.observability.domain_metrics import DomainMetricsRecorder
from core.telemetry.sinks.telemetry_sink import TelemetrySink
from core.telemetry.tracing.trace_context import TraceContext


class ObservabilityManager:
    """
    High-level observability coordinator.

    Coordinates:
    - telemetry event collection
    - sink fan-out
    - metrics recording
    - trace context creation

    This remains platform-generic and does not contain runtime,
    workflow, or business logic.
    """

    def __init__(
        self,
        collector: TelemetryCollector | None = None,
        metrics_store: MetricsStore | None = None,
        enable_domain_metrics: bool = True,
        domain_metrics_recorder: DomainMetricsRecorder | None = None,
    ) -> None:
        self.metrics_store = metrics_store or (
            collector.metrics_store if collector is not None else MetricsStore()
        )
        self.collector = collector or TelemetryCollector(
            metrics_store=self.metrics_store,
        )
        self.collector.metrics_store = self.metrics_store
        self.enable_domain_metrics = enable_domain_metrics
        self.domain_metrics_recorder = (
            domain_metrics_recorder or DomainMetricsRecorder()
        )

    # ========================================================
    # SINKS
    # ========================================================

    def add_sink(
        self,
        sink: TelemetrySink,
    ) -> None:
        self.collector.add_sink(
            sink,
        )

    def add_sinks(
        self,
        sinks: list[TelemetrySink],
    ) -> None:
        self.collector.add_sinks(
            sinks,
        )

    # ========================================================
    # LIFECYCLE
    # ========================================================

    def force_flush(
        self,
    ) -> None:
        self.collector.force_flush()

    def shutdown(
        self,
    ) -> None:
        self.collector.shutdown()

    # ========================================================
    # EVENTS
    # ========================================================

    async def emit(
        self,
        event: TelemetryEvent,
    ) -> None:
        await self.collector.emit(
            event,
        )

        self._record_event_metrics(
            event,
        )

    async def info(
        self,
        event_type: str,
        source: str,
        payload: dict[str, Any] | None = None,
        attributes: dict[str, Any] | None = None,
        trace_context: TraceContext | None = None,
    ) -> None:
        await self.emit(
            self._event(
                event_type=event_type,
                source=source,
                level=TelemetryEventLevel.INFO,
                payload=payload,
                attributes=attributes,
                trace_context=trace_context,
            )
        )

    async def warning(
        self,
        event_type: str,
        source: str,
        payload: dict[str, Any] | None = None,
        attributes: dict[str, Any] | None = None,
        trace_context: TraceContext | None = None,
    ) -> None:
        await self.emit(
            self._event(
                event_type=event_type,
                source=source,
                level=TelemetryEventLevel.WARNING,
                payload=payload,
                attributes=attributes,
                trace_context=trace_context,
            )
        )

    async def error(
        self,
        event_type: str,
        source: str,
        payload: dict[str, Any] | None = None,
        attributes: dict[str, Any] | None = None,
        trace_context: TraceContext | None = None,
        error_count: int = 1,
    ) -> None:
        await self.emit(
            self._event(
                event_type=event_type,
                source=source,
                level=TelemetryEventLevel.ERROR,
                payload=payload,
                attributes=attributes,
                trace_context=trace_context,
                success=False,
                error_count=error_count,
            )
        )

    # ========================================================
    # TRACING
    # ========================================================

    def create_trace_context(
        self,
        workflow_id: str | None = None,
        execution_id: str | None = None,
        runtime_id: str | None = None,
        node_name: str | None = None,
        correlation_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TraceContext:
        return TraceContext(
            workflow_id=workflow_id,
            execution_id=execution_id,
            runtime_id=runtime_id,
            node_name=node_name,
            correlation_id=correlation_id,
            attributes=dict(attributes or {}),
        )

    # ========================================================
    # METRICS
    # ========================================================

    def increment(
        self,
        name: str,
        value: float = 1.0,
        tags: tuple[str, ...] = (),
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self.metrics_store.increment(
            name=name,
            value=value,
            tags=tags,
            attributes=attributes,
        )

    def gauge(
        self,
        name: str,
        value: float,
        tags: tuple[str, ...] = (),
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self.metrics_store.gauge(
            name=name,
            value=value,
            tags=tags,
            attributes=attributes,
        )

    def observe(
        self,
        name: str,
        value: float,
        tags: tuple[str, ...] = (),
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self.metrics_store.observe(
            name=name,
            value=value,
            tags=tags,
            attributes=attributes,
        )

    # ========================================================
    # INSPECTION
    # ========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "collector": self.collector.to_dict(),
            "metrics": self.metrics_store.to_dict(),
        }

    # ========================================================
    # INTERNALS
    # ========================================================

    def _event(
        self,
        event_type: str,
        source: str,
        level: TelemetryEventLevel,
        payload: dict[str, Any] | None = None,
        attributes: dict[str, Any] | None = None,
        trace_context: TraceContext | None = None,
        success: bool | None = None,
        error_count: int = 0,
    ) -> TelemetryEvent:
        return TelemetryEvent(
            event_type=event_type,
            source=source,
            level=level,
            workflow_id=(
                trace_context.workflow_id if trace_context is not None else None
            ),
            execution_id=(
                trace_context.execution_id if trace_context is not None else None
            ),
            runtime_id=(
                trace_context.runtime_id if trace_context is not None else None
            ),
            node_name=(trace_context.node_name if trace_context is not None else None),
            correlation_id=(
                trace_context.correlation_id if trace_context is not None else None
            ),
            trace_id=(trace_context.trace_id if trace_context is not None else None),
            span_id=(trace_context.span_id if trace_context is not None else None),
            parent_span_id=(
                trace_context.parent_span_id if trace_context is not None else None
            ),
            success=success,
            error_count=error_count,
            attributes={
                **dict(attributes or {}),
                **(trace_context.attributes if trace_context is not None else {}),
                **(
                    trace_context.telemetry_attributes()
                    if trace_context is not None
                    else {}
                ),
            },
            payload=dict(payload or {}),
        )

    def _record_event_metrics(
        self,
        event: TelemetryEvent,
    ) -> None:
        tags = (
            event.source,
            event.level.value,
        )

        self.metrics_store.increment(
            name="telemetry.events.total",
            tags=tags,
            attributes={
                "event_type": event.event_type,
            },
        )

        if event.error_count > 0 or event.success is False:
            self.metrics_store.increment(
                name="telemetry.events.errors",
                tags=tags,
                attributes={
                    "event_type": event.event_type,
                },
            )

        if event.duration_seconds is not None:
            self.metrics_store.observe(
                name="telemetry.event.duration_seconds",
                value=event.duration_seconds,
                tags=tags,
                attributes={
                    "event_type": event.event_type,
                },
            )

        if self.enable_domain_metrics:
            self.domain_metrics_recorder.record(
                event=event,
                metrics_store=self.metrics_store,
            )
