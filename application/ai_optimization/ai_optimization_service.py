from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import Protocol

from application.ai_optimization.contracts import AiOptimizationRequest
from application.ai_optimization.contracts import AiOptimizationResult
from application.ai_optimization.contracts import AiOptimizationStatus
from application.ai_optimization.contracts import coerce_ai_optimization_target
from application.ai_optimization.contracts import (
    evaluation_target_type_for_optimization,
)
from application.evaluations import EvaluationRunServiceRequest
from application.evaluations import EvaluationRunServiceResult
from core.storage.persistence.ai_artifacts import AiArtifactApprovalStatus
from core.storage.persistence.ai_artifacts import AiArtifactPersistenceRepository
from core.storage.persistence.ai_artifacts import AiArtifactType
from core.storage.persistence.ai_artifacts import AiPromptProgramArtifactRecord
from core.storage.persistence.ai_artifacts import JsonObject
from core.storage.persistence.ai_artifacts import new_ai_prompt_program_artifact_id
from core.storage.persistence.evaluation import EvaluationCaseRecord
from core.storage.persistence.evaluation import EvaluationDatasetRecord
from core.storage.persistence.evaluation import EvaluationPersistenceRepository
from domain.evaluation import EvaluationCase
from domain.evaluation import EvaluationDatasetReference
from domain.evaluation import EvaluationStatus
from domain.evaluation import EvaluationTargetType
from integration.providers.ai_optimization import DspyOptimizationProviderProtocol
from integration.providers.ai_optimization import DspyOptimizationProviderRequest
from integration.providers.ai_optimization import DspyOptimizationProviderResult


class AiOptimizationEvaluationRunner(Protocol):
    """Evaluation boundary used by the optimization workbench."""

    async def run_evaluation(
        self,
        request: EvaluationRunServiceRequest,
    ) -> EvaluationRunServiceResult: ...


@dataclass(frozen=True, slots=True)
class AiOptimizationService:
    """Controlled workbench for offline AI prompt/program optimization.

    This service loads persisted golden evaluation cases, asks the DSPy provider to
    build a candidate artifact, scores candidate outputs through the canonical
    evaluation service, and persists the selected artifact as a non-active draft.
    """

    evaluation_repository: EvaluationPersistenceRepository
    artifact_repository: AiArtifactPersistenceRepository
    optimization_provider: DspyOptimizationProviderProtocol
    evaluation_runner: AiOptimizationEvaluationRunner

    async def optimize(self, request: AiOptimizationRequest) -> AiOptimizationResult:
        target = coerce_ai_optimization_target(request.target)
        dataset = await self.evaluation_repository.get_dataset(request.dataset_id)
        if dataset is None:
            raise ValueError(f"evaluation dataset not found: {request.dataset_id}")
        case_records = tuple(
            await self.evaluation_repository.list_cases_by_dataset(
                request.dataset_id,
                limit=request.max_trainset_cases,
            )
        )
        if not case_records:
            raise ValueError(f"evaluation dataset has no cases: {request.dataset_id}")
        dataset_reference = _dataset_reference(dataset)
        cases = tuple(
            _case_from_record(case, dataset_reference) for case in case_records
        )
        provider_result = await self.optimization_provider.optimize(
            DspyOptimizationProviderRequest(
                optimization_id=request.optimization_id,
                target_component=target.value,
                cases=cases,
                prompt_name=request.prompt_name,
                prompt_version=request.prompt_version,
                artifact_name=request.artifact_name,
                artifact_version=request.artifact_version,
                model_name=request.model_name,
            )
        )
        evaluation_cases = _candidate_evaluation_cases(cases, provider_result)
        evaluation_result = await self.evaluation_runner.run_evaluation(
            EvaluationRunServiceRequest(
                run_id=f"{request.optimization_id}-evaluation",
                target_type=evaluation_target_type_for_optimization(target),
                cases=evaluation_cases,
                metrics=request.metrics,
                evaluator_provider=request.evaluator_provider,
                evaluator_model=request.evaluator_model,
                dataset=dataset_reference,
                timeout_seconds=request.timeout_seconds,
            )
        )
        if evaluation_result.run.status is EvaluationStatus.ERRORED:
            return AiOptimizationResult(
                optimization_id=request.optimization_id,
                target=target,
                status=AiOptimizationStatus.FAILED,
                evaluation_result=evaluation_result,
                provider_result=provider_result,
                artifact=None,
            )
        artifact = await self.artifact_repository.upsert_artifact(
            AiPromptProgramArtifactRecord(
                artifact_id=new_ai_prompt_program_artifact_id(),
                artifact_type=AiArtifactType.DSPY_COMPILED_PROMPT,
                artifact_name=provider_result.artifact.artifact_name,
                artifact_version=provider_result.artifact.artifact_version,
                target_component=target.value,
                model_name=provider_result.model_name,
                provider_name=provider_result.provider_name,
                prompt_reference=provider_result.artifact.prompt_reference,
                prompt_hash=provider_result.artifact.prompt_hash,
                source="application.ai_optimization",
                approval_status=AiArtifactApprovalStatus.DRAFT,
                evaluation_dataset_id=request.dataset_id,
                evaluation_run_id=evaluation_result.run.run_id,
                deepeval_score_summary=_score_summary(evaluation_result),
                langfuse_trace_id=_langfuse_trace_id(evaluation_result),
                active=False,
                created_at=datetime.now(UTC),
            )
        )
        return AiOptimizationResult(
            optimization_id=request.optimization_id,
            target=target,
            status=AiOptimizationStatus.SUCCEEDED,
            evaluation_result=evaluation_result,
            provider_result=provider_result,
            artifact=artifact,
        )


