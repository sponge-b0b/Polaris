from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol

from application.evaluations.contracts import EvaluationLangfuseProjectionRequest
from application.evaluations.contracts import EvaluationLangfuseProjectionResult
from application.observability.ai_observability_contracts import AiEvaluationObservation
from application.observability.ai_observability_contracts import (
    AiObservabilityCorrelationIds,
)
from application.observability.ai_observability_contracts import (
    AiObservabilityExportResult,
)
from application.observability.ai_observability_contracts import (
    AiObservabilityExportStatus,
)
from application.observability.ai_observability_contracts import AiObservationStatus
from application.observability.ai_observability_contracts import AiObservationType
from application.observability.ai_observability_contracts import AiScoreProjection
from application.observability.ai_observability_contracts import AiScoreResult
from core.storage.persistence.evaluation import EvaluationCaseRecord
from core.storage.persistence.evaluation import EvaluationMetricResultRecord
from core.storage.persistence.evaluation import EvaluationRunRecord
from domain.evaluation import EvaluationStatus
from domain.evaluation import EvaluationTargetType

logger = logging.getLogger(__name__)


class EvaluationScoreProjector(Protocol):
    async def project(
        self,
        observation: AiEvaluationObservation,
    ) -> AiObservabilityExportResult: ...


@dataclass(frozen=True, slots=True)
class EvaluationLangfuseProjectionService:
    """Project canonical DeepEval metric results into Langfuse observability."""

    projector: EvaluationScoreProjector

    async def project_run_scores(
        self,
        request: EvaluationLangfuseProjectionRequest,
    ) -> EvaluationLangfuseProjectionResult:
        observations = _build_evaluation_observations(request)
        export_results: list[AiObservabilityExportResult] = []
        failed_count = 0
        for observation in observations:
            try:
                export_result = await self.projector.project(observation)
            except Exception as exc:
                logger.exception(
                    "Langfuse evaluation-score projection failed.",
                    extra={
                        "run_id": request.run.run_id,
                        "observation_id": observation.correlation_ids.observation_id,
                    },
                )
                export_result = AiObservabilityExportResult.failed(
                    idempotency_key=observation.idempotency_key(),
                    error_message=str(exc),
                )
            export_results.append(export_result)
            if export_result.status is AiObservabilityExportStatus.FAILED:
                failed_count += 1
        return EvaluationLangfuseProjectionResult(
            export_results=tuple(export_results),
            exported_count=sum(
                1
                for result in export_results
                if result.status is AiObservabilityExportStatus.EXPORTED
            ),
            pending_count=sum(
                1
                for result in export_results
                if result.status is AiObservabilityExportStatus.PENDING
            ),
            failed_count=failed_count,
            skipped_count=0 if observations else len(request.metric_results),
        )


def _build_evaluation_observations(
    request: EvaluationLangfuseProjectionRequest,
) -> tuple[AiEvaluationObservation, ...]:
    metric_results_by_case: dict[str, list[EvaluationMetricResultRecord]] = defaultdict(
        list
    )
    for metric_result in request.metric_results:
        metric_results_by_case[metric_result.case_id].append(metric_result)
    cases_by_id = {case.case_id: case for case in request.cases}
    observations: list[AiEvaluationObservation] = []
    for case_id, metric_results in sorted(metric_results_by_case.items()):
        case = cases_by_id.get(case_id)
        observations.append(
            _build_case_observation(request.run, case, tuple(metric_results))
        )
    return tuple(observations)


def _build_case_observation(
    run: EvaluationRunRecord,
    case: EvaluationCaseRecord | None,
    metric_results: tuple[EvaluationMetricResultRecord, ...],
) -> AiEvaluationObservation:
    case_id = metric_results[0].case_id if case is None else case.case_id
    target_type = EvaluationTargetType(run.target_type)
    return AiEvaluationObservation(
        observation_type=_observation_type_for(target_type),
        name=f"evaluation.{target_type.value}.{case_id}",
        correlation_ids=AiObservabilityCorrelationIds(
            trace_id=None if case is None else case.langfuse_trace_id,
            observation_id=f"evaluation:{run.run_id}:{case_id}",
            parent_observation_id=None
            if case is None
            else case.langfuse_observation_id,
            dataset_id=run.dataset_id,
            case_id=case_id,
            run_id=run.run_id,
        ),
        status=_observation_status(metric_results),
        model_name=run.evaluator_model,
        provider_name=run.evaluator_provider,
        latency_ms=_total_duration_ms(metric_results),
        output_shape="evaluation_metric_results",
        metadata={"target_type": target_type.value},
        scores=tuple(
            _score_projection(metric_result) for metric_result in metric_results
        ),
        evaluated_observation_id=None if case is None else case.langfuse_observation_id,
    )


def _score_projection(metric_result: EvaluationMetricResultRecord) -> AiScoreProjection:
    return AiScoreProjection(
        metric_name=metric_result.metric_name,
        score=metric_result.score,
        result=_score_result(metric_result),
        threshold=metric_result.threshold,
        reason=metric_result.reason,
        evaluator_model=metric_result.evaluator_model,
        evaluator_provider=metric_result.evaluator_provider,
    )


def _score_result(metric_result: EvaluationMetricResultRecord) -> AiScoreResult:
    if metric_result.status is EvaluationStatus.ERRORED:
        return AiScoreResult.UNKNOWN
    if metric_result.passed is True:
        return AiScoreResult.PASS
    if metric_result.passed is False:
        return AiScoreResult.FAIL
    return AiScoreResult.UNKNOWN


def _observation_status(
    metric_results: tuple[EvaluationMetricResultRecord, ...],
) -> AiObservationStatus:
    statuses = tuple(metric_result.status for metric_result in metric_results)
    if any(status is EvaluationStatus.ERRORED for status in statuses):
        return AiObservationStatus.FAILED
    if any(status is EvaluationStatus.FAILED for status in statuses):
        return AiObservationStatus.DEGRADED
    if all(status is EvaluationStatus.PASSED for status in statuses):
        return AiObservationStatus.SUCCESS
    return AiObservationStatus.DEGRADED


def _observation_type_for(target_type: EvaluationTargetType) -> AiObservationType:
    if target_type in {
        EvaluationTargetType.RAG_ANSWER,
        EvaluationTargetType.RAG_RETRIEVAL,
        EvaluationTargetType.RAG_GENERATION,
    }:
        return AiObservationType.RAG_ANSWER_QUALITY
    if target_type is EvaluationTargetType.MORNING_REPORT:
        return AiObservationType.INTELLIGENCE_REPORT_GENERATION
    if target_type is EvaluationTargetType.STRATEGY_SYNTHESIS:
        return AiObservationType.INTELLIGENCE_STRATEGY_SYNTHESIS
    if target_type is EvaluationTargetType.RECOMMENDATION_EXPLANATION:
        return AiObservationType.INTELLIGENCE_RECOMMENDATION_EXPLANATION
    return AiObservationType.INTELLIGENCE_AGENT_REASONING


def _total_duration_ms(
    metric_results: tuple[EvaluationMetricResultRecord, ...],
) -> float | None:
    durations = tuple(
        metric_result.duration_ms
        for metric_result in metric_results
        if metric_result.duration_ms is not None
    )
    if not durations:
        return None
    return sum(durations)
