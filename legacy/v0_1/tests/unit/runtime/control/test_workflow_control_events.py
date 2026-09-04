from __future__ import annotations

import asyncio

import pytest

from core.runtime.control import WorkflowControlManager
from core.runtime.events import EventBus, RuntimeEvent, RuntimeEventType


def create_event_collector() -> tuple[EventBus, list[RuntimeEvent]]:
    event_bus = EventBus()
    events: list[RuntimeEvent] = []

    async def collect(
        event: RuntimeEvent,
    ) -> None:
        events.append(
            event,
        )

    event_bus.subscribe_all(
        collect,
    )
    return event_bus, events


def event_types(
    events: list[RuntimeEvent],
) -> list[RuntimeEventType]:
    return [event.event_type for event in events]


@pytest.mark.asyncio
async def test_mark_running_emits_state_changed_and_running_progress_events() -> None:
    event_bus, events = create_event_collector()
    manager = WorkflowControlManager(
        event_bus=event_bus,
    )

    await manager.mark_running(
        "execution-1",
        metadata={
            "workflow_id": "morning_report",
            "runtime_id": "runtime-1",
        },
    )

    assert event_types(
        events,
    ) == [
        RuntimeEventType.WORKFLOW_STATE_CHANGED,
        RuntimeEventType.WORKFLOW_PROGRESS_RUNNING,
    ]

    for event in events:
        assert event.execution_id == "execution-1"
        assert event.workflow_id == "morning_report"
        assert event.runtime_id == "runtime-1"
        assert event.payload["execution_id"] == "execution-1"
        assert event.payload["state"] == "running"
        assert event.payload["previous_state"] is None
        assert event.metadata == {
            "workflow_id": "morning_report",
            "runtime_id": "runtime-1",
        }


@pytest.mark.asyncio
async def test_pause_resume_emits_ordered_control_progress_events() -> None:
    event_bus, events = create_event_collector()
    manager = WorkflowControlManager(
        event_bus=event_bus,
    )

    await manager.mark_running(
        "execution-1",
        metadata={
            "workflow_name": "morning_report",
            "runtime_id": "runtime-1",
        },
    )
    await manager.request_pause(
        "execution-1",
        reason="operator requested pause",
        requested_by="cli",
    )
    wait_task = asyncio.create_task(
        manager.wait_if_paused(
            "execution-1",
        ),
    )
    await asyncio.sleep(
        0,
    )
    await manager.request_resume(
        "execution-1",
        reason="operator requested resume",
        requested_by="cli",
    )
    await asyncio.wait_for(
        wait_task,
        timeout=1.0,
    )

    assert event_types(
        events,
    ) == [
        RuntimeEventType.WORKFLOW_STATE_CHANGED,
        RuntimeEventType.WORKFLOW_PROGRESS_RUNNING,
        RuntimeEventType.WORKFLOW_STATE_CHANGED,
        RuntimeEventType.WORKFLOW_PROGRESS_PAUSING,
        RuntimeEventType.WORKFLOW_STATE_CHANGED,
        RuntimeEventType.WORKFLOW_PROGRESS_PAUSED,
        RuntimeEventType.WORKFLOW_STATE_CHANGED,
        RuntimeEventType.WORKFLOW_PROGRESS_RESUMING,
        RuntimeEventType.WORKFLOW_STATE_CHANGED,
        RuntimeEventType.WORKFLOW_PROGRESS_RESUMED,
    ]

    resumed_event = events[-1]
    assert resumed_event.workflow_id == "morning_report"
    assert resumed_event.payload["state"] == "running"
    assert resumed_event.payload["previous_state"] == "resuming"
    assert resumed_event.payload["reason"] == "operator requested resume"
    assert resumed_event.payload["requested_by"] == "cli"


@pytest.mark.asyncio
async def test_cancel_while_paused_emits_cancelling_without_resumed_event() -> None:
    event_bus, events = create_event_collector()
    manager = WorkflowControlManager(
        event_bus=event_bus,
    )

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
    await asyncio.sleep(
        0,
    )

    await manager.request_cancel(
        "execution-1",
        reason="operator requested cancel",
        requested_by="cli",
    )
    await asyncio.wait_for(
        wait_task,
        timeout=1.0,
    )
    await manager.mark_cancelled(
        "execution-1",
    )

    types = event_types(
        events,
    )
    assert RuntimeEventType.WORKFLOW_PROGRESS_PAUSED in types
    assert RuntimeEventType.WORKFLOW_PROGRESS_CANCELLING in types
    assert RuntimeEventType.WORKFLOW_PROGRESS_CANCELLED in types
    assert RuntimeEventType.WORKFLOW_PROGRESS_RESUMED not in types

    cancelled_event = events[-1]
    assert cancelled_event.event_type is RuntimeEventType.WORKFLOW_PROGRESS_CANCELLED
    assert cancelled_event.payload["state"] == "cancelled"
    assert cancelled_event.payload["previous_state"] == "cancelling"
    assert cancelled_event.payload["reason"] == "operator requested cancel"
    assert cancelled_event.payload["requested_by"] == "cli"
    assert cancelled_event.is_terminal is True
    assert cancelled_event.is_error is False


@pytest.mark.asyncio
async def test_completed_and_failed_emit_terminal_progress_events() -> None:
    event_bus, events = create_event_collector()
    manager = WorkflowControlManager(
        event_bus=event_bus,
    )

    await manager.mark_completed(
        "execution-completed",
        metadata={
            "workflow_id": "morning_report",
        },
    )
    await manager.mark_failed(
        "execution-failed",
        reason="node failed",
        metadata={
            "workflow_id": "morning_report",
        },
    )

    completed_progress = next(
        event
        for event in events
        if event.event_type is RuntimeEventType.WORKFLOW_PROGRESS_COMPLETED
    )
    failed_progress = next(
        event
        for event in events
        if event.event_type is RuntimeEventType.WORKFLOW_PROGRESS_FAILED
    )

    assert completed_progress.execution_id == "execution-completed"
    assert completed_progress.payload["state"] == "completed"
    assert completed_progress.is_terminal is True
    assert completed_progress.is_error is False

    assert failed_progress.execution_id == "execution-failed"
    assert failed_progress.payload["state"] == "failed"
    assert failed_progress.payload["reason"] == "node failed"
    assert failed_progress.is_terminal is True
    assert failed_progress.is_error is True
