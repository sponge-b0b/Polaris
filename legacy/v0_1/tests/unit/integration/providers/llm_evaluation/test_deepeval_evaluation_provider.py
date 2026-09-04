from __future__ import annotations

import asyncio
import sys
from types import ModuleType
from typing import Any, cast

import pytest

from domain.evaluation import (
    EvaluationCase,
    EvaluationStatus,
    EvaluationTargetType,
    EvaluationThreshold,
)
from integration.providers.llm_evaluation import (
    DeepEvalEvaluationProvider,
    DeepEvalJudgeModelConfig,
    DeepEvalMetricName,
    DeepEvalMetricOutcome,
    EvaluationMetricSpec,
    EvaluationProviderRequest,
    build_deepeval_judge_model,
)
from integration.providers.llm_evaluation.deepeval_evaluation_provider import (
    _build_metric,
    _build_test_case,
    _deepeval_threshold_for,
    _litellm_model_name,
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
            judge_provider="litellm",
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


def test_native_deepeval_test_case_maps_canonical_case_fields() -> None:
    case = EvaluationCase(
        case_id="case-1",
        target_type=EvaluationTargetType.RAG_ANSWER,
        input_text="What changed?",
        actual_output="Risk was reduced because volatility rose.",
        expected_output="Risk was reduced.",
        rubric="Verify the answer is grounded in retrieved evidence.",
        source_record_ids=("record-1",),
        workflow_execution_id="exec-1",
        langfuse_trace_id="trace-1",
        langfuse_observation_id="observation-1",
        retrieval_context=("Risk exposure was reduced.",),
        citation_context_ids=("chunk-1",),
        tags=("rag", "golden"),
    )

    test_case = _build_test_case(case)

    assert test_case.input == case.input_text
    assert test_case.actual_output == case.actual_output
    assert test_case.expected_output == case.expected_output
    assert test_case.context == ["Risk exposure was reduced."]
    assert test_case.retrieval_context == ["Risk exposure was reduced."]
    assert test_case.name == "case-1"
    assert test_case.tags == ["rag", "golden"]
    assert test_case.metadata == {
        "case_id": "case-1",
        "target_type": "rag_answer",
        "source_record_ids": ["record-1"],
        "workflow_execution_id": "exec-1",
        "langfuse_trace_id": "trace-1",
        "langfuse_observation_id": "observation-1",
        "citation_context_ids": ["chunk-1"],
        "rubric": "Verify the answer is grounded in retrieved evidence.",
    }


def test_native_metric_builder_maps_supported_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_metrics = _install_fake_deepeval_metric_module(monkeypatch)

    metric = _build_metric(
        DeepEvalMetricName.HALLUCINATION.value,
        0.85,
        "qwen3.5:4b",
        True,
    )

    assert isinstance(metric, fake_metrics.HallucinationMetric)
    assert metric.threshold == pytest.approx(0.15)
    assert metric.model == "qwen3.5:4b"
    assert metric.include_reason is True
    assert metric.async_mode is True
    assert metric.strict_mode is False
    assert metric.verbose_mode is False


def test_native_metric_builder_maps_custom_geval_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_metrics = _install_fake_deepeval_metric_module(monkeypatch)
    _install_fake_deepeval_test_case_params(monkeypatch)

    metric = _build_metric(
        "financial_answer_quality",
        0.75,
        "qwen3.5:4b",
        True,
        criteria="Assess whether the answer is financially grounded.",
        evaluation_steps=("Check cited evidence.",),
    )

    assert isinstance(metric, fake_metrics.GEval)
    assert metric.name == "financial_answer_quality"
    assert metric.threshold == pytest.approx(0.75)
    assert metric.model == "qwen3.5:4b"
    assert metric.criteria == "Assess whether the answer is financially grounded."
    assert metric.evaluation_steps == ["Check cited evidence."]
    assert metric.evaluation_params == [
        "input",
        "actual_output",
        "expected_output",
        "context",
        "retrieval_context",
    ]
    assert metric.async_mode is True
    assert metric.strict_mode is False
    assert metric.verbose_mode is False


def test_native_metric_builder_rejects_unknown_metrics_without_rubric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_deepeval_metric_module(monkeypatch)

    with pytest.raises(ValueError, match="Unsupported DeepEval metric"):
        _build_metric(
            "financial_answer_quality",
            0.75,
            "qwen3.5:4b",
            True,
        )


def test_deepeval_judge_model_factory_builds_openai_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_models = _install_fake_deepeval_model_module(monkeypatch)

    model = build_deepeval_judge_model(
        DeepEvalJudgeModelConfig(provider="openai", model="gpt-4.1-mini")
    )

    assert isinstance(model, fake_models.GPTModel)
    assert model.model == "gpt-4.1-mini"


def test_deepeval_judge_model_factory_builds_litellm_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_models = _install_fake_deepeval_model_module(monkeypatch)

    model = build_deepeval_judge_model(
        DeepEvalJudgeModelConfig(
            provider="litellm",
            model="qwen3.5:4b",
            litellm_base_url="http://localhost:4000/v1",
            litellm_api_key="unit-test-placeholder",
        )
    )

    assert isinstance(model, fake_models.LiteLLMModel)
    assert model.model == "openai/qwen3.5:4b"
    assert model.base_url == "http://localhost:4000/v1"
    assert model.api_key == "unit-test-placeholder"


def test_deepeval_litellm_model_name_preserves_prefixed_models() -> None:
    assert _litellm_model_name("openai/qwen3.5:4b", "openai") == "openai/qwen3.5:4b"
    assert _litellm_model_name("qwen3.5:4b", "openai") == "openai/qwen3.5:4b"


def test_deepeval_judge_model_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported DeepEval judge provider"):
        build_deepeval_judge_model(
            DeepEvalJudgeModelConfig(provider="unknown", model="qwen3.5:4b")
        )


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
        judge_provider="litellm",
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


class _FakeMetric:
    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)


