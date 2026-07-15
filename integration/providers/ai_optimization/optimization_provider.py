from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from domain.evaluation import EvaluationCase


@dataclass(frozen=True, slots=True)
class DspyOptimizationProviderRequest:
    """Provider request for building a DSPy optimization candidate artifact."""

    optimization_id: str
    target_component: str
    cases: Sequence[EvaluationCase]
    prompt_name: str
    prompt_version: str
    artifact_name: str
    artifact_version: str
    model_name: str

    def __post_init__(self) -> None:
        for field_name in (
            "optimization_id",
            "target_component",
            "prompt_name",
            "prompt_version",
            "artifact_name",
            "artifact_version",
            "model_name",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if not self.cases:
            raise ValueError("cases cannot be empty.")


@dataclass(frozen=True, slots=True)
class DspyOptimizedCaseOutput:
    """Candidate output produced for one evaluation case."""

    case_id: str
    actual_output: str

    def __post_init__(self) -> None:
        _require_non_empty(self.case_id, "case_id")
        _require_non_empty(self.actual_output, "actual_output")


@dataclass(frozen=True, slots=True)
class DspyOptimizedArtifact:
    """Serialized DSPy prompt/program candidate prepared for persistence."""

    artifact_name: str
    artifact_version: str
    prompt_reference: str
    prompt_hash: str
    program_text: str

    def __post_init__(self) -> None:
        for field_name in (
            "artifact_name",
            "artifact_version",
            "prompt_reference",
            "prompt_hash",
            "program_text",
        ):
            _require_non_empty(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class DspyOptimizationProviderResult:
    """Provider result for one DSPy optimization candidate."""

    optimization_id: str
    target_component: str
    provider_name: str
    model_name: str
    artifact: DspyOptimizedArtifact
    case_outputs: tuple[DspyOptimizedCaseOutput, ...]
    candidate_count: int
    selected_candidate_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "optimization_id",
            "target_component",
            "provider_name",
            "model_name",
            "selected_candidate_id",
        ):
            _require_non_empty(getattr(self, field_name), field_name)
        if not self.case_outputs:
            raise ValueError("case_outputs cannot be empty.")
        if self.candidate_count <= 0:
            raise ValueError("candidate_count must be greater than zero.")


class DspyOptimizationProviderProtocol(Protocol):
    """Provider boundary for DSPy optimization workbench implementations."""

    async def optimize(
        self,
        request: DspyOptimizationProviderRequest,
    ) -> DspyOptimizationProviderResult: ...


def _require_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
