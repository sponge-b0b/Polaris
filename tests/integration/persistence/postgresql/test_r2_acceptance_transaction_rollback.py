from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from polaris.application.decisions import (
    DecisionCommandEnvelope,
    DecisionInitiationService,
    DecisionMemoryService,
    DecisionMutationResultKind,
    DecisionOrdinaryWorkService,
    ExpectedDecisionVersion,
    InitiateDecisionCommand,
    InitiationResult,
    PersistenceUnavailable,
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

START = datetime(2026, 9, 24, 8, 0, tzinfo=UTC)
ACTOR = KnownActorAttribution(ActorId(UUID("00000000-0000-4000-8000-000000000a01")))


# duplicate-code: this acceptance proof keeps deterministic command construction local
# so transaction-failure diagnostics do not depend on another ticket's test scaffold.
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


async def _initiate(store: PostgresDecisionStore) -> InitiationResult:
    generated = _ids(0xA02, 0xA03, 0xA04)
    return await DecisionInitiationService(
        reader=store,
        store=store,
        now=lambda: START,
        new_uuid=lambda: next(generated),
    ).initiate(
        InitiateDecisionCommand(
            envelope=_envelope(
                operation=0xA05,
                reference="acceptance-rollback-initiate",
                effective_at=START,
            ),
            need_statement="Decide whether to rebalance the portfolio",
            subject=DecisionSubject("Portfolio allocation"),
            scope=DecisionScope.unresolved(),
        )
    )


def _revision(
    *,
    decision_id: InvestmentDecisionId,
    operation_id: OperationId,
    effective_at: datetime,
) -> ReviseDecisionSubjectCommand:
    return ReviseDecisionSubjectCommand(
        envelope=DecisionCommandEnvelope(
            operation_id=operation_id,
            actor_attribution=ACTOR,
            trigger=TriggerProvenance(
                TriggerKind.HUMAN_REQUEST,
                "acceptance-rollback-revise-subject",
            ),
            effective_at=effective_at,
            technical_provenance=_technical("acceptance-rollback-revise-subject"),
            expected_versions=frozenset(
                {ExpectedDecisionVersion(decision_id, DecisionVersion(1))}
            ),
        ),
        decision_id=decision_id,
        subject=DecisionSubject("Rebalanced portfolio allocation"),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
    )


# arid: enable


# duplicate-code: the acceptance test intentionally uses the adapter's established
# transaction-failure seam rather than importing lower-level test-only classes.
# arid: disable
class _FailAfterReceiptStore(PostgresDecisionStore):
    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__(engine)
        self.receipt_write_completed = False

    def _write_completed(self, step: str) -> None:
        if step == "receipt":
            self.receipt_write_completed = True
            raise RuntimeError("injected transaction failure")


# arid: enable


def test_r2_acceptance_failed_decision_transaction_rolls_back_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        failure_at = START + timedelta(minutes=10)
        retry_at = failure_at + timedelta(minutes=10)
        operation_id = OperationId(_uuid(0xA06))

        async with postgres_engine_store(postgres_target) as (engine, store):
            initiation = await _initiate(store)
            decision_id = initiation.decision_id
            command = _revision(
                decision_id=decision_id,
                operation_id=operation_id,
                effective_at=failure_at,
            )

            before_memory = DecisionMemoryService(
                reader=store,
                now=lambda: failure_at,
            )
            before_current = await before_memory.current(decision_id)
            before_history = await before_memory.history(decision_id)

            failing_store = _FailAfterReceiptStore(engine)
            with pytest.raises(PersistenceUnavailable):
                await DecisionOrdinaryWorkService(
                    store=failing_store,
                    now=lambda: failure_at,
                    new_uuid=lambda: _uuid(0xA07),
                ).revise_subject(command)

            assert failing_store.receipt_write_completed
            after_failure_memory = DecisionMemoryService(
                reader=failing_store,
                now=lambda: failure_at,
            )
            after_failure_current = await after_failure_memory.current(decision_id)
            after_failure_history = await after_failure_memory.history(decision_id)
            assert after_failure_current == before_current
            assert (
                after_failure_history.lifecycle_facts == before_history.lifecycle_facts
            )
            assert (
                after_failure_history.relationship_facts
                == before_history.relationship_facts
            )

        async with postgres_engine_store(postgres_target) as (_, restarted_store):
            restarted_memory = DecisionMemoryService(
                reader=restarted_store,
                now=lambda: failure_at,
            )
            restarted_current = await restarted_memory.current(decision_id)
            restarted_history = await restarted_memory.history(decision_id)

            assert restarted_current == before_current
            assert restarted_history.lifecycle_facts == before_history.lifecycle_facts
            assert (
                restarted_history.relationship_facts
                == before_history.relationship_facts
            )
            retried = await DecisionOrdinaryWorkService(
                store=restarted_store,
                now=lambda: retry_at,
                new_uuid=lambda: _uuid(0xA08),
            ).revise_subject(command)

            assert retried.decision_id == decision_id
            assert retried.kind is DecisionMutationResultKind.APPLIED
            assert retried.version == DecisionVersion(2)
            assert not retried.replayed

            final_memory = DecisionMemoryService(
                reader=restarted_store,
                now=lambda: retry_at,
            )
            final_current = await final_memory.current(decision_id)
            final_history = await final_memory.history(decision_id)
            assert final_current.need == before_current.need
            assert final_current.subject == DecisionSubject(
                "Rebalanced portfolio allocation"
            )
            assert final_current.version == DecisionVersion(2)
            assert [type(fact) for fact in final_history.lifecycle_facts] == [
                DecisionInitiated,
                DecisionSubjectRevised,
            ]
            assert final_history.relationship_facts == before_history.relationship_facts

    asyncio.run(scenario())
