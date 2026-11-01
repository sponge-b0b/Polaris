"""Governance-owned, authority-bearing Human Investment Decision facts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from polaris.domain.actors import KnownActorAttribution
from polaris.domain.decisions import HumanInvestmentDecisionEffect, InvestmentDecisionId
from polaris.domain.evidence import InvestmentAuthorityRegimeId
from polaris.domain.evidence.judgments import (
    HumanInvestmentDecisionRef,
    InvestmentRecommendationRef,
)
from polaris.domain.investment_intelligence import EconomicDisposition
from polaris.domain.portfolio import PortfolioId

from .governance_authority import (
    InvestmentAuthorityCheck,
    InvestmentAuthorityPower,
    InvestmentAuthorityRegime,
    check_investment_authority,
)


class InvalidHumanInvestmentDecision(ValueError):
    """A proposed Human Investment Decision is not a canonical authority act."""


class HumanDecisionChoice(StrEnum):
    DEFERRAL = "deferral"


class RecommendationRelationship(StrEnum):
    CONSIDERED = "considered"
    ADOPTED = "adopted"
    MODIFIED = "modified"
    REJECTED = "rejected"
    DIFFERED = "differed"


@dataclass(frozen=True, slots=True)
class ConsideredRecommendation:
    recommendation_id: InvestmentRecommendationRef
    relationship: RecommendationRelationship

    def __post_init__(self) -> None:
        if type(self.recommendation_id) is not InvestmentRecommendationRef:
            raise InvalidHumanInvestmentDecision(
                "Recommendation identity must be typed"
            )
        if type(self.relationship) is not RecommendationRelationship:
            raise InvalidHumanInvestmentDecision(
                "Recommendation relationship is invalid"
            )


def _validate_choice(
    choice: EconomicDisposition | HumanDecisionChoice,
    effect: HumanInvestmentDecisionEffect,
) -> None:
    if type(choice) not in (EconomicDisposition, HumanDecisionChoice):
        raise InvalidHumanInvestmentDecision("economic choice or Deferral is required")
    if (choice is HumanDecisionChoice.DEFERRAL) != (
        effect is HumanInvestmentDecisionEffect.DEFERRING
    ):
        raise InvalidHumanInvestmentDecision("Deferral and resolution effect disagree")


def _validate_recommendations(
    links: tuple[ConsideredRecommendation, ...],
) -> None:
    if type(links) is not tuple or any(
        type(item) is not ConsideredRecommendation for item in links
    ):
        raise InvalidHumanInvestmentDecision("Recommendation links must be typed")
    if len({item.recommendation_id for item in links}) != len(links):
        raise InvalidHumanInvestmentDecision("Recommendation links must be distinct")


@dataclass(frozen=True, slots=True)
class HumanInvestmentDecision:
    """One independently identified human act; the Decisions consequence is separate."""

    decision_ref: HumanInvestmentDecisionRef
    investment_decision_id: InvestmentDecisionId
    portfolio_id: PortfolioId
    actor: KnownActorAttribution
    made_at: datetime
    choice: EconomicDisposition | HumanDecisionChoice
    effect: HumanInvestmentDecisionEffect
    authority_regime_id: InvestmentAuthorityRegimeId
    recommendations: tuple[ConsideredRecommendation, ...] = ()
    material_rationale: str | None = None

    def __post_init__(self) -> None:
        if type(self.decision_ref) is not HumanInvestmentDecisionRef:
            raise InvalidHumanInvestmentDecision(
                "Human Decision identity must be typed"
            )
        if type(self.investment_decision_id) is not InvestmentDecisionId:
            raise InvalidHumanInvestmentDecision(
                "governing Decision identity must be typed"
            )
        if type(self.portfolio_id) is not PortfolioId:
            raise InvalidHumanInvestmentDecision("one Portfolio scope is required")
        if type(self.actor) is not KnownActorAttribution:
            raise InvalidHumanInvestmentDecision(
                "an attributable human actor is required"
            )
        if not isinstance(self.made_at, datetime) or self.made_at.utcoffset() is None:
            raise InvalidHumanInvestmentDecision("act time must be timezone-aware")
        if type(self.effect) is not HumanInvestmentDecisionEffect:
            raise InvalidHumanInvestmentDecision("resolution effect must be explicit")
        if type(self.authority_regime_id) is not InvestmentAuthorityRegimeId:
            raise InvalidHumanInvestmentDecision(
                "authority regime identity must be typed"
            )
        _validate_choice(self.choice, self.effect)
        _validate_recommendations(self.recommendations)
        if self.material_rationale is not None:
            if (
                not isinstance(self.material_rationale, str)
                or not self.material_rationale.strip()
            ):
                raise InvalidHumanInvestmentDecision(
                    "material rationale must be substantive"
                )
            object.__setattr__(
                self, "material_rationale", self.material_rationale.strip()
            )


@dataclass(frozen=True, slots=True)
class HumanInvestmentDecisionDraft:
    """Caller-selected content before Application captures the trusted act time."""

    # duplicate-code: The command draft excludes act time while the durable
    # fact includes it; sharing their dataclass identity would allow callers
    # to supply the authority-effective time.
    # arid: disable
    decision_ref: HumanInvestmentDecisionRef
    investment_decision_id: InvestmentDecisionId
    portfolio_id: PortfolioId
    actor: KnownActorAttribution
    choice: EconomicDisposition | HumanDecisionChoice
    effect: HumanInvestmentDecisionEffect
    authority_regime_id: InvestmentAuthorityRegimeId
    recommendations: tuple[ConsideredRecommendation, ...] = ()
    material_rationale: str | None = None
    # arid: enable

    def at(self, made_at: datetime) -> HumanInvestmentDecision:
        return HumanInvestmentDecision(
            self.decision_ref,
            self.investment_decision_id,
            self.portfolio_id,
            self.actor,
            made_at,
            self.choice,
            self.effect,
            self.authority_regime_id,
            self.recommendations,
            self.material_rationale,
        )


def require_human_decision_authority(
    regime: InvestmentAuthorityRegime | None, decision: HumanInvestmentDecision
) -> None:
    """Fail closed on any missing or mismatched power, actor, scope, or act time."""
    if (
        check_investment_authority(
            regime,
            decision.actor,
            decision.portfolio_id,
            InvestmentAuthorityPower.HUMAN_INVESTMENT_DECISION,
            decision.made_at,
        )
        is not InvestmentAuthorityCheck.ESTABLISHED
    ):
        raise InvalidHumanInvestmentDecision("human decision power is unestablished")
