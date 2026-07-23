from __future__ import annotations

import asyncio

from core.runtime.events import RuntimeEventType
from core.runtime.execution.runtime_context_transitions import (
    RuntimeContextTransitions,
)
from core.runtime.execution.runtime_event_publisher import RuntimeEventPublisher
from core.runtime.execution.runtime_execution_context import (
    RuntimeExecutionLocation,
    RuntimeNodeExecutionResult,
    RuntimeNodeInvocation,
)
from core.runtime.lifecycle.runtime_lifecycle_manager import RuntimeLifecycleManager
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput


class RuntimeNodeExecutor:
    """Invokes one runtime node with trace, timeout, retry, and metadata rules."""

    def __init__(
        self,
        *,
        event_publisher: RuntimeEventPublisher,
        context_transitions: RuntimeContextTransitions,
        lifecycle_manager: RuntimeLifecycleManager,
    ) -> None:
        self._event_publisher = event_publisher
        self._context_transitions = context_transitions
        self._lifecycle_manager = lifecycle_manager

    @staticmethod
    def with_node_trace_context(
        location: RuntimeExecutionLocation,
        *,
        attempt: int | None = None,
    ) -> RuntimeExecutionLocation:
        context = location.context
        plan_node = location.plan_node
        if context.trace_context is None or plan_node is None:
            return location

        return location.with_context(
            context.with_trace_context(
                context.trace_context.child(
                    node_name=plan_node.name,
                    attributes={
                        "node_type": plan_node.node_type,
                        "operation_kind": (
                            "runtime_node_attempt"
                            if attempt is not None
                            else "runtime_node_transition"
                        ),
                        **({"attempt": attempt} if attempt is not None else {}),
                    },
                )
            )
        )

    async def prepare_attempt(
        self,
        *,
        location: RuntimeExecutionLocation,
        attempt: int,
        max_attempts: int,
    ) -> RuntimeExecutionLocation:
        plan_node = location.plan_node
        if plan_node is None:
            raise ValueError("Runtime node attempt requires a plan node.")

        attempt_location = self.with_node_trace_context(
            location,
            attempt=attempt,
        )
        await self._event_publisher.emit_progress_event(
            event_type=RuntimeEventType.NODE_PROGRESS_STARTED,
            location=attempt_location,
            payload={
                "node_type": plan_node.node_type,
                "attempt": attempt,
                "max_attempts": max_attempts,
            },
        )
        await self._event_publisher.emit_progress_event(
            event_type=RuntimeEventType.NODE_PROGRESS_RUNNING,
            location=attempt_location,
            payload={
                "node_type": plan_node.node_type,
                "attempt": attempt,
                "max_attempts": max_attempts,
            },
        )
        await self._lifecycle_manager.before_node_execute(
            context=attempt_location.context,
            plan_node=plan_node,
        )
        return attempt_location

    async def execute(
        self,
        invocation: RuntimeNodeInvocation,
        *,
        prepared_first_attempt: RuntimeExecutionLocation | None = None,
    ) -> RuntimeNodeExecutionResult:
        location = invocation.location
        plan_node = location.plan_node
        if plan_node is None or location.wave_index is None:
            raise ValueError("Runtime node invocation requires node and wave location.")

        max_attempts = max(1, plan_node.max_retries + 1)
        retry_backoff_seconds = float(
            plan_node.metadata.get("retry_backoff_seconds", 0.0)
        )
        last_output: RuntimeNodeOutput | None = None
        last_location: RuntimeExecutionLocation | None = None

        for attempt in range(1, max_attempts + 1):
            if attempt == 1 and prepared_first_attempt is not None:
                attempt_location = prepared_first_attempt
            else:
                attempt_location = await self.prepare_attempt(
                    location=location,
                    attempt=attempt,
                    max_attempts=max_attempts,
                )
            attempt_invocation = RuntimeNodeInvocation(
                node=invocation.node,
                location=attempt_location,
            )

            output = await self._run_with_timeout(
                invocation=attempt_invocation,
                timeout_seconds=plan_node.timeout_seconds,
            )
            output = self._context_transitions.with_runtime_metadata(
                output=output,
                plan_node=plan_node,
                wave_index=location.wave_index,
                attempt=attempt,
                max_attempts=max_attempts,
            )
            if output.success or attempt == max_attempts:
                return RuntimeNodeExecutionResult(
                    output=output,
                    location=attempt_location,
                )

            last_output = output
            last_location = attempt_location
            await self._lifecycle_manager.after_node_execute(
                context=attempt_location.context,
                plan_node=plan_node,
                output=output,
            )
            await self._event_publisher.emit_node_event(
                event_type=RuntimeEventType.NODE_RETRYING,
                location=attempt_location,
                output=output,
                payload={
                    "attempt": attempt,
                    "next_attempt": attempt + 1,
                    "max_attempts": max_attempts,
                    "retry_backoff_seconds": retry_backoff_seconds,
                },
            )
            if retry_backoff_seconds > 0:
                await asyncio.sleep(retry_backoff_seconds)

        fallback_output = last_output or RuntimeNodeOutput.failure_output(
            errors=[
                {
                    "node_name": plan_node.name,
                    "error_type": "RuntimeExecutionError",
                    "message": "Node execution failed without output.",
                    "wave_index": location.wave_index,
                }
            ],
            execution_metadata={
                "node_name": plan_node.name,
                "wave_index": location.wave_index,
                "failed": True,
            },
        )
        return RuntimeNodeExecutionResult(
            output=fallback_output,
            location=last_location or location,
        )

    @staticmethod
    async def _run_with_timeout(
        *,
        invocation: RuntimeNodeInvocation,
        timeout_seconds: float | None,
    ) -> RuntimeNodeOutput:
        if timeout_seconds is None:
            return await invocation.node.run(invocation.location.context)

        try:
            return await asyncio.wait_for(
                invocation.node.run(invocation.location.context),
                timeout=timeout_seconds,
            )
        except TimeoutError:
            return RuntimeNodeOutput.failure_output(
                errors=[
                    {
                        "node_name": invocation.node.node_name,
                        "error_type": "TimeoutError",
                        "message": (f"Node timed out after {timeout_seconds} seconds."),
                    }
                ],
                execution_metadata={
                    "node_name": invocation.node.node_name,
                    "timeout_seconds": timeout_seconds,
                    "failed": True,
                },
            )

    @staticmethod
    def with_trace_context(
        *,
        context: RuntimeContext,
        source: RuntimeContext,
    ) -> RuntimeContext:
        if source.trace_context is None:
            return context
        return context.with_trace_context(source.trace_context)
