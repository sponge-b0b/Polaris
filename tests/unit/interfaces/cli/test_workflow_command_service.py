from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest

import interfaces.cli.services.workflow_command_service as workflow_command_service
from core.runtime.events import EventBus, RuntimeEvent, RuntimeEventType
from interfaces.cli.services.workflow_command_service import (
    MorningReportCommandRequest,
    WorkflowCommandService,
    WorkflowRunCommandRequest,
)


def _runtime_scope_from_builder(
    builder: Callable[..., Any],
) -> Callable[..., Any]:
    @asynccontextmanager
    async def scope(**kwargs: object) -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(
            runtime=await builder(**kwargs),
        )

    return scope


@pytest.mark.asyncio
async def test_workflow_command_service_runs_workflow_and_returns_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeFacade:
        def workflow_exists(
            self,
            workflow_name: str,
        ) -> bool:
            return workflow_name == "morning_report"

        async def run_workflow(
            self,
            **kwargs: Any,
        ) -> dict[str, Any]:
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_id": kwargs["execution_id"],
                "execution_result": {
                    "success": True,
                    "status": "succeeded",
                    "final_context": {
                        "workflow_inputs": {
                            "symbol": "SPY",
                        },
                        "node_outputs": {
                            "technical_agent": {
                                "success": True,
                                "outputs": {
                                    "technical_signal": {
                                        "directional_score": 0.42,
                                    },
                                },
                            },
                        },
                    },
                },
            }

    class FakeRuntime:
        facade = FakeFacade()

    async def build_runtime(**_: object) -> FakeRuntime:
        return FakeRuntime()

    monkeypatch.setattr(
        workflow_command_service,
        "cli_runtime_scope",
        _runtime_scope_from_builder(build_runtime),
    )

    envelope = await WorkflowCommandService().run_workflow(
        WorkflowRunCommandRequest(
            workflow_name="morning_report",
            execution_id="exec-123",
            metadata={
                "interface": "cli",
            },
        )
    )

    assert envelope.success is True
    assert envelope.workflow_name == "morning_report"
    assert envelope.execution_id == "exec-123"
    assert (
        envelope.payload["node_outputs"]["technical_agent"]["outputs"][
            "technical_signal"
        ]["directional_score"]
        == 0.42
    )


@pytest.mark.asyncio
async def test_workflow_command_service_renders_missing_workflow_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeFacade:
        def workflow_exists(
            self,
            workflow_name: str,
        ) -> bool:
            return False

        def list_workflows(
            self,
        ) -> list[str]:
            return [
                "other_workflow",
            ]

    class FakeRuntime:
        facade = FakeFacade()

    async def build_runtime(**_: object) -> FakeRuntime:
        return FakeRuntime()

    monkeypatch.setattr(
        workflow_command_service,
        "cli_runtime_scope",
        _runtime_scope_from_builder(build_runtime),
    )

    envelope = await WorkflowCommandService().run_workflow(
        WorkflowRunCommandRequest(
            workflow_name="morning_report",
        )
    )

    assert envelope.success is False
    assert envelope.workflow_name == "morning_report"
    assert envelope.status == "failed"
    assert "workflow is not registered" in (envelope.error_message or "")
    assert envelope.summary["command"] == "workflow run"


@pytest.mark.asyncio
async def test_morning_report_command_service_builds_workflow_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeFacade:
        def workflow_exists(
            self,
            workflow_name: str,
        ) -> bool:
            return workflow_name == "morning_report"

        async def run_workflow(
            self,
            **kwargs: Any,
        ) -> dict[str, Any]:
            captured.update(
                kwargs,
            )
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_result": {
                    "success": True,
                    "final_context": {},
                },
            }

    class FakeRuntime:
        facade = FakeFacade()

    async def build_runtime(**_: object) -> FakeRuntime:
        return FakeRuntime()

    monkeypatch.setattr(
        workflow_command_service,
        "cli_runtime_scope",
        _runtime_scope_from_builder(build_runtime),
    )

    envelope = await WorkflowCommandService().run_morning_report(
        MorningReportCommandRequest(
            symbol="QQQ",
        )
    )

    assert envelope.success is True
    assert captured["workflow_name"] == "morning_report"
    assert captured["workflow_inputs"] == {
        "symbol": "QQQ",
    }
    assert captured["metadata"] == {
        "symbol": "QQQ",
        "interface": "cli",
        "command": "morning-report",
    }


