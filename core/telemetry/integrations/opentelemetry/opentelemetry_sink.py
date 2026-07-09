from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Iterator

from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.id_generator import IdGenerator
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from opentelemetry.trace import NonRecordingSpan
from opentelemetry.trace import Span
from opentelemetry.trace import SpanContext
from opentelemetry.trace import Status
from opentelemetry.trace import StatusCode
from opentelemetry.trace import TraceFlags
from opentelemetry.trace import set_span_in_context

from core.telemetry.events.telemetry_event import (
    TelemetryEvent,
    TelemetryEventLevel,
)
from core.telemetry.integrations.opentelemetry.opentelemetry_config import (
    OpenTelemetryConfig,
)
from core.telemetry.sanitization import sanitize_telemetry_mapping
from core.telemetry.tracing.operation_lifecycle import (
    is_terminal_operation_event,
)
from core.telemetry.tracing.operation_lifecycle import resolve_operation_name
from core.telemetry.sinks.telemetry_sink import (
    TelemetrySink,
)

_MAX_OPEN_SPANS = 4096
_MAX_CLOSED_SPAN_KEYS = 4096


@dataclass(slots=True)
class _OpenOperationSpan:
    span: Span
    started_at_ns: int


class OpenTelemetrySink(TelemetrySink):
    """Project canonical operation spans into OpenTelemetry."""

    def __init__(
        self,
        config: OpenTelemetryConfig,
        span_exporter: SpanExporter | None = None,
    ) -> None:
        self.config = config
        self._shutdown = False
        self._max_open_spans = _MAX_OPEN_SPANS
        self._open_spans: OrderedDict[tuple[str, str], _OpenOperationSpan] = (
            OrderedDict()
        )
        self._closed_span_keys: OrderedDict[tuple[str, str], None] = OrderedDict()

        resource = Resource.create(
            {
                "service.name": config.service_name,
                "service.version": config.service_version,
                "deployment.environment": config.environment,
            }
        )

        self._id_generator = _CanonicalIdGenerator()
        provider = TracerProvider(
            resource=resource,
            id_generator=self._id_generator,
        )

        if span_exporter is None:
            otlp_exporter = OTLPSpanExporter(
                endpoint=config.otlp_endpoint,
                insecure=config.insecure,
            )
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        else:
            provider.add_span_processor(SimpleSpanProcessor(span_exporter))

        if config.enable_console_export:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        self.provider = provider
        self.tracer = provider.get_tracer(
            config.service_name,
            config.service_version,
        )

    async def emit(
        self,
        event: TelemetryEvent,
    ) -> None:
        key = _canonical_span_key(
            trace_id=event.trace_id,
            span_id=event.span_id,
        )
        if key is None or key in self._closed_span_keys or self._shutdown:
            return

        operation_span = self._open_spans.get(key)
        if operation_span is None:
            operation_span = self._start_operation_span(event)
            if operation_span is None:
                return
            self._open_spans[key] = operation_span
            self._evict_oldest_incomplete_span_if_needed(
                current_key=key,
                timestamp_ns=_timestamp_ns(event.timestamp),
            )
        else:
            self._open_spans.move_to_end(key)

        self._populate_span(
            span=operation_span.span,
            event=event,
        )

        if is_terminal_operation_event(event):
            self._finish_span(
                key=key,
                end_time_ns=_timestamp_ns(event.timestamp),
            )

    def _start_operation_span(
        self,
        event: TelemetryEvent,
    ) -> _OpenOperationSpan | None:
        trace_id = _parse_otel_id(event.trace_id, expected_length=32)
        span_id = _parse_otel_id(event.span_id, expected_length=16)
        if trace_id is None or span_id is None:
            return None

        started_at_ns = _operation_started_at_ns(event)
        with self._id_generator.use_ids(trace_id=trace_id, span_id=span_id):
            span = self.tracer.start_span(
                resolve_operation_name(event),
                context=_canonical_parent_context(event),
                start_time=started_at_ns,
            )
        return _OpenOperationSpan(
            span=span,
            started_at_ns=started_at_ns,
        )

    def _populate_span(
        self,
        *,
        span: Span,
        event: TelemetryEvent,
    ) -> None:
        span.set_attribute("telemetry.source", event.source)
        span.set_attribute("telemetry.level", event.level.value)
        span.set_attribute("telemetry.event_count", _next_event_count(span))

        self._set_execution_attributes(span=span, event=event)
        self._set_trace_attributes(span=span, event=event)
        self._set_provider_attributes(span=span, event=event)

        if event.duration_seconds is not None:
            span.set_attribute("duration.seconds", event.duration_seconds)
        if event.success is not None:
            span.set_attribute("success", event.success)
        span.set_attribute("error.count", event.error_count)

        self._set_payload_attributes(span=span, payload=event.payload)
        self._set_payload_attributes(
            span=span,
            payload=event.attributes,
            prefix="attr.",
        )
        self._record_telemetry_event(span=span, event=event)
        self._record_exception_event(span=span, event=event)

        if _is_failed_operation(event):
            description = (
                event.exception_details.message
                if event.exception_details is not None
                else event.event_type
            )
            span.set_status(
                Status(
                    status_code=StatusCode.ERROR,
                    description=description,
                )
            )

    def _record_telemetry_event(
        self,
        *,
        span: Span,
        event: TelemetryEvent,
    ) -> None:
        attributes: dict[str, Any] = {
            "telemetry.event_id": event.event_id,
            "telemetry.source": event.source,
            "telemetry.level": event.level.value,
            "telemetry.error_count": event.error_count,
        }
        if event.success is not None:
            attributes["telemetry.success"] = event.success
        if event.duration_seconds is not None:
            attributes["telemetry.duration_seconds"] = event.duration_seconds
        if event.tags:
            attributes["telemetry.tags"] = event.tags

        span.add_event(
            event.event_type,
            attributes=attributes,
            timestamp=_timestamp_ns(event.timestamp),
        )

    def _set_execution_attributes(
        self,
        *,
        span: Span,
        event: TelemetryEvent,
    ) -> None:
        execution_attributes = (
            ("workflow.id", event.workflow_id),
            ("execution.id", event.execution_id),
            ("runtime.id", event.runtime_id),
            ("node.name", event.node_name),
            ("correlation.id", event.correlation_id),
        )
        for attribute_name, value in execution_attributes:
            if value is not None:
                span.set_attribute(attribute_name, value)

    def _record_exception_event(
        self,
        *,
        span: Span,
        event: TelemetryEvent,
    ) -> None:
        details = event.exception_details
        if details is None:
            return

        span.add_event(
            "exception",
            attributes={
                "exception.type": details.exception_type,
                "exception.message": details.message,
                "exception.stacktrace": details.stack_trace,
            },
            timestamp=_timestamp_ns(event.timestamp),
        )

    def _finish_span(
        self,
        *,
        key: tuple[str, str],
        end_time_ns: int,
    ) -> None:
        operation_span = self._open_spans.pop(key, None)
        if operation_span is None:
            return
        operation_span.span.end(
            end_time=max(end_time_ns, operation_span.started_at_ns),
        )
        self._remember_closed_span(key)

    def _evict_oldest_incomplete_span_if_needed(
        self,
        *,
        current_key: tuple[str, str],
        timestamp_ns: int,
    ) -> None:
        if len(self._open_spans) <= self._max_open_spans:
            return

        key, operation_span = self._open_spans.popitem(last=False)
        operation_span.span.set_attribute("telemetry.lifecycle.incomplete", True)
        operation_span.span.set_attribute("telemetry.lifecycle.evicted", True)
        operation_span.span.add_event(
            "telemetry.lifecycle.evicted",
            attributes={"telemetry.reason": "open_span_limit_exceeded"},
            timestamp=timestamp_ns,
        )
        operation_span.span.end(
            end_time=max(timestamp_ns, operation_span.started_at_ns),
        )
        self._remember_closed_span(key)
        if key == current_key:
            self._open_spans.pop(current_key, None)

    def _remember_closed_span(
        self,
        key: tuple[str, str],
    ) -> None:
        self._closed_span_keys[key] = None
        self._closed_span_keys.move_to_end(key)
        if len(self._closed_span_keys) > _MAX_CLOSED_SPAN_KEYS:
            self._closed_span_keys.popitem(last=False)

    def _finish_incomplete_spans(self) -> None:
        ended_at_ns = _timestamp_ns(datetime.now(timezone.utc))
        while self._open_spans:
            key, operation_span = self._open_spans.popitem(last=False)
            operation_span.span.set_attribute("telemetry.lifecycle.incomplete", True)
            operation_span.span.add_event(
                "telemetry.lifecycle.incomplete",
                attributes={"telemetry.reason": "sink_shutdown"},
                timestamp=ended_at_ns,
            )
            operation_span.span.end(
                end_time=max(ended_at_ns, operation_span.started_at_ns),
            )
            self._remember_closed_span(key)

    def shutdown(
        self,
    ) -> None:
        if self._shutdown:
            return

        self._finish_incomplete_spans()
        self.provider.shutdown()
        self._shutdown = True

    def force_flush(
        self,
    ) -> None:
        if self._shutdown:
            return
        self.provider.force_flush()

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "sink": self.__class__.__name__,
            "shutdown": self._shutdown,
            "open_span_count": len(self._open_spans),
            "config": self.config.to_dict(),
        }

    def _set_trace_attributes(
        self,
        span: Span,
        event: TelemetryEvent,
    ) -> None:
        if event.trace_id is not None:
            span.set_attribute("trace.id", event.trace_id)
        if event.span_id is not None:
            span.set_attribute("span.id", event.span_id)
        if event.parent_span_id is not None:
            span.set_attribute("parent_span.id", event.parent_span_id)

    def _set_provider_attributes(
        self,
        span: Span,
        event: TelemetryEvent,
    ) -> None:
        provider_name = event.attributes.get(
            "provider_name",
            event.payload.get("provider_name"),
        )
        operation = event.attributes.get(
            "operation",
            event.payload.get("operation"),
        )

        if isinstance(provider_name, str) and provider_name:
            span.set_attribute("provider.name", provider_name)
        if isinstance(operation, str) and operation:
            span.set_attribute("provider.operation", operation)

    def _set_payload_attributes(
        self,
        span: Span,
        payload: dict[str, Any],
        prefix: str = "",
    ) -> None:
        for key, value in sanitize_telemetry_mapping(payload).items():
            attribute_name = f"{prefix}{key}"
            if isinstance(value, (str, bool, int, float)):
                span.set_attribute(attribute_name, value)
            elif value is not None:
                span.set_attribute(attribute_name, str(value))


