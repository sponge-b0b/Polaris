from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import Iterable

from core.runtime.artifacts.artifact_ref import ArtifactRef
from core.runtime.events.runtime_events import RuntimeEvent
from core.runtime.lifecycle.runtime_lifecycle_failure import (
    RuntimeLifecycleFailureContext,
    RuntimeLifecycleFailureHandler,
)
from core.runtime.lifecycle.runtime_lifecycle_hooks import (
    RuntimeLifecycleHook,
)
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.workflow.models.workflow_execution_plan import (
    ExecutionPlanNode,
    ExecutionWave,
    WorkflowExecutionPlan,
)


class RuntimeLifecycleManager:
    """
    Canonical runtime lifecycle coordinator.

    Coordinates lifecycle hook execution across:
    - workflow execution
    - wave execution
    - node execution
    - artifact persistence
    - runtime events
    """

    def __init__(
        self,
        hooks: Iterable[RuntimeLifecycleHook] | None = None,
        fail_fast: bool = False,
        failure_handler: RuntimeLifecycleFailureHandler | None = None,
    ) -> None:
        self._hooks: list[RuntimeLifecycleHook] = list(
            hooks or [],
        )

        self.fail_fast = fail_fast
        self._failure_handler = failure_handler

    # ========================================================
    # REGISTRATION
    # ========================================================

    def register(
        self,
        hook: RuntimeLifecycleHook,
    ) -> None:
        self._hooks.append(
            hook,
        )

    def register_many(
        self,
        hooks: Iterable[RuntimeLifecycleHook],
    ) -> None:
        for hook in hooks:
            self.register(
                hook,
            )

    def clear(
        self,
    ) -> None:
        self._hooks.clear()

    # ========================================================
    # LOOKUPS
    # ========================================================

    @property
    def hooks(
        self,
    ) -> tuple[RuntimeLifecycleHook, ...]:
        return tuple(
            self._hooks,
        )

    def total_hooks(
        self,
    ) -> int:
        return len(
            self._hooks,
        )

    # ========================================================
    # WORKFLOW LIFECYCLE
    # ========================================================

    async def before_workflow_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
    ) -> None:
        await self._dispatch(
            RuntimeLifecycleFailureContext.from_runtime_context(
                lifecycle_event="before_workflow_execute",
                context=context,
            ),
            lambda hook: hook.before_workflow_execute(
                context=context,
                execution_plan=execution_plan,
            ),
        )

    async def after_workflow_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
    ) -> None:
        await self._dispatch(
            RuntimeLifecycleFailureContext.from_runtime_context(
                lifecycle_event="after_workflow_execute",
                context=context,
            ),
            lambda hook: hook.after_workflow_execute(
                context=context,
                execution_plan=execution_plan,
            ),
        )

    # ========================================================
    # WAVE LIFECYCLE
    # ========================================================

    async def before_wave_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
        wave: ExecutionWave,
    ) -> None:
        await self._dispatch(
            RuntimeLifecycleFailureContext.from_runtime_context(
                lifecycle_event="before_wave_execute",
                context=context,
            ),
            lambda hook: hook.before_wave_execute(
                context=context,
                execution_plan=execution_plan,
                wave=wave,
            ),
        )

    async def after_wave_execute(
        self,
        context: RuntimeContext,
        execution_plan: WorkflowExecutionPlan,
        wave: ExecutionWave,
    ) -> None:
        await self._dispatch(
            RuntimeLifecycleFailureContext.from_runtime_context(
                lifecycle_event="after_wave_execute",
                context=context,
            ),
            lambda hook: hook.after_wave_execute(
                context=context,
                execution_plan=execution_plan,
                wave=wave,
            ),
        )

    # ========================================================
    # NODE LIFECYCLE
    # ========================================================

    async def before_node_execute(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
    ) -> None:
        await self._dispatch(
            RuntimeLifecycleFailureContext.from_runtime_context(
                lifecycle_event="before_node_execute",
                context=context,
                node_name=plan_node.name,
            ),
            lambda hook: hook.before_node_execute(
                context=context,
                plan_node=plan_node,
            ),
        )

    async def after_node_execute(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
        output: RuntimeNodeOutput,
    ) -> None:
        await self._dispatch(
            RuntimeLifecycleFailureContext.from_runtime_context(
                lifecycle_event="after_node_execute",
                context=context,
                node_name=plan_node.name,
            ),
            lambda hook: hook.after_node_execute(
                context=context,
                plan_node=plan_node,
                output=output,
            ),
        )

    # ========================================================
    # ARTIFACT LIFECYCLE
    # ========================================================

    async def on_artifact_persisted(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
        artifact_name: str,
        artifact_ref: ArtifactRef,
    ) -> None:
        """
        Called after an artifact is successfully persisted.
        """

        await self._dispatch(
            RuntimeLifecycleFailureContext.from_runtime_context(
                lifecycle_event="on_artifact_persisted",
                context=context,
                node_name=plan_node.name,
            ),
            lambda hook: hook.on_artifact_persisted(
                context=context,
                plan_node=plan_node,
                artifact_name=artifact_name,
                artifact_ref=artifact_ref,
            ),
        )

    async def on_artifact_failed(
        self,
        context: RuntimeContext,
        plan_node: ExecutionPlanNode,
        artifact_name: str,
        error: Exception,
    ) -> None:
        """
        Called when artifact persistence fails.
        """

        await self._dispatch(
            RuntimeLifecycleFailureContext.from_runtime_context(
                lifecycle_event="on_artifact_failed",
                context=context,
                node_name=plan_node.name,
            ),
            lambda hook: hook.on_artifact_failed(
                context=context,
                plan_node=plan_node,
                artifact_name=artifact_name,
                error=error,
            ),
        )

    # ========================================================
    # EVENT LIFECYCLE
    # ========================================================

    async def on_runtime_event(
        self,
        event: RuntimeEvent,
    ) -> None:
        await self._dispatch(
            RuntimeLifecycleFailureContext.from_runtime_event(
                lifecycle_event="on_runtime_event",
                event=event,
            ),
            lambda hook: hook.on_runtime_event(
                event=event,
            ),
        )

    # ========================================================
    # INTERNAL DISPATCH
    # ========================================================

    async def _dispatch(
        self,
        failure_context: RuntimeLifecycleFailureContext,
        callback: Callable[
            [RuntimeLifecycleHook],
            Awaitable[None],
        ],
    ) -> None:
        if not self._hooks:
            return

        results = await asyncio.gather(
            *[callback(hook) for hook in self._hooks],
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, asyncio.CancelledError):
                raise result

        failures = [
            (hook, result)
            for hook, result in zip(self._hooks, results)
            if isinstance(result, BaseException)
        ]
        if self._failure_handler is not None:
            for hook, error in failures:
                await self._failure_handler(
                    failure_context,
                    hook,
                    error,
                )

        if self.fail_fast and failures:
            raise failures[0][1]

    # ========================================================
    # SERIALIZATION
    # ========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "hook_count": len(self._hooks),
            "hooks": [hook.__class__.__name__ for hook in self._hooks],
            "fail_fast": self.fail_fast,
        }
