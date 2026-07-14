from __future__ import annotations

import asyncio

import pytest

from domain.evaluation import EvaluationCase
from domain.evaluation import EvaluationStatus
from domain.evaluation import EvaluationTargetType
from domain.evaluation import EvaluationThreshold
from integration.providers.llm_evaluation import DeepEvalEvaluationProvider
from integration.providers.llm_evaluation import DeepEvalMetricName
from integration.providers.llm_evaluation import DeepEvalMetricOutcome
from integration.providers.llm_evaluation import EvaluationMetricSpec
from integration.providers.llm_evaluation import EvaluationProviderRequest
from integration.providers.llm_evaluation.deepeval_evaluation_provider import (
    _deepeval_threshold_for,
)
from integration.providers.llm_evaluation.deepeval_evaluation_provider import (
    _normalize_metric_score,
)


@pytest.mark.asyncio
async def test_deepeval_provider_returns_typed_metric_results() -> None:
    adapter = FakeMetricAdapter(scores={"faithfulness": 0.91, "answer_relevancy": 0.61})
    provider = _provider(adapter)

    result = await provider.evaluate(
        EvaluationProviderRequest(
            run_id="run-1",
            cases=(_case("case-1"),),
            metrics=(
                EvaluationMetricSpec(
                    metric_name=DeepEvalMetricName.FAITHFULNESS.value,
                    threshold=EvaluationThreshold(
                        metric_name="faithfulness",
                        minimum_score=0.8,
                    ),
                ),
                EvaluationMetricSpec(
                    metric_name=DeepEvalMetricName.ANSWER_RELEVANCY.value,
                    threshold=EvaluationThreshold(
                        metric_name="answer_relevancy",
                        minimum_score=0.75,
                    ),
                ),
            ),
        )
    )

    assert result.run_id == "run-1"
    assert result.evaluator_provider == "deepeval"
    assert result.evaluator_model == "qwen3.5:4b"
    assert result.status is EvaluationStatus.FAILED
    assert [metric.status for metric in result.metric_results] == [
        EvaluationStatus.PASSED,
        EvaluationStatus.FAILED,
    ]
    assert [metric.score.score for metric in result.metric_results] == [0.91, 0.61]
    assert adapter.calls == [
        ("case-1", "faithfulness", 0.8, "qwen3.5:4b"),
        ("case-1", "answer_relevancy", 0.75, "qwen3.5:4b"),
    ]


@pytest.mark.asyncio
async def test_deepeval_provider_uses_default_threshold() -> None:
    adapter = FakeMetricAdapter(scores={"contextual_relevancy": 0.72})
    provider = _provider(adapter, default_threshold=0.7)

    result = await provider.evaluate(
        EvaluationProviderRequest(
            run_id="run-1",
            cases=(_case("case-1"),),
            metrics=(
                EvaluationMetricSpec(
                    metric_name=DeepEvalMetricName.CONTEXTUAL_RELEVANCY.value,
                ),
            ),
        )
    )

    score = result.metric_results[0].score
    assert score.threshold is not None
    assert score.threshold.minimum_score == 0.7
    assert result.status is EvaluationStatus.PASSED


@pytest.mark.asyncio
async def test_deepeval_provider_normalizes_metric_errors() -> None:
    adapter = FakeMetricAdapter(error=RuntimeError("judge unavailable"))
    provider = _provider(adapter)

    result = await provider.evaluate(
        EvaluationProviderRequest(
            run_id="run-1",
            cases=(_case("case-1"),),
            metrics=(EvaluationMetricSpec(metric_name="faithfulness"),),
        )
    )

    metric = result.metric_results[0]
    assert result.status is EvaluationStatus.ERRORED
    assert metric.status is EvaluationStatus.ERRORED
    assert metric.score.score == 0.0
    assert metric.error_message == "judge unavailable"
    assert metric.score.reason == "judge unavailable"


@pytest.mark.asyncio
async def test_deepeval_provider_enforces_timeout() -> None:
    adapter = FakeMetricAdapter(delay_seconds=0.05)
    provider = _provider(adapter, timeout_seconds=0.01)

    result = await provider.evaluate(
        EvaluationProviderRequest(
            run_id="run-1",
            cases=(_case("case-1"),),
            metrics=(EvaluationMetricSpec(metric_name="faithfulness"),),
        )
    )

    metric = result.metric_results[0]
    assert result.status is EvaluationStatus.ERRORED
    assert metric.status is EvaluationStatus.ERRORED
    assert "timed out" in str(metric.error_message)


