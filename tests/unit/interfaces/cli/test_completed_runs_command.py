from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import AsyncIterator

import pytest
from typer.testing import CliRunner

from application.projections.workflow_outputs import CompletedRunProjectionSummary
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionReconciliationRequest,
)
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionReconciliationResult,
)
from application.projections.workflow_outputs import WorkflowOutputProjectionRequest
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionRetryRequest,
)
from application.projections.workflow_outputs import WorkflowOutputProjectionRetryResult
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionStatusRequest,
)
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionStatusResult,
)

from core.runtime.state.runtime_context import RuntimeContext
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapConfig
from interfaces.cli.app import create_app


class FakeCompletedRunsFacade:
    def __init__(
        self,
        context: RuntimeContext | None = None,
    ) -> None:
        self.context = context
        self.cleanup_calls: list[dict[str, int | None]] = []
        self.deleted_runs: list[tuple[str, str]] = []

    async def list_completed_runs(
        self,
        workflow_name: str,
    ) -> list[str]:
        return ["exec-1"] if workflow_name == "morning_report" else []

    async def load_completed_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> RuntimeContext | None:
        if workflow_name == "morning_report" and execution_id == "exec-1":
            return self.context
        return None

    async def delete_completed_run(
        self,
        workflow_name: str,
        execution_id: str,
        *,
        confirmation: object,
    ) -> None:
        self.deleted_runs.append(
            (
                workflow_name,
                execution_id,
            )
        )

    async def cleanup_completed_runs(
        self,
        *,
        max_age_days: int | None = None,
        max_count: int | None = None,
        confirmation: object,
    ) -> int:
        self.cleanup_calls.append(
            {
                "max_age_days": max_age_days,
                "max_count": max_count,
            }
        )
        return 3


def _runtime(
    *,
    facade: FakeCompletedRunsFacade,
    config: WorkflowBootstrapConfig | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        facade=facade,
        config=config or WorkflowBootstrapConfig(),
    )


def _runtime_scope(runtime: SimpleNamespace):
    @asynccontextmanager
    async def scope(**_: object) -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(runtime=runtime)

    return scope


def test_completed_runs_list_awaits_async_facade_and_renders_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = FakeCompletedRunsFacade()
    monkeypatch.setattr(
        "interfaces.cli.commands.completed_runs_command.cli_runtime_scope",
        _runtime_scope(_runtime(facade=facade)),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "runs",
            "list",
            "morning_report",
        ],
    )

    assert result.exit_code == 0
    assert "Archived runs for 'morning_report':" in result.output
    assert "exec-1" in result.output


def test_completed_runs_delete_awaits_async_facade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = FakeCompletedRunsFacade()
    monkeypatch.setattr(
        "interfaces.cli.commands.completed_runs_command.cli_runtime_scope",
        _runtime_scope(_runtime(facade=facade)),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "runs",
            "delete",
            "morning_report",
            "exec-1",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    assert (
        "Deleted archived run 'exec-1' for workflow 'morning_report'" in result.output
    )
    assert facade.deleted_runs == [("morning_report", "exec-1")]


def test_completed_runs_show_console_renders_current_runtime_context_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
    ).add_node_output(
        "node_a",
        {"value": 42},
    )
    facade = FakeCompletedRunsFacade(
        context=context,
    )
    monkeypatch.setattr(
        "interfaces.cli.commands.completed_runs_command.cli_runtime_scope",
        _runtime_scope(_runtime(facade=facade)),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "runs",
            "show",
            "morning_report",
            "exec-1",
            "--format",
            "console",
        ],
    )

    assert result.exit_code == 0
    assert "Workflow: morning_report" in result.output
    assert "Success: True" in result.output
    assert "Status: succeeded" in result.output
    assert "Node Outputs: 1" in result.output
    assert "Errors: 0" in result.output


