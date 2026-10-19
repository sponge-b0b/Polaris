from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from polaris.application.decisions import (
    DecisionCommandEnvelope,
    DecisionInitiationService,
    InitiateDecisionCommand,
)
from polaris.application.investment_intelligence import (
    FIRST_R3_SPY_INSTRUMENT_ID,
    InvestmentIntelligenceService,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.decisions import (
    DecisionScope,
    DecisionSubject,
    InvestmentDecisionId,
    OperationId,
    TechnicalProvenance,
    TriggerKind,
    TriggerProvenance,
)
from polaris.domain.evidence import EvidenceBindingId
from polaris.domain.evidence.judgments import (
    InvestmentHypothesisRef,
    InvestmentViewRef,
)
from polaris.domain.evidence.judgments import (
    MeaningfulChallengeResultRef as ChallengeResultRef,
)
from polaris.domain.investment_intelligence import (
    ChallengeDisposition,
    DecisionAlternative,
    DecisionAlternativeId,
    EconomicDisposition,
    InvalidInvestmentJudgment,
    InvestmentHypothesis,
    InvestmentView,
    MeaningfulChallengeResult,
    R3InvestmentSlice,
)
from polaris.domain.portfolio import FinancialInstrumentId, PortfolioId
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    PostgresInvestmentIntelligenceStore,
    create_postgres_engine,
)
from polaris.infrastructure.persistence.postgresql.investment_intelligence import (
    JudgmentConcurrencyConflict,
    JudgmentIdempotencyConflict,
)

from .conftest import PostgresTestTarget

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


