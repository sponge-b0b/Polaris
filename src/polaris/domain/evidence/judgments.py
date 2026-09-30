from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import cast
from uuid import UUID

from .observations import InvalidEvidenceIdentity


def _uuid4(value: object, field: str) -> None:
    if type(value) is not UUID or value.version != 4:
        raise InvalidEvidenceIdentity(f"{field} must be UUIDv4")


@dataclass(frozen=True, slots=True)
class _EvidenceJudgmentIdentity:
    value: UUID

    def __post_init__(self) -> None:
        _uuid4(self.value, f"{type(self).__name__}.value")


@dataclass(frozen=True, slots=True)
class InvestmentHypothesisRef(_EvidenceJudgmentIdentity):
    pass


@dataclass(frozen=True, slots=True)
class InvestmentViewRef(_EvidenceJudgmentIdentity):
    pass


@dataclass(frozen=True, slots=True)
class MeaningfulChallengeResultRef(_EvidenceJudgmentIdentity):
    pass


@dataclass(frozen=True, slots=True)
class ProjectedPortfolioConsequenceRef(_EvidenceJudgmentIdentity):
    pass


@dataclass(frozen=True, slots=True)
class PortfolioRiskAssessmentRef(_EvidenceJudgmentIdentity):
    pass


@dataclass(frozen=True, slots=True)
class InvestmentRecommendationRef(_EvidenceJudgmentIdentity):
    pass


@dataclass(frozen=True, slots=True)
class RecommendationWithholdingJudgmentRef(_EvidenceJudgmentIdentity):
    pass


@dataclass(frozen=True, slots=True)
class HumanInvestmentDecisionRef(_EvidenceJudgmentIdentity):
    pass


@dataclass(frozen=True, slots=True)
class DecisionEvaluationRef(_EvidenceJudgmentIdentity):
    pass


@dataclass(frozen=True, slots=True)
class LessonRef(_EvidenceJudgmentIdentity):
    pass


type EvidenceJudgmentRef = (
    InvestmentHypothesisRef
    | InvestmentViewRef
    | MeaningfulChallengeResultRef
    | ProjectedPortfolioConsequenceRef
    | PortfolioRiskAssessmentRef
    | InvestmentRecommendationRef
    | RecommendationWithholdingJudgmentRef
    | HumanInvestmentDecisionRef
    | DecisionEvaluationRef
    | LessonRef
)


class EvidenceJudgmentFamily(StrEnum):
    INVESTMENT_HYPOTHESIS = "investment_hypothesis"
    INVESTMENT_VIEW = "investment_view"
    MEANINGFUL_CHALLENGE_RESULT = "meaningful_challenge_result"
    PROJECTED_PORTFOLIO_CONSEQUENCE = "projected_portfolio_consequence"
    PORTFOLIO_RISK_ASSESSMENT = "portfolio_risk_assessment"
    INVESTMENT_RECOMMENDATION = "investment_recommendation"
    RECOMMENDATION_WITHHOLDING_JUDGMENT = "recommendation_withholding_judgment"
    HUMAN_INVESTMENT_DECISION = "human_investment_decision"
    DECISION_EVALUATION = "decision_evaluation"
    LESSON = "lesson"


_REF_TYPE_BY_FAMILY: dict[
    EvidenceJudgmentFamily,
    type[_EvidenceJudgmentIdentity],
] = {
    EvidenceJudgmentFamily.INVESTMENT_HYPOTHESIS: InvestmentHypothesisRef,
    EvidenceJudgmentFamily.INVESTMENT_VIEW: InvestmentViewRef,
    EvidenceJudgmentFamily.MEANINGFUL_CHALLENGE_RESULT: MeaningfulChallengeResultRef,
    EvidenceJudgmentFamily.PROJECTED_PORTFOLIO_CONSEQUENCE: (
        ProjectedPortfolioConsequenceRef
    ),
    EvidenceJudgmentFamily.PORTFOLIO_RISK_ASSESSMENT: PortfolioRiskAssessmentRef,
    EvidenceJudgmentFamily.INVESTMENT_RECOMMENDATION: InvestmentRecommendationRef,
    EvidenceJudgmentFamily.RECOMMENDATION_WITHHOLDING_JUDGMENT: (
        RecommendationWithholdingJudgmentRef
    ),
    EvidenceJudgmentFamily.HUMAN_INVESTMENT_DECISION: HumanInvestmentDecisionRef,
    EvidenceJudgmentFamily.DECISION_EVALUATION: DecisionEvaluationRef,
    EvidenceJudgmentFamily.LESSON: LessonRef,
}
_FAMILY_BY_REF_TYPE = {
    reference_type: family for family, reference_type in _REF_TYPE_BY_FAMILY.items()
}


def evidence_judgment_ref(
    family: EvidenceJudgmentFamily,
    value: UUID,
) -> EvidenceJudgmentRef:
    if type(family) is not EvidenceJudgmentFamily:
        raise TypeError("family must be EvidenceJudgmentFamily")
    reference_type = _REF_TYPE_BY_FAMILY[family]
    return cast(EvidenceJudgmentRef, reference_type(value))


def evidence_judgment_family(
    reference: EvidenceJudgmentRef,
) -> EvidenceJudgmentFamily:
    try:
        return _FAMILY_BY_REF_TYPE[type(reference)]
    except KeyError as error:
        raise TypeError("reference must be an EvidenceJudgmentRef") from error


def is_evidence_judgment_ref(value: object) -> bool:
    return type(value) in _FAMILY_BY_REF_TYPE


@dataclass(frozen=True, slots=True)
class ClaimId:
    """Dependent identity meaningful only with a typed target judgment."""

    value: UUID

    def __post_init__(self) -> None:
        _uuid4(self.value, "ClaimId.value")


class EvidenceScopeKind(StrEnum):
    JUDGMENT_WIDE = "judgment_wide"
    CLAIM_SPECIFIC = "claim_specific"


@dataclass(frozen=True, slots=True)
class JudgmentWideEvidenceScope:
    pass


@dataclass(frozen=True, slots=True)
class ClaimSpecificEvidenceScope:
    claim_id: ClaimId

    def __post_init__(self) -> None:
        if type(self.claim_id) is not ClaimId:
            raise TypeError("claim_id must be ClaimId")


type EvidenceScope = JudgmentWideEvidenceScope | ClaimSpecificEvidenceScope


def evidence_scope_kind(scope: EvidenceScope) -> EvidenceScopeKind:
    if type(scope) is JudgmentWideEvidenceScope:
        return EvidenceScopeKind.JUDGMENT_WIDE
    if type(scope) is ClaimSpecificEvidenceScope:
        return EvidenceScopeKind.CLAIM_SPECIFIC
    raise TypeError("scope must be an EvidenceScope")


class EvidenceUse(StrEnum):
    JUDGMENT_BASIS = "judgment_basis"
    CHALLENGE_BASIS = "challenge_basis"
    CURRENT_SUPPORT_CHECK = "current_support_check"
    RETROSPECTIVE_LATER_EVIDENCE = "retrospective_later_evidence"
    RECONSTRUCTION_ONLY = "reconstruction_only"
