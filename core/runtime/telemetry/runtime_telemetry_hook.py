from __future__ import annotations

from datetime import datetime
from datetime import timezone
from types import MappingProxyType
from typing import Any, Mapping

from core.runtime.artifacts.artifact_ref import ArtifactRef
from core.runtime.events.runtime_events import RuntimeEvent
from core.runtime.events.runtime_events import RuntimeEventType
from core.runtime.lifecycle.runtime_lifecycle_hooks import (
    NoOpRuntimeLifecycleHook,
)
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.runtime.telemetry.runtime_telemetry import (
    RuntimeTelemetry,
    RuntimeTelemetryEvent,
    RuntimeTelemetryEventType,
)
from core.workflow.models.workflow_execution_plan import (
    ExecutionPlanNode,
    ExecutionWave,
    WorkflowExecutionPlan,
)


RUNTIME_EVENT_TELEMETRY_TYPE_MAP: Mapping[str, RuntimeTelemetryEventType] = (
    MappingProxyType(
        {
            RuntimeEventType.WORKFLOW_STARTED.value: RuntimeTelemetryEventType.WORKFLOW_STARTED,
            RuntimeEventType.WORKFLOW_COMPLETED.value: RuntimeTelemetryEventType.WORKFLOW_COMPLETED,
            RuntimeEventType.WORKFLOW_FAILED.value: RuntimeTelemetryEventType.WORKFLOW_FAILED,
            RuntimeEventType.WORKFLOW_CANCELLED.value: RuntimeTelemetryEventType.WORKFLOW_PROGRESS_CANCELLED,
            RuntimeEventType.WORKFLOW_PAUSED.value: RuntimeTelemetryEventType.WORKFLOW_CONTROL_PAUSED,
            RuntimeEventType.WORKFLOW_RESUMED.value: RuntimeTelemetryEventType.WORKFLOW_CONTROL_RESUMED,
            RuntimeEventType.WORKFLOW_STATE_CHANGED.value: RuntimeTelemetryEventType.WORKFLOW_CONTROL_STATE_CHANGED,
            RuntimeEventType.WORKFLOW_PROGRESS_STARTED.value: RuntimeTelemetryEventType.WORKFLOW_PROGRESS_STARTED,
            RuntimeEventType.WORKFLOW_PROGRESS_RUNNING.value: RuntimeTelemetryEventType.WORKFLOW_PROGRESS_RUNNING,
            RuntimeEventType.WORKFLOW_PROGRESS_PAUSING.value: RuntimeTelemetryEventType.WORKFLOW_CONTROL_PAUSE_REQUESTED,
            RuntimeEventType.WORKFLOW_PROGRESS_PAUSED.value: RuntimeTelemetryEventType.WORKFLOW_CONTROL_PAUSED,
            RuntimeEventType.WORKFLOW_PROGRESS_RESUMING.value: RuntimeTelemetryEventType.WORKFLOW_CONTROL_RESUME_REQUESTED,
            RuntimeEventType.WORKFLOW_PROGRESS_RESUMED.value: RuntimeTelemetryEventType.WORKFLOW_CONTROL_RESUMED,
            RuntimeEventType.WORKFLOW_PROGRESS_CANCELLING.value: RuntimeTelemetryEventType.WORKFLOW_CONTROL_CANCEL_REQUESTED,
            RuntimeEventType.WORKFLOW_PROGRESS_CANCELLED.value: RuntimeTelemetryEventType.WORKFLOW_CONTROL_CANCELLED,
            RuntimeEventType.WORKFLOW_PROGRESS_COMPLETED.value: RuntimeTelemetryEventType.WORKFLOW_PROGRESS_COMPLETED,
            RuntimeEventType.WORKFLOW_PROGRESS_FAILED.value: RuntimeTelemetryEventType.WORKFLOW_PROGRESS_FAILED,
            RuntimeEventType.EXECUTION_STARTED.value: RuntimeTelemetryEventType.WORKFLOW_PROGRESS_STARTED,
            RuntimeEventType.EXECUTION_COMPLETED.value: RuntimeTelemetryEventType.WORKFLOW_PROGRESS_COMPLETED,
            RuntimeEventType.EXECUTION_FAILED.value: RuntimeTelemetryEventType.WORKFLOW_PROGRESS_FAILED,
            RuntimeEventType.WAVE_STARTED.value: RuntimeTelemetryEventType.WAVE_STARTED,
            RuntimeEventType.WAVE_COMPLETED.value: RuntimeTelemetryEventType.WAVE_COMPLETED,
            RuntimeEventType.WAVE_FAILED.value: RuntimeTelemetryEventType.WAVE_FAILED,
            RuntimeEventType.WAVE_PROGRESS_STARTED.value: RuntimeTelemetryEventType.WAVE_PROGRESS_STARTED,
            RuntimeEventType.WAVE_PROGRESS_COMPLETED.value: RuntimeTelemetryEventType.WAVE_PROGRESS_COMPLETED,
            RuntimeEventType.WAVE_PROGRESS_FAILED.value: RuntimeTelemetryEventType.WAVE_PROGRESS_FAILED,
            RuntimeEventType.NODE_STARTED.value: RuntimeTelemetryEventType.NODE_STARTED,
            RuntimeEventType.NODE_COMPLETED.value: RuntimeTelemetryEventType.NODE_COMPLETED,
            RuntimeEventType.NODE_FAILED.value: RuntimeTelemetryEventType.NODE_FAILED,
            RuntimeEventType.NODE_SKIPPED.value: RuntimeTelemetryEventType.NODE_SKIPPED,
            RuntimeEventType.NODE_PROGRESS_STARTED.value: RuntimeTelemetryEventType.NODE_PROGRESS_STARTED,
            RuntimeEventType.NODE_PROGRESS_RUNNING.value: RuntimeTelemetryEventType.NODE_PROGRESS_RUNNING,
            RuntimeEventType.NODE_PROGRESS_COMPLETED.value: RuntimeTelemetryEventType.NODE_PROGRESS_COMPLETED,
            RuntimeEventType.NODE_PROGRESS_SKIPPED.value: RuntimeTelemetryEventType.NODE_PROGRESS_SKIPPED,
            RuntimeEventType.NODE_PROGRESS_FAILED.value: RuntimeTelemetryEventType.NODE_PROGRESS_FAILED,
            RuntimeEventType.CHECKPOINT_CREATED.value: RuntimeTelemetryEventType.CHECKPOINT_CREATED,
            RuntimeEventType.CHECKPOINT_RESTORED.value: RuntimeTelemetryEventType.CHECKPOINT_RESTORED,
            RuntimeEventType.CHECKPOINT_FAILED.value: RuntimeTelemetryEventType.CHECKPOINT_FAILED,
            RuntimeEventType.REPLAY_STARTED.value: RuntimeTelemetryEventType.REPLAY_STARTED,
            RuntimeEventType.REPLAY_COMPLETED.value: RuntimeTelemetryEventType.REPLAY_COMPLETED,
            RuntimeEventType.REPLAY_FAILED.value: RuntimeTelemetryEventType.REPLAY_FAILED,
            "checkpoint.created": RuntimeTelemetryEventType.CHECKPOINT_CREATED,
            "checkpoint.restored": RuntimeTelemetryEventType.CHECKPOINT_RESTORED,
            "checkpoint.failed": RuntimeTelemetryEventType.CHECKPOINT_FAILED,
            "replay.started": RuntimeTelemetryEventType.REPLAY_STARTED,
            "replay.completed": RuntimeTelemetryEventType.REPLAY_COMPLETED,
            "replay.failed": RuntimeTelemetryEventType.REPLAY_FAILED,
        }
    )
)


