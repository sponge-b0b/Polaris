from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from polaris.application.evidence import (
    ClaimCatalogMembershipResolver,
    EvidenceBindingService,
    EvidenceBindingStore,
    EvidenceRequirementVersionResolver,
    RecordEvidenceBindingCommand,
    ResolvedEvidenceRequirementVersion,
)
from polaris.domain.configuration import EvidenceRequirementApplicabilityKey
from polaris.domain.decisions import OperationId
from polaris.domain.evidence.bindings import (
    EvidenceAvailability,
    EvidenceMaterialQualification,
    EvidenceRole,
)
from polaris.domain.evidence.freshness import EvidenceFreshnessBasisReference
from polaris.domain.evidence.judgments import (
    EvidenceScope,
    EvidenceUse,
    InvestmentRecommendationRef,
    JudgmentWideEvidenceScope,
)
from polaris.domain.evidence.observations import EvidenceObservationId
from tests.configuration_support import (
    TARGET_ID,
    requirement_assignment_for_key,
    requirement_key,
    requirement_version,
)
from tests.evidence_support import OBSERVATION_ID

BINDING_OPERATION_ID = UUID("00000000-0000-4000-8000-000000000301")
SECOND_BINDING_OPERATION_ID = UUID("00000000-0000-4000-8000-000000000302")
BINDING_ID = UUID("00000000-0000-4000-8000-000000000303")
SECOND_BINDING_ID = UUID("00000000-0000-4000-8000-000000000304")
SECOND_TARGET_ID = UUID("00000000-0000-4000-8000-000000000305")
BINDING_EFFECTIVE_AT = datetime(2026, 9, 29, 14, 0, tzinfo=UTC)
BINDING_RECORDED_AT = datetime(2026, 9, 29, 14, 3, tzinfo=UTC)


def binding_command(
    operation_id: UUID = BINDING_OPERATION_ID,
    *,
    availability: EvidenceAvailability = EvidenceAvailability.AVAILABLE,
    materially_used: bool = True,
    role: EvidenceRole = EvidenceRole.SUPPORTING,
    target_id: UUID = TARGET_ID,
    qualification: str | None = "decision-grade source",
    scope: EvidenceScope | None = None,
    key: EvidenceRequirementApplicabilityKey | None = None,
    freshness_basis: EvidenceFreshnessBasisReference | None = None,
) -> RecordEvidenceBindingCommand:
    target = InvestmentRecommendationRef(target_id)
    resolved_scope = scope or JudgmentWideEvidenceScope()
    resolved_key = key or replace(
        requirement_key(),
        target=target,
        scope=resolved_scope,
        evidence_use=EvidenceUse.JUDGMENT_BASIS,
    )
    return RecordEvidenceBindingCommand(
        operation_id=OperationId(operation_id),
        observation_id=EvidenceObservationId(OBSERVATION_ID),
        target=target,
        scope=resolved_scope,
        evidence_use=EvidenceUse.JUDGMENT_BASIS,
        role=role,
        availability=availability,
        materially_used=materially_used,
        effective_at=BINDING_EFFECTIVE_AT,
        # duplicate-code: fixture construction must stay independent from
        # persistence reconstruction so codec tests do not share their subject.
        # arid: disable
        material_qualification=(
            EvidenceMaterialQualification(qualification)
            if qualification is not None
            else None
        ),
        # arid: enable
        freshness_basis=(
            freshness_basis
            or EvidenceFreshnessBasisReference(
                "observation:market-price:SPY",
                BINDING_EFFECTIVE_AT,
                resolved_key,
            )
        ),
    )


class _MatchingRequirementResolver:
    async def resolve(
        self,
        key: EvidenceRequirementApplicabilityKey,
        *,
        effective_at: datetime,
        known_at: datetime,
    ):
        del effective_at, known_at
        return ResolvedEvidenceRequirementVersion(
            requirement_version(
                assignment=requirement_assignment_for_key(key)
            )
        )


def binding_service(
    store: EvidenceBindingStore,
    *identities: UUID,
    claim_catalog: ClaimCatalogMembershipResolver | None = None,
    requirements: EvidenceRequirementVersionResolver | None = None,
) -> EvidenceBindingService:
    values = iter(identities)
    return EvidenceBindingService(
        store=store,
        now=lambda: BINDING_RECORDED_AT,
        new_uuid=lambda: next(values),
        claim_catalog=claim_catalog,
        requirements=requirements or _MatchingRequirementResolver(),
    )
