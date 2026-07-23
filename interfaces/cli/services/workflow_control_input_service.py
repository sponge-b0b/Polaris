from __future__ import annotations

import asyncio
import select
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, TextIO

from core.runtime.control import WorkflowControlSnapshot

AsyncLineReader = Callable[
    [],
    Awaitable[str | None],
]
WorkflowControlNotificationHandler = Callable[
    ["WorkflowControlNotification"],
    None,
]


class WorkflowControlFacade(Protocol):
    """
    Minimal WorkflowFacade control API consumed by the CLI boundary.
    """

    async def pause_workflow(
        self,
        execution_id: str,
        reason: str | None = None,
        requested_by: str | None = "workflow_facade",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot: ...

    async def resume_workflow(
        self,
        execution_id: str,
        reason: str | None = None,
        requested_by: str | None = "workflow_facade",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot: ...

    async def cancel_workflow(
        self,
        execution_id: str,
        reason: str | None = None,
        requested_by: str | None = "workflow_facade",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot: ...


@dataclass(frozen=True, slots=True)
class WorkflowInteractiveControlRequest:
    """
    Typed request for a CLI interactive workflow-control session.
    """

    execution_id: str
    prompt: str = "polaris> "
    requested_by: str = "cli"
    reason_prefix: str = "interactive cli control"
    metadata: dict[str, Any] = field(
        default_factory=lambda: {
            "interface": "cli",
            "command": "interactive-control",
        }
    )


@dataclass(frozen=True, slots=True)
class WorkflowControlNotification:
    """
    CLI-facing notification emitted by the interactive control layer.
    """

    message: str
    execution_id: str
    command: str | None = None
    state: str | None = None
    error: str | None = None

    def to_console(
        self,
    ) -> str:
        parts = [
            "[control]",
            self.message,
            f"execution={self.execution_id}",
        ]

        if self.command:
            parts.append(
                f"command={self.command}",
            )

        if self.state:
            parts.append(
                f"state={self.state}",
            )

        if self.error:
            parts.append(
                f"error={self.error}",
            )

        return " ".join(
            parts,
        )


@dataclass(slots=True)
class PollingStdinLineReader:
    """
    Async line reader for terminal input without blocking workflow completion.
    """

    input_stream: TextIO = sys.stdin
    poll_interval_seconds: float = 0.1

    async def __call__(
        self,
    ) -> str | None:
        while True:
            ready, _, _ = await asyncio.to_thread(
                select.select,
                [
                    self.input_stream,
                ],
                [],
                [],
                self.poll_interval_seconds,
            )
            if ready:
                line = self.input_stream.readline()
                if line == "":
                    return None
                return line.rstrip(
                    "\n",
                )

            await asyncio.sleep(
                0,
            )


class WorkflowInteractiveControlSession:
    """
    Runs a cooperative CLI control loop beside an executing workflow.
    """

    def __init__(
        self,
        *,
        facade: WorkflowControlFacade,
        request: WorkflowInteractiveControlRequest,
        input_reader: AsyncLineReader | None = None,
        notification_handler: WorkflowControlNotificationHandler | None = None,
    ) -> None:
        self.facade = facade
        self.request = request
        self.input_reader = input_reader or PollingStdinLineReader()
        self.notification_handler = notification_handler
        self._task: asyncio.Task[None] | None = None

    def start(
        self,
    ) -> None:
        if self._task is not None:
            return

        self._emit(
            WorkflowControlNotification(
                message=("interactive control enabled (pause/resume/cancel/help)"),
                execution_id=self.request.execution_id,
            )
        )
        self._task = asyncio.create_task(
            self._run(),
        )

    async def stop(
        self,
    ) -> None:
        if self._task is None:
            return

        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def _run(
        self,
    ) -> None:
        while True:
            line = await self.input_reader()
            if line is None:
                return

            await self._handle_line(
                line,
            )

    async def _handle_line(
        self,
        line: str,
    ) -> None:
        command = _normalize_command(
            line,
        )
        if command is None:
            return

        if command == "help":
            self._emit_help()
            return

        try:
            snapshot = await self._execute_command(
                command,
            )
        except Exception as exc:
            self._emit(
                WorkflowControlNotification(
                    message="control command failed",
                    execution_id=self.request.execution_id,
                    command=command,
                    error=str(
                        exc,
                    )
                    or exc.__class__.__name__,
                )
            )
            return

        self._emit(
            WorkflowControlNotification(
                message="control command accepted",
                execution_id=snapshot.execution_id,
                command=command,
                state=snapshot.state.value,
            )
        )

    async def _execute_command(
        self,
        command: str,
    ) -> WorkflowControlSnapshot:
        metadata = dict(
            self.request.metadata,
        )
        metadata["control_command"] = command
        reason = f"{self.request.reason_prefix}: {command}"

        if command == "pause":
            return await self.facade.pause_workflow(
                execution_id=self.request.execution_id,
                reason=reason,
                requested_by=self.request.requested_by,
                metadata=metadata,
            )

        if command == "resume":
            return await self.facade.resume_workflow(
                execution_id=self.request.execution_id,
                reason=reason,
                requested_by=self.request.requested_by,
                metadata=metadata,
            )

        return await self.facade.cancel_workflow(
            execution_id=self.request.execution_id,
            reason=reason,
            requested_by=self.request.requested_by,
            metadata=metadata,
        )

    def _emit_help(
        self,
    ) -> None:
        self._emit(
            WorkflowControlNotification(
                message="available commands: pause, resume, cancel, help",
                execution_id=self.request.execution_id,
                command="help",
            )
        )

    def _emit(
        self,
        notification: WorkflowControlNotification,
    ) -> None:
        if self.notification_handler is None:
            return

        self.notification_handler(
            notification,
        )


def _normalize_command(
    line: str,
) -> str | None:
    value = line.strip().lower()
    if not value:
        return None

    aliases = {
        "p": "pause",
        "pause": "pause",
        "r": "resume",
        "resume": "resume",
        "c": "cancel",
        "cancel": "cancel",
        "q": "cancel",
        "quit": "cancel",
        "stop": "cancel",
        "?": "help",
        "h": "help",
        "help": "help",
    }
    return aliases.get(
        value,
    )
