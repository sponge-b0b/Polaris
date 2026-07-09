from __future__ import annotations

import asyncio

import pytest

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.execution.runtime_engine import RuntimeEngine
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.telemetry.tracing.trace_context import TraceContext
from core.workflow.models.workflow_execution_plan import ExecutionPlanNode
from core.workflow.models.workflow_execution_plan import ExecutionWave
from core.workflow.models.workflow_execution_plan import WorkflowExecutionPlan


class ConcurrentTraceNode(RuntimeNode):
    node_type = "trace_test"

    def __init__(
        self,
        *,
        node_name: str,
        started_nodes: set[str],
        both_started: asyncio.Event,
        observed_traces: dict[str, TraceContext],
    ) -> None:
        self.node_name = node_name
        self._started_nodes = started_nodes
        self._both_started = both_started
        self._observed_traces = observed_traces

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        assert context.trace_context is not None
        self._observed_traces[self.node_name] = context.trace_context
        self._started_nodes.add(self.node_name)
        if len(self._started_nodes) == 2:
            self._both_started.set()

        await asyncio.wait_for(
            self._both_started.wait(),
            timeout=0.5,
        )

        return RuntimeNodeOutput.success_output(
            outputs={
                "node_name": self.node_name,
                "trace_id": context.trace_context.trace_id,
                "span_id": context.trace_context.span_id,
                "parent_span_id": context.trace_context.parent_span_id,
            }
        )


@pytest.mark.asyncio
async def test_same_wave_nodes_run_concurrently_with_distinct_child_traces() -> None:
    started_nodes: set[str] = set()
    both_started = asyncio.Event()
    observed_traces: dict[str, TraceContext] = {}
    engine = RuntimeEngine()

    for node_name in ("alpha", "beta"):
        engine.register(
            node_name,
            ConcurrentTraceNode(
                node_name=node_name,
                started_nodes=started_nodes,
                both_started=both_started,
                observed_traces=observed_traces,
            ),
        )

    result = await engine.execute(
        context=RuntimeContext(
            runtime_id="runtime-1",
            workflow_id="concurrent_trace_workflow",
            execution_id="execution-1",
        ),
        execution_plan=WorkflowExecutionPlan(
            workflow_name="concurrent_trace_workflow",
            execution_id="execution-1",
            nodes={
                node_name: ExecutionPlanNode(
                    name=node_name,
                    node_type="trace_test",
                    max_retries=0,
                )
                for node_name in ("alpha", "beta")
            },
            waves=(
                ExecutionWave(
                    index=0,
                    nodes=("alpha", "beta"),
                ),
            ),
        ),
    )

    assert result.trace_context is not None
    assert started_nodes == {"alpha", "beta"}
    assert set(observed_traces) == {"alpha", "beta"}

    alpha_trace = observed_traces["alpha"]
    beta_trace = observed_traces["beta"]
    assert alpha_trace.trace_id == result.trace_context.trace_id
    assert beta_trace.trace_id == result.trace_context.trace_id
    assert alpha_trace.span_id != beta_trace.span_id
    assert alpha_trace.parent_span_id == result.trace_context.span_id
    assert beta_trace.parent_span_id == result.trace_context.span_id
    assert alpha_trace.node_name == "alpha"
    assert beta_trace.node_name == "beta"

    for node_name, trace_context in observed_traces.items():
        persisted_output = result.node_outputs[node_name]["outputs"]
        assert persisted_output == {
            "node_name": node_name,
            "trace_id": result.trace_context.trace_id,
            "span_id": trace_context.span_id,
            "parent_span_id": result.trace_context.span_id,
        }
