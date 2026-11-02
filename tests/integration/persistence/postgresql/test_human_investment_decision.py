"""Governance decision admission and restart reconstruction against PostgreSQL."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select, text, update
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
from polaris.domain.governance_judgment_history import (
    HumanDecisionTargetCorrectionDraft,
    HumanDecisionTargetEffect,
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
from polaris.infrastructure.persistence.postgresql.governance_history import (
    PostgresHumanDecisionTargetHistoryStore,
)
from polaris.infrastructure.persistence.postgresql.intelligence_contract_codec import (
    contract_value_payload,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    human_decision_act_publications,
    human_decision_target_corrections,
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
        target_store = PostgresHumanDecisionTargetHistoryStore(engine)
        target_history = await target_store.load(fact.decision_ref)
        assert target_history is not None
        initial = target_history.select(
            target_history.root_known_at, target_history.root_known_at
        )
        assert initial.version.revision.value == 1
        assert initial.assertion == fact
        corrected = replace(fact, material_rationale="Corrected recorded rationale")
        correction = HumanDecisionTargetCorrectionDraft(
            uuid4(),
            fact.decision_ref,
            fact.decision_ref,
            actor,
            "Correct the recorded rationale",
            AT,
            HumanDecisionTargetEffect.REVISE,
            corrected,
        )
        correction_operation = OperationId(uuid4())
        target_history = await target_store.append(correction_operation, correction)
        assert target_history.revisions[-1].value == 2
        assert (
            await target_store.append(correction_operation, correction)
            == target_history
        )
        current = target_history.select(
            target_history.corrections[-1].known_at,
            target_history.corrections[-1].known_at,
        )
        assert current.assertion == corrected
        assert (
            target_history.select(
                current.effective_at, target_history.root_known_at
            ).assertion
            == fact
        )
        assert await service.get(fact.decision_ref) == fact
        unarchived = HumanDecisionTargetCorrectionDraft(
            uuid4(),
            fact.decision_ref,
            correction.correction_id,
            actor,
            "Correct the correction's recorded rationale",
            AT,
            HumanDecisionTargetEffect.REVISE,
            replace(fact, material_rationale="Second corrected rationale"),
        )
        async with engine.begin() as connection:
            await connection.execute(
                insert(human_decision_target_corrections).values(
                    correction_id=unarchived.correction_id,
                    operation_id=uuid4(),
                    decision_ref=fact.decision_ref.value,
                    sequence=2,
                    effective_at=unarchived.effective_at,
                    draft=contract_value_payload(unarchived),
                )
            )
            before_commit = await connection.scalar(select(func.clock_timestamp()))
            assert isinstance(before_commit, datetime)
            await asyncio.sleep(0.03)
        async with engine.connect() as connection:
            # duplicate-code: This assertion proves an unarchived correction
            # is recovered from WAL, independently of the root publication.
            # arid: disable
            assert (
                await connection.scalar(
                    select(human_decision_act_publications.c.act_id).where(
                        human_decision_act_publications.c.act_id
                        == unarchived.correction_id
                    )
                )
                is None
            )
            # arid: enable
        target_history = await target_store.load(fact.decision_ref)
        assert target_history is not None
        committed_at = target_history.corrections[-1].known_at
        assert committed_at > before_commit
        assert target_history.select(committed_at, before_commit).assertion == corrected
        assert (
            target_history.select(committed_at, committed_at).assertion
            == unarchived.replacement
        )
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
            assert (
                await connection.scalar(
                    select(human_decision_act_publications.c.act_id).where(
                        human_decision_act_publications.c.act_id
                        == fact.decision_ref.value
                    )
                )
                == fact.decision_ref.value
            )
            correction_ids = set(
                (
                    await connection.execute(
                        select(human_decision_target_corrections.c.correction_id)
                    )
                ).scalars()
            )
            assert correction_ids == {
                correction.correction_id,
                unarchived.correction_id,
            }
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
        target_history_after_restart = await PostgresHumanDecisionTargetHistoryStore(
            restarted
        ).load(fact.decision_ref)
        assert target_history_after_restart == target_history
    finally:
        await restarted.dispose()
    # arid: enable


def test_human_hold_is_durable_and_immutable(
    postgres_target: PostgresTestTarget,
) -> None:
    asyncio.run(_scenario(postgres_target))
