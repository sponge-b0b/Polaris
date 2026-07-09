from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import AsyncIterator

import pytest
from typer.testing import CliRunner

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
