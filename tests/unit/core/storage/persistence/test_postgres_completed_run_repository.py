from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.completed_runs import CompletedRunArtifactModel
from core.database.models.completed_runs import CompletedWorkflowNodeOutputModel
from core.database.models.completed_runs import CompletedWorkflowRunModel
from core.storage.persistence.completed_run_archive import CompletedNodeOutputRecord
from core.storage.persistence.completed_run_archive import CompletedRunArtifactRecord
from core.storage.persistence.completed_run_archive import CompletedRunBundle
from core.storage.persistence.completed_run_archive import CompletedRunExecutionMode
from core.storage.persistence.completed_run_archive import CompletedRunRecord
from core.storage.persistence.repositories.postgres_completed_run_repository import (
    PostgresCompletedRunRepository,
)


class FakeExecuteResult:
    def __init__(
        self,
        rows: Sequence[object] | None = None,
        rowcount: int | None = None,
    ) -> None:
        self._rows = list(rows or [])
        self.rowcount = rowcount

    def scalar_one_or_none(
        self,
    ) -> object | None:
        if not self._rows:
            return None

        return self._rows[0]

    def scalars(
        self,
    ) -> FakeExecuteResult:
        return self

    def all(
        self,
    ) -> Sequence[object]:
        return tuple(
            self._rows,
        )


class FakeAsyncSession:
    def __init__(
        self,
        results: Sequence[FakeExecuteResult] | None = None,
        error: SQLAlchemyError | None = None,
    ) -> None:
        self.results = list(results or [])
        self.error = error
        self.executed: list[Any] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(
        self,
        statement: Any,
    ) -> FakeExecuteResult:
        self.executed.append(statement)

        if self.error is not None:
            raise self.error

        if self.results:
            return self.results.pop(0)

        return FakeExecuteResult()

    async def commit(
        self,
    ) -> None:
        self.commits += 1

    async def rollback(
        self,
    ) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_persist_completed_run_bundle_upserts_parent_and_replaces_children() -> (
    None
):
    session = FakeAsyncSession()
    repository = PostgresCompletedRunRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    await repository.persist_completed_run_bundle(
        _bundle(),
    )

    compiled = [_compile(statement) for statement in session.executed]

    assert session.commits == 1
    assert len(session.executed) == 5
    assert "INSERT INTO completed_workflow_runs" in compiled[0]
    assert "execution_mode" in compiled[0]
    assert "ON CONFLICT" in compiled[0]
    assert "DELETE FROM completed_workflow_node_outputs" in compiled[1]
    assert "DELETE FROM completed_run_artifacts" in compiled[2]
    assert "INSERT INTO completed_workflow_node_outputs" in compiled[3]
    assert "ON CONFLICT" in compiled[3]
    assert "INSERT INTO completed_run_artifacts" in compiled[4]
    assert "ON CONFLICT" in compiled[4]


@pytest.mark.asyncio
async def test_persist_completed_run_bundle_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(
        error=SQLAlchemyError(
            "database unavailable",
        )
    )
    repository = PostgresCompletedRunRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    with pytest.raises(SQLAlchemyError):
        await repository.persist_completed_run_bundle(
            _bundle(),
        )

    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_load_completed_run_bundle_round_trips_models_to_records() -> None:
    session = FakeAsyncSession(
        results=(
            FakeExecuteResult([_run_model()]),
            FakeExecuteResult([_node_model()]),
            FakeExecuteResult([_artifact_model()]),
        )
    )
    repository = PostgresCompletedRunRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    bundle = await repository.load_completed_run_bundle(
        workflow_name="morning_report",
        execution_id="exec-1",
    )

    assert bundle is not None
    assert bundle.run.execution_id == "exec-1"
    assert bundle.run.execution_mode is CompletedRunExecutionMode.BACKTEST
    assert bundle.run.context_json == {"state": {"score": 0.12345678901234568}}
    assert bundle.node_outputs[0].node_name == "technical_analysis"
    assert bundle.node_outputs[0].output_contract == "polaris.market.technical_analysis"
    assert bundle.node_outputs[0].output_schema_version == 1
    assert bundle.node_outputs[0].outputs == {"technical_score": 0.12345678901234568}
    assert bundle.artifacts[0].artifact_path == "reports/technical.md"


@pytest.mark.asyncio
async def test_list_completed_run_ids_orders_by_repository_query() -> None:
    session = FakeAsyncSession(results=(FakeExecuteResult(["exec-2", "exec-1"]),))
    repository = PostgresCompletedRunRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    execution_ids = await repository.list_completed_run_ids(
        "morning_report",
    )

    assert execution_ids == ["exec-2", "exec-1"]
    assert "ORDER BY" in _compile(session.executed[0])


