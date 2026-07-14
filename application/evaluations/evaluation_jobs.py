from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from enum import StrEnum

from application.evaluations.contracts import EvaluationLangfuseProjectionRequest
from application.evaluations.evaluation_result_service import EvaluationResultService
from application.evaluations.evaluation_telemetry import EvaluationTelemetry
from application.evaluations.evaluation_run_service import (
    EvaluationRunScoreProjectionService,
)
from application.evaluations.evaluation_run_service import EvaluationRunService
from application.evaluations.rag_evaluation_metrics import (
    intelligence_evaluation_metric_specs,
)
from application.evaluations.rag_evaluation_metrics import rag_evaluation_metric_specs
from core.storage.persistence.evaluation import EvaluationCaseRecord
from core.storage.persistence.evaluation import EvaluationDatasetRecord
from core.storage.persistence.evaluation import EvaluationRunRecord
from domain.evaluation import EvaluationCase
from domain.evaluation import EvaluationDatasetReference
from domain.evaluation import EvaluationTargetType
from integration.providers.llm_evaluation import EvaluationMetricSpec
from application.evaluations.contracts import EvaluationRunServiceRequest

logger = logging.getLogger(__name__)


class EvaluationJobType(StrEnum):
    """Canonical asynchronous LLM-evaluation job types."""

    EVALUATE_RAG_RESULT = "evaluate_rag_result"
    EVALUATE_STRATEGY_OUTPUT = "evaluate_strategy_output"
    EVALUATE_REPORT = "evaluate_report"
    PROJECT_EVAL_SCORES_TO_LANGFUSE = "project_eval_scores_to_langfuse"
    RETRY_FAILED_EVAL_PROJECTION = "retry_failed_eval_projection"


