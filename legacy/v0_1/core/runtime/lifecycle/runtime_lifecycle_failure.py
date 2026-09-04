from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from core.runtime.events.runtime_events import RuntimeEvent
from core.runtime.lifecycle.runtime_lifecycle_hooks import RuntimeLifecycleHook
from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.tracing.trace_context import TraceContext


@dataclass(frozen=True, slots=True)
class RuntimeLifecycleFailureContext:
    lifecycle_event: str
    workflow_id: str
    execution_id: str
    runtime_id: str | None = None
    node_name: str | None = None
    trace_context: TraceContext | None = None
    original_event_type: str | None = None

    @classmethod
    def from_runtime_context(
        cls,
        *,
        lifecycle_event: str,
        context: RuntimeContext,
        node_name: str | None = None,
    ) -> RuntimeLifecycleFailureContext:
        return cls(
            lifecycle_event=lifecycle_event,
            workflow_id=context.workflow_id,
            execution_id=context.execution_id,
            runtime_id=context.runtime_id,
            node_name=node_name,
            trace_context=context.trace_context,
        )

    @classmethod
    def from_runtime_event(
        cls,
        *,
        lifecycle_event: str,
        event: RuntimeEvent,
    ) -> RuntimeLifecycleFailureContext:
        trace_data = {
            key: event.payload.get(key, event.metadata.get(key))
            for key in ("trace_id", "span_id", "parent_span_id")
        }
        trace_context = None
        if isinstance(trace_data["trace_id"], str) and isinstance(
            trace_data["span_id"], str
        ):
            trace_context = TraceContext(
                trace_id=trace_data["trace_id"],
                span_id=trace_data["span_id"],
                parent_span_id=(
                    trace_data["parent_span_id"]
                    if isinstance(trace_data["parent_span_id"], str)
                    else None
                ),
                workflow_id=event.workflow_id,
                execution_id=event.execution_id,
                runtime_id=event.runtime_id,
                node_name=event.node_name,
            )
        return cls(
            lifecycle_event=lifecycle_event,
            workflow_id=event.workflow_id,
            execution_id=event.execution_id,
            runtime_id=event.runtime_id,
            node_name=event.node_name,
            trace_context=trace_context,
            original_event_type=event.event_type.value,
        )


RuntimeLifecycleFailureHandler = Callable[
    [RuntimeLifecycleFailureContext, RuntimeLifecycleHook, BaseException],
    Awaitable[None],
]
