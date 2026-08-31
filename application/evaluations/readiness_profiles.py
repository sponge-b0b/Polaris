from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from math import isfinite

from application.evaluations.evaluation_datasets import (
    CANONICAL_EVALUATION_DATASET_DEFINITIONS,
    CANONICAL_EVALUATION_DATASET_SLICE_DEFINITIONS,
    EVALUATION_DATASET_VERSION,
)
from application.evaluations.rag_evaluation_metrics import (
    INTELLIGENCE_EVALUATION_METRIC_DEFINITIONS,
    MCP_TOOL_RESPONSE_EVALUATION_METRIC_DEFINITIONS,
    RAG_EVALUATION_METRIC_DEFINITIONS,
    EvaluationMetricDefinition,
)
from domain.authority import GateProfile, RiskTier, gate_profile_for_tier
from domain.evaluation import EvaluationTargetType


class ReadinessRunMode(StrEnum):
    """Operational cadence for one readiness evaluation."""

    LOCAL_PR = "local_pr"
    RELEASE = "release"
    MODEL_PROFILE_REPLACEMENT = "model_profile_replacement"
    PRODUCTION = "production"


class ReadinessFailurePolicy(StrEnum):
    """Failure semantics owned by a versioned readiness profile."""

    FAIL_CLOSED = "fail_closed"
    PROHIBITED_NEGATIVE = "prohibited_negative"


class ReadinessDatasetScope(StrEnum):
    """Whether a dataset requirement names a full dataset or named slice."""

    DATASET = "dataset"
    SLICE = "slice"


@dataclass(frozen=True, slots=True)
class ReadinessDatasetRequirement:
    """Versioned evaluation dataset or slice required by a readiness profile."""

    name: str
    version: str
    scope: ReadinessDatasetScope
    target_types: tuple[EvaluationTargetType, ...] = ()
    run_modes: tuple[ReadinessRunMode, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _require_non_empty(self.name, "name"))
        object.__setattr__(
            self,
            "version",
            _require_non_empty(self.version, "version"),
        )

    def applies_to(
        self,
        *,
        target_type: EvaluationTargetType,
        run_mode: ReadinessRunMode,
    ) -> bool:
        target_applies = not self.target_types or target_type in self.target_types
        run_mode_applies = not self.run_modes or run_mode in self.run_modes
        return target_applies and run_mode_applies


@dataclass(frozen=True, slots=True)
class ReadinessMetricRequirement:
    """Unit-quality metric threshold owned by a readiness profile."""

    metric_name: str
    version: str
    minimum_score: float
    allowed_drift: float
    target_types: tuple[EvaluationTargetType, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metric_name",
            _require_non_empty(self.metric_name, "metric_name"),
        )
        object.__setattr__(
            self,
            "version",
            _require_non_empty(self.version, "version"),
        )
        _require_unit_score(self.minimum_score, "minimum_score")
        _require_unit_score(self.allowed_drift, "allowed_drift")
        if not self.target_types:
            raise ValueError("target_types cannot be empty.")

    def applies_to(self, target_type: EvaluationTargetType) -> bool:
        return target_type in self.target_types


@dataclass(frozen=True, slots=True)
class ReadinessProfile:
    """Versioned requirements for one canonical risk-authority gate profile."""

    profile_version: str
    risk_tier: RiskTier
    gate_profile: GateProfile
    dataset_requirements: tuple[ReadinessDatasetRequirement, ...]
    metric_requirements: tuple[ReadinessMetricRequirement, ...]
    cadence: tuple[ReadinessRunMode, ...]
    required_artifacts: tuple[str, ...]
    live_service_requirements: tuple[str, ...]
    failure_policy: ReadinessFailurePolicy

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "profile_version",
            _require_non_empty(self.profile_version, "profile_version"),
        )
        if self.gate_profile is not gate_profile_for_tier(self.risk_tier):
            raise ValueError("gate_profile must match the canonical risk tier.")
        if not self.cadence:
            raise ValueError("cadence cannot be empty.")
        object.__setattr__(
            self,
            "required_artifacts",
            _clean_string_tuple(self.required_artifacts, "required_artifact"),
        )
        object.__setattr__(
            self,
            "live_service_requirements",
            _clean_string_tuple(
                self.live_service_requirements,
                "live_service_requirement",
            ),
        )

    @property
    def profile_id(self) -> str:
        return self.gate_profile.value


def _clean_string_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    return tuple(_require_non_empty(value, field_name) for value in values)


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned


def _require_unit_score(value: float, field_name: str) -> None:
    if not isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")


_ENHANCED_DATASETS = tuple(
    ReadinessDatasetRequirement(
        definition.reference.name,
        definition.reference.version,
        ReadinessDatasetScope.DATASET,
        (definition.target_type,),
    )
    for definition in CANONICAL_EVALUATION_DATASET_DEFINITIONS
) + tuple(
    ReadinessDatasetRequirement(
        definition.name,
        EVALUATION_DATASET_VERSION,
        ReadinessDatasetScope.SLICE,
        run_modes=(ReadinessRunMode.MODEL_PROFILE_REPLACEMENT,),
    )
    for definition in CANONICAL_EVALUATION_DATASET_SLICE_DEFINITIONS
)


