from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from polaris.application.decisions import (
    ContinuityAmbiguous,
    ContinuityConflict,
    ContinuityDetermination,
    DecisionCommandEnvelope,
    DecisionHistoryView,
    DecisionInitiationService,
    DecisionMemoryReader,
    DecisionMemoryService,
    InitiateDecisionCommand,
    InitiationResult,
    InitiationResultKind,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionInitiated,
    DecisionInitiationDetermination,
    DecisionScope,
    DecisionSubject,
    InvestmentDecisionId,
    OperationId,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
)
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    create_postgres_engine,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    decision_needs,
    investment_decision_command_receipts,
    investment_decision_lifecycle_facts,
    investment_decisions,
)

from .conftest import PostgresTestTarget, postgres_engine_store, postgres_row_counts

START = datetime(2026, 9, 19, 7, 0, tzinfo=UTC)
ACTOR = KnownActorAttribution(ActorId(UUID("00000000-0000-4000-8000-000000001001")))


def _uuid(value: int) -> UUID:
    return UUID(f"00000000-0000-4000-8000-{value:012x}")


def _ids(*values: int) -> Iterator[UUID]:
    yield from (_uuid(value) for value in values)


# duplicate-code: each acceptance slice owns its command-fixture semantics; sharing
# this constructor across acceptance modules would couple independent proof setup.
# arid: disable
def _envelope(
    *,
    operation: int,
    reference: str,
    effective_at: datetime,
) -> DecisionCommandEnvelope:
    return DecisionCommandEnvelope(
        operation_id=OperationId(_uuid(operation)),
        actor_attribution=ACTOR,
        trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, reference),
        effective_at=effective_at,
        technical_provenance=TechnicalProvenance(
            (
                TechnicalReference(
                    TechnicalReferenceKind.TRACE,
                    f"trace-{reference}",
                ),
                TechnicalReference(TechnicalReferenceKind.REQUEST, reference),
            )
        ),
    )


# arid: enable


def _command(
    *,
    operation: int,
    reference: str,
    effective_at: datetime,
    continuity: ContinuityDetermination | None = None,
) -> InitiateDecisionCommand:
    return InitiateDecisionCommand(
        envelope=_envelope(
            operation=operation,
            reference=reference,
            effective_at=effective_at,
        ),
        need_statement="Decide whether to adjust the portfolio allocation",
        subject=DecisionSubject("Portfolio allocation"),
        scope=DecisionScope.unresolved(),
        continuity=continuity,
    )


def _service(
    store: PostgresDecisionStore,
    *,
    recorded_at: datetime,
    ids: tuple[int, int, int],
    reader: DecisionMemoryReader | None = None,
) -> DecisionInitiationService:
    generated = _ids(*ids)
    return DecisionInitiationService(
        reader=reader if reader is not None else store,
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: next(generated),
    )


async def _assert_persistence_counts(
    engine: AsyncEngine,
    expected: tuple[int, int, int, int],
) -> None:
    # duplicate-code: this acceptance proof intentionally enumerates its durable
    # business-write surfaces; sharing that assertion with lower-level store tests
    # would couple independent acceptance and persistence falsifiers.
    # arid: disable
    assert (
        await postgres_row_counts(
            engine,
            decision_needs,
            investment_decisions,
            investment_decision_lifecycle_facts,
            investment_decision_command_receipts,
        )
        == expected
    )
    # arid: enable


async def _history_after_restart(
    target: PostgresTestTarget,
    *,
    known_at: datetime,
    decision_id: InvestmentDecisionId,
) -> DecisionHistoryView:
    async with postgres_engine_store(target) as (_, restarted):
        return await DecisionMemoryService(
            reader=restarted,
            now=lambda: known_at,
        ).history(decision_id)


def _assert_no_database_mechanics(metadata: object) -> None:
    for database_mechanic in (
        "advisory_lock_key",
        "continuity_token",
        "generation_token",
        "lock_id",
        "row_version",
    ):
        assert not hasattr(metadata, database_mechanic)


def _store(target: PostgresTestTarget) -> tuple[AsyncEngine, PostgresDecisionStore]:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    return engine, PostgresDecisionStore(engine)


class _BarrierDecisionReader:
    def __init__(
        self,
        reader: DecisionMemoryReader,
        barrier: asyncio.Barrier,
    ) -> None:
        self._reader = reader
        self._barrier = barrier

    async def find_unresolved_continuity_candidates(
        self,
        *,
        known_at: datetime,
    ) -> tuple[InvestmentDecisionId, ...]:
        candidates = await self._reader.find_unresolved_continuity_candidates(
            known_at=known_at
        )
        await self._barrier.wait()
        return candidates


