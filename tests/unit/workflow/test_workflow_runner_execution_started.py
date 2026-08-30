from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from core.workflow.execution.workflow_runner import WorkflowRunner, WorkflowRunRequest


@pytest.mark.asyncio
async def test_workflow_runner_reports_execution_id_before_execution() -> None:
    events: list[str] = []

    class FakeRegistry:
        def get(
            self,
            workflow_name: str,
        ) -> object:
            events.append(
                f"get:{workflow_name}",
            )
            return object()

    class FakeCompiler:
        def compile(
            self,
            *,
            workflow_definition: object,
            execution_id: str,
        ) -> SimpleNamespace:
            events.append(
                f"compile:{execution_id}",
            )
            return SimpleNamespace(
                workflow_name="morning_report",
                execution_id=execution_id,
            )

    class FakeWorkflowEngine:
        async def execute(
            self,
            *,
            compiled_workflow: SimpleNamespace,
            workflow_inputs: Mapping[str, Any] | None = None,
            mode: str = "live",
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
        ) -> SimpleNamespace:
            assert workflow_inputs is None
            assert mode == "live"
            assert simulation_time is None
            assert archive_on_completion is True
            assert checkpoint_on_completion is False
            events.append(
                f"execute:{compiled_workflow.execution_id}",
            )
            return SimpleNamespace(
                success=True,
                execution_id=compiled_workflow.execution_id,
            )

    runner = WorkflowRunner(
        registry=cast(
            Any,
            FakeRegistry(),
        ),
        compiler=cast(
            Any,
            FakeCompiler(),
        ),
        workflow_engine=cast(
            Any,
            FakeWorkflowEngine(),
        ),
    )

    result = await runner.run(
        WorkflowRunRequest(
            workflow_name="morning_report",
            execution_id="facade-issued",
            execution_started_handler=lambda execution_id: events.append(
                f"started:{execution_id}",
            ),
        )
    )

    assert result.execution_id == "facade-issued"
    assert events == [
        "get:morning_report",
        "compile:facade-issued",
        "started:facade-issued",
        "execute:facade-issued",
    ]
