from __future__ import annotations

import pytest

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.events import EventBus
from core.runtime.events import RuntimeEvent
from core.runtime.events import RuntimeEventType
from core.runtime.execution.runtime_engine import RuntimeEngine
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.workflow.models.workflow_execution_plan import ExecutionPlanNode
from core.workflow.models.workflow_execution_plan import ExecutionWave
from core.workflow.models.workflow_execution_plan import WorkflowExecutionPlan


class EmittingRuntimeNode(RuntimeNode):
    node_name = "emitting_node"
    node_type = "test"

    def __init__(
        self,
    ) -> None:
        self.missing_location_event = RuntimeEvent(
            event_type=RuntimeEventType.METRIC_RECORDED,
            execution_id="",
            workflow_id="",
            payload={
                "metric_name": "node.output.metric",
                "value": 1,
            },
        )
        self.explicit_location_event = RuntimeEvent(
            event_type=RuntimeEventType.AUDIT_RECORDED,
            execution_id="explicit-execution",
            workflow_id="explicit-workflow",
            runtime_id="explicit-runtime",
            node_name="explicit-node",
            wave_index=7,
            payload={
                "audit": "preserve-location",
            },
            metadata={
                "source": "node-output",
            },
        )

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput(
            success=True,
            outputs={
                "ok": True,
            },
            emitted_events=[
                self.missing_location_event,
                self.explicit_location_event,
            ],
        )


def build_context() -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="unit_workflow",
        execution_id="execution-1",
    )


def build_plan() -> WorkflowExecutionPlan:
    return WorkflowExecutionPlan(
        workflow_name="unit_workflow",
        execution_id="execution-1",
        nodes={
            "emitting_node": ExecutionPlanNode(
                name="emitting_node",
                node_type="test",
                max_retries=0,
            ),
        },
        waves=(
            ExecutionWave(
                index=0,
                nodes=("emitting_node",),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_runtime_engine_emits_node_output_events_with_runtime_location() -> None:
    event_bus = EventBus()
    received_events: list[RuntimeEvent] = []

    async def collect(
        event: RuntimeEvent,
    ) -> None:
        received_events.append(
            event,
        )

    event_bus.subscribe_all(
        collect,
    )

    node = EmittingRuntimeNode()
    engine = RuntimeEngine(
        event_bus=event_bus,
    )
    engine.register(
        "emitting_node",
        node,
    )

    await engine.execute(
        context=build_context(),
        execution_plan=build_plan(),
    )

    output_events = [
        event
        for event in received_events
        if event.event_type
        in {
            RuntimeEventType.METRIC_RECORDED,
            RuntimeEventType.AUDIT_RECORDED,
        }
    ]

    assert len(output_events) == 2

    missing_location_event = output_events[0]
    assert missing_location_event is not node.missing_location_event
    assert missing_location_event.event_type is RuntimeEventType.METRIC_RECORDED
    assert missing_location_event.execution_id == "execution-1"
    assert missing_location_event.workflow_id == "unit_workflow"
    assert missing_location_event.runtime_id == "runtime-1"
    assert missing_location_event.node_name == "emitting_node"
    assert missing_location_event.wave_index == 0
    assert missing_location_event.payload["metric_name"] == "node.output.metric"
    assert missing_location_event.payload["value"] == 1
    assert missing_location_event.payload["trace_id"]
    assert missing_location_event.payload["span_id"]
    assert (
        missing_location_event.metadata["trace_id"]
        == (missing_location_event.payload["trace_id"])
    )

    explicit_location_event = output_events[1]
    assert explicit_location_event is not node.explicit_location_event
    assert explicit_location_event.event_type is RuntimeEventType.AUDIT_RECORDED
    assert explicit_location_event.execution_id == "explicit-execution"
    assert explicit_location_event.workflow_id == "explicit-workflow"
    assert explicit_location_event.runtime_id == "explicit-runtime"
    assert explicit_location_event.node_name == "explicit-node"
    assert explicit_location_event.wave_index == 7
    assert explicit_location_event.payload["audit"] == "preserve-location"
    assert explicit_location_event.payload["trace_id"]
    assert explicit_location_event.payload["span_id"]
    assert explicit_location_event.metadata["source"] == "node-output"
    assert (
        explicit_location_event.metadata["trace_id"]
        == (explicit_location_event.payload["trace_id"])
    )
