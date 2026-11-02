"""Shared command and query boundary for Human Investment Decisions."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from polaris.domain.decisions import (
    DecisionVersion,
    InvestmentDecisionId,
    OperationId,
    TrustedHumanInvestmentDecisionBasis,
)
from polaris.domain.evidence import InvestmentAuthorityRegimeId
from polaris.domain.evidence.judgments import HumanInvestmentDecisionRef
from polaris.domain.governance_authority import InvestmentAuthorityRegime
from polaris.domain.governance_claim_catalog import GovernanceClaimCatalog
from polaris.domain.human_investment_decision import (
    HumanDecisionChoice,
    HumanInvestmentDecision,
    HumanInvestmentDecisionDraft,
    InvalidHumanInvestmentDecision,
    RecommendationRelationship,
    require_human_decision_authority,
)
from polaris.domain.investment_recommendation import InvestmentRecommendation

from .investment_recommendation import RecommendationEvent


class HumanDecisionStore(Protocol):
    async def human_decision_for_operation(
        self, operation_id: OperationId
    ) -> (
        tuple[HumanInvestmentDecision, DecisionVersion, GovernanceClaimCatalog] | None
    ): ...

    async def authority_regime(
        self, regime_id: InvestmentAuthorityRegimeId
    ) -> InvestmentAuthorityRegime | None: ...

    async def record_human_decision(
        self,
        operation_id: OperationId,
        decision: HumanInvestmentDecision,
        expected_decision_version: DecisionVersion,
        initial_claim_catalog: GovernanceClaimCatalog,
    ) -> HumanInvestmentDecision: ...

    async def human_decision(
        self, decision_ref: HumanInvestmentDecisionRef
    ) -> HumanInvestmentDecision | None: ...

    async def human_decision_history(
        self, decision_id: InvestmentDecisionId
    ) -> tuple[HumanInvestmentDecision, ...]: ...


class RecommendationReader(Protocol):
    async def recommendation_history(
        self, decision_id: InvestmentDecisionId
    ) -> tuple[RecommendationEvent, ...]: ...


class HumanInvestmentDecisionService:
    """Admit an attributable act only against stored power and owner Recommendations."""

    def __init__(
        self,
        store: HumanDecisionStore,
        recommendations: RecommendationReader,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._store = store
        self._recommendations = recommendations
        self._now = now

    async def record(
        self,
        operation_id: OperationId,
        draft: HumanInvestmentDecisionDraft,
        expected_decision_version: DecisionVersion,
        *,
        initial_claim_catalog: GovernanceClaimCatalog,
    ) -> HumanInvestmentDecision:
        if (
            type(operation_id) is not OperationId
            or type(draft) is not HumanInvestmentDecisionDraft
            or type(expected_decision_version) is not DecisionVersion
            or type(initial_claim_catalog) is not GovernanceClaimCatalog
        ):
            raise InvalidHumanInvestmentDecision("typed command inputs are required")
        prior = await self._store.human_decision_for_operation(operation_id)
        if prior is not None:
            fact, version, catalog = prior
            if (
                draft.at(fact.made_at) != fact
                or version != expected_decision_version
                or catalog != initial_claim_catalog
            ):
                raise InvalidHumanInvestmentDecision("operation ID has another request")
            return fact
        decision = draft.at(self._now())
        regime = await self._store.authority_regime(decision.authority_regime_id)
        require_human_decision_authority(regime, decision)
        history = await self._recommendations.recommendation_history(
            decision.investment_decision_id
        )
        by_id = {
            item.recommendation_id: item
            for item in history
            if type(item) is InvestmentRecommendation
        }
        for link in decision.recommendations:
            recommendation = by_id.get(link.recommendation_id)
            if recommendation is None:
                raise InvalidHumanInvestmentDecision(
                    "materially considered Recommendation is unavailable"
                )
            same_choice = decision.choice == recommendation.disposition
            if (
                link.relationship is RecommendationRelationship.ADOPTED
                and not same_choice
            ):
                raise InvalidHumanInvestmentDecision(
                    "adoption must select the Recommendation disposition"
                )
            if link.relationship is RecommendationRelationship.DIFFERED and same_choice:
                raise InvalidHumanInvestmentDecision(
                    "difference requires another disposition or Deferral"
                )
            if (
                decision.choice is HumanDecisionChoice.DEFERRAL
                and link.relationship
                in (
                    RecommendationRelationship.ADOPTED,
                    RecommendationRelationship.MODIFIED,
                )
            ):
                raise InvalidHumanInvestmentDecision(
                    "Deferral cannot adopt or modify an economic Recommendation"
                )
        return await self._store.record_human_decision(
            operation_id, decision, expected_decision_version, initial_claim_catalog
        )

    async def get(
        self, decision_ref: HumanInvestmentDecisionRef
    ) -> HumanInvestmentDecision | None:
        if type(decision_ref) is not HumanInvestmentDecisionRef:
            raise TypeError("Human Decision identity must be typed")
        return await self._store.human_decision(decision_ref)

    async def trusted_basis(
        self,
        decision_ref: HumanInvestmentDecisionRef,
        decision_id: InvestmentDecisionId,
    ) -> TrustedHumanInvestmentDecisionBasis | None:
        if type(decision_id) is not InvestmentDecisionId:
            raise TypeError("governing Decision identity must be typed")
        fact = await self.get(decision_ref)
        if fact is None:
            return None
        if fact.investment_decision_id != decision_id:
            raise InvalidHumanInvestmentDecision(
                "Human Decision belongs to another Decision"
            )
        return TrustedHumanInvestmentDecisionBasis(
            str(fact.decision_ref.value), fact.effect
        )

    async def history(
        self, decision_id: InvestmentDecisionId
    ) -> tuple[HumanInvestmentDecision, ...]:
        if type(decision_id) is not InvestmentDecisionId:
            raise TypeError("governing Decision identity must be typed")
        return await self._store.human_decision_history(decision_id)
