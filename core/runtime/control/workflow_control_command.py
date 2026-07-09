from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any


class WorkflowControlCommand(str, Enum):
    """
    Canonical workflow control command types.
    """

    PAUSE = "pause"
    RESUME = "resume"
    CANCEL = "cancel"


@dataclass(frozen=True, slots=True)
class WorkflowControlRequest:
    """
    Immutable request to change cooperative workflow execution state.
    """

    execution_id: str
    command: WorkflowControlCommand
    reason: str | None = None
    requested_by: str | None = None
    metadata: dict[str, Any] | None = None
    requested_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        )
    )