def _canonical_parent_context(event: TelemetryEvent) -> Context | None:
    trace_id = _parse_otel_id(event.trace_id, expected_length=32)
    parent_span_id = _parse_otel_id(event.parent_span_id, expected_length=16)
    if trace_id is None or parent_span_id is None:
        return None

    return set_span_in_context(
        NonRecordingSpan(
            SpanContext(
                trace_id=trace_id,
                span_id=parent_span_id,
                is_remote=False,
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
            )
        )
    )


def _canonical_span_key(
    *,
    trace_id: str | None,
    span_id: str | None,
) -> tuple[str, str] | None:
    if (
        _parse_otel_id(trace_id, expected_length=32) is None
        or _parse_otel_id(span_id, expected_length=16) is None
    ):
        return None
    assert trace_id is not None
    assert span_id is not None
    return trace_id, span_id


def _is_failed_operation(event: TelemetryEvent) -> bool:
    if event.level in (TelemetryEventLevel.ERROR, TelemetryEventLevel.CRITICAL):
        return True
    if event.exception_details is not None:
        return True
    return event.success is False and not event.event_type.endswith(".cancelled")


def _operation_started_at_ns(event: TelemetryEvent) -> int:
    timestamp_ns = _timestamp_ns(event.timestamp)
    if event.duration_seconds is None:
        return timestamp_ns
    duration_ns = max(0, int(event.duration_seconds * 1_000_000_000))
    return max(0, timestamp_ns - duration_ns)


