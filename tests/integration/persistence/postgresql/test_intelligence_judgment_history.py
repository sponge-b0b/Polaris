"""Restart proof for append-only Intelligence target and catalog acts."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from polaris.application.decisions import (
    DecisionCommandEnvelope,
    DecisionInitiationService,
    InitiateDecisionCommand,
)
from polaris.application.evidence.judgment_versions import (
    ResolvedTargetJudgment,
    TargetJudgmentMissing,
)
from polaris.application.evidence.owner_meaning import (
    OwnerCauseVerdict,
    OwnerMeaningWitness,
    TargetJudgmentMeaning,
)
from polaris.application.intelligence_judgment_history import (
    IntelligenceJudgmentHistoryUnavailable,
    IntelligenceJudgmentMeaningReader,
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
from polaris.domain.evidence.context_versions import BasisScopeKey
from polaris.domain.evidence.judgments import EvidenceUse, JudgmentWideEvidenceScope
from polaris.domain.intelligence_judgment_history import (
    IntelligenceJudgmentHistory,
    PendingDisposition,
)
from polaris.domain.portfolio import PortfolioId
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    create_postgres_engine,
)
from polaris.infrastructure.persistence.postgresql import (
    intelligence_judgment_history as history_persistence,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    investment_intelligence_act_publications,
)
from tests.domain.test_intelligence_judgment_history import (
    _draft,
    _future,
    _immediate,
    _initial,
)

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
        await history_persistence.ensure_intelligence_commit_slot(engine)
        async with engine.begin() as connection:
            await history_persistence.insert_initial_intelligence_act(
                connection, _draft(initial)
            )
            async with engine.connect() as observer:
                before_initial_commit = await observer.scalar(
                    select(func.clock_timestamp())
                )
        assert isinstance(before_initial_commit, datetime)
        slot = await history_persistence.ensure_intelligence_commit_slot(engine)
        async with engine.connect() as connection:
            assert (
                await connection.scalar(
                    select(func.count()).select_from(
                        investment_intelligence_act_publications
                    )
                )
                == 0
            )
            pending = (
                (
                    await connection.execute(
                        text(
                            "SELECT data FROM pg_logical_slot_peek_binary_changes("
                            ":slot, NULL, NULL, 'proto_version', '1', "
                            "'publication_names', :publication, 'messages', 'true')"
                        ),
                        {"slot": slot, "publication": slot},
                    )
                )
                .scalars()
                .all()
            )
            assert any(
                payload.startswith(b"M") and str(initial.act_id).encode() in payload
                for payload in pending
            )
        store = history_persistence.PostgresIntelligenceJudgmentHistoryStore(engine)
        reader = IntelligenceJudgmentTargetReader(store)
        assert isinstance(
            await reader.read_at(
                initial.root,
                effective_at=before_initial_commit,
                known_at=before_initial_commit,
            ),
            TargetJudgmentMissing,
        )
        loaded_initial = await store.load(initial.root)
        assert loaded_initial is not None
        assert loaded_initial.acts[0].act_id == initial.act_id
        assert loaded_initial.acts[0].known_at > before_initial_commit
        async with engine.connect() as connection:
            assert (
                await connection.scalar(
                    select(
                        investment_intelligence_act_publications.c.committed_at
                    ).where(
                        investment_intelligence_act_publications.c.act_id
                        == initial.act_id
                    )
                )
                == loaded_initial.acts[0].known_at
            )
        future = replace(
            _future(history), effective_at=datetime.now(UTC) + timedelta(days=1)
        )
        await store.append(_draft(future))
        restarted = history_persistence.PostgresIntelligenceJudgmentHistoryStore(engine)
        loaded = await restarted.load(initial.root)
        assert loaded is not None
        assert tuple(act.act_id for act in loaded.acts) == (
            initial.act_id,
            future.act_id,
        )
        assert loaded.versions[0] == loaded.versions[1]
        async with engine.connect() as observer:
            before_correction = await observer.scalar(select(func.clock_timestamp()))
        assert isinstance(before_correction, datetime)
        prior = await reader.read_at(
            initial.root,
            effective_at=before_correction,
            known_at=before_correction,
        )
        assert isinstance(prior, ResolvedTargetJudgment)
        meaning_reader = IntelligenceJudgmentMeaningReader(store)
        key = BasisScopeKey(
            result.decision_id,
            initial.root,
            JudgmentWideEvidenceScope(),
            EvidenceUse.JUDGMENT_BASIS,
        )
        witness = await meaning_reader.read_at(
            key,
            TargetJudgmentMeaning(prior.version),
            effective_at=before_correction,
            known_at=before_correction,
            read_at=before_correction,
        )
        assert isinstance(witness, OwnerMeaningWitness)
        correction = _draft(_immediate(loaded, PendingDisposition.CANCEL))
        corrected = await store.append(correction)
        assert await store.append(correction) == corrected
        assert corrected.versions[-1][0].value == loaded.versions[-1][0].value + 1
        assert (
            await reader.read_at(
                initial.root,
                effective_at=before_correction,
                known_at=before_correction,
            )
            == prior
        )
        assert (
            await meaning_reader.verify_cause(
                witness, validation_at=corrected.acts[-1].known_at
            )
            is OwnerCauseVerdict.VALID
        )
        target = await IntelligenceJudgmentTargetReader(restarted).read_at(
            initial.root,
            effective_at=future.effective_at,
            known_at=loaded.acts[1].known_at,
        )
        assert isinstance(target, ResolvedTargetJudgment)
        assert target.assertion == future.assertion
        async with engine.connect() as connection:
            connection = await connection.execution_options(
                isolation_level="AUTOCOMMIT"
            )
            await connection.execute(
                text("SELECT pg_drop_replication_slot(:slot)"), {"slot": slot}
            )
        assert await restarted.load(initial.root) == corrected
        with pytest.raises(IntelligenceJudgmentHistoryUnavailable):
            await store.append(correction)
    finally:
        await engine.dispose()


def test_intelligence_target_history_survives_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    asyncio.run(_exercise(postgres_target))
