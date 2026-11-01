"""Governance decision admission and restart reconstruction against PostgreSQL."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import DBAPIError

from polaris.application.decisions import (
    ApplySubstantiveResolutionCommand,
    DecisionCommandEnvelope,
    DecisionInitiationService,
    DecisionOrdinaryWorkService,
    ExpectedDecisionVersion,
    InitiateDecisionCommand,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionLifecycleDisposition,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    HumanInvestmentDecisionEffect,
    OperationId,
    TechnicalProvenance,
    TriggerKind,
    TriggerProvenance,
)
from polaris.domain.evidence import InvestmentAuthorityRegimeId
from polaris.domain.evidence.judgments import HumanInvestmentDecisionRef
from polaris.domain.governance_authority import (
    InvestmentAuthorityPower,
    InvestmentAuthorityRegime,
)
from polaris.domain.human_investment_decision import (
    HumanInvestmentDecisionDraft,
    InvalidHumanInvestmentDecision,
)
from polaris.domain.investment_intelligence import EconomicDisposition
from polaris.domain.portfolio import PortfolioId
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    PostgresGovernanceStore,
    create_postgres_engine,
    create_postgres_human_decision_service,
)
from polaris.infrastructure.persistence.postgresql.governance import (
    HumanDecisionConflict,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    human_investment_decisions,
)

from .conftest import PostgresTestTarget

AT = datetime(2026, 11, 1, 12, tzinfo=UTC)


async def _scenario(target: PostgresTestTarget) -> None:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    portfolio_id = PortfolioId(uuid4())
    actor = KnownActorAttribution(ActorId(uuid4()))
    try:
        decisions = PostgresDecisionStore(engine)
        # duplicate-code: This independent Governance persistence proof
        # initiates a real Decision; sharing the sibling test's setup would
        # make both proofs depend on one fixture's command construction.
        # arid: disable
        accepted = await DecisionInitiationService(
            reader=decisions, store=decisions, now=lambda: AT
        ).initiate(
            InitiateDecisionCommand(
                envelope=DecisionCommandEnvelope(
                    operation_id=OperationId(uuid4()),
                    actor_attribution=actor,
                    trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "human-479"),
                    effective_at=AT,
                    technical_provenance=TechnicalProvenance(),
                    expected_versions=frozenset(),
                ),
                need_statement="Choose SPY exposure",
                subject=DecisionSubject("Increase, hold, or reduce SPY"),
                scope=DecisionScope.established(portfolio_id),
            )
        )
        # arid: enable
        state = await decisions.load_decision_for_command(
            accepted.decision_id, known_at=AT
        )
        assert state is not None
        regime = InvestmentAuthorityRegime(
            InvestmentAuthorityRegimeId(uuid4()),
            actor.actor_id,
            portfolio_id,
            InvestmentAuthorityPower.HUMAN_INVESTMENT_DECISION,
            AT - timedelta(days=1),
            AT + timedelta(days=1),
        )
        store = PostgresGovernanceStore(engine)
        await store.install_regime(regime)
        service = create_postgres_human_decision_service(engine, now=lambda: AT)
        draft = HumanInvestmentDecisionDraft(
            decision_ref=HumanInvestmentDecisionRef(uuid4()),
            investment_decision_id=accepted.decision_id,
            portfolio_id=portfolio_id,
            actor=actor,
            choice=EconomicDisposition.HOLD,
            effect=HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
            authority_regime_id=regime.regime_id,
            material_rationale="Hold until the next decision horizon",
        )
        operation = OperationId(uuid4())
        fact = await service.record(operation, draft, state.decision.version)
        assert fact.made_at == AT
        assert await service.record(operation, draft, state.decision.version) == fact
        assert await service.get(fact.decision_ref) == fact
        with pytest.raises(InvalidHumanInvestmentDecision, match="another request"):
            await service.record(
                operation,
                replace(draft, material_rationale="Changed"),
                state.decision.version,
            )
        with pytest.raises(HumanDecisionConflict, match="version changed"):
            await service.record(
                OperationId(uuid4()),
                replace(draft, decision_ref=HumanInvestmentDecisionRef(uuid4())),
                DecisionVersion(999),
            )
        async with engine.connect() as connection:
            rows = (
                (await connection.execute(select(human_investment_decisions)))
                .mappings()
                .all()
            )
            assert len(rows) == 1
            assert rows[0]["choice"] == "hold"
            assert rows[0]["effect"] == "substantively_resolving"
        with pytest.raises(DBAPIError, match="immutable Governance fact"):
            async with engine.begin() as connection:
                await connection.execute(
                    update(human_investment_decisions)
                    .where(
                        human_investment_decisions.c.decision_ref
                        == fact.decision_ref.value
                    )
                    .values(material_rationale="rewritten")
                )
        basis = await service.trusted_basis(fact.decision_ref, accepted.decision_id)
        assert basis is not None
        with pytest.raises(InvalidHumanInvestmentDecision, match="another Decision"):
            await service.trusted_basis(
                fact.decision_ref, type(accepted.decision_id)(uuid4())
            )
        await DecisionOrdinaryWorkService(
            store=decisions, now=lambda: AT + timedelta(seconds=1)
        ).apply_substantive_resolution(
            ApplySubstantiveResolutionCommand(
                # duplicate-code: This Governance-to-Decisions proof owns a
                # distinct real lifecycle command with its own actor and basis.
                # arid: disable
                envelope=DecisionCommandEnvelope(
                    operation_id=OperationId(uuid4()),
                    actor_attribution=actor,
                    trigger=TriggerProvenance(
                        TriggerKind.HUMAN_REQUEST, "human-479-hold"
                    ),
                    effective_at=AT + timedelta(seconds=1),
                    technical_provenance=TechnicalProvenance(),
                    expected_versions=frozenset(
                        {
                            ExpectedDecisionVersion(
                                accepted.decision_id, state.decision.version
                            )
                        }
                    ),
                ),
                # arid: enable
                decision_id=accepted.decision_id,
                basis=basis,
            )
        )
        resolved = await decisions.load_decision_for_command(
            accepted.decision_id, known_at=AT + timedelta(seconds=1)
        )
        assert resolved is not None
        assert (
            resolved.decision.lifecycle_interpretation.disposition
            is DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
        )
        async with engine.connect() as connection:
            action_intent_tables = await connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = current_schema() "
                    "AND table_name LIKE '%action_intent%'"
                )
            )
        assert action_intent_tables == 0
    finally:
        await engine.dispose()

    # duplicate-code: Each owner has a separate restart reconstruction proof;
    # sharing this scaffold would couple their independent persistence checks.
    # arid: disable
    restarted = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        service = create_postgres_human_decision_service(restarted)
        assert await service.get(fact.decision_ref) == fact
        assert await service.history(accepted.decision_id) == (fact,)
    finally:
        await restarted.dispose()
    # arid: enable


def test_human_hold_is_durable_and_immutable(
    postgres_target: PostgresTestTarget,
) -> None:
    asyncio.run(_scenario(postgres_target))
