"""Attributable Recommendation and explicit withholding judgments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from polaris.domain.actors import ActorAttribution, is_actor_attribution
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.decisions import InvestmentDecisionId
from polaris.domain.evidence import EvidenceBindingId
from polaris.domain.evidence.context_versions import DecisionAlternativeVersionRef
from polaris.domain.evidence.judgments import (
    InvestmentRecommendationRef,
    InvestmentViewRef,
    MeaningfulChallengeResultRef,
    PortfolioRiskAssessmentRef,
    ProjectedPortfolioConsequenceRef,
    RecommendationWithholdingJudgmentRef,
)
from polaris.domain.investment_intelligence import EconomicDisposition
from polaris.domain.portfolio import PortfolioStateId


def _typed_refs(values: tuple[object, ...], kind: type[object], field: str) -> None:
    if type(values) is not tuple or any(type(value) is not kind for value in values):
        raise TypeError(f"{field} must contain typed references")
    if len(set(values)) != len(values):
        raise ValueError(f"{field} must contain distinct references")


def _substantive(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be substantive")


def _common(
    decision_id: InvestmentDecisionId,
    horizon: InvestmentHorizon,
    actor: ActorAttribution,
    formed_at: datetime,
) -> None:
    if type(decision_id) is not InvestmentDecisionId:
        raise TypeError("Recommendation judgment requires a typed Decision")
    if type(horizon) is not InvestmentHorizon:
        raise TypeError("Recommendation judgment requires an explicit horizon")
    if not is_actor_attribution(actor):
        raise TypeError("Recommendation judgment requires actor attribution")
    if not isinstance(formed_at, datetime) or formed_at.utcoffset() is None:
        raise ValueError("formation time must be timezone-aware")


def _require_consequences(
    alternatives: tuple[DecisionAlternativeVersionRef, ...],
    consequences: tuple[AlternativeConsequence, ...],
) -> None:
    if type(consequences) is not tuple or any(
        type(item) is not AlternativeConsequence for item in consequences
    ):
        raise TypeError("projected consequences must be typed")
    if len(consequences) != len(alternatives) or {
        item.alternative for item in consequences
    } != set(alternatives):
        raise ValueError("each material Alternative needs one projected consequence")
    if len({item.consequence_id for item in consequences}) != len(consequences):
        raise ValueError("projected consequence identities must be distinct")


def _require_texts_and_refs(recommendation: InvestmentRecommendation) -> None:
    _substantive(recommendation.uncertainty, "investment uncertainty")
    for field in ("material_assumptions", "invalidation_conditions"):
        values = getattr(recommendation, field)
        if type(values) is not tuple:
            raise TypeError(f"{field} must be a tuple")
        for value in values:
            _substantive(value, field)
    for field in ("review_condition_refs", "proposed_action_refs"):
        values = getattr(recommendation, field)
        if type(values) is not tuple or any(
            type(value) is not UUID or value.version != 4 for value in values
        ):
            raise TypeError(f"{field} must contain opaque UUIDv4 references")
        if len(set(values)) != len(values):
            raise ValueError(f"{field} must contain distinct references")


@dataclass(frozen=True, slots=True)
class AlternativeConsequence:
    alternative: DecisionAlternativeVersionRef
    consequence_id: ProjectedPortfolioConsequenceRef

    def __post_init__(self) -> None:
        if type(self.alternative) is not DecisionAlternativeVersionRef:
            raise TypeError("alternative must be a typed owner version")
        if type(self.consequence_id) is not ProjectedPortfolioConsequenceRef:
            raise TypeError("consequence must be a typed Portfolio judgment")


@dataclass(frozen=True, slots=True)
class InvestmentRecommendation:
    """A new attributable preference; current support is derived elsewhere."""

    recommendation_id: InvestmentRecommendationRef
    decision_id: InvestmentDecisionId
    horizon: InvestmentHorizon
    disposition: EconomicDisposition
    view_ids: tuple[InvestmentViewRef, ...]
    alternatives: tuple[DecisionAlternativeVersionRef, ...]
    material_evidence: tuple[EvidenceBindingId, ...]
    challenge_ids: tuple[MeaningfulChallengeResultRef, ...]
    uncertainty: str
    source_state_id: PortfolioStateId
    consequences: tuple[AlternativeConsequence, ...]
    risk_assessment_ids: tuple[PortfolioRiskAssessmentRef, ...]
    material_assumptions: tuple[str, ...]
    invalidation_conditions: tuple[str, ...]
    review_condition_refs: tuple[UUID, ...]
    proposed_action_refs: tuple[UUID, ...]
    actor_attribution: ActorAttribution
    formed_at: datetime

    @property
    def evidence_target(self) -> InvestmentRecommendationRef:
        return self.recommendation_id

    def __post_init__(self) -> None:
        if type(self.recommendation_id) is not InvestmentRecommendationRef:
            raise TypeError("recommendation identity must be typed")
        _common(self.decision_id, self.horizon, self.actor_attribution, self.formed_at)
        if type(self.disposition) is not EconomicDisposition:
            raise TypeError("preferred economic disposition must be closed")
        _typed_refs(self.view_ids, InvestmentViewRef, "views")
        _typed_refs(self.alternatives, DecisionAlternativeVersionRef, "alternatives")
        _typed_refs(self.material_evidence, EvidenceBindingId, "material Evidence")
        _typed_refs(self.challenge_ids, MeaningfulChallengeResultRef, "challenges")
        _typed_refs(self.risk_assessment_ids, PortfolioRiskAssessmentRef, "Risk")
        if (
            not self.view_ids
            or not self.challenge_ids
            or not self.alternatives
            or not self.risk_assessment_ids
        ):
            raise ValueError("View, challenge, and Alternatives are material")
        if type(self.source_state_id) is not PortfolioStateId:
            raise TypeError("actual Portfolio State identity must be typed")
        _require_consequences(self.alternatives, self.consequences)
        _require_texts_and_refs(self)


@dataclass(frozen=True, slots=True)
class RecommendationWithholdingJudgment:
    """A durable attempted formation with unresolved material support."""

    withholding_id: RecommendationWithholdingJudgmentRef
    decision_id: InvestmentDecisionId
    horizon: InvestmentHorizon
    explanation: str
    actor_attribution: ActorAttribution
    formed_at: datetime

    @property
    def evidence_target(self) -> RecommendationWithholdingJudgmentRef:
        return self.withholding_id

    def __post_init__(self) -> None:
        if type(self.withholding_id) is not RecommendationWithholdingJudgmentRef:
            raise TypeError("withholding identity must be typed")
        _common(self.decision_id, self.horizon, self.actor_attribution, self.formed_at)
        _substantive(self.explanation, "withholding explanation")
