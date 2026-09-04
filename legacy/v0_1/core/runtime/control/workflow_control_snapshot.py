from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.runtime.control.workflow_control_state import WorkflowControlState


@dataclass(frozen=True, slots=True)
class WorkflowControlSnapshot:
    """
    Immutable point-in-time view of cooperative workflow control state.
    """

    execution_id: str
    state: WorkflowControlState
    reason: str | None = None
    requested_by: str | None = None
    metadata: dict[str, Any] = field(
        default_factory=dict,
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(
            UTC,
        )
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "state": self.state.value,
            "reason": self.reason,
            "requested_by": self.requested_by,
            "metadata": deepcopy(
                self.metadata,
            ),
            "updated_at": self.updated_at.isoformat(),
        }
