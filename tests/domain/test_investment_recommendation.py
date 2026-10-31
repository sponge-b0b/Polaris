from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from polaris.application.investment_recommendation import (
    RecommendationSupportKind,
    derive_current_recommendation_support,
)
from polaris.domain.actors import UnknownActorAttribution
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.decisions import InvestmentDecisionId
from polaris.domain.evidence.context_versions import (
    DecisionAlternativeId,
    DecisionAlternativeRevision,
    DecisionAlternativeVersionRef,
)
from polaris.domain.evidence.judgments import (
    InvestmentRecommendationRef,
    InvestmentViewRef,
    MeaningfulChallengeResultRef,
    PortfolioRiskAssessmentRef,
    ProjectedPortfolioConsequenceRef,
    RecommendationWithholdingJudgmentRef,
)
from polaris.domain.investment_intelligence import EconomicDisposition
from polaris.domain.investment_recommendation import (
    AlternativeConsequence,
    InvestmentRecommendation,
    RecommendationWithholdingJudgment,
)
from polaris.domain.portfolio import PortfolioStateId

NOW = datetime(2026, 10, 23, tzinfo=UTC)


def _recommendation(
    decision_id: InvestmentDecisionId, disposition: EconomicDisposition
) -> InvestmentRecommendation:
    alternatives = tuple(
        DecisionAlternativeVersionRef(
            DecisionAlternativeId(uuid4()), DecisionAlternativeRevision(1)
        )
        for _ in range(3)
    )
    return InvestmentRecommendation(
        recommendation_id=InvestmentRecommendationRef(uuid4()),
        decision_id=decision_id,
        horizon=InvestmentHorizon("three months"),
        disposition=disposition,
        view_ids=(InvestmentViewRef(uuid4()),),
        alternatives=alternatives,
        material_evidence=(),
        challenge_ids=(MeaningfulChallengeResultRef(uuid4()),),
        uncertainty="Market path remains uncertain",
        source_state_id=PortfolioStateId(uuid4()),
        consequences=tuple(
            AlternativeConsequence(item, ProjectedPortfolioConsequenceRef(uuid4()))
            for item in alternatives
        ),
        risk_assessment_ids=(PortfolioRiskAssessmentRef(uuid4()),),
        material_assumptions=("cash remains sufficient",),
        invalidation_conditions=("liquidity falls",),
        review_condition_refs=(),
        proposed_action_refs=(),
        actor_attribution=UnknownActorAttribution(),
        formed_at=NOW,
    )


def test_withholding_and_hold_are_distinct_from_no_attempt() -> None:
    decision_id = InvestmentDecisionId(uuid4())
    empty = derive_current_recommendation_support(
        (), decision_applicable=True, evidence_fit=True, risk_fit=True
    )
    withholding = RecommendationWithholdingJudgment(
        RecommendationWithholdingJudgmentRef(uuid4()),
        decision_id,
        InvestmentHorizon("three months"),
        "Material Risk is unresolved",
        UnknownActorAttribution(),
        NOW,
    )
    withheld = derive_current_recommendation_support(
        (withholding,), decision_applicable=True, evidence_fit=True, risk_fit=True
    )
    hold = _recommendation(decision_id, EconomicDisposition.HOLD)
    supported = derive_current_recommendation_support(
        (withholding, hold),
        decision_applicable=True,
        evidence_fit=True,
        risk_fit=True,
    )
    assert empty.kind is RecommendationSupportKind.NO_ATTEMPT
    assert withheld.kind is RecommendationSupportKind.WITHHELD
    assert supported.kind is RecommendationSupportKind.SUPPORTED
    assert supported.latest == hold
    assert hold.disposition is EconomicDisposition.HOLD


def test_unsupported_latest_preference_does_not_reactivate_older_one() -> None:
    decision_id = InvestmentDecisionId(uuid4())
    older = _recommendation(decision_id, EconomicDisposition.INCREASE)
    newer = _recommendation(decision_id, EconomicDisposition.REDUCE)
    result = derive_current_recommendation_support(
        (older, newer),
        decision_applicable=True,
        evidence_fit=False,
        risk_fit=True,
    )
    assert result.kind is RecommendationSupportKind.UNSUPPORTED
    assert result.latest == newer
    assert result.latest != older


def test_material_portfolio_consequence_set_is_complete() -> None:
    recommendation = _recommendation(
        InvestmentDecisionId(uuid4()), EconomicDisposition.INCREASE
    )
    with pytest.raises(ValueError, match="each material Alternative"):
        replace(recommendation, consequences=recommendation.consequences[:-1])
    with pytest.raises(TypeError, match="actual Portfolio State"):
        replace(recommendation, source_state_id=None)  # type: ignore[arg-type]
