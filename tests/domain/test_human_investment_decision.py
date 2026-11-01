from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from polaris.application.human_investment_decision import HumanInvestmentDecisionService
from polaris.domain.actors import (
    ActorId,
    KnownActorAttribution,
    UnknownActorAttribution,
)
from polaris.domain.decisions import (
    DecisionVersion,
    HumanInvestmentDecisionEffect,
    InvestmentDecisionId,
    OperationId,
)
from polaris.domain.evidence import InvestmentAuthorityRegimeId
from polaris.domain.evidence.judgments import HumanInvestmentDecisionRef
from polaris.domain.governance_authority import (
    InvestmentAuthorityPower,
    InvestmentAuthorityRegime,
)
from polaris.domain.human_investment_decision import (
    ConsideredRecommendation,
    HumanDecisionChoice,
    HumanInvestmentDecision,
    HumanInvestmentDecisionDraft,
    InvalidHumanInvestmentDecision,
    RecommendationRelationship,
)
from polaris.domain.investment_intelligence import EconomicDisposition
from polaris.domain.portfolio import PortfolioId
from tests.domain.test_investment_recommendation import _recommendation

AT = datetime(2026, 11, 1, tzinfo=UTC)
RESOLVES = HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING


def _fact(
    *,
    choice: EconomicDisposition | HumanDecisionChoice = EconomicDisposition.HOLD,
    effect: HumanInvestmentDecisionEffect = RESOLVES,
) -> HumanInvestmentDecision:
    return HumanInvestmentDecision(
        HumanInvestmentDecisionRef(uuid4()),
        InvestmentDecisionId(uuid4()),
        PortfolioId(uuid4()),
        KnownActorAttribution(ActorId(uuid4())),
        AT,
        choice,
        effect,
        InvestmentAuthorityRegimeId(uuid4()),
        material_rationale="No change is warranted now",
    )


def _draft(fact: HumanInvestmentDecision) -> HumanInvestmentDecisionDraft:
    return HumanInvestmentDecisionDraft(
        fact.decision_ref,
        fact.investment_decision_id,
        fact.portfolio_id,
        fact.actor,
        fact.choice,
        fact.effect,
        fact.authority_regime_id,
        fact.recommendations,
        fact.material_rationale,
    )


def test_hold_resolution_and_deferral_are_distinct_authority_facts() -> None:
    hold = _fact()
    deferred = _fact(
        choice=HumanDecisionChoice.DEFERRAL,
        effect=HumanInvestmentDecisionEffect.DEFERRING,
    )
    assert hold.choice is EconomicDisposition.HOLD
    assert hold.effect is HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING
    assert hold.recommendations == ()
    assert deferred.choice is HumanDecisionChoice.DEFERRAL
    assert deferred.effect is HumanInvestmentDecisionEffect.DEFERRING
    with pytest.raises(InvalidHumanInvestmentDecision, match="disagree"):
        replace(hold, effect=HumanInvestmentDecisionEffect.DEFERRING)
    with pytest.raises(InvalidHumanInvestmentDecision, match="attributable"):
        replace(hold, actor=UnknownActorAttribution())  # type: ignore[arg-type]


class _Store:
    def __init__(self, regime: InvestmentAuthorityRegime) -> None:
        self.regime = regime
        self.recorded: list[HumanInvestmentDecision] = []
        self.operations: dict[
            OperationId, tuple[HumanInvestmentDecision, DecisionVersion]
        ] = {}

    async def human_decision_for_operation(self, operation_id):
        return self.operations.get(operation_id)

    async def authority_regime(self, regime_id):
        return self.regime if regime_id == self.regime.regime_id else None

    async def record_human_decision(
        self, operation_id, decision, expected_decision_version
    ):
        self.recorded.append(decision)
        self.operations[operation_id] = decision, expected_decision_version
        return decision

    async def human_decision(self, decision_ref):
        return next(
            (item for item in self.recorded if item.decision_ref == decision_ref), None
        )

    async def human_decision_history(self, decision_id):
        return tuple(
            item for item in self.recorded if item.investment_decision_id == decision_id
        )


class _Recommendations:
    def __init__(self, history) -> None:
        self.history = history

    async def recommendation_history(self, decision_id):
        return self.history


def test_reject_and_differ_preserve_recommendation_and_do_not_set_effect() -> None:
    async def scenario() -> None:
        base = _fact(choice=EconomicDisposition.REDUCE)
        recommendation = _recommendation(
            base.investment_decision_id, EconomicDisposition.INCREASE
        )
        reader = _Recommendations((recommendation,))
        regime = InvestmentAuthorityRegime(
            base.authority_regime_id,
            base.actor.actor_id,
            base.portfolio_id,
            InvestmentAuthorityPower.HUMAN_INVESTMENT_DECISION,
            AT - timedelta(days=1),
            AT + timedelta(days=1),
        )
        store = _Store(regime)
        service = HumanInvestmentDecisionService(store, reader, now=lambda: AT)
        rejected = replace(
            base,
            recommendations=(
                ConsideredRecommendation(
                    recommendation.recommendation_id,
                    RecommendationRelationship.REJECTED,
                ),
            ),
        )
        differed = replace(
            base,
            decision_ref=HumanInvestmentDecisionRef(uuid4()),
            recommendations=(
                ConsideredRecommendation(
                    recommendation.recommendation_id,
                    RecommendationRelationship.DIFFERED,
                ),
            ),
        )
        assert (
            await service.record(
                OperationId(uuid4()), _draft(rejected), DecisionVersion(1)
            )
            == rejected
        )
        assert (
            await service.record(
                OperationId(uuid4()), _draft(differed), DecisionVersion(1)
            )
            == differed
        )
        assert reader.history == (recommendation,)
        assert recommendation.disposition is EconomicDisposition.INCREASE
        assert rejected.effect is differed.effect
        deferred_rejection = replace(
            rejected,
            decision_ref=HumanInvestmentDecisionRef(uuid4()),
            choice=HumanDecisionChoice.DEFERRAL,
            effect=HumanInvestmentDecisionEffect.DEFERRING,
        )
        assert (
            await service.record(
                OperationId(uuid4()), _draft(deferred_rejection), DecisionVersion(1)
            )
            == deferred_rejection
        )
        assert deferred_rejection.effect is HumanInvestmentDecisionEffect.DEFERRING

    asyncio.run(scenario())


