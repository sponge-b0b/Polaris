from __future__ import annotations

from typing import Any

from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.contracts.telemetry_context import TelemetryContext


def telemetry_context_from_runtime(
    context: RuntimeContext,
    *,
    node_name: str,
    attributes: dict[str, Any] | None = None,
) -> TelemetryContext:
    """
    Build service telemetry attribution from the active runtime node context.
    """

    trace_context = context.trace_context

    return TelemetryContext(
        workflow_id=context.workflow_id,
        execution_id=context.execution_id,
        runtime_id=context.runtime_id,
        node_name=node_name,
        correlation_id=(
            trace_context.correlation_id
            if trace_context is not None and trace_context.correlation_id is not None
            else context.execution_id
        ),
        tags=(
            "runtime",
            "intelligence",
        ),
        attributes={
            **dict(trace_context.attributes if trace_context is not None else {}),
            "runtime_mode": context.mode,
            **dict(attributes or {}),
        },
        trace_id=trace_context.trace_id if trace_context is not None else None,
        span_id=trace_context.span_id if trace_context is not None else None,
        parent_span_id=(
            trace_context.parent_span_id if trace_context is not None else None
        ),
    )
