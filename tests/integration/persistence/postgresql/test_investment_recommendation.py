from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from polaris.application.decisions import (
    DecisionCommandEnvelope,
    DecisionInitiationService,
    InitiateDecisionCommand,
)
from polaris.application.investment_recommendation import (
    InvestmentRecommendationService,
    RecommendationSupportKind,
    derive_current_recommendation_support,
)
from polaris.domain.actors import (
    ActorId,
    KnownActorAttribution,
    UnknownActorAttribution,
)
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.decisions import (
    DecisionScope,
    DecisionSubject,
    OperationId,
    TechnicalProvenance,
    TriggerKind,
    TriggerProvenance,
)
from polaris.domain.evidence.judgments import RecommendationWithholdingJudgmentRef
from polaris.domain.intelligence_judgment_history import IntelligenceClaimCatalog
from polaris.domain.investment_recommendation import RecommendationWithholdingJudgment
from polaris.domain.portfolio import PortfolioId
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    PostgresInvestmentIntelligenceStore,
    create_postgres_engine,
)

from .conftest import PostgresTestTarget

AT = datetime(2026, 10, 20, tzinfo=UTC)


async def _scenario(target: PostgresTestTarget) -> None:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        decision_store = PostgresDecisionStore(engine)
        # duplicate-code: Sharing would couple restart proofs.
        # arid: disable
        accepted = await DecisionInitiationService(
            reader=decision_store, store=decision_store, now=lambda: AT
        ).initiate(
            InitiateDecisionCommand(
                envelope=DecisionCommandEnvelope(
                    operation_id=OperationId(uuid4()),
                    actor_attribution=KnownActorAttribution(ActorId(uuid4())),
                    trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "user-399"),
                    effective_at=AT,
                    technical_provenance=TechnicalProvenance(),
                    expected_versions=frozenset(),
                ),
                need_statement="Choose SPY exposure",
                subject=DecisionSubject("Increase, hold, or reduce SPY"),
                scope=DecisionScope.established(PortfolioId(uuid4())),
            )
        )
        # arid: enable
        state = await decision_store.load_decision_for_command(
            accepted.decision_id, known_at=AT
        )
        assert state is not None
        service = InvestmentRecommendationService(
            PostgresInvestmentIntelligenceStore(engine)
        )
        assert (
            await service.current_support(accepted.decision_id)
        ).kind is RecommendationSupportKind.NO_ATTEMPT
        first = RecommendationWithholdingJudgment(
            RecommendationWithholdingJudgmentRef(uuid4()),
            accepted.decision_id,
            InvestmentHorizon("three months"),
            "Material Portfolio Risk is unresolved",
            UnknownActorAttribution(),
            AT,
        )
        second = RecommendationWithholdingJudgment(
            RecommendationWithholdingJudgmentRef(uuid4()),
            accepted.decision_id,
            InvestmentHorizon("three months"),
            "A later formation attempt still lacks sufficient support",
            UnknownActorAttribution(),
            AT + timedelta(seconds=1),
        )
        catalog = IntelligenceClaimCatalog(())
        await service.withhold(
            OperationId(uuid4()), first, state.decision.version, catalog
        )
        await service.withhold(
            OperationId(uuid4()), second, state.decision.version, catalog
        )
    finally:
        await engine.dispose()

    restarted = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        service = InvestmentRecommendationService(
            PostgresInvestmentIntelligenceStore(restarted)
        )
        history = await service.history(accepted.decision_id)
        assert history == (first, second)
        current = derive_current_recommendation_support(
            history, decision_applicable=True, evidence_fit=True, risk_fit=True
        )
        assert current.kind is RecommendationSupportKind.WITHHELD
        assert current.latest == second
        assert (
            await service.current_support(accepted.decision_id)
        ).kind is RecommendationSupportKind.WITHHELD
    finally:
        await restarted.dispose()


def test_withholding_history_is_durable_and_ordered(
    postgres_target: PostgresTestTarget,
) -> None:
    asyncio.run(_scenario(postgres_target))