def test_missing_authority_or_recommendation_fails_closed() -> None:
    async def scenario() -> None:
        fact = _fact()
        regime = InvestmentAuthorityRegime(
            fact.authority_regime_id,
            ActorId(uuid4()),
            fact.portfolio_id,
            InvestmentAuthorityPower.HUMAN_INVESTMENT_DECISION,
            AT - timedelta(days=1),
            None,
        )
        store = _Store(regime)
        reader = _Recommendations(())
        service = HumanInvestmentDecisionService(store, reader, now=lambda: AT)
        with pytest.raises(InvalidHumanInvestmentDecision, match="unestablished"):
            await service.record(OperationId(uuid4()), _draft(fact), DecisionVersion(1))
        store.regime = replace(regime, actor_id=fact.actor.actor_id)
        linked = replace(
            fact,
            recommendations=(
                ConsideredRecommendation(
                    _recommendation(
                        fact.investment_decision_id, EconomicDisposition.HOLD
                    ).recommendation_id,
                    RecommendationRelationship.CONSIDERED,
                ),
            ),
        )
        with pytest.raises(InvalidHumanInvestmentDecision, match="unavailable"):
            await service.record(
                OperationId(uuid4()), _draft(linked), DecisionVersion(1)
            )
        assert store.recorded == []

    # duplicate-code: Each independent authority test builds its own
    # regime and command boundary; sharing setup would couple the falsifiers.
    # arid: disable
    asyncio.run(scenario())


def test_act_time_is_captured_by_application_and_replay_preserves_it() -> None:
    async def scenario() -> None:
        fact = _fact()
        regime = InvestmentAuthorityRegime(
            fact.authority_regime_id,
            fact.actor.actor_id,
            fact.portfolio_id,
            InvestmentAuthorityPower.HUMAN_INVESTMENT_DECISION,
            AT - timedelta(days=1),
            AT + timedelta(hours=1),
        )
        # arid: enable
        store = _Store(regime)
        clock = [AT]
        service = HumanInvestmentDecisionService(
            store, _Recommendations(()), now=lambda: clock[0]
        )
        operation = OperationId(uuid4())
        draft = _draft(fact)
        assert await service.record(operation, draft, DecisionVersion(1)) == fact
        clock[0] = AT + timedelta(days=2)
        assert await service.record(operation, draft, DecisionVersion(1)) == fact
        with pytest.raises(InvalidHumanInvestmentDecision, match="unestablished"):
            await service.record(OperationId(uuid4()), draft, DecisionVersion(1))
        assert store.recorded == [fact]

    asyncio.run(scenario())


def test_adoption_modification_and_rationale_keep_recommendation_identity() -> None:
    # duplicate-code: Independent relationship cases need their own real
    # command setup; sharing a scenario fixture would couple their outcomes.
    # arid: disable
    async def scenario() -> None:
        base = _fact(choice=EconomicDisposition.HOLD)
        recommendation = _recommendation(
            base.investment_decision_id, EconomicDisposition.HOLD
        )
        regime = InvestmentAuthorityRegime(
            base.authority_regime_id,
            base.actor.actor_id,
            base.portfolio_id,
            InvestmentAuthorityPower.HUMAN_INVESTMENT_DECISION,
            AT - timedelta(days=1),
            None,
        )
        store = _Store(regime)
        service = HumanInvestmentDecisionService(
            store, _Recommendations((recommendation,)), now=lambda: AT
        )
        adopted = replace(
            base,
            recommendations=(
                ConsideredRecommendation(
                    recommendation.recommendation_id,
                    RecommendationRelationship.ADOPTED,
                ),
            ),
            material_rationale="  Holding is prudent  ",
        )
        # arid: enable
        assert adopted.material_rationale == "Holding is prudent"
        assert (
            await service.record(
                OperationId(uuid4()), _draft(adopted), DecisionVersion(1)
            )
            == adopted
        )
        changed = replace(
            adopted,
            decision_ref=HumanInvestmentDecisionRef(uuid4()),
            choice=EconomicDisposition.REDUCE,
            recommendations=(
                ConsideredRecommendation(
                    recommendation.recommendation_id,
                    RecommendationRelationship.MODIFIED,
                ),
            ),
        )
        assert (
            await service.record(
                OperationId(uuid4()), _draft(changed), DecisionVersion(1)
            )
            == changed
        )
        with pytest.raises(InvalidHumanInvestmentDecision, match="adoption"):
            await service.record(
                OperationId(uuid4()),
                _draft(
                    replace(
                        adopted,
                        decision_ref=HumanInvestmentDecisionRef(uuid4()),
                        choice=EconomicDisposition.REDUCE,
                    )
                ),
                DecisionVersion(1),
            )
        assert recommendation.disposition is EconomicDisposition.HOLD
        assert len(store.recorded) == 2

    asyncio.run(scenario())
