from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from polaris.domain.configuration import (
    EvidenceRequirementId,
    EvidenceRequirementSetId,
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
)
from polaris.domain.evidence.sufficiency import (
    EvidenceBindingInterpretation,
    EvidenceBindingInterpretationState,
)
from tests.configuration_support import (
    FRESHNESS_ID,
    ROOT_VERSION_ID,
    SET_ID,
    requirement_key,
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
