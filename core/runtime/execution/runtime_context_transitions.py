from __future__ import annotations

from typing import Any

from core.runtime.control import WorkflowControlState
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.runtime.events import RuntimeEventType
from core.workflow.models.workflow_execution_plan import ExecutionPlanNode
from core.workflow.models.workflow_execution_plan import ExecutionWave


CANCELLED_WORKFLOW_OUTPUT_NAME = "workflow_control.cancelled"


class RuntimeContextTransitions:
    """Pure runtime output and terminal-state transition rules."""

    def apply_output(
        self,
        *,
        context: RuntimeContext,
        output: RuntimeNodeOutput,
    ) -> RuntimeContext:
        node_name = output.execution_metadata.get(
            "node_name",
            "unknown_node",
        )
        node_outputs = dict(context.node_outputs)
        node_outputs[node_name] = output.to_dict()
        errors = [*context.errors, *output.errors]

        return context.model_copy(
            update={
                "node_outputs": node_outputs,
                "errors": errors,
                "context_version": context.context_version + 1,
            },
            deep=True,
        )

    @staticmethod
    def with_runtime_metadata(
        *,
        output: RuntimeNodeOutput,
        plan_node: ExecutionPlanNode,
        wave_index: int,
        attempt: int,
        max_attempts: int,
    ) -> RuntimeNodeOutput:
        metadata = {
            **dict(output.execution_metadata),
            "node_name": plan_node.name,
            "wave_index": wave_index,
            "attempt": attempt,
            "max_attempts": max_attempts,
        }
        return RuntimeNodeOutput(
            success=output.success,
            skipped=output.skipped,
            stop_propagation=output.stop_propagation,
            outputs=dict(output.outputs),
            artifacts=dict(output.artifacts),
            emitted_events=list(output.emitted_events),
            errors=list(output.errors),
            execution_metadata=metadata,
        )

    @staticmethod
    def dependencies_succeeded(
        *,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
    ) -> bool:
        for dependency in plan_node.dependencies:
            dependency_output = context.node_outputs.get(dependency)
            if not isinstance(dependency_output, dict):
                return False
            if dependency_output.get("success") is not True:
                return False
            if dependency_output.get("skipped") is True:
                return False
        return True

    def should_stop_execution(
        self,
        context: RuntimeContext,
    ) -> bool:
        for output in context.node_outputs.values():
            if not isinstance(output, dict):
                continue
            if output.get("stop_propagation") is True:
                return True
            if (
                output.get("success") is False
                and output.get("skipped") is not True
                and not self.is_cancelled_output(output)
            ):
                return True
        return False

    def has_execution_failure(
        self,
        context: RuntimeContext,
    ) -> bool:
        return bool(context.errors or self.failed_nodes(context))

    @staticmethod
    def completed_nodes(
        context: RuntimeContext,
    ) -> list[str]:
        return sorted(
            node_name
            for node_name, output in context.node_outputs.items()
            if (
                isinstance(output, dict)
                and output.get("success") is True
                and output.get("skipped") is not True
            )
        )

    def failed_nodes(
        self,
        context: RuntimeContext,
    ) -> list[str]:
        return sorted(
            node_name
            for node_name, output in context.node_outputs.items()
            if (
                isinstance(output, dict)
                and output.get("success") is False
                and output.get("skipped") is not True
                and not self.is_cancelled_output(output)
            )
        )

    @staticmethod
    def skipped_nodes(
        context: RuntimeContext,
    ) -> list[str]:
        return sorted(
            node_name
            for node_name, output in context.node_outputs.items()
            if isinstance(output, dict) and output.get("skipped") is True
        )

    @staticmethod
    def is_cancelled_output(
        output: dict[str, Any],
    ) -> bool:
        execution_metadata = output.get("execution_metadata")
        outputs = output.get("outputs")
        return (
            isinstance(execution_metadata, dict)
            and execution_metadata.get("node_name") == CANCELLED_WORKFLOW_OUTPUT_NAME
            and execution_metadata.get("status") == WorkflowControlState.CANCELLED.value
            and isinstance(outputs, dict)
            and outputs.get("cancelled") is True
        )

    @staticmethod
    def wave_progress_terminal_event_type(
        *,
        context: RuntimeContext,
        wave: ExecutionWave,
    ) -> RuntimeEventType:
        for node_name in wave.nodes:
            node_output = context.node_outputs.get(node_name)
            if not isinstance(node_output, dict):
                continue
            if (
                node_output.get("success") is False
                and node_output.get("skipped") is not True
            ):
                return RuntimeEventType.WAVE_PROGRESS_FAILED
        return RuntimeEventType.WAVE_PROGRESS_COMPLETED

    @staticmethod
    def node_progress_terminal_event_type(
        output: RuntimeNodeOutput,
    ) -> RuntimeEventType:
        if output.success:
            return RuntimeEventType.NODE_PROGRESS_COMPLETED
        return RuntimeEventType.NODE_PROGRESS_FAILED
