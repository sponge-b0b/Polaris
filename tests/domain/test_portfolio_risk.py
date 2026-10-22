from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from polaris.application.portfolio_risk import PortfolioRiskService
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.evidence.context_versions import (
    DecisionAlternativeId,
    DecisionAlternativeRevision,
    DecisionAlternativeVersionRef,
)
from polaris.domain.evidence.judgments import PortfolioRiskAssessmentRef
from polaris.domain.evidence.observations import EvidenceObservationId
from polaris.domain.portfolio import PortfolioStateId, RecordedPortfolioState
from polaris.domain.portfolio_consequences import ProjectedChange
from polaris.domain.portfolio_risk import (
    RecordedPortfolioRiskAssessment,
    RiskDimensionKind,
    RiskSupport,
    assess_portfolio_risk,
)
from tests.domain.test_portfolio_consequences import _consequence, _state

NOW = datetime(2026, 10, 19, tzinfo=UTC)
HORIZON = InvestmentHorizon("one quarter")
ACTOR = KnownActorAttribution(ActorId(uuid4()))
ALTERNATIVE = DecisionAlternativeVersionRef(
    DecisionAlternativeId(uuid4()), DecisionAlternativeRevision(1)
)


def _support(*, downside: Decimal | None = Decimal("0.2")) -> RiskSupport:
    return RiskSupport(
        basis="Scenario support from current market observation",
        evidence=(EvidenceObservationId(uuid4()),),
        material_dimensions=tuple(RiskDimensionKind),
        downside_fraction=downside,
        market_volatility_fraction=Decimal("0.15"),
        objective_shortfall_amount=Decimal("2000"),
        assumptions=("SPY exposure is held through the horizon",),
        uncertainty=("Market path remains uncertain",),
    )


def _assess(
    state: RecordedPortfolioState,
    *,
    consequence_change: ProjectedChange | None = None,
    support: RiskSupport | None = None,
):
    consequence = (
        None
        if consequence_change is None
        else _consequence(state, ALTERNATIVE, consequence_change)
    )
    return assess_portfolio_risk(
        assessment_id=PortfolioRiskAssessmentRef(uuid4()),
        state=state.state,
        consequence=consequence,
        horizon=HORIZON,
        scenario="SPY downside over one quarter",
        support=_support() if support is None else support,
        attribution=ACTOR,
        formed_at=NOW,
    )


def test_actual_and_projected_risk_are_typed_multidimensional_judgments() -> None:
    state = _state()
    actual = _assess(state)
    projected = _assess(state, consequence_change=ProjectedChange(Decimal("10000")))

    assert actual.projected_consequence_id is None
    assert projected.projected_consequence_id is not None
    assert actual.source_state_id == projected.source_state_id == state.state.state_id
    assert actual.horizon == projected.horizon == HORIZON
    assert {item.kind for item in actual.dimensions} == {
        RiskDimensionKind.EXPOSURE_CONCENTRATION,
        RiskDimensionKind.DOWNSIDE_SENSITIVITY,
        RiskDimensionKind.LIQUIDITY_BUFFER,
        RiskDimensionKind.MARKET_SENSITIVITY,
        RiskDimensionKind.OBJECTIVE_SHORTFALL,
    }
    assert actual.dimensions[0].value == Decimal("0.8")
    assert projected.dimensions[0].value == Decimal("0.9")
    assert actual.dimensions[1].value == Decimal("16000")
    assert projected.dimensions[1].value == Decimal("18000")
    assert all(
        type(item) is EvidenceObservationId for item in projected.support.evidence
    )
    assert projected.uncertainty[-1].startswith("Future SPY prices")
    assert not projected.unresolved
    with pytest.raises(ValueError, match="material typed Risk dimensions"):
        replace(actual, dimensions=())


