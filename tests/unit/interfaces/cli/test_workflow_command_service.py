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
            execution_id = kwargs["execution_id"] or "runtime-issued"
            kwargs["execution_started_handler"](execution_id)
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_id": execution_id,
                "execution_result": {
                    "success": True,
                    "execution_id": execution_id,
                    "status": "succeeded",
                    "final_context": {
                        "execution_id": execution_id,
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
    assert envelope.execution_id == "runtime-issued"
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
            kwargs["execution_started_handler"]("governed-test")
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_result": {
                    "success": True,
                    "execution_id": "governed-test",
                    "final_context": {"execution_id": "governed-test"},
                },
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
async def test_workflow_command_service_uses_platform_execution_for_governed_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_bus = EventBus()
    notifications: list[tuple[str, str]] = []

    class FakeFacade:
        def workflow_exists(self, workflow_name: str) -> bool:
            return workflow_name == "morning_report"

    class FakeRuntime:
        def __init__(
            self,
        ) -> None:
            self.facade = FakeFacade()
            self.event_bus = event_bus
            self.policy_engine = object()
            self.governance_engine = None

    class FakeGovernedExecutionService:
        async def run_workflow(self, **kwargs: Any) -> dict[str, Any]:
            execution_id = "governed-platform-progress"
            kwargs["execution_started_handler"](execution_id)
            await event_bus.emit(
                RuntimeEvent(
                    event_type=RuntimeEventType.WORKFLOW_PROGRESS_STARTED,
                    execution_id=execution_id,
                    workflow_id=kwargs["workflow_name"],
                    runtime_id="runtime-platform-progress",
                    payload={"state": "running"},
                )
            )
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_result": {
                    "success": True,
                    "execution_id": execution_id,
                    "final_context": {"execution_id": execution_id},
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
            progress_handler=lambda notification: notifications.append(
                (
                    notification.event_type,
                    notification.execution_id,
                )
            ),
        )
    )

    assert envelope.success is True
    assert envelope.execution_id == "governed-platform-progress"
    assert notifications == [
        (
            "runtime.workflow.started",
            "governed-platform-progress",
        ),
    ]


@pytest.mark.asyncio
async def test_workflow_command_service_preserves_platform_execution_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeFacade:
        def workflow_exists(self, workflow_name: str) -> bool:
            return workflow_name == "morning_report"

    class FakeRuntime:
        facade = FakeFacade()
        event_bus = EventBus()
        policy_engine = object()
        governance_engine = None

    class FakeGovernedExecutionService:
        async def run_workflow(self, **kwargs: Any) -> dict[str, Any]:
            kwargs["execution_started_handler"]("governed-platform-error")
            raise RuntimeError("workflow failed after execution start")

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
        )
    )

    assert envelope.success is False
    assert envelope.execution_id == "governed-platform-error"
    assert envelope.error_message == "workflow failed after execution start"


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
            execution_id = kwargs["execution_id"] or "exec-123"
            kwargs["execution_started_handler"](execution_id)
            await event_bus.emit(
                RuntimeEvent(
                    event_type=RuntimeEventType.WORKFLOW_PROGRESS_STARTED,
                    execution_id=execution_id,
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
                "execution_id": execution_id,
                "execution_result": {
                    "success": True,
                    "execution_id": execution_id,
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


@pytest.mark.asyncio
async def test_workflow_command_service_starts_control_for_facade_issued_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.runtime.control import WorkflowControlSnapshot, WorkflowControlState

    commands: list[tuple[str, str]] = []
    messages: list[str] = []
    processed = asyncio.Event()
    inputs = [
        "help",
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

        async def run_workflow(
            self,
            **kwargs: Any,
        ) -> dict[str, Any]:
            execution_id = "facade-issued-control"
            kwargs["execution_started_handler"](execution_id)
            await asyncio.wait_for(
                processed.wait(),
                timeout=1,
            )
            return {
                "success": False,
                "workflow_name": kwargs["workflow_name"],
                "execution_id": execution_id,
                "execution_result": {
                    "success": False,
                    "execution_id": execution_id,
                    "status": "cancelled",
                    "final_context": {
                        "execution_id": execution_id,
                    },
                },
            }

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
            interactive_control=True,
            interactive_input=read_input,
            control_handler=lambda notification: messages.append(
                notification.to_console(),
            ),
        )
    )

    assert envelope.success is False
    assert envelope.status == "cancelled"
    assert envelope.execution_id == "facade-issued-control"
    assert commands == [
        ("pause", "facade-issued-control"),
        ("resume", "facade-issued-control"),
        ("cancel", "facade-issued-control"),
    ]
    assert messages == [
        "[control] interactive control enabled (pause/resume/cancel/help) "
        "execution=facade-issued-control",
        "[control] available commands: pause, resume, cancel, help "
        "execution=facade-issued-control command=help",
        "[control] control command accepted execution=facade-issued-control "
        "command=pause state=pausing",
        "[control] control command accepted execution=facade-issued-control "
        "command=resume state=resuming",
        "[control] control command accepted execution=facade-issued-control "
        "command=cancel state=cancelling",
    ]


@pytest.mark.asyncio
async def test_workflow_command_service_stops_control_on_eof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    read_attempts = 0

    async def read_input() -> str | None:
        nonlocal read_attempts
        read_attempts += 1
        return None

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
            execution_id = "facade-eof"
            kwargs["execution_started_handler"](execution_id)
            await asyncio.sleep(
                0,
            )
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_id": execution_id,
                "execution_result": {
                    "success": True,
                    "execution_id": execution_id,
                    "status": "succeeded",
                    "final_context": {
                        "execution_id": execution_id,
                    },
                },
            }

    class FakeRuntime:
        facade = FakeFacade()
        event_bus = EventBus()
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
            interactive_control=True,
            interactive_input=read_input,
            control_handler=lambda notification: messages.append(
                notification.to_console(),
            ),
        )
    )

    assert envelope.success is True
    assert envelope.execution_id == "facade-eof"
    assert read_attempts == 1
    assert messages == [
        "[control] interactive control enabled (pause/resume/cancel/help) "
        "execution=facade-eof",
    ]


