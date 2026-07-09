from __future__ import annotations

import asyncio

import pytest

from core.runtime.lifecycle.runtime_lifecycle_failure_telemetry import (
    RuntimeLifecycleFailureTelemetry,
)
from core.runtime.lifecycle.runtime_lifecycle_hooks import NoOpRuntimeLifecycleHook
from core.runtime.lifecycle.runtime_lifecycle_manager import RuntimeLifecycleManager
from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.telemetry.tracing.trace_context import TraceContext
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapConfig
from core.workflow.bootstrap.workflow_bootstrap import build_workflow_runtime
from core.workflow.models.workflow_execution_plan import ExecutionPlanNode


class FailingRuntimeLifecycleHook(NoOpRuntimeLifecycleHook):
    async def before_node_execute(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
    ) -> None:
        raise RuntimeError("runtime lifecycle hook exploded")


class CancelledRuntimeLifecycleHook(NoOpRuntimeLifecycleHook):
    async def before_node_execute(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
    ) -> None:
        raise asyncio.CancelledError


class RecordingRuntimeLifecycleHook(NoOpRuntimeLifecycleHook):
    def __init__(self) -> None:
        self.before_node_calls = 0

    async def before_node_execute(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
    ) -> None:
        self.before_node_calls += 1


def build_context() -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-lifecycle-runtime",
        workflow_id="runtime-lifecycle-workflow",
        execution_id="runtime-lifecycle-execution",
        trace_context=TraceContext(
            trace_id="runtime-lifecycle-trace",
            span_id="runtime-lifecycle-span",
            parent_span_id="runtime-lifecycle-parent",
            correlation_id="runtime-lifecycle-correlation",
            workflow_id="runtime-lifecycle-workflow",
            execution_id="runtime-lifecycle-execution",
            runtime_id="runtime-lifecycle-runtime",
        ),
    )


def build_plan_node() -> ExecutionPlanNode:
    return ExecutionPlanNode(
        name="runtime_lifecycle_node",
        node_type="runtime_lifecycle_test",
    )


@pytest.mark.asyncio
async def test_runtime_lifecycle_reports_hook_failure_once_and_continues() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    failure_telemetry = RuntimeLifecycleFailureTelemetry(observability)
    healthy_hook = RecordingRuntimeLifecycleHook()
    manager = RuntimeLifecycleManager(
        hooks=[FailingRuntimeLifecycleHook(), healthy_hook],
        failure_handler=failure_telemetry.emit_hook_failure,
    )

    await manager.before_node_execute(build_context(), build_plan_node())

    assert healthy_hook.before_node_calls == 1
    failure_events = [
        event
        for event in sink.events
        if event.event_type == "runtime.lifecycle.hook_failed"
    ]
    assert len(failure_events) == 1
    event = failure_events[0]
    assert event.workflow_id == "runtime-lifecycle-workflow"
    assert event.execution_id == "runtime-lifecycle-execution"
    assert event.runtime_id == "runtime-lifecycle-runtime"
    assert event.node_name == "runtime_lifecycle_node"
    assert event.trace_id == "runtime-lifecycle-trace"
    assert event.span_id == "runtime-lifecycle-span"
    assert event.parent_span_id == "runtime-lifecycle-parent"
    assert event.correlation_id == "runtime-lifecycle-correlation"
    assert event.payload == {
        "lifecycle_event": "before_node_execute",
        "hook": "FailingRuntimeLifecycleHook",
        "original_event_type": None,
    }
    assert event.exception_details is not None
    assert event.exception_details.exception_type == "RuntimeError"
    assert event.exception_details.message == "runtime lifecycle hook exploded"
    assert "before_node_execute" in event.exception_details.stack_trace


@pytest.mark.asyncio
async def test_runtime_lifecycle_reports_fail_fast_failure_before_raising() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    failure_telemetry = RuntimeLifecycleFailureTelemetry(observability)
    manager = RuntimeLifecycleManager(
        hooks=[FailingRuntimeLifecycleHook()],
        fail_fast=True,
        failure_handler=failure_telemetry.emit_hook_failure,
    )

    with pytest.raises(RuntimeError, match="runtime lifecycle hook exploded"):
        await manager.before_node_execute(build_context(), build_plan_node())

    assert [event.event_type for event in sink.events] == [
        "runtime.lifecycle.hook_failed"
    ]


@pytest.mark.asyncio
async def test_runtime_lifecycle_propagates_cancellation_without_failure_event() -> (
    None
):
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    failure_telemetry = RuntimeLifecycleFailureTelemetry(observability)
    manager = RuntimeLifecycleManager(
        hooks=[CancelledRuntimeLifecycleHook()],
        failure_handler=failure_telemetry.emit_hook_failure,
    )

    with pytest.raises(asyncio.CancelledError):
        await manager.before_node_execute(build_context(), build_plan_node())

    assert sink.events == []


@pytest.mark.asyncio
async def test_workflow_bootstrap_wires_runtime_lifecycle_failure_telemetry() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_checkpoints=False,
            enable_artifacts=False,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
            enable_observability=True,
            enable_telemetry_logging=False,
            enable_policies=False,
            enable_governance=False,
        ),
        observability_manager=observability,
    )
    runtime.lifecycle_manager.register(FailingRuntimeLifecycleHook())

    await runtime.lifecycle_manager.before_node_execute(
        build_context(),
        build_plan_node(),
    )

    failure_events = [
        event
        for event in sink.events
        if event.event_type == "runtime.lifecycle.hook_failed"
    ]
    assert len(failure_events) == 1
    assert failure_events[0].payload["hook"] == "FailingRuntimeLifecycleHook"