@pytest.mark.asyncio
async def test_delete_completed_run_commits_parent_delete() -> None:
    session = FakeAsyncSession()
    repository = PostgresCompletedRunRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    await repository.delete_completed_run(
        workflow_name="morning_report",
        execution_id="exec-1",
    )

    assert session.commits == 1
    assert "DELETE FROM completed_workflow_runs" in _compile(session.executed[0])


@pytest.mark.asyncio
async def test_cleanup_completed_runs_deletes_by_age_and_count() -> None:
    session = FakeAsyncSession(
        results=(
            FakeExecuteResult(rowcount=2),
            FakeExecuteResult(rowcount=3),
        )
    )
    repository = PostgresCompletedRunRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    deleted = await repository.cleanup_completed_runs(
        max_age_days=30,
        max_count=10,
    )

    assert deleted == 5
    assert session.commits == 1
    assert len(session.executed) == 2
    assert all(
        "DELETE FROM completed_workflow_runs" in _compile(stmt)
        for stmt in session.executed
    )


def _bundle() -> CompletedRunBundle:
    return CompletedRunBundle(
        run=_run_record(),
        node_outputs=(_node_record(),),
        artifacts=(_artifact_record(),),
    )


def _run_record() -> CompletedRunRecord:
    completed_at = datetime(2026, 6, 21, 12, tzinfo=timezone.utc)
    return CompletedRunRecord(
        run_id="run-1",
        workflow_name="morning_report",
        workflow_id="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        status="succeeded",
        success=True,
        context_json={"state": {"score": 0.12345678901234568}},
        inputs_json={"symbols": ["SPY"]},
        outputs_json={"report": "full report"},
        metadata={"source": "test"},
        errors_json=[],
        started_at=completed_at,
        completed_at=completed_at,
        duration_seconds=1.2345678901234567,
        node_count=1,
        completed_node_count=1,
        failed_node_count=0,
        execution_mode=CompletedRunExecutionMode.BACKTEST,
    )


def _node_record() -> CompletedNodeOutputRecord:
    completed_at = datetime(2026, 6, 21, 12, tzinfo=timezone.utc)
    return CompletedNodeOutputRecord(
        node_output_id="node-output-1",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="technical_analysis",
        node_type="runtime",
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
        status="succeeded",
        success=True,
        outputs={"technical_score": 0.12345678901234568},
        metadata={"attempt": 1},
        errors_json=[],
        started_at=completed_at,
        completed_at=completed_at,
        duration_seconds=1.2345678901234567,
    )


def _artifact_record() -> CompletedRunArtifactRecord:
    return CompletedRunArtifactRecord(
        artifact_id="artifact-1",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        artifact_type="markdown",
        artifact_name="technical.md",
        artifact_path="reports/technical.md",
        mime_type="text/markdown",
        size_bytes=2048,
        metadata={"source": "test"},
    )


def _run_model() -> CompletedWorkflowRunModel:
    record = _run_record()
    return CompletedWorkflowRunModel(
        run_id=record.run_id,
        workflow_name=record.workflow_name,
        workflow_id=record.workflow_id,
        execution_id=record.execution_id,
        runtime_id=record.runtime_id,
        status=record.status,
        success=record.success,
        started_at=record.started_at,
        completed_at=record.completed_at,
        duration_seconds=record.duration_seconds,
        schema_version=record.schema_version,
        context_json=dict(record.context_json),
        inputs_json=dict(record.inputs_json),
        outputs_json=dict(record.outputs_json),
        metadata_payload=dict(record.metadata),
        errors_json=list(record.errors_json),
        node_count=record.node_count,
        completed_node_count=record.completed_node_count,
        failed_node_count=record.failed_node_count,
        execution_mode="backtest",
    )


def _node_model() -> CompletedWorkflowNodeOutputModel:
    record = _node_record()
    return CompletedWorkflowNodeOutputModel(
        node_output_id=record.node_output_id,
        run_id=record.run_id,
        workflow_name=record.workflow_name,
        execution_id=record.execution_id,
        node_name=record.node_name,
        node_type=record.node_type,
        output_contract=record.output_contract,
        output_schema_version=record.output_schema_version,
        status=record.status,
        success=record.success,
        started_at=record.started_at,
        completed_at=record.completed_at,
        duration_seconds=record.duration_seconds,
        outputs_payload=dict(record.outputs),
        metadata_payload=dict(record.metadata),
        errors_json=list(record.errors_json),
    )


def _artifact_model() -> CompletedRunArtifactModel:
    record = _artifact_record()
    return CompletedRunArtifactModel(
        artifact_id=record.artifact_id,
        run_id=record.run_id,
        workflow_name=record.workflow_name,
        execution_id=record.execution_id,
        artifact_type=record.artifact_type,
        artifact_name=record.artifact_name,
        artifact_path=record.artifact_path,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        metadata_payload=dict(record.metadata),
    )


def _compile(
    statement: Any,
) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
        )
    )
