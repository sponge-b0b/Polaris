from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import Select, func, null, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Executable

from core.database.models.ai_artifacts import AiPromptProgramArtifactModel
from core.storage.persistence.ai_artifacts import (
    AiArtifactApprovalStatus,
    AiArtifactType,
    AiPromptProgramArtifactRecord,
    JsonObject,
    approval_status_value,
    artifact_type_value,
)


class PostgresAiArtifactPersistenceRepository:
    """PostgreSQL repository for approved AI prompt/program artifacts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_artifact(
        self,
        record: AiPromptProgramArtifactRecord,
    ) -> AiPromptProgramArtifactRecord:
        try:
            result = await self._session.execute(_upsert_artifact_statement(record))
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise
        return _artifact_record_from_model(result.scalar_one())

    async def get_artifact(
        self,
        artifact_id: str,
    ) -> AiPromptProgramArtifactRecord | None:
        result = await self._session.execute(
            select(AiPromptProgramArtifactModel).where(
                AiPromptProgramArtifactModel.artifact_id
                == _require_non_empty(artifact_id, "artifact_id")
            )
        )
        model = result.scalar_one_or_none()
        return None if model is None else _artifact_record_from_model(model)

    async def list_artifacts(
        self,
        *,
        target_component: str | None = None,
        artifact_type: AiArtifactType | str | None = None,
        active: bool | None = None,
        limit: int | None = None,
    ) -> Sequence[AiPromptProgramArtifactRecord]:
        result = await self._session.execute(
            _artifacts_select(
                target_component=target_component,
                artifact_type=artifact_type,
                active=active,
                limit=limit,
            )
        )
        return tuple(
            _artifact_record_from_model(model) for model in result.scalars().all()
        )

    async def get_active_artifact(
        self,
        target_component: str,
        *,
        artifact_type: AiArtifactType | str | None = None,
    ) -> AiPromptProgramArtifactRecord | None:
        result = await self._session.execute(
            _artifacts_select(
                target_component=target_component,
                artifact_type=artifact_type,
                active=True,
                limit=1,
            )
        )
        model = result.scalar_one_or_none()
        return None if model is None else _artifact_record_from_model(model)

    async def approve_artifact(
        self,
        artifact_id: str,
        *,
        approved_by: str,
        approved_at: datetime,
    ) -> AiPromptProgramArtifactRecord | None:
        try:
            result = await self._session.execute(
                update(AiPromptProgramArtifactModel)
                .where(
                    AiPromptProgramArtifactModel.artifact_id
                    == _require_non_empty(artifact_id, "artifact_id")
                )
                .values(
                    approval_status=AiArtifactApprovalStatus.APPROVED.value,
                    approved_by=_require_non_empty(approved_by, "approved_by"),
                    approved_at=approved_at,
                    active=False,
                    updated_at=func.now(),
                )
                .returning(AiPromptProgramArtifactModel)
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise
        model = result.scalar_one_or_none()
        return None if model is None else _artifact_record_from_model(model)

    async def deactivate_artifact(
        self,
        artifact_id: str,
    ) -> AiPromptProgramArtifactRecord | None:
        try:
            result = await self._session.execute(
                update(AiPromptProgramArtifactModel)
                .where(
                    AiPromptProgramArtifactModel.artifact_id
                    == _require_non_empty(artifact_id, "artifact_id")
                )
                .values(
                    approval_status=AiArtifactApprovalStatus.INACTIVE.value,
                    active=False,
                    updated_at=func.now(),
                )
                .returning(AiPromptProgramArtifactModel)
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise
        model = result.scalar_one_or_none()
        return None if model is None else _artifact_record_from_model(model)


def _upsert_artifact_statement(record: AiPromptProgramArtifactRecord) -> Executable:
    values = _artifact_values(record)
    stmt = insert(AiPromptProgramArtifactModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=[AiPromptProgramArtifactModel.artifact_id],
        set_={
            "artifact_type": excluded.artifact_type,
            "artifact_name": excluded.artifact_name,
            "artifact_version": excluded.artifact_version,
            "target_component": excluded.target_component,
            "model_name": excluded.model_name,
            "provider_name": excluded.provider_name,
            "prompt_reference": excluded.prompt_reference,
            "prompt_hash": excluded.prompt_hash,
            "source": excluded.source,
            "evaluation_dataset_id": excluded.evaluation_dataset_id,
            "evaluation_run_id": excluded.evaluation_run_id,
            "deepeval_score_summary": excluded.deepeval_score_summary,
            "langfuse_trace_id": excluded.langfuse_trace_id,
            "approval_status": excluded.approval_status,
            "approved_by": excluded.approved_by,
            "approved_at": excluded.approved_at,
            "active": excluded.active,
            "updated_at": func.now(),
        },
    ).returning(AiPromptProgramArtifactModel)


def _artifacts_select(
    *,
    target_component: str | None,
    artifact_type: AiArtifactType | str | None,
    active: bool | None,
    limit: int | None,
) -> Select[tuple[AiPromptProgramArtifactModel]]:
    stmt = select(AiPromptProgramArtifactModel)
    if target_component is not None:
        stmt = stmt.where(
            AiPromptProgramArtifactModel.target_component
            == _require_non_empty(target_component, "target_component")
        )
    if artifact_type is not None:
        stmt = stmt.where(
            AiPromptProgramArtifactModel.artifact_type
            == artifact_type_value(artifact_type)
        )
    if active is not None:
        stmt = stmt.where(AiPromptProgramArtifactModel.active.is_(active))
    stmt = stmt.order_by(
        AiPromptProgramArtifactModel.approved_at.desc().nullslast(),
        AiPromptProgramArtifactModel.created_at.desc(),
        AiPromptProgramArtifactModel.artifact_id.asc(),
    )
    if limit is None:
        return stmt
    if limit <= 0:
        raise ValueError("limit must be greater than 0.")
    return stmt.limit(limit)


def _artifact_values(record: AiPromptProgramArtifactRecord) -> dict[str, object]:
    values: dict[str, object] = {
        "artifact_id": record.artifact_id,
        "artifact_type": artifact_type_value(record.artifact_type),
        "artifact_name": record.artifact_name,
        "artifact_version": record.artifact_version,
        "target_component": record.target_component,
        "model_name": record.model_name,
        "provider_name": record.provider_name,
        "prompt_reference": record.prompt_reference,
        "prompt_hash": record.prompt_hash,
        "source": record.source,
        "evaluation_dataset_id": record.evaluation_dataset_id,
        "evaluation_run_id": record.evaluation_run_id,
        "deepeval_score_summary": _nullable_json_object(record.deepeval_score_summary),
        "langfuse_trace_id": record.langfuse_trace_id,
        "approval_status": approval_status_value(record.approval_status),
        "approved_by": record.approved_by,
        "approved_at": record.approved_at,
        "active": record.active,
    }
    _include_optional_timestamps(values, record.created_at, record.updated_at)
    return values


def _nullable_json_object(value: JsonObject | None) -> object:
    if value is None:
        return null()
    return dict(value)


def _include_optional_timestamps(
    values: dict[str, object],
    created_at: object | None,
    updated_at: object | None,
) -> None:
    if created_at is not None:
        values["created_at"] = created_at
    if updated_at is not None:
        values["updated_at"] = updated_at


def _artifact_record_from_model(
    model: AiPromptProgramArtifactModel,
) -> AiPromptProgramArtifactRecord:
    return AiPromptProgramArtifactRecord(
        artifact_id=model.artifact_id,
        artifact_type=model.artifact_type,
        artifact_name=model.artifact_name,
        artifact_version=model.artifact_version,
        target_component=model.target_component,
        model_name=model.model_name,
        provider_name=model.provider_name,
        prompt_reference=model.prompt_reference,
        prompt_hash=model.prompt_hash,
        source=model.source,
        evaluation_dataset_id=model.evaluation_dataset_id,
        evaluation_run_id=model.evaluation_run_id,
        deepeval_score_summary=cast(JsonObject | None, model.deepeval_score_summary),
        langfuse_trace_id=model.langfuse_trace_id,
        approval_status=model.approval_status,
        approved_by=model.approved_by,
        approved_at=model.approved_at,
        active=model.active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned
