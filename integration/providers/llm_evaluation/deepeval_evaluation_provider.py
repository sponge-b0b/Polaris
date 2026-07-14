from __future__ import annotations

import asyncio
import os

from dataclasses import dataclass
from enum import StrEnum
from time import perf_counter
from typing import Any
from typing import Protocol
from typing import cast

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from domain.evaluation import EvaluationCase
from domain.evaluation import EvaluationMetricResult
from domain.evaluation import EvaluationScore
from domain.evaluation import EvaluationStatus
from domain.evaluation import EvaluationThreshold
from integration.providers.llm_evaluation.evaluation_provider import (
    EvaluationMetricSpec,
)
from integration.providers.llm_evaluation.evaluation_provider import EvaluationProvider
from integration.providers.llm_evaluation.evaluation_provider import (
    EvaluationProviderRequest,
)
from integration.providers.llm_evaluation.evaluation_provider import (
    EvaluationProviderResult,
)
from integration.providers.provider_telemetry import record_provider_call


class DeepEvalMetricName(StrEnum):
    """DeepEval-backed metric names supported by the provider boundary.

    Polaris score semantics are always higher-is-better. The native DeepEval
    hallucination metric is lower-is-better, so the native adapter normalizes
    it to an absence score before returning it to application code.
    """

    FAITHFULNESS = "faithfulness"
    ANSWER_RELEVANCY = "answer_relevancy"
    CONTEXTUAL_RELEVANCY = "contextual_relevancy"
    CONTEXTUAL_PRECISION = "contextual_precision"
    CONTEXTUAL_RECALL = "contextual_recall"
    HALLUCINATION = "hallucination"


@dataclass(frozen=True, slots=True)
class DeepEvalMetricOutcome:
    """Vendor-neutral outcome from executing one DeepEval metric."""

    score: float
    reason: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0.")
        if self.reason is not None and not self.reason.strip():
            raise ValueError("reason cannot be empty.")


class DeepEvalMetricAdapter(Protocol):
    """Adapter seam that isolates DeepEval's vendor API from Polaris contracts."""

    async def evaluate_metric(
        self,
        case: EvaluationCase,
        metric: EvaluationMetricSpec,
        threshold: EvaluationThreshold,
        evaluator_model: str,
    ) -> DeepEvalMetricOutcome: ...


