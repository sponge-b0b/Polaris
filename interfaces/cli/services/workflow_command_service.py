from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
from interfaces.cli.bootstrap.container import cli_runtime_scope
from interfaces.cli.rendering.workflow_rendering import WorkflowRenderEnvelope
from interfaces.cli.rendering.workflow_rendering import (
    workflow_exception_to_render_envelope,
)
from interfaces.cli.rendering.workflow_rendering import (
    workflow_result_to_render_envelope,
)
from interfaces.cli.services.workflow_control_input_service import AsyncLineReader
from interfaces.cli.services.workflow_control_input_service import (
    WorkflowControlNotificationHandler,
)
from interfaces.cli.services.workflow_control_input_service import (
    WorkflowInteractiveControlRequest,
)
from interfaces.cli.services.workflow_control_input_service import (
    WorkflowInteractiveControlSession,
)
from interfaces.cli.services.workflow_progress_service import (
    ProgressNotificationHandler,
)
from interfaces.cli.services.workflow_progress_service import (
    WorkflowProgressSubscription,
)


@dataclass(frozen=True, slots=True)
class WorkflowRunCommandRequest:
    """
    Typed command-service request for workflow execution from the CLI boundary.
    """

    workflow_name: str
    mode: str = "live"
    execution_id: str | None = None
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


class WorkflowCommandServiceError(RuntimeError):
    """
    Base command-service error rendered by the CLI output layer.
    """


class WorkflowNotRegisteredError(WorkflowCommandServiceError):
    """
    Raised when a requested workflow is not registered in the runtime facade.
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
        resolved_request = self._with_execution_id(
            request,
        )
        try:
            result = await self._run_workflow_result(
                resolved_request,
            )
            return workflow_result_to_render_envelope(
                result,
                workflow_name=resolved_request.workflow_name,
                execution_id=resolved_request.execution_id,
            )
        except Exception as exc:
            return workflow_exception_to_render_envelope(
                exc,
                workflow_name=resolved_request.workflow_name,
                execution_id=resolved_request.execution_id,
                summary=self._error_summary(
                    resolved_request,
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
    ) -> Any:
        async with cli_runtime_scope(
            plugin_dirs=request.plugin_dirs,
            autoload_plugins=bool(
                request.plugin_dirs,
            ),
        ) as scope:
            return await self._execute_with_runtime(
                request,
                runtime=scope.runtime,
            )

    async def _execute_with_runtime(
        self,
        request: WorkflowRunCommandRequest,
        *,
        runtime: WorkflowBootstrapResult,
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
            if request.interactive_control:
                if request.execution_id is None:
                    raise WorkflowCommandServiceError(
                        "interactive control requires an execution id"
                    )
                control_session = WorkflowInteractiveControlSession(
                    facade=runtime.facade,
                    request=WorkflowInteractiveControlRequest(
                        execution_id=request.execution_id,
                    ),
                    input_reader=request.interactive_input,
                    notification_handler=request.control_handler,
                )

            workflow_task = asyncio.create_task(
                runtime.facade.run_workflow(
                    workflow_name=request.workflow_name,
                    execution_id=request.execution_id,
                    mode=request.mode,
                    workflow_inputs=request.workflow_inputs,
                    metadata=dict(
                        request.metadata,
                    ),
                )
            )
            if control_session is not None:
                control_session.start()

            try:
                return await workflow_task
            finally:
                if control_session is not None:
                    await control_session.stop()
        finally:
            if subscription is not None:
                subscription.stop()

    def _with_execution_id(
        self,
        request: WorkflowRunCommandRequest,
    ) -> WorkflowRunCommandRequest:
        if request.execution_id is not None:
            return request

        return replace(
            request,
            execution_id=uuid4().hex,
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
