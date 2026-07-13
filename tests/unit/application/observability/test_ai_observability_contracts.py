from __future__ import annotations

import pytest

from typing import Mapping
from typing import cast

from application.observability import AiEvaluationObservation
from application.observability import AiEvaluationScore
from application.observability import AiGenerationObservation
from application.observability import AiObservation
from application.observability import AiObservationFamily
from application.observability import AiObservationStatus
from application.observability import AiObservationType
from application.observability import AiObservabilityCapturePolicy
from application.observability import AiObservabilityCorrelationIds
from application.observability import AiObservabilityExportResult
from application.observability import AiObservabilityExportStatus
from application.observability import AiPromptVersionReference
from application.observability import AiRedactionMode
from application.observability import AiRerankingObservation
from application.observability import AiRetrievalObservation
from application.observability import AiScoreResult


def test_ai_observation_types_map_to_canonical_families() -> None:
    assert AiObservationType.RAG_QUERY.family is AiObservationFamily.RAG
    assert AiObservationType.RAG_RETRIEVAL_VECTOR.family is AiObservationFamily.RAG
    assert AiObservationType.RAG_RERANKING.family is AiObservationFamily.RAG
    assert AiObservationType.RAG_ANSWER_QUALITY.family is AiObservationFamily.RAG
    assert (
        AiObservationType.INTELLIGENCE_STRATEGY_SYNTHESIS.family
        is AiObservationFamily.INTELLIGENCE
    )
    assert (
        AiObservationType.INTELLIGENCE_RECOMMENDATION_EXPLANATION.family
        is AiObservationFamily.INTELLIGENCE
    )


def test_capture_policy_defaults_to_redacted_metadata_safe_capture() -> None:
    policy = AiObservabilityCapturePolicy()

    assert policy.capture_prompts is False
    assert policy.capture_responses is False
    assert policy.capture_contexts is False
    assert policy.capture_user_input is False
    assert policy.redaction_mode is AiRedactionMode.STRICT
    assert policy.max_payload_characters == 8_000


def test_generation_observation_uses_stable_idempotency_key() -> None:
    correlation_ids = AiObservabilityCorrelationIds(
        trace_id="trace-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="rag_answer",
        observation_id="generation-1",
    )
    prompt_reference = AiPromptVersionReference(
        prompt_name="rag.answer",
        prompt_version="v1",
        prompt_hash="abc123",
    )

    first = AiGenerationObservation(
        observation_type=AiObservationType.RAG_GENERATION,
        name="answer_generation",
        correlation_ids=correlation_ids,
        model_name="qwen3.5:4b",
        provider_name="ollama",
        prompt_reference=prompt_reference,
        input_shape="question+contexts",
        output_shape="answer+citations",
        token_count_input=512,
        token_count_output=128,
        metadata={"context_count": 4, "web_used": False},
    )
    second = AiGenerationObservation(
        observation_type=AiObservationType.RAG_GENERATION,
        name="answer_generation",
        correlation_ids=correlation_ids,
        model_name="qwen3.5:4b",
        provider_name="ollama",
        prompt_reference=prompt_reference,
        input_shape="question+contexts",
        output_shape="answer+citations",
        token_count_input=512,
        token_count_output=128,
        metadata={"context_count": 4, "web_used": False},
    )

    assert first.family is AiObservationFamily.RAG
    assert first.idempotency_key() == second.idempotency_key()
    assert first.idempotency_key().startswith("aiobs:")


def test_retrieval_and_reranking_observations_capture_stage_shapes() -> None:
    retrieval = AiRetrievalObservation(
        observation_type=AiObservationType.RAG_RETRIEVAL_VECTOR,
        name="vector_retrieval",
        retrieved_count=3,
        selected_context_ids=("chunk-2", "chunk-1", ""),
        retrieval_scores=(0.72, 0.64),
    )
    reranking = AiRerankingObservation(
        observation_type=AiObservationType.RAG_RERANKING,
        name="cross_encoder_rerank",
        candidate_count=3,
        selected_count=2,
        reranking_scores=(0.95, 0.81),
    )

    assert retrieval.selected_context_ids == ("chunk-2", "chunk-1")
    assert retrieval.retrieval_scores == (0.72, 0.64)
    assert reranking.reranking_scores == (0.95, 0.81)


@pytest.mark.parametrize(
    ("score", "expected_result"),
    [
        (0.91, AiScoreResult.PASS),
        (0.55, AiScoreResult.WARN),
        (0.12, AiScoreResult.FAIL),
    ],
)
def test_evaluation_observation_is_deepeval_ready(
    score: float,
    expected_result: AiScoreResult,
) -> None:
    correlation_ids = AiObservabilityCorrelationIds(
        trace_id="trace-2",
        observation_id="eval-1",
        dataset_id="dataset-rag-smoke",
        case_id="case-42",
        run_id="run-20260712",
    )
    evaluation_score = AiEvaluationScore(
        metric_name="answer_relevancy",
        score=score,
        threshold=0.8,
        result=expected_result,
        reason="deterministic test reason",
        evaluator_model="qwen3.5:4b",
        evaluator_provider="deepeval",
    )
    observation = AiEvaluationObservation(
        observation_type=AiObservationType.RAG_ANSWER_QUALITY,
        name="answer_quality_eval",
        status=AiObservationStatus.SUCCESS,
        correlation_ids=correlation_ids,
        scores=(evaluation_score,),
        evaluated_observation_id="generation-1",
    )

    assert observation.scores == (evaluation_score,)
    assert observation.correlation_ids.dataset_id == "dataset-rag-smoke"
    assert observation.correlation_ids.case_id == "case-42"
    assert observation.correlation_ids.run_id == "run-20260712"
    assert observation.idempotency_key().startswith("aievaluation:")


def test_export_result_preserves_external_correlation_identifiers() -> None:
    result = AiObservabilityExportResult.exported(
        idempotency_key="aiobs:123",
        observation_id="generation-1",
        external_trace_id="langfuse-trace-1",
        external_observation_id="langfuse-generation-1",
        dataset_id="dataset-1",
        case_id="case-1",
        run_id="run-1",
    )

    assert result.status is AiObservabilityExportStatus.EXPORTED
    assert result.external_trace_id == "langfuse-trace-1"
    assert result.external_observation_id == "langfuse-generation-1"
    assert result.exported_at is not None


def test_contracts_reject_invalid_scores_and_counts() -> None:
    with pytest.raises(ValueError, match="score must be between"):
        AiEvaluationScore(metric_name="faithfulness", score=1.1)

    with pytest.raises(ValueError, match="selected_count cannot exceed"):
        AiRerankingObservation(
            observation_type=AiObservationType.RAG_RERANKING,
            name="bad_rerank",
            candidate_count=1,
            selected_count=2,
        )

    with pytest.raises(TypeError, match="metadata values"):
        AiObservation(
            observation_type=AiObservationType.INTELLIGENCE_AGENT_REASONING,
            name="agent_reasoning",
            metadata=cast(
                Mapping[str, str | int | float | bool | None], {"nested": object()}
            ),
        )
