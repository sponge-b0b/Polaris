from __future__ import annotations

import logging
from typing import Any

from core.telemetry.events.telemetry_event import (
    TelemetryEvent,
    TelemetryEventLevel,
)
from core.telemetry.sanitization import sanitize_telemetry_mapping
from core.telemetry.sinks.telemetry_sink import TelemetrySink


class TelemetryLogger(TelemetrySink):
    """
    Logging sink for generic TelemetryEvent objects.

    Converts platform telemetry events into standard Python log records.

    This is useful for:
    - local debugging
    - runtime audit logs
    - structured logging adapters
    - forwarding to logging infrastructure
    """

    def __init__(
        self,
        logger_name: str = "core.telemetry",
        include_payload: bool = True,
        include_attributes: bool = True,
    ) -> None:
        self.logger_name = logger_name
        self.include_payload = include_payload
        self.include_attributes = include_attributes

        self.logger = logging.getLogger(
            logger_name,
        )

    async def emit(
        self,
        event: TelemetryEvent,
    ) -> None:
        level = self._logging_level(
            event.level,
        )
        structured, stack_trace = self._build_extra(
            event,
        )

        self.logger.log(
            level,
            self._message(
                event,
                stack_trace=stack_trace,
            ),
            extra={
                **structured,
                "telemetry": structured,
            },
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "sink": self.__class__.__name__,
            "logger_name": self.logger_name,
            "include_payload": self.include_payload,
            "include_attributes": self.include_attributes,
        }

    def _message(
        self,
        event: TelemetryEvent,
        *,
        stack_trace: str | None,
    ) -> str:
        parts = [
            f"[{event.source}]",
            event.event_type,
            f"event_id={event.event_id}",
        ]

        if event.trace_id:
            parts.append(
                f"trace_id={event.trace_id}",
            )

        if event.span_id:
            parts.append(
                f"span_id={event.span_id}",
            )

        if event.correlation_id:
            parts.append(
                f"correlation_id={event.correlation_id}",
            )

        if event.workflow_id:
            parts.append(
                f"workflow={event.workflow_id}",
            )

        if event.execution_id:
            parts.append(
                f"execution={event.execution_id}",
            )

        if event.node_name:
            parts.append(
                f"node={event.node_name}",
            )

        if event.success is not None:
            parts.append(
                f"success={event.success}",
            )

        if event.error_count:
            parts.append(
                f"errors={event.error_count}",
            )

        if event.duration_seconds is not None:
            parts.append(
                f"duration={event.duration_seconds:.6f}s",
            )

        message = " ".join(
            parts,
        )
        if stack_trace:
            return f"{message}\n{stack_trace}"
        return message

    def _build_extra(
        self,
        event: TelemetryEvent,
    ) -> tuple[dict[str, Any], str | None]:
        data: dict[str, Any] = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "source": event.source,
            "timestamp": event.timestamp.isoformat(),
            "severity": event.level.value,
            "level": event.level.value,
            "workflow_id": event.workflow_id,
            "execution_id": event.execution_id,
            "runtime_id": event.runtime_id,
            "node_name": event.node_name,
            "correlation_id": event.correlation_id,
            "trace_id": event.trace_id,
            "span_id": event.span_id,
            "parent_span_id": event.parent_span_id,
            "duration_seconds": event.duration_seconds,
            "success": event.success,
            "error_count": event.error_count,
            "tags": list(event.tags),
        }

        stack_trace: str | None = None
        if event.exception_details is not None:
            exception_details = sanitize_telemetry_mapping(
                event.exception_details.to_dict(),
            )
            stack_trace = str(
                exception_details.pop(
                    "stack_trace",
                    "",
                )
            )
            data["exception_details"] = exception_details

        if self.include_attributes:
            data["attributes"] = sanitize_telemetry_mapping(
                event.attributes,
            )

        if self.include_payload:
            data["payload"] = sanitize_telemetry_mapping(
                event.payload,
            )

        return data, stack_trace

    def _logging_level(
        self,
        level: TelemetryEventLevel,
    ) -> int:
        mapping = {
            TelemetryEventLevel.DEBUG: logging.DEBUG,
            TelemetryEventLevel.INFO: logging.INFO,
            TelemetryEventLevel.WARNING: logging.WARNING,
            TelemetryEventLevel.ERROR: logging.ERROR,
            TelemetryEventLevel.CRITICAL: logging.CRITICAL,
        }

        return mapping.get(
            level,
            logging.INFO,
        )
