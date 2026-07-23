from __future__ import annotations

import asyncio

import pytest

from core.runtime.events import EventBus, RuntimeEvent, RuntimeEventType


def build_event() -> RuntimeEvent:
    return RuntimeEvent(
        event_type=RuntimeEventType.METRIC_RECORDED,
        execution_id="execution-1",
        workflow_id="unit_workflow",
        runtime_id="runtime-1",
        node_name="node-1",
        wave_index=2,
        payload={
            "metric_name": "test.metric",
            "trace_id": "trace-1",
            "span_id": "span-1",
            "parent_span_id": "parent-span-1",
        },
    )


@pytest.mark.asyncio
async def test_event_bus_reports_subscriber_failure_without_blocking_successful_handler() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    event_bus = EventBus()
    handled_events: list[RuntimeEvent] = []
    warning_events: list[RuntimeEvent] = []

    async def failing_handler(
        event: RuntimeEvent,
    ) -> None:
        raise RuntimeError(f"boom: {event.event_type.value}")

    async def successful_handler(
        event: RuntimeEvent,
    ) -> None:
        handled_events.append(
            event,
        )

    async def warning_handler(
        event: RuntimeEvent,
    ) -> None:
        warning_events.append(
            event,
        )

    event_bus.subscribe(
        RuntimeEventType.METRIC_RECORDED,
        failing_handler,
    )
    event_bus.subscribe(
        RuntimeEventType.METRIC_RECORDED,
        successful_handler,
    )
    event_bus.subscribe(
        RuntimeEventType.SYSTEM_WARNING,
        warning_handler,
    )

    original_event = build_event()
    await event_bus.emit(
        original_event,
    )

    assert handled_events == [
        original_event,
    ]
    assert (
        len(
            warning_events,
        )
        == 1
    )

    warning = warning_events[0]
    assert warning.event_type is RuntimeEventType.SYSTEM_WARNING
    assert warning.execution_id == original_event.execution_id
    assert warning.workflow_id == original_event.workflow_id
    assert warning.runtime_id == original_event.runtime_id
    assert warning.node_name == original_event.node_name
    assert warning.wave_index == original_event.wave_index
    assert warning.payload["warning_type"] == "EventBusSubscriberFailure"
    assert warning.payload["failed_event_type"] == "metric_recorded"
    assert warning.payload["failure_count"] == 1
    assert warning.payload["failures"][0]["handler"].endswith("failing_handler")
    failure = warning.payload["failures"][0]
    assert failure["exception_details"]["exception_type"] == "RuntimeError"
    assert failure["exception_details"]["message"] == "boom: metric_recorded"
    assert "failing_handler" in failure["exception_details"]["stack_trace"]
    assert warning.payload["failed_event"] == {
        "event_type": "metric_recorded",
        "timestamp": original_event.timestamp.isoformat(),
        "execution_id": original_event.execution_id,
        "workflow_id": original_event.workflow_id,
        "runtime_id": original_event.runtime_id,
        "node_name": original_event.node_name,
        "wave_index": original_event.wave_index,
    }
    assert warning.payload["trace_id"] == "trace-1"
    assert warning.payload["span_id"] == "span-1"
    assert warning.payload["parent_span_id"] == "parent-span-1"
    assert warning.metadata == {
        "source": "EventBus",
        "original_event_type": "metric_recorded",
        "original_event_timestamp": original_event.timestamp.isoformat(),
        "trace_id": "trace-1",
        "span_id": "span-1",
        "parent_span_id": "parent-span-1",
    }


@pytest.mark.asyncio
async def test_event_bus_does_not_recursively_report_failure_warning_failures() -> None:
    event_bus = EventBus()
    observed_warnings: list[RuntimeEvent] = []
    failed_event_types: list[RuntimeEventType] = []

    async def failing_global_handler(
        event: RuntimeEvent,
    ) -> None:
        failed_event_types.append(
            event.event_type,
        )
        raise RuntimeError("global subscriber failed")

    async def warning_handler(
        event: RuntimeEvent,
    ) -> None:
        observed_warnings.append(
            event,
        )

    event_bus.subscribe_all(
        failing_global_handler,
    )
    event_bus.subscribe(
        RuntimeEventType.SYSTEM_WARNING,
        warning_handler,
    )

    await event_bus.emit(
        build_event(),
    )

    assert failed_event_types == [
        RuntimeEventType.METRIC_RECORDED,
        RuntimeEventType.SYSTEM_WARNING,
    ]
    assert (
        len(
            observed_warnings,
        )
        == 1
    )
    assert observed_warnings[0].payload["failure_count"] == 1


@pytest.mark.asyncio
async def test_event_bus_fail_fast_behavior_is_unchanged() -> None:
    event_bus = EventBus(
        fail_fast=True,
    )
    successful_handler_called = False
    warning_events: list[RuntimeEvent] = []

    async def failing_handler(
        event: RuntimeEvent,
    ) -> None:
        raise RuntimeError("fail fast")

    async def successful_handler(
        event: RuntimeEvent,
    ) -> None:
        nonlocal successful_handler_called
        successful_handler_called = True

    async def warning_handler(
        event: RuntimeEvent,
    ) -> None:
        warning_events.append(
            event,
        )

    event_bus.subscribe(
        RuntimeEventType.METRIC_RECORDED,
        failing_handler,
    )
    event_bus.subscribe(
        RuntimeEventType.METRIC_RECORDED,
        successful_handler,
    )
    event_bus.subscribe(
        RuntimeEventType.SYSTEM_WARNING,
        warning_handler,
    )

    with pytest.raises(
        RuntimeError,
        match="fail fast",
    ):
        await event_bus.emit(
            build_event(),
        )

    assert successful_handler_called is False
    assert warning_events == []


@pytest.mark.asyncio
async def test_event_bus_propagates_subscriber_cancellation() -> None:
    event_bus = EventBus()
    warning_events: list[RuntimeEvent] = []

    async def cancelled_handler(
        event: RuntimeEvent,
    ) -> None:
        raise asyncio.CancelledError

    async def warning_handler(
        event: RuntimeEvent,
    ) -> None:
        warning_events.append(event)

    event_bus.subscribe(RuntimeEventType.METRIC_RECORDED, cancelled_handler)
    event_bus.subscribe(RuntimeEventType.SYSTEM_WARNING, warning_handler)

    with pytest.raises(asyncio.CancelledError):
        await event_bus.emit(build_event())

    assert warning_events == []