class _FakeGEval(_FakeMetric):
    pass


def _install_fake_deepeval_metric_module(
    monkeypatch: pytest.MonkeyPatch,
) -> Any:
    fake_metrics = cast(Any, ModuleType("deepeval.metrics"))
    fake_metrics.AnswerRelevancyMetric = type(
        "AnswerRelevancyMetric", (_FakeMetric,), {}
    )
    fake_metrics.ContextualPrecisionMetric = type(
        "ContextualPrecisionMetric", (_FakeMetric,), {}
    )
    fake_metrics.ContextualRecallMetric = type(
        "ContextualRecallMetric", (_FakeMetric,), {}
    )
    fake_metrics.ContextualRelevancyMetric = type(
        "ContextualRelevancyMetric", (_FakeMetric,), {}
    )
    fake_metrics.FaithfulnessMetric = type("FaithfulnessMetric", (_FakeMetric,), {})
    fake_metrics.HallucinationMetric = type("HallucinationMetric", (_FakeMetric,), {})
    fake_metrics.GEval = _FakeGEval
    monkeypatch.setitem(sys.modules, "deepeval.metrics", fake_metrics)
    return fake_metrics


def _install_fake_deepeval_model_module(
    monkeypatch: pytest.MonkeyPatch,
) -> Any:
    fake_models = cast(Any, ModuleType("deepeval.models"))
    fake_models.GPTModel = type("GPTModel", (_FakeMetric,), {})
    fake_models.LiteLLMModel = type("LiteLLMModel", (_FakeMetric,), {})
    monkeypatch.setitem(sys.modules, "deepeval.models", fake_models)
    return fake_models


def _install_fake_deepeval_test_case_params(
    monkeypatch: pytest.MonkeyPatch,
) -> ModuleType:
    fake_llm_test_case = cast(Any, ModuleType("deepeval.test_case.llm_test_case"))

    class SingleTurnParams:
        INPUT = "input"
        ACTUAL_OUTPUT = "actual_output"
        EXPECTED_OUTPUT = "expected_output"
        CONTEXT = "context"
        RETRIEVAL_CONTEXT = "retrieval_context"

    fake_llm_test_case.SingleTurnParams = SingleTurnParams
    monkeypatch.setitem(
        sys.modules,
        "deepeval.test_case.llm_test_case",
        fake_llm_test_case,
    )
    return fake_llm_test_case
