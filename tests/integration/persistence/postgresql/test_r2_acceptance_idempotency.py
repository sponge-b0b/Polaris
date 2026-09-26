from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from polaris.application.decisions import (
    DecisionCommandEnvelope,
    DecisionInitiationService,
    DecisionMemoryService,
    DecisionMutationResultKind,
    DecisionOrdinaryWorkService,
    ExpectedDecisionVersion,
    IdempotencyConflict,
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

START = datetime(2026, 9, 20, 7, 0, tzinfo=UTC)
ACTOR = KnownActorAttribution(ActorId(UUID("00000000-0000-4000-8000-000000000801")))


# duplicate-code: this acceptance module keeps deterministic identity/envelope fixtures
# local so receipt semantics remain independently executable at the product boundary.
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
    generated = _ids(802, 803, 804)
    # duplicate-code: this ticket-level acceptance seam owns its initiation setup;
    # sharing the application-call scaffold with renewal acceptance would couple
    # independently evolving end-to-end proofs.
    # arid: disable
    result = await DecisionInitiationService(
        reader=store,
        store=store,
        now=lambda: START,
        new_uuid=lambda: next(generated),
    ).initiate(
        InitiateDecisionCommand(
            envelope=_envelope(
                operation=805,
                reference="acceptance-idempotency-initiate",
                effective_at=START,
            ),
            need_statement="Decide whether to rebalance the portfolio",
            subject=DecisionSubject("Portfolio allocation"),
            scope=DecisionScope.unresolved(),
        )
    )
    # arid: enable
    return result


def test_r2_acceptance_operation_receipt_replays_after_restart_and_rejects_reuse(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        mutation_at = START + timedelta(minutes=10)
        operation_id = OperationId(_uuid(806))
        revised_subject = DecisionSubject("Rebalanced portfolio allocation")

        async with postgres_engine_store(postgres_target) as (_, store):
            initiation = await _initiate(store)
            decision_id = initiation.decision_id
            command = ReviseDecisionSubjectCommand(
                envelope=DecisionCommandEnvelope(
                    operation_id=operation_id,
                    actor_attribution=ACTOR,
                    trigger=TriggerProvenance(
                        TriggerKind.HUMAN_REQUEST,
                        "acceptance-idempotency-revise-subject",
                    ),
                    effective_at=mutation_at,
                    technical_provenance=_technical(
                        "acceptance-idempotency-revise-subject"
                    ),
                    expected_versions=frozenset(
                        {ExpectedDecisionVersion(decision_id, DecisionVersion(1))}
                    ),
                ),
                decision_id=decision_id,
                subject=revised_subject,
                continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            )
            committed = await DecisionOrdinaryWorkService(
                store=store,
                now=lambda: mutation_at,
                new_uuid=lambda: _uuid(807),
            ).revise_subject(command)

            assert committed.decision_id == decision_id
            assert committed.kind is DecisionMutationResultKind.APPLIED
            assert committed.version == DecisionVersion(2)
            assert not committed.replayed

            memory = DecisionMemoryService(reader=store, now=lambda: mutation_at)
            committed_current = await memory.current(decision_id)
            committed_history = await memory.history(decision_id)
            assert committed_current.subject == revised_subject
            assert committed_current.version == DecisionVersion(2)
            assert [type(fact) for fact in committed_history.lifecycle_facts] == [
                DecisionInitiated,
                DecisionSubjectRevised,
            ]
            revised_fact = committed_history.lifecycle_facts[-1]
            assert isinstance(revised_fact, DecisionSubjectRevised)
            assert revised_fact.metadata.operation_id == operation_id
            assert revised_fact.metadata.recorded_at == mutation_at

        replay_at = mutation_at + timedelta(minutes=10)
        async with postgres_engine_store(postgres_target) as (_, restarted_store):
            replayed = await DecisionOrdinaryWorkService(
                store=restarted_store,
                now=lambda: replay_at,
                new_uuid=lambda: _uuid(808),
            ).revise_subject(command)

            assert replayed.decision_id == committed.decision_id
            assert replayed.kind is committed.kind
            assert replayed.version == committed.version
            assert replayed.replayed

            restarted_memory = DecisionMemoryService(
                reader=restarted_store,
                now=lambda: replay_at,
            )
            replayed_current = await restarted_memory.current(decision_id)
            replayed_history = await restarted_memory.history(decision_id)
            assert replayed_current.subject == committed_current.subject
            assert replayed_current.version == committed_current.version
            assert replayed_history.lifecycle_facts == committed_history.lifecycle_facts

            changed_request = ReviseDecisionSubjectCommand(
                envelope=command.envelope,
                decision_id=decision_id,
                subject=DecisionSubject("Materially different allocation"),
                continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            )
            with pytest.raises(IdempotencyConflict) as exc_info:
                await DecisionOrdinaryWorkService(
                    store=restarted_store,
                    now=lambda: replay_at + timedelta(minutes=5),
                    new_uuid=lambda: _uuid(809),
                ).revise_subject(changed_request)
            assert exc_info.value.operation_id == operation_id

            after_conflict = await restarted_memory.current(decision_id)
            history_after_conflict = await restarted_memory.history(decision_id)
            assert after_conflict.subject == replayed_current.subject
            assert after_conflict.version == replayed_current.version
            assert (
                history_after_conflict.lifecycle_facts
                == replayed_history.lifecycle_facts
            )

        final_replay_at = replay_at + timedelta(minutes=10)
        async with postgres_engine_store(postgres_target) as (_, final_store):
            replayed_again = await DecisionOrdinaryWorkService(
                store=final_store,
                now=lambda: final_replay_at,
                new_uuid=lambda: _uuid(810),
            ).revise_subject(command)

            assert replayed_again.decision_id == committed.decision_id
            assert replayed_again.kind is committed.kind
            assert replayed_again.version == committed.version
            assert replayed_again.replayed

            final_memory = DecisionMemoryService(
                reader=final_store,
                now=lambda: final_replay_at,
            )
            final_current = await final_memory.current(decision_id)
            final_history = await final_memory.history(decision_id)
            assert final_current.subject == committed_current.subject
            assert final_current.version == committed_current.version
            assert final_history.lifecycle_facts == committed_history.lifecycle_facts

    asyncio.run(scenario())
