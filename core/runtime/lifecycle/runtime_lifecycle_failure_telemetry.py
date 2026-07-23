from __future__ import annotations

from core.runtime.lifecycle.runtime_lifecycle_failure import (
    RuntimeLifecycleFailureContext,
)
from core.runtime.lifecycle.runtime_lifecycle_hooks import RuntimeLifecycleHook
from core.telemetry.events.telemetry_event import TelemetryEvent, TelemetryEventLevel
from core.telemetry.events.telemetry_exception_details import (
    TelemetryExceptionDetails,
)
from core.telemetry.observability.observability_manager import ObservabilityManager


class RuntimeLifecycleFailureTelemetry:
    def __init__(
        self,
        observability_manager: ObservabilityManager,
        source: str = "runtime.lifecycle",
    ) -> None:
        self._observability_manager = observability_manager
        self._source = source

    async def emit_hook_failure(
        self,
        context: RuntimeLifecycleFailureContext,
        hook: RuntimeLifecycleHook,
        error: BaseException,
    ) -> None:
        trace_context = context.trace_context
        await self._observability_manager.emit(
            TelemetryEvent(
                event_type="runtime.lifecycle.hook_failed",
                source=self._source,
                level=TelemetryEventLevel.ERROR,
                workflow_id=context.workflow_id,
                execution_id=context.execution_id,
                runtime_id=context.runtime_id,
                node_name=context.node_name,
                correlation_id=(
                    trace_context.correlation_id if trace_context is not None else None
                ),
                trace_id=(
                    trace_context.trace_id if trace_context is not None else None
                ),
                span_id=(trace_context.span_id if trace_context is not None else None),
                parent_span_id=(
                    trace_context.parent_span_id if trace_context is not None else None
                ),
                success=False,
                error_count=1,
                exception_details=TelemetryExceptionDetails.from_exception(error),
                payload={
                    "lifecycle_event": context.lifecycle_event,
                    "hook": hook.__class__.__name__,
                    "original_event_type": context.original_event_type,
                },
            )
        )
