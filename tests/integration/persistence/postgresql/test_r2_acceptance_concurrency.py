from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from polaris.application.decisions import (
    ConcurrencyConflict,
    DecisionCommandEnvelope,
    DecisionInitiationService,
    DecisionMemoryService,
    DecisionMutationResultKind,
    DecisionOrdinaryWorkService,
    ExpectedDecisionVersion,
    InitiateDecisionCommand,
    InitiationResult,
    ReviseDecisionSubjectCommand,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionContinuity,
    DecisionInitiated,
    DecisionScope,
    DecisionSubject,
    DecisionSubjectRevised,
    DecisionVersion,
    InvestmentDecisionId,
    OperationId,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
)
from polaris.infrastructure.persistence.postgresql import PostgresDecisionStore

from .conftest import PostgresTestTarget, postgres_engine_store

START = datetime(2026, 9, 20, 8, 0, tzinfo=UTC)
ACTOR = KnownActorAttribution(ActorId(UUID("00000000-0000-4000-8000-000000000901")))


# duplicate-code: this acceptance module owns deterministic command fixtures locally;
# sharing them across ticket-level acceptance proofs would couple independent scenarios.
# arid: disable
def _uuid(value: int) -> UUID:
    return UUID(f"00000000-0000-4000-8000-{value:012x}")


def _ids(*values: int) -> Iterator[UUID]:
    yield from (_uuid(value) for value in values)


def _technical(reference: str) -> TechnicalProvenance:
    return TechnicalProvenance(
        (
            TechnicalReference(TechnicalReferenceKind.TRACE, f"trace-{reference}"),
            TechnicalReference(TechnicalReferenceKind.REQUEST, reference),
        )
    )


def _envelope(
    *,
    operation: int,
    reference: str,
    effective_at: datetime,
    decision_id: InvestmentDecisionId | None = None,
    version: DecisionVersion | None = None,
) -> DecisionCommandEnvelope:
    expected = (
        frozenset()
        if decision_id is None or version is None
        else frozenset({ExpectedDecisionVersion(decision_id, version)})
    )
    return DecisionCommandEnvelope(
        operation_id=OperationId(_uuid(operation)),
        actor_attribution=ACTOR,
        trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, reference),
        effective_at=effective_at,
        technical_provenance=_technical(reference),
        expected_versions=expected,
    )


# arid: enable
async def _initiate(store: PostgresDecisionStore) -> InitiationResult:
    generated = _ids(902, 903, 904)
    # duplicate-code: the acceptance seam keeps its initiation setup local so failure
    # identifies this ticket's concurrency proof rather than a shared test abstraction.
    # arid: disable
    result = await DecisionInitiationService(
        reader=store,
        store=store,
        now=lambda: START,
        new_uuid=lambda: next(generated),
    ).initiate(
        InitiateDecisionCommand(
            envelope=_envelope(
                operation=905,
                reference="acceptance-stale-version-initiate",
                effective_at=START,
            ),
            need_statement="Decide whether to rebalance the portfolio",
            subject=DecisionSubject("Portfolio allocation"),
            scope=DecisionScope.unresolved(),
        )
    )
    # arid: enable
    return result


def _revision(
    *,
    decision_id: InvestmentDecisionId,
    operation: int,
    reference: str,
    effective_at: datetime,
    expected_version: DecisionVersion,
    subject: str,
) -> ReviseDecisionSubjectCommand:
    # duplicate-code: this ticket owns its stale-version command construction;
    # sharing it with other acceptance scenarios would couple independent proofs.
    # arid: disable
    result = ReviseDecisionSubjectCommand(
        envelope=_envelope(
            operation=operation,
            reference=reference,
            effective_at=effective_at,
            decision_id=decision_id,
            version=expected_version,
        ),
        decision_id=decision_id,
        subject=DecisionSubject(subject),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
    )
    # arid: enable
    return result


def test_r2_acceptance_stale_expected_version_fails_closed_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        committed_at = START + timedelta(minutes=10)
        stale_at = committed_at + timedelta(minutes=10)

        async with postgres_engine_store(postgres_target) as (_, store):
            initiation = await _initiate(store)
            decision_id = initiation.decision_id

            current_command = _revision(
                decision_id=decision_id,
                operation=906,
                reference="acceptance-current-version",
                effective_at=committed_at,
                expected_version=DecisionVersion(1),
                subject="Rebalanced portfolio allocation",
            )
            committed = await DecisionOrdinaryWorkService(
                store=store,
                now=lambda: committed_at,
                new_uuid=lambda: _uuid(907),
            ).revise_subject(current_command)

            # duplicate-code: current-version success assertions stay local so this
            # acceptance proof remains independently diagnostic.
            # arid: disable
            assert committed.decision_id == decision_id
            assert committed.kind is DecisionMutationResultKind.APPLIED
            assert committed.version == DecisionVersion(2)
            assert not committed.replayed
            # arid: enable

            memory = DecisionMemoryService(reader=store, now=lambda: committed_at)
            committed_current = await memory.current(decision_id)
            committed_history = await memory.history(decision_id)
            assert committed_current.subject == DecisionSubject(
                "Rebalanced portfolio allocation"
            )
            # duplicate-code: the canonical two-fact lifecycle assertion is part of
            # this ticket's acceptance seam, not a shared test abstraction.
            # arid: disable
            assert committed_current.version == DecisionVersion(2)
            assert [type(fact) for fact in committed_history.lifecycle_facts] == [
                DecisionInitiated,
                DecisionSubjectRevised,
            ]
            # arid: enable
            assert committed_history.relationship_facts == ()

            stale_command = _revision(
                decision_id=decision_id,
                operation=908,
                reference="acceptance-stale-version",
                effective_at=stale_at,
                expected_version=DecisionVersion(1),
                subject="Stale portfolio allocation",
            )
            with pytest.raises(ConcurrencyConflict):
                await DecisionOrdinaryWorkService(
                    store=store,
                    now=lambda: stale_at,
                    new_uuid=lambda: _uuid(909),
                ).revise_subject(stale_command)

            after_stale = await memory.current(decision_id)
            history_after_stale = await memory.history(decision_id)
            assert after_stale.subject == committed_current.subject
            assert after_stale.version == committed_current.version
            assert (
                history_after_stale.lifecycle_facts == committed_history.lifecycle_facts
            )
            assert (
                history_after_stale.relationship_facts
                == committed_history.relationship_facts
            )

        restart_at = stale_at + timedelta(minutes=10)
        async with postgres_engine_store(postgres_target) as (_, restarted_store):
            with pytest.raises(ConcurrencyConflict):
                await DecisionOrdinaryWorkService(
                    store=restarted_store,
                    now=lambda: restart_at,
                    new_uuid=lambda: _uuid(910),
                ).revise_subject(stale_command)

            restarted_memory = DecisionMemoryService(
                reader=restarted_store,
                now=lambda: restart_at,
            )
            restarted_current = await restarted_memory.current(decision_id)
            restarted_history = await restarted_memory.history(decision_id)
            assert restarted_current.subject == committed_current.subject
            assert restarted_current.version == committed_current.version
            assert (
                restarted_history.lifecycle_facts == committed_history.lifecycle_facts
            )
            assert (
                restarted_history.relationship_facts
                == committed_history.relationship_facts
            )

    asyncio.run(scenario())
