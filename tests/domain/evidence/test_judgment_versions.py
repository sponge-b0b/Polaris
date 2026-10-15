from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest

from polaris.domain.evidence import (
    ClaimCatalogVersion,
    DecisionEvaluationRef,
    DecisionEvaluationVersionRef,
    HumanInvestmentDecisionRef,
    HumanInvestmentDecisionVersionRef,
    InvestmentHypothesisRef,
    InvestmentHypothesisVersionRef,
    InvestmentRecommendationRef,
    InvestmentRecommendationVersionRef,
    InvestmentViewRef,
    InvestmentViewVersionRef,
    JudgmentRevision,
    LessonRef,
    LessonVersionRef,
    MeaningfulChallengeResultRef,
    MeaningfulChallengeResultVersionRef,
    PortfolioRiskAssessmentRef,
    PortfolioRiskAssessmentVersionRef,
    ProjectedPortfolioConsequenceRef,
    ProjectedPortfolioConsequenceVersionRef,
    RecommendationWithholdingJudgmentRef,
    RecommendationWithholdingJudgmentVersionRef,
    TargetJudgmentVersionRef,
    is_target_judgment_version_ref,
)


@pytest.mark.parametrize(
    ("root_type", "version_type"),
    [
        (InvestmentHypothesisRef, InvestmentHypothesisVersionRef),
        (InvestmentViewRef, InvestmentViewVersionRef),
        (MeaningfulChallengeResultRef, MeaningfulChallengeResultVersionRef),
        (ProjectedPortfolioConsequenceRef, ProjectedPortfolioConsequenceVersionRef),
        (PortfolioRiskAssessmentRef, PortfolioRiskAssessmentVersionRef),
        (InvestmentRecommendationRef, InvestmentRecommendationVersionRef),
        (
            RecommendationWithholdingJudgmentRef,
            RecommendationWithholdingJudgmentVersionRef,
        ),
        (HumanInvestmentDecisionRef, HumanInvestmentDecisionVersionRef),
        (DecisionEvaluationRef, DecisionEvaluationVersionRef),
        (LessonRef, LessonVersionRef),
    ],
)
def test_each_target_family_has_its_own_root_and_version_variant(
    root_type: type[object], version_type: type[object]
) -> None:
    root = root_type(uuid4())  # type: ignore[call-arg]
    version = cast(
        TargetJudgmentVersionRef,
        version_type(root, JudgmentRevision(1)),  # type: ignore[call-arg]
    )

    assert is_target_judgment_version_ref(version)
    assert version.root == root
    assert version.revision == JudgmentRevision(1)
    assert not hasattr(version, "__dict__")

    other_root = root_type(uuid4())  # type: ignore[call-arg]
    assert version_type(other_root, JudgmentRevision(1)) != version  # type: ignore[call-arg]


def test_revision_is_positive_and_distinct_from_claim_catalog_version() -> None:
    for invalid in (0, -1, True, 1.0, "1"):
        with pytest.raises(ValueError, match="positive"):
            JudgmentRevision(invalid)  # type: ignore[arg-type]

    root = InvestmentViewRef(uuid4())
    with pytest.raises(TypeError, match="JudgmentRevision"):
        InvestmentViewVersionRef(root, ClaimCatalogVersion(1))  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="InvestmentViewRef"):
        InvestmentViewVersionRef(InvestmentHypothesisRef(uuid4()), JudgmentRevision(1))  # type: ignore[arg-type]

    assert not is_target_judgment_version_ref(("investment_view", root.value, 1))
