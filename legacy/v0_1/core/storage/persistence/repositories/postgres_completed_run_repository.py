from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Executable

from core.database.models.completed_runs import (
    CompletedRunArtifactModel,
    CompletedWorkflowNodeOutputModel,
    CompletedWorkflowRunModel,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunArtifactRecord,
    CompletedRunBundle,
)
from core.storage.persistence.serializers.completed_run_serializer import (
    CompletedRunModelSerializer,
)


class PostgresCompletedRunRepository:
    """
    PostgreSQL repository for completed workflow run archives.

    The repository persists one canonical completed-run bundle per execution ID.
    Child node-output and artifact rows are replaced on retry so completed-run
    archival remains deterministic and idempotent.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_completed_run_bundle(
        self,
        bundle: CompletedRunBundle,
    ) -> None:
        try:
            await self._session.execute(
                _upsert_run_statement(
                    bundle,
                )
            )
            await self._replace_child_records(
                bundle,
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

    async def load_completed_run_bundle(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> CompletedRunBundle | None:
        run_stmt = select(CompletedWorkflowRunModel).where(
            CompletedWorkflowRunModel.workflow_name == workflow_name,
            CompletedWorkflowRunModel.execution_id == execution_id,
        )
        run_result = await self._session.execute(
            run_stmt,
        )
        run_model = run_result.scalar_one_or_none()
        if run_model is None:
            return None

        node_result = await self._session.execute(
            select(CompletedWorkflowNodeOutputModel)
            .where(
                CompletedWorkflowNodeOutputModel.run_id == run_model.run_id,
            )
            .order_by(
                CompletedWorkflowNodeOutputModel.node_name.asc(),
                CompletedWorkflowNodeOutputModel.node_output_id.asc(),
            )
        )
        artifact_result = await self._session.execute(
            select(CompletedRunArtifactModel)
            .where(
                CompletedRunArtifactModel.run_id == run_model.run_id,
            )
            .order_by(
                CompletedRunArtifactModel.artifact_type.asc(),
                CompletedRunArtifactModel.artifact_name.asc(),
                CompletedRunArtifactModel.artifact_id.asc(),
            )
        )

        return CompletedRunBundle(
            run=CompletedRunModelSerializer.run_from_model(
                run_model,
            ),
            node_outputs=tuple(
                CompletedRunModelSerializer.node_output_from_model(
                    model,
                )
                for model in node_result.scalars().all()
            ),
            artifacts=tuple(
                CompletedRunModelSerializer.artifact_from_model(
                    model,
                )
                for model in artifact_result.scalars().all()
            ),
        )

    async def list_completed_run_ids(
        self,
        workflow_name: str,
    ) -> list[str]:
        stmt = (
            select(CompletedWorkflowRunModel.execution_id)
            .where(
                CompletedWorkflowRunModel.workflow_name == workflow_name,
            )
            .order_by(
                CompletedWorkflowRunModel.completed_at.desc().nullslast(),
                CompletedWorkflowRunModel.created_at.desc(),
                CompletedWorkflowRunModel.execution_id.asc(),
            )
        )
        result = await self._session.execute(
            stmt,
        )

        return list(
            result.scalars().all(),
        )

    async def delete_completed_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> None:
        try:
            await self._session.execute(
                delete(CompletedWorkflowRunModel).where(
                    CompletedWorkflowRunModel.workflow_name == workflow_name,
                    CompletedWorkflowRunModel.execution_id == execution_id,
                )
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

    async def cleanup_completed_runs(
        self,
        max_age_days: int | None = None,
        max_count: int | None = None,
    ) -> int:
        deleted_count = 0
        try:
            if max_age_days is not None:
                deleted_count += await self._delete_older_than(
                    max_age_days,
                )

            if max_count is not None:
                deleted_count += await self._delete_over_count(
                    max_count,
                )

            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

        return deleted_count

    async def _replace_child_records(
        self,
        bundle: CompletedRunBundle,
    ) -> None:
        await self._session.execute(
            delete(CompletedWorkflowNodeOutputModel).where(
                CompletedWorkflowNodeOutputModel.run_id == bundle.run.run_id,
            )
        )
        await self._session.execute(
            delete(CompletedRunArtifactModel).where(
                CompletedRunArtifactModel.run_id == bundle.run.run_id,
            )
        )

        for node_output in bundle.node_outputs:
            await self._session.execute(
                _upsert_node_output_statement(
                    node_output,
                )
            )
        for artifact in bundle.artifacts:
            await self._session.execute(
                _upsert_artifact_statement(
                    artifact,
                )
            )

    async def _delete_older_than(
        self,
        max_age_days: int,
    ) -> int:
        cutoff = datetime.now(
            UTC,
        ) - timedelta(
            days=max_age_days,
        )
        result = await self._session.execute(
            delete(CompletedWorkflowRunModel).where(
                CompletedWorkflowRunModel.completed_at < cutoff,
            )
        )

        return _rowcount(
            cast(Any, result).rowcount,
        )

    async def _delete_over_count(
        self,
        max_count: int,
    ) -> int:
        if max_count < 0:
            raise ValueError("max_count cannot be negative.")

        stale_run_ids = (
            select(CompletedWorkflowRunModel.run_id)
            .order_by(
                CompletedWorkflowRunModel.completed_at.desc().nullslast(),
                CompletedWorkflowRunModel.created_at.desc(),
                CompletedWorkflowRunModel.run_id.asc(),
            )
            .offset(max_count)
            .subquery()
        )
        result = await self._session.execute(
            delete(CompletedWorkflowRunModel).where(
                CompletedWorkflowRunModel.run_id.in_(
                    select(stale_run_ids.c.run_id),
                )
            )
        )

        return _rowcount(
            cast(Any, result).rowcount,
        )


def _upsert_run_statement(
    bundle: CompletedRunBundle,
) -> Executable:
    values = CompletedRunModelSerializer.run_values(
        bundle.run,
    )
    stmt = insert(CompletedWorkflowRunModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        constraint="uq_completed_workflow_runs_execution_id",
        set_={
            "run_id": excluded.run_id,
            "workflow_name": excluded.workflow_name,
            "workflow_id": excluded.workflow_id,
            "runtime_id": excluded.runtime_id,
            "status": excluded.status,
            "success": excluded.success,
            "execution_mode": excluded.execution_mode,
            "started_at": excluded.started_at,
            "completed_at": excluded.completed_at,
            "duration_seconds": excluded.duration_seconds,
            "schema_version": excluded.schema_version,
            "context_json": excluded.context_json,
            "inputs_json": excluded.inputs_json,
            "outputs_json": excluded.outputs_json,
            "metadata": excluded.metadata,
            "errors_json": excluded.errors_json,
            "node_count": excluded.node_count,
            "completed_node_count": excluded.completed_node_count,
            "failed_node_count": excluded.failed_node_count,
            "updated_at": func.now(),
        },
    )


def _upsert_node_output_statement(
    record: CompletedNodeOutputRecord,
) -> Executable:
    values = CompletedRunModelSerializer.node_output_values(
        record,
    )
    stmt = insert(CompletedWorkflowNodeOutputModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "node_output_id",
        ],
        set_={
            "run_id": excluded.run_id,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "node_name": excluded.node_name,
            "node_type": excluded.node_type,
            "output_contract": excluded.output_contract,
            "output_schema_version": excluded.output_schema_version,
            "status": excluded.status,
            "success": excluded.success,
            "started_at": excluded.started_at,
            "completed_at": excluded.completed_at,
            "duration_seconds": excluded.duration_seconds,
            "outputs": excluded.outputs,
            "metadata": excluded.metadata,
            "errors_json": excluded.errors_json,
        },
    )


def _upsert_artifact_statement(
    record: CompletedRunArtifactRecord,
) -> Executable:
    values = CompletedRunModelSerializer.artifact_values(
        record,
    )
    stmt = insert(CompletedRunArtifactModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=[
            "artifact_id",
        ],
        set_={
            "run_id": excluded.run_id,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "artifact_type": excluded.artifact_type,
            "artifact_name": excluded.artifact_name,
            "artifact_path": excluded.artifact_path,
            "mime_type": excluded.mime_type,
            "size_bytes": excluded.size_bytes,
            "metadata": excluded.metadata,
        },
    )


def _rowcount(
    value: int | None,
) -> int:
    if value is None:
        return 0

    return value
