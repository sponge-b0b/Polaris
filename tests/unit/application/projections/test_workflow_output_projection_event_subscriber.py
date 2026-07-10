from __future__ import annotations

import pytest

from application.projections.workflow_outputs import CompletedRunProjectionSummary
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionEventSubscriber,
)
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionEventSubscriberConfig,
)
from application.projections.workflow_outputs import WorkflowOutputProjectionRequest
from core.runtime.events.event_bus import EventBus
from core.runtime.events.runtime_events import RuntimeEvent
from core.runtime.events.runtime_events import RuntimeEventType


class FakeProjectionService:
    def __init__(self, *, error: BaseException | None = None) -> None:
        self.requests: list[WorkflowOutputProjectionRequest] = []
        self._error = error

    async def project_completed_run(
        self,
        request: WorkflowOutputProjectionRequest,
    ) -> CompletedRunProjectionSummary:
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        return CompletedRunProjectionSummary(
            workflow_name=request.workflow_name,
            execution_id=request.execution_id,
            run_id="run-1",
        )


class RuntimeEventRecorder:
    def __init__(self) -> None:
        self.events: list[RuntimeEvent] = []

    async def handle_event(self, event: RuntimeEvent) -> None:
        self.events.append(event)


@pytest.mark.asyncio
async def test_subscribe_registers_completed_and_failed_events_only() -> None:
    event_bus = EventBus()
    service = FakeProjectionService()
    subscriber = WorkflowOutputProjectionEventSubscriber(service)

    subscriber.subscribe(event_bus)
    subscriber.subscribe(event_bus)

    assert event_bus.subscriber_count(RuntimeEventType.WORKFLOW_COMPLETED) == 1
    assert event_bus.subscriber_count(RuntimeEventType.WORKFLOW_FAILED) == 1
    assert event_bus.subscriber_count(RuntimeEventType.WORKFLOW_STARTED) == 0


@pytest.mark.asyncio
async def test_handle_completed_event_uses_payload_workflow_name() -> None:
    service = FakeProjectionService()
    subscriber = WorkflowOutputProjectionEventSubscriber(service)

    await subscriber.handle_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_COMPLETED,
            execution_id="execution-1",
            workflow_id="workflow-id",
            runtime_id="runtime-1",
            payload={"workflow_name": "morning_report"},
        )
    )

    assert len(service.requests) == 1
    request = service.requests[0]
    assert request.workflow_name == "morning_report"
    assert request.execution_id == "execution-1"
    assert request.force_reproject is False
    assert request.dry_run is False


@pytest.mark.asyncio
async def test_handle_failed_event_invokes_projection_for_successful_node_outputs() -> (
    None
):
    service = FakeProjectionService()
    subscriber = WorkflowOutputProjectionEventSubscriber(
        service,
        config=WorkflowOutputProjectionEventSubscriberConfig(
            force_reproject=True,
            dry_run=True,
        ),
    )

    await subscriber.handle_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_FAILED,
            execution_id="execution-2",
            workflow_id="morning_report",
            runtime_id="runtime-2",
            payload={"workflow_name": "morning_report"},
        )
    )

    assert len(service.requests) == 1
    request = service.requests[0]
    assert request.workflow_name == "morning_report"
    assert request.execution_id == "execution-2"
    assert request.force_reproject is True
    assert request.dry_run is True


@pytest.mark.asyncio
async def test_handle_event_falls_back_to_metadata_and_workflow_id() -> None:
    metadata_service = FakeProjectionService()
    metadata_subscriber = WorkflowOutputProjectionEventSubscriber(metadata_service)

    await metadata_subscriber.handle_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_COMPLETED,
            execution_id="execution-3",
            workflow_id="workflow-id",
            metadata={"workflow_name": "metadata_workflow"},
        )
    )

    workflow_id_service = FakeProjectionService()
    workflow_id_subscriber = WorkflowOutputProjectionEventSubscriber(
        workflow_id_service
    )

    await workflow_id_subscriber.handle_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_COMPLETED,
            execution_id="execution-4",
            workflow_id="workflow_id_workflow",
        )
    )

    assert metadata_service.requests[0].workflow_name == "metadata_workflow"
    assert workflow_id_service.requests[0].workflow_name == "workflow_id_workflow"


@pytest.mark.asyncio
async def test_handle_event_ignores_non_terminal_workflow_event() -> None:
    service = FakeProjectionService()
    subscriber = WorkflowOutputProjectionEventSubscriber(service)

    await subscriber.handle_event(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_STARTED,
            execution_id="execution-5",
            workflow_id="morning_report",
        )
    )

    assert service.requests == []


@pytest.mark.asyncio
async def test_event_bus_non_fail_fast_isolates_projection_failure() -> None:
    event_bus = EventBus(fail_fast=False)
    service = FakeProjectionService(error=RuntimeError("projection failed"))
    subscriber = WorkflowOutputProjectionEventSubscriber(service)
    warning_recorder = RuntimeEventRecorder()

    subscriber.subscribe(event_bus)
    event_bus.subscribe(RuntimeEventType.SYSTEM_WARNING, warning_recorder.handle_event)

    await event_bus.emit(
        RuntimeEvent(
            event_type=RuntimeEventType.WORKFLOW_COMPLETED,
            execution_id="execution-6",
            workflow_id="morning_report",
            payload={"workflow_name": "morning_report"},
        )
    )

    assert len(service.requests) == 1
    assert len(warning_recorder.events) == 1
    warning = warning_recorder.events[0]
    assert warning.event_type is RuntimeEventType.SYSTEM_WARNING
    assert warning.payload["warning_type"] == "EventBusSubscriberFailure"
    assert (
        warning.payload["failed_event_type"]
        == RuntimeEventType.WORKFLOW_COMPLETED.value
    )
    assert warning.payload["failure_count"] == 1