@pytest.mark.asyncio
async def test_workflow_command_service_stops_control_when_workflow_finishes_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read_cancelled = asyncio.Event()

    async def read_input() -> str | None:
        try:
            await asyncio.sleep(
                60,
            )
        except asyncio.CancelledError:
            read_cancelled.set()
            raise
        return None

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
            execution_id = "facade-fast-complete"
            kwargs["execution_started_handler"](execution_id)
            await asyncio.sleep(
                0,
            )
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_id": execution_id,
                "execution_result": {
                    "success": True,
                    "execution_id": execution_id,
                    "status": "succeeded",
                    "final_context": {
                        "execution_id": execution_id,
                    },
                },
            }

    class FakeRuntime:
        facade = FakeFacade()
        event_bus = EventBus()
        policy_engine = None
        governance_engine = None

    async def build_runtime(**_: object) -> FakeRuntime:
        return FakeRuntime()

    monkeypatch.setattr(
        workflow_command_service,
        "cli_runtime_scope",
        _runtime_scope_from_builder(build_runtime),
    )

    envelope = await asyncio.wait_for(
        WorkflowCommandService().run_workflow(
            WorkflowRunCommandRequest(
                workflow_name="morning_report",
                interactive_control=True,
                interactive_input=read_input,
            )
        ),
        timeout=1,
    )

    assert envelope.success is True
    assert envelope.execution_id == "facade-fast-complete"
    assert read_cancelled.is_set()


@pytest.mark.asyncio
async def test_workflow_command_service_reports_control_failure_without_corruption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    processed = asyncio.Event()
    inputs = [
        "pause",
    ]

    async def read_input() -> str | None:
        if inputs:
            return inputs.pop()
        processed.set()
        return None

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
            execution_id = "facade-control-failure"
            kwargs["execution_started_handler"](execution_id)
            await asyncio.wait_for(
                processed.wait(),
                timeout=1,
            )
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_id": execution_id,
                "execution_result": {
                    "success": True,
                    "execution_id": execution_id,
                    "status": "succeeded",
                    "final_context": {
                        "execution_id": execution_id,
                    },
                },
            }

        async def pause_workflow(
            self,
            **_: Any,
        ) -> None:
            raise RuntimeError("pause rejected")

    class FakeRuntime:
        facade = FakeFacade()
        event_bus = EventBus()
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
            interactive_control=True,
            interactive_input=read_input,
            control_handler=lambda notification: messages.append(
                notification.to_console(),
            ),
        )
    )

    assert envelope.success is True
    assert envelope.execution_id == "facade-control-failure"
    assert messages == [
        "[control] interactive control enabled (pause/resume/cancel/help) "
        "execution=facade-control-failure",
        "[control] control command failed execution=facade-control-failure "
        "command=pause error=pause rejected",
    ]


def test_workflow_run_request_has_no_caller_selected_execution_id() -> None:
    request_fields = {field.name for field in fields(WorkflowRunCommandRequest)}

    assert "execution_id" not in request_fields
    assert "governed_execution_id" not in request_fields
