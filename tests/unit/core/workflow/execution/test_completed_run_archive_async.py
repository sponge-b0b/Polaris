from __future__ import annotations

import logging

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.completed_run_archive import CompletedRunBundle
from core.workflow.execution.workflow_facade import WorkflowFacade
from core.workflow.execution.workflow_facade import WorkflowFacadeConfig
from core.workflow.models.destructive_operation_confirmation import (
    DestructiveOperationConfirmation,
)
from core.workflow.models.destructive_operation_confirmation import (
    DestructiveWorkflowOperation,
)
from core.workflow.models.workflow_graph_definition import WorkflowGraphDefinition
from core.workflow.models.workflow_node_definition import WorkflowNodeDefinition


class InMemoryCompletedRunArchive(CompletedRunArchive):
    def __init__(
        self,
    ) -> None:
        self.bundles: dict[tuple[str, str], CompletedRunBundle] = {}
        self.cleanup_calls: list[tuple[int | None, int | None]] = []

    async def archive_run(
        self,
        bundle: CompletedRunBundle,
    ) -> None:
        self.bundles[(bundle.run.workflow_name, bundle.run.execution_id)] = bundle

    async def load_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> CompletedRunBundle | None:
        return self.bundles.get(
            (workflow_name, execution_id),
        )

    async def list_archived_runs(
        self,
        workflow_name: str,
    ) -> list[str]:
        return sorted(
            execution_id
            for (stored_workflow_name, execution_id) in self.bundles
            if stored_workflow_name == workflow_name
        )

    async def delete_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> None:
        self.bundles.pop(
            (workflow_name, execution_id),
            None,
        )

    async def cleanup_archived_runs(
        self,
        max_age_days: int | None = None,
        max_count: int | None = None,
    ) -> int:
        self.cleanup_calls.append(
            (max_age_days, max_count),
        )
        return 0


class FailingCompletedRunArchive(InMemoryCompletedRunArchive):
    async def archive_run(
        self,
        bundle: CompletedRunBundle,
    ) -> None:
        raise RuntimeError("archive unavailable")


class SampleNode(RuntimeNode):
    node_name = "sample_node"
    node_type = "sample"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput.success_output(
            outputs={
                "value": 42,
            },
        )


class FailingNode(RuntimeNode):
    node_name = "failing_node"
    node_type = "sample"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput.failure_output(
            errors=[
                {
                    "message": "node failed",
                }
            ],
        )


class SampleWorkflow(WorkflowGraphDefinition):
    @property
    def workflow_name(
        self,
    ) -> str:
        return "completed_run_async_test"

    @property
    def workflow_description(
        self,
    ) -> str:
        return "Completed run async archive test workflow."

    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        return [
            WorkflowNodeDefinition(
                name="sample_node",
                node_type=SampleNode,
            )
        ]


class FailingWorkflow(WorkflowGraphDefinition):
    @property
    def workflow_name(
        self,
    ) -> str:
        return "completed_run_failure_test"

    @property
    def workflow_description(
        self,
    ) -> str:
        return "Completed run failed archive test workflow."

    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        return [
            WorkflowNodeDefinition(
                name="failing_node",
                node_type=FailingNode,
            )
        ]


def _facade_with_archive(
    archive: CompletedRunArchive,
) -> WorkflowFacade:
    facade = WorkflowFacade.create(
        archive=archive,
        config=WorkflowFacadeConfig(
            enable_checkpoints=False,
            enable_artifacts=False,
            enable_telemetry=False,
        ),
    )
    facade.register_workflow(
        SampleWorkflow(),
    )
    return facade


def _facade_with_workflows(
    archive: CompletedRunArchive,
    workflows: list[WorkflowGraphDefinition],
) -> WorkflowFacade:
    facade = WorkflowFacade.create(
        archive=archive,
        config=WorkflowFacadeConfig(
            enable_checkpoints=False,
            enable_artifacts=False,
            enable_telemetry=False,
        ),
    )
    for workflow in workflows:
        facade.register_workflow(
            workflow,
        )
    return facade


async def test_workflow_facade_completed_run_methods_are_async() -> None:
    archive = InMemoryCompletedRunArchive()
    facade = _facade_with_archive(
        archive,
    )

    result = await facade.run_workflow(
        "completed_run_async_test",
        execution_id="exec-async-1",
    )

    assert result.success is True
    assert await facade.list_completed_runs("completed_run_async_test") == [
        "exec-async-1",
    ]

    loaded = await facade.load_completed_run(
        "completed_run_async_test",
        "exec-async-1",
    )
    assert loaded is not None
    assert loaded.workflow_id == "completed_run_async_test"
    assert loaded.execution_id == "exec-async-1"
    assert loaded.node_outputs["sample_node"]["outputs"] == {"value": 42}

    assert (
        await facade.cleanup_completed_runs(
            max_age_days=7,
            max_count=100,
            confirmation=DestructiveOperationConfirmation(
                operation=DestructiveWorkflowOperation.CLEANUP_COMPLETED_RUNS,
                target="completed_runs",
                requested_by="test",
                confirmed=True,
            ),
        )
        == 0
    )
    assert archive.cleanup_calls == [(7, 100)]

    await facade.delete_completed_run(
        "completed_run_async_test",
        "exec-async-1",
        confirmation=DestructiveOperationConfirmation(
            operation=DestructiveWorkflowOperation.DELETE_COMPLETED_RUN,
            target="completed_run_async_test:exec-async-1",
            requested_by="test",
            confirmed=True,
        ),
    )
    assert (
        await facade.load_completed_run(
            "completed_run_async_test",
            "exec-async-1",
        )
        is None
    )


async def test_workflow_engine_skips_archive_when_archive_on_completion_is_false() -> (
    None
):
    archive = InMemoryCompletedRunArchive()
    facade = _facade_with_archive(
        archive,
    )

    result = await facade.run_workflow(
        "completed_run_async_test",
        execution_id="exec-skip-archive",
        archive_on_completion=False,
    )

    assert result.success is True
    assert archive.bundles == {}
    assert await facade.list_completed_runs("completed_run_async_test") == []


async def test_workflow_engine_archives_failed_completed_runs() -> None:
    archive = InMemoryCompletedRunArchive()
    facade = _facade_with_workflows(
        archive,
        [FailingWorkflow()],
    )

    result = await facade.run_workflow(
        "completed_run_failure_test",
        execution_id="exec-failed-archive",
    )

    assert result.success is False
    bundle = archive.bundles[("completed_run_failure_test", "exec-failed-archive")]
    assert bundle.run.status == "failed"
    assert bundle.run.success is False
    assert bundle.run.failed_node_count == 1
    assert bundle.node_outputs[0].node_name == "failing_node"
    assert bundle.node_outputs[0].status == "failed"
    assert bundle.node_outputs[0].errors_json == [{"message": "node failed"}]


async def test_workflow_archive_failure_is_logged_and_non_fatal(
    caplog,
) -> None:
    facade = _facade_with_archive(
        FailingCompletedRunArchive(),
    )

    with caplog.at_level(
        logging.ERROR,
        logger="core.workflow.execution.workflow_engine",
    ):
        result = await facade.run_workflow(
            "completed_run_async_test",
            execution_id="exec-archive-failure",
        )

    assert result.success is True
    assert result.execution_id == "exec-archive-failure"
    assert "Completed workflow run archival failed." in caplog.text
