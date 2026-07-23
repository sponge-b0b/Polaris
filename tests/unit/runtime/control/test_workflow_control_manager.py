from __future__ import annotations

import asyncio
from typing import Any

import pytest

from core.runtime.control import (
    WorkflowControlManager,
    WorkflowControlSnapshot,
    WorkflowControlState,
)


@pytest.mark.asyncio
async def test_unknown_execution_defaults_to_pending_snapshot() -> None:
    manager = WorkflowControlManager()

    snapshot = manager.get_snapshot(
        "execution-1",
    )

    assert isinstance(
        snapshot,
        WorkflowControlSnapshot,
    )
    assert snapshot.execution_id == "execution-1"
    assert snapshot.state is WorkflowControlState.PENDING
    assert snapshot.metadata == {}
    assert (
        manager.get_state(
            "execution-1",
        )
        is WorkflowControlState.PENDING
    )


@pytest.mark.asyncio
async def test_manager_tracks_basic_lifecycle_state_transitions() -> None:
    manager = WorkflowControlManager()

    await manager.initialize_execution(
        "execution-1",
        metadata={
            "workflow": "morning_report",
        },
    )
    assert (
        manager.get_state(
            "execution-1",
        )
        is WorkflowControlState.PENDING
    )

    await manager.mark_running(
        "execution-1",
        metadata={
            "wave_index": 1,
        },
    )
    assert (
        manager.get_state(
            "execution-1",
        )
        is WorkflowControlState.RUNNING
    )

    await manager.mark_completed(
        "execution-1",
    )
    snapshot = manager.get_snapshot(
        "execution-1",
    )

    assert snapshot.state is WorkflowControlState.COMPLETED
    assert snapshot.metadata == {
        "workflow": "morning_report",
        "wave_index": 1,
    }


@pytest.mark.asyncio
async def test_mark_failed_sets_failed_state_and_reason() -> None:
    manager = WorkflowControlManager()

    await manager.initialize_execution(
        "execution-1",
        metadata={
            "workflow": "morning_report",
        },
    )
    await manager.mark_failed(
        "execution-1",
        reason="node failed",
        metadata={
            "node_name": "technical_analysis",
        },
    )

    snapshot = manager.get_snapshot(
        "execution-1",
    )

    assert snapshot.state is WorkflowControlState.FAILED
    assert snapshot.reason == "node failed"
    assert snapshot.metadata == {
        "workflow": "morning_report",
        "node_name": "technical_analysis",
    }


@pytest.mark.asyncio
async def test_snapshot_metadata_is_defensively_copied() -> None:
    manager = WorkflowControlManager()
    source_metadata: dict[str, Any] = {
        "workflow": "morning_report",
        "nested": {
            "wave_index": 1,
        },
    }

    await manager.initialize_execution(
        "execution-1",
        metadata=source_metadata,
    )
    source_metadata["workflow"] = "mutated"
    source_metadata["nested"]["wave_index"] = 99

    snapshot = manager.get_snapshot(
        "execution-1",
    )
    snapshot.metadata["workflow"] = "mutated again"
    snapshot.metadata["nested"]["wave_index"] = 100

    assert manager.get_snapshot(
        "execution-1",
    ).metadata == {
        "workflow": "morning_report",
        "nested": {
            "wave_index": 1,
        },
    }


@pytest.mark.asyncio
async def test_empty_execution_id_is_rejected() -> None:
    manager = WorkflowControlManager()

    with pytest.raises(
        ValueError,
        match="execution_id cannot be empty",
    ):
        await manager.initialize_execution(
            "   ",
        )


@pytest.mark.asyncio
async def test_request_pause_marks_pausing_and_preserves_request_context() -> None:
    manager = WorkflowControlManager()

    await manager.mark_running(
        "execution-1",
        metadata={
            "workflow": "morning_report",
        },
    )
    await manager.request_pause(
        "execution-1",
        reason="operator requested pause",
        requested_by="cli",
        metadata={
            "safe_boundary": "before_wave_2",
        },
    )

    snapshot = manager.get_snapshot(
        "execution-1",
    )

    assert snapshot.state is WorkflowControlState.PAUSING
    assert snapshot.reason == "operator requested pause"
    assert snapshot.requested_by == "cli"
    assert snapshot.metadata == {
        "workflow": "morning_report",
        "safe_boundary": "before_wave_2",
    }
    assert (
        manager.should_pause(
            "execution-1",
        )
        is True
    )


@pytest.mark.asyncio
async def test_wait_if_paused_parks_execution_until_resume_requested() -> None:
    manager = WorkflowControlManager()

    await manager.mark_running(
        "execution-1",
    )
    await manager.request_pause(
        "execution-1",
    )

    wait_task = asyncio.create_task(
        manager.wait_if_paused(
            "execution-1",
        ),
    )
    await asyncio.sleep(0)

    assert (
        manager.get_state(
            "execution-1",
        )
        is WorkflowControlState.PAUSED
    )
    assert wait_task.done() is False

    await manager.request_resume(
        "execution-1",
    )
    await asyncio.wait_for(
        wait_task,
        timeout=1.0,
    )

    assert (
        manager.get_state(
            "execution-1",
        )
        is WorkflowControlState.RUNNING
    )
    assert (
        manager.should_pause(
            "execution-1",
        )
        is False
    )


