from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class WorkflowControlCommand(StrEnum):
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
            UTC,
        )
    )