def _metric_requirements(
    definitions: tuple[EvaluationMetricDefinition, ...],
    *,
    allowed_drift: float,
) -> tuple[ReadinessMetricRequirement, ...]:
    return tuple(
        ReadinessMetricRequirement(
            metric_name=definition.metric_name,
            version=definition.threshold.version,
            minimum_score=definition.threshold.minimum_score,
            allowed_drift=allowed_drift,
            target_types=definition.target_types,
        )
        for definition in definitions
    )


_ENHANCED_METRICS = _metric_requirements(
    (
        *RAG_EVALUATION_METRIC_DEFINITIONS,
        *INTELLIGENCE_EVALUATION_METRIC_DEFINITIONS,
        *MCP_TOOL_RESPONSE_EVALUATION_METRIC_DEFINITIONS,
    ),
    allowed_drift=0.05,
)
_VIGILANT_METRICS = tuple(
    replace(requirement, allowed_drift=0.02) for requirement in _ENHANCED_METRICS
)

_BASELINE_ARTIFACTS = ("baseline_architecture_regression",)
_ENHANCED_ARTIFACTS = (
    *_BASELINE_ARTIFACTS,
    "structured_output_conformance",
    "canonical_evaluation_coverage",
    "provenance_reconstruction",
    "retention_reconstruction",
)
_VIGILANT_ARTIFACTS = (
    *_ENHANCED_ARTIFACTS,
    "decision_evidence_packet",
    "governance_accountability",
    "red_team_evidence",
    "replay_evidence",
    "residual_risk_acceptance",
)

_READINESS_PROFILE_BY_GATE: Mapping[GateProfile, ReadinessProfile] = {
    GateProfile.BASELINE_INTERNAL: ReadinessProfile(
        profile_version="baseline_v1",
        risk_tier=RiskTier.BASELINE,
        gate_profile=GateProfile.BASELINE_INTERNAL,
        dataset_requirements=(),
        metric_requirements=(),
        cadence=(ReadinessRunMode.LOCAL_PR, ReadinessRunMode.RELEASE),
        required_artifacts=_BASELINE_ARTIFACTS,
        live_service_requirements=(),
        failure_policy=ReadinessFailurePolicy.FAIL_CLOSED,
    ),
    GateProfile.ENHANCED_PROVENANCE: ReadinessProfile(
        profile_version="enhanced_v2",
        risk_tier=RiskTier.ENHANCED,
        gate_profile=GateProfile.ENHANCED_PROVENANCE,
        dataset_requirements=_ENHANCED_DATASETS,
        metric_requirements=_ENHANCED_METRICS,
        cadence=(
            ReadinessRunMode.RELEASE,
            ReadinessRunMode.MODEL_PROFILE_REPLACEMENT,
        ),
        required_artifacts=_ENHANCED_ARTIFACTS,
        live_service_requirements=("observability_projection",),
        failure_policy=ReadinessFailurePolicy.FAIL_CLOSED,
    ),
    GateProfile.VIGILANT_DECISION_EVIDENCE: ReadinessProfile(
        profile_version="vigilant_v2",
        risk_tier=RiskTier.VIGILANT,
        gate_profile=GateProfile.VIGILANT_DECISION_EVIDENCE,
        dataset_requirements=_ENHANCED_DATASETS,
        metric_requirements=_VIGILANT_METRICS,
        cadence=(
            ReadinessRunMode.RELEASE,
            ReadinessRunMode.MODEL_PROFILE_REPLACEMENT,
            ReadinessRunMode.PRODUCTION,
        ),
        required_artifacts=_VIGILANT_ARTIFACTS,
        live_service_requirements=(
            "persisted_live_evaluation",
            "observability_projection",
        ),
        failure_policy=ReadinessFailurePolicy.FAIL_CLOSED,
    ),
    GateProfile.PROHIBITED_BOUNDARY: ReadinessProfile(
        profile_version="prohibited_v1",
        risk_tier=RiskTier.PROHIBITED_OUTSIDE_AUTHORITY,
        gate_profile=GateProfile.PROHIBITED_BOUNDARY,
        dataset_requirements=(),
        metric_requirements=(),
        cadence=(
            ReadinessRunMode.LOCAL_PR,
            ReadinessRunMode.RELEASE,
            ReadinessRunMode.PRODUCTION,
        ),
        required_artifacts=("prohibited_boundary_negative_test",),
        live_service_requirements=(),
        failure_policy=ReadinessFailurePolicy.PROHIBITED_NEGATIVE,
    ),
}


def readiness_profile_for_gate(gate_profile: GateProfile) -> ReadinessProfile:
    """Resolve the current versioned readiness profile for a canonical gate."""

    return _READINESS_PROFILE_BY_GATE[gate_profile]


def canonical_readiness_profiles() -> tuple[ReadinessProfile, ...]:
    """Return canonical profiles in increasing risk order."""

    return tuple(_READINESS_PROFILE_BY_GATE[gate] for gate in GateProfile)
