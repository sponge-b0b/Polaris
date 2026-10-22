from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from polaris.application.investment_intelligence import FIRST_R3_SPY_INSTRUMENT_ID
from polaris.application.portfolio_consequences import PortfolioConsequenceService
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.decisions.facts import InvestmentDecisionId
from polaris.domain.evidence.context_versions import (
    DecisionAlternativeId,
    DecisionAlternativeRevision,
    DecisionAlternativeVersionRef,
)
from polaris.domain.evidence.judgments import ProjectedPortfolioConsequenceRef
from polaris.domain.investment_intelligence import (
    DecisionAlternative,
    EconomicDisposition,
)
from polaris.domain.investment_intelligence import (
    DecisionAlternativeId as OwnerAlternativeId,
)
from polaris.domain.portfolio import (
    PortfolioId,
    PortfolioSource,
    PortfolioState,
    PortfolioStateId,
    RecordedPortfolioState,
)
from polaris.domain.portfolio_consequences import (
    ProjectedChange,
    ProjectedPortfolioConsequence,
    RecordedProjectedPortfolioConsequence,
)
from polaris.domain.portfolio_judgment_history import PortfolioClaimCatalog

NOW = datetime(2026, 10, 19, tzinfo=UTC)


def _state() -> RecordedPortfolioState:
    state = PortfolioState(
        state_id=PortfolioStateId(uuid4()),
        portfolio_id=PortfolioId(uuid4()),
        as_of=NOW,
        source=PortfolioSource("custodian", "snapshot-1", NOW),
        currency="USD",
        capital_basis=Decimal("100000"),
        cash=Decimal("20000"),
        instrument_id=FIRST_R3_SPY_INSTRUMENT_ID,
        position_quantity=Decimal("100"),
        position_value=Decimal("80000"),
        exposure_value=Decimal("80000"),
        allocation_fraction=Decimal("0.8"),
        interpretation_basis="Custodian positions interpreted for this Decision",
    )
    return RecordedPortfolioState(state, NOW)


def _consequence(
    state: RecordedPortfolioState,
    alternative: DecisionAlternativeVersionRef,
    exposure_change: ProjectedChange,
) -> ProjectedPortfolioConsequence:
    return ProjectedPortfolioConsequence(
        consequence_id=ProjectedPortfolioConsequenceRef(uuid4()),
        alternative=alternative,
        source_state_id=state.state.state_id,
        source_as_of=state.state.as_of,
        horizon=InvestmentHorizon("one quarter"),
        scenario="Flat market with one SPY rebalance",
        assumptions=("Position price stays at the observation level",),
        exposure_change=exposure_change,
        allocation_change=None,
        cash_effect=ProjectedChange(Decimal("-10000")),
        economic_benefits=("Additional expected participation in SPY upside",),
        adverse_possibilities=("Higher loss if SPY falls",),
        material_risk_changes=("SPY concentration rises",),
        attribution=KnownActorAttribution(ActorId(uuid4())),
        formed_at=NOW,
        uncertainty="Future SPY prices and returns remain uncertain",
    )


def _alternatives(
    state: RecordedPortfolioState, decision_id: InvestmentDecisionId
) -> tuple[DecisionAlternative, ...]:
    return tuple(
        DecisionAlternative(
            alternative_id=OwnerAlternativeId(uuid4()),
            decision_id=decision_id,
            instrument_id=state.state.instrument_id,
            horizon=InvestmentHorizon("one quarter"),
            disposition=disposition,
            material_comparison=f"Material {disposition.value} comparison",
            actor_attribution=KnownActorAttribution(ActorId(uuid4())),
            formed_at=NOW,
        )
        for disposition in EconomicDisposition
    )


def _reference(alternative: DecisionAlternative) -> DecisionAlternativeVersionRef:
    return DecisionAlternativeVersionRef(
        DecisionAlternativeId(alternative.alternative_id.value),
        DecisionAlternativeRevision(alternative.revision),
    )


def _consequences(
    state: RecordedPortfolioState,
    alternatives: tuple[DecisionAlternative, ...],
) -> tuple[ProjectedPortfolioConsequence, ...]:
    return tuple(
        _consequence(
            state,
            _reference(alternative),
            ProjectedChange(Decimal("0") if index == 1 else Decimal("10000")),
        )
        for index, alternative in enumerate(alternatives)
    )


