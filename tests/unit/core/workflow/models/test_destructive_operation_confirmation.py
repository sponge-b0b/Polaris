from __future__ import annotations

import pytest

from core.workflow.models.destructive_operation_confirmation import (
    DestructiveOperationConfirmation,
    DestructiveWorkflowOperation,
)


def _confirmation(
    *,
    operation: DestructiveWorkflowOperation = (
        DestructiveWorkflowOperation.DELETE_COMPLETED_RUN
    ),
    target: str = "workflow:execution",
    requested_by: str = "test",
    confirmed: bool = True,
) -> DestructiveOperationConfirmation:
    return DestructiveOperationConfirmation(
        operation=operation,
        target=target,
        requested_by=requested_by,
        confirmed=confirmed,
    )


def test_confirmation_accepts_exact_operation_and_target() -> None:
    _confirmation().require(
        operation=DestructiveWorkflowOperation.DELETE_COMPLETED_RUN,
        target="workflow:execution",
    )


def test_confirmation_rejects_unconfirmed_operation() -> None:
    with pytest.raises(PermissionError, match="Explicit confirmation"):
        _confirmation(confirmed=False).require(
            operation=DestructiveWorkflowOperation.DELETE_COMPLETED_RUN,
            target="workflow:execution",
        )


def test_confirmation_rejects_mismatched_operation_or_target() -> None:
    with pytest.raises(ValueError, match="requested operation"):
        _confirmation().require(
            operation=DestructiveWorkflowOperation.CLEANUP_COMPLETED_RUNS,
            target="workflow:execution",
        )

    with pytest.raises(ValueError, match="requested target"):
        _confirmation().require(
            operation=DestructiveWorkflowOperation.DELETE_COMPLETED_RUN,
            target="other:execution",
        )


def test_confirmation_rejects_empty_requester() -> None:
    with pytest.raises(ValueError, match="requested_by"):
        _confirmation(requested_by=" ").require(
            operation=DestructiveWorkflowOperation.DELETE_COMPLETED_RUN,
            target="workflow:execution",
        )
