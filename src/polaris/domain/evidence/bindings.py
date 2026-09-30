from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from polaris.domain.configuration.evidence_requirements import (
    EvidenceRequirementId,
    EvidenceRequirementSetId,
    EvidenceRequirementSetVersionId,
)

from .judgments import (
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


def _aware(value: object, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InvalidEvidenceBinding(f"{field} must be timezone-aware")


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


@dataclass(frozen=True, slots=True)
class EvidenceMaterialQualification:
    statement: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "statement",
            _text(self.statement, "EvidenceMaterialQualification.statement"),
        )


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessAuthorityReference:
    """Exact Configuration authority used by later freshness evaluation."""

    set_id: EvidenceRequirementSetId
    version_id: EvidenceRequirementSetVersionId
    requirement_id: EvidenceRequirementId

    def __post_init__(self) -> None:
        if type(self.set_id) is not EvidenceRequirementSetId:
            raise TypeError("set_id must be EvidenceRequirementSetId")
        if type(self.version_id) is not EvidenceRequirementSetVersionId:
            raise TypeError("version_id must be EvidenceRequirementSetVersionId")
        if type(self.requirement_id) is not EvidenceRequirementId:
            raise TypeError("requirement_id must be EvidenceRequirementId")


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessBasisReference:
    """Opaque durable handle to the exact basis used by freshness evaluation."""

    reference: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reference",
            _text(self.reference, "EvidenceFreshnessBasisReference.reference"),
        )


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
    material_qualification: EvidenceMaterialQualification | None = None
    freshness_authority: EvidenceFreshnessAuthorityReference | None = None
    freshness_basis: EvidenceFreshnessBasisReference | None = None

    def __post_init__(self) -> None:
        if type(self.binding_id) is not EvidenceBindingId:
            raise TypeError("binding_id must be EvidenceBindingId")
        if type(self.observation_id) is not EvidenceObservationId:
            raise TypeError("observation_id must be EvidenceObservationId")
        if not is_evidence_judgment_ref(self.target):
            raise TypeError("target must be an EvidenceJudgmentRef")

        # Claim-specific scope is already part of the accepted vocabulary, but
        # admission requires target-owned historical claim validation implemented
        # by the next ticket. This ticket establishes the judgment-wide root only.
        if type(self.scope) is not JudgmentWideEvidenceScope:
            raise InvalidEvidenceBinding(
                "binding scope must be judgment-wide until target-owned "
                "claim validation is available"
            )
        if type(self.evidence_use) is not EvidenceUse:
            raise TypeError("evidence_use must be EvidenceUse")
        if type(self.role) is not EvidenceRole:
            raise TypeError("role must be EvidenceRole")
        if type(self.availability) is not EvidenceAvailability:
            raise TypeError("availability must be EvidenceAvailability")
        if type(self.materially_used) is not bool:
            raise TypeError("materially_used must be bool")
        if self.materially_used and self.availability is not EvidenceAvailability.AVAILABLE:
            raise InvalidEvidenceBinding(
                "materially used Evidence must have AVAILABLE judgment-time availability"
            )

        _aware(self.effective_at, "EvidenceBinding.effective_at")
        _aware(self.recorded_at, "EvidenceBinding.recorded_at")

        if (
            self.material_qualification is not None
            and type(self.material_qualification) is not EvidenceMaterialQualification
        ):
            raise TypeError(
                "material_qualification must be EvidenceMaterialQualification or None"
            )
        if (
            self.freshness_authority is not None
            and type(self.freshness_authority)
            is not EvidenceFreshnessAuthorityReference
        ):
            raise TypeError(
                "freshness_authority must be EvidenceFreshnessAuthorityReference or None"
            )
        if (
            self.freshness_basis is not None
            and type(self.freshness_basis) is not EvidenceFreshnessBasisReference
        ):
            raise TypeError(
                "freshness_basis must be EvidenceFreshnessBasisReference or None"
            )
        if (self.freshness_authority is None) != (self.freshness_basis is None):
            raise InvalidEvidenceBinding(
                "freshness authority and basis references must be present together"
            )


__all__ = [
    "EvidenceAvailability",
    "EvidenceBinding",
    "EvidenceFreshnessAuthorityReference",
    "EvidenceFreshnessBasisReference",
    "EvidenceMaterialQualification",
    "EvidenceRole",
    "InvalidEvidenceBinding",
    "InvalidEvidenceIdentity",
]
