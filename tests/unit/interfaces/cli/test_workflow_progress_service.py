from __future__ import annotations

from datetime import datetime
from datetime import timezone
import pytest

from core.runtime.events import EventBus
from core.runtime.events import RuntimeEvent
from core.runtime.events import RuntimeEventType
from interfaces.cli.services.workflow_progress_service import (
    WorkflowProgressNotification,
)
from interfaces.cli.services.workflow_progress_service import (
    WorkflowProgressSubscription,
)
from interfaces.cli.services.workflow_progress_service import (
    format_workflow_progress_notification,
)
from interfaces.cli.services.workflow_progress_service import (
    progress_notification_from_event,
)


def build_event(
    event_type: RuntimeEventType,
    *,
    node_name: str | None = None,
    wave_index: int | None = None,
) -> RuntimeEvent:
    return RuntimeEvent(
        event_type=event_type,
        execution_id="exec-123",
        workflow_id="morning_report",
        runtime_id="runtime-123",
        timestamp=datetime.now(
            timezone.utc,
        ),
        node_name=node_name,
        wave_index=wave_index,
        payload={
            "state": "running",
            "node_name": node_name,
            "wave_index": wave_index,
        },
        metadata={
            "interface": "cli",
        },
    )


def test_progress_notification_from_event_preserves_runtime_identity() -> None:
    notification = progress_notification_from_event(
        build_event(
            RuntimeEventType.NODE_PROGRESS_STARTED,
            node_name="technical_agent",
            wave_index=1,
        )
    )

    assert notification.event_type == "runtime.node.started"
    assert notification.execution_id == "exec-123"
    assert notification.workflow_id == "morning_report"
    assert notification.runtime_id == "runtime-123"
    assert notification.node_name == "technical_agent"
    assert notification.wave_index == 1
    assert notification.state == "running"
    assert "technical_agent" in notification.message
    assert notification.to_dict()["metadata"] == {
        "interface": "cli",
    }


@pytest.mark.asyncio
async def test_progress_subscription_filters_runtime_progress_events() -> None:
    event_bus = EventBus()
    notifications: list[WorkflowProgressNotification] = []
    subscription = WorkflowProgressSubscription(
        event_bus=event_bus,
        handler=notifications.append,
    )

    subscription.start()
    await event_bus.emit(
        build_event(
            RuntimeEventType.WORKFLOW_PROGRESS_STARTED,
        )
    )
    await event_bus.emit(
        build_event(
            RuntimeEventType.CHECKPOINT_CREATED,
        )
    )
    await event_bus.emit(
        build_event(
            RuntimeEventType.NODE_PROGRESS_COMPLETED,
            node_name="technical_agent",
            wave_index=0,
        )
    )
    subscription.stop()
    await event_bus.emit(
        build_event(
            RuntimeEventType.WORKFLOW_PROGRESS_COMPLETED,
        )
    )

    assert [notification.event_type for notification in notifications] == [
        "runtime.workflow.started",
        "runtime.node.completed",
    ]
    assert event_bus.global_subscriber_count() == 0


def test_format_workflow_progress_notification_is_console_safe() -> None:
    rendered = format_workflow_progress_notification(
        WorkflowProgressNotification(
            event_type="runtime.node.completed",
            execution_id="exec-123",
            workflow_id="morning_report",
            runtime_id="runtime-123",
            node_name="technical_agent",
            wave_index=0,
            state="running",
        )
    )

    assert rendered.startswith("[progress]")
    assert "workflow=morning_report" in rendered
    assert "execution=exec-123" in rendered
    assert "node=technical_agent" in rendered
    assert "wave=0" in rendered
    assert "state=running" in rendered


def test_progress_console_renderer_emits_notification_and_bar() -> None:
    from interfaces.cli.services.workflow_progress_service import (
        WorkflowProgressConsoleRenderer,
    )

    lines: list[str] = []
    renderer = WorkflowProgressConsoleRenderer(
        emitter=lines.append,
        width=10,
    )

    renderer.handle(
        WorkflowProgressNotification(
            event_type="runtime.workflow.started",
            execution_id="exec-123",
            workflow_id="morning_report",
            payload={
                "metadata": {
                    "total_nodes": 2,
                },
            },
        )
    )
    renderer.handle(
        WorkflowProgressNotification(
            event_type="runtime.node.completed",
            execution_id="exec-123",
            workflow_id="morning_report",
            node_name="technical_agent",
        )
    )

    assert lines[0].startswith(
        "[progress]",
    )
    assert lines[1] == "[progress-bar] [----------] 0/2 nodes (0%)"
    assert lines[3] == "[progress-bar] [#####-----] 1/2 nodes (50%)"
