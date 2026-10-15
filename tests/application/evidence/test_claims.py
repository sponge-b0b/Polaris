from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from polaris.application.evidence import (
    ClaimCatalogReadUnavailable,
    ClaimCatalogResolver,
    ClaimCatalogStore,
    ClaimMembershipResolution,
    ClaimNotCurrent,
    ClaimNotKnownAtCutoff,
    ClaimNotYetEffective,
    ClaimTargetNotKnownAtCutoff,
    ClaimTargetNotYetEffective,
    ContestedClaimHistory,
    InvalidClaimHistory,
    InvalidClaimReference,
    ResolvedClaimMembership,
    UnavailableClaimCatalog,
)
from polaris.domain.evidence import (
    ClaimCatalog,
    ClaimCatalogRevision,
    ClaimCatalogVersion,
    ClaimId,
    DecisionEvaluationRef,
    EvidenceJudgmentRef,
    HumanInvestmentDecisionRef,
    InvestmentHypothesisRef,
    InvestmentRecommendationRef,
    InvestmentViewRef,
    LessonRef,
    MeaningfulChallengeResultRef,
    PortfolioRiskAssessmentRef,
    ProjectedPortfolioConsequenceRef,
    RecommendationWithholdingJudgmentRef,
)

TARGET_ID = UUID("00000000-0000-4000-8000-000000000411")
CLAIM_ID = UUID("00000000-0000-4000-8000-000000000412")
UNKNOWN_CLAIM_ID = UUID("00000000-0000-4000-8000-000000000413")
EFFECTIVE_AT = datetime(2026, 9, 10, tzinfo=UTC)
RECORDED_AT = datetime(2026, 9, 11, tzinfo=UTC)


class _ClaimStore(ClaimCatalogStore):
    def __init__(
        self,
        revisions: tuple[ClaimCatalogRevision, ...],
        *,
        unavailable: bool = False,
    ) -> None:
        self.revisions = revisions
        self.unavailable = unavailable

    async def load_claim_catalog(
        self,
        target: EvidenceJudgmentRef,
    ) -> tuple[ClaimCatalogRevision, ...]:
        del target
        if self.unavailable:
            raise ClaimCatalogReadUnavailable("target catalog unavailable")
        return self.revisions


def _catalog(target: EvidenceJudgmentRef | None = None) -> ClaimCatalog:
    return ClaimCatalog.form(
        target or InvestmentRecommendationRef(TARGET_ID),
        (ClaimId(CLAIM_ID),),
        effective_at=EFFECTIVE_AT,
        recorded_at=RECORDED_AT,
    )


def _resolve(
    revisions: tuple[ClaimCatalogRevision, ...],
    target: EvidenceJudgmentRef,
    claim_id: ClaimId | None = None,
    *,
    effective_at: datetime = EFFECTIVE_AT,
    known_at: datetime = RECORDED_AT,
) -> ClaimMembershipResolution:
    return asyncio.run(
        ClaimCatalogResolver(_ClaimStore(revisions)).resolve(
            target,
            claim_id or ClaimId(CLAIM_ID),
            effective_at=effective_at,
            known_at=known_at,
        )
    )


@pytest.mark.parametrize(
    "target",
    [
        InvestmentHypothesisRef(TARGET_ID),
        InvestmentViewRef(TARGET_ID),
        MeaningfulChallengeResultRef(TARGET_ID),
        ProjectedPortfolioConsequenceRef(TARGET_ID),
        PortfolioRiskAssessmentRef(TARGET_ID),
        InvestmentRecommendationRef(TARGET_ID),
        RecommendationWithholdingJudgmentRef(TARGET_ID),
        HumanInvestmentDecisionRef(TARGET_ID),
        DecisionEvaluationRef(TARGET_ID),
        LessonRef(TARGET_ID),
    ],
)
def test_every_admitted_target_family_uses_the_same_typed_catalog_contract(
    target: EvidenceJudgmentRef,
) -> None:
    catalog = _catalog(target)

    assert _resolve(catalog.revisions, target) == ResolvedClaimMembership(
        target,
        ClaimId(CLAIM_ID),
        ClaimCatalogVersion(1),
    )


def test_resolution_preserves_typed_temporal_and_reference_failures() -> None:
    target = InvestmentRecommendationRef(TARGET_ID)
    catalog = _catalog(target)
    retracted = catalog.retract_claim(
        ClaimId(CLAIM_ID),
        effective_at=EFFECTIVE_AT + timedelta(days=2),
        recorded_at=RECORDED_AT + timedelta(days=2),
    )

    assert isinstance(
        _resolve(catalog.revisions, target, known_at=RECORDED_AT - timedelta(days=1)),
        ClaimTargetNotKnownAtCutoff,
    )
    assert isinstance(
        _resolve(
            catalog.revisions,
            target,
            effective_at=EFFECTIVE_AT - timedelta(days=1),
        ),
        ClaimTargetNotYetEffective,
    )
    assert isinstance(
        _resolve(retracted.revisions, target, known_at=RECORDED_AT),
        ResolvedClaimMembership,
    )
    assert isinstance(
        _resolve(
            retracted.revisions,
            target,
            effective_at=EFFECTIVE_AT + timedelta(days=2),
            known_at=RECORDED_AT + timedelta(days=2),
        ),
        ClaimNotCurrent,
    )
    assert isinstance(
        _resolve(catalog.revisions, target, ClaimId(UNKNOWN_CLAIM_ID)),
        InvalidClaimReference,
    )


@pytest.mark.parametrize(
    ("effective_at", "known_at", "expected"),
    [
        (
            EFFECTIVE_AT + timedelta(days=3),
            RECORDED_AT,
            ClaimNotKnownAtCutoff,
        ),
        (
            EFFECTIVE_AT + timedelta(days=1),
            RECORDED_AT + timedelta(days=1),
            ClaimNotYetEffective,
        ),
    ],
)
def test_later_claim_declaration_preserves_temporal_failure_distinctions(
    effective_at: datetime,
    known_at: datetime,
    expected: type[ClaimNotKnownAtCutoff | ClaimNotYetEffective],
) -> None:
    target = InvestmentRecommendationRef(TARGET_ID)
    declared = _catalog(target).declare_claim(
        ClaimId(UNKNOWN_CLAIM_ID),
        effective_at=EFFECTIVE_AT + timedelta(days=2),
        recorded_at=RECORDED_AT + timedelta(days=1),
    )

    result = _resolve(
        declared.revisions,
        target,
        ClaimId(UNKNOWN_CLAIM_ID),
        effective_at=effective_at,
        known_at=known_at,
    )

    assert isinstance(result, expected)


def test_contested_invalid_and_unavailable_histories_remain_distinct() -> None:
    target = InvestmentRecommendationRef(TARGET_ID)
    catalog = _catalog(target)
    competing = replace(catalog.current, claim_ids=frozenset())
    invalid = replace(catalog.current, version=ClaimCatalogVersion(2))

    assert isinstance(
        _resolve((*catalog.revisions, competing), target),
        ContestedClaimHistory,
    )
    assert isinstance(_resolve((invalid,), target), InvalidClaimHistory)
    unavailable = asyncio.run(
        ClaimCatalogResolver(_ClaimStore((), unavailable=True)).resolve(
            target,
            ClaimId(CLAIM_ID),
            effective_at=EFFECTIVE_AT,
            known_at=RECORDED_AT,
        )
    )
    assert isinstance(unavailable, UnavailableClaimCatalog)