@pytest.mark.asyncio
async def test_request_resume_records_resume_context_before_wait_boundary_runs() -> (
    None
):
    manager = WorkflowControlManager()

    await manager.mark_running(
        "execution-1",
        metadata={
            "workflow": "morning_report",
        },
    )
    await manager.request_pause(
        "execution-1",
        reason="pause",
        requested_by="cli",
    )
    wait_task = asyncio.create_task(
        manager.wait_if_paused(
            "execution-1",
        ),
    )
    await asyncio.sleep(0)

    await manager.request_resume(
        "execution-1",
        reason="resume",
        requested_by="cli",
        metadata={
            "resumed": True,
        },
    )
    snapshot = manager.get_snapshot(
        "execution-1",
    )

    assert snapshot.state is WorkflowControlState.RESUMING
    assert snapshot.reason == "resume"
    assert snapshot.requested_by == "cli"
    assert snapshot.metadata == {
        "workflow": "morning_report",
        "resumed": True,
    }

    await asyncio.wait_for(
        wait_task,
        timeout=1.0,
    )

    assert (
        manager.get_state(
            "execution-1",
        )
        is WorkflowControlState.RUNNING
    )


@pytest.mark.asyncio
async def test_wait_if_paused_returns_immediately_when_execution_is_not_pausing() -> (
    None
):
    manager = WorkflowControlManager()

    await manager.mark_running(
        "execution-1",
    )

    await asyncio.wait_for(
        manager.wait_if_paused(
            "execution-1",
        ),
        timeout=1.0,
    )

    assert (
        manager.get_state(
            "execution-1",
        )
        is WorkflowControlState.RUNNING
    )


@pytest.mark.asyncio
async def test_request_cancel_marks_cancelling_and_preserves_request_context() -> None:
    manager = WorkflowControlManager()

    await manager.mark_running(
        "execution-1",
        metadata={
            "workflow": "morning_report",
        },
    )
    await manager.request_cancel(
        "execution-1",
        reason="operator requested cancel",
        requested_by="cli",
        metadata={
            "safe_boundary": "before_wave_2",
        },
    )

    snapshot = manager.get_snapshot(
        "execution-1",
    )

    assert snapshot.state is WorkflowControlState.CANCELLING
    assert snapshot.reason == "operator requested cancel"
    assert snapshot.requested_by == "cli"
    assert snapshot.metadata == {
        "workflow": "morning_report",
        "safe_boundary": "before_wave_2",
    }
    assert (
        manager.should_cancel(
            "execution-1",
        )
        is True
    )
    assert (
        manager.should_pause(
            "execution-1",
        )
        is False
    )


@pytest.mark.asyncio
async def test_mark_cancelled_sets_terminal_cancelled_state() -> None:
    manager = WorkflowControlManager()

    await manager.mark_running(
        "execution-1",
        metadata={
            "workflow": "morning_report",
        },
    )
    await manager.request_cancel(
        "execution-1",
        reason="operator requested cancel",
        requested_by="cli",
        metadata={
            "safe_boundary": "before_wave_2",
        },
    )
    await manager.mark_cancelled(
        "execution-1",
        metadata={
            "stopped_at": "wave_boundary",
        },
    )

    snapshot = manager.get_snapshot(
        "execution-1",
    )

    assert snapshot.state is WorkflowControlState.CANCELLED
    assert snapshot.reason == "operator requested cancel"
    assert snapshot.requested_by == "cli"
    assert snapshot.metadata == {
        "workflow": "morning_report",
        "safe_boundary": "before_wave_2",
        "stopped_at": "wave_boundary",
    }
    assert (
        manager.should_cancel(
            "execution-1",
        )
        is True
    )


@pytest.mark.asyncio
async def test_request_cancel_releases_execution_parked_in_pause() -> None:
    manager = WorkflowControlManager()

    await manager.mark_running(
        "execution-1",
    )
    await manager.request_pause(
        "execution-1",
    )

    wait_task = asyncio.create_task(
        manager.wait_if_paused(
            "execution-1",
        ),
    )
    await asyncio.sleep(0)

    assert (
        manager.get_state(
            "execution-1",
        )
        is WorkflowControlState.PAUSED
    )
    assert wait_task.done() is False

    await manager.request_cancel(
        "execution-1",
        reason="cancel while paused",
        requested_by="cli",
    )
    await asyncio.wait_for(
        wait_task,
        timeout=1.0,
    )

    snapshot = manager.get_snapshot(
        "execution-1",
    )

    assert snapshot.state is WorkflowControlState.CANCELLING
    assert snapshot.reason == "cancel while paused"
    assert snapshot.requested_by == "cli"
    assert (
        manager.should_pause(
            "execution-1",
        )
        is False
    )
    assert (
        manager.should_cancel(
            "execution-1",
        )
        is True
    )


@pytest.mark.asyncio
async def test_should_cancel_is_false_for_non_cancel_states() -> None:
    manager = WorkflowControlManager()

    assert (
        manager.should_cancel(
            "execution-1",
        )
        is False
    )

    await manager.initialize_execution(
        "execution-1",
    )
    assert (
        manager.should_cancel(
            "execution-1",
        )
        is False
    )

    await manager.mark_running(
        "execution-1",
    )
    assert (
        manager.should_cancel(
            "execution-1",
        )
        is False
    )
