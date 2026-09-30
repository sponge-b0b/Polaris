from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from polaris.application.evidence import (
    EvidenceBindingService,
    EvidenceBindingStore,
    RecordEvidenceBindingCommand,
)
from polaris.domain.configuration import (
    EvidenceRequirementId,
    EvidenceRequirementSetId,
    EvidenceRequirementSetVersionId,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence.bindings import (
    EvidenceAvailability,
    EvidenceFreshnessAuthorityReference,
    EvidenceFreshnessBasisReference,
    EvidenceMaterialQualification,
    EvidenceRole,
)
from polaris.domain.evidence.judgments import (
    EvidenceUse,
    InvestmentRecommendationRef,
    JudgmentWideEvidenceScope,
)
from polaris.domain.evidence.observations import EvidenceObservationId
from tests.configuration_support import (
    FRESHNESS_ID,
    ROOT_VERSION_ID,
    SET_ID,
    TARGET_ID,
)
from tests.evidence_support import OBSERVATION_ID

BINDING_OPERATION_ID = UUID("00000000-0000-4000-8000-000000000301")
SECOND_BINDING_OPERATION_ID = UUID("00000000-0000-4000-8000-000000000302")
BINDING_ID = UUID("00000000-0000-4000-8000-000000000303")
SECOND_BINDING_ID = UUID("00000000-0000-4000-8000-000000000304")
BINDING_EFFECTIVE_AT = datetime(2026, 9, 29, 14, 0, tzinfo=UTC)
BINDING_RECORDED_AT = datetime(2026, 9, 29, 14, 3, tzinfo=UTC)


def binding_command(
    operation_id: UUID = BINDING_OPERATION_ID,
    *,
    availability: EvidenceAvailability = EvidenceAvailability.AVAILABLE,
    materially_used: bool = True,
    role: EvidenceRole = EvidenceRole.SUPPORTING,
    with_freshness: bool = False,
    qualification: str | None = "decision-grade source",
) -> RecordEvidenceBindingCommand:
    return RecordEvidenceBindingCommand(
        operation_id=OperationId(operation_id),
        observation_id=EvidenceObservationId(OBSERVATION_ID),
        target=InvestmentRecommendationRef(TARGET_ID),
        scope=JudgmentWideEvidenceScope(),
        evidence_use=EvidenceUse.JUDGMENT_BASIS,
        role=role,
        availability=availability,
        materially_used=materially_used,
        effective_at=BINDING_EFFECTIVE_AT,
        material_qualification=(
            EvidenceMaterialQualification(qualification)
            if qualification is not None
            else None
        ),
        freshness_authority=(
            EvidenceFreshnessAuthorityReference(
                set_id=EvidenceRequirementSetId(SET_ID),
                version_id=EvidenceRequirementSetVersionId(ROOT_VERSION_ID),
                requirement_id=EvidenceRequirementId(FRESHNESS_ID),
            )
            if with_freshness
            else None
        ),
        freshness_basis=(
            EvidenceFreshnessBasisReference("observation:market-price:SPY")
            if with_freshness
            else None
        ),
    )


def binding_service(
    store: EvidenceBindingStore,
    *identities: UUID,
) -> EvidenceBindingService:
    values = iter(identities)
    return EvidenceBindingService(
        store=store,
        now=lambda: BINDING_RECORDED_AT,
        new_uuid=lambda: next(values),
    )
