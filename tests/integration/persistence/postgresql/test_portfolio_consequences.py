from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import DBAPIError

from polaris.application.decisions import (
    DecisionCommandEnvelope,
    DecisionInitiationService,
    InitiateDecisionCommand,
)
from polaris.application.investment_intelligence import InvestmentIntelligenceService
from polaris.application.portfolio_consequences import (
    PortfolioConsequenceConflict,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionScope,
    DecisionSubject,
    OperationId,
    TechnicalProvenance,
    TriggerKind,
    TriggerProvenance,
)
from polaris.domain.evidence.judgments import ProjectedPortfolioConsequenceRef
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    PostgresInvestmentIntelligenceStore,
    PostgresPortfolioConsequenceStore,
    PostgresPortfolioStateStore,
    create_postgres_portfolio_consequence_service,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    projected_portfolio_consequences,
)
from tests.domain.test_portfolio_consequences import (
    NOW,
    _alternatives,
    _consequences,
    _state,
)

from .conftest import PostgresTestTarget, postgres_row_counts, postgres_store


def test_owner_alternatives_produce_complete_immutable_consequences(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        source = _state()
        actor = KnownActorAttribution(ActorId(uuid4()))
        async with postgres_store(
            postgres_target, PostgresPortfolioConsequenceStore
        ) as (engine, consequence_store):
            state_store = PostgresPortfolioStateStore(engine)
            await state_store.append(source.state)
            decision_store = PostgresDecisionStore(engine)
            # duplicate-code: This consumer proof constructs its own governing
            # Decision; sharing the provider test's setup would couple two
            # independent integration falsifiers to one test implementation.
            # arid: disable
            result = await DecisionInitiationService(
                reader=decision_store,
                store=decision_store,
                now=lambda: NOW,
            ).initiate(
                InitiateDecisionCommand(
                    envelope=DecisionCommandEnvelope(
                        operation_id=OperationId(uuid4()),
                        actor_attribution=actor,
                        trigger=TriggerProvenance(
                            TriggerKind.HUMAN_REQUEST, "user-405"
                        ),
                        effective_at=NOW,
                        technical_provenance=TechnicalProvenance(),
                        expected_versions=frozenset(),
                    ),
                    need_statement="Choose SPY exposure for this Portfolio",
                    subject=DecisionSubject("Increase, hold, or reduce SPY exposure"),
                    scope=DecisionScope.established(source.state.portfolio_id),
                )
            )
            # arid: enable
            decision_state = await decision_store.load_decision_for_command(
                result.decision_id, known_at=NOW
            )
            assert decision_state is not None
            alternatives = _alternatives(source, result.decision_id)
            owner = PostgresInvestmentIntelligenceStore(engine)
            await InvestmentIntelligenceService(owner).record_alternatives(
                OperationId(uuid4()), decision_state.decision, alternatives
            )
            assert await owner.for_decision(result.decision_id) == tuple(
                sorted(alternatives, key=lambda item: item.alternative_id.value.hex)
            )
            consequences = _consequences(source, alternatives)
            service = create_postgres_portfolio_consequence_service(engine)
            with pytest.raises(ValueError, match="cover exact"):
                await service.produce(
                    decision_id=result.decision_id,
                    source_state_id=source.state.state_id,
                    consequences=consequences[:2],
                )
            committed = await service.produce(
                decision_id=result.decision_id,
                source_state_id=source.state.state_id,
                consequences=consequences,
            )
            assert tuple(item.consequence for item in committed) == consequences
            assert await postgres_row_counts(
                engine, projected_portfolio_consequences
            ) == (3,)
            await InvestmentIntelligenceService(owner).revise_alternative(
                OperationId(uuid4()),
                replace(
                    alternatives[0],
                    revision=2,
                    material_comparison="Updated material comparison",
                ),
                1,
            )
            with pytest.raises(PortfolioConsequenceConflict, match="stale"):
                await consequence_store.append_batch(
                    result.decision_id,
                    tuple(
                        replace(
                            item,
                            consequence_id=ProjectedPortfolioConsequenceRef(uuid4()),
                        )
                        for item in consequences
                    ),
                )
            async with engine.connect() as connection:
                stored_row = (
                    (
                        await connection.execute(
                            select(projected_portfolio_consequences).where(
                                projected_portfolio_consequences.c.consequence_id
                                == consequences[0].consequence_id.value
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
            mismatched = dict(stored_row)
            mismatched["consequence_id"] = uuid4()
            mismatched["source_as_of"] = source.state.as_of - timedelta(days=1)
            with pytest.raises(DBAPIError):
                async with engine.begin() as connection:
                    await connection.execute(
                        insert(projected_portfolio_consequences).values(**mismatched)
                    )
            assert await postgres_row_counts(
                engine, projected_portfolio_consequences
            ) == (3,)

        async with postgres_store(
            postgres_target, PostgresPortfolioConsequenceStore
        ) as (engine, restarted):
            assert await restarted.get(consequences[0].consequence_id) == committed[0]
            assert await restarted.get(consequences[1].consequence_id) == committed[1]
            with pytest.raises(PortfolioConsequenceConflict):
                await restarted.append_batch(result.decision_id, (consequences[0],))
            with pytest.raises(DBAPIError):
                async with engine.begin() as connection:
                    await connection.execute(
                        update(projected_portfolio_consequences)
                        .where(
                            projected_portfolio_consequences.c.consequence_id
                            == consequences[0].consequence_id.value
                        )
                        .values(uncertainty="later market movement")
                    )
            with pytest.raises(DBAPIError):
                async with engine.begin() as connection:
                    await connection.execute(
                        delete(projected_portfolio_consequences).where(
                            projected_portfolio_consequences.c.consequence_id
                            == consequences[0].consequence_id.value
                        )
                    )

    asyncio.run(scenario())
