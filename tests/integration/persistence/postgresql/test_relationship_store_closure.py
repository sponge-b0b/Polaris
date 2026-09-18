from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from polaris.application.decisions import (
    DecisionCommandEnvelope,
    DecisionMemoryService,
    ExpectedDecisionVersion,
    PersistenceUnavailable,
    RelationshipConflict,
    RelationshipCycle,
    RelationshipCycleSafetyIndeterminate,
)
from polaris.application.decisions.relationships import (
    CorrectDecisionRelationshipCommand,
    CorrectDecisionRelationshipSetCommand,
    DecisionRelationshipCorrectionService,
    DecisionRelationshipService,
    EstablishSupersessionCommand,
    RelationshipCorrectionMember,
    RenewalPredecessor,
    RenewDecisionCommand,
    SupersessionTarget,
)
from polaris.application.decisions.relationships import (
    DecisionRelationshipState as DecisionRelationshipStoreState,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionLifecycleDisposition,
    DecisionLifecycleLineageCycle,
    DecisionRelationshipCorrected,
    DecisionRelationshipCorrectionBasis,
    DecisionRelationshipCorrectionEffect,
    DecisionRelationshipFact,
    DecisionRelationshipFactId,
    DecisionRelationshipState,
    DecisionScope,
    DecisionSubject,
    DeterminateDecisionLifecycleInterpretation,
    OperationId,
    RenewedFromRelationshipBasis,
    SupersedesRelationshipBasis,
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
from polaris.infrastructure.persistence.postgresql import (
    relationship_store as relationship_store_module,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    investment_decision_command_receipts,
    investment_decision_relationships,
    investment_decisions,
)

from .conftest import PostgresTestTarget, postgres_engine_store, postgres_row_counts
from .test_relationship_store import (
    BASE,
    _create_decision,
    _envelope,
    _resolve,
    _supersede,
    _version,
)


class _ConcurrentRelationshipStateStore(PostgresDecisionStore):
    def __init__(self, engine: AsyncEngine, barrier: asyncio.Barrier) -> None:
        super().__init__(engine)
        self._barrier = barrier

    async def load_relationship_state(
        self, *, known_at: datetime
    ) -> DecisionRelationshipStoreState:
        state = await super().load_relationship_state(known_at=known_at)
        await self._barrier.wait()
        return state


class _FailAfterRelationshipWriteStore(PostgresDecisionStore):
    def __init__(self, engine: AsyncEngine, fail_step: str) -> None:
        super().__init__(engine)
        self._fail_step = fail_step

    def _write_completed(self, step: str) -> None:
        if step == self._fail_step:
            raise RuntimeError(f"injected relationship failure after {step}")


async def _qualify_base(
    store: PostgresDecisionStore,
    *,
    source: object,
    target: object,
    base_fact_id: UUID,
    recorded_at: object,
    replacement_effective_at: object,
    reference: str,
) -> UUID:
    from datetime import datetime

    from polaris.domain.decisions import InvestmentDecisionId

    if not isinstance(source, InvestmentDecisionId):
        raise TypeError("source must be InvestmentDecisionId")
    if not isinstance(target, InvestmentDecisionId):
        raise TypeError("target must be InvestmentDecisionId")
    if not isinstance(recorded_at, datetime):
        raise TypeError("recorded_at must be datetime")
    if not isinstance(replacement_effective_at, datetime):
        raise TypeError("replacement_effective_at must be datetime")

    fact_id = uuid4()
    result = await DecisionRelationshipCorrectionService(
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: fact_id,
        # duplicate-code: graph falsifiers require local proof shape.
        # arid: disable
    ).correct(
        CorrectDecisionRelationshipCommand(
            envelope=_envelope(
                operation_id=OperationId(uuid4()),
                # arid: enable
                effective_at=recorded_at,
                versions={
                    source: await _version(store, source, recorded_at),
                    target: await _version(store, target, recorded_at),
                },
                reference=reference,
            ),
            target_relationship_fact_id=DecisionRelationshipFactId(base_fact_id),
            effect=DecisionRelationshipCorrectionEffect.QUALIFY,
            correction_effective_at=recorded_at,
            correction_basis=DecisionRelationshipCorrectionBasis(
                (f"{reference}-correction",)
            ),
            replacement_relationship_effective_at=replacement_effective_at,
            replacement_relationship_basis=SupersedesRelationshipBasis(
                (f"{reference}-replacement",)
            ),
        )
    )
    assert result.relationship_fact_ids == (DecisionRelationshipFactId(fact_id),)
    return fact_id


def test_competing_persisted_corrections_reconstruct_contested(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_engine_store(postgres_target) as (_, store):
            source = await _create_decision(
                store, recorded_at=BASE, label="correction-source"
            )
            target = await _create_decision(
                store,
                recorded_at=BASE + timedelta(minutes=1),
                label="correction-target",
            )
            base_at = BASE + timedelta(hours=1)
            base_fact_id = uuid4()
            # duplicate-code: graph falsifiers require local proof shape.
            # arid: disable
            await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=base_at,
                # arid: enable
                fact_ids=(base_fact_id,),
                relationship_effective_at=base_at,
                reference="correction-base",
            )

            first_at = base_at + timedelta(minutes=10)
            first_fact_id = await _qualify_base(
                store,
                source=source,
                target=target,
                base_fact_id=base_fact_id,
                recorded_at=first_at,
                replacement_effective_at=base_at,
                reference="first-qualification",
            )
            second_at = first_at + timedelta(minutes=10)
            second_fact_id = await _qualify_base(
                # duplicate-code: graph falsifiers require local proof shape.
                # arid: disable
                store,
                source=source,
                target=target,
                base_fact_id=base_fact_id,
                # arid: enable
                recorded_at=second_at,
                replacement_effective_at=base_at + timedelta(minutes=1),
                reference="second-qualification",
            )

        async with postgres_engine_store(postgres_target) as (_, restarted):
            lineage = await DecisionMemoryService(
                reader=restarted, now=lambda: second_at
            ).lineage(target, known_at=second_at)
            assert len(lineage) == 1
            assert lineage[0].state is DecisionRelationshipState.CONTESTED
            assert {
                DecisionRelationshipFactId(first_fact_id),
                DecisionRelationshipFactId(second_fact_id),
            } <= lineage[0].support_fact_ids

    asyncio.run(scenario())


def test_resolved_target_supersession_preserves_lifecycle_history(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_engine_store(postgres_target) as (_, store):
            source = await _create_decision(
                store, recorded_at=BASE, label="resolved-supersession-source"
            )
            target = await _create_decision(
                store,
                recorded_at=BASE + timedelta(minutes=1),
                label="resolved-supersession-target",
            )
            resolved_at = BASE + timedelta(minutes=30)
            await _resolve(store, target, recorded_at=resolved_at)
            history_before = await store.load_decision_history(target)
            assert history_before is not None

            superseded_at = BASE + timedelta(hours=1)
            # duplicate-code: graph falsifiers require local proof shape.
            # arid: disable
            await _supersede(
                store,
                source=source,
                targets=(target,),
                # arid: enable
                recorded_at=superseded_at,
                relationship_effective_at=superseded_at,
                reference="resolved-target-supersession",
            )

            history_after = await store.load_decision_history(target)
            assert history_after == history_before
            view = await DecisionMemoryService(
                reader=store, now=lambda: superseded_at
            ).current(target)
            assert isinstance(
                view.lifecycle_interpretation,
                DeterminateDecisionLifecycleInterpretation,
            )
            assert (
                view.lifecycle_interpretation.disposition
                is DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
            )
            lineage = await DecisionMemoryService(
                reader=store, now=lambda: superseded_at
            ).lineage(target, known_at=superseded_at)
            assert len(lineage) == 1
            assert lineage[0].state is DecisionRelationshipState.SUPPORTED

    asyncio.run(scenario())


def test_relationship_fact_provenance_round_trips_separately(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        actor = KnownActorAttribution(ActorId(uuid4()))
        trigger = TriggerProvenance(
            TriggerKind.HUMAN_REQUEST,
            "relationship-provenance-trigger",
        )
        technical = TechnicalProvenance(
            {
                TechnicalReference(
                    TechnicalReferenceKind.TRACE,
                    "relationship-provenance-trace",
                )
            }
        )
        fact_id = uuid4()
        operation_id = OperationId(uuid4())
        recorded_at = BASE + timedelta(hours=1)

        async with postgres_engine_store(postgres_target) as (_, store):
            source = await _create_decision(
                store, recorded_at=BASE, label="provenance-source"
            )
            target = await _create_decision(
                store,
                recorded_at=BASE + timedelta(minutes=1),
                label="provenance-target",
            )
            command = EstablishSupersessionCommand(
                envelope=DecisionCommandEnvelope(
                    operation_id=operation_id,
                    actor_attribution=actor,
                    trigger=trigger,
                    effective_at=recorded_at,
                    technical_provenance=technical,
                    expected_versions=frozenset(
                        (
                            ExpectedDecisionVersion(
                                source, await _version(store, source, recorded_at)
                            ),
                            ExpectedDecisionVersion(
                                target, await _version(store, target, recorded_at)
                            ),
                        )
                    ),
                ),
                # duplicate-code: graph falsifiers require local proof shape.
                # arid: disable
                source_decision_id=source,
                targets=(
                    SupersessionTarget(
                        target,
                        # arid: enable
                        SupersedesRelationshipBasis(("provenance-basis",)),
                        recorded_at,
                    ),
                    # duplicate-code: graph falsifiers require local proof shape.
                    # arid: disable
                ),
            )
            result = await DecisionRelationshipService(
                reader=store,
                store=store,
                now=lambda: recorded_at,
                # arid: enable
                new_uuid=lambda: fact_id,
            ).establish_supersession(command)
            assert result.relationship_fact_ids == (
                DecisionRelationshipFactId(fact_id),
            )

        async with postgres_engine_store(postgres_target) as (_, restarted):
            history = await restarted.load_relationship_history()
            persisted = next(
                fact
                for fact in history
                if fact.metadata.relationship_fact_id
                == DecisionRelationshipFactId(fact_id)
            )
            assert isinstance(persisted, DecisionRelationshipFact)
            assert persisted.metadata.operation_id == operation_id
            assert persisted.metadata.actor_attribution == actor
            assert persisted.metadata.trigger == trigger
            assert persisted.metadata.technical_provenance == technical

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "fail_step",
    ("relationship_fact", "relationship_projection", "receipt"),
)
def test_many_target_supersession_failure_rolls_back_complete_command(
    postgres_target: PostgresTestTarget,
    fail_step: str,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        setup = PostgresDecisionStore(engine)
        try:
            source = await _create_decision(
                setup, recorded_at=BASE, label=f"rollback-source-{fail_step}"
            )
            first = await _create_decision(
                setup,
                recorded_at=BASE + timedelta(minutes=1),
                label=f"rollback-first-{fail_step}",
            )
            second = await _create_decision(
                setup,
                recorded_at=BASE + timedelta(minutes=2),
                label=f"rollback-second-{fail_step}",
            )
            command_at = BASE + timedelta(hours=1)
            tables = (
                investment_decisions,
                investment_decision_relationships,
                investment_decision_command_receipts,
            )
            before_counts = await postgres_row_counts(engine, *tables)
            before_versions = {
                identity: await _version(setup, identity, command_at)
                for identity in (source, first, second)
            }

            failing = _FailAfterRelationshipWriteStore(engine, fail_step)
            with pytest.raises(PersistenceUnavailable):
                await _supersede(
                    failing,
                    source=source,
                    targets=(first, second),
                    recorded_at=command_at,
                    reference=f"rollback-{fail_step}",
                )

            after_counts = await postgres_row_counts(engine, *tables)
            assert after_counts == before_counts
            assert await setup.load_relationship_history() == ()
            assert {
                identity: await _version(setup, identity, command_at)
                for identity in (source, first, second)
            } == before_versions
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_atomic_correction_set_persists_same_command_ancestry_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        base_at = BASE + timedelta(hours=1)
        correction_at = base_at + timedelta(minutes=10)
        base_fact_id = uuid4()
        generated = (uuid4(), uuid4())
        async with postgres_engine_store(postgres_target) as (_, store):
            source = await _create_decision(store, recorded_at=BASE, label="set-source")
            target = await _create_decision(
                store, recorded_at=BASE + timedelta(minutes=1), label="set-target"
            )
            # duplicate-code: graph falsifiers require local proof shape.
            # arid: disable
            await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=base_at,
                fact_ids=(base_fact_id,),
                # arid: enable
                reference="set-base",
            )
            command = CorrectDecisionRelationshipSetCommand(
                # duplicate-code: graph falsifiers require local proof shape.
                # arid: disable
                envelope=_envelope(
                    operation_id=OperationId(uuid4()),
                    effective_at=correction_at,
                    versions={
                        source: await _version(store, source, correction_at),
                        target: await _version(store, target, correction_at),
                    },
                    # arid: enable
                    reference="atomic-correction-set",
                ),
                corrections=(
                    RelationshipCorrectionMember(
                        local_id="restore",
                        target="withdraw",
                        effect=DecisionRelationshipCorrectionEffect.QUALIFY,
                        correction_effective_at=correction_at,
                        correction_basis=DecisionRelationshipCorrectionBasis(
                            ("restore-correction",)
                        ),
                        replacement_relationship_effective_at=base_at,
                        replacement_relationship_basis=SupersedesRelationshipBasis(
                            ("restore-relationship",)
                        ),
                    ),
                    RelationshipCorrectionMember(
                        local_id="withdraw",
                        target=DecisionRelationshipFactId(base_fact_id),
                        effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
                        correction_effective_at=correction_at,
                        correction_basis=DecisionRelationshipCorrectionBasis(
                            ("withdraw-base",)
                        ),
                    ),
                ),
            )
            result = await DecisionRelationshipCorrectionService(
                store=store,
                now=lambda: correction_at,
                new_uuid=iter(generated).__next__,
            ).correct_set(command)
            assert set(result.relationship_fact_ids) == {
                DecisionRelationshipFactId(identity) for identity in generated
            }

        async with postgres_engine_store(postgres_target) as (_, restarted):
            history = await restarted.load_relationship_history()
            corrections = tuple(
                fact
                for fact in history
                if isinstance(fact, DecisionRelationshipCorrected)
            )
            assert len(corrections) == 2
            parent = next(
                fact
                for fact in corrections
                if fact.target_relationship_fact_id
                == DecisionRelationshipFactId(base_fact_id)
            )
            child = next(fact for fact in corrections if fact is not parent)
            assert child.target_relationship_fact_id == (
                parent.metadata.relationship_fact_id
            )
            lineage = await DecisionMemoryService(
                reader=restarted, now=lambda: correction_at
            ).lineage(target, known_at=correction_at)
            assert lineage[0].state is DecisionRelationshipState.SUPPORTED

    asyncio.run(scenario())


def test_postgres_rejects_self_direct_and_indirect_lineage_cycles(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_engine_store(postgres_target) as (_, store):
            first = await _create_decision(store, recorded_at=BASE, label="cycle-a")
            second = await _create_decision(
                store, recorded_at=BASE + timedelta(minutes=1), label="cycle-b"
            )
            third = await _create_decision(
                store, recorded_at=BASE + timedelta(minutes=2), label="cycle-c"
            )
            at = BASE + timedelta(hours=1)

            with pytest.raises(RelationshipCycle):
                await _supersede(
                    store,
                    source=first,
                    targets=(first,),
                    recorded_at=at,
                    reference="self-cycle",
                )
            assert await store.load_relationship_history() == ()

            await _supersede(
                store,
                source=first,
                targets=(second,),
                recorded_at=at + timedelta(minutes=1),
                reference="direct-forward",
            )
            with pytest.raises(RelationshipCycle):
                await _supersede(
                    store,
                    source=second,
                    targets=(first,),
                    recorded_at=at + timedelta(minutes=2),
                    reference="direct-return",
                )
            assert len(await store.load_relationship_history()) == 1

            await _supersede(
                store,
                source=second,
                targets=(third,),
                recorded_at=at + timedelta(minutes=3),
                reference="indirect-forward",
            )
            with pytest.raises(RelationshipCycle):
                await _supersede(
                    store,
                    source=third,
                    targets=(first,),
                    recorded_at=at + timedelta(minutes=4),
                    reference="indirect-return",
                )
            assert len(await store.load_relationship_history()) == 2

    asyncio.run(scenario())


def test_postgres_rejects_mixed_renewal_supersession_cycle(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_engine_store(postgres_target) as (_, store):
            predecessor = await _create_decision(
                store, recorded_at=BASE, label="mixed-predecessor"
            )
            renewal_at = BASE + timedelta(hours=1)
            predecessor_version, _ = await _resolve(
                store,
                predecessor,
                recorded_at=renewal_at - timedelta(minutes=10),
            )
            identities = iter((uuid4(), uuid4(), uuid4(), uuid4()))
            renewed = await DecisionRelationshipService(
                reader=store,
                store=store,
                now=lambda: renewal_at,
                new_uuid=identities.__next__,
                # duplicate-code: graph falsifiers require local proof shape.
                # arid: disable
            ).renew(
                RenewDecisionCommand(
                    envelope=_envelope(
                        operation_id=OperationId(uuid4()),
                        effective_at=renewal_at,
                        versions={predecessor: predecessor_version},
                        # arid: enable
                        reference="mixed-renewal",
                    ),
                    need_statement="Renew the resolved predecessor",
                    subject=DecisionSubject("Renewed mixed-cycle decision"),
                    # duplicate-code: graph falsifiers require local proof shape.
                    # arid: disable
                    scope=DecisionScope.unresolved(),
                    predecessors=(
                        RenewalPredecessor(
                            predecessor,
                            # arid: enable
                            RenewedFromRelationshipBasis(("mixed-renewal",)),
                        ),
                    ),
                    continuity=None,
                )
            )
            assert renewed.new_decision_id is not None

            with pytest.raises(RelationshipCycle):
                await _supersede(
                    store,
                    source=predecessor,
                    targets=(renewed.new_decision_id,),
                    recorded_at=renewal_at + timedelta(minutes=1),
                    reference="mixed-cycle-return",
                )
            assert len(await store.load_relationship_history()) == 1

    asyncio.run(scenario())


def test_known_future_and_contested_positive_cycles_fail_closed(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_engine_store(postgres_target) as (_, store):
            first = await _create_decision(store, recorded_at=BASE, label="future-a")
            second = await _create_decision(
                store, recorded_at=BASE + timedelta(minutes=1), label="future-b"
            )
            recorded_at = BASE + timedelta(hours=1)
            # duplicate-code: graph falsifiers require local proof shape.
            # arid: disable
            await _supersede(
                store,
                source=first,
                targets=(second,),
                # arid: enable
                recorded_at=recorded_at,
                relationship_effective_at=recorded_at + timedelta(days=1),
                reference="known-future-forward",
                # duplicate-code: graph falsifiers require local proof shape.
                # arid: disable
            )
            with pytest.raises(RelationshipCycle):
                await _supersede(
                    store,
                    source=second,
                    targets=(first,),
                    # arid: enable
                    recorded_at=recorded_at + timedelta(minutes=1),
                    reference="known-future-return",
                )

            third = await _create_decision(
                store,
                recorded_at=recorded_at + timedelta(minutes=2),
                label="contest-a",
            )
            fourth = await _create_decision(
                store,
                recorded_at=recorded_at + timedelta(minutes=3),
                label="contest-b",
            )
            base_at = recorded_at + timedelta(minutes=4)
            base_fact_id = uuid4()
            await _supersede(
                store,
                source=third,
                targets=(fourth,),
                recorded_at=base_at,
                fact_ids=(base_fact_id,),
                reference="contest-base",
            )
            first_qualification = base_at + timedelta(minutes=1)
            await _qualify_base(
                store,
                source=third,
                target=fourth,
                base_fact_id=base_fact_id,
                recorded_at=first_qualification,
                replacement_effective_at=base_at,
                reference="contest-first",
            )
            second_qualification = base_at + timedelta(minutes=2)
            # duplicate-code: graph falsifiers require local proof shape.
            # arid: disable
            await _qualify_base(
                store,
                source=third,
                target=fourth,
                base_fact_id=base_fact_id,
                # arid: enable
                recorded_at=second_qualification,
                replacement_effective_at=base_at + timedelta(seconds=1),
                reference="contest-second",
            )
            with pytest.raises(RelationshipCycleSafetyIndeterminate):
                await _supersede(
                    store,
                    source=fourth,
                    targets=(third,),
                    recorded_at=base_at + timedelta(minutes=3),
                    reference="contest-return",
                )

    asyncio.run(scenario())


def test_disjoint_endpoint_graph_race_commits_only_one_safe_edge(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        # duplicate-code: graph falsifiers require local proof shape.
        # arid: disable
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        setup = PostgresDecisionStore(engine)
        try:
            # arid: enable
            first = await _create_decision(setup, recorded_at=BASE, label="race-a")
            second = await _create_decision(
                setup, recorded_at=BASE + timedelta(minutes=1), label="race-b"
            )
            third = await _create_decision(
                setup, recorded_at=BASE + timedelta(minutes=2), label="race-c"
            )
            fourth = await _create_decision(
                setup, recorded_at=BASE + timedelta(minutes=3), label="race-d"
            )
            await _supersede(
                setup,
                source=second,
                targets=(first,),
                recorded_at=BASE + timedelta(hours=1),
                reference="race-existing-left",
            )
            await _supersede(
                setup,
                source=fourth,
                targets=(third,),
                recorded_at=BASE + timedelta(hours=1, minutes=1),
                reference="race-existing-right",
            )

            concurrent = _ConcurrentRelationshipStateStore(engine, asyncio.Barrier(2))
            race_at = BASE + timedelta(hours=2)
            outcomes = await asyncio.gather(
                _supersede(
                    concurrent,
                    source=first,
                    targets=(fourth,),
                    recorded_at=race_at,
                    reference="race-first-to-fourth",
                ),
                _supersede(
                    concurrent,
                    source=third,
                    targets=(second,),
                    recorded_at=race_at,
                    reference="race-third-to-second",
                ),
                return_exceptions=True,
            )
            assert sum(not isinstance(item, Exception) for item in outcomes) == 1
            assert sum(isinstance(item, RelationshipConflict) for item in outcomes) == 1
            assert len(await setup.load_relationship_history()) == 3
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_commit_time_semantic_revalidation_is_not_reported_as_outage(
    postgres_target: PostgresTestTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        async with postgres_engine_store(postgres_target) as (_, store):
            source = await _create_decision(
                store, recorded_at=BASE, label="revalidation-source"
            )
            target = await _create_decision(
                store,
                recorded_at=BASE + timedelta(minutes=1),
                label="revalidation-target",
            )

            def reject_revalidation(*args: object, **kwargs: object) -> str | None:
                del args, kwargs
                raise DecisionLifecycleLineageCycle("commit-time cycle")

            monkeypatch.setattr(
                relationship_store_module,
                "_semantic_revalidation_mismatch",
                reject_revalidation,
            )
            with pytest.raises(RelationshipConflict):
                # duplicate-code: graph falsifiers require local proof shape.
                # arid: disable
                await _supersede(
                    store,
                    source=source,
                    targets=(target,),
                    # arid: enable
                    recorded_at=BASE + timedelta(hours=1),
                    reference="semantic-revalidation",
                )
            assert await store.load_relationship_history() == ()

    asyncio.run(scenario())