class DeepEvalEvaluationProvider(EvaluationProvider):
    """LLM evaluation provider backed by DeepEval."""

    provider_name = "deepeval"

    def __init__(
        self,
        *,
        judge_provider: str,
        judge_model: str,
        default_threshold: float,
        max_concurrency: int,
        timeout_seconds: float,
        telemetry_opt_out: bool = True,
        telemetry: IntegrationTelemetry | None = None,
        adapter: DeepEvalMetricAdapter | None = None,
    ) -> None:
        if not judge_provider.strip():
            raise ValueError("judge_provider cannot be empty.")
        if not judge_model.strip():
            raise ValueError("judge_model cannot be empty.")
        if not 0.0 <= default_threshold <= 1.0:
            raise ValueError("default_threshold must be between 0.0 and 1.0.")
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0.")
        if timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be greater than 0.0.")

        self._judge_provider = judge_provider
        self._judge_model = judge_model
        self._default_threshold = default_threshold
        self._max_concurrency = max_concurrency
        self._timeout_seconds = timeout_seconds
        self._telemetry = telemetry
        self._adapter = adapter or _NativeDeepEvalMetricAdapter()
        if telemetry_opt_out:
            os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "true")

    async def evaluate(
        self,
        request: EvaluationProviderRequest,
    ) -> EvaluationProviderResult:
        return await record_provider_call(
            self._telemetry,
            self.provider_name,
            "evaluate",
            lambda: self._evaluate(request),
            attributes={
                "semantic_operation": "llm_evaluation",
                "evaluator_provider": self.provider_name,
                "judge_provider": self._judge_provider,
                "model": self._judge_model,
                "run_id": request.run_id,
                "case_count": len(request.cases),
                "metric_count": len(request.metrics),
            },
        )

    async def _evaluate(
        self,
        request: EvaluationProviderRequest,
    ) -> EvaluationProviderResult:
        started_at = perf_counter()
        semaphore = asyncio.Semaphore(self._max_concurrency)
        timeout_seconds = request.timeout_seconds or self._timeout_seconds
        tasks = [
            self._evaluate_case_metric(
                request.run_id,
                case,
                metric,
                semaphore,
                timeout_seconds,
            )
            for case in request.cases
            for metric in request.metrics
        ]
        metric_results = tuple(await asyncio.gather(*tasks))
        status = _result_status(metric_results)
        return EvaluationProviderResult(
            run_id=request.run_id,
            status=status,
            metric_results=metric_results,
            evaluator_provider=self.provider_name,
            evaluator_model=self._judge_model,
            duration_ms=(perf_counter() - started_at) * 1000.0,
        )

    async def _evaluate_case_metric(
        self,
        run_id: str,
        case: EvaluationCase,
        metric: EvaluationMetricSpec,
        semaphore: asyncio.Semaphore,
        timeout_seconds: float,
    ) -> EvaluationMetricResult:
        started_at = perf_counter()
        threshold = self._threshold_for(metric)
        async with semaphore:
            try:
                async with asyncio.timeout(timeout_seconds):
                    outcome = await self._adapter.evaluate_metric(
                        case,
                        metric,
                        threshold,
                        self._judge_model,
                    )
            except TimeoutError:
                message = (
                    f"DeepEval metric '{metric.metric_name}' timed out after "
                    f"{timeout_seconds:.2f} seconds."
                )
                return self._error_result(run_id, case, threshold, started_at, message)
            except Exception as exc:
                return self._error_result(
                    run_id,
                    case,
                    threshold,
                    started_at,
                    str(exc) or type(exc).__name__,
                )

        score = EvaluationScore(
            metric_name=threshold.metric_name,
            score=outcome.score,
            threshold=threshold,
            reason=outcome.reason if metric.include_reason else None,
        )
        return EvaluationMetricResult(
            run_id=run_id,
            case_id=case.case_id,
            score=score,
            status=EvaluationStatus.PASSED
            if score.passed is True
            else EvaluationStatus.FAILED,
            evaluator_provider=self.provider_name,
            evaluator_model=self._judge_model,
            duration_ms=(perf_counter() - started_at) * 1000.0,
        )

    def _threshold_for(self, metric: EvaluationMetricSpec) -> EvaluationThreshold:
        if metric.threshold is not None:
            return metric.threshold
        return EvaluationThreshold(
            metric_name=metric.metric_name,
            minimum_score=self._default_threshold,
        )

    def _error_result(
        self,
        run_id: str,
        case: EvaluationCase,
        threshold: EvaluationThreshold,
        started_at: float,
        message: str,
    ) -> EvaluationMetricResult:
        return EvaluationMetricResult(
            run_id=run_id,
            case_id=case.case_id,
            score=EvaluationScore(
                metric_name=threshold.metric_name,
                score=0.0,
                threshold=threshold,
                reason=message,
            ),
            status=EvaluationStatus.ERRORED,
            evaluator_provider=self.provider_name,
            evaluator_model=self._judge_model,
            duration_ms=(perf_counter() - started_at) * 1000.0,
            error_message=message,
        )


class _NativeDeepEvalMetricAdapter:
    async def evaluate_metric(
        self,
        case: EvaluationCase,
        metric: EvaluationMetricSpec,
        threshold: EvaluationThreshold,
        evaluator_model: str,
    ) -> DeepEvalMetricOutcome:
        metric_instance = _build_metric(
            metric.metric_name,
            threshold.minimum_score,
            evaluator_model,
            metric.include_reason,
            metric.criteria,
            metric.evaluation_steps,
        )
        test_case = _build_test_case(case)
        score = await metric_instance.a_measure(
            test_case,
            _show_indicator=False,
            _in_component=True,
            _log_metric_to_confident=False,
        )
        normalized_score = _normalize_metric_score(metric.metric_name, float(score))
        return DeepEvalMetricOutcome(
            score=normalized_score,
            reason=cast("str | None", getattr(metric_instance, "reason", None)),
        )


