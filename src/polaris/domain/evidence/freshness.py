from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from polaris.domain.configuration.evidence_requirements import (
    EvidenceRequirementApplicabilityKey,
    EvidenceRequirementId,
    EvidenceRequirementSetId,
    EvidenceRequirementSetVersionId,
    FreshnessRequirementDefinition,
)


class InvalidEvidenceFreshness(ValueError):
    pass


# duplicate-code: Evidence freshness owns its failure contract independently of
# Decision time validation; sharing a validator would couple bounded contexts.
# arid: disable
def _aware(value: object, field_name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InvalidEvidenceFreshness(f"{field_name} must be timezone-aware")


# arid: enable


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidEvidenceFreshness(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_exact(
    value: object,
    expected: type[object],
    field_name: str,
) -> None:
    if type(value) is not expected:
        raise TypeError(f"{field_name} must be {expected.__name__}")


def _require_basis(value: object) -> None:
    _require_exact(value, EvidenceFreshnessBasisReference, "basis")


def _reason(value: object, owner: str) -> str:
    return _text(value, f"{owner}.reason")


class EvidenceFreshnessResult(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessBasisReference:
    """Exact durable basis used by one historical freshness evaluation."""

    reference: str
    as_of_at: datetime
    applicability_key: EvidenceRequirementApplicabilityKey

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reference",
            _text(self.reference, "EvidenceFreshnessBasisReference.reference"),
        )
        _aware(self.as_of_at, "EvidenceFreshnessBasisReference.as_of_at")
        _require_exact(
            self.applicability_key,
            EvidenceRequirementApplicabilityKey,
            "applicability_key",
        )


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessAuthorityReference:
    """Exact resolved Configuration authority used by freshness evaluation."""

    set_id: EvidenceRequirementSetId
    version_id: EvidenceRequirementSetVersionId
    requirement_id: EvidenceRequirementId

    def __post_init__(self) -> None:
        _require_exact(self.set_id, EvidenceRequirementSetId, "set_id")
        _require_exact(self.version_id, EvidenceRequirementSetVersionId, "version_id")
        _require_exact(self.requirement_id, EvidenceRequirementId, "requirement_id")


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessNoRequirementWitness:
    """Resolved set/version that authoritatively contains no freshness rule."""

    set_id: EvidenceRequirementSetId
    version_id: EvidenceRequirementSetVersionId

    def __post_init__(self) -> None:
        _require_exact(self.set_id, EvidenceRequirementSetId, "set_id")
        _require_exact(self.version_id, EvidenceRequirementSetVersionId, "version_id")


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessApplicable:
    authority: EvidenceFreshnessAuthorityReference
    basis: EvidenceFreshnessBasisReference
    result: EvidenceFreshnessResult

    def __post_init__(self) -> None:
        _require_exact(
            self.authority,
            EvidenceFreshnessAuthorityReference,
            "authority",
        )
        _require_basis(self.basis)
        _require_exact(self.result, EvidenceFreshnessResult, "result")


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessNotApplicable:
    witness: EvidenceFreshnessNoRequirementWitness
    basis: EvidenceFreshnessBasisReference

    def __post_init__(self) -> None:
        _require_exact(
            self.witness,
            EvidenceFreshnessNoRequirementWitness,
            "witness",
        )
        _require_basis(self.basis)


@dataclass(frozen=True, slots=True)
class _IndeterminateFreshness:
    basis: EvidenceFreshnessBasisReference
    result: EvidenceFreshnessResult = field(
        default=EvidenceFreshnessResult.INDETERMINATE,
        init=False,
    )

    def __post_init__(self) -> None:
        _require_basis(self.basis)


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessMissingAuthority(_IndeterminateFreshness):
    pass


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessUnavailableAuthority(_IndeterminateFreshness):
    reason: str

    def __post_init__(self) -> None:
        _IndeterminateFreshness.__post_init__(self)
        object.__setattr__(
            self,
            "reason",
            _reason(self.reason, "EvidenceFreshnessUnavailableAuthority"),
        )


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessContestedAuthority(_IndeterminateFreshness):
    version_ids: frozenset[EvidenceRequirementSetVersionId]

    def __post_init__(self) -> None:
        _IndeterminateFreshness.__post_init__(self)
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
        _require_basis(self.basis)
        object.__setattr__(
            self,
            "reason",
            _reason(self.reason, "EvidenceFreshnessInvalidAuthority"),
        )


type EvidenceFreshnessEvaluation = (
    EvidenceFreshnessApplicable
    | EvidenceFreshnessNotApplicable
    | EvidenceFreshnessMissingAuthority
    | EvidenceFreshnessUnavailableAuthority
    | EvidenceFreshnessContestedAuthority
    | EvidenceFreshnessInvalidAuthority
)


def evaluate_evidence_freshness(
    *,
    basis: EvidenceFreshnessBasisReference,
    authority_set_id: EvidenceRequirementSetId,
    authority_version_id: EvidenceRequirementSetVersionId,
    requirement: FreshnessRequirementDefinition,
    effective_at: datetime,
) -> EvidenceFreshnessApplicable:
    """Evaluate freshness against one exact resolved Configuration requirement."""

    result = (
        EvidenceFreshnessResult.INDETERMINATE
        if basis.as_of_at > effective_at
        else (
            EvidenceFreshnessResult.FRESH
            if effective_at - basis.as_of_at <= requirement.maximum_age
            else EvidenceFreshnessResult.STALE
        )
    )
    return EvidenceFreshnessApplicable(
        EvidenceFreshnessAuthorityReference(
            authority_set_id,
            authority_version_id,
            requirement.requirement_id,
        ),
        basis,
        result,
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
