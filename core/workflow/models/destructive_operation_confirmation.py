from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DestructiveWorkflowOperation(StrEnum):
    UNREGISTER_WORKFLOW = "unregister_workflow"
    DELETE_COMPLETED_RUN = "delete_completed_run"
    CLEANUP_COMPLETED_RUNS = "cleanup_completed_runs"


@dataclass(frozen=True, slots=True)
class DestructiveOperationConfirmation:
    """Explicit caller acknowledgement for a destructive workflow operation."""

    operation: DestructiveWorkflowOperation
    target: str
    requested_by: str
    confirmed: bool

    def require(
        self,
        *,
        operation: DestructiveWorkflowOperation,
        target: str,
    ) -> None:
        if self.operation is not operation:
            raise ValueError(
                "Destructive operation confirmation does not match the requested "
                f"operation: expected {operation.value}, got {self.operation.value}."
            )
        if self.target != target:
            raise ValueError(
                "Destructive operation confirmation does not match the requested "
                f"target: expected {target!r}, got {self.target!r}."
            )
        if not self.requested_by.strip():
            raise ValueError("Destructive operation requested_by cannot be empty.")
        if not self.confirmed:
            raise PermissionError(
                f"Explicit confirmation is required for {operation.value}."
            )
