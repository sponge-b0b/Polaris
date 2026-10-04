from datetime import UTC, datetime
from uuid import UUID

import pytest

from polaris.domain.evidence import (
    EvidenceBindingId,
    EvidenceCorrectionId,
    EvidenceObservation,
    EvidenceObservationId,
    EvidenceObservationMaterial,
    EvidenceSourceProvenance,
    EvidenceSubjectReference,
    EvidenceSufficiencyAssessmentId,
    InvalidEvidenceIdentity,
    InvalidEvidenceObservation,
)

OBSERVATION_ID = UUID("00000000-0000-4000-8000-000000000101")
BINDING_ID = UUID("00000000-0000-4000-8000-000000000102")
ASSESSMENT_ID = UUID("00000000-0000-4000-8000-000000000103")
CORRECTION_ID = UUID("00000000-0000-4000-8000-000000000104")
OBSERVED_AT = datetime(2026, 9, 29, 13, 0, tzinfo=UTC)
ACQUIRED_AT = datetime(2026, 9, 29, 13, 1, tzinfo=UTC)


def _observation(**changes: object) -> EvidenceObservation:
    values: dict[str, object] = {
        "observation_id": EvidenceObservationId(OBSERVATION_ID),
        "source": EvidenceSourceProvenance(
            "fred",
            "series:CPIAUCSL:2026-08",
            "Federal Reserve Bank of St. Louis / source publisher",
        ),
        "subject": EvidenceSubjectReference(
            "US:CPI",
            "2026-08",
        ),
        "observed_at": OBSERVED_AT,
        "acquired_at": ACQUIRED_AT,
        "effective_at": OBSERVED_AT,
        "material": EvidenceObservationMaterial(
            retained_representation='{"value": 321.1}'
        ),
    }
    values.update(changes)
    return EvidenceObservation(**values)  # type: ignore[arg-type]


def test_first_class_evidence_identities_are_distinct_uuid4_types() -> None:
    identities = (
        EvidenceObservationId(OBSERVATION_ID),
        EvidenceBindingId(BINDING_ID),
        EvidenceSufficiencyAssessmentId(ASSESSMENT_ID),
        EvidenceCorrectionId(CORRECTION_ID),
    )

    assert len({type(identity) for identity in identities}) == 4
    assert len({identity.value for identity in identities}) == 4


@pytest.mark.parametrize(
    "identity_type",
    # duplicate-code: this test independently enumerates the closed identity union;
    # deriving cases from production would make the contract proof tautological.
    # arid: disable
    [
        EvidenceObservationId,
        EvidenceBindingId,
        EvidenceSufficiencyAssessmentId,
        EvidenceCorrectionId,
    ],
    # arid: enable
)
def test_evidence_identities_reject_non_uuid4(identity_type: type[object]) -> None:
    with pytest.raises(InvalidEvidenceIdentity):
        identity_type(UUID("00000000-0000-1000-8000-000000000001"))  # type: ignore[call-arg]


def test_observation_preserves_attributable_temporal_and_reconstruction_data() -> None:
    observation = _observation()

    assert observation.source.source_identity == "fred"
    assert observation.source.source_authority.startswith("Federal Reserve")
    assert observation.subject.subject_identity == "US:CPI"
    assert observation.observed_at == OBSERVED_AT
    assert observation.acquired_at == ACQUIRED_AT
    assert observation.effective_at == OBSERVED_AT
    assert observation.material.retained_representation == '{"value": 321.1}'


def test_observation_requires_reconstructable_material() -> None:
    with pytest.raises(InvalidEvidenceObservation):
        EvidenceObservationMaterial()


@pytest.mark.parametrize("field", ["observed_at", "acquired_at", "effective_at"])
def test_observation_rejects_naive_temporal_boundaries(field: str) -> None:
    with pytest.raises(InvalidEvidenceObservation):
        _observation(**{field: datetime(2026, 9, 29, 13, 0)})


def test_observation_may_reference_immutable_verification_material_only() -> None:
    material = EvidenceObservationMaterial(verification_reference="sha256:abc123")
    observation = _observation(material=material)

    assert observation.material.retained_representation is None
    assert observation.material.verification_reference == "sha256:abc123"


def test_observation_rejects_self_supersession() -> None:
    identity = EvidenceObservationId(OBSERVATION_ID)
    with pytest.raises(InvalidEvidenceObservation):
        _observation(
            observation_id=identity,
            supersedes_observation_id=identity,
        )