def _build_test_case(case: EvaluationCase) -> Any:
    from deepeval.test_case import LLMTestCase

    return LLMTestCase(
        input=case.input_text,
        actual_output=case.actual_output,
        expected_output=case.expected_output,
        context=list(case.retrieval_context),
        retrieval_context=list(case.retrieval_context),
        name=case.case_id,
        tags=list(case.tags),
        metadata={
            "case_id": case.case_id,
            "target_type": case.target_type.value,
            "source_record_ids": list(case.source_record_ids),
            "workflow_execution_id": case.workflow_execution_id,
            "langfuse_trace_id": case.langfuse_trace_id,
            "langfuse_observation_id": case.langfuse_observation_id,
            "citation_context_ids": list(case.citation_context_ids),
            "rubric": case.rubric,
        },
    )


def _build_metric(
    metric_name: str,
    threshold: float,
    evaluator_model: str,
    include_reason: bool,
    criteria: str | None = None,
    evaluation_steps: tuple[str, ...] = (),
) -> Any:
    from deepeval.metrics import AnswerRelevancyMetric
    from deepeval.metrics import ContextualPrecisionMetric
    from deepeval.metrics import ContextualRecallMetric
    from deepeval.metrics import ContextualRelevancyMetric
    from deepeval.metrics import FaithfulnessMetric
    from deepeval.metrics import HallucinationMetric

    metric_classes = {
        DeepEvalMetricName.FAITHFULNESS.value: FaithfulnessMetric,
        DeepEvalMetricName.ANSWER_RELEVANCY.value: AnswerRelevancyMetric,
        DeepEvalMetricName.CONTEXTUAL_RELEVANCY.value: ContextualRelevancyMetric,
        DeepEvalMetricName.CONTEXTUAL_PRECISION.value: ContextualPrecisionMetric,
        DeepEvalMetricName.CONTEXTUAL_RECALL.value: ContextualRecallMetric,
        DeepEvalMetricName.HALLUCINATION.value: HallucinationMetric,
    }
    metric_class = metric_classes.get(metric_name)
    if metric_class is None:
        if criteria is not None or evaluation_steps:
            return _build_geval_metric(
                metric_name,
                threshold,
                evaluator_model,
                criteria,
                evaluation_steps,
            )
        supported = ", ".join(sorted(metric_classes))
        raise ValueError(
            f"Unsupported DeepEval metric '{metric_name}'. Supported: {supported}; "
            "custom metrics must provide criteria or evaluation_steps."
        )
    metric_threshold = _deepeval_threshold_for(metric_name, threshold)
    return metric_class(
        threshold=metric_threshold,
        model=evaluator_model,
        include_reason=include_reason,
        async_mode=True,
        strict_mode=False,
        verbose_mode=False,
    )


def _build_geval_metric(
    metric_name: str,
    threshold: float,
    evaluator_model: str,
    criteria: str | None,
    evaluation_steps: tuple[str, ...],
) -> Any:
    from deepeval.metrics import GEval
    from deepeval.test_case.llm_test_case import SingleTurnParams

    return GEval(
        name=metric_name,
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
            SingleTurnParams.CONTEXT,
            SingleTurnParams.RETRIEVAL_CONTEXT,
        ],
        criteria=criteria,
        evaluation_steps=list(evaluation_steps) or None,
        model=evaluator_model,
        threshold=threshold,
        async_mode=True,
        strict_mode=False,
        verbose_mode=False,
    )


def _deepeval_threshold_for(metric_name: str, canonical_threshold: float) -> float:
    if metric_name == DeepEvalMetricName.HALLUCINATION.value:
        return 1.0 - canonical_threshold
    return canonical_threshold


def _normalize_metric_score(metric_name: str, raw_score: float) -> float:
    if metric_name == DeepEvalMetricName.HALLUCINATION.value:
        return 1.0 - raw_score
    return raw_score


def _result_status(
    metric_results: tuple[EvaluationMetricResult, ...],
) -> EvaluationStatus:
    if any(result.status is EvaluationStatus.ERRORED for result in metric_results):
        return EvaluationStatus.ERRORED
    if any(result.status is EvaluationStatus.FAILED for result in metric_results):
        return EvaluationStatus.FAILED
    return EvaluationStatus.PASSED