@pytest.mark.asyncio
async def test_workflow_command_service_forwards_progress_notifications(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_bus = EventBus()
    notifications: list[str] = []

    class FakeFacade:
        def workflow_exists(
            self,
            workflow_name: str,
        ) -> bool:
            return workflow_name == "morning_report"

        async def run_workflow(
            self,
            **kwargs: Any,
        ) -> dict[str, Any]:
            await event_bus.emit(
                RuntimeEvent(
                    event_type=RuntimeEventType.WORKFLOW_PROGRESS_STARTED,
                    execution_id=kwargs["execution_id"] or "exec-123",
                    workflow_id=kwargs["workflow_name"],
                    runtime_id="runtime-123",
                    payload={
                        "state": "running",
                    },
                )
            )
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_id": kwargs["execution_id"],
                "execution_result": {
                    "success": True,
                    "final_context": {},
                },
            }

    class FakeRuntime:
        def __init__(
            self,
        ) -> None:
            self.facade = FakeFacade()
            self.event_bus = event_bus

    async def build_runtime(**_: object) -> FakeRuntime:
        return FakeRuntime()

    monkeypatch.setattr(
        workflow_command_service,
        "cli_runtime_scope",
        _runtime_scope_from_builder(build_runtime),
    )

    envelope = await WorkflowCommandService().run_workflow(
        WorkflowRunCommandRequest(
            workflow_name="morning_report",
            execution_id="exec-123",
            progress_handler=lambda notification: notifications.append(
                notification.event_type,
            ),
        )
    )

    assert envelope.success is True
    assert notifications == [
        "runtime.workflow.started",
    ]
    assert event_bus.global_subscriber_count() == 0


@pytest.mark.asyncio
async def test_workflow_command_service_forwards_interactive_control_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.runtime.control import WorkflowControlSnapshot, WorkflowControlState

    commands: list[tuple[str, str]] = []
    messages: list[str] = []
    processed = asyncio.Event()
    inputs = [
        "pause",
        "resume",
        "cancel",
    ]

    async def read_input() -> str | None:
        await asyncio.sleep(
            0,
        )
        if inputs:
            return inputs.pop(
                0,
            )
        return None

    class FakeFacade:
        def workflow_exists(
            self,
            workflow_name: str,
        ) -> bool:
            return workflow_name == "morning_report"

        async def pause_workflow(
            self,
            **kwargs: Any,
        ) -> WorkflowControlSnapshot:
            commands.append(
                (
                    "pause",
                    kwargs["execution_id"],
                )
            )
            return WorkflowControlSnapshot(
                execution_id=kwargs["execution_id"],
                state=WorkflowControlState.PAUSING,
            )

        async def resume_workflow(
            self,
            **kwargs: Any,
        ) -> WorkflowControlSnapshot:
            commands.append(
                (
                    "resume",
                    kwargs["execution_id"],
                )
            )
            return WorkflowControlSnapshot(
                execution_id=kwargs["execution_id"],
                state=WorkflowControlState.RESUMING,
            )

        async def cancel_workflow(
            self,
            **kwargs: Any,
        ) -> WorkflowControlSnapshot:
            commands.append(
                (
                    "cancel",
                    kwargs["execution_id"],
                )
            )
            processed.set()
            return WorkflowControlSnapshot(
                execution_id=kwargs["execution_id"],
                state=WorkflowControlState.CANCELLING,
            )

        async def run_workflow(
            self,
            **kwargs: Any,
        ) -> dict[str, Any]:
            await asyncio.wait_for(
                processed.wait(),
                timeout=1,
            )
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_id": kwargs["execution_id"],
                "execution_result": {
                    "success": True,
                    "status": "succeeded",
                    "final_context": {},
                },
            }

    class FakeRuntime:
        def __init__(
            self,
        ) -> None:
            self.facade = FakeFacade()
            self.event_bus = EventBus()

    async def build_runtime(**_: object) -> FakeRuntime:
        return FakeRuntime()

    monkeypatch.setattr(
        workflow_command_service,
        "cli_runtime_scope",
        _runtime_scope_from_builder(build_runtime),
    )

    envelope = await WorkflowCommandService().run_workflow(
        WorkflowRunCommandRequest(
            workflow_name="morning_report",
            execution_id="exec-control",
            interactive_control=True,
            interactive_input=read_input,
            control_handler=lambda notification: messages.append(
                notification.to_console(),
            ),
        )
    )

    assert envelope.success is True
    assert commands == [
        (
            "pause",
            "exec-control",
        ),
        (
            "resume",
            "exec-control",
        ),
        (
            "cancel",
            "exec-control",
        ),
    ]
    assert any("interactive control enabled" in message for message in messages)
