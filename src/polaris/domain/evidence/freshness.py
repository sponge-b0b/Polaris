from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from polaris.domain.configuration.evidence_requirements import (
    EvidenceRequirementId,
    EvidenceRequirementSetId,
    EvidenceRequirementSetVersionId,
)


class InvalidEvidenceFreshness(ValueError):
    pass


def _aware(value: object, field_name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InvalidEvidenceFreshness(f"{field_name} must be timezone-aware")


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidEvidenceFreshness(f"{field_name} must be a non-empty string")
    return value.strip()


class EvidenceFreshnessResult(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessBasisReference:
    """Exact durable basis used by one historical freshness evaluation."""

    reference: str
    as_of_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reference",
            _text(self.reference, "EvidenceFreshnessBasisReference.reference"),
        )
        _aware(self.as_of_at, "EvidenceFreshnessBasisReference.as_of_at")


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessAuthorityReference:
    """Exact resolved Configuration authority used by freshness evaluation."""

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
class EvidenceFreshnessNoRequirementWitness:
    """Resolved set/version that authoritatively contains no freshness rule."""

    set_id: EvidenceRequirementSetId
    version_id: EvidenceRequirementSetVersionId

    def __post_init__(self) -> None:
        if type(self.set_id) is not EvidenceRequirementSetId:
            raise TypeError("set_id must be EvidenceRequirementSetId")
        if type(self.version_id) is not EvidenceRequirementSetVersionId:
            raise TypeError("version_id must be EvidenceRequirementSetVersionId")


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessApplicable:
    authority: EvidenceFreshnessAuthorityReference
    basis: EvidenceFreshnessBasisReference
    result: EvidenceFreshnessResult

    def __post_init__(self) -> None:
        if type(self.authority) is not EvidenceFreshnessAuthorityReference:
            raise TypeError("authority must be EvidenceFreshnessAuthorityReference")
        if type(self.basis) is not EvidenceFreshnessBasisReference:
            raise TypeError("basis must be EvidenceFreshnessBasisReference")
        if type(self.result) is not EvidenceFreshnessResult:
            raise TypeError("result must be EvidenceFreshnessResult")


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessNotApplicable:
    witness: EvidenceFreshnessNoRequirementWitness
    basis: EvidenceFreshnessBasisReference

    def __post_init__(self) -> None:
        if type(self.witness) is not EvidenceFreshnessNoRequirementWitness:
            raise TypeError("witness must be EvidenceFreshnessNoRequirementWitness")
        if type(self.basis) is not EvidenceFreshnessBasisReference:
            raise TypeError("basis must be EvidenceFreshnessBasisReference")


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessMissingAuthority:
    basis: EvidenceFreshnessBasisReference
    result: EvidenceFreshnessResult = field(
        default=EvidenceFreshnessResult.INDETERMINATE,
        init=False,
    )

    def __post_init__(self) -> None:
        if type(self.basis) is not EvidenceFreshnessBasisReference:
            raise TypeError("basis must be EvidenceFreshnessBasisReference")


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessUnavailableAuthority:
    basis: EvidenceFreshnessBasisReference
    reason: str
    result: EvidenceFreshnessResult = field(
        default=EvidenceFreshnessResult.INDETERMINATE,
        init=False,
    )

    def __post_init__(self) -> None:
        if type(self.basis) is not EvidenceFreshnessBasisReference:
            raise TypeError("basis must be EvidenceFreshnessBasisReference")
        object.__setattr__(
            self,
            "reason",
            _text(self.reason, "EvidenceFreshnessUnavailableAuthority.reason"),
        )


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessContestedAuthority:
    basis: EvidenceFreshnessBasisReference
    version_ids: frozenset[EvidenceRequirementSetVersionId]
    result: EvidenceFreshnessResult = field(
        default=EvidenceFreshnessResult.INDETERMINATE,
        init=False,
    )

    def __post_init__(self) -> None:
        if type(self.basis) is not EvidenceFreshnessBasisReference:
            raise TypeError("basis must be EvidenceFreshnessBasisReference")
        if (
            type(self.version_ids) is not frozenset
            or len(self.version_ids) < 2
            or any(
                type(version_id) is not EvidenceRequirementSetVersionId
                for version_id in self.version_ids
            )
        ):
            raise InvalidEvidenceFreshness(
                "version_ids must contain at least two requirement-set version IDs"
            )


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessInvalidAuthority:
    basis: EvidenceFreshnessBasisReference
    reason: str

    def __post_init__(self) -> None:
        if type(self.basis) is not EvidenceFreshnessBasisReference:
            raise TypeError("basis must be EvidenceFreshnessBasisReference")
        object.__setattr__(
            self,
            "reason",
            _text(self.reason, "EvidenceFreshnessInvalidAuthority.reason"),
        )


type EvidenceFreshnessEvaluation = (
    EvidenceFreshnessApplicable
    | EvidenceFreshnessNotApplicable
    | EvidenceFreshnessMissingAuthority
    | EvidenceFreshnessUnavailableAuthority
    | EvidenceFreshnessContestedAuthority
    | EvidenceFreshnessInvalidAuthority
)


def is_evidence_freshness_evaluation(value: object) -> bool:
    return type(value) in (
        EvidenceFreshnessApplicable,
        EvidenceFreshnessNotApplicable,
        EvidenceFreshnessMissingAuthority,
        EvidenceFreshnessUnavailableAuthority,
        EvidenceFreshnessContestedAuthority,
        EvidenceFreshnessInvalidAuthority,
    )