def test_completed_runs_cleanup_uses_configured_retention_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = FakeCompletedRunsFacade()
    config = WorkflowBootstrapConfig(
        completed_run_retention_max_age_days=30,
        completed_run_retention_max_count=100,
    )
    monkeypatch.setattr(
        "interfaces.cli.commands.completed_runs_command.cli_runtime_scope",
        _runtime_scope(
            _runtime(
                facade=facade,
                config=config,
            )
        ),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "runs",
            "cleanup",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    assert "Deleted 3 archived runs" in result.output
    assert facade.cleanup_calls == [
        {
            "max_age_days": 30,
            "max_count": 100,
        }
    ]


class FakeProjectionOperationsService:
    def __init__(self) -> None:
        self.status_request: WorkflowOutputProjectionStatusRequest | None = None
        self.project_request: WorkflowOutputProjectionRequest | None = None
        self.retry_request: WorkflowOutputProjectionRetryRequest | None = None
        self.reconcile_request: WorkflowOutputProjectionReconciliationRequest | None = (
            None
        )

    async def projection_status(
        self,
        request: WorkflowOutputProjectionStatusRequest,
    ) -> WorkflowOutputProjectionStatusResult:
        self.status_request = request
        return WorkflowOutputProjectionStatusResult(requested=request, jobs=())

    async def project(
        self,
        request: WorkflowOutputProjectionRequest,
    ) -> CompletedRunProjectionSummary:
        self.project_request = request
        return CompletedRunProjectionSummary(
            workflow_name=request.workflow_name,
            execution_id=request.execution_id,
            run_id=request.run_id,
        )

    async def retry_projection(
        self,
        request: WorkflowOutputProjectionRetryRequest,
    ) -> WorkflowOutputProjectionRetryResult:
        self.retry_request = request
        return WorkflowOutputProjectionRetryResult(
            requested=request,
            matched_jobs=0,
            retried_jobs=0,
        )

    async def reconcile_projections(
        self,
        request: WorkflowOutputProjectionReconciliationRequest,
    ) -> WorkflowOutputProjectionReconciliationResult:
        self.reconcile_request = request
        return WorkflowOutputProjectionReconciliationResult(
            requested=request,
            scanned_runs=0,
            missing_projection_runs=0,
        )


def _projection_operations_scope(
    service: FakeProjectionOperationsService,
):
    @asynccontextmanager
    async def scope() -> AsyncIterator[FakeProjectionOperationsService]:
        yield service

    return scope


def test_completed_runs_projection_status_uses_projection_operations_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FakeProjectionOperationsService()
    monkeypatch.setattr(
        "interfaces.cli.commands.completed_runs_command._projection_operations_scope",
        _projection_operations_scope(service),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "completed-runs",
            "projection-status",
            "--workflow",
            "morning_report",
            "--status",
            "failed",
        ],
    )

    assert result.exit_code == 0
    assert "Projection Jobs" in result.output
    assert service.status_request is not None
    assert service.status_request.workflow_name == "morning_report"
    assert [
        str(status.value) if hasattr(status, "value") else str(status)
        for status in service.status_request.statuses
    ] == ["failed"]


def test_completed_runs_project_uses_projection_operations_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FakeProjectionOperationsService()
    monkeypatch.setattr(
        "interfaces.cli.commands.completed_runs_command._projection_operations_scope",
        _projection_operations_scope(service),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "completed-runs",
            "project",
            "morning_report",
            "exec-1",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "Workflow Output Projection" in result.output
    assert service.project_request is not None
    assert service.project_request.workflow_name == "morning_report"
    assert service.project_request.execution_id == "exec-1"
    assert service.project_request.dry_run is True


def test_completed_runs_retry_projection_uses_projection_operations_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FakeProjectionOperationsService()
    monkeypatch.setattr(
        "interfaces.cli.commands.completed_runs_command._projection_operations_scope",
        _projection_operations_scope(service),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "completed-runs",
            "retry-projection",
            "--workflow",
            "morning_report",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "Projection Retry" in result.output
    assert service.retry_request is not None
    assert service.retry_request.workflow_name == "morning_report"
    assert service.retry_request.dry_run is True


def test_completed_runs_reconcile_projections_uses_projection_operations_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FakeProjectionOperationsService()
    monkeypatch.setattr(
        "interfaces.cli.commands.completed_runs_command._projection_operations_scope",
        _projection_operations_scope(service),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "completed-runs",
            "reconcile-projections",
            "--workflow",
            "morning_report",
        ],
    )

    assert result.exit_code == 0
    assert "Projection Reconciliation" in result.output
    assert service.reconcile_request is not None
    assert service.reconcile_request.workflow_name == "morning_report"
    assert service.reconcile_request.dry_run is True