async def _exercise(target: PostgresTestTarget) -> None:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        decision_store = PostgresDecisionStore(engine)
        judgment_store = PostgresInvestmentIntelligenceStore(engine)
        actor = KnownActorAttribution(ActorId(uuid4()))
        portfolio_id = PortfolioId(uuid4())
        instrument_id = FIRST_R3_SPY_INSTRUMENT_ID
        decision_result = await DecisionInitiationService(
            reader=decision_store,
            store=decision_store,
            now=lambda: NOW,
        ).initiate(
            InitiateDecisionCommand(
                envelope=DecisionCommandEnvelope(
                    operation_id=OperationId(uuid4()),
                    actor_attribution=actor,
                    trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "user-398"),
                    effective_at=NOW,
                    technical_provenance=TechnicalProvenance(),
                    expected_versions=frozenset(),
                ),
                need_statement="Choose SPY exposure for this Portfolio",
                subject=DecisionSubject("Increase, hold, or reduce SPY exposure"),
                scope=DecisionScope.established(portfolio_id),
            )
        )
        assert isinstance(decision_result.decision_id, InvestmentDecisionId)
        decision_state = await decision_store.load_decision_for_command(
            decision_result.decision_id, known_at=NOW
        )
        assert decision_state is not None
        decision = decision_state.decision
        service = InvestmentIntelligenceService(judgment_store)
        hypothesis_id = InvestmentHypothesisRef(uuid4())
        view = InvestmentView(
            InvestmentViewRef(uuid4()),
            decision.decision_id,
            R3InvestmentSlice(
                portfolio_id, instrument_id, InvestmentHorizon("three months")
            ),
            "A moderate SPY increase may be justified",
            actor,
            NOW,
            (EvidenceBindingId(uuid4()),),
            ("cash remains adequate",),
            "returns remain uncertain",
            "holding cash may be preferable",
            ("liquidity deteriorates",),
            ("market trend observation",),
            (hypothesis_id,),
        )
        hypothesis = InvestmentHypothesis(
            hypothesis_id,
            decision.decision_id,
            "Liquidity can support the increase",
            view.view_id,
            actor,
            NOW,
        )
        view_operation = OperationId(uuid4())
        receipt = await service.record_view(
            view_operation, decision, view, (hypothesis,)
        )
        assert (
            await service.record_view(view_operation, decision, view, (hypothesis,))
            == receipt
        )
        assert await judgment_store.load_view(view.view_id) == view
        assert await judgment_store.load_hypothesis(hypothesis_id) == hypothesis
        wrong_instrument_view = replace(
            view,
            view_id=InvestmentViewRef(uuid4()),
            slice=replace(view.slice, instrument_id=FinancialInstrumentId(uuid4())),
            hypothesis_ids=(),
        )
        with pytest.raises(InvalidInvestmentJudgment):
            await service.record_view(
                OperationId(uuid4()), decision, wrong_instrument_view
            )
        with pytest.raises(DBAPIError):
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "UPDATE investment_views SET payload = payload "
                        "WHERE view_id = :view_id"
                    ),
                    {"view_id": view.view_id.value},
                )
        with pytest.raises(JudgmentIdempotencyConflict):
            await service.record_view(
                view_operation,
                decision,
                replace(view, thesis="changed thesis"),
                (hypothesis,),
            )

        challenge = MeaningfulChallengeResult(
            ChallengeResultRef(uuid4()),
            view.view_id,
            decision.decision_id,
            actor,
            NOW,
            "The trend may be a temporary rebound",
            (EvidenceBindingId(uuid4()),),
            "The liquidity assumption may fail",
            ChallengeDisposition.QUALIFIED,
            "Conflicting Evidence makes the increase conditional",
        )
        challenge_hypothesis = InvestmentHypothesis(
            InvestmentHypothesisRef(uuid4()),
            decision.decision_id,
            "A rebound could explain the observed trend",
            challenge.challenge_id,
            actor,
            NOW,
        )
        challenge = replace(
            challenge, hypothesis_ids=(challenge_hypothesis.hypothesis_id,)
        )
        await service.record_challenge(
            OperationId(uuid4()),
            challenge,
            decision.version,
            (challenge_hypothesis,),
        )
        assert await judgment_store.load_challenge(challenge.challenge_id) == challenge
        assert (
            await judgment_store.load_hypothesis(challenge_hypothesis.hypothesis_id)
            == challenge_hypothesis
        )

        alternatives = tuple(
            DecisionAlternative(
                DecisionAlternativeId(uuid4()),
                decision.decision_id,
                instrument_id,
                InvestmentHorizon("three months"),
                disposition,
                f"Material comparison for {disposition.value}",
                actor,
                NOW,
            )
            for disposition in EconomicDisposition
        )
        with pytest.raises(InvalidInvestmentJudgment):
            await service.record_alternatives(
                OperationId(uuid4()),
                decision,
                tuple(
                    replace(item, horizon=InvestmentHorizon("six months"))
                    for item in alternatives
                ),
            )
        await service.record_alternatives(OperationId(uuid4()), decision, alternatives)
        wrong_horizon_view = replace(
            view,
            view_id=InvestmentViewRef(uuid4()),
            slice=replace(view.slice, horizon=InvestmentHorizon("six months")),
            hypothesis_ids=(),
        )
        with pytest.raises(InvalidInvestmentJudgment):
            await service.record_view(
                OperationId(uuid4()), decision, wrong_horizon_view
            )
        for item in alternatives:
            assert await judgment_store.load_alternative(item.alternative_id) == item
        chosen = alternatives[0]
        await service.select_alternative(
            OperationId(uuid4()),
            decision,
            chosen.alternative_id,
            0,
            1,
        )
        assert await judgment_store.load_selection(decision.decision_id) == (
            chosen.alternative_id,
            1,
        )
        selected = await judgment_store.load_alternative(chosen.alternative_id)
        assert selected is not None and selected.revision == 2
        assert (
            await judgment_store.load_alternative(
                chosen.alternative_id,
                revision=1,
            )
            == chosen
        )
        assert (
            await judgment_store.load_alternative(alternatives[1].alternative_id)
        ).revision == 1
        with pytest.raises(JudgmentConcurrencyConflict):
            await service.select_alternative(
                OperationId(uuid4()),
                decision,
                alternatives[1].alternative_id,
                0,
                1,
            )
        corrected = replace(
            selected, material_comparison="Revised material comparison", revision=3
        )
        with pytest.raises(InvalidInvestmentJudgment):
            await service.revise_alternative(
                OperationId(uuid4()),
                replace(selected, disposition=EconomicDisposition.HOLD, revision=3),
                2,
            )
        with pytest.raises(InvalidInvestmentJudgment):
            await service.revise_alternative(
                OperationId(uuid4()),
                replace(selected, horizon=InvestmentHorizon("six months"), revision=3),
                2,
            )
        await service.revise_alternative(OperationId(uuid4()), corrected, 2)
        assert await judgment_store.load_alternative(chosen.alternative_id) == corrected
        assert (
            await judgment_store.load_alternative(
                chosen.alternative_id,
                revision=2,
            )
            == selected
        )
        with pytest.raises(JudgmentConcurrencyConflict):
            await service.select_alternative(
                OperationId(uuid4()), decision, chosen.alternative_id, 1, 2
            )
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE investment_decisions SET decision_version = 2 "
                    "WHERE decision_id = :decision_id"
                ),
                {"decision_id": decision.decision_id.value},
            )
        with pytest.raises(JudgmentConcurrencyConflict):
            await service.record_alternatives(
                OperationId(uuid4()), decision, alternatives
            )
    finally:
        await engine.dispose()


def test_investment_intelligence_judgments_are_durable_and_root_local(
    postgres_target: PostgresTestTarget,
) -> None:
    asyncio.run(_exercise(postgres_target))
