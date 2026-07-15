from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from application.evaluations import EvaluationRunServiceResult
from core.storage.persistence.ai_artifacts import AiPromptProgramArtifactRecord
from domain.evaluation import EvaluationTargetType
from integration.providers.ai_optimization import DspyOptimizationProviderResult
from integration.providers.llm_evaluation import EvaluationMetricSpec


class AiOptimizationTarget(StrEnum):
    """Initial Polaris AI components eligible for offline DSPy optimization."""

    RAG_ANSWER_GENERATION = "rag_answer_generation"
    RAG_QUERY_REWRITE = "rag_query_rewrite"
    STRATEGY_SYNTHESIS = "strategy_synthesis"
    RECOMMENDATION_EXPLANATION = "recommendation_explanation"


class AiOptimizationStatus(StrEnum):
    """Application result status for a controlled optimization workbench run."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AiOptimizationRequest:
    """Request to run an explicit offline DSPy optimization workbench pass."""

    optimization_id: str
    target: AiOptimizationTarget | str
    dataset_id: str
    metrics: Sequence[EvaluationMetricSpec]
    evaluator_provider: str
    evaluator_model: str
    model_name: str
    prompt_name: str
    prompt_version: str
    artifact_name: str
    artifact_version: str
    max_trainset_cases: int | None = None
    timeout_seconds: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "target", coerce_ai_optimization_target(self.target))
        for field_name in (
            "optimization_id",
            "dataset_id",
            "evaluator_provider",
            "evaluator_model",
            "model_name",
            "prompt_name",
            "prompt_version",
            "artifact_name",
            "artifact_version",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if not self.metrics:
            raise ValueError("metrics cannot be empty.")
        if self.max_trainset_cases is not None and self.max_trainset_cases <= 0:
            raise ValueError("max_trainset_cases must be greater than zero.")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be greater than 0.0.")


@dataclass(frozen=True, slots=True)
class AiOptimizationResult:
    """Result of one explicit DSPy workbench optimization run."""

    optimization_id: str
    target: AiOptimizationTarget
    status: AiOptimizationStatus
    evaluation_result: EvaluationRunServiceResult
    provider_result: DspyOptimizationProviderResult
    artifact: AiPromptProgramArtifactRecord | None

    @property
    def artifact_persisted(self) -> bool:
        return self.artifact is not None


def coerce_ai_optimization_target(
    value: AiOptimizationTarget | str,
) -> AiOptimizationTarget:
    if isinstance(value, AiOptimizationTarget):
        return value
    return AiOptimizationTarget(value)


def evaluation_target_type_for_optimization(
    target: AiOptimizationTarget,
) -> EvaluationTargetType:
    if target is AiOptimizationTarget.RAG_ANSWER_GENERATION:
        return EvaluationTargetType.RAG_GENERATION
    if target is AiOptimizationTarget.RAG_QUERY_REWRITE:
        return EvaluationTargetType.RAG_RETRIEVAL
    if target is AiOptimizationTarget.STRATEGY_SYNTHESIS:
        return EvaluationTargetType.STRATEGY_SYNTHESIS
    return EvaluationTargetType.RECOMMENDATION_EXPLANATION


def _require_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
