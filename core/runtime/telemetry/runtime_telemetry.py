from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any


class RuntimeTelemetryEventType(str, Enum):
    """
    Runtime-specific telemetry event taxonomy.
    """

    WORKFLOW_STARTED = "runtime.workflow.started"
    WORKFLOW_COMPLETED = "runtime.workflow.completed"
    WORKFLOW_FAILED = "runtime.workflow.failed"

    WAVE_STARTED = "runtime.wave.started"
    WAVE_COMPLETED = "runtime.wave.completed"
    WAVE_FAILED = "runtime.wave.failed"

    NODE_STARTED = "runtime.node.started"
    NODE_COMPLETED = "runtime.node.completed"
    NODE_FAILED = "runtime.node.failed"
    NODE_SKIPPED = "runtime.node.skipped"

    ARTIFACT_PERSISTED = "runtime.artifact.persisted"
    ARTIFACT_FAILED = "runtime.artifact.failed"

    CHECKPOINT_CREATED = "runtime.checkpoint.created"
    CHECKPOINT_RESTORED = "runtime.checkpoint.restored"
    CHECKPOINT_FAILED = "runtime.checkpoint.failed"

    REPLAY_STARTED = "runtime.replay.started"
    REPLAY_COMPLETED = "runtime.replay.completed"
    REPLAY_FAILED = "runtime.replay.failed"

    RUNTIME_EVENT = "runtime.event"

    WORKFLOW_CONTROL_STATE_CHANGED = "workflow_control.state_changed"
    WORKFLOW_CONTROL_PAUSE_REQUESTED = "workflow_control.pause_requested"
    WORKFLOW_CONTROL_PAUSED = "workflow_control.paused"
    WORKFLOW_CONTROL_RESUME_REQUESTED = "workflow_control.resume_requested"
    WORKFLOW_CONTROL_RESUMED = "workflow_control.resumed"
    WORKFLOW_CONTROL_CANCEL_REQUESTED = "workflow_control.cancel_requested"
    WORKFLOW_CONTROL_CANCELLED = "workflow_control.cancelled"

    WORKFLOW_PROGRESS_STARTED = "workflow_progress.workflow_started"
    WORKFLOW_PROGRESS_RUNNING = "workflow_progress.workflow_running"
    WORKFLOW_PROGRESS_COMPLETED = "workflow_progress.workflow_completed"
    WORKFLOW_PROGRESS_FAILED = "workflow_progress.workflow_failed"
    WORKFLOW_PROGRESS_CANCELLED = "workflow_progress.workflow_cancelled"

    WAVE_PROGRESS_STARTED = "workflow_progress.wave_started"
    WAVE_PROGRESS_COMPLETED = "workflow_progress.wave_completed"
    WAVE_PROGRESS_FAILED = "workflow_progress.wave_failed"

    NODE_PROGRESS_STARTED = "workflow_progress.node_started"
    NODE_PROGRESS_RUNNING = "workflow_progress.node_running"
    NODE_PROGRESS_COMPLETED = "workflow_progress.node_completed"
    NODE_PROGRESS_SKIPPED = "workflow_progress.node_skipped"
    NODE_PROGRESS_FAILED = "workflow_progress.node_failed"


@dataclass(frozen=True, slots=True)
class RuntimeTelemetryEvent:
    """
    Immutable runtime telemetry event.
    """

    event_type: RuntimeTelemetryEventType

    workflow_id: str

    execution_id: str

    runtime_id: str | None = None

    node_name: str | None = None

    wave_index: int | None = None

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    duration_seconds: float | None = None

    success: bool | None = None

    error_count: int = 0

    tags: tuple[str, ...] = ()

    payload: dict[str, Any] = field(
        default_factory=dict,
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "runtime_id": self.runtime_id,
            "node_name": self.node_name,
            "wave_index": self.wave_index,
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "error_count": self.error_count,
            "tags": list(self.tags),
            "payload": deepcopy(self.payload),
        }


class RuntimeTelemetrySink:
    """
    Runtime telemetry sink contract.
    """

    async def emit(
        self,
        event: RuntimeTelemetryEvent,
    ) -> None:
        raise NotImplementedError


class InMemoryRuntimeTelemetrySink(RuntimeTelemetrySink):
    """
    Simple in-memory sink for tests and local debugging.
    """

    def __init__(
        self,
    ) -> None:
        self.events: list[RuntimeTelemetryEvent] = []

    async def emit(
        self,
        event: RuntimeTelemetryEvent,
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
            "event_count": len(self.events),
            "events": [event.to_dict() for event in self.events],
        }


class RuntimeTelemetry:
    """
    Runtime telemetry dispatcher.
    """

    def __init__(
        self,
        sinks: list[RuntimeTelemetrySink] | None = None,
        fail_fast: bool = False,
    ) -> None:
        self.sinks = list(
            sinks or [],
        )
        self.fail_fast = fail_fast

    def register_sink(
        self,
        sink: RuntimeTelemetrySink,
    ) -> None:
        self.sinks.append(
            sink,
        )

    def add_sink(
        self,
        sink: RuntimeTelemetrySink,
    ) -> None:
        """
        Alias for register_sink().
        """

        self.register_sink(
            sink,
        )

    def register_many(
        self,
        sinks: list[RuntimeTelemetrySink],
    ) -> None:
        for sink in sinks:
            self.register_sink(
                sink,
            )

    def clear_sinks(
        self,
    ) -> None:
        self.sinks.clear()

    async def emit(
        self,
        event: RuntimeTelemetryEvent,
    ) -> None:
        for sink in self.sinks:
            try:
                await sink.emit(
                    event,
                )
            except Exception:
                if self.fail_fast:
                    raise

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "sink_count": len(self.sinks),
            "sinks": [sink.__class__.__name__ for sink in self.sinks],
            "fail_fast": self.fail_fast,
        }