class EvaluationJobStatus(StrEnum):
    """Lifecycle result returned by the application-level evaluation job worker."""

    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class EvaluationJobRequest:
    """Typed request for one asynchronous evaluation job.

    The request is intentionally transport- and queue-agnostic so it can be
    produced by a durable worker, scheduler, CLI, or future MCP boundary without
    introducing a second evaluation runtime.
    """

    job_id: str
    job_type: EvaluationJobType | str
    case_id: str | None = None
    run_id: str | None = None
    evaluator_provider: str | None = None
    evaluator_model: str | None = None
    timeout_seconds: float | None = None
    include_custom_rag_metrics: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "job_id", _require_non_empty(self.job_id, "job_id"))
        object.__setattr__(self, "job_type", _coerce_job_type(self.job_type))
        object.__setattr__(self, "case_id", _clean_optional(self.case_id, "case_id"))
        object.__setattr__(self, "run_id", _clean_optional(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "evaluator_provider",
            _clean_optional(self.evaluator_provider, "evaluator_provider"),
        )
        object.__setattr__(
            self,
            "evaluator_model",
            _clean_optional(self.evaluator_model, "evaluator_model"),
        )
        if self.timeout_seconds is not None and self.timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be greater than 0.0.")
        if self.job_type in _EVALUATION_JOB_TYPES:
            if self.case_id is None:
                raise ValueError("case_id is required for evaluation jobs.")
            if self.evaluator_provider is None:
                raise ValueError("evaluator_provider is required for evaluation jobs.")
            if self.evaluator_model is None:
                raise ValueError("evaluator_model is required for evaluation jobs.")
        if self.job_type in _PROJECTION_JOB_TYPES and self.run_id is None:
            raise ValueError("run_id is required for projection jobs.")


@dataclass(frozen=True, slots=True)
class EvaluationJobResult:
    """Typed outcome for one asynchronous evaluation job."""

    job_id: str
    job_type: EvaluationJobType
    status: EvaluationJobStatus
    run_id: str | None = None
    case_ids: tuple[str, ...] = ()
    metric_result_count: int = 0
    langfuse_exported_count: int = 0
    langfuse_pending_count: int = 0
    langfuse_failed_count: int = 0
    langfuse_skipped_count: int = 0
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status is EvaluationJobStatus.COMPLETED


@dataclass(frozen=True, slots=True)
class EvaluationJobBatchResult:
    """Summary of a batch of asynchronous evaluation jobs."""

    results: tuple[EvaluationJobResult, ...]

    @property
    def processed_count(self) -> int:
        return len(self.results)

    @property
    def completed_count(self) -> int:
        return sum(1 for result in self.results if result.succeeded)

    @property
    def failed_count(self) -> int:
        return sum(
            1 for result in self.results if result.status is EvaluationJobStatus.FAILED
        )

    @property
    def skipped_count(self) -> int:
        return sum(
            1 for result in self.results if result.status is EvaluationJobStatus.SKIPPED
        )


@dataclass(frozen=True, slots=True)
class EvaluationJobProcessor:
    """Process asynchronous DeepEval evaluation and Langfuse projection jobs."""

    run_service: EvaluationRunService
    result_service: EvaluationResultService
    projection_service: EvaluationRunScoreProjectionService
    telemetry: EvaluationTelemetry | None = None

    async def process(self, request: EvaluationJobRequest) -> EvaluationJobResult:
        job_type = _coerce_job_type(request.job_type)
        try:
            if job_type in _EVALUATION_JOB_TYPES:
                return await self._process_evaluation_job(request, job_type)
            if job_type in _PROJECTION_JOB_TYPES:
                return await self._process_projection_job(request, job_type)
        except Exception as exc:
            logger.exception(
                "Evaluation job failed.",
                extra={"job_id": request.job_id, "job_type": job_type.value},
            )
            return EvaluationJobResult(
                job_id=request.job_id,
                job_type=job_type,
                status=EvaluationJobStatus.FAILED,
                run_id=request.run_id,
                case_ids=() if request.case_id is None else (request.case_id,),
                error_message=str(exc),
            )
        return EvaluationJobResult(
            job_id=request.job_id,
            job_type=job_type,
            status=EvaluationJobStatus.SKIPPED,
            error_message="Unsupported evaluation job type.",
        )

    async def process_batch(
        self,
        requests: Sequence[EvaluationJobRequest],
    ) -> EvaluationJobBatchResult:
        results = tuple([await self.process(request) for request in requests])
        return EvaluationJobBatchResult(results=results)

    async def _process_evaluation_job(
        self,
        request: EvaluationJobRequest,
        job_type: EvaluationJobType,
    ) -> EvaluationJobResult:
        case_id = _required(request.case_id, "case_id")
        case_record = await self.result_service.get_case(case_id)
        if case_record is None:
            raise ValueError(f"Evaluation case not found: {case_id}.")
        dataset_record = await self._load_dataset(case_record, request, job_type)
        case = _case_from_record(case_record, dataset_record)
        _validate_case_target(job_type, case.target_type)
        metrics = _metric_specs_for_job(job_type, request.include_custom_rag_metrics)
        run_id = request.run_id or f"evaluation_run_{request.job_id}"
        result = await self.run_service.run_evaluation(
            EvaluationRunServiceRequest(
                run_id=run_id,
                target_type=case.target_type,
                cases=(case,),
                metrics=metrics,
                evaluator_provider=_required(
                    request.evaluator_provider,
                    "evaluator_provider",
                ),
                evaluator_model=_required(request.evaluator_model, "evaluator_model"),
                dataset=case.dataset,
                timeout_seconds=request.timeout_seconds,
            )
        )
        projection_result = result.langfuse_projection_result
        return EvaluationJobResult(
            job_id=request.job_id,
            job_type=job_type,
            status=EvaluationJobStatus.COMPLETED,
            run_id=result.run.run_id,
            case_ids=(case.case_id,),
            metric_result_count=result.metric_result_count,
            langfuse_exported_count=0
            if projection_result is None
            else projection_result.exported_count,
            langfuse_pending_count=0
            if projection_result is None
            else projection_result.pending_count,
            langfuse_failed_count=0
            if projection_result is None
            else projection_result.failed_count,
            langfuse_skipped_count=0
            if projection_result is None
            else projection_result.skipped_count,
        )

    async def _process_projection_job(
        self,
        request: EvaluationJobRequest,
        job_type: EvaluationJobType,
    ) -> EvaluationJobResult:
        run_id = _required(request.run_id, "run_id")
        if (
            self.telemetry is not None
            and job_type is EvaluationJobType.RETRY_FAILED_EVAL_PROJECTION
        ):
            self.telemetry.record_retry_count(
                job_id=request.job_id,
                job_type=job_type.value,
            )
        bundle = await self.result_service.get_run_results(run_id)
        if bundle is None:
            raise ValueError(f"Evaluation run not found: {run_id}.")
        if not bundle.metric_results:
            if self.telemetry is not None:
                self.telemetry.record_skipped_cases(
                    job_id=request.job_id,
                    job_type=job_type.value,
                    skipped_count=len(bundle.run.case_ids),
                    reason="no_metric_results",
                )
            return EvaluationJobResult(
                job_id=request.job_id,
                job_type=job_type,
                status=EvaluationJobStatus.SKIPPED,
                run_id=run_id,
                case_ids=bundle.run.case_ids,
                error_message="Evaluation run has no metric results to project.",
            )
        cases = await self._load_cases(bundle.run)
        projection_result = await self.projection_service.project_run_scores(
            EvaluationLangfuseProjectionRequest(
                run=bundle.run,
                metric_results=bundle.metric_results,
                cases=cases,
            )
        )
        return EvaluationJobResult(
            job_id=request.job_id,
            job_type=job_type,
            status=EvaluationJobStatus.COMPLETED,
            run_id=run_id,
            case_ids=tuple(case.case_id for case in cases) or bundle.run.case_ids,
            metric_result_count=len(bundle.metric_results),
            langfuse_exported_count=projection_result.exported_count,
            langfuse_pending_count=projection_result.pending_count,
            langfuse_failed_count=projection_result.failed_count,
            langfuse_skipped_count=projection_result.skipped_count,
        )

    async def _load_dataset(
        self,
        case_record: EvaluationCaseRecord,
        request: EvaluationJobRequest,
        job_type: EvaluationJobType,
    ) -> EvaluationDatasetRecord | None:
        if case_record.dataset_id is None:
            return None
        dataset = await self.result_service.get_dataset(case_record.dataset_id)
        if dataset is None and self.telemetry is not None:
            await self.telemetry.emit_dataset_load_failed(
                job_id=request.job_id,
                job_type=job_type.value,
                case_id=case_record.case_id,
                dataset_id=case_record.dataset_id,
            )
        return dataset

    async def _load_cases(
        self,
        run: EvaluationRunRecord,
    ) -> tuple[EvaluationCaseRecord, ...]:
        cases: list[EvaluationCaseRecord] = []
        for case_id in run.case_ids:
            case = await self.result_service.get_case(case_id)
            if case is not None:
                cases.append(case)
        return tuple(cases)


_EVALUATION_JOB_TYPES = frozenset(
    {
        EvaluationJobType.EVALUATE_RAG_RESULT,
        EvaluationJobType.EVALUATE_STRATEGY_OUTPUT,
        EvaluationJobType.EVALUATE_REPORT,
    }
)
_PROJECTION_JOB_TYPES = frozenset(
    {
        EvaluationJobType.PROJECT_EVAL_SCORES_TO_LANGFUSE,
        EvaluationJobType.RETRY_FAILED_EVAL_PROJECTION,
    }
)
_RAG_TARGET_TYPES = frozenset(
    {
        EvaluationTargetType.RAG_ANSWER,
        EvaluationTargetType.RAG_RETRIEVAL,
        EvaluationTargetType.RAG_GENERATION,
    }
)


def _metric_specs_for_job(
    job_type: EvaluationJobType,
    include_custom_rag_metrics: bool,
) -> tuple[EvaluationMetricSpec, ...]:
    if job_type is EvaluationJobType.EVALUATE_RAG_RESULT:
        return rag_evaluation_metric_specs(
            include_custom_metrics=include_custom_rag_metrics
        )
    if job_type is EvaluationJobType.EVALUATE_STRATEGY_OUTPUT:
        return intelligence_evaluation_metric_specs(
            EvaluationTargetType.STRATEGY_SYNTHESIS
        )
    if job_type is EvaluationJobType.EVALUATE_REPORT:
        return intelligence_evaluation_metric_specs(EvaluationTargetType.MORNING_REPORT)
    raise ValueError(f"Unsupported evaluation metrics job type: {job_type.value}.")


def _validate_case_target(
    job_type: EvaluationJobType,
    target_type: EvaluationTargetType,
) -> None:
    if (
        job_type is EvaluationJobType.EVALUATE_RAG_RESULT
        and target_type not in _RAG_TARGET_TYPES
    ):
        raise ValueError("evaluate_rag_result requires a RAG evaluation case.")
    if (
        job_type is EvaluationJobType.EVALUATE_STRATEGY_OUTPUT
        and target_type is not EvaluationTargetType.STRATEGY_SYNTHESIS
    ):
        raise ValueError("evaluate_strategy_output requires a strategy synthesis case.")
    if (
        job_type is EvaluationJobType.EVALUATE_REPORT
        and target_type is not EvaluationTargetType.MORNING_REPORT
    ):
        raise ValueError("evaluate_report requires a morning report case.")


def _case_from_record(
    record: EvaluationCaseRecord,
    dataset_record: EvaluationDatasetRecord | None,
) -> EvaluationCase:
    dataset = None
    if dataset_record is not None:
        dataset = EvaluationDatasetReference(
            dataset_id=dataset_record.dataset_id,
            name=dataset_record.name,
            version=dataset_record.version,
            tags=dataset_record.tags,
        )
    return EvaluationCase(
        case_id=record.case_id,
        target_type=_coerce_target_type(record.target_type),
        input_text=record.input_text,
        actual_output=record.actual_output,
        dataset=dataset,
        expected_output=record.expected_output,
        rubric=record.rubric,
        source_record_ids=record.source_record_ids,
        workflow_execution_id=record.workflow_execution_id,
        langfuse_trace_id=record.langfuse_trace_id,
        langfuse_observation_id=record.langfuse_observation_id,
        retrieval_context=record.retrieval_context,
        citation_context_ids=record.citation_context_ids,
        tags=record.tags,
        created_at=record.created_at or datetime.now(UTC),
    )


def _coerce_job_type(value: EvaluationJobType | str) -> EvaluationJobType:
    if isinstance(value, EvaluationJobType):
        return value
    return EvaluationJobType(value)


def _required(value: str | None, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required.")
    return value


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned


def _clean_optional(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty when provided.")
    return cleaned


def _coerce_target_type(value: EvaluationTargetType | str) -> EvaluationTargetType:
    if isinstance(value, EvaluationTargetType):
        return value
    return EvaluationTargetType(value)