def _timestamp_ns(value: datetime) -> int:
    return int(value.timestamp() * 1_000_000_000)


def _next_event_count(span: Span) -> int:
    attributes = getattr(span, "attributes", None)
    if attributes is None:
        return 1
    current = attributes.get("telemetry.event_count", 0)
    return int(current) + 1 if isinstance(current, int) else 1


class _CanonicalIdGenerator(IdGenerator):
    """Use Polaris's canonical trace and operation-span identifiers externally."""

    def __init__(self) -> None:
        self._random = RandomIdGenerator()
        self._trace_id: ContextVar[int | None] = ContextVar(
            "polaris_otel_trace_id",
            default=None,
        )
        self._span_id: ContextVar[int | None] = ContextVar(
            "polaris_otel_span_id",
            default=None,
        )

    def generate_trace_id(self) -> int:
        return self._trace_id.get() or self._random.generate_trace_id()

    def generate_span_id(self) -> int:
        return self._span_id.get() or self._random.generate_span_id()

    @contextmanager
    def use_ids(
        self,
        *,
        trace_id: int,
        span_id: int,
    ) -> Iterator[None]:
        trace_token = self._trace_id.set(trace_id)
        span_token = self._span_id.set(span_id)
        try:
            yield
        finally:
            self._span_id.reset(span_token)
            self._trace_id.reset(trace_token)


def _parse_otel_id(
    value: str | None,
    *,
    expected_length: int,
) -> int | None:
    if value is None or len(value) != expected_length:
        return None

    try:
        parsed = int(value, 16)
    except ValueError:
        return None

    return parsed or None
