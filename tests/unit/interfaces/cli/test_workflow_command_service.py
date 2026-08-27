from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import fields
from types import MappingProxyType, SimpleNamespace
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
    *,
    dependencies: Mapping[type[object], object] | None = None,
) -> Callable[..., Any]:
    resolved_dependencies = MappingProxyType(dict(dependencies or {}))

    @asynccontextmanager
    async def scope(**kwargs: object) -> AsyncIterator[SimpleNamespace]:
        runtime = await builder(**kwargs)

        async def get(dependency_type: type[object]) -> object:
            try:
                return resolved_dependencies[dependency_type]
            except KeyError as exc:
                raise RuntimeError(
                    f"dependency not available: {dependency_type.__name__}"
                ) from exc

        yield SimpleNamespace(
            runtime=runtime,
            get=get,
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
        policy_engine = None
        governance_engine = None

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
            metadata={
                "interface": "cli",
            },
        )
    )

    assert envelope.success is True
    assert envelope.workflow_name == "morning_report"
    assert envelope.execution_id is None
    assert (
        envelope.payload["node_outputs"]["technical_agent"]["outputs"][
            "technical_signal"
        ]["directional_score"]
        == 0.42
    )


@pytest.mark.asyncio
async def test_workflow_command_service_uses_governed_execution_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    direct_facade_calls: list[dict[str, Any]] = []

    class FakeFacade:
        def workflow_exists(self, workflow_name: str) -> bool:
            return workflow_name == "morning_report"

        async def run_workflow(
            self,
            **kwargs: Any,
        ) -> dict[str, Any]:
            direct_facade_calls.append(kwargs)
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_id": kwargs["execution_id"],
                "execution_result": {"success": True, "final_context": {}},
            }

    class FakeGovernedExecutionService:
        async def run_workflow(self, **kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_id": "governed-test",
                "execution_result": {"success": True, "final_context": {}},
            }

    class FakeRuntime:
        facade = FakeFacade()
        policy_engine = object()
        governance_engine = None

    async def build_runtime(**_: object) -> FakeRuntime:
        return FakeRuntime()

    governed_execution_service = FakeGovernedExecutionService()

    monkeypatch.setattr(
        workflow_command_service,
        "cli_runtime_scope",
        _runtime_scope_from_builder(
            build_runtime,
            dependencies={
                workflow_command_service.GovernedWorkflowExecutionService: (
                    governed_execution_service
                ),
            },
        ),
    )

    envelope = await WorkflowCommandService().run_workflow(
        WorkflowRunCommandRequest(
            workflow_name="morning_report",
        )
    )

    assert envelope.success is True
    assert envelope.execution_id == "governed-test"
    assert "execution_id" not in captured
    assert "governed_execution_evidence" not in captured
    assert direct_facade_calls == []


@pytest.mark.asyncio
async def test_workflow_command_service_fails_closed_when_governed_dependency_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    direct_facade_calls: list[dict[str, Any]] = []

    class FakeFacade:
        def workflow_exists(self, workflow_name: str) -> bool:
            return workflow_name == "morning_report"

        async def run_workflow(
            self,
            **kwargs: Any,
        ) -> dict[str, Any]:
            direct_facade_calls.append(kwargs)
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_id": kwargs["execution_id"],
                "execution_result": {"success": True, "final_context": {}},
            }

    class FakeRuntime:
        facade = FakeFacade()
        policy_engine = None
        governance_engine = object()

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
    assert direct_facade_calls == []
    assert "GovernedWorkflowExecutionService" in (envelope.error_message or "")


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
        policy_engine = None
        governance_engine = None

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
        policy_engine = None
        governance_engine = None

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
            self.policy_engine = None
            self.governance_engine = None

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

    class FakeRuntime:
        def __init__(
            self,
        ) -> None:
            self.facade = FakeFacade()
            self.event_bus = EventBus()
            self.policy_engine = object()
            self.governance_engine = None

    class FakeGovernedExecutionService:
        async def run_workflow(self, **kwargs: Any) -> dict[str, Any]:
            kwargs["execution_started_handler"]("governed-control")
            await asyncio.wait_for(
                processed.wait(),
                timeout=1,
            )
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_id": "governed-control",
                "execution_result": {
                    "success": True,
                    "status": "succeeded",
                    "final_context": {},
                },
            }

    async def build_runtime(**_: object) -> FakeRuntime:
        return FakeRuntime()

    monkeypatch.setattr(
        workflow_command_service,
        "cli_runtime_scope",
        _runtime_scope_from_builder(
            build_runtime,
            dependencies={
                workflow_command_service.GovernedWorkflowExecutionService: (
                    FakeGovernedExecutionService()
                ),
            },
        ),
    )

    envelope = await WorkflowCommandService().run_workflow(
        WorkflowRunCommandRequest(
            workflow_name="morning_report",
            interactive_control=True,
            interactive_input=read_input,
            control_handler=lambda notification: messages.append(
                notification.to_console(),
            ),
        )
    )

    assert envelope.success is True
    assert commands == [
        ("pause", "governed-control"),
        ("resume", "governed-control"),
        ("cancel", "governed-control"),
    ]
    assert messages == [
        "[control] interactive control enabled (pause/resume/cancel/help) "
        "execution=governed-control",
        "[control] control command accepted execution=governed-control "
        "command=pause state=pausing",
        "[control] control command accepted execution=governed-control "
        "command=resume state=resuming",
        "[control] control command accepted execution=governed-control "
        "command=cancel state=cancelling",
    ]


def test_workflow_run_request_has_no_caller_selected_execution_id() -> None:
    request_fields = {field.name for field in fields(WorkflowRunCommandRequest)}

    assert "execution_id" not in request_fields
    assert "governed_execution_id" not in request_fields
