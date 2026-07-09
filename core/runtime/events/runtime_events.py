from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from datetime import datetime
from datetime import timezone

from enum import Enum

from typing import Any
from typing import Dict


# ============================================================
# RUNTIME EVENT TYPES
# ============================================================


class RuntimeEventType(str, Enum):
    """
    Canonical runtime event taxonomy.

    PURPOSE
    ============================================================
    Standardized event types across:
    - orchestration
    - execution
    - checkpoints
    - replay
    - telemetry
    - observability
    - auditing
    """

    # ========================================================
    # WORKFLOW EVENTS
    # ========================================================

    WORKFLOW_STARTED = "workflow_started"

    WORKFLOW_COMPLETED = "workflow_completed"

    WORKFLOW_FAILED = "workflow_failed"

    WORKFLOW_CANCELLED = "workflow_cancelled"

    WORKFLOW_PAUSED = "workflow_paused"

    WORKFLOW_RESUMED = "workflow_resumed"

    # ========================================================
    # WORKFLOW CONTROL / EXTERNAL PROGRESS EVENTS
    # ========================================================

    WORKFLOW_STATE_CHANGED = "runtime.workflow.state_changed"

    WORKFLOW_PROGRESS_STARTED = "runtime.workflow.started"

    WORKFLOW_PROGRESS_RUNNING = "runtime.workflow.running"

    WORKFLOW_PROGRESS_PAUSING = "runtime.workflow.pausing"

    WORKFLOW_PROGRESS_PAUSED = "runtime.workflow.paused"

    WORKFLOW_PROGRESS_RESUMING = "runtime.workflow.resuming"

    WORKFLOW_PROGRESS_RESUMED = "runtime.workflow.resumed"

    WORKFLOW_PROGRESS_CANCELLING = "runtime.workflow.cancelling"

    WORKFLOW_PROGRESS_CANCELLED = "runtime.workflow.cancelled"

    WORKFLOW_PROGRESS_COMPLETED = "runtime.workflow.completed"

    WORKFLOW_PROGRESS_FAILED = "runtime.workflow.failed"

    # ========================================================
    # EXECUTION EVENTS
    # ========================================================

    EXECUTION_STARTED = "execution_started"

    EXECUTION_COMPLETED = "execution_completed"

    EXECUTION_FAILED = "execution_failed"

    EXECUTION_STOPPED = "execution_stopped"

    # ========================================================
    # WAVE EVENTS
    # ========================================================

    WAVE_STARTED = "wave_started"

    WAVE_COMPLETED = "wave_completed"

    WAVE_FAILED = "wave_failed"

    # ========================================================
    # WAVE EXTERNAL PROGRESS EVENTS
    # ========================================================

    WAVE_PROGRESS_STARTED = "runtime.workflow.wave.started"

    WAVE_PROGRESS_COMPLETED = "runtime.workflow.wave.completed"

    WAVE_PROGRESS_FAILED = "runtime.workflow.wave.failed"

    # ========================================================
    # NODE EVENTS
    # ========================================================

    NODE_STARTED = "node_started"

    NODE_COMPLETED = "node_completed"

    NODE_FAILED = "node_failed"

    NODE_SKIPPED = "node_skipped"

    NODE_RETRYING = "node_retrying"

    # ========================================================
    # NODE EXTERNAL PROGRESS EVENTS
    # ========================================================

    NODE_PROGRESS_STARTED = "runtime.node.started"

    NODE_PROGRESS_RUNNING = "runtime.node.running"

    NODE_PROGRESS_COMPLETED = "runtime.node.completed"

    NODE_PROGRESS_SKIPPED = "runtime.node.skipped"

    NODE_PROGRESS_FAILED = "runtime.node.failed"

    # ========================================================
    # CHECKPOINT EVENTS
    # ========================================================

    CHECKPOINT_CREATED = "checkpoint_created"

    CHECKPOINT_RESTORED = "checkpoint_restored"

    CHECKPOINT_FAILED = "checkpoint_failed"

    # ========================================================
    # REPLAY EVENTS
    # ========================================================

    REPLAY_STARTED = "replay_started"

    REPLAY_COMPLETED = "replay_completed"

    REPLAY_FAILED = "replay_failed"

    # ========================================================
    # STATE EVENTS
    # ========================================================

    STATE_UPDATED = "state_updated"

    STATE_PERSISTED = "state_persisted"

    # ========================================================
    # SYSTEM EVENTS
    # ========================================================

    SYSTEM_WARNING = "system_warning"

    SYSTEM_ERROR = "system_error"

    SYSTEM_HEALTHCHECK = "system_healthcheck"

    # ========================================================
    # TELEMETRY EVENTS
    # ========================================================

    METRIC_RECORDED = "metric_recorded"

    TRACE_RECORDED = "trace_recorded"

    AUDIT_RECORDED = "audit_recorded"


