from __future__ import annotations

import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import DBAPIError

from polaris.application.decisions import (
    DecisionCommandEnvelope,
    DecisionInitiationService,
    InitiateDecisionCommand,
)
from polaris.application.investment_intelligence import InvestmentIntelligenceService
from polaris.application.portfolio_risk import PortfolioRiskConflict
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.decisions import (
    DecisionScope,
    DecisionSubject,
    OperationId,
    TechnicalProvenance,
    TriggerKind,
    TriggerProvenance,
)
from polaris.domain.evidence.judgments import PortfolioRiskAssessmentRef
from polaris.domain.portfolio_judgment_history import (
    PendingDisposition,
    PortfolioClaimCatalog,
)
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    PostgresInvestmentIntelligenceStore,
    PostgresPortfolioConsequenceStore,
    PostgresPortfolioRiskStore,
    PostgresPortfolioStateStore,
    create_postgres_portfolio_consequence_service,
    create_postgres_portfolio_risk_service,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    portfolio_risk_assessments,
)
from tests.domain.test_portfolio_consequences import (
    NOW,
    _alternatives,
    _consequences,
    _state,
)
from tests.domain.test_portfolio_risk import _support

from ._portfolio_judgment_history_support import (
    initial_catalog_with_distinct_support,
    prove_durable_corrections,
)
from .conftest import PostgresTestTarget, postgres_row_counts, postgres_store


def test_risk_history_preserves_actual_and_projected_judgments_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        source = _state()
        actor = KnownActorAttribution(ActorId(uuid4()))
        async with postgres_store(postgres_target, PostgresPortfolioRiskStore) as (
            engine,
            store,
        ):
            state_store = PostgresPortfolioStateStore(engine)
            await state_store.append(source.state)
            decision_store = PostgresDecisionStore(engine)
            # duplicate-code: this Risk persistence falsifier constructs its own
            # Decision, Alternative, and consequence prerequisites; sharing the
            # consequence test's setup would couple their independent proofs.
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
                            TriggerKind.HUMAN_REQUEST, "portfolio-risk-test"
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
            decision_state = await decision_store.load_decision_for_command(
                result.decision_id, known_at=NOW
            )
            assert decision_state is not None
            alternatives = _alternatives(source, result.decision_id)
            owner = PostgresInvestmentIntelligenceStore(engine)
            await InvestmentIntelligenceService(owner).record_alternatives(
                OperationId(uuid4()), decision_state.decision, alternatives
            )
            consequences = _consequences(source, alternatives)
            committed = await create_postgres_portfolio_consequence_service(
                engine
            ).produce(
                decision_id=result.decision_id,
                source_state_id=source.state.state_id,
                consequences=consequences,
                initial_claim_catalogs={
                    item.consequence_id: PortfolioClaimCatalog(())
                    for item in consequences
                },
            )
            # arid: enable
            assert len(committed) == 3
            risk_service = create_postgres_portfolio_risk_service(engine)
            actual_id = PortfolioRiskAssessmentRef(uuid4())
            projected_id = PortfolioRiskAssessmentRef(uuid4())
            initial_catalog = initial_catalog_with_distinct_support(
                "Downside sensitivity", "Liquidity buffer"
            )
            actual = await risk_service.assess(
                assessment_id=actual_id,
                source_state_id=source.state.state_id,
                projected_consequence_id=None,
                horizon=InvestmentHorizon("one quarter"),
                scenario="SPY downside over one quarter",
                support=_support(),
                attribution=actor,
                formed_at=NOW,
                initial_claim_catalog=initial_catalog,
            )
            projected = await risk_service.assess(
                assessment_id=projected_id,
                source_state_id=source.state.state_id,
                projected_consequence_id=consequences[0].consequence_id,
                horizon=InvestmentHorizon("one quarter"),
                scenario="SPY downside over one quarter",
                support=_support(downside=None),
                attribution=actor,
                formed_at=NOW,
                initial_claim_catalog=PortfolioClaimCatalog(()),
            )
            assert actual.assessment.projected_consequence_id is None
            assert projected.assessment.projected_consequence_id == (
                consequences[0].consequence_id
            )
            assert projected.assessment.unresolved
            assert projected.assessment.dimensions[1].value is None
            assert projected.assessment.uncertainty[-1] == consequences[0].uncertainty
            await prove_durable_corrections(
                engine, actual.assessment, PendingDisposition.CANCEL, initial_catalog
            )
            await prove_durable_corrections(
                engine, projected.assessment, PendingDisposition.RETAIN
            )
            assert await postgres_row_counts(engine, portfolio_risk_assessments) == (2,)
            with pytest.raises(PortfolioRiskConflict):
                await store.append(
                    replace(actual.assessment, scenario="A later conflicting scenario"),
                    initial_catalog,
                )
            with pytest.raises(PortfolioRiskConflict, match="basis differs"):
                await store.append(
                    replace(
                        projected.assessment,
                        assessment_id=PortfolioRiskAssessmentRef(uuid4()),
                        horizon=InvestmentHorizon("one year"),
                    ),
                    PortfolioClaimCatalog(()),
                )
            with pytest.raises(DBAPIError):
                async with engine.begin() as connection:
                    await connection.execute(
                        update(portfolio_risk_assessments)
                        .where(
                            portfolio_risk_assessments.c.assessment_id
                            == actual_id.value
                        )
                        .values(scenario="rewritten")
                    )
            with pytest.raises(DBAPIError):
                async with engine.begin() as connection:
                    await connection.execute(
                        delete(portfolio_risk_assessments).where(
                            portfolio_risk_assessments.c.assessment_id
                            == projected_id.value
                        )
                    )

        async with postgres_store(postgres_target, PostgresPortfolioRiskStore) as (
            engine,
            restarted,
        ):
            assert await restarted.get(actual_id) == actual
            assert await restarted.get(projected_id) == projected
            retained_state = await PostgresPortfolioStateStore(engine).get(
                source.state.state_id
            )
            assert retained_state is not None
            assert retained_state.state == source.state
            assert (
                await PostgresPortfolioConsequenceStore(engine).get(
                    consequences[0].consequence_id
                )
            ) == committed[0]

    asyncio.run(scenario())
