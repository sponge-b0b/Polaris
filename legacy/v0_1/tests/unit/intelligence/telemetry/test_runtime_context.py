from __future__ import annotations

from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.tracing.trace_context import TraceContext
from intelligence.telemetry import telemetry_context_from_runtime


def test_telemetry_context_from_runtime_uses_runtime_identifiers() -> None:
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="workflow-1",
        execution_id="execution-1",
        mode="replay",
    )

    telemetry_context = telemetry_context_from_runtime(
        context,
        node_name="technical_agent",
        attributes={
            "operation": "technical.analysis.execute",
        },
    )

    assert telemetry_context.workflow_id == "workflow-1"
    assert telemetry_context.execution_id == "execution-1"
    assert telemetry_context.runtime_id == "runtime-1"
    assert telemetry_context.node_name == "technical_agent"
    assert telemetry_context.correlation_id == "execution-1"
    assert telemetry_context.tags == (
        "runtime",
        "intelligence",
    )
    assert telemetry_context.attributes == {
        "runtime_mode": "replay",
        "operation": "technical.analysis.execute",
    }


def test_telemetry_context_from_runtime_preserves_trace_identity() -> None:
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="workflow-1",
        execution_id="execution-1",
        mode="live",
        trace_context=TraceContext(
            trace_id="trace-1",
            span_id="node-span-1",
            parent_span_id="workflow-span-1",
            correlation_id="correlation-1",
            workflow_id="workflow-1",
            execution_id="execution-1",
            runtime_id="runtime-1",
            node_name="runtime_node",
            attributes={
                "trace_scope": "runtime_node",
            },
        ),
    )

    telemetry_context = telemetry_context_from_runtime(
        context,
        node_name="technical_agent",
        attributes={
            "operation": "technical.analysis.execute",
        },
    )

    assert telemetry_context.workflow_id == "workflow-1"
    assert telemetry_context.execution_id == "execution-1"
    assert telemetry_context.runtime_id == "runtime-1"
    assert telemetry_context.node_name == "technical_agent"
    assert telemetry_context.correlation_id == "correlation-1"
    assert telemetry_context.trace_id == "trace-1"
    assert telemetry_context.span_id == "node-span-1"
    assert telemetry_context.parent_span_id == "workflow-span-1"
    assert telemetry_context.attributes == {
        "trace_scope": "runtime_node",
        "runtime_mode": "live",
        "operation": "technical.analysis.execute",
    }