# ============================================================
# RUNTIME EVENT
# ============================================================


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    """
    Canonical immutable runtime event.

    PURPOSE
    ============================================================
    Standard event envelope used across:
    - RuntimeEngine
    - WorkflowEngine
    - EventBus
    - ReplayEngine
    - CheckpointManager
    - telemetry systems
    - observability systems

    DESIGN PRINCIPLES
    ============================================================
    - immutable
    - serializable
    - replay-safe
    - infrastructure-level only
    """

    # ========================================================
    # CORE EVENT INFO
    # ========================================================

    event_type: RuntimeEventType

    # ========================================================
    # EXECUTION IDs
    # ========================================================

    execution_id: str

    workflow_id: str

    runtime_id: str | None = None

    # ========================================================
    # TIMING
    # ========================================================

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # ========================================================
    # EXECUTION LOCATION
    # ========================================================

    node_name: str | None = None

    wave_index: int | None = None

    # ========================================================
    # PAYLOAD
    # ========================================================

    payload: Dict[str, Any] = field(
        default_factory=dict,
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict,
    )

    # ========================================================
    # SERIALIZATION
    # ========================================================

    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {
            "event_type": self.event_type.value,
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "runtime_id": self.runtime_id,
            "timestamp": self.timestamp.isoformat(),
            "node_name": self.node_name,
            "wave_index": self.wave_index,
            "payload": dict(self.payload),
            "metadata": dict(self.metadata),
        }

    # ========================================================
    # HELPERS
    # ========================================================

    @property
    def is_error(
        self,
    ) -> bool:

        return self.event_type in {
            RuntimeEventType.WORKFLOW_FAILED,
            RuntimeEventType.WORKFLOW_PROGRESS_FAILED,
            RuntimeEventType.EXECUTION_FAILED,
            RuntimeEventType.WAVE_FAILED,
            RuntimeEventType.WAVE_PROGRESS_FAILED,
            RuntimeEventType.NODE_FAILED,
            RuntimeEventType.NODE_PROGRESS_FAILED,
            RuntimeEventType.CHECKPOINT_FAILED,
            RuntimeEventType.REPLAY_FAILED,
            RuntimeEventType.SYSTEM_ERROR,
        }

    @property
    def is_terminal(
        self,
    ) -> bool:

        return self.event_type in {
            RuntimeEventType.WORKFLOW_COMPLETED,
            RuntimeEventType.WORKFLOW_FAILED,
            RuntimeEventType.WORKFLOW_CANCELLED,
            RuntimeEventType.WORKFLOW_PROGRESS_COMPLETED,
            RuntimeEventType.WORKFLOW_PROGRESS_FAILED,
            RuntimeEventType.WORKFLOW_PROGRESS_CANCELLED,
            RuntimeEventType.EXECUTION_COMPLETED,
            RuntimeEventType.EXECUTION_FAILED,
            RuntimeEventType.REPLAY_COMPLETED,
            RuntimeEventType.REPLAY_FAILED,
        }
