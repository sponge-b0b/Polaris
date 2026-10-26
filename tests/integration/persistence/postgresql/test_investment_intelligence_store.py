from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta, tzinfo
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from polaris.application.decisions import (
    ApplySubstantiveResolutionCommand,
    ContinuityDetermination,
    DecisionCommandEnvelope,
    DecisionInitiationService,
    DecisionOrdinaryWorkService,
    ExpectedDecisionVersion,
    InitiateDecisionCommand,
)
from polaris.application.decisions.relationships import (
    DecisionRelationshipService,
    EstablishSupersessionCommand,
    SupersessionTarget,
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
    HumanInvestmentDecisionEffect,
    InvestmentDecisionId,
    OperationId,
    SupersedesRelationshipBasis,
    TechnicalProvenance,
    TriggerKind,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
)
from polaris.domain.evidence.judgments import (
    InvestmentHypothesisRef,
    InvestmentViewRef,
    RecommendationWithholdingJudgmentRef,
)
from polaris.domain.evidence.judgments import (
    MeaningfulChallengeResultRef as ChallengeResultRef,
)
from polaris.domain.intelligence_judgment_history import IntelligenceClaimCatalog
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
from polaris.domain.investment_recommendation import RecommendationWithholdingJudgment
from polaris.domain.portfolio import FinancialInstrumentId, PortfolioId
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    PostgresInvestmentIntelligenceStore,
    create_postgres_engine,
)
from polaris.infrastructure.persistence.postgresql import (
    investment_intelligence as intelligence_module,
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
            (),
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
            (),
            "The liquidity assumption may fail",
            ChallengeDisposition.QUALIFIED,
            "A competing interpretation makes the increase conditional",
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
        async with engine.connect() as connection:
            receipt_count = await connection.scalar(
                text("SELECT count(*) FROM investment_intelligence_command_receipts")
            )
        decision_state_update = text(
            "UPDATE investment_decisions SET "
            "lifecycle_interpretation_kind = :interpretation, "
            "lifecycle_disposition = :disposition, "
            "applicability = :applicability "
            "WHERE decision_id = :decision_id"
        )
        operative_state = {
            "interpretation": "DETERMINATE",
            "disposition": "unresolved",
            "applicability": "operative",
            "decision_id": decision.decision_id.value,
        }
        resolved_at = datetime.now(UTC)
        resolution = await DecisionOrdinaryWorkService(
            store=decision_store,
            now=lambda: resolved_at,
        ).apply_substantive_resolution(
            ApplySubstantiveResolutionCommand(
                DecisionCommandEnvelope(
                    operation_id=OperationId(uuid4()),
                    actor_attribution=actor,
                    trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "resolve"),
                    effective_at=resolved_at,
                    technical_provenance=TechnicalProvenance(),
                    expected_versions=frozenset(
                        {
                            ExpectedDecisionVersion(
                                decision.decision_id, decision.version
                            )
                        }
                    ),
                ),
                decision.decision_id,
                TrustedHumanInvestmentDecisionBasis(
                    "resolved by human",
                    HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
                ),
            )
        )

        async def reject_after_resolution() -> None:
            rejected_challenge = replace(
                challenge, challenge_id=ChallengeResultRef(uuid4()), hypothesis_ids=()
            )
            rejected_alternatives = tuple(
                replace(item, alternative_id=DecisionAlternativeId(uuid4()))
                for item in alternatives
            )
            withholding = RecommendationWithholdingJudgment(
                withholding_id=RecommendationWithholdingJudgmentRef(uuid4()),
                decision_id=decision.decision_id,
                horizon=InvestmentHorizon("three months"),
                explanation="Ordinary work gate rejects this attempted formation",
                actor_attribution=actor,
                formed_at=NOW,
            )
            with pytest.raises(InvalidInvestmentJudgment, match="ordinary work"):
                await judgment_store.record_view(
                    OperationId(uuid4()),
                    replace(
                        view, view_id=InvestmentViewRef(uuid4()), hypothesis_ids=()
                    ),
                    (),
                    resolution.version,
                )
            with pytest.raises(InvalidInvestmentJudgment, match="ordinary work"):
                await judgment_store.record_challenge(
                    OperationId(uuid4()), rejected_challenge, (), resolution.version
                )
            with pytest.raises(InvalidInvestmentJudgment, match="ordinary work"):
                await judgment_store.record_alternatives(
                    OperationId(uuid4()), rejected_alternatives, resolution.version
                )
            with pytest.raises(InvalidInvestmentJudgment, match="ordinary work"):
                await judgment_store.record_withholding(
                    operation_id=OperationId(uuid4()),
                    withholding=withholding,
                    expected_decision_version=resolution.version,
                    initial_claim_catalog=IntelligenceClaimCatalog(()),
                )
            async with engine.connect() as connection:
                assert (
                    await connection.scalar(
                        text(
                            "SELECT count(*) FROM "
                            "investment_intelligence_command_receipts"
                        )
                    )
                    == receipt_count
                )

        await reject_after_resolution()
        async with engine.begin() as connection:
            await connection.execute(decision_state_update, operative_state)
        await reject_after_resolution()
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


