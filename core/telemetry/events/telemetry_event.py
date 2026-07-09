from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from core.telemetry.events.telemetry_exception_details import (
    TelemetryExceptionDetails,
)


class TelemetryEventLevel(str, Enum):
    """Generic telemetry event severity."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    """Canonical immutable telemetry event used across the platform."""

    event_type: str
    source: str
    event_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    level: TelemetryEventLevel = TelemetryEventLevel.INFO
    workflow_id: str | None = None
    execution_id: str | None = None
    runtime_id: str | None = None
    node_name: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    duration_seconds: float | None = None
    success: bool | None = None
    error_count: int = 0
    exception_details: TelemetryExceptionDetails | None = None
    tags: tuple[str, ...] = ()
    attributes: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "runtime_id": self.runtime_id,
            "node_name": self.node_name,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "error_count": self.error_count,
            "exception_details": (
                self.exception_details.to_dict()
                if self.exception_details is not None
                else None
            ),
            "tags": list(self.tags),
            "attributes": deepcopy(self.attributes),
            "payload": deepcopy(self.payload),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TelemetryEvent:
        timestamp_raw = data.get("timestamp")
        timestamp = (
            datetime.fromisoformat(str(timestamp_raw))
            if timestamp_raw
            else datetime.now(timezone.utc)
        )
        level_raw = data.get(
            "level",
            data.get("severity", TelemetryEventLevel.INFO.value),
        )
        attributes = deepcopy(data.get("attributes", {}))
        exception_raw = data.get("exception_details")
        exception_details = (
            TelemetryExceptionDetails.from_dict(exception_raw)
            if isinstance(exception_raw, dict)
            else None
        )

        return cls(
            event_id=str(data.get("event_id") or uuid4().hex),
            event_type=str(data["event_type"]),
            source=str(data["source"]),
            timestamp=timestamp,
            level=TelemetryEventLevel(str(level_raw)),
            workflow_id=data.get("workflow_id"),
            execution_id=data.get("execution_id"),
            runtime_id=data.get("runtime_id"),
            node_name=data.get("node_name"),
            correlation_id=data.get("correlation_id"),
            trace_id=_optional_text(data.get("trace_id", attributes.get("trace_id"))),
            span_id=_optional_text(data.get("span_id", attributes.get("span_id"))),
            parent_span_id=_optional_text(
                data.get("parent_span_id", attributes.get("parent_span_id"))
            ),
            duration_seconds=data.get("duration_seconds"),
            success=data.get("success"),
            error_count=int(data.get("error_count", 0)),
            exception_details=exception_details,
            tags=tuple(data.get("tags", ())),
            attributes=attributes,
            payload=deepcopy(data.get("payload", {})),
        )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
