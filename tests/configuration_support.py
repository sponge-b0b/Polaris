from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from polaris.domain.configuration import (
    ConfigurationAuthority,
    EvidenceRequirementApplicabilityAssignment,
    EvidenceRequirementApplicabilityKey,
    EvidenceRequirementId,
    EvidenceRequirementPredecessor,
    EvidenceRequirementPredecessorEffect,
    EvidenceRequirementScopeAssignment,
    EvidenceRequirementSetId,
    EvidenceRequirementSetVersion,
    EvidenceRequirementSetVersionId,
    EvidenceRequirementTargetAssignment,
    FreshnessRequirementDefinition,
    InvestmentHorizon,
    SufficiencyRequirementDefinition,
)
from polaris.domain.evidence import (
    ClaimSpecificEvidenceScope,
    EvidenceSubjectReference,
    EvidenceUse,
    InvestmentRecommendationRef,
    JudgmentWideEvidenceScope,
    evidence_judgment_family,
    evidence_scope_kind,
)
from polaris.domain.portfolio import FinancialInstrumentId, PortfolioId

SET_ID = UUID("00000000-0000-4000-8000-000000000201")
ROOT_VERSION_ID = UUID("00000000-0000-4000-8000-000000000202")
SECOND_VERSION_ID = UUID("00000000-0000-4000-8000-000000000203")
THIRD_VERSION_ID = UUID("00000000-0000-4000-8000-000000000204")
FRESHNESS_ID = UUID("00000000-0000-4000-8000-000000000205")
SUFFICIENCY_ID = UUID("00000000-0000-4000-8000-000000000206")
PORTFOLIO_ID = UUID("00000000-0000-4000-8000-000000000207")
INSTRUMENT_ID = UUID("00000000-0000-4000-8000-000000000208")
TARGET_ID = UUID("00000000-0000-4000-8000-000000000209")
CLAIM_ID = UUID("00000000-0000-4000-8000-00000000020a")
EFFECTIVE_AT = datetime(2026, 9, 29, 14, 0, tzinfo=UTC)
RECORDED_AT = datetime(2026, 9, 29, 14, 1, tzinfo=UTC)


def requirement_key() -> EvidenceRequirementApplicabilityKey:
    return EvidenceRequirementApplicabilityKey(
        target=InvestmentRecommendationRef(TARGET_ID),
        scope=JudgmentWideEvidenceScope(),
        evidence_use=EvidenceUse.JUDGMENT_BASIS,
        subject=EvidenceSubjectReference("market_price", "SPY"),
        portfolio_id=PortfolioId(PORTFOLIO_ID),
        instrument_id=FinancialInstrumentId(INSTRUMENT_ID),
        investment_horizon=InvestmentHorizon("five trading days"),
    )


def requirement_assignment_for_key(
    key: EvidenceRequirementApplicabilityKey,
) -> EvidenceRequirementApplicabilityAssignment:
    claim_id = (
        key.scope.claim_id
        if type(key.scope) is ClaimSpecificEvidenceScope
        else None
    )
    return EvidenceRequirementApplicabilityAssignment(
        target=EvidenceRequirementTargetAssignment(
            evidence_judgment_family(key.target),
            key.target,
        ),
        scope=EvidenceRequirementScopeAssignment(
            evidence_scope_kind(key.scope),
            claim_id,
        ),
        evidence_use=key.evidence_use,
        subject=key.subject,
        portfolio_id=key.portfolio_id,
        instrument_id=key.instrument_id,
        investment_horizon=key.investment_horizon,
    )


def requirement_assignment() -> EvidenceRequirementApplicabilityAssignment:
    return requirement_assignment_for_key(requirement_key())


class RequirementResolutionStub:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls = 0

    async def resolve(
        self,
        key: EvidenceRequirementApplicabilityKey,
        *,
        effective_at: datetime,
        known_at: datetime,
    ):
        del key, effective_at, known_at
        self.calls += 1
        return self.result


class RequirementVersionStoreStub:
    def __init__(self, versions: object) -> None:
        self.versions = tuple(versions)

    async def load_requirement_versions(self):
        return self.versions

    async def append_requirement_version(self, version):
        raise AssertionError("not used by requirement-resolution tests")


def requirement_version(
    version_id: UUID = ROOT_VERSION_ID,
    *,
    set_id: UUID = SET_ID,
    effective_at: datetime = EFFECTIVE_AT,
    recorded_at: datetime = RECORDED_AT,
    predecessor_id: UUID | None = None,
    effect: EvidenceRequirementPredecessorEffect = (
        EvidenceRequirementPredecessorEffect.CORRECTS
    ),
    maximum_age: timedelta = timedelta(minutes=2),
    predicate: str = "one available non-contested supporting price observation",
    assignment: EvidenceRequirementApplicabilityAssignment | None = None,
) -> EvidenceRequirementSetVersion:
    return EvidenceRequirementSetVersion(
        set_id=EvidenceRequirementSetId(set_id),
        version_id=EvidenceRequirementSetVersionId(version_id),
        authority=ConfigurationAuthority(
            "Polaris product configuration",
            "r3-spy-evidence-requirements",
        ),
        effective_at=effective_at,
        recorded_at=recorded_at,
        applicability=assignment or requirement_assignment(),
        requirements=(
            FreshnessRequirementDefinition(
                EvidenceRequirementId(FRESHNESS_ID),
                maximum_age,
            ),
            SufficiencyRequirementDefinition(
                EvidenceRequirementId(SUFFICIENCY_ID),
                predicate,
            ),
        ),
        predecessor=(
            EvidenceRequirementPredecessor(
                EvidenceRequirementSetVersionId(predecessor_id),
                effect,
            )
            if predecessor_id is not None
            else None
        ),
    )


def corrected_requirement_version() -> EvidenceRequirementSetVersion:
    return requirement_version(
        SECOND_VERSION_ID,
        effective_at=EFFECTIVE_AT - timedelta(days=1),
        recorded_at=RECORDED_AT + timedelta(hours=1),
        predecessor_id=ROOT_VERSION_ID,
        effect=EvidenceRequirementPredecessorEffect.CORRECTS,
    )

