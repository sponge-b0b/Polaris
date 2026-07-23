from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from application.evaluations import (
    EvaluationRunService,
    EvaluationRunServiceRequest,
    canonical_evaluation_dataset_definition_by_name,
    rag_evaluation_metric_specs,
)
from application.rag.contracts.rag_structured_answer import (
    RagStructuredAnswer,
    RagStructuredAnswerQuality,
    RagStructuredCitation,
)
from domain.evaluation import EvaluationStatus, EvaluationTargetType
from integration.providers.llm_evaluation import (
    EvaluationProviderRequest,
    EvaluationProviderResult,
)
from tests.evaluation._helpers import (
    InMemoryEvaluationRepository,
    PassingEvaluationProvider,
    RecordingProjectionService,
    evaluation_case_from_row,
)

LoadJsonlFixture = Callable[[Path], tuple[dict[str, Any], ...]]

pytestmark = pytest.mark.eval_rag_regression

_RAG_FIXTURE_FILES = (
    "golden_rag_questions.jsonl",
    "rag_citation_support.jsonl",
    "rag_security_prompt_injection.jsonl",
)

_REQUIRED_RAG_METRICS = {
    "faithfulness",
    "answer_relevancy",
    "contextual_relevancy",
    "contextual_precision",
    "contextual_recall",
    "hallucination",
    "citation_support",
    "financial_answer_quality",
    "risk_explanation_quality",
    "unsupported_claim_penalty",
    "refusal_correctness",
    "prompt_injection_resistance",
}


@dataclass(slots=True)
class RecordingPassingEvaluationProvider:
    """Deterministic provider that records the exact evaluated case set."""

    score: float = 0.95
    requests: list[EvaluationProviderRequest] = field(default_factory=list)

    async def evaluate(
        self,
        request: EvaluationProviderRequest,
    ) -> EvaluationProviderResult:
        self.requests.append(request)
        return await PassingEvaluationProvider(score=self.score).evaluate(request)


def test_active_rag_fixtures_are_structured_answer_schema_compatible(
    evaluation_fixture_dir: Path,
    load_jsonl_fixture: LoadJsonlFixture,
) -> None:
    for fixture_name in _RAG_FIXTURE_FILES:
        rows = load_jsonl_fixture(evaluation_fixture_dir / fixture_name)
        assert rows
        for row in rows:
            case = evaluation_case_from_row(row)
            assert case.citation_context_ids

            answer = RagStructuredAnswer(
                answer_text=case.actual_output,
                citations=tuple(
                    RagStructuredCitation(
                        citation_id=citation_id,
                        claim_summary=f"Fixture claim supported by {citation_id}.",
                    )
                    for citation_id in case.citation_context_ids
                ),
                quality=RagStructuredAnswerQuality(
                    confidence_score=0.95,
                    grounding_summary="Fixture answer is grounded in deterministic retrieval context.",  # noqa: E501
                ),
            )

            assert answer.answer_text == case.actual_output
            assert {citation.citation_id for citation in answer.citations} == set(
                case.citation_context_ids
            )


def test_structured_rag_schema_failure_reports_missing_citation_summary() -> None:
    with pytest.raises(ValidationError, match="claim_summary"):
        RagStructuredAnswer.model_validate(
            {
                "answer_text": "The answer cites the retrieved portfolio record.",
                "citations": [
                    {
                        "citation_id": "portfolio-risk-context-1",
                    }
                ],
                "quality": {
                    "confidence_score": 0.9,
                    "grounding_summary": "The answer is grounded in retrieved context.",
                },
            }
        )


def test_rag_metric_policy_covers_structured_output_regression_concerns() -> None:
    metric_names = {metric.metric_name for metric in rag_evaluation_metric_specs()}

    assert _REQUIRED_RAG_METRICS <= metric_names


@pytest.mark.asyncio
async def test_selected_golden_rag_dataset_runs_full_metric_set_through_persistence_and_projection(  # noqa: E501
    evaluation_fixture_dir: Path,
    load_jsonl_fixture: LoadJsonlFixture,
) -> None:
    dataset_definition = canonical_evaluation_dataset_definition_by_name(
        "golden_rag_questions"
    )
    rows = load_jsonl_fixture(evaluation_fixture_dir / "golden_rag_questions.jsonl")[:3]
    cases = tuple(
        evaluation_case_from_row(row, dataset=dataset_definition.reference)
        for row in rows
    )
    metrics = rag_evaluation_metric_specs()
    repository = InMemoryEvaluationRepository()
    projection_service = RecordingProjectionService()
    service = EvaluationRunService(
        provider=PassingEvaluationProvider(score=0.95),
        repository=repository,
        projection_service=projection_service,
    )

    result = await service.run_evaluation(
        EvaluationRunServiceRequest(
            run_id="structured-rag-regression-golden-001",
            target_type=EvaluationTargetType.RAG_ANSWER,
            cases=cases,
            metrics=metrics,
            evaluator_provider="deterministic_ci",
            evaluator_model="structured_fixture_judge",
            dataset=dataset_definition.reference,
            timeout_seconds=5.0,
        )
    )

    expected_metric_count = len(cases) * len(metrics)
    assert result.run.status is EvaluationStatus.PASSED
    assert result.metric_result_count == expected_metric_count
    assert result.persistence_result.datasets_written == 1
    assert result.persistence_result.cases_written == len(cases)
    assert result.persistence_result.runs_written == 2
    assert result.persistence_result.metric_results_written == expected_metric_count
    assert all(
        metric_result.score.reason == "deterministic CI evaluation passed"
        for metric_result in result.metric_results
    )
    assert result.langfuse_projection_attempted is True
    assert projection_service.requests
    projection_request = projection_service.requests[0]
    assert len(projection_request.cases) == len(cases)
    assert len(projection_request.metric_results) == expected_metric_count


@pytest.mark.asyncio
async def test_structured_rag_regression_run_excludes_detached_cases_by_default(
    evaluation_fixture_dir: Path,
    load_jsonl_fixture: LoadJsonlFixture,
) -> None:
    dataset_definition = canonical_evaluation_dataset_definition_by_name(
        "rag_citation_support"
    )
    rows = load_jsonl_fixture(evaluation_fixture_dir / "rag_citation_support.jsonl")
    active_cases = tuple(
        evaluation_case_from_row(row, dataset=dataset_definition.reference)
        for row in rows[:2]
    )
    detached_case = evaluation_case_from_row(
        rows[2],
        dataset=dataset_definition.reference,
    )
    provider = RecordingPassingEvaluationProvider(score=0.95)
    service = EvaluationRunService(
        provider=provider,
        repository=InMemoryEvaluationRepository(),
        projection_service=RecordingProjectionService(),
    )

    await service.run_evaluation(
        EvaluationRunServiceRequest(
            run_id="structured-rag-regression-active-only-001",
            target_type=EvaluationTargetType.RAG_ANSWER,
            cases=active_cases,
            metrics=rag_evaluation_metric_specs(),
            evaluator_provider="deterministic_ci",
            evaluator_model="structured_fixture_judge",
            dataset=dataset_definition.reference,
            timeout_seconds=5.0,
        )
    )

    assert len(provider.requests) == 1
    evaluated_case_ids = tuple(case.case_id for case in provider.requests[0].cases)
    assert evaluated_case_ids == tuple(case.case_id for case in active_cases)
    assert detached_case.case_id not in evaluated_case_ids
