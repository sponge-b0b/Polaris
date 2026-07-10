from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any
from typing import cast
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from core.database.models.completed_runs import CompletedRunArtifactModel
from core.database.models.completed_runs import CompletedWorkflowNodeOutputModel
from core.database.models.completed_runs import CompletedWorkflowRunModel
from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.storage.persistence.postgres_completed_run_archive import (
    PostgresCompletedRunArchive,
)
from core.workflow.execution.workflow_facade import WorkflowFacade
from core.workflow.execution.workflow_facade import WorkflowFacadeConfig
from core.workflow.models.workflow_graph_definition import WorkflowGraphDefinition
from core.workflow.models.workflow_node_definition import WorkflowNodeDefinition

TEST_DATABASE_URL = os.environ.get("POLARIS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="POLARIS_TEST_DATABASE_URL is required for workflow archive integration tests.",
)


@pytest_asyncio.fixture
async def postgres_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: cast(
                Any, CompletedWorkflowRunModel.__table__
            ).create(
                sync_connection,
                checkfirst=True,
            )
        )
        await connection.run_sync(
            lambda sync_connection: cast(
                Any, CompletedWorkflowNodeOutputModel.__table__
            ).create(
                sync_connection,
                checkfirst=True,
            )
        )
        await connection.run_sync(
            lambda sync_connection: cast(
                Any, CompletedRunArtifactModel.__table__
            ).create(
                sync_connection,
                checkfirst=True,
            )
        )

    yield session_factory

    await engine.dispose()


class WorkflowArchiveNode(RuntimeNode):
    node_name = "workflow_archive_node"
    node_type = "workflow_archive_test"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput.success_output(
            outputs={
                "deterministic_value": 123,
            },
        )


class WorkflowArchiveTestDefinition(WorkflowGraphDefinition):
    def __init__(
        self,
        workflow_name: str,
    ) -> None:
        self._workflow_name = workflow_name

    @property
    def workflow_name(
        self,
    ) -> str:
        return self._workflow_name

    @property
    def workflow_description(
        self,
    ) -> str:
        return "PostgreSQL completed-run workflow archive integration test."

    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        return [
            WorkflowNodeDefinition(
                name="workflow_archive_node",
                node_type=WorkflowArchiveNode,
            )
        ]


@pytest.mark.asyncio
async def test_workflow_execution_archives_completed_run_to_postgres(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workflow_name = f"completed-run-workflow-{uuid4().hex}"
    execution_id = f"exec-{uuid4().hex}"
    archive = PostgresCompletedRunArchive(
        session_factory=postgres_session_factory,
    )
    facade = WorkflowFacade.create(
        archive=archive,
        config=WorkflowFacadeConfig(
            enable_checkpoints=False,
            enable_artifacts=False,
            enable_telemetry=False,
        ),
    )
    facade.register_workflow(
        WorkflowArchiveTestDefinition(
            workflow_name,
        )
    )

    try:
        result = await facade.run_workflow(
            workflow_name,
            execution_id=execution_id,
        )
        loaded = await archive.load_archived_run(
            workflow_name=workflow_name,
            execution_id=execution_id,
        )

        assert result.success is True
        assert loaded is not None
        assert loaded.run.workflow_name == workflow_name
        assert loaded.run.execution_id == execution_id
        context_json = cast(dict[str, Any], loaded.run.context_json)
        node_outputs = cast(dict[str, Any], context_json["node_outputs"])
        workflow_archive_node = cast(
            dict[str, Any],
            node_outputs["workflow_archive_node"],
        )
        assert workflow_archive_node["outputs"] == {"deterministic_value": 123}
        assert loaded.node_outputs[0].node_name == "workflow_archive_node"
        assert loaded.node_outputs[0].outputs == {"deterministic_value": 123}
    finally:
        async with postgres_session_factory() as session:
            await session.execute(
                delete(CompletedWorkflowRunModel).where(
                    CompletedWorkflowRunModel.workflow_name == workflow_name,
                )
            )
            await session.commit()
