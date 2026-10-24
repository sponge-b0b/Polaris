"""Restart proof for append-only Intelligence target and catalog acts."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from polaris.application.decisions import (
    DecisionCommandEnvelope,
    DecisionInitiationService,
    InitiateDecisionCommand,
)
from polaris.application.evidence.judgment_versions import ResolvedTargetJudgment
from polaris.application.intelligence_judgment_history import (
    IntelligenceJudgmentTargetReader,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionScope,
    DecisionSubject,
    InvestmentDecisionId,
    OperationId,
    TechnicalProvenance,
    TriggerKind,
    TriggerProvenance,
)
from polaris.domain.intelligence_judgment_history import IntelligenceJudgmentHistory
from polaris.domain.portfolio import PortfolioId
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    create_postgres_engine,
)
from polaris.infrastructure.persistence.postgresql import (
    intelligence_judgment_history as history_persistence,
)
from tests.domain.test_intelligence_judgment_history import _future, _initial

from .conftest import PostgresTestTarget

NOW = datetime(2026, 10, 23, tzinfo=UTC)


async def _exercise(target: PostgresTestTarget) -> None:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        decision_store = PostgresDecisionStore(engine)
        result = await DecisionInitiationService(
            # duplicate-code: Sharing would couple restart proofs.
            # arid: disable
            reader=decision_store,
            store=decision_store,
            now=lambda: NOW,
        ).initiate(
            InitiateDecisionCommand(
                envelope=DecisionCommandEnvelope(
                    operation_id=OperationId(uuid4()),
                    actor_attribution=KnownActorAttribution(ActorId(uuid4())),
                    # arid: enable
                    trigger=TriggerProvenance(
                        TriggerKind.HUMAN_REQUEST, "owner-history"
                    ),
                    effective_at=NOW,
                    technical_provenance=TechnicalProvenance(),
                    expected_versions=frozenset(),
                ),
                need_statement="Decide the Portfolio investment exposure",
                subject=DecisionSubject("Investment exposure"),
                scope=DecisionScope.established(PortfolioId(uuid4())),
            )
        )
        assert isinstance(result.decision_id, InvestmentDecisionId)
        seed = _initial().acts[0]
        assert seed.assertion is not None
        initial = replace(
            seed,
            assertion=replace(seed.assertion, decision_id=result.decision_id),
        )
        history = IntelligenceJudgmentHistory.form(initial)
        async with engine.begin() as connection:
            await history_persistence.insert_initial_intelligence_act(
                connection, initial
            )
        store = history_persistence.PostgresIntelligenceJudgmentHistoryStore(engine)
        assert await store.load(initial.root) == history
        future = _future(history)
        await store.append(future)
        restarted = history_persistence.PostgresIntelligenceJudgmentHistoryStore(engine)
        loaded = await restarted.load(initial.root)
        assert loaded is not None
        assert loaded.acts == (initial, future)
        assert loaded.versions[0] == loaded.versions[1]
        target = await IntelligenceJudgmentTargetReader(restarted).read_at(
            initial.root,
            effective_at=future.effective_at,
            known_at=future.known_at,
        )
        assert isinstance(target, ResolvedTargetJudgment)
        assert target.assertion == future.assertion
    finally:
        await engine.dispose()


def test_intelligence_target_history_survives_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    asyncio.run(_exercise(postgres_target))
