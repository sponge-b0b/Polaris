from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from sqlalchemy import Select
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Executable

from core.database.models.evaluation import EvaluationArtifactModel
from core.database.models.evaluation import EvaluationCaseModel
from core.database.models.evaluation import EvaluationDatasetModel
from core.database.models.evaluation import EvaluationMetricResultModel
from core.database.models.evaluation import EvaluationRunModel
from core.storage.persistence.evaluation import EvaluationArtifactRecord
from core.storage.persistence.evaluation import EvaluationCaseRecord
from core.storage.persistence.evaluation import EvaluationDatasetRecord
from core.storage.persistence.evaluation import EvaluationMetricResultRecord
from core.storage.persistence.evaluation import EvaluationPersistenceBundle
from core.storage.persistence.evaluation import EvaluationPersistenceResult
from core.storage.persistence.evaluation import EvaluationRunRecord
from core.storage.persistence.evaluation import JsonObject
from core.storage.persistence.evaluation import LangfuseProjectionStatus
from domain.evaluation import EvaluationStatus
from domain.evaluation import EvaluationTargetType


class PostgresEvaluationPersistenceRepository:
    """PostgreSQL repository for canonical Polaris LLM evaluation records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist_evaluation_bundle(
        self,
        bundle: EvaluationPersistenceBundle,
    ) -> EvaluationPersistenceResult:
        try:
            datasets_written = await self._upsert_records(
                tuple(_upsert_dataset_statement(record) for record in bundle.datasets)
            )
            cases_written = await self._upsert_records(
                tuple(_upsert_case_statement(record) for record in bundle.cases)
            )
            runs_written = await self._upsert_records(
                tuple(_upsert_run_statement(record) for record in bundle.runs)
            )
            metric_results_written = await self._upsert_records(
                tuple(
                    _upsert_metric_result_statement(record)
                    for record in bundle.metric_results
                )
            )
            artifacts_written = await self._upsert_records(
                tuple(_upsert_artifact_statement(record) for record in bundle.artifacts)
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

        return EvaluationPersistenceResult(
            datasets_written=datasets_written,
            cases_written=cases_written,
            runs_written=runs_written,
            metric_results_written=metric_results_written,
            artifacts_written=artifacts_written,
        )

    async def upsert_dataset(
        self,
        record: EvaluationDatasetRecord,
    ) -> EvaluationDatasetRecord:
        try:
            result = await self._session.execute(_upsert_dataset_statement(record))
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise
        return _dataset_record_from_model(result.scalar_one())

    async def upsert_case(
        self,
        record: EvaluationCaseRecord,
    ) -> EvaluationCaseRecord:
        try:
            result = await self._session.execute(_upsert_case_statement(record))
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise
        return _case_record_from_model(result.scalar_one())

    async def upsert_run(
        self,
        record: EvaluationRunRecord,
    ) -> EvaluationRunRecord:
        try:
            result = await self._session.execute(_upsert_run_statement(record))
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise
        return _run_record_from_model(result.scalar_one())

    async def upsert_metric_result(
        self,
        record: EvaluationMetricResultRecord,
    ) -> EvaluationMetricResultRecord:
        try:
            result = await self._session.execute(
                _upsert_metric_result_statement(record)
            )
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise
        return _metric_result_record_from_model(result.scalar_one())

    async def create_artifact(
        self,
        record: EvaluationArtifactRecord,
    ) -> EvaluationArtifactRecord:
        try:
            result = await self._session.execute(_upsert_artifact_statement(record))
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise
        return _artifact_record_from_model(result.scalar_one())

    async def get_dataset(
        self,
        dataset_id: str,
    ) -> EvaluationDatasetRecord | None:
        result = await self._session.execute(
            select(EvaluationDatasetModel).where(
                EvaluationDatasetModel.dataset_id
                == _require_non_empty(dataset_id, "dataset_id")
            )
        )
        model = result.scalar_one_or_none()
        return None if model is None else _dataset_record_from_model(model)

    async def get_case(
        self,
        case_id: str,
    ) -> EvaluationCaseRecord | None:
        result = await self._session.execute(
            select(EvaluationCaseModel).where(
                EvaluationCaseModel.case_id == _require_non_empty(case_id, "case_id")
            )
        )
        model = result.scalar_one_or_none()
        return None if model is None else _case_record_from_model(model)

    async def get_run(
        self,
        run_id: str,
    ) -> EvaluationRunRecord | None:
        result = await self._session.execute(
            select(EvaluationRunModel).where(
                EvaluationRunModel.run_id == _require_non_empty(run_id, "run_id")
            )
        )
        model = result.scalar_one_or_none()
        return None if model is None else _run_record_from_model(model)

    async def list_cases_by_dataset(
        self,
        dataset_id: str,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]:
        result = await self._session.execute(
            _cases_by_dataset_select(dataset_id, limit=limit)
        )
        return tuple(_case_record_from_model(model) for model in result.scalars().all())

    async def list_cases_by_target_type(
        self,
        target_type: EvaluationTargetType,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]:
        result = await self._session.execute(
            _cases_by_target_type_select(target_type, limit=limit)
        )
        return tuple(_case_record_from_model(model) for model in result.scalars().all())

    async def list_metric_results(
        self,
        run_id: str,
    ) -> Sequence[EvaluationMetricResultRecord]:
        result = await self._session.execute(_metric_results_select(run_id))
        return tuple(
            _metric_result_record_from_model(model) for model in result.scalars().all()
        )

    async def list_artifacts(
        self,
        run_id: str,
    ) -> Sequence[EvaluationArtifactRecord]:
        result = await self._session.execute(_artifacts_select(run_id))
        return tuple(
            _artifact_record_from_model(model) for model in result.scalars().all()
        )

    async def _upsert_records(self, statements: Sequence[Executable]) -> int:
        count = 0
        for stmt in statements:
            result = await self._session.execute(stmt)
            result.scalar_one()
            count += 1
        return count


def _upsert_dataset_statement(record: EvaluationDatasetRecord) -> Executable:
    values = _dataset_values(record)
    stmt = insert(EvaluationDatasetModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=[EvaluationDatasetModel.dataset_id],
        set_={
            "name": excluded.name,
            "version": excluded.version,
            "target_type": excluded.target_type,
            "description": excluded.description,
            "tags": excluded.tags,
            "source_lineage": excluded.source_lineage,
            "deterministic_fixture_uri": excluded.deterministic_fixture_uri,
            "threshold_profile": excluded.threshold_profile,
            "active": excluded.active,
            "updated_at": excluded.updated_at,
        },
    ).returning(EvaluationDatasetModel)


def _upsert_case_statement(record: EvaluationCaseRecord) -> Executable:
    values = _case_values(record)
    stmt = insert(EvaluationCaseModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=[EvaluationCaseModel.case_id],
        set_={
            "dataset_id": excluded.dataset_id,
            "target_type": excluded.target_type,
            "input_text": excluded.input_text,
            "actual_output": excluded.actual_output,
            "expected_output": excluded.expected_output,
            "rubric": excluded.rubric,
            "source_record_ids": excluded.source_record_ids,
            "workflow_execution_id": excluded.workflow_execution_id,
            "langfuse_trace_id": excluded.langfuse_trace_id,
            "langfuse_observation_id": excluded.langfuse_observation_id,
            "retrieval_context": excluded.retrieval_context,
            "citation_context_ids": excluded.citation_context_ids,
            "tags": excluded.tags,
            "updated_at": excluded.updated_at,
        },
    ).returning(EvaluationCaseModel)


def _upsert_run_statement(record: EvaluationRunRecord) -> Executable:
    values = _run_values(record)
    stmt = insert(EvaluationRunModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=[EvaluationRunModel.run_id],
        set_={
            "dataset_id": excluded.dataset_id,
            "target_type": excluded.target_type,
            "status": excluded.status,
            "evaluator_provider": excluded.evaluator_provider,
            "evaluator_model": excluded.evaluator_model,
            "case_ids": excluded.case_ids,
            "langfuse_projection_status": excluded.langfuse_projection_status,
            "langfuse_export_job_id": excluded.langfuse_export_job_id,
            "started_at": excluded.started_at,
            "completed_at": excluded.completed_at,
            "error_message": excluded.error_message,
            "error_details": excluded.error_details,
            "updated_at": excluded.updated_at,
        },
    ).returning(EvaluationRunModel)


def _upsert_metric_result_statement(record: EvaluationMetricResultRecord) -> Executable:
    values = _metric_result_values(record)
    stmt = insert(EvaluationMetricResultModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        constraint="uq_evaluation_metric_results_run_case_metric",
        set_={
            "metric_result_id": excluded.metric_result_id,
            "score": excluded.score,
            "threshold": excluded.threshold,
            "threshold_version": excluded.threshold_version,
            "passed": excluded.passed,
            "reason": excluded.reason,
            "status": excluded.status,
            "evaluator_provider": excluded.evaluator_provider,
            "evaluator_model": excluded.evaluator_model,
            "duration_ms": excluded.duration_ms,
            "error_message": excluded.error_message,
            "error_details": excluded.error_details,
            "langfuse_projection_status": excluded.langfuse_projection_status,
            "langfuse_export_job_id": excluded.langfuse_export_job_id,
            "updated_at": excluded.updated_at,
        },
    ).returning(EvaluationMetricResultModel)


def _upsert_artifact_statement(record: EvaluationArtifactRecord) -> Executable:
    values = _artifact_values(record)
    stmt = insert(EvaluationArtifactModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=[EvaluationArtifactModel.artifact_id],
        set_={
            "run_id": excluded.run_id,
            "case_id": excluded.case_id,
            "artifact_type": excluded.artifact_type,
            "uri": excluded.uri,
            "payload": excluded.payload,
        },
    ).returning(EvaluationArtifactModel)


def _cases_by_dataset_select(
    dataset_id: str,
    *,
    limit: int | None,
) -> Select[tuple[EvaluationCaseModel]]:
    stmt = (
        select(EvaluationCaseModel)
        .where(
            EvaluationCaseModel.dataset_id
            == _require_non_empty(dataset_id, "dataset_id")
        )
        .order_by(
            EvaluationCaseModel.created_at.desc(),
            EvaluationCaseModel.case_id.asc(),
        )
    )
    return _apply_limit(stmt, limit)


def _cases_by_target_type_select(
    target_type: EvaluationTargetType,
    *,
    limit: int | None,
) -> Select[tuple[EvaluationCaseModel]]:
    stmt = (
        select(EvaluationCaseModel)
        .where(EvaluationCaseModel.target_type == _target_type_value(target_type))
        .order_by(
            EvaluationCaseModel.created_at.desc(),
            EvaluationCaseModel.case_id.asc(),
        )
    )
    return _apply_limit(stmt, limit)


def _apply_limit(
    stmt: Select[tuple[EvaluationCaseModel]],
    limit: int | None,
) -> Select[tuple[EvaluationCaseModel]]:
    if limit is None:
        return stmt
    if limit <= 0:
        raise ValueError("limit must be greater than 0.")
    return stmt.limit(limit)


def _metric_results_select(
    run_id: str,
) -> Select[tuple[EvaluationMetricResultModel]]:
    return (
        select(EvaluationMetricResultModel)
        .where(
            EvaluationMetricResultModel.run_id == _require_non_empty(run_id, "run_id")
        )
        .order_by(
            EvaluationMetricResultModel.case_id.asc(),
            EvaluationMetricResultModel.metric_name.asc(),
        )
    )


def _artifacts_select(run_id: str) -> Select[tuple[EvaluationArtifactModel]]:
    return (
        select(EvaluationArtifactModel)
        .where(EvaluationArtifactModel.run_id == _require_non_empty(run_id, "run_id"))
        .order_by(
            EvaluationArtifactModel.created_at.asc(),
            EvaluationArtifactModel.artifact_id.asc(),
        )
    )


def _dataset_values(record: EvaluationDatasetRecord) -> dict[str, object]:
    target_type = _target_type_value(record.target_type)
    values: dict[str, object] = {
        "dataset_id": record.dataset_id,
        "name": record.name,
        "version": record.version,
        "target_type": target_type,
        "description": record.description,
        "tags": list(record.tags),
        "source_lineage": list(record.source_lineage),
        "deterministic_fixture_uri": record.deterministic_fixture_uri,
        "threshold_profile": None
        if record.threshold_profile is None
        else dict(record.threshold_profile),
        "active": record.active,
    }
    _include_optional_timestamps(values, record.created_at, record.updated_at)
    return values


def _case_values(record: EvaluationCaseRecord) -> dict[str, object]:
    values: dict[str, object] = {
        "case_id": record.case_id,
        "dataset_id": record.dataset_id,
        "target_type": _target_type_value(record.target_type),
        "input_text": record.input_text,
        "actual_output": record.actual_output,
        "expected_output": record.expected_output,
        "rubric": record.rubric,
        "source_record_ids": list(record.source_record_ids),
        "workflow_execution_id": record.workflow_execution_id,
        "langfuse_trace_id": record.langfuse_trace_id,
        "langfuse_observation_id": record.langfuse_observation_id,
        "retrieval_context": list(record.retrieval_context),
        "citation_context_ids": list(record.citation_context_ids),
        "tags": list(record.tags),
    }
    _include_optional_timestamps(values, record.created_at, record.updated_at)
    return values


def _run_values(record: EvaluationRunRecord) -> dict[str, object]:
    values: dict[str, object] = {
        "run_id": record.run_id,
        "dataset_id": record.dataset_id,
        "target_type": _target_type_value(record.target_type),
        "status": _status_value(record.status),
        "evaluator_provider": record.evaluator_provider,
        "evaluator_model": record.evaluator_model,
        "case_ids": list(record.case_ids),
        "langfuse_projection_status": _langfuse_projection_status_value(
            record.langfuse_projection_status
        ),
        "langfuse_export_job_id": record.langfuse_export_job_id,
        "completed_at": record.completed_at,
        "error_message": record.error_message,
        "error_details": None
        if record.error_details is None
        else dict(record.error_details),
    }
    if record.started_at is not None:
        values["started_at"] = record.started_at
    _include_optional_timestamps(values, record.created_at, record.updated_at)
    return values


def _metric_result_values(record: EvaluationMetricResultRecord) -> dict[str, object]:
    values: dict[str, object] = {
        "metric_result_id": record.metric_result_id,
        "run_id": record.run_id,
        "case_id": record.case_id,
        "metric_name": record.metric_name,
        "score": record.score,
        "threshold": record.threshold,
        "threshold_version": record.threshold_version,
        "passed": record.passed,
        "reason": record.reason,
        "status": _status_value(record.status),
        "evaluator_provider": record.evaluator_provider,
        "evaluator_model": record.evaluator_model,
        "duration_ms": record.duration_ms,
        "error_message": record.error_message,
        "error_details": None
        if record.error_details is None
        else dict(record.error_details),
        "langfuse_projection_status": _langfuse_projection_status_value(
            record.langfuse_projection_status
        ),
        "langfuse_export_job_id": record.langfuse_export_job_id,
    }
    _include_optional_timestamps(values, record.created_at, record.updated_at)
    return values


def _artifact_values(record: EvaluationArtifactRecord) -> dict[str, object]:
    values: dict[str, object] = {
        "artifact_id": record.artifact_id,
        "run_id": record.run_id,
        "case_id": record.case_id,
        "artifact_type": record.artifact_type,
        "uri": record.uri,
        "payload": None if record.payload is None else dict(record.payload),
    }
    if record.created_at is not None:
        values["created_at"] = record.created_at
    return values


def _dataset_record_from_model(
    model: EvaluationDatasetModel,
) -> EvaluationDatasetRecord:
    return EvaluationDatasetRecord(
        dataset_id=model.dataset_id,
        name=model.name,
        version=model.version,
        target_type=model.target_type,
        description=model.description,
        tags=tuple(model.tags),
        source_lineage=tuple(model.source_lineage),
        deterministic_fixture_uri=model.deterministic_fixture_uri,
        threshold_profile=cast(JsonObject | None, model.threshold_profile),
        active=model.active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _case_record_from_model(model: EvaluationCaseModel) -> EvaluationCaseRecord:
    return EvaluationCaseRecord(
        case_id=model.case_id,
        dataset_id=model.dataset_id,
        target_type=model.target_type,
        input_text=model.input_text,
        actual_output=model.actual_output,
        expected_output=model.expected_output,
        rubric=model.rubric,
        source_record_ids=tuple(model.source_record_ids),
        workflow_execution_id=model.workflow_execution_id,
        langfuse_trace_id=model.langfuse_trace_id,
        langfuse_observation_id=model.langfuse_observation_id,
        retrieval_context=tuple(model.retrieval_context),
        citation_context_ids=tuple(model.citation_context_ids),
        tags=tuple(model.tags),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _run_record_from_model(model: EvaluationRunModel) -> EvaluationRunRecord:
    return EvaluationRunRecord(
        run_id=model.run_id,
        dataset_id=model.dataset_id,
        target_type=model.target_type,
        status=model.status,
        evaluator_provider=model.evaluator_provider,
        evaluator_model=model.evaluator_model,
        case_ids=tuple(model.case_ids),
        langfuse_projection_status=model.langfuse_projection_status,
        langfuse_export_job_id=model.langfuse_export_job_id,
        started_at=model.started_at,
        completed_at=model.completed_at,
        error_message=model.error_message,
        error_details=cast(JsonObject | None, model.error_details),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _metric_result_record_from_model(
    model: EvaluationMetricResultModel,
) -> EvaluationMetricResultRecord:
    return EvaluationMetricResultRecord(
        metric_result_id=model.metric_result_id,
        run_id=model.run_id,
        case_id=model.case_id,
        metric_name=model.metric_name,
        score=model.score,
        threshold=model.threshold,
        threshold_version=model.threshold_version,
        passed=model.passed,
        reason=model.reason,
        status=model.status,
        evaluator_provider=model.evaluator_provider,
        evaluator_model=model.evaluator_model,
        duration_ms=model.duration_ms,
        error_message=model.error_message,
        error_details=cast(JsonObject | None, model.error_details),
        langfuse_projection_status=model.langfuse_projection_status,
        langfuse_export_job_id=model.langfuse_export_job_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _artifact_record_from_model(
    model: EvaluationArtifactModel,
) -> EvaluationArtifactRecord:
    return EvaluationArtifactRecord(
        artifact_id=model.artifact_id,
        run_id=model.run_id,
        case_id=model.case_id,
        artifact_type=model.artifact_type,
        uri=model.uri,
        payload=cast(JsonObject | None, model.payload),
        created_at=model.created_at,
    )


def _include_optional_timestamps(
    values: dict[str, object],
    created_at: object | None,
    updated_at: object | None,
) -> None:
    if created_at is not None:
        values["created_at"] = created_at
    if updated_at is not None:
        values["updated_at"] = updated_at


def _target_type_value(value: EvaluationTargetType | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, EvaluationTargetType):
        return value.value
    return value


def _status_value(value: EvaluationStatus | str) -> str:
    if isinstance(value, EvaluationStatus):
        return value.value
    return value


def _langfuse_projection_status_value(value: LangfuseProjectionStatus | str) -> str:
    if isinstance(value, LangfuseProjectionStatus):
        return value.value
    return value


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned
