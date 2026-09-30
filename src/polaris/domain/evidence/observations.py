from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class EvidenceError(ValueError):
    """Base class for Evidence-domain semantic failures."""


class InvalidEvidenceIdentity(EvidenceError):
    pass


class InvalidEvidenceObservation(EvidenceError):
    pass


def _uuid4(value: object, field: str) -> None:
    if type(value) is not UUID or value.version != 4:
        raise InvalidEvidenceIdentity(f"{field} must be UUIDv4")


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidEvidenceObservation(f"{field} must be a non-empty string")
    return value.strip()


# duplicate-code: Evidence owns its domain validation and failure type;
# sharing this with Decisions would couple independent bounded-context semantics.
# arid: disable
def _aware(value: object, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InvalidEvidenceObservation(f"{field} must be timezone-aware")


# arid: enable


@dataclass(frozen=True, slots=True)
class EvidenceObservationId:
    value: UUID

    def __post_init__(self) -> None:
        _uuid4(self.value, "EvidenceObservationId.value")


@dataclass(frozen=True, slots=True)
class EvidenceBindingId:
    value: UUID

    def __post_init__(self) -> None:
        _uuid4(self.value, "EvidenceBindingId.value")


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyAssessmentId:
    value: UUID

    def __post_init__(self) -> None:
        _uuid4(self.value, "EvidenceSufficiencyAssessmentId.value")


@dataclass(frozen=True, slots=True)
class EvidenceCorrectionId:
    value: UUID

    def __post_init__(self) -> None:
        _uuid4(self.value, "EvidenceCorrectionId.value")


@dataclass(frozen=True, slots=True)
class EvidenceSourceProvenance:
    """Attributable source identity without transferring factual authority."""

    source_identity: str
    source_reference: str
    source_authority: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_identity",
            _text(self.source_identity, "EvidenceSourceProvenance.source_identity"),
        )
        object.__setattr__(
            self,
            "source_reference",
            _text(self.source_reference, "EvidenceSourceProvenance.source_reference"),
        )
        object.__setattr__(
            self,
            "source_authority",
            _text(self.source_authority, "EvidenceSourceProvenance.source_authority"),
        )


@dataclass(frozen=True, slots=True)
class EvidenceSubjectReference:
    subject_identity: str
    subject_reference: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "subject_identity",
            _text(self.subject_identity, "EvidenceSubjectReference.subject_identity"),
        )
        object.__setattr__(
            self,
            "subject_reference",
            _text(
                self.subject_reference,
                "EvidenceSubjectReference.subject_reference",
            ),
        )


@dataclass(frozen=True, slots=True)
class EvidenceObservationMaterial:
    """Durable observation material sufficient for later reconstruction."""

    retained_representation: str | None = None
    verification_reference: str | None = None

    def __post_init__(self) -> None:
        retained = (
            _text(
                self.retained_representation,
                "EvidenceObservationMaterial.retained_representation",
            )
            if self.retained_representation is not None
            else None
        )
        reference = (
            _text(
                self.verification_reference,
                "EvidenceObservationMaterial.verification_reference",
            )
            if self.verification_reference is not None
            else None
        )
        if retained is None and reference is None:
            raise InvalidEvidenceObservation(
                "Evidence observation requires retained representation or "
                "verification reference"
            )
        object.__setattr__(self, "retained_representation", retained)
        object.__setattr__(self, "verification_reference", reference)


@dataclass(frozen=True, slots=True)
class EvidenceObservation:
    observation_id: EvidenceObservationId
    source: EvidenceSourceProvenance
    subject: EvidenceSubjectReference
    observed_at: datetime
    acquired_at: datetime
    material: EvidenceObservationMaterial
    effective_at: datetime | None = None
    supersedes_observation_id: EvidenceObservationId | None = None

    def __post_init__(self) -> None:
        if type(self.observation_id) is not EvidenceObservationId:
            raise TypeError("observation_id must be EvidenceObservationId")
        if type(self.source) is not EvidenceSourceProvenance:
            raise TypeError("source must be EvidenceSourceProvenance")
        if type(self.subject) is not EvidenceSubjectReference:
            raise TypeError("subject must be EvidenceSubjectReference")
        if type(self.material) is not EvidenceObservationMaterial:
            raise TypeError("material must be EvidenceObservationMaterial")
        _aware(self.observed_at, "EvidenceObservation.observed_at")
        _aware(self.acquired_at, "EvidenceObservation.acquired_at")
        if self.effective_at is not None:
            _aware(self.effective_at, "EvidenceObservation.effective_at")
        if (
            self.supersedes_observation_id is not None
            and type(self.supersedes_observation_id) is not EvidenceObservationId
        ):
            raise TypeError(
                "supersedes_observation_id must be EvidenceObservationId or None"
            )
        if self.supersedes_observation_id == self.observation_id:
            raise InvalidEvidenceObservation(
                "Evidence observation cannot supersede itself"
            )
