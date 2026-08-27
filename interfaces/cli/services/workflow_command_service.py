from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from application.governance import GovernedWorkflowExecutionService
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
from interfaces.cli.bootstrap.container import CliRuntimeScope, cli_runtime_scope
from interfaces.cli.rendering.workflow_rendering import (
    WorkflowRenderEnvelope,
    workflow_exception_to_render_envelope,
    workflow_result_to_render_envelope,
)
from interfaces.cli.services.workflow_control_input_service import (
    AsyncLineReader,
    WorkflowControlNotificationHandler,
    WorkflowInteractiveControlRequest,
    WorkflowInteractiveControlSession,
)
from interfaces.cli.services.workflow_progress_service import (
    ProgressNotificationHandler,
    WorkflowProgressSubscription,
)


@dataclass(frozen=True, slots=True)
class WorkflowRunCommandRequest:
    """
    Typed command-service request for workflow execution from the CLI boundary.
    """

    workflow_name: str
    mode: str = "live"
    metadata: Mapping[str, Any] = field(
        default_factory=dict,
    )
    workflow_inputs: Mapping[str, Any] | None = None
    plugin_dirs: tuple[Path, ...] = ()
    error_summary: Mapping[str, Any] = field(
        default_factory=dict,
    )
    progress_handler: ProgressNotificationHandler | None = None
    interactive_control: bool = False
    interactive_input: AsyncLineReader | None = None
    control_handler: WorkflowControlNotificationHandler | None = None


@dataclass(frozen=True, slots=True)
class MorningReportCommandRequest:
    """
    Typed command-service request for the canonical morning-report workflow.
    """

    symbol: str = "SPY"
    plugin_dirs: tuple[Path, ...] = ()
    progress_handler: ProgressNotificationHandler | None = None
    interactive_control: bool = False
    interactive_input: AsyncLineReader | None = None
    control_handler: WorkflowControlNotificationHandler | None = None


@dataclass(slots=True)
class _ObservedWorkflowExecution:
    execution_id: str | None = None

    def record_started(
        self,
        execution_id: str,
    ) -> None:
        if self.execution_id is not None and self.execution_id != execution_id:
            raise WorkflowCommandServiceError(
                "workflow execution correlation changed during CLI run"
            )
        self.execution_id = execution_id


class WorkflowCommandServiceError(RuntimeError):
    """
    Base command-service error rendered by the CLI output layer.
    """


class WorkflowNotRegisteredError(WorkflowCommandServiceError):
    """
    Raised when a requested workflow is not registered in the runtime facade.
    """


class GovernedWorkflowExecutionDependencyError(WorkflowCommandServiceError):
    """
    Raised when governed CLI execution cannot resolve its request-scoped service.
    """


