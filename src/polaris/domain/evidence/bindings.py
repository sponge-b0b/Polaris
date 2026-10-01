from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .freshness import EvidenceFreshnessEvaluation, is_evidence_freshness_evaluation
from .judgments import (
    ClaimSpecificEvidenceScope,
    EvidenceJudgmentRef,
    EvidenceScope,
    EvidenceUse,
    JudgmentWideEvidenceScope,
    is_evidence_judgment_ref,
)
from .observations import (
    EvidenceBindingId,
    EvidenceObservationId,
    InvalidEvidenceIdentity,
)


class InvalidEvidenceBinding(ValueError):
    pass


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidEvidenceBinding(f"{field} must be a non-empty string")
    return value.strip()


# duplicate-code: binding-domain time validation owns InvalidEvidenceBinding
# semantics; sharing another layer/domain validator would couple failure contracts.
# arid: disable
def _aware(value: object, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InvalidEvidenceBinding(f"{field} must be timezone-aware")


# arid: enable


class EvidenceRole(StrEnum):
    SUPPORTING = "supporting"
    CONFLICTING = "conflicting"
    CONSTRAINING = "constraining"
    QUALIFYING = "qualifying"
    CONTEXTUAL = "contextual"
    RECONSTRUCTION = "reconstruction"


class EvidenceAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


# duplicate-code: this Evidence-owned value object may evolve independently of
# similarly shaped statement wrappers in other domains.
# arid: disable
@dataclass(frozen=True, slots=True)
class EvidenceMaterialQualification:
    statement: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "statement",
            _text(self.statement, "EvidenceMaterialQualification.statement"),
        )


# arid: enable


@dataclass(frozen=True, slots=True)
class EvidenceBinding:
    binding_id: EvidenceBindingId
    observation_id: EvidenceObservationId
    target: EvidenceJudgmentRef
    scope: EvidenceScope
    evidence_use: EvidenceUse
    role: EvidenceRole
    availability: EvidenceAvailability
    materially_used: bool
    effective_at: datetime
    recorded_at: datetime
    freshness: EvidenceFreshnessEvaluation
    material_qualification: EvidenceMaterialQualification | None = None

    def __post_init__(self) -> None:
        _validate_binding_endpoints(self)
        _validate_binding_usage(self)
        _validate_binding_optional_metadata(self)


def _validate_binding_endpoints(binding: EvidenceBinding) -> None:
    if type(binding.binding_id) is not EvidenceBindingId:
        raise TypeError("binding_id must be EvidenceBindingId")
    if type(binding.observation_id) is not EvidenceObservationId:
        raise TypeError("observation_id must be EvidenceObservationId")
    if not is_evidence_judgment_ref(binding.target):
        raise TypeError("target must be an EvidenceJudgmentRef")

    if type(binding.scope) not in (
        JudgmentWideEvidenceScope,
        ClaimSpecificEvidenceScope,
    ):
        raise TypeError("scope must be an EvidenceScope")
    if type(binding.evidence_use) is not EvidenceUse:
        raise TypeError("evidence_use must be EvidenceUse")


def _validate_binding_usage(binding: EvidenceBinding) -> None:
    if type(binding.role) is not EvidenceRole:
        raise TypeError("role must be EvidenceRole")
    if type(binding.availability) is not EvidenceAvailability:
        raise TypeError("availability must be EvidenceAvailability")
    if type(binding.materially_used) is not bool:
        raise TypeError("materially_used must be bool")
    if (
        binding.materially_used
        and binding.availability is not EvidenceAvailability.AVAILABLE
    ):
        raise InvalidEvidenceBinding(
            "materially used Evidence must have AVAILABLE "
            + "judgment-time availability"
        )

    _aware(binding.effective_at, "EvidenceBinding.effective_at")
    _aware(binding.recorded_at, "EvidenceBinding.recorded_at")


def _validate_binding_optional_metadata(binding: EvidenceBinding) -> None:
    if (
        binding.material_qualification is not None
        and type(binding.material_qualification) is not EvidenceMaterialQualification
    ):
        raise TypeError(
            "material_qualification must be EvidenceMaterialQualification or None"
        )
    if not is_evidence_freshness_evaluation(binding.freshness):
        raise TypeError("freshness must be an EvidenceFreshnessEvaluation")
    key = binding.freshness.basis.applicability_key
    if (
        key.target != binding.target
        or key.scope != binding.scope
        or key.evidence_use is not binding.evidence_use
    ):
        raise InvalidEvidenceBinding(
            "freshness applicability target/scope/use must match binding endpoints"
        )


__all__ = [
    "EvidenceAvailability",
    "EvidenceBinding",
    "EvidenceMaterialQualification",
    "EvidenceRole",
    "InvalidEvidenceBinding",
    "InvalidEvidenceIdentity",
]
