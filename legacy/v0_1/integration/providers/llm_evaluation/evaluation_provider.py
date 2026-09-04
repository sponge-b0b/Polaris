from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from domain.evaluation import (
    EvaluationCase,
    EvaluationMetricResult,
    EvaluationStatus,
    EvaluationThreshold,
)


@dataclass(frozen=True, slots=True)
class EvaluationMetricSpec:
    """Metric selection and threshold policy for one evaluation run."""

    metric_name: str
    threshold: EvaluationThreshold | None = None
    include_reason: bool = True
    criteria: str | None = None
    evaluation_steps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.metric_name.strip():
            raise ValueError("metric_name cannot be empty.")
        if (
            self.threshold is not None
            and self.threshold.metric_name != self.metric_name
        ):
            raise ValueError("threshold metric_name must match metric_name.")
        if self.criteria is not None and not self.criteria.strip():
            raise ValueError("criteria cannot be empty when provided.")
        cleaned_steps = tuple(
            step.strip() for step in self.evaluation_steps if step.strip()
        )
        if len(cleaned_steps) != len(self.evaluation_steps):
            raise ValueError("evaluation_steps cannot contain empty values.")
        object.__setattr__(self, "evaluation_steps", cleaned_steps)


@dataclass(frozen=True, slots=True)
class EvaluationProviderRequest:
    """Typed request for evaluating canonical Polaris evaluation cases."""

    run_id: str
    cases: Sequence[EvaluationCase]
    metrics: Sequence[EvaluationMetricSpec]
    timeout_seconds: float | None = None

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id cannot be empty.")
        if not self.cases:
            raise ValueError("cases cannot be empty.")
        if not self.metrics:
            raise ValueError("metrics cannot be empty.")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be greater than 0.0.")


@dataclass(frozen=True, slots=True)
class EvaluationProviderResult:
    """Normalized provider result returned to the application layer."""

    run_id: str
    status: EvaluationStatus
    metric_results: tuple[EvaluationMetricResult, ...]
    evaluator_provider: str
    evaluator_model: str
    duration_ms: float
    error_message: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("run_id", "evaluator_provider", "evaluator_model"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} cannot be empty.")
        if self.duration_ms < 0.0:
            raise ValueError("duration_ms cannot be negative.")
        if self.error_message is not None and not self.error_message.strip():
            raise ValueError("error_message cannot be empty.")


@runtime_checkable
class EvaluationProvider(Protocol):
    """Provider boundary for LLM evaluation engines such as DeepEval."""

    async def evaluate(
        self,
        request: EvaluationProviderRequest,
    ) -> EvaluationProviderResult: ...
