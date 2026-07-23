from __future__ import annotations

import asyncio
from typing import Any

from core.runtime.artifacts.artifact_manager import ArtifactManager
from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.control import WorkflowControlManager, WorkflowControlState
from core.runtime.events import RuntimeEventType
from core.runtime.execution.runtime_context_transitions import (
    CANCELLED_WORKFLOW_OUTPUT_NAME,
    RuntimeContextTransitions,
)
from core.runtime.execution.runtime_event_publisher import RuntimeEventPublisher
from core.runtime.execution.runtime_execution_context import (
    RuntimeExecutionLocation,
    RuntimeNodeExecutionResult,
    RuntimeNodeInvocation,
)
from core.runtime.execution.runtime_node_executor import RuntimeNodeExecutor
from core.runtime.lifecycle.runtime_lifecycle_manager import RuntimeLifecycleManager
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput


class RuntimeWaveExecutor:
    """Schedules and finalizes one deterministic runtime execution wave."""

    def __init__(
        self,
        *,
        nodes: dict[str, RuntimeNode],
        lifecycle_manager: RuntimeLifecycleManager,
        artifact_manager: ArtifactManager | None,
        control_manager: WorkflowControlManager,
        event_publisher: RuntimeEventPublisher,
        node_executor: RuntimeNodeExecutor,
        context_transitions: RuntimeContextTransitions,
    ) -> None:
        self._nodes = nodes
        self._lifecycle_manager = lifecycle_manager
        self._artifact_manager = artifact_manager
        self._control_manager = control_manager
        self._event_publisher = event_publisher
        self._node_executor = node_executor
        self._context_transitions = context_transitions

    async def execute(
        self,
        *,
        location: RuntimeExecutionLocation,
        node_names: list[str],
    ) -> RuntimeContext:
        if location.wave_index is None:
            raise ValueError("Runtime wave execution requires a wave index.")

        tasks: list[asyncio.Task[RuntimeNodeExecutionResult]] = []
        task_locations: list[RuntimeExecutionLocation] = []
        updated_context = location.context

        for node_name in node_names:
            await self._control_manager.wait_if_paused(
                location.execution_plan.execution_id
            )
            current_location = location.with_context(updated_context)
            updated_context, was_cancelled = await self.apply_cancel_if_requested(
                location=current_location,
                boundary="before_node",
                node_name=node_name,
            )
            if was_cancelled:
                break

            plan_node = location.execution_plan.get_node(node_name)
            node_location = current_location.for_node(
                plan_node,
                context=updated_context,
            )
            if not plan_node.enabled:
                updated_context = await self._mark_skipped(
                    location=node_location,
                    reason="node_disabled",
                )
                continue

            if not self._context_transitions.dependencies_succeeded(
                context=updated_context,
                plan_node=plan_node,
            ):
                updated_context = await self._mark_skipped(
                    location=node_location,
                    reason="dependency_failed",
                )
                continue

            runtime_node = self._nodes.get(node_name)
            if runtime_node is None:
                updated_context = await self._mark_failure(
                    location=node_location,
                    error_type="NodeRegistrationError",
                    message=f"Runtime node is not registered: {node_name}",
                )
                continue

            max_attempts = max(1, plan_node.max_retries + 1)
            first_attempt_location = await self._node_executor.prepare_attempt(
                location=node_location,
                attempt=1,
                max_attempts=max_attempts,
            )
            tasks.append(
                asyncio.create_task(
                    self._node_executor.execute(
                        RuntimeNodeInvocation(
                            node=runtime_node,
                            location=node_location,
                        ),
                        prepared_first_attempt=first_attempt_location,
                    )
                )
            )
            task_locations.append(first_attempt_location)

        if not tasks:
            return updated_context

        results: list[
            RuntimeNodeExecutionResult | BaseException
        ] = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )
        for scheduled_location, result in zip(task_locations, results, strict=False):
            if isinstance(result, RuntimeNodeExecutionResult):
                node_location = result.location
                node_result: RuntimeNodeOutput | BaseException = result.output
            else:
                node_location = scheduled_location
                node_result = result
            updated_context = await self._finalize_node_result(
                workflow_context=updated_context,
                node_location=node_location,
                result=node_result,
            )
            await self._control_manager.wait_if_paused(
                location.execution_plan.execution_id
            )
            updated_context, _ = await self.apply_cancel_if_requested(
                location=node_location.with_context(updated_context),
                boundary="after_node",
                node_name=node_location.node_name,
            )

        return updated_context

    async def apply_cancel_if_requested(
        self,
        *,
        location: RuntimeExecutionLocation,
        boundary: str,
        node_name: str | None = None,
    ) -> tuple[RuntimeContext, bool]:
        execution_id = location.execution_plan.execution_id
        if not self._control_manager.should_cancel(execution_id):
            return location.context, False

        cancelled_context = self._apply_cancelled_result(
            location=location,
            boundary=boundary,
            node_name=node_name,
        )
        if (
            self._control_manager.get_state(execution_id)
            is not WorkflowControlState.CANCELLED
        ):
            cancelled_location = location.with_context(cancelled_context)
            metadata = {
                **self._event_publisher.control_metadata(cancelled_location),
                "cancelled": True,
                "status": WorkflowControlState.CANCELLED.value,
                "cancel_boundary": boundary,
            }
            if location.wave_index is not None:
                metadata["wave_index"] = location.wave_index
            if node_name is not None:
                metadata["node_name"] = node_name
            await self._control_manager.mark_cancelled(
                execution_id,
                metadata=metadata,
            )

        return cancelled_context, True

    async def _finalize_node_result(
        self,
        *,
        workflow_context: RuntimeContext,
        node_location: RuntimeExecutionLocation,
        result: RuntimeNodeOutput | BaseException,
    ) -> RuntimeContext:
        plan_node = node_location.plan_node
        wave_index = node_location.wave_index
        if plan_node is None or wave_index is None:
            raise ValueError("Runtime node result requires node and wave location.")

        if isinstance(result, asyncio.CancelledError):
            raise result

        if isinstance(result, BaseException):
            output = RuntimeNodeOutput.failure_output(
                errors=[
                    {
                        "node_name": plan_node.name,
                        "error_type": type(result).__name__,
                        "message": str(result),
                        "wave_index": wave_index,
                    }
                ],
                execution_metadata={
                    "node_name": plan_node.name,
                    "wave_index": wave_index,
                    "failed": True,
                },
            )
        else:
            output = result

        workflow_trace_context = workflow_context.trace_context
        event_context = self._node_executor.with_trace_context(
            context=workflow_context,
            source=node_location.context,
        )
        event_context, output = await self._persist_artifacts_if_needed(
            context=event_context,
            location=node_location,
            output=output,
        )
        updated_context = event_context
        if workflow_trace_context is not None:
            updated_context = updated_context.with_trace_context(workflow_trace_context)

        await self._lifecycle_manager.after_node_execute(
            context=event_context,
            plan_node=plan_node,
            output=output,
        )
        updated_context = self._context_transitions.apply_output(
            context=updated_context,
            output=output,
        )
        event_context = self._node_executor.with_trace_context(
            context=updated_context,
            source=node_location.context,
        )
        event_location = node_location.with_context(event_context)
        await self._event_publisher.emit_node_output_events(
            location=event_location,
            output=output,
        )
        await self._event_publisher.emit_progress_event(
            event_type=self._context_transitions.node_progress_terminal_event_type(
                output
            ),
            location=event_location,
            payload={
                "node_type": plan_node.node_type,
                "success": output.success,
                "skipped": output.skipped,
                "error_count": len(output.errors),
            },
        )
        return updated_context

    async def _persist_artifacts_if_needed(
        self,
        *,
        context: RuntimeContext,
        location: RuntimeExecutionLocation,
        output: RuntimeNodeOutput,
    ) -> tuple[RuntimeContext, RuntimeNodeOutput]:
        plan_node = location.plan_node
        if self._artifact_manager is None or not output.artifacts:
            return context, output
        if plan_node is None:
            raise ValueError("Artifact persistence requires a runtime node location.")

        artifact_names = list(output.artifacts)
        try:
            updated_context, updated_output = (
                self._artifact_manager.persist_output_artifacts(
                    context=context,
                    node_name=plan_node.name,
                    output=output,
                )
            )
            for artifact_name in artifact_names:
                artifact_data = updated_output.artifacts.get(artifact_name)
                if not isinstance(artifact_data, dict):
                    continue
                artifact_ref = self._artifact_manager.artifact_ref_from_dict(
                    artifact_data
                )
                await self._lifecycle_manager.on_artifact_persisted(
                    context=updated_context,
                    plan_node=plan_node,
                    artifact_name=artifact_name,
                    artifact_ref=artifact_ref,
                )
            return updated_context, updated_output
        except Exception as exc:
            for artifact_name in artifact_names:
                await self._lifecycle_manager.on_artifact_failed(
                    context=context,
                    plan_node=plan_node,
                    artifact_name=artifact_name,
                    error=exc,
                )
            return context, RuntimeNodeOutput.failure_output(
                errors=[
                    {
                        "node_name": plan_node.name,
                        "error_type": type(exc).__name__,
                        "message": f"Artifact persistence failed: {str(exc)}",
                    }
                ],
                execution_metadata={
                    **dict(output.execution_metadata),
                    "node_name": plan_node.name,
                    "artifact_persistence_failed": True,
                    "failed": True,
                },
            )

    def _apply_cancelled_result(
        self,
        *,
        location: RuntimeExecutionLocation,
        boundary: str,
        node_name: str | None,
    ) -> RuntimeContext:
        context = location.context
        if CANCELLED_WORKFLOW_OUTPUT_NAME in context.node_outputs:
            return context

        snapshot = self._control_manager.get_snapshot(
            location.execution_plan.execution_id
        )
        status = WorkflowControlState.CANCELLED.value
        outputs: dict[str, Any] = {
            "cancelled": True,
            "status": status,
            "reason": snapshot.reason,
            "requested_by": snapshot.requested_by,
            "cancel_boundary": boundary,
            "workflow_id": context.workflow_id,
            "workflow_name": location.execution_plan.workflow_name,
            "execution_id": location.execution_plan.execution_id,
            "runtime_id": context.runtime_id,
        }
        if location.wave_index is not None:
            outputs["wave_index"] = location.wave_index
        if node_name is not None:
            outputs["node_name"] = node_name

        metadata = {
            **self._event_publisher.control_metadata(location),
            "node_name": CANCELLED_WORKFLOW_OUTPUT_NAME,
            "cancelled": True,
            "status": status,
            "cancel_boundary": boundary,
        }
        if location.wave_index is not None:
            metadata["wave_index"] = location.wave_index
        if node_name is not None:
            metadata["cancelled_node_name"] = node_name

        return self._context_transitions.apply_output(
            context=context,
            output=RuntimeNodeOutput(
                success=False,
                stop_propagation=True,
                outputs=outputs,
                execution_metadata=metadata,
            ),
        )

    async def _mark_skipped(
        self,
        *,
        location: RuntimeExecutionLocation,
        reason: str,
    ) -> RuntimeContext:
        plan_node = location.plan_node
        wave_index = location.wave_index
        if plan_node is None or wave_index is None:
            raise ValueError("Skipped transition requires node and wave location.")

        output = RuntimeNodeOutput.skipped_output(
            reason=reason,
            execution_metadata={
                "node_name": plan_node.name,
                "wave_index": wave_index,
                "skipped": True,
                "reason": reason,
            },
        )
        updated_context = self._context_transitions.apply_output(
            context=location.context,
            output=output,
        )
        event_location = self._node_executor.with_node_trace_context(
            location.with_context(updated_context)
        )
        await self._event_publisher.emit_node_event(
            event_type=RuntimeEventType.NODE_SKIPPED,
            location=event_location,
            output=output,
            payload={"reason": reason},
        )
        await self._event_publisher.emit_progress_event(
            event_type=RuntimeEventType.NODE_PROGRESS_SKIPPED,
            location=event_location,
            payload={
                "node_type": plan_node.node_type,
                "success": output.success,
                "skipped": output.skipped,
                "reason": reason,
                "error_count": len(output.errors),
            },
        )
        return updated_context

    async def _mark_failure(
        self,
        *,
        location: RuntimeExecutionLocation,
        error_type: str,
        message: str,
    ) -> RuntimeContext:
        plan_node = location.plan_node
        wave_index = location.wave_index
        if plan_node is None or wave_index is None:
            raise ValueError("Failure transition requires node and wave location.")

        output = RuntimeNodeOutput.failure_output(
            errors=[
                {
                    "node_name": plan_node.name,
                    "error_type": error_type,
                    "message": message,
                    "wave_index": wave_index,
                }
            ],
            execution_metadata={
                "node_name": plan_node.name,
                "wave_index": wave_index,
                "failed": True,
            },
        )
        updated_context = self._context_transitions.apply_output(
            context=location.context,
            output=output,
        )
        event_location = self._node_executor.with_node_trace_context(
            location.with_context(updated_context)
        )
        await self._event_publisher.emit_node_event(
            event_type=RuntimeEventType.NODE_FAILED,
            location=event_location,
            output=output,
            payload={
                "error_type": error_type,
                "message": message,
            },
        )
        await self._event_publisher.emit_progress_event(
            event_type=RuntimeEventType.NODE_PROGRESS_FAILED,
            location=event_location,
            payload={
                "node_type": plan_node.node_type,
                "success": output.success,
                "skipped": output.skipped,
                "error_count": len(output.errors),
                "errors": list(output.errors),
            },
        )
        return updated_context
