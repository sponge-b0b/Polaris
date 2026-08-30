from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any, Protocol

import pytest

import interfaces.cli.services.workflow_command_service as workflow_command_service
from core.runtime.control import WorkflowControlSnapshot, WorkflowControlState
from core.runtime.events import EventBus, RuntimeEvent, RuntimeEventType
from interfaces.cli.services.workflow_command_service import (
    MorningReportCommandRequest,
    WorkflowCommandService,
    WorkflowRunCommandRequest,
)


class _CliRuntimeScopeFactory(Protocol):
    def __call__(
        self,
        *,
        plugin_dirs: tuple[Path, ...] = (),
        autoload_plugins: bool = False,
        provider_profile: str | None = None,
    ) -> AbstractAsyncContextManager[SimpleNamespace]: ...


@dataclass(slots=True)
class _WorkflowControlFacadeFake:
    execution_id: str
    commands: list[tuple[str, str]]
    workflow_success: bool = True
    workflow_status: str = "succeeded"
    processed: asyncio.Event | None = None
    pause_error: str | None = None

    def workflow_exists(
        self,
        workflow_name: str,
    ) -> bool:
        return workflow_name == "morning_report"

    async def run_workflow(
        self,
        *,
        workflow_name: str,
        execution_id: str | None = None,
        mode: str = "live",
        workflow_inputs: Mapping[str, Any] | None = None,
        simulation_time: datetime | None = None,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
        execution_started_handler: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        del execution_id, mode, workflow_inputs, simulation_time
        del archive_on_completion, checkpoint_on_completion, metadata
        if execution_started_handler is not None:
            execution_started_handler(self.execution_id)
        if self.processed is not None:
            await asyncio.wait_for(
                self.processed.wait(),
                timeout=1,
            )
        else:
            await asyncio.sleep(
                0,
            )
        return {
            "success": self.workflow_success,
            "workflow_name": workflow_name,
            "execution_id": self.execution_id,
            "execution_result": {
                "success": self.workflow_success,
                "execution_id": self.execution_id,
                "status": self.workflow_status,
                "final_context": {
                    "execution_id": self.execution_id,
                },
            },
        }

    async def pause_workflow(
        self,
        execution_id: str,
        reason: str | None = None,
        requested_by: str | None = "workflow_facade",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        del reason, requested_by, metadata
        if self.pause_error is not None:
            raise RuntimeError(
                self.pause_error,
            )
        return self._record_control(
            command="pause",
            execution_id=execution_id,
            state=WorkflowControlState.PAUSING,
        )

    async def resume_workflow(
        self,
        execution_id: str,
        reason: str | None = None,
        requested_by: str | None = "workflow_facade",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        del reason, requested_by, metadata
        return self._record_control(
            command="resume",
            execution_id=execution_id,
            state=WorkflowControlState.RESUMING,
        )

    async def cancel_workflow(
        self,
        execution_id: str,
        reason: str | None = None,
        requested_by: str | None = "workflow_facade",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowControlSnapshot:
        del reason, requested_by, metadata
        snapshot = self._record_control(
            command="cancel",
            execution_id=execution_id,
            state=WorkflowControlState.CANCELLING,
        )
        if self.processed is not None:
            self.processed.set()
        return snapshot

    def _record_control(
        self,
        *,
        command: str,
        execution_id: str,
        state: WorkflowControlState,
    ) -> WorkflowControlSnapshot:
        self.commands.append(
            (
                command,
                execution_id,
            )
        )
        return WorkflowControlSnapshot(
            execution_id=execution_id,
            state=state,
        )


def _runtime_scope_from_builder(
    builder: Callable[[], Any],
    *,
    dependencies: Mapping[type[object], object] | None = None,
) -> _CliRuntimeScopeFactory:
    resolved_dependencies = MappingProxyType(dict(dependencies or {}))

    @asynccontextmanager
    async def scope(
        *,
        plugin_dirs: tuple[Path, ...] = (),
        autoload_plugins: bool = False,
        provider_profile: str | None = None,
    ) -> AsyncIterator[SimpleNamespace]:
        del plugin_dirs, autoload_plugins, provider_profile
        runtime = await builder()

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
            *,
            workflow_name: str,
            execution_id: str | None = None,
            mode: str = "live",
            workflow_inputs: Mapping[str, Any] | None = None,
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
            metadata: dict[str, Any] | None = None,
            execution_started_handler: Callable[[str], None] | None = None,
        ) -> dict[str, Any]:
            del mode, simulation_time, archive_on_completion
            del checkpoint_on_completion, metadata
            runtime_execution_id = execution_id or "runtime-issued"
            if execution_started_handler is not None:
                execution_started_handler(runtime_execution_id)
            return {
                "success": True,
                "workflow_name": workflow_name,
                "execution_id": runtime_execution_id,
                "execution_result": {
                    "success": True,
                    "execution_id": runtime_execution_id,
                    "status": "succeeded",
                    "final_context": {
                        "execution_id": runtime_execution_id,
                        "workflow_inputs": dict(workflow_inputs or {}),
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

    async def build_runtime() -> FakeRuntime:
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
            *,
            workflow_name: str,
            execution_id: str | None = None,
            mode: str = "live",
            workflow_inputs: Mapping[str, Any] | None = None,
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
            metadata: dict[str, Any] | None = None,
            execution_started_handler: Callable[[str], None] | None = None,
        ) -> dict[str, Any]:
            del mode, workflow_inputs, simulation_time
            del archive_on_completion, checkpoint_on_completion
            del metadata, execution_started_handler
            direct_facade_calls.append(
                {
                    "workflow_name": workflow_name,
                    "execution_id": execution_id,
                }
            )
            return {
                "success": True,
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "execution_result": {"success": True, "final_context": {}},
            }

    class FakeGovernedExecutionService:
        async def run_workflow(
            self,
            *,
            workflow_name: str,
            mode: str = "live",
            workflow_inputs: Mapping[str, Any] | None = None,
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
            metadata: dict[str, Any] | None = None,
            execution_started_handler: Callable[[str], None] | None = None,
        ) -> dict[str, Any]:
            del simulation_time, archive_on_completion, checkpoint_on_completion
            captured.update(
                {
                    "workflow_name": workflow_name,
                    "mode": mode,
                    "workflow_inputs": workflow_inputs,
                    "metadata": metadata,
                    "execution_started_handler": execution_started_handler,
                }
            )
            if execution_started_handler is not None:
                execution_started_handler("governed-test")
            return {
                "success": True,
                "workflow_name": workflow_name,
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

    async def build_runtime() -> FakeRuntime:
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
        async def run_workflow(
            self,
            *,
            workflow_name: str,
            mode: str = "live",
            workflow_inputs: Mapping[str, Any] | None = None,
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
            metadata: dict[str, Any] | None = None,
            execution_started_handler: Callable[[str], None] | None = None,
        ) -> dict[str, Any]:
            del mode, workflow_inputs, simulation_time
            del archive_on_completion, checkpoint_on_completion, metadata
            execution_id = "governed-platform-progress"
            if execution_started_handler is not None:
                execution_started_handler(execution_id)
            await event_bus.emit(
                RuntimeEvent(
                    event_type=RuntimeEventType.WORKFLOW_PROGRESS_STARTED,
                    execution_id=execution_id,
                    workflow_id=workflow_name,
                    runtime_id="runtime-platform-progress",
                    payload={"state": "running"},
                )
            )
            return {
                "success": True,
                "workflow_name": workflow_name,
                "execution_result": {
                    "success": True,
                    "execution_id": execution_id,
                    "final_context": {"execution_id": execution_id},
                },
            }

    async def build_runtime() -> FakeRuntime:
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
        async def run_workflow(
            self,
            *,
            workflow_name: str,
            mode: str = "live",
            workflow_inputs: Mapping[str, Any] | None = None,
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
            metadata: dict[str, Any] | None = None,
            execution_started_handler: Callable[[str], None] | None = None,
        ) -> dict[str, Any]:
            del workflow_name, mode, workflow_inputs, simulation_time
            del archive_on_completion, checkpoint_on_completion, metadata
            if execution_started_handler is not None:
                execution_started_handler("governed-platform-error")
            raise RuntimeError("workflow failed after execution start")

    async def build_runtime() -> FakeRuntime:
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
            *,
            workflow_name: str,
            execution_id: str | None = None,
            mode: str = "live",
            workflow_inputs: Mapping[str, Any] | None = None,
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
            metadata: dict[str, Any] | None = None,
            execution_started_handler: Callable[[str], None] | None = None,
        ) -> dict[str, Any]:
            del mode, workflow_inputs, simulation_time
            del archive_on_completion, checkpoint_on_completion
            del metadata, execution_started_handler
            direct_facade_calls.append(
                {
                    "workflow_name": workflow_name,
                    "execution_id": execution_id,
                }
            )
            return {
                "success": True,
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "execution_result": {"success": True, "final_context": {}},
            }

    class FakeRuntime:
        facade = FakeFacade()
        policy_engine = None
        governance_engine = object()

    async def build_runtime() -> FakeRuntime:
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

    async def build_runtime() -> FakeRuntime:
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
            *,
            workflow_name: str,
            execution_id: str | None = None,
            mode: str = "live",
            workflow_inputs: Mapping[str, Any] | None = None,
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
            metadata: dict[str, Any] | None = None,
            execution_started_handler: Callable[[str], None] | None = None,
        ) -> dict[str, Any]:
            del execution_id, mode, simulation_time, archive_on_completion
            del checkpoint_on_completion, execution_started_handler
            captured.update(
                {
                    "workflow_name": workflow_name,
                    "workflow_inputs": workflow_inputs,
                    "metadata": metadata,
                },
            )
            return {
                "success": True,
                "workflow_name": workflow_name,
                "execution_result": {
                    "success": True,
                    "final_context": {},
                },
            }

    class FakeRuntime:
        facade = FakeFacade()
        policy_engine = None
        governance_engine = None

    async def build_runtime() -> FakeRuntime:
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
            *,
            workflow_name: str,
            execution_id: str | None = None,
            mode: str = "live",
            workflow_inputs: Mapping[str, Any] | None = None,
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
            metadata: dict[str, Any] | None = None,
            execution_started_handler: Callable[[str], None] | None = None,
        ) -> dict[str, Any]:
            del mode, workflow_inputs, simulation_time
            del archive_on_completion, checkpoint_on_completion, metadata
            runtime_execution_id = execution_id or "exec-123"
            if execution_started_handler is not None:
                execution_started_handler(runtime_execution_id)
            await event_bus.emit(
                RuntimeEvent(
                    event_type=RuntimeEventType.WORKFLOW_PROGRESS_STARTED,
                    execution_id=runtime_execution_id,
                    workflow_id=workflow_name,
                    runtime_id="runtime-123",
                    payload={
                        "state": "running",
                    },
                )
            )
            return {
                "success": True,
                "workflow_name": workflow_name,
                "execution_id": runtime_execution_id,
                "execution_result": {
                    "success": True,
                    "execution_id": runtime_execution_id,
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

    async def build_runtime() -> FakeRuntime:
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

    facade = _WorkflowControlFacadeFake(
        execution_id="governed-control",
        commands=commands,
        processed=processed,
    )

    class FakeRuntime:
        def __init__(
            self,
        ) -> None:
            self.facade = facade
            self.event_bus = EventBus()
            self.policy_engine = object()
            self.governance_engine = None

    class FakeGovernedExecutionService:
        async def run_workflow(
            self,
            *,
            workflow_name: str,
            mode: str = "live",
            workflow_inputs: Mapping[str, Any] | None = None,
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
            metadata: dict[str, Any] | None = None,
            execution_started_handler: Callable[[str], None] | None = None,
        ) -> dict[str, Any]:
            del mode, workflow_inputs, simulation_time
            del archive_on_completion, checkpoint_on_completion, metadata
            if execution_started_handler is not None:
                execution_started_handler("governed-control")
            await asyncio.wait_for(
                processed.wait(),
                timeout=1,
            )
            return {
                "success": True,
                "workflow_name": workflow_name,
                "execution_id": "governed-control",
                "execution_result": {
                    "success": True,
                    "status": "succeeded",
                    "final_context": {},
                },
            }

    async def build_runtime() -> FakeRuntime:
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

    facade = _WorkflowControlFacadeFake(
        execution_id="facade-issued-control",
        commands=commands,
        workflow_success=False,
        workflow_status="cancelled",
        processed=processed,
    )

    class FakeRuntime:
        def __init__(
            self,
        ) -> None:
            self.facade = facade
            self.event_bus = EventBus()
            self.policy_engine = None
            self.governance_engine = None

    async def build_runtime() -> FakeRuntime:
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
            *,
            workflow_name: str,
            execution_id: str | None = None,
            mode: str = "live",
            workflow_inputs: Mapping[str, Any] | None = None,
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
            metadata: dict[str, Any] | None = None,
            execution_started_handler: Callable[[str], None] | None = None,
        ) -> dict[str, Any]:
            del execution_id, mode, workflow_inputs, simulation_time
            del archive_on_completion, checkpoint_on_completion, metadata
            runtime_execution_id = "facade-eof"
            if execution_started_handler is not None:
                execution_started_handler(runtime_execution_id)
            await asyncio.sleep(
                0,
            )
            return {
                "success": True,
                "workflow_name": workflow_name,
                "execution_id": runtime_execution_id,
                "execution_result": {
                    "success": True,
                    "execution_id": runtime_execution_id,
                    "status": "succeeded",
                    "final_context": {
                        "execution_id": runtime_execution_id,
                    },
                },
            }

    class FakeRuntime:
        facade = FakeFacade()
        event_bus = EventBus()
        policy_engine = None
        governance_engine = None

    async def build_runtime() -> FakeRuntime:
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
            *,
            workflow_name: str,
            execution_id: str | None = None,
            mode: str = "live",
            workflow_inputs: Mapping[str, Any] | None = None,
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
            metadata: dict[str, Any] | None = None,
            execution_started_handler: Callable[[str], None] | None = None,
        ) -> dict[str, Any]:
            del execution_id, mode, workflow_inputs, simulation_time
            del archive_on_completion, checkpoint_on_completion, metadata
            runtime_execution_id = "facade-fast-complete"
            if execution_started_handler is not None:
                execution_started_handler(runtime_execution_id)
            await asyncio.sleep(
                0,
            )
            return {
                "success": True,
                "workflow_name": workflow_name,
                "execution_id": runtime_execution_id,
                "execution_result": {
                    "success": True,
                    "execution_id": runtime_execution_id,
                    "status": "succeeded",
                    "final_context": {
                        "execution_id": runtime_execution_id,
                    },
                },
            }

    class FakeRuntime:
        facade = FakeFacade()
        event_bus = EventBus()
        policy_engine = None
        governance_engine = None

    async def build_runtime() -> FakeRuntime:
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
            *,
            workflow_name: str,
            execution_id: str | None = None,
            mode: str = "live",
            workflow_inputs: Mapping[str, Any] | None = None,
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
            metadata: dict[str, Any] | None = None,
            execution_started_handler: Callable[[str], None] | None = None,
        ) -> dict[str, Any]:
            del execution_id, mode, workflow_inputs, simulation_time
            del archive_on_completion, checkpoint_on_completion, metadata
            runtime_execution_id = "facade-control-failure"
            if execution_started_handler is not None:
                execution_started_handler(runtime_execution_id)
            await asyncio.wait_for(
                processed.wait(),
                timeout=1,
            )
            return {
                "success": True,
                "workflow_name": workflow_name,
                "execution_id": runtime_execution_id,
                "execution_result": {
                    "success": True,
                    "execution_id": runtime_execution_id,
                    "status": "succeeded",
                    "final_context": {
                        "execution_id": runtime_execution_id,
                    },
                },
            }

        async def pause_workflow(
            self,
            execution_id: str,
            reason: str | None = None,
            requested_by: str | None = "workflow_facade",
            metadata: dict[str, Any] | None = None,
        ) -> None:
            del execution_id, reason, requested_by, metadata
            raise RuntimeError("pause rejected")

    class FakeRuntime:
        facade = FakeFacade()
        event_bus = EventBus()
        policy_engine = None
        governance_engine = None

    async def build_runtime() -> FakeRuntime:
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


@pytest.mark.asyncio
async def test_workflow_command_service_reports_invalid_control_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    processed = asyncio.Event()
    inputs = [
        "unknown-control",
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
            *,
            workflow_name: str,
            execution_id: str | None = None,
            mode: str = "live",
            workflow_inputs: Mapping[str, Any] | None = None,
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
            metadata: dict[str, Any] | None = None,
            execution_started_handler: Callable[[str], None] | None = None,
        ) -> dict[str, Any]:
            del execution_id, mode, workflow_inputs, simulation_time
            del archive_on_completion, checkpoint_on_completion, metadata
            runtime_execution_id = "facade-invalid-control"
            if execution_started_handler is not None:
                execution_started_handler(runtime_execution_id)
            await asyncio.wait_for(
                processed.wait(),
                timeout=1,
            )
            return {
                "success": True,
                "workflow_name": workflow_name,
                "execution_id": runtime_execution_id,
                "execution_result": {
                    "success": True,
                    "execution_id": runtime_execution_id,
                    "status": "succeeded",
                    "final_context": {
                        "execution_id": runtime_execution_id,
                    },
                },
            }

        async def pause_workflow(
            self,
            execution_id: str,
            reason: str | None = None,
            requested_by: str | None = "workflow_facade",
            metadata: dict[str, Any] | None = None,
        ) -> None:
            del execution_id, reason, requested_by, metadata
            raise AssertionError("invalid input must not call facade control APIs")

    class FakeRuntime:
        facade = FakeFacade()
        event_bus = EventBus()
        policy_engine = None
        governance_engine = None

    async def build_runtime() -> FakeRuntime:
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
    assert envelope.execution_id == "facade-invalid-control"
    assert messages == [
        "[control] interactive control enabled (pause/resume/cancel/help) "
        "execution=facade-invalid-control",
        "[control] control command failed execution=facade-invalid-control "
        "command=unknown-control error=unknown command",
    ]


def test_workflow_run_request_has_no_caller_selected_execution_id() -> None:
    request_fields = {field.name for field in fields(WorkflowRunCommandRequest)}

    assert "execution_id" not in request_fields
    assert "governed_execution_id" not in request_fields