def test_hypothetical_consequence_keeps_alternative_and_unresolved_delta() -> None:
    source = _state()
    alternative = _reference(_alternatives(source, InvestmentDecisionId(uuid4()))[0])
    consequence = _consequence(
        source, alternative, ProjectedChange(None, "Exposure cannot be quantified")
    )
    assert consequence.alternative == alternative
    assert consequence.source_state_id == source.state.state_id
    assert consequence.source_as_of == source.state.as_of
    assert consequence.exposure_change.value is None
    assert consequence.exposure_change.unresolved_reason is not None
    with pytest.raises(ValueError, match="finite"):
        ProjectedChange(Decimal("NaN"))
    with pytest.raises(ValueError, match="value or unresolved"):
        ProjectedChange(None)
    with pytest.raises(ValueError, match="SPY exposure or allocation"):
        replace(consequence, exposure_change=None)


def test_producer_refuses_partial_alternative_set_or_wrong_state() -> None:
    source = _state()
    decision = InvestmentDecisionId(uuid4())
    alternatives = _alternatives(source, decision)
    consequences = _consequences(source, alternatives)
    catalogs = {item.consequence_id: PortfolioClaimCatalog(()) for item in consequences}

    class StateStore:
        async def get(
            self, state_id: PortfolioStateId
        ) -> RecordedPortfolioState | None:
            return source if state_id == source.state.state_id else None

    class ConsequenceStore:
        calls = 0

        async def append_batch(
            self,
            decision_id: InvestmentDecisionId,
            consequences: tuple[ProjectedPortfolioConsequence, ...],
            initial_claim_catalogs: Mapping[
                ProjectedPortfolioConsequenceRef, PortfolioClaimCatalog
            ],
        ) -> tuple[RecordedProjectedPortfolioConsequence, ...]:
            assert decision_id == decision
            assert initial_claim_catalogs == catalogs
            self.calls += 1
            return tuple(
                RecordedProjectedPortfolioConsequence(item, NOW)
                for item in consequences
            )

    class AlternativeReader:
        alternatives: tuple[DecisionAlternative, ...] = ()

        async def for_decision(
            self, decision_id: InvestmentDecisionId
        ) -> tuple[DecisionAlternative, ...]:
            assert decision_id == decision
            return self.alternatives

    async def scenario() -> None:
        reader = AlternativeReader()
        reader.alternatives = alternatives
        store = ConsequenceStore()
        service = PortfolioConsequenceService(StateStore(), store, reader)

        async def produce(
            initial_claim_catalogs: Mapping[
                ProjectedPortfolioConsequenceRef, PortfolioClaimCatalog
            ],
        ) -> tuple[RecordedProjectedPortfolioConsequence, ...]:
            return await service.produce(
                decision_id=decision,
                source_state_id=source.state.state_id,
                consequences=consequences,
                initial_claim_catalogs=initial_claim_catalogs,
            )

        with pytest.raises(ValueError, match="cover exact"):
            await service.produce(
                decision_id=decision,
                source_state_id=source.state.state_id,
                consequences=consequences[:2],
                initial_claim_catalogs=catalogs,
            )
        with pytest.raises(ValueError, match="source State, as-of"):
            await service.produce(
                decision_id=decision,
                source_state_id=source.state.state_id,
                consequences=(
                    consequences[0],
                    replace(
                        consequences[1],
                        source_as_of=datetime(2026, 10, 18, tzinfo=UTC),
                    ),
                    consequences[2],
                ),
                initial_claim_catalogs=catalogs,
            )
        assert store.calls == 0
        reader.alternatives = ()
        with pytest.raises(ValueError, match="material alternatives"):
            await produce(catalogs)
        reader.alternatives = alternatives
        invalid_catalogs = (
            {consequences[0].consequence_id: catalogs[consequences[0].consequence_id]},
            {
                **catalogs,
                ProjectedPortfolioConsequenceRef(uuid4()): PortfolioClaimCatalog(()),
            },
        )
        for invalid_catalog in invalid_catalogs:
            with pytest.raises(ValueError, match="complete initial claim catalog"):
                await produce(invalid_catalog)
        result = await produce(catalogs)
        assert tuple(item.consequence.alternative for item in result) == tuple(
            _reference(item) for item in alternatives
        )
        assert store.calls == 1

    asyncio.run(scenario())