def test_r2_acceptance_continuity_choices_and_candidate_basis_survive_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine, store = _store(postgres_target)
        try:
            first = await _service(
                store,
                recorded_at=START,
                ids=(1002, 1003, 1004),
            ).initiate(
                _command(
                    operation=1005,
                    reference="acceptance-continuity-no-candidate",
                    effective_at=START,
                )
            )
            assert first.kind is InitiationResultKind.CREATED
            assert first.need_id is not None
            await _assert_persistence_counts(engine, (1, 1, 1, 1))

            ambiguous_at = START + timedelta(minutes=10)
            with pytest.raises(ContinuityAmbiguous) as raised:
                await _service(
                    store,
                    recorded_at=ambiguous_at,
                    ids=(1006, 1007, 1008),
                ).initiate(
                    _command(
                        operation=1009,
                        reference="acceptance-continuity-ambiguous",
                        effective_at=ambiguous_at,
                    )
                )
            assert raised.value.candidate_decision_ids == frozenset({first.decision_id})
            await _assert_persistence_counts(engine, (1, 1, 1, 1))

            continued_at = START + timedelta(minutes=20)
            continued = await _service(
                store,
                recorded_at=continued_at,
                ids=(1010, 1011, 1012),
            ).initiate(
                _command(
                    operation=1013,
                    reference="acceptance-continuity-continue",
                    effective_at=continued_at,
                    continuity=ContinuityDetermination.continue_existing(
                        first.decision_id
                    ),
                )
            )
            assert continued == InitiationResult(
                decision_id=first.decision_id,
                need_id=None,
                kind=InitiationResultKind.CONTINUED,
            )
            await _assert_persistence_counts(engine, (1, 1, 1, 2))

            second_at = START + timedelta(minutes=30)
            second = await _service(
                store,
                recorded_at=second_at,
                ids=(1014, 1015, 1016),
            ).initiate(
                _command(
                    operation=1017,
                    reference="acceptance-continuity-create-second",
                    effective_at=second_at,
                    continuity=ContinuityDetermination.create_new(
                        "The candidate addresses a different coherent choice"
                    ),
                )
            )
            assert second.kind is InitiationResultKind.CREATED

            third_at = START + timedelta(minutes=40)
            reference = "acceptance-continuity-create-third"
            rationale = "Both candidates address different coherent choices"
            third = await _service(
                store,
                recorded_at=third_at,
                ids=(1018, 1019, 1020),
            ).initiate(
                _command(
                    operation=1021,
                    reference=reference,
                    effective_at=third_at,
                    continuity=ContinuityDetermination.create_new(rationale),
                )
            )
            assert third.kind is InitiationResultKind.CREATED
            await _assert_persistence_counts(engine, (3, 3, 3, 4))
        finally:
            await engine.dispose()

        first_history = await _history_after_restart(
            postgres_target,
            known_at=third_at,
            decision_id=first.decision_id,
        )
        assert len(first_history.lifecycle_facts) == 1

        third_history = await _history_after_restart(
            postgres_target,
            known_at=third_at,
            decision_id=third.decision_id,
        )
        assert len(third_history.lifecycle_facts) == 1
        initiated = third_history.lifecycle_facts[0]
        assert isinstance(initiated, DecisionInitiated)
        assert (
            initiated.continuity.determination
            is DecisionInitiationDetermination.EXPLICIT_CREATE_NEW
        )
        assert initiated.continuity.candidate_decision_ids == frozenset(
            {first.decision_id, second.decision_id}
        )
        assert initiated.continuity.known_at == third_at
        assert initiated.continuity.rationale == rationale
        assert initiated.metadata.actor_attribution == ACTOR
        assert initiated.metadata.trigger == TriggerProvenance(
            TriggerKind.HUMAN_REQUEST,
            reference,
        )
        assert (
            initiated.metadata.technical_provenance
            == _envelope(
                operation=1021,
                reference=reference,
                effective_at=third_at,
            ).technical_provenance
        )
        assert initiated.metadata.effective_at == third_at
        assert initiated.metadata.recorded_at == third_at
        _assert_no_database_mechanics(initiated.metadata)

    asyncio.run(scenario())


def test_r2_acceptance_concurrent_initiation_revalidates_and_commits_one_need(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine, store = _store(postgres_target)
        reader = _BarrierDecisionReader(store, asyncio.Barrier(2))
        shared_need_id = 1101
        recorded_at = START + timedelta(hours=1)
        services = (
            _service(
                store,
                recorded_at=recorded_at,
                ids=(1102, shared_need_id, 1103),
                reader=reader,
            ),
            _service(
                store,
                recorded_at=recorded_at,
                ids=(1104, shared_need_id, 1105),
                reader=reader,
            ),
        )
        commands = (
            _command(
                operation=1106,
                reference="acceptance-continuity-race",
                effective_at=recorded_at,
            ),
            _command(
                operation=1107,
                reference="acceptance-continuity-race",
                effective_at=recorded_at,
            ),
        )
        try:
            outcomes = await asyncio.gather(
                services[0].initiate(commands[0]),
                services[1].initiate(commands[1]),
                return_exceptions=True,
            )
            created = [
                value
                for value in outcomes
                if isinstance(value, InitiationResult)
                and value.kind is InitiationResultKind.CREATED
            ]
            conflicts = [
                value for value in outcomes if isinstance(value, ContinuityConflict)
            ]
            assert len(created) == 1
            assert len(conflicts) == 1
            winner = created[0]
            winner_index = next(
                index for index, outcome in enumerate(outcomes) if outcome is winner
            )
            winner_command = commands[winner_index]
            assert conflicts[0].candidate_decision_ids == frozenset(
                {winner.decision_id}
            )
            await _assert_persistence_counts(engine, (1, 1, 1, 1))
        finally:
            await engine.dispose()

        winner_history = await _history_after_restart(
            postgres_target,
            known_at=recorded_at,
            decision_id=winner.decision_id,
        )
        assert len(winner_history.lifecycle_facts) == 1
        initiated = winner_history.lifecycle_facts[0]
        assert isinstance(initiated, DecisionInitiated)
        assert (
            initiated.continuity.determination
            is DecisionInitiationDetermination.NO_CANDIDATES
        )
        assert initiated.continuity.candidate_decision_ids == frozenset()
        assert initiated.continuity.known_at == recorded_at
        assert initiated.metadata.actor_attribution == ACTOR
        assert initiated.metadata.trigger == winner_command.envelope.trigger
        assert (
            initiated.metadata.technical_provenance
            == winner_command.envelope.technical_provenance
        )
        _assert_no_database_mechanics(initiated.metadata)

    asyncio.run(scenario())
