from __future__ import annotations

from uuid import UUID

import pytest

from polaris.domain.evidence import (
    ClaimId,
    DecisionEvaluationRef,
    EvidenceJudgmentFamily,
    HumanInvestmentDecisionRef,
    InvalidEvidenceIdentity,
    InvestmentHypothesisRef,
    InvestmentRecommendationRef,
    InvestmentViewRef,
    LessonRef,
    MeaningfulChallengeResultRef,
    PortfolioRiskAssessmentRef,
    ProjectedPortfolioConsequenceRef,
    RecommendationWithholdingJudgmentRef,
    evidence_judgment_family,
    evidence_judgment_ref,
)

IDENTITY = UUID("00000000-0000-4000-8000-000000000301")


@pytest.mark.parametrize(
    ("family", "reference_type"),
    [
        (EvidenceJudgmentFamily.INVESTMENT_HYPOTHESIS, InvestmentHypothesisRef),
        (EvidenceJudgmentFamily.INVESTMENT_VIEW, InvestmentViewRef),
        (
            EvidenceJudgmentFamily.MEANINGFUL_CHALLENGE_RESULT,
            MeaningfulChallengeResultRef,
        ),
        (
            EvidenceJudgmentFamily.PROJECTED_PORTFOLIO_CONSEQUENCE,
            ProjectedPortfolioConsequenceRef,
        ),
        (
            EvidenceJudgmentFamily.PORTFOLIO_RISK_ASSESSMENT,
            PortfolioRiskAssessmentRef,
        ),
        (
            EvidenceJudgmentFamily.INVESTMENT_RECOMMENDATION,
            InvestmentRecommendationRef,
        ),
        (
            EvidenceJudgmentFamily.RECOMMENDATION_WITHHOLDING_JUDGMENT,
            RecommendationWithholdingJudgmentRef,
        ),
        (
            EvidenceJudgmentFamily.HUMAN_INVESTMENT_DECISION,
            HumanInvestmentDecisionRef,
        ),
        (EvidenceJudgmentFamily.DECISION_EVALUATION, DecisionEvaluationRef),
        (EvidenceJudgmentFamily.LESSON, LessonRef),
    ],
)
def test_judgment_reference_union_is_closed_and_owner_specific(
    family: EvidenceJudgmentFamily,
    reference_type: type[object],
) -> None:
    reference = evidence_judgment_ref(family, IDENTITY)

    assert type(reference) is reference_type
    assert evidence_judgment_family(reference) is family
    assert not hasattr(reference, "__dict__")


@pytest.mark.parametrize("identity_type", [InvestmentViewRef, ClaimId])
def test_judgment_and_claim_identities_require_uuid4(
    identity_type: type[object],
) -> None:
    with pytest.raises(InvalidEvidenceIdentity):
        identity_type(UUID("00000000-0000-1000-8000-000000000001"))  # type: ignore[call-arg]