def test_future_supersession_rejects_intelligence_writes_with_lagging_process_clock(
    postgres_target: PostgresTestTarget, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        try:
            decisions = PostgresDecisionStore(engine)
            intelligence = PostgresInvestmentIntelligenceStore(engine)
            async with engine.connect() as connection:
                database_now = await connection.scalar(text("SELECT clock_timestamp()"))
            assert isinstance(database_now, datetime)
            lagging_now = database_now - timedelta(days=2)
            effective_at = database_now - timedelta(days=1)
            actor = KnownActorAttribution(ActorId(uuid4()))
            portfolio_id = PortfolioId(uuid4())

            async def initiate(label: str) -> InvestmentDecisionId:
                # duplicate-code: this clock-boundary proof creates its own Decision
                # history; sharing the earlier lifecycle fixture could hide the skew.
                # arid: disable
                result = await DecisionInitiationService(
                    reader=decisions, store=decisions, now=lambda: lagging_now
                ).initiate(
                    InitiateDecisionCommand(
                        envelope=DecisionCommandEnvelope(
                            operation_id=OperationId(uuid4()),
                            actor_attribution=actor,
                            trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, label),
                            effective_at=lagging_now,
                            technical_provenance=TechnicalProvenance(),
                            expected_versions=frozenset(),
                        ),
                        need_statement=f"Need {label}",
                        subject=DecisionSubject(label),
                        scope=DecisionScope.established(portfolio_id),
                        continuity=ContinuityDetermination.create_new(label),
                    )
                )
                return result.decision_id
                # arid: enable

            target_id = await initiate("intelligence target")
            source_id = await initiate("superseding source")
            target_state = await decisions.load_decision_for_command(
                target_id, known_at=lagging_now
            )
            source_state = await decisions.load_decision_for_command(
                source_id, known_at=lagging_now
            )
            assert target_state is not None and source_state is not None
            target_version = target_state.decision.version
            source_version = source_state.decision.version
            view = InvestmentView(
                InvestmentViewRef(uuid4()),
                target_id,
                R3InvestmentSlice(
                    portfolio_id,
                    FIRST_R3_SPY_INSTRUMENT_ID,
                    InvestmentHorizon("three months"),
                ),
                "A SPY increase may be justified",
                actor,
                lagging_now,
                # duplicate-code: this independent temporal proof keeps the full View
                # content visible instead of inheriting the earlier View's assertions.
                # arid: disable
                (),
                ("cash remains adequate",),
                "returns remain uncertain",
                "holding cash may be preferable",
                ("liquidity deteriorates",),
                # arid: enable
                (),
                (),
            )
            await intelligence.record_view(
                OperationId(uuid4()), view, (), target_version
            )

            relationship_recorded_at = lagging_now + timedelta(hours=1)
            result = await DecisionRelationshipService(
                reader=decisions,
                store=decisions,
                now=lambda: relationship_recorded_at,
            ).establish_supersession(
                EstablishSupersessionCommand(
                    envelope=DecisionCommandEnvelope(
                        operation_id=OperationId(uuid4()),
                        actor_attribution=actor,
                        trigger=TriggerProvenance(
                            TriggerKind.HUMAN_REQUEST, "supersede"
                        ),
                        effective_at=relationship_recorded_at,
                        technical_provenance=TechnicalProvenance(),
                        expected_versions=frozenset(
                            {
                                ExpectedDecisionVersion(source_id, source_version),
                                ExpectedDecisionVersion(target_id, target_version),
                            }
                        ),
                    ),
                    source_decision_id=source_id,
                    targets=(
                        SupersessionTarget(
                            target_id,
                            SupersedesRelationshipBasis(("replacement",)),
                            effective_at,
                        ),
                    ),
                )
            )
            assert result.versioned_decision_ids == frozenset()

            class LaggingDateTime(datetime):
                @classmethod
                def now(cls, tz: tzinfo | None = None) -> LaggingDateTime:
                    return cls.fromtimestamp(lagging_now.timestamp(), tz or UTC)

            monkeypatch.setattr(intelligence_module, "datetime", LaggingDateTime)
            async with engine.connect() as connection:
                receipt_count = await connection.scalar(
                    text(
                        "SELECT count(*) FROM investment_intelligence_command_receipts"
                    )
                )
            challenge = MeaningfulChallengeResult(
                ChallengeResultRef(uuid4()),
                view.view_id,
                target_id,
                actor,
                lagging_now,
                "A rebound may be temporary",
                (),
                "The liquidity assumption may fail",
                ChallengeDisposition.QUALIFIED,
                "The interpretation remains conditional",
            )
            # duplicate-code: each proof states its own complete economic alternatives;
            # sharing their setup could couple unrelated lifecycle and clock assertions.
            # arid: disable
            alternatives = tuple(
                DecisionAlternative(
                    DecisionAlternativeId(uuid4()),
                    target_id,
                    FIRST_R3_SPY_INSTRUMENT_ID,
                    InvestmentHorizon("three months"),
                    disposition,
                    f"Material comparison for {disposition.value}",
                    actor,
                    lagging_now,
                )
                for disposition in EconomicDisposition
            )
            # arid: enable
            withholding = RecommendationWithholdingJudgment(
                withholding_id=RecommendationWithholdingJudgmentRef(uuid4()),
                decision_id=target_id,
                horizon=InvestmentHorizon("three months"),
                explanation="Support is insufficient",
                actor_attribution=actor,
                formed_at=lagging_now,
            )
            with pytest.raises(InvalidInvestmentJudgment, match="ordinary work"):
                await intelligence.record_view(
                    OperationId(uuid4()),
                    replace(view, view_id=InvestmentViewRef(uuid4())),
                    (),
                    target_version,
                )
            with pytest.raises(InvalidInvestmentJudgment, match="ordinary work"):
                await intelligence.record_challenge(
                    OperationId(uuid4()), challenge, (), target_version
                )
            with pytest.raises(InvalidInvestmentJudgment, match="ordinary work"):
                await intelligence.record_alternatives(
                    OperationId(uuid4()), alternatives, target_version
                )
            with pytest.raises(InvalidInvestmentJudgment, match="ordinary work"):
                await intelligence.record_withholding(
                    OperationId(uuid4()),
                    withholding,
                    target_version,
                    IntelligenceClaimCatalog(()),
                )
            # duplicate-code: independent no-write evidence stays beside this clock
            # boundary so a shared assertion cannot mask the regression.
            # arid: disable
            async with engine.connect() as connection:
                assert (
                    await connection.scalar(
                        text(
                            "SELECT count(*) FROM "
                            "investment_intelligence_command_receipts"
                        )
                    )
                    == receipt_count
                )
            # arid: enable
        finally:
            await engine.dispose()

    asyncio.run(scenario())
