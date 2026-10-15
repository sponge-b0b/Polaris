from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from polaris.domain.actors import UnknownActorAttribution
from polaris.domain.configuration import (
    EvidenceRequirementId,
    EvidenceRequirementSetId,
    EvidenceRequirementSetVersion,
    EvidenceRequirementSetVersionId,
)
from polaris.domain.evidence.bindings import (
    EvidenceAvailability,
    EvidenceBinding,
    EvidenceRole,
)
from polaris.domain.evidence.freshness import (
    EvidenceFreshnessApplicable,
    EvidenceFreshnessAuthorityReference,
    EvidenceFreshnessBasisReference,
    EvidenceFreshnessResult,
)
from polaris.domain.evidence.observations import (
    EvidenceBindingId,
    EvidenceObservationId,
    EvidenceSufficiencyAssessmentId,
    EvidenceSupportVersion,
)
from polaris.domain.evidence.sufficiency import (
    EvidenceBindingInterpretation,
    EvidenceBindingInterpretationState,
    EvidenceBindingUniverseGuard,
    EvidenceCorrectionUniverseGuard,
    EvidenceRequirementAuthorityGuard,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyBasisGuards,
    evaluate_evidence_sufficiency,
)
from tests.configuration_support import (
    FRESHNESS_ID,
    ROOT_VERSION_ID,
    SET_ID,
    requirement_key,
    requirement_version,
)

ASSESSMENT_EFFECTIVE_AT = datetime(2026, 9, 29, 14, 2, tzinfo=UTC)
ASSESSMENT_KNOWN_AT = datetime(2026, 9, 29, 14, 3, tzinfo=UTC)
BINDING_RECORDED_AT = datetime(2026, 9, 29, 14, 1, tzinfo=UTC)


def interpreted_binding(
    ordinal: int = 1,
    *,
    observation_ordinal: int | None = None,
    role: EvidenceRole = EvidenceRole.SUPPORTING,
    availability: EvidenceAvailability = EvidenceAvailability.AVAILABLE,
    materially_used: bool = True,
    freshness_result: EvidenceFreshnessResult = EvidenceFreshnessResult.FRESH,
    basis_at: datetime | None = None,
    state: EvidenceBindingInterpretationState = (
        EvidenceBindingInterpretationState.DETERMINATE
    ),
) -> EvidenceBindingInterpretation:
    key = requirement_key()
    assert key.subject is not None
    binding_id = EvidenceBindingId(UUID(f"00000000-0000-4000-8000-{ordinal:012x}"))
    observation_id = EvidenceObservationId(
        UUID(f"10000000-0000-4000-8000-{(observation_ordinal or ordinal):012x}")
    )
    binding = EvidenceBinding(
        binding_id=binding_id,
        observation_id=observation_id,
        target=key.target,
        scope=key.scope,
        evidence_use=key.evidence_use,
        role=role,
        availability=availability,
        materially_used=materially_used,
        effective_at=ASSESSMENT_EFFECTIVE_AT - timedelta(minutes=1),
        recorded_at=BINDING_RECORDED_AT,
        freshness=EvidenceFreshnessApplicable(
            EvidenceFreshnessAuthorityReference(
                set_id=EvidenceRequirementSetId(SET_ID),
                version_id=EvidenceRequirementSetVersionId(ROOT_VERSION_ID),
                requirement_id=EvidenceRequirementId(FRESHNESS_ID),
            ),
            EvidenceFreshnessBasisReference(
                "test:sufficiency-basis",
                basis_at or ASSESSMENT_EFFECTIVE_AT,
                key,
            ),
            freshness_result,
        ),
    )
    return EvidenceBindingInterpretation(
        binding=binding,
        subject=key.subject,
        state=state,
        fact_support=frozenset({binding_id, observation_id}),
    )


def derived_assessment(
    ordinal: int = 1,
    *,
    interpretations: tuple[EvidenceBindingInterpretation, ...] | None = None,
    version: EvidenceRequirementSetVersion | None = None,
) -> EvidenceSufficiencyAssessment:
    key = requirement_key()
    version = requirement_version() if version is None else version
    bindings = (interpreted_binding(),) if interpretations is None else interpretations
    evaluation = evaluate_evidence_sufficiency(
        version,
        key,
        bindings,
        effective_at=ASSESSMENT_EFFECTIVE_AT,
        known_at=ASSESSMENT_KNOWN_AT,
    )
    # duplicate-code: the test builder states an independent expected proof
    # shape and must not derive its expectation through the application writer.
    # arid: disable
    return EvidenceSufficiencyAssessment(
        assessment_id=EvidenceSufficiencyAssessmentId(
            UUID(f"20000000-0000-4000-8000-{ordinal:012x}")
        ),
        target=key.target,
        scope=key.scope,
        evidence_use=key.evidence_use,
        applicability_key=key,
        requirement_set_id=version.set_id,
        requirement_version_id=version.version_id,
        support_version=EvidenceSupportVersion(1),
        basis_guards=EvidenceSufficiencyBasisGuards(
            EvidenceBindingUniverseGuard(
                frozenset(value.binding.binding_id for value in bindings)
            ),
            EvidenceCorrectionUniverseGuard(frozenset()),
            EvidenceRequirementAuthorityGuard(frozenset({version.version_id})),
        ),
        requirement_assessments=evaluation.requirement_assessments,
        attribution=UnknownActorAttribution(),
        effective_at=ASSESSMENT_EFFECTIVE_AT,
        known_at=ASSESSMENT_KNOWN_AT,
        recorded_at=ASSESSMENT_KNOWN_AT + timedelta(minutes=1),
        result=evaluation.result,
        no_requirements_witness=evaluation.no_requirements_witness,
    )
    # arid: enable