LIFECYCLE_EQUIVALENT_RUNTIME_EVENT_TYPES: frozenset[RuntimeEventType] = frozenset(
    {
        RuntimeEventType.WORKFLOW_STARTED,
        RuntimeEventType.WORKFLOW_COMPLETED,
        RuntimeEventType.WORKFLOW_FAILED,
        RuntimeEventType.WAVE_STARTED,
        RuntimeEventType.WAVE_COMPLETED,
        RuntimeEventType.WAVE_FAILED,
        RuntimeEventType.NODE_STARTED,
        RuntimeEventType.NODE_COMPLETED,
        RuntimeEventType.NODE_FAILED,
        RuntimeEventType.NODE_SKIPPED,
    }
)


class RuntimeTelemetryHook(NoOpRuntimeLifecycleHook):
    """
    Runtime lifecycle hook that emits runtime telemetry events.

    Bridges RuntimeLifecycleManager into RuntimeTelemetry.
    """

    def __init__(
        self,
        telemetry: RuntimeTelemetry,
    ) -> None:
        self.telemetry = telemetry

        self._workflow_started_at: dict[str, datetime] = {}
        self._wave_started_at: dict[str, datetime] = {}
        self._node_started_at: dict[str, datetime] = {}

    def _trace_payload(
        self,
        context: RuntimeContext,
    ) -> dict[str, Any]:
        if context.trace_context is None:
            return {}

        return context.trace_context.telemetry_attributes()

    # ========================================================
    # WORKFLOW
    # ========================================================

    async def before_workflow_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
    ) -> None:
        key = self._workflow_key(
            context,
        )

        started_at = datetime.now(
            timezone.utc,
        )

        self._workflow_started_at[key] = started_at

        await self.telemetry.emit(
            RuntimeTelemetryEvent(
                event_type=RuntimeTelemetryEventType.WORKFLOW_STARTED,
                workflow_id=context.workflow_id,
                execution_id=context.execution_id,
                runtime_id=context.runtime_id,
                timestamp=started_at,
                payload={
                    "workflow_name": execution_plan.workflow_name,
                    "node_count": execution_plan.total_nodes(),
                    "wave_count": execution_plan.total_waves(),
                    "context_version": context.context_version,
                    **self._trace_payload(
                        context,
                    ),
                },
            )
        )

    async def after_workflow_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
    ) -> None:
        completed_at = datetime.now(
            timezone.utc,
        )

        started_at = self._workflow_started_at.pop(
            self._workflow_key(
                context,
            ),
            completed_at,
        )

        success = not bool(
            context.errors,
        )

        await self.telemetry.emit(
            RuntimeTelemetryEvent(
                event_type=(
                    RuntimeTelemetryEventType.WORKFLOW_COMPLETED
                    if success
                    else RuntimeTelemetryEventType.WORKFLOW_FAILED
                ),
                workflow_id=context.workflow_id,
                execution_id=context.execution_id,
                runtime_id=context.runtime_id,
                timestamp=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
                success=success,
                error_count=len(context.errors),
                payload={
                    "workflow_name": execution_plan.workflow_name,
                    "context_version": context.context_version,
                    "node_output_count": len(context.node_outputs),
                    "artifact_ref_count": len(context.artifact_refs),
                    **self._trace_payload(
                        context,
                    ),
                },
            )
        )

    # ========================================================
    # WAVE
    # ========================================================

    async def before_wave_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
        wave: ExecutionWave,
    ) -> None:
        key = self._wave_key(
            context=context,
            wave_index=wave.index,
        )

        started_at = datetime.now(
            timezone.utc,
        )

        self._wave_started_at[key] = started_at

        await self.telemetry.emit(
            RuntimeTelemetryEvent(
                event_type=RuntimeTelemetryEventType.WAVE_STARTED,
                workflow_id=context.workflow_id,
                execution_id=context.execution_id,
                runtime_id=context.runtime_id,
                wave_index=wave.index,
                timestamp=started_at,
                payload={
                    "workflow_name": execution_plan.workflow_name,
                    "nodes": list(wave.nodes),
                    "context_version": context.context_version,
                    **self._trace_payload(
                        context,
                    ),
                },
            )
        )

    async def after_wave_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
        wave: ExecutionWave,
    ) -> None:
        completed_at = datetime.now(
            timezone.utc,
        )

        started_at = self._wave_started_at.pop(
            self._wave_key(
                context=context,
                wave_index=wave.index,
            ),
            completed_at,
        )

        await self.telemetry.emit(
            RuntimeTelemetryEvent(
                event_type=RuntimeTelemetryEventType.WAVE_COMPLETED,
                workflow_id=context.workflow_id,
                execution_id=context.execution_id,
                runtime_id=context.runtime_id,
                wave_index=wave.index,
                timestamp=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
                payload={
                    "workflow_name": execution_plan.workflow_name,
                    "nodes": list(wave.nodes),
                    "context_version": context.context_version,
                    **self._trace_payload(
                        context,
                    ),
                },
            )
        )

    # ========================================================
    # NODE
    # ========================================================

    async def before_node_execute(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
    ) -> None:
        key = self._node_key(
            context=context,
            node_name=plan_node.name,
        )

        started_at = datetime.now(
            timezone.utc,
        )

        self._node_started_at[key] = started_at

        await self.telemetry.emit(
            RuntimeTelemetryEvent(
                event_type=RuntimeTelemetryEventType.NODE_STARTED,
                workflow_id=context.workflow_id,
                execution_id=context.execution_id,
                runtime_id=context.runtime_id,
                node_name=plan_node.name,
                timestamp=started_at,
                payload={
                    "node_type": plan_node.node_type,
                    "dependencies": list(plan_node.dependencies),
                    "context_version": context.context_version,
                    **self._trace_payload(
                        context,
                    ),
                },
            )
        )

    async def after_node_execute(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
        output: RuntimeNodeOutput,
    ) -> None:
        completed_at = datetime.now(
            timezone.utc,
        )

        started_at = self._node_started_at.pop(
            self._node_key(
                context=context,
                node_name=plan_node.name,
            ),
            completed_at,
        )

        if output.skipped:
            event_type = RuntimeTelemetryEventType.NODE_SKIPPED
        elif output.success:
            event_type = RuntimeTelemetryEventType.NODE_COMPLETED
        else:
            event_type = RuntimeTelemetryEventType.NODE_FAILED

        await self.telemetry.emit(
            RuntimeTelemetryEvent(
                event_type=event_type,
                workflow_id=context.workflow_id,
                execution_id=context.execution_id,
                runtime_id=context.runtime_id,
                node_name=plan_node.name,
                wave_index=output.execution_metadata.get(
                    "wave_index",
                ),
                timestamp=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
                success=output.success,
                error_count=len(output.errors),
                payload={
                    "node_type": plan_node.node_type,
                    "skipped": output.skipped,
                    "stop_propagation": output.stop_propagation,
                    "attempt": output.execution_metadata.get("attempt"),
                    "max_attempts": output.execution_metadata.get("max_attempts"),
                    "artifact_count": len(output.artifacts),
                    "errors": list(output.errors),
                    **self._trace_payload(
                        context,
                    ),
                },
            )
        )

    # ========================================================
    # ARTIFACTS
    # ========================================================

    async def on_artifact_persisted(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
        artifact_name: str,
        artifact_ref: ArtifactRef,
    ) -> None:
        await self.telemetry.emit(
            RuntimeTelemetryEvent(
                event_type=RuntimeTelemetryEventType.ARTIFACT_PERSISTED,
                workflow_id=context.workflow_id,
                execution_id=context.execution_id,
                runtime_id=context.runtime_id,
                node_name=plan_node.name,
                timestamp=datetime.now(timezone.utc),
                success=True,
                payload={
                    "artifact_name": artifact_name,
                    "artifact": artifact_ref.to_dict(),
                    "artifact_id": artifact_ref.artifact_id,
                    "artifact_kind": artifact_ref.kind.value,
                    "artifact_uri": artifact_ref.uri,
                    "content_type": artifact_ref.content_type,
                    "size_bytes": artifact_ref.size_bytes,
                    "checksum": artifact_ref.checksum,
                    **self._trace_payload(
                        context,
                    ),
                },
            )
        )

    async def on_artifact_failed(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
        artifact_name: str,
        error: Exception,
    ) -> None:
        await self.telemetry.emit(
            RuntimeTelemetryEvent(
                event_type=RuntimeTelemetryEventType.ARTIFACT_FAILED,
                workflow_id=context.workflow_id,
                execution_id=context.execution_id,
                runtime_id=context.runtime_id,
                node_name=plan_node.name,
                timestamp=datetime.now(timezone.utc),
                success=False,
                error_count=1,
                payload={
                    "artifact_name": artifact_name,
                    "error_type": type(error).__name__,
                    "message": str(error),
                    **self._trace_payload(
                        context,
                    ),
                },
            )
        )

    # ========================================================
    # RUNTIME EVENTS
    # ========================================================

    async def on_runtime_event(
        self,
        event: RuntimeEvent,
    ) -> None:
        if self._is_lifecycle_equivalent_runtime_event(
            event,
        ):
            return

        success = self._runtime_event_success(
            event,
        )
        error_count = self._runtime_event_error_count(
            event,
        )

        await self.telemetry.emit(
            RuntimeTelemetryEvent(
                event_type=self._map_runtime_event_type(
                    event.event_type.value,
                ),
                workflow_id=event.workflow_id,
                execution_id=event.execution_id,
                runtime_id=event.runtime_id,
                node_name=event.node_name,
                wave_index=event.wave_index,
                timestamp=event.timestamp,
                success=success,
                error_count=error_count,
                payload={
                    "runtime_event": event.to_dict(),
                    **self._runtime_event_trace_payload(
                        event,
                    ),
                },
            )
        )

    # ========================================================
    # INTERNALS
    # ========================================================

    def _workflow_key(
        self,
        context: RuntimeContext,
    ) -> str:
        return context.execution_id

    def _wave_key(
        self,
        context: RuntimeContext,
        wave_index: int,
    ) -> str:
        return f"{context.execution_id}:{wave_index}"

    def _node_key(
        self,
        context: RuntimeContext,
        node_name: str,
    ) -> str:
        return f"{context.execution_id}:{node_name}"

    def _map_runtime_event_type(
        self,
        runtime_event_type: str,
    ) -> RuntimeTelemetryEventType:
        return RUNTIME_EVENT_TELEMETRY_TYPE_MAP.get(
            runtime_event_type,
            RuntimeTelemetryEventType.RUNTIME_EVENT,
        )

    def _is_lifecycle_equivalent_runtime_event(
        self,
        event: RuntimeEvent,
    ) -> bool:
        return event.event_type in LIFECYCLE_EQUIVALENT_RUNTIME_EVENT_TYPES

    def _runtime_event_success(
        self,
        event: RuntimeEvent,
    ) -> bool | None:
        payload_success = event.payload.get(
            "success",
        )
        if isinstance(
            payload_success,
            bool,
        ):
            return payload_success

        if event.is_error:
            return False

        if event.is_terminal:
            return True

        return None

    def _runtime_event_trace_payload(
        self,
        event: RuntimeEvent,
    ) -> dict[str, str]:
        trace_payload: dict[str, str] = {}
        for key in ("trace_id", "span_id", "parent_span_id"):
            value = event.payload.get(key, event.metadata.get(key))
            if isinstance(value, str) and value:
                trace_payload[key] = value
        return trace_payload

    def _runtime_event_error_count(
        self,
        event: RuntimeEvent,
    ) -> int:
        payload_error_count = event.payload.get(
            "error_count",
        )
        if isinstance(
            payload_error_count,
            int,
        ):
            return payload_error_count

        if event.is_error:
            return 1

        return 0
