from __future__ import annotations

from enum import StrEnum


class WorkflowControlState(StrEnum):
    """
    Canonical cooperative workflow control lifecycle state.
    """

    PENDING = "pending"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    RESUMING = "resuming"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