@pytest.mark.asyncio
async def test_deepeval_provider_limits_metric_concurrency() -> None:
    adapter = FakeMetricAdapter(delay_seconds=0.01)
    provider = _provider(adapter, max_concurrency=1)

    await provider.evaluate(
        EvaluationProviderRequest(
            run_id="run-1",
            cases=(_case("case-1"), _case("case-2")),
            metrics=(
                EvaluationMetricSpec(metric_name="faithfulness"),
                EvaluationMetricSpec(metric_name="answer_relevancy"),
            ),
        )
    )

    assert adapter.max_active_calls == 1
    assert len(adapter.calls) == 4


def test_deepeval_provider_requires_explicit_judge_configuration() -> None:
    with pytest.raises(ValueError, match="judge_provider"):
        DeepEvalEvaluationProvider(
            judge_provider=" ",
            judge_model="qwen3.5:4b",
            default_threshold=0.7,
            max_concurrency=1,
            timeout_seconds=10.0,
        )
    with pytest.raises(ValueError, match="judge_model"):
        DeepEvalEvaluationProvider(
            judge_provider="ollama",
            judge_model=" ",
            default_threshold=0.7,
            max_concurrency=1,
            timeout_seconds=10.0,
        )


def test_metric_spec_rejects_blank_custom_rubric_values() -> None:
    with pytest.raises(ValueError, match="criteria"):
        EvaluationMetricSpec(metric_name="custom_metric", criteria=" ")

    with pytest.raises(ValueError, match="evaluation_steps"):
        EvaluationMetricSpec(
            metric_name="custom_metric",
            evaluation_steps=("Check the answer.", " "),
        )


def test_deepeval_provider_normalizes_hallucination_to_polaris_score_semantics() -> (
    None
):
    assert _deepeval_threshold_for("hallucination", 0.85) == pytest.approx(0.15)
    assert _deepeval_threshold_for("faithfulness", 0.80) == pytest.approx(0.80)
    assert _normalize_metric_score("hallucination", 0.10) == pytest.approx(0.90)
    assert _normalize_metric_score("faithfulness", 0.91) == pytest.approx(0.91)


class FakeMetricAdapter:
    def __init__(
        self,
        *,
        scores: dict[str, float] | None = None,
        error: Exception | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        self.calls: list[tuple[str, str, float, str]] = []
        self.max_active_calls = 0
        self._active_calls = 0
        self._scores = scores or {}
        self._error = error
        self._delay_seconds = delay_seconds

    async def evaluate_metric(
        self,
        case: EvaluationCase,
        metric: EvaluationMetricSpec,
        threshold: EvaluationThreshold,
        evaluator_model: str,
    ) -> DeepEvalMetricOutcome:
        self._active_calls += 1
        self.max_active_calls = max(self.max_active_calls, self._active_calls)
        try:
            if self._delay_seconds:
                await asyncio.sleep(self._delay_seconds)
            self.calls.append(
                (
                    case.case_id,
                    metric.metric_name,
                    threshold.minimum_score,
                    evaluator_model,
                )
            )
            if self._error is not None:
                raise self._error
            return DeepEvalMetricOutcome(
                score=self._scores.get(metric.metric_name, 0.88),
                reason=f"{metric.metric_name} reason",
            )
        finally:
            self._active_calls -= 1


def _provider(
    adapter: FakeMetricAdapter,
    *,
    default_threshold: float = 0.7,
    max_concurrency: int = 2,
    timeout_seconds: float = 10.0,
) -> DeepEvalEvaluationProvider:
    return DeepEvalEvaluationProvider(
        judge_provider="ollama",
        judge_model="qwen3.5:4b",
        default_threshold=default_threshold,
        max_concurrency=max_concurrency,
        timeout_seconds=timeout_seconds,
        adapter=adapter,
    )


def _case(case_id: str) -> EvaluationCase:
    return EvaluationCase(
        case_id=case_id,
        target_type=EvaluationTargetType.RAG_ANSWER,
        input_text="What changed?",
        actual_output="Risk was reduced because volatility rose.",
        expected_output="Risk was reduced.",
        retrieval_context=("Risk exposure was reduced.",),
        citation_context_ids=("chunk-1",),
        tags=("rag",),
    )
