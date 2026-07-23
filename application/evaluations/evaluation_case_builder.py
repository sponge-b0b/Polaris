from __future__ import annotations

from dataclasses import dataclass

from application.evaluations.contracts import EvaluationCaseBuildRequest, utc_now
from domain.evaluation import EvaluationCase


@dataclass(frozen=True, slots=True)
class EvaluationCaseBuilder:
    """Build canonical evaluation cases from typed Polaris source data."""

    def build(self, request: EvaluationCaseBuildRequest) -> EvaluationCase:
        return EvaluationCase(
            case_id=request.case_id,
            target_type=request.target_type,
            input_text=request.input_text,
            actual_output=request.actual_output,
            dataset=request.dataset,
            expected_output=request.expected_output,
            rubric=request.rubric,
            source_record_ids=request.source_record_ids,
            workflow_execution_id=request.workflow_execution_id,
            langfuse_trace_id=request.langfuse_trace_id,
            langfuse_observation_id=request.langfuse_observation_id,
            retrieval_context=request.retrieval_context,
            citation_context_ids=request.citation_context_ids,
            tags=request.tags,
            created_at=request.created_at or utc_now(),
        )

    def build_many(
        self,
        requests: tuple[EvaluationCaseBuildRequest, ...],
    ) -> tuple[EvaluationCase, ...]:
        return tuple(self.build(request) for request in requests)