def test_state_and_support_changes_affect_risk_without_fabricated_precision() -> None:
    state = _state()
    changed = RecordedPortfolioState(
        replace(
            state.state,
            state_id=PortfolioStateId(uuid4()),
            exposure_value=Decimal("50000"),
            cash=Decimal("50000"),
            allocation_fraction=Decimal("0.5"),
        ),
        state.known_at,
    )
    first = _assess(state, consequence_change=ProjectedChange(Decimal("10000")))
    other_state = _assess(changed, consequence_change=ProjectedChange(Decimal("10000")))
    weak_support = _assess(
        state,
        consequence_change=ProjectedChange(Decimal("10000")),
        support=_support(downside=None),
    )
    unresolved_projection = _assess(
        state,
        consequence_change=ProjectedChange(
            None, "projected SPY exposure cannot be established"
        ),
    )

    assert first.dimensions != other_state.dimensions
    assert first.dimensions[1].value == Decimal("18000")
    assert other_state.dimensions[1].value == Decimal("12000")
    assert weak_support.dimensions[1].value is None
    assert weak_support.dimensions[1].unresolved_reason is not None
    assert unresolved_projection.unresolved
    assert unresolved_projection.dimensions[0].value is None
    assert unresolved_projection.dimensions[2].value == Decimal("0.1")

    focused = _assess(
        state,
        support=replace(
            _support(),
            material_dimensions=(
                RiskDimensionKind.EXPOSURE_CONCENTRATION,
                RiskDimensionKind.DOWNSIDE_SENSITIVITY,
            ),
        ),
    )
    assert len(focused.dimensions) == 2

    missing_cash = replace(
        _consequence(state, ALTERNATIVE, ProjectedChange(Decimal("10000"))),
        cash_effect=None,
    )
    assessed_missing_cash = assess_portfolio_risk(
        assessment_id=PortfolioRiskAssessmentRef(uuid4()),
        state=state.state,
        consequence=missing_cash,
        horizon=HORIZON,
        scenario="SPY downside over one quarter",
        support=_support(),
        attribution=ACTOR,
        formed_at=NOW,
    )
    assert assessed_missing_cash.dimensions[2].value is None


def test_service_exposes_durable_typed_risk_and_rejects_wrong_source() -> None:
    async def scenario() -> None:
        state = _state()
        consequence = _consequence(
            state, ALTERNATIVE, ProjectedChange(Decimal("10000"))
        )

        class StateReader:
            async def get(self, state_id: PortfolioStateId):
                return state if state_id == state.state.state_id else None

        class ConsequenceReader:
            async def get(self, consequence_id):
                if consequence_id == consequence.consequence_id:
                    from polaris.domain.portfolio_consequences import (
                        RecordedProjectedPortfolioConsequence,
                    )

                    return RecordedProjectedPortfolioConsequence(consequence, NOW)
                return None

        class RiskStore:
            def __init__(self) -> None:
                self.recorded: RecordedPortfolioRiskAssessment | None = None

            async def append(self, assessment):
                self.recorded = RecordedPortfolioRiskAssessment(assessment, NOW)
                return self.recorded

            async def get(self, assessment_id):
                if (
                    self.recorded
                    and self.recorded.assessment.assessment_id == assessment_id
                ):
                    return self.recorded
                return None

        store = RiskStore()
        service = PortfolioRiskService(StateReader(), ConsequenceReader(), store)
        assessment_id = PortfolioRiskAssessmentRef(uuid4())
        # duplicate-code: the service-port proof supplies its own exact Risk
        # inputs independently of the pure producer's missing-cash falsifier.
        # arid: disable
        recorded = await service.assess(
            assessment_id=assessment_id,
            source_state_id=state.state.state_id,
            projected_consequence_id=consequence.consequence_id,
            horizon=HORIZON,
            scenario="SPY downside over one quarter",
            support=_support(),
            attribution=ACTOR,
            formed_at=NOW,
        )
        # arid: enable
        assert recorded.assessment.assessment_id == assessment_id
        assert await store.get(assessment_id) == recorded
        # duplicate-code: the negative source test keeps its exact call shape
        # independent of the successful producer proof above.
        # arid: disable
        with pytest.raises(ValueError, match="source Portfolio State"):
            await service.assess(
                assessment_id=PortfolioRiskAssessmentRef(uuid4()),
                source_state_id=PortfolioStateId(uuid4()),
                projected_consequence_id=consequence.consequence_id,
                horizon=HORIZON,
                scenario="SPY downside over one quarter",
                support=_support(),
                attribution=ACTOR,
                formed_at=NOW,
            )
        # arid: enable

    asyncio.run(scenario())
