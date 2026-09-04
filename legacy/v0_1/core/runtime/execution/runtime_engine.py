from __future__ import annotations

from typing import ClassVar

from core.runtime.artifacts.artifact_manager import ArtifactManager
from core.runtime.checkpoints.checkpoint_manager import CheckpointManager
from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.control import WorkflowControlManager
from core.runtime.events import EventBus, RuntimeEventType
from core.runtime.execution.runtime_context_transitions import (
    CANCELLED_WORKFLOW_OUTPUT_NAME,
    RuntimeContextTransitions,
)
from core.runtime.execution.runtime_event_publisher import RuntimeEventPublisher
from core.runtime.execution.runtime_execution_context import (
    RuntimeExecutionLocation,
)
from core.runtime.execution.runtime_node_executor import RuntimeNodeExecutor
from core.runtime.execution.runtime_wave_executor import RuntimeWaveExecutor
from core.runtime.lifecycle.runtime_lifecycle_manager import RuntimeLifecycleManager
from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.workflow.models.workflow_execution_plan import (
    ExecutionWave,
    WorkflowExecutionPlan,
)


class RuntimeEngine:
    """Deterministic runtime execution engine."""

    CANCELLED_WORKFLOW_OUTPUT_NAME: ClassVar[str] = CANCELLED_WORKFLOW_OUTPUT_NAME

    def __init__(
        self,
        lifecycle_manager: RuntimeLifecycleManager | None = None,
        artifact_manager: ArtifactManager | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        checkpoint_on_wave_completion: bool = False,
        control_manager: WorkflowControlManager | None = None,
        event_bus: EventBus | None = None,
        observability_manager: ObservabilityManager | None = None,
    ) -> None:
        self.nodes: dict[str, RuntimeNode] = {}
        self.lifecycle_manager = lifecycle_manager or RuntimeLifecycleManager()
        self.artifact_manager = artifact_manager
        self.checkpoint_manager = checkpoint_manager
        self.checkpoint_on_wave_completion = checkpoint_on_wave_completion
        self.control_manager = control_manager or WorkflowControlManager(
            event_bus=event_bus,
        )
        self.event_bus = event_bus or self.control_manager.event_bus
        self.observability_manager = observability_manager or ObservabilityManager()

        self._context_transitions = RuntimeContextTransitions()
        self._event_publisher = RuntimeEventPublisher(
            control_manager=self.control_manager,
            event_bus=self.event_bus,
        )
        self._node_executor = RuntimeNodeExecutor(
            event_publisher=self._event_publisher,
            context_transitions=self._context_transitions,
            lifecycle_manager=self.lifecycle_manager,
        )
        self._wave_executor = RuntimeWaveExecutor(
            nodes=self.nodes,
            lifecycle_manager=self.lifecycle_manager,
            artifact_manager=self.artifact_manager,
            control_manager=self.control_manager,
            event_publisher=self._event_publisher,
            node_executor=self._node_executor,
            context_transitions=self._context_transitions,
        )

    def clear_nodes(self) -> None:
        self.nodes.clear()

    def register(
        self,
        node_name: str,
        node: RuntimeNode,
    ) -> None:
        self.nodes[node_name] = node

    def register_many(
        self,
        nodes: dict[str, RuntimeNode],
        clear_existing: bool = True,
    ) -> None:
        if clear_existing:
            self.clear_nodes()
        for node_name, node in nodes.items():
            self.register(
                node_name=node_name,
                node=node,
            )

    def _ensure_root_trace_context(
        self,
        *,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
    ) -> RuntimeContext:
        if context.trace_context is not None:
            return context

        trace_context = self.observability_manager.create_trace_context(
            workflow_id=context.workflow_id,
            execution_id=context.execution_id,
            runtime_id=context.runtime_id,
            correlation_id=context.execution_id,
            attributes={
                "workflow_name": execution_plan.workflow_name,
                "operation_kind": "workflow_execution",
            },
        )
        return context.with_trace_context(trace_context)

    async def execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
        checkpoint_on_wave_completion: bool | None = None,
    ) -> RuntimeContext:
        execution_plan.validate()
        current_context = self._ensure_root_trace_context(
            context=context,
            execution_plan=execution_plan,
        )
        workflow_location = RuntimeExecutionLocation(
            context=current_context,
            execution_plan=execution_plan,
        )
        control_metadata = self._event_publisher.control_metadata(workflow_location)

        await self.control_manager.initialize_execution(
            execution_plan.execution_id,
            metadata=control_metadata,
        )
        await self._event_publisher.emit_progress_event(
            event_type=RuntimeEventType.WORKFLOW_PROGRESS_STARTED,
            location=workflow_location,
        )
        await self.control_manager.mark_running(
            execution_plan.execution_id,
            metadata=control_metadata,
        )

        should_checkpoint_waves = (
            self.checkpoint_on_wave_completion
            if checkpoint_on_wave_completion is None
            else checkpoint_on_wave_completion
        )

        try:
            await self.lifecycle_manager.before_workflow_execute(
                context=current_context,
                execution_plan=execution_plan,
            )
            for wave in execution_plan.waves:
                await self.control_manager.wait_if_paused(execution_plan.execution_id)
                wave_location = workflow_location.with_context(
                    current_context
                ).for_wave(wave.index)
                (
                    current_context,
                    was_cancelled,
                ) = await self._wave_executor.apply_cancel_if_requested(
                    location=wave_location,
                    boundary="before_wave",
                )
                if was_cancelled:
                    break

                wave_location = wave_location.with_context(current_context)
                await self._event_publisher.emit_progress_event(
                    event_type=RuntimeEventType.WAVE_PROGRESS_STARTED,
                    location=wave_location,
                    payload={"wave_nodes": list(wave.nodes)},
                )
                await self.lifecycle_manager.before_wave_execute(
                    context=current_context,
                    execution_plan=execution_plan,
                    wave=wave,
                )
                current_context = await self._wave_executor.execute(
                    location=wave_location,
                    node_names=list(wave.nodes),
                )
                await self.lifecycle_manager.after_wave_execute(
                    context=current_context,
                    execution_plan=execution_plan,
                    wave=wave,
                )
                terminal_location = wave_location.with_context(current_context)
                await self._event_publisher.emit_progress_event(
                    event_type=(
                        self._context_transitions.wave_progress_terminal_event_type(
                            context=current_context,
                            wave=wave,
                        )
                    ),
                    location=terminal_location,
                    payload={"wave_nodes": list(wave.nodes)},
                )
                if should_checkpoint_waves:
                    await self._save_wave_checkpoint_safe(
                        context=current_context,
                        execution_plan=execution_plan,
                        wave=wave,
                    )
                if self._context_transitions.should_stop_execution(current_context):
                    break

            await self.lifecycle_manager.after_workflow_execute(
                context=current_context,
                execution_plan=execution_plan,
            )
        except Exception as exc:
            await self.control_manager.mark_failed(
                execution_plan.execution_id,
                reason=str(exc),
                metadata={
                    **control_metadata,
                    "error_type": type(exc).__name__,
                },
            )
            raise

        terminal_location = workflow_location.with_context(current_context)
        terminal_metadata = self._event_publisher.control_metadata(terminal_location)
        if self.control_manager.should_cancel(execution_plan.execution_id):
            return current_context

        if self._context_transitions.has_execution_failure(current_context):
            await self.control_manager.mark_failed(
                execution_plan.execution_id,
                reason="workflow execution completed with failures",
                metadata=terminal_metadata,
            )
        else:
            await self.control_manager.mark_completed(
                execution_plan.execution_id,
                metadata=terminal_metadata,
            )
        return current_context

    async def _save_wave_checkpoint_safe(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
        wave: ExecutionWave,
    ) -> None:
        if self.checkpoint_manager is None:
            return

        try:
            checkpoint_name = (
                f"{execution_plan.workflow_name}_"
                f"{context.execution_id}_wave_{wave.index}"
            )
            await self.checkpoint_manager.save_checkpoint(
                context=context,
                checkpoint_name=checkpoint_name,
                wave_index=wave.index,
                completed_nodes=tuple(
                    self._context_transitions.completed_nodes(context)
                ),
                failed_nodes=tuple(self._context_transitions.failed_nodes(context)),
                skipped_nodes=tuple(self._context_transitions.skipped_nodes(context)),
                metadata={
                    "workflow_name": execution_plan.workflow_name,
                    "execution_id": execution_plan.execution_id,
                    "wave_index": wave.index,
                    "wave_nodes": list(wave.nodes),
                    "checkpoint_reason": "wave_completion",
                    "context_version": context.context_version,
                },
            )
        except Exception:
            return