def _dataset_reference(record: EvaluationDatasetRecord) -> EvaluationDatasetReference:
    return EvaluationDatasetReference(
        dataset_id=record.dataset_id,
        name=record.name,
        version=record.version,
        tags=record.tags,
    )


def _case_from_record(
    record: EvaluationCaseRecord,
    dataset: EvaluationDatasetReference,
) -> EvaluationCase:
    return EvaluationCase(
        case_id=record.case_id,
        target_type=EvaluationTargetType(record.target_type),
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


def _candidate_evaluation_cases(
    cases: Sequence[EvaluationCase],
    provider_result: DspyOptimizationProviderResult,
) -> tuple[EvaluationCase, ...]:
    case_outputs = {
        output.case_id: output.actual_output for output in provider_result.case_outputs
    }
    return tuple(
        EvaluationCase(
            case_id=case.case_id,
            target_type=case.target_type,
            input_text=case.input_text,
            actual_output=case_outputs.get(case.case_id, case.actual_output),
            dataset=case.dataset,
            expected_output=case.expected_output,
            rubric=case.rubric,
            source_record_ids=case.source_record_ids,
            workflow_execution_id=case.workflow_execution_id,
            langfuse_trace_id=case.langfuse_trace_id,
            langfuse_observation_id=case.langfuse_observation_id,
            retrieval_context=case.retrieval_context,
            citation_context_ids=case.citation_context_ids,
            tags=case.tags,
            created_at=case.created_at,
        )
        for case in cases
    )


def _score_summary(result: EvaluationRunServiceResult) -> JsonObject:
    by_metric: dict[str, list[float]] = {}
    passed_count = 0
    failed_count = 0
    for metric_result in result.metric_results:
        by_metric.setdefault(metric_result.score.metric_name, []).append(
            metric_result.score.score
        )
        if metric_result.status is EvaluationStatus.PASSED:
            passed_count += 1
        elif metric_result.status in (
            EvaluationStatus.FAILED,
            EvaluationStatus.ERRORED,
        ):
            failed_count += 1
    metric_summary: dict[str, Mapping[str, float | int]] = {
        metric_name: {
            "average_score": sum(scores) / len(scores),
            "max_score": max(scores),
            "min_score": min(scores),
            "result_count": len(scores),
        }
        for metric_name, scores in by_metric.items()
    }
    all_scores = [score for scores in by_metric.values() for score in scores]
    return {
        "average_score": sum(all_scores) / len(all_scores) if all_scores else None,
        "case_count": len(result.run.case_ids),
        "failed_metric_count": failed_count,
        "metric_count": len(result.metric_results),
        "metrics": metric_summary,
        "passed_metric_count": passed_count,
        "run_status": result.run.status.value,
    }


def _langfuse_trace_id(result: EvaluationRunServiceResult) -> str | None:
    projection = result.langfuse_projection_result
    if projection is None:
        return None
    for export_result in projection.export_results:
        if export_result.external_trace_id is not None:
            return export_result.external_trace_id
    return None