class WorkflowCommandService:
    """
    Async workflow command service used behind the synchronous Typer boundary.
    """

    def __init__(
        self,
        *,
        default_morning_report_workflow: str = "morning_report",
    ) -> None:
        self.default_morning_report_workflow = default_morning_report_workflow

    async def run_workflow(
        self,
        request: WorkflowRunCommandRequest,
    ) -> WorkflowRenderEnvelope:
        observed_execution = _ObservedWorkflowExecution()
        try:
            result = await self._run_workflow_result(
                request,
                observed_execution=observed_execution,
            )
            return workflow_result_to_render_envelope(
                result,
                workflow_name=request.workflow_name,
                execution_id=observed_execution.execution_id,
            )
        except Exception as exc:
            return workflow_exception_to_render_envelope(
                exc,
                workflow_name=request.workflow_name,
                execution_id=observed_execution.execution_id,
                summary=self._error_summary(
                    request,
                ),
            )

    async def run_morning_report(
        self,
        request: MorningReportCommandRequest,
    ) -> WorkflowRenderEnvelope:
        return await self.run_workflow(
            WorkflowRunCommandRequest(
                workflow_name=self.default_morning_report_workflow,
                workflow_inputs={"symbol": request.symbol},
                metadata={
                    "symbol": request.symbol,
                    "interface": "cli",
                    "command": "morning-report",
                },
                plugin_dirs=request.plugin_dirs,
                progress_handler=request.progress_handler,
                interactive_control=request.interactive_control,
                interactive_input=request.interactive_input,
                control_handler=request.control_handler,
                error_summary={
                    "symbol": request.symbol,
                    "interface": "cli",
                    "command": "morning-report",
                },
            )
        )

    async def _run_workflow_result(
        self,
        request: WorkflowRunCommandRequest,
        *,
        observed_execution: _ObservedWorkflowExecution,
    ) -> Any:
        async with cli_runtime_scope(
            plugin_dirs=request.plugin_dirs,
            autoload_plugins=bool(
                request.plugin_dirs,
            ),
        ) as scope:
            governed_execution_service = await _resolve_governed_execution_service(
                scope,
            )
            return await self._execute_with_runtime(
                request,
                runtime=scope.runtime,
                governed_execution_service=governed_execution_service,
                observed_execution=observed_execution,
            )

    async def _execute_with_runtime(
        self,
        request: WorkflowRunCommandRequest,
        *,
        runtime: WorkflowBootstrapResult,
        governed_execution_service: GovernedWorkflowExecutionService | None,
        observed_execution: _ObservedWorkflowExecution,
    ) -> Any:

        subscription: WorkflowProgressSubscription | None = None
        if request.progress_handler is not None:
            subscription = WorkflowProgressSubscription(
                event_bus=runtime.event_bus,
                handler=request.progress_handler,
            )
            subscription.start()

        try:
            if not runtime.facade.workflow_exists(
                request.workflow_name,
            ):
                available = runtime.facade.list_workflows()
                raise WorkflowNotRegisteredError(
                    "workflow is not registered: "
                    f"{request.workflow_name}. Available workflows: {available}"
                )

            control_session: WorkflowInteractiveControlSession | None = None

            def start_control_session(execution_id: str) -> None:
                nonlocal control_session
                observed_execution.record_started(
                    execution_id,
                )
                if not request.interactive_control:
                    return
                control_session = WorkflowInteractiveControlSession(
                    facade=runtime.facade,
                    request=WorkflowInteractiveControlRequest(
                        execution_id=execution_id,
                        metadata=dict(request.metadata),
                    ),
                    input_reader=request.interactive_input,
                    notification_handler=request.control_handler,
                )
                control_session.start()

            workflow_task = asyncio.create_task(
                self._run_workflow(
                    runtime=runtime,
                    governed_execution_service=governed_execution_service,
                    workflow_name=request.workflow_name,
                    mode=request.mode,
                    workflow_inputs=request.workflow_inputs,
                    metadata=dict(
                        request.metadata,
                    ),
                    execution_started_handler=start_control_session,
                )
            )

            try:
                return await workflow_task
            finally:
                if control_session is not None:
                    await control_session.stop()
        finally:
            if subscription is not None:
                subscription.stop()

    async def _run_workflow(
        self,
        *,
        runtime: WorkflowBootstrapResult,
        governed_execution_service: GovernedWorkflowExecutionService | None,
        workflow_name: str,
        mode: str,
        workflow_inputs: Mapping[str, Any] | None,
        metadata: dict[str, Any],
        execution_started_handler: Callable[[str], None] | None,
    ) -> Any:
        if governed_execution_service is not None:
            return await governed_execution_service.run_workflow(
                workflow_name=workflow_name,
                mode=mode,
                workflow_inputs=workflow_inputs,
                metadata=metadata,
                execution_started_handler=execution_started_handler,
            )
        return await runtime.facade.run_workflow(
            workflow_name=workflow_name,
            execution_id=None,
            mode=mode,
            workflow_inputs=workflow_inputs,
            metadata=metadata,
        )

    def _error_summary(
        self,
        request: WorkflowRunCommandRequest,
    ) -> dict[str, Any]:
        if request.error_summary:
            return dict(
                request.error_summary,
            )

        return {
            "mode": request.mode,
            "metadata": dict(
                request.metadata,
            ),
            "interface": "cli",
            "command": "workflow run",
        }


def _requires_governed_execution(runtime: WorkflowBootstrapResult) -> bool:
    return runtime.policy_engine is not None or runtime.governance_engine is not None


async def _resolve_governed_execution_service(
    scope: CliRuntimeScope,
) -> GovernedWorkflowExecutionService | None:
    if not _requires_governed_execution(scope.runtime):
        return None

    try:
        return await scope.get(GovernedWorkflowExecutionService)
    except Exception as exc:
        raise GovernedWorkflowExecutionDependencyError(
            "governed workflow execution requires request-scoped "
            "GovernedWorkflowExecutionService and its audit/evidence dependencies"
        ) from exc
