from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Any

from core.runtime.control import WorkflowControlManager
from core.runtime.events import EventBus
from core.runtime.events import RuntimeEvent
from core.runtime.events import RuntimeEventType
from core.runtime.execution.runtime_execution_context import (
    RuntimeExecutionLocation,
)
from core.runtime.state.runtime_node_output import RuntimeNodeOutput


class RuntimeEventPublisher:
    """Publishes canonical runtime node and progress events through EventBus."""

    def __init__(
        self,
        *,
        control_manager: WorkflowControlManager,
        event_bus: EventBus | None,
    ) -> None:
        self._control_manager = control_manager
        self._event_bus = event_bus

    def control_metadata(
        self,
        location: RuntimeExecutionLocation,
    ) -> dict[str, object]:
        context = location.context
        execution_plan = location.execution_plan
        metadata: dict[str, object] = {
            "workflow_id": context.workflow_id,
            "workflow_name": execution_plan.workflow_name,
            "runtime_id": context.runtime_id,
            "execution_id": execution_plan.execution_id,
            "mode": context.mode,
            "total_waves": execution_plan.total_waves(),
            "total_nodes": execution_plan.total_nodes(),
            "context_version": context.context_version,
        }
        if context.trace_context is not None:
            metadata.update(context.trace_context.telemetry_attributes())
        return metadata

    async def emit_node_event(
        self,
        *,
        event_type: RuntimeEventType,
        location: RuntimeExecutionLocation,
        output: RuntimeNodeOutput,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if self._event_bus is None or location.plan_node is None:
            return

        context = location.context
        execution_plan = location.execution_plan
        plan_node = location.plan_node
        timestamp = datetime.now(timezone.utc)
        event_payload: dict[str, Any] = {
            "workflow_id": context.workflow_id,
            "workflow_name": execution_plan.workflow_name,
            "execution_id": execution_plan.execution_id,
            "runtime_id": context.runtime_id,
            "node_name": plan_node.name,
            "node_type": plan_node.node_type,
            "wave_index": location.wave_index,
            "success": output.success,
            "skipped": output.skipped,
            "error_count": len(output.errors),
            "errors": list(output.errors),
            "context_version": context.context_version,
            "timestamp": timestamp.isoformat(),
        }
        if context.trace_context is not None:
            event_payload.update(context.trace_context.telemetry_attributes())
        if payload:
            event_payload.update(payload)

        event_metadata = {
            **self.control_metadata(location),
            "node_type": plan_node.node_type,
        }
        if context.trace_context is not None:
            event_metadata.update(context.trace_context.telemetry_attributes())

        await self._event_bus.emit(
            RuntimeEvent(
                event_type=event_type,
                execution_id=execution_plan.execution_id,
                workflow_id=context.workflow_id,
                runtime_id=context.runtime_id,
                timestamp=timestamp,
                node_name=plan_node.name,
                wave_index=location.wave_index,
                payload=event_payload,
                metadata=event_metadata,
            )
        )

    async def emit_node_output_events(
        self,
        *,
        location: RuntimeExecutionLocation,
        output: RuntimeNodeOutput,
    ) -> None:
        if (
            self._event_bus is None
            or location.plan_node is None
            or not output.emitted_events
        ):
            return

        for event in output.emitted_events:
            await self._event_bus.emit(
                self._with_runtime_location(
                    event=event,
                    location=location,
                )
            )

    async def emit_progress_event(
        self,
        *,
        event_type: RuntimeEventType,
        location: RuntimeExecutionLocation,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._event_bus is None:
            return

        context = location.context
        execution_plan = location.execution_plan
        timestamp = datetime.now(timezone.utc)
        control_metadata = self.control_metadata(location)
        event_payload: dict[str, Any] = {
            "workflow_id": context.workflow_id,
            "workflow_name": execution_plan.workflow_name,
            "execution_id": execution_plan.execution_id,
            "runtime_id": context.runtime_id,
            "state": self._control_manager.get_state(execution_plan.execution_id).value,
            "node_name": location.node_name,
            "wave_index": location.wave_index,
            "timestamp": timestamp.isoformat(),
            "context_version": context.context_version,
            "metadata": dict(control_metadata),
        }
        if context.trace_context is not None:
            event_payload.update(context.trace_context.telemetry_attributes())
        if payload:
            event_payload.update(payload)

        event_metadata = dict(control_metadata)
        if context.trace_context is not None:
            event_metadata.update(context.trace_context.telemetry_attributes())
        if metadata:
            event_metadata.update(metadata)

        await self._event_bus.emit(
            RuntimeEvent(
                event_type=event_type,
                execution_id=execution_plan.execution_id,
                workflow_id=context.workflow_id,
                runtime_id=context.runtime_id,
                timestamp=timestamp,
                node_name=location.node_name,
                wave_index=location.wave_index,
                payload=event_payload,
                metadata=event_metadata,
            )
        )

    @staticmethod
    def _with_runtime_location(
        *,
        event: RuntimeEvent,
        location: RuntimeExecutionLocation,
    ) -> RuntimeEvent:
        context = location.context
        execution_plan = location.execution_plan
        return RuntimeEvent(
            event_type=event.event_type,
            execution_id=event.execution_id or execution_plan.execution_id,
            workflow_id=event.workflow_id or context.workflow_id,
            runtime_id=event.runtime_id or context.runtime_id,
            timestamp=event.timestamp,
            node_name=event.node_name or location.node_name,
            wave_index=(
                event.wave_index
                if event.wave_index is not None
                else location.wave_index
            ),
            payload={
                **(
                    context.trace_context.telemetry_attributes()
                    if context.trace_context is not None
                    else {}
                ),
                **event.payload,
            },
            metadata={
                **(
                    context.trace_context.telemetry_attributes()
                    if context.trace_context is not None
                    else {}
                ),
                **event.metadata,
            },
        )
