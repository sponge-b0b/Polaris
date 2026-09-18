from __future__ import annotations

import asyncio
import inspect
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from polaris.application.decisions import (
    ApplySubstantiveResolutionCommand,
    ContinuityConflict,
    ContinuityDetermination,
    DecisionCommandEnvelope,
    DecisionCommandReadUnavailable,
    DecisionInitiationService,
    DecisionMemoryService,
    DecisionOrdinaryWorkService,
    ExpectedDecisionVersion,
    IdempotencyConflict,
    InitiateDecisionCommand,
    PersistenceUnavailable,
    ReviseDecisionSubjectCommand,
)
from polaris.application.decisions.lifecycle_correction import (
    DecisionLifecycleCorrectionService,
    RecordDecisionLifecycleCorrectionCommand,
)
from polaris.application.decisions.relationships import (
    AttachOmittedRenewalLineageCommand,
    CorrectDecisionRelationshipCommand,
    DecisionRelationshipCorrectionService,
    DecisionRelationshipService,
    EstablishSupersessionCommand,
    RenewalPredecessor,
    RenewDecisionCommand,
    SupersessionTarget,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionApplicability,
    DecisionContinuity,
    DecisionLifecycleCorrectionBasis,
    DecisionLifecycleCorrectionEffect,
    DecisionLifecycleFactId,
    DecisionRelationshipBasisRole,
    DecisionRelationshipCorrectionBasis,
    DecisionRelationshipCorrectionEffect,
    DecisionRelationshipFactId,
    DecisionRelationshipNotKnownAtCutoff,
    DecisionRelationshipState,
    DecisionRelationshipType,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    HumanInvestmentDecisionEffect,
    InvestmentDecisionId,
    OperationId,
    RenewedFromRelationshipBasis,
    SupersedesRelationshipBasis,
    TechnicalProvenance,
    TriggerKind,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
    interpret_relationship,
)
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    create_postgres_engine,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    decision_needs,
    investment_decision_command_receipts,
    investment_decision_lifecycle_facts,
    investment_decision_relationships,
    investment_decisions,
)

from .conftest import PostgresTestTarget

BASE = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)


def _actor() -> KnownActorAttribution:
    return KnownActorAttribution(ActorId(uuid4()))


def _envelope(
    *,
    operation_id: OperationId,
    effective_at: datetime,
    versions: dict[InvestmentDecisionId, DecisionVersion] | None = None,
    reference: str = "relationship-test",
) -> DecisionCommandEnvelope:
    return DecisionCommandEnvelope(
        operation_id=operation_id,
        actor_attribution=_actor(),
        trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, reference),
        effective_at=effective_at,
        technical_provenance=TechnicalProvenance(),
        expected_versions=frozenset(
            ExpectedDecisionVersion(identity, version)
            for identity, version in (versions or {}).items()
        ),
    )


async def _create_decision(
    store: PostgresDecisionStore,
    *,
    recorded_at: datetime,
    label: str,
) -> InvestmentDecisionId:
    candidates = await store.find_unresolved_continuity_candidates(known_at=recorded_at)
    identities = iter((uuid4(), uuid4(), uuid4()))
    result = await DecisionInitiationService(
        reader=store,
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: next(identities),
    ).initiate(
        InitiateDecisionCommand(
            envelope=_envelope(
                operation_id=OperationId(uuid4()),
                effective_at=recorded_at,
                reference=f"init-{label}",
            ),
            need_statement=f"Need {label}",
            subject=DecisionSubject(f"Decision {label}"),
            scope=DecisionScope.unresolved(),
            continuity=(
                ContinuityDetermination.create_new(f"independent {label}")
                if candidates
                else None
            ),
        )
    )
    return result.decision_id


class _ConcurrentCandidateReadStore(PostgresDecisionStore):
    def __init__(self, engine: AsyncEngine, barrier: asyncio.Barrier) -> None:
        super().__init__(engine)
        self._barrier = barrier

    async def find_unresolved_continuity_candidates(
        self, *, known_at: datetime
    ) -> tuple[InvestmentDecisionId, ...]:
        candidates = await super().find_unresolved_continuity_candidates(
            known_at=known_at
        )
        await self._barrier.wait()
        return candidates


async def _version(
    store: PostgresDecisionStore,
    identity: InvestmentDecisionId,
    at: datetime,
) -> DecisionVersion:
    state = await store.load_decision_for_command(identity, known_at=at)
    assert state is not None
    return state.decision.version


async def _resolve(
    store: PostgresDecisionStore,
    identity: InvestmentDecisionId,
    *,
    recorded_at: datetime,
) -> tuple[DecisionVersion, UUID]:
    fact_id = uuid4()
    version = await _version(store, identity, recorded_at)
    result = await DecisionOrdinaryWorkService(
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: fact_id,
    ).apply_substantive_resolution(
        ApplySubstantiveResolutionCommand(
            _envelope(
                operation_id=OperationId(uuid4()),
                effective_at=recorded_at,
                versions={identity: version},
                reference="resolve",
            ),
            identity,
            TrustedHumanInvestmentDecisionBasis(
                "human-resolution",
                HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
            ),
        )
    )
    return result.version, fact_id


async def _supersede(
    store: PostgresDecisionStore,
    *,
    source: InvestmentDecisionId,
    targets: tuple[InvestmentDecisionId, ...],
    recorded_at: datetime,
    operation_id: OperationId | None = None,
    fact_ids: tuple[UUID, ...] | None = None,
    reference: str = "supersede",
    relationship_effective_at: datetime | None = None,
):
    versions = {
        identity: await _version(store, identity, recorded_at)
        for identity in (source, *targets)
    }
    operation = operation_id or OperationId(uuid4())
    ids = iter(fact_ids or tuple(uuid4() for _ in targets))
    command = EstablishSupersessionCommand(
        envelope=_envelope(
            operation_id=operation,
            effective_at=recorded_at,
            versions=versions,
            reference=reference,
        ),
        source_decision_id=source,
        targets=tuple(
            SupersessionTarget(
                target,
                SupersedesRelationshipBasis((f"{reference}-{index}",)),
                relationship_effective_at or recorded_at,
            )
            for index, target in enumerate(targets)
        ),
    )
    result = await DecisionRelationshipService(
        reader=store,
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: next(ids),
    ).establish_supersession(command)
    return command, result


def test_many_to_many_supersession_round_trips_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        store = PostgresDecisionStore(engine)
        try:
            source_a = await _create_decision(store, recorded_at=BASE, label="source-a")
            target_a = await _create_decision(
                store, recorded_at=BASE + timedelta(minutes=1), label="target-a"
            )
            target_b = await _create_decision(
                store, recorded_at=BASE + timedelta(minutes=2), label="target-b"
            )
            source_b = await _create_decision(
                store, recorded_at=BASE + timedelta(minutes=3), label="source-b"
            )
            first_at = BASE + timedelta(hours=1)
            _, first = await _supersede(
                store,
                source=source_a,
                targets=(target_a, target_b),
                recorded_at=first_at,
            )
            assert len(first.relationship_fact_ids) == 2
            assert await _version(store, source_a, first_at) == DecisionVersion(2)
            assert await _version(store, target_a, first_at) == DecisionVersion(2)
            assert await _version(store, target_b, first_at) == DecisionVersion(2)

            second_at = first_at + timedelta(minutes=5)
            _, second = await _supersede(
                store,
                source=source_b,
                targets=(target_a,),
                recorded_at=second_at,
            )
            assert len(second.relationship_fact_ids) == 1
            assert await _version(store, target_a, second_at) == DecisionVersion(3)

            memory = DecisionMemoryService(reader=store, now=lambda: second_at)
            current = await memory.current(target_a)
            assert current.applicability is DecisionApplicability.NON_OPERATIVE
            assert current.version == DecisionVersion(3)
            assert len(current.lifecycle_interpretation.support_fact_ids) == 1
            lineage = await memory.lineage(target_a, known_at=second_at)
            assert len(lineage) == 2
            assert {item.state for item in lineage} == {
                DecisionRelationshipState.SUPPORTED
            }
        finally:
            await engine.dispose()

        restarted_engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        restarted = PostgresDecisionStore(restarted_engine)
        try:
            memory = DecisionMemoryService(reader=restarted, now=lambda: second_at)
            current = await memory.current(target_a)
            assert current.version == DecisionVersion(3)
            assert current.applicability is DecisionApplicability.NON_OPERATIVE
            assert len(await memory.lineage(target_a, known_at=second_at)) == 2
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())


def test_relationship_version_projection_drift_fails_closed(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        store = PostgresDecisionStore(engine)
        try:
            source = await _create_decision(store, recorded_at=BASE, label="source")
            target = await _create_decision(
                store, recorded_at=BASE + timedelta(minutes=1), label="target"
            )
            relationship_at = BASE + timedelta(hours=1)
            await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=relationship_at,
            )
            assert await _version(store, target, relationship_at) == DecisionVersion(2)

            async with engine.begin() as connection:
                await connection.execute(
                    investment_decisions.update()
                    .where(investment_decisions.c.decision_id == target.value)
                    .values(decision_version=99)
                )

            with pytest.raises(DecisionCommandReadUnavailable):
                await store.load_current_decision_state(
                    target, known_at=relationship_at
                )
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_replay_conflict_and_equivalent_support_are_distinct(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        store = PostgresDecisionStore(engine)
        try:
            source = await _create_decision(store, recorded_at=BASE, label="source")
            target = await _create_decision(
                store, recorded_at=BASE + timedelta(minutes=1), label="target"
            )
            at = BASE + timedelta(hours=1)
            operation = OperationId(uuid4())
            first_fact = uuid4()
            command, first = await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=at,
                operation_id=operation,
                fact_ids=(first_fact,),
                reference="same-request",
            )

            await engine.dispose()
            engine = create_postgres_engine(
                postgres_target.database_url, schema=postgres_target.schema
            )
            store = PostgresDecisionStore(engine)
            replay = await DecisionRelationshipService(
                reader=store,
                store=store,
                now=lambda: at,
                new_uuid=uuid4,
            ).establish_supersession(command)
            assert replay.replayed is True
            assert replay.relationship_fact_ids == first.relationship_fact_ids
            assert await _version(store, target, at) == DecisionVersion(2)

            changed = EstablishSupersessionCommand(
                envelope=command.envelope,
                source_decision_id=source,
                targets=(
                    SupersessionTarget(
                        target,
                        SupersedesRelationshipBasis(("changed-basis",)),
                        at,
                    ),
                ),
            )
            with pytest.raises(IdempotencyConflict):
                await DecisionRelationshipService(
                    reader=store,
                    store=store,
                    now=lambda: at,
                ).establish_supersession(changed)

            second_at = at + timedelta(minutes=1)
            second_fact = uuid4()
            _, second = await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=second_at,
                fact_ids=(second_fact,),
                reference="equivalent-support",
                relationship_effective_at=at,
            )
            assert second.relationship_fact_ids != first.relationship_fact_ids
            assert await _version(store, target, second_at) == DecisionVersion(3)
            lineage = await DecisionMemoryService(
                reader=store, now=lambda: second_at
            ).lineage(target, known_at=second_at)
            assert len(lineage) == 1
            assert lineage[0].state is DecisionRelationshipState.SUPPORTED
            assert lineage[0].support_fact_ids == frozenset(
                {
                    DecisionRelationshipFactId(first_fact),
                    DecisionRelationshipFactId(second_fact),
                }
            )
            assert {
                contribution.relationship_fact_id
                for contribution in lineage[0].basis_contributions
                if contribution.role is DecisionRelationshipBasisRole.RELATIONSHIP
            } == {
                DecisionRelationshipFactId(first_fact),
                DecisionRelationshipFactId(second_fact),
            }
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_initiation_rejects_relationship_operation_id_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        store = PostgresDecisionStore(engine)
        try:
            source = await _create_decision(store, recorded_at=BASE, label="source")
            target = await _create_decision(
                store,
                recorded_at=BASE + timedelta(minutes=1),
                label="target",
            )
            relationship_at = BASE + timedelta(hours=1)
            operation_id = OperationId(uuid4())
            await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=relationship_at,
                operation_id=operation_id,
            )
        finally:
            await engine.dispose()

        restarted_engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        restarted = PostgresDecisionStore(restarted_engine)
        initiation_at = relationship_at + timedelta(minutes=1)
        identities = iter((uuid4(), uuid4(), uuid4()))
        command = InitiateDecisionCommand(
            envelope=_envelope(
                operation_id=operation_id,
                effective_at=initiation_at,
                reference="reuse-relationship-operation",
            ),
            need_statement="Start a different unresolved choice",
            subject=DecisionSubject("A different unresolved choice"),
            scope=DecisionScope.unresolved(),
            continuity=ContinuityDetermination.create_new(
                "A distinct unresolved choice"
            ),
        )
        try:
            with pytest.raises(IdempotencyConflict):
                await DecisionInitiationService(
                    reader=restarted,
                    store=restarted,
                    now=lambda: initiation_at,
                    new_uuid=lambda: next(identities),
                ).initiate(command)
            async with restarted_engine.connect() as connection:
                decision_count = await connection.scalar(
                    select(func.count()).select_from(investment_decisions)
                )
                receipt_count = await connection.scalar(
                    select(func.count()).select_from(
                        investment_decision_command_receipts
                    )
                )
            assert decision_count == 2
            assert receipt_count == 3
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())


def test_qualification_gap_ages_without_synthetic_version_and_restores(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        store = PostgresDecisionStore(engine)
        try:
            source = await _create_decision(store, recorded_at=BASE, label="source")
            target = await _create_decision(
                store, recorded_at=BASE + timedelta(minutes=1), label="target"
            )
            base_at = BASE + timedelta(hours=1)
            base_fact = uuid4()
            _, established = await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=base_at,
                fact_ids=(base_fact,),
            )
            assert established.versioned_decision_ids == {source, target}

            qualify_at = base_at + timedelta(minutes=10)
            replacement_at = qualify_at + timedelta(hours=1)
            qualify_fact = uuid4()
            versions = {
                source: await _version(store, source, qualify_at),
                target: await _version(store, target, qualify_at),
            }
            qualified = await DecisionRelationshipCorrectionService(
                store=store,
                now=lambda: qualify_at,
                new_uuid=lambda: qualify_fact,
            ).correct(
                CorrectDecisionRelationshipCommand(
                    envelope=_envelope(
                        operation_id=OperationId(uuid4()),
                        effective_at=qualify_at,
                        versions=versions,
                        reference="qualify-gap",
                    ),
                    target_relationship_fact_id=DecisionRelationshipFactId(base_fact),
                    effect=DecisionRelationshipCorrectionEffect.QUALIFY,
                    correction_effective_at=qualify_at,
                    correction_basis=DecisionRelationshipCorrectionBasis(
                        ("qualification",)
                    ),
                    replacement_relationship_effective_at=replacement_at,
                    replacement_relationship_basis=SupersedesRelationshipBasis(
                        ("replacement",)
                    ),
                )
            )
            assert qualified.versioned_decision_ids == {source, target}
            assert await _version(store, target, qualify_at) == DecisionVersion(3)

            async with engine.connect() as connection:
                persisted_qualify = (
                    (
                        await connection.execute(
                            select(investment_decision_relationships).where(
                                investment_decision_relationships.c.relationship_fact_id
                                == qualify_fact
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
            assert persisted_qualify["target_relationship_fact_id"] == base_fact
            assert persisted_qualify["effective_at"] == qualify_at
            assert persisted_qualify["positive_claim_effective_at"] == replacement_at
            assert persisted_qualify["positive_basis"] is not None
            assert persisted_qualify["correction_basis"] is not None

            memory = DecisionMemoryService(reader=store, now=lambda: qualify_at)
            gap = await memory.lineage(
                target, effective_at=qualify_at, known_at=qualify_at
            )
            assert len(gap) == 1
            assert gap[0].state is DecisionRelationshipState.NOT_EFFECTIVE
            assert gap[0].support_fact_ids == {DecisionRelationshipFactId(qualify_fact)}
            assert (await memory.current(target)).applicability is (
                DecisionApplicability.OPERATIVE
            )

            aged_memory = DecisionMemoryService(
                reader=store, now=lambda: replacement_at
            )
            aged = await aged_memory.current(target)
            assert aged.applicability is DecisionApplicability.NON_OPERATIVE
            assert aged.version == DecisionVersion(3)
            supported = await aged_memory.lineage(
                target, effective_at=replacement_at, known_at=replacement_at
            )
            assert supported[0].state is DecisionRelationshipState.SUPPORTED

            restore_at = replacement_at + timedelta(minutes=10)
            restored = await DecisionRelationshipCorrectionService(
                store=store,
                now=lambda: restore_at,
                new_uuid=uuid4,
            ).correct(
                CorrectDecisionRelationshipCommand(
                    envelope=_envelope(
                        operation_id=OperationId(uuid4()),
                        effective_at=restore_at,
                        versions={
                            source: await _version(store, source, restore_at),
                            target: await _version(store, target, restore_at),
                        },
                        reference="restore-qualification",
                    ),
                    target_relationship_fact_id=DecisionRelationshipFactId(
                        qualify_fact
                    ),
                    effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
                    correction_effective_at=restore_at,
                    correction_basis=DecisionRelationshipCorrectionBasis(("restore",)),
                )
            )
            assert restored.versioned_decision_ids == {source, target}
            assert await _version(store, target, restore_at) == DecisionVersion(4)
            final_lineage = await DecisionMemoryService(
                reader=store, now=lambda: restore_at
            ).lineage(target, known_at=restore_at)
            assert final_lineage[0].state is DecisionRelationshipState.SUPPORTED
            raw_history = await DecisionMemoryService(
                reader=store, now=lambda: restore_at
            ).history(target, known_at=restore_at)
            assert {
                fact.metadata.relationship_fact_id
                for fact in raw_history.relationship_facts
            } >= {
                DecisionRelationshipFactId(base_fact),
                DecisionRelationshipFactId(qualify_fact),
            }
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_renewal_persists_admission_evidence_and_survives_later_endpoint_change(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        store = PostgresDecisionStore(engine)
        try:
            predecessor = await _create_decision(
                store, recorded_at=BASE, label="predecessor"
            )
            resolved_at = BASE + timedelta(minutes=30)
            predecessor_version, resolution_fact = await _resolve(
                store, predecessor, recorded_at=resolved_at
            )
            renewal_at = BASE + timedelta(hours=1)
            identities = iter((uuid4(), uuid4(), uuid4(), uuid4()))
            renewal = await DecisionRelationshipService(
                reader=store,
                store=store,
                now=lambda: renewal_at,
                new_uuid=lambda: next(identities),
            ).renew(
                RenewDecisionCommand(
                    envelope=_envelope(
                        operation_id=OperationId(uuid4()),
                        effective_at=renewal_at,
                        versions={predecessor: predecessor_version},
                        reference="renewal",
                    ),
                    need_statement="Renew the resolved choice",
                    subject=DecisionSubject("Renewed choice"),
                    scope=DecisionScope.unresolved(),
                    predecessors=(
                        RenewalPredecessor(
                            predecessor,
                            RenewedFromRelationshipBasis(("renewal-basis",)),
                        ),
                    ),
                )
            )
            assert renewal.new_decision_id is not None
            source = renewal.new_decision_id
            assert await _version(store, source, renewal_at) == DecisionVersion(1)
            assert await _version(store, predecessor, renewal_at) == DecisionVersion(3)

            async with engine.connect() as connection:
                persisted = (
                    (
                        await connection.execute(
                            select(investment_decision_relationships).where(
                                investment_decision_relationships.c.relationship_fact_id
                                == renewal.relationship_fact_ids[0].value
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
            evidence = persisted["admission_evidence"]
            assert evidence["known_at"] == renewal_at.isoformat()
            assert evidence["renewal_predecessor"]["episode_start"] == (
                renewal_at.isoformat()
            )
            assert (
                evidence["renewal_predecessor"]["target_at_claim"][
                    "lifecycle_disposition"
                ]
                == "substantively_resolved"
            )

            correction_at = renewal_at + timedelta(minutes=15)
            await DecisionLifecycleCorrectionService(
                store=store,
                now=lambda: correction_at,
                new_uuid=uuid4,
            ).record_lifecycle_correction(
                RecordDecisionLifecycleCorrectionCommand(
                    envelope=_envelope(
                        operation_id=OperationId(uuid4()),
                        effective_at=correction_at,
                        versions={
                            predecessor: await _version(
                                store, predecessor, correction_at
                            )
                        },
                        reference="later-endpoint-correction",
                    ),
                    decision_id=predecessor,
                    target_fact_id=DecisionLifecycleFactId(resolution_fact),
                    effect=DecisionLifecycleCorrectionEffect.DISCONFIRM,
                    correction_basis=DecisionLifecycleCorrectionBasis(
                        "later-endpoint-correction"
                    ),
                )
            )
            lineage = await DecisionMemoryService(
                reader=store, now=lambda: correction_at
            ).lineage(source, known_at=correction_at)
            assert len(lineage) == 1
            assert lineage[0].state is DecisionRelationshipState.SUPPORTED
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_ordinary_and_renewal_initiation_share_one_continuity_guard(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        store = PostgresDecisionStore(engine)
        try:
            predecessor = await _create_decision(
                store, recorded_at=BASE, label="predecessor"
            )
            initiation_at = BASE + timedelta(hours=1)
            predecessor_version, _ = await _resolve(
                store,
                predecessor,
                recorded_at=initiation_at - timedelta(minutes=30),
            )
            concurrent = _ConcurrentCandidateReadStore(engine, asyncio.Barrier(2))

            ordinary_ids = iter((uuid4(), uuid4(), uuid4()))
            ordinary = DecisionInitiationService(
                reader=concurrent,
                store=concurrent,
                now=lambda: initiation_at,
                new_uuid=lambda: next(ordinary_ids),
            ).initiate(
                InitiateDecisionCommand(
                    envelope=_envelope(
                        operation_id=OperationId(uuid4()),
                        effective_at=initiation_at,
                        reference="concurrent-ordinary-initiation",
                    ),
                    need_statement="Start a new ordinary choice",
                    subject=DecisionSubject("Ordinary concurrent choice"),
                    scope=DecisionScope.unresolved(),
                )
            )

            renewal_ids = iter((uuid4(), uuid4(), uuid4(), uuid4()))
            renewal = DecisionRelationshipService(
                reader=concurrent,
                store=concurrent,
                now=lambda: initiation_at,
                new_uuid=lambda: next(renewal_ids),
            ).renew(
                RenewDecisionCommand(
                    envelope=_envelope(
                        operation_id=OperationId(uuid4()),
                        effective_at=initiation_at,
                        versions={predecessor: predecessor_version},
                        reference="concurrent-renewal-initiation",
                    ),
                    need_statement="Renew the resolved choice",
                    subject=DecisionSubject("Renewal concurrent choice"),
                    scope=DecisionScope.unresolved(),
                    predecessors=(
                        RenewalPredecessor(
                            predecessor,
                            RenewedFromRelationshipBasis(("renewal-basis",)),
                        ),
                    ),
                )
            )

            outcomes = await asyncio.gather(
                ordinary,
                renewal,
                return_exceptions=True,
            )
            assert sum(not isinstance(item, Exception) for item in outcomes) == 1
            assert sum(isinstance(item, ContinuityConflict) for item in outcomes) == 1
            async with engine.connect() as connection:
                decision_count = await connection.scalar(
                    select(func.count()).select_from(investment_decisions)
                )
            assert decision_count == 2
        finally:
            await engine.dispose()

    asyncio.run(scenario())


class _FailAfterRenewalWriteStore(PostgresDecisionStore):
    def __init__(self, engine: AsyncEngine, fail_step: str) -> None:
        super().__init__(engine)
        self._fail_step = fail_step

    def _write_completed(self, step: str) -> None:
        if step == self._fail_step:
            raise RuntimeError(f"injected renewal failure after {step}")


@pytest.mark.parametrize(
    "fail_step",
    ["relationship_fact", "relationship_projection", "receipt"],
)
def test_renewal_initial_lineage_failure_rolls_back_entire_creation(
    postgres_target: PostgresTestTarget,
    fail_step: str,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        setup = PostgresDecisionStore(engine)
        try:
            predecessor = await _create_decision(
                setup, recorded_at=BASE, label=f"rollback-{fail_step}"
            )
            renewal_at = BASE + timedelta(hours=1)
            predecessor_version, _ = await _resolve(
                setup,
                predecessor,
                recorded_at=renewal_at - timedelta(minutes=30),
            )

            tables = (
                decision_needs,
                investment_decisions,
                investment_decision_lifecycle_facts,
                investment_decision_relationships,
                investment_decision_command_receipts,
            )
            async with engine.connect() as connection:
                before_counts = []
                for table in tables:
                    before_counts.append(
                        await connection.scalar(select(func.count()).select_from(table))
                    )
            before_history = await setup.load_decision_history(predecessor)
            before_relationships = await setup.load_relationship_history()

            failing = _FailAfterRenewalWriteStore(engine, fail_step)
            identities = iter((uuid4(), uuid4(), uuid4(), uuid4()))
            with pytest.raises(PersistenceUnavailable):
                await DecisionRelationshipService(
                    reader=failing,
                    store=failing,
                    now=lambda: renewal_at,
                    new_uuid=lambda: next(identities),
                ).renew(
                    RenewDecisionCommand(
                        envelope=_envelope(
                            operation_id=OperationId(uuid4()),
                            effective_at=renewal_at,
                            versions={predecessor: predecessor_version},
                            reference=f"rollback-renewal-{fail_step}",
                        ),
                        need_statement="Renew after the resolved predecessor",
                        subject=DecisionSubject("Renewed choice"),
                        scope=DecisionScope.unresolved(),
                        predecessors=(
                            RenewalPredecessor(
                                predecessor,
                                RenewedFromRelationshipBasis(
                                    (f"rollback-{fail_step}",)
                                ),
                            ),
                        ),
                    )
                )

            async with engine.connect() as connection:
                after_counts = []
                for table in tables:
                    after_counts.append(
                        await connection.scalar(select(func.count()).select_from(table))
                    )
            assert after_counts == before_counts
            assert await setup.load_decision_history(predecessor) == before_history
            assert await setup.load_relationship_history() == before_relationships
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_late_omitted_renewal_lineage_uses_existing_decision_and_need(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        store = PostgresDecisionStore(engine)
        try:
            predecessor = await _create_decision(
                store, recorded_at=BASE, label="resolved-predecessor"
            )
            await _resolve(
                store,
                predecessor,
                recorded_at=BASE + timedelta(minutes=10),
            )
            source_at = BASE + timedelta(minutes=20)
            source = await _create_decision(
                store, recorded_at=source_at, label="existing-source"
            )
            before = await store.load_decision_for_command(source, known_at=source_at)
            assert before is not None
            need_id = before.decision.need_id

            attach_at = BASE + timedelta(hours=1)
            result = await DecisionRelationshipService(
                reader=store,
                store=store,
                now=lambda: attach_at,
                new_uuid=uuid4,
            ).attach_omitted_renewal_lineage(
                AttachOmittedRenewalLineageCommand(
                    envelope=_envelope(
                        operation_id=OperationId(uuid4()),
                        effective_at=attach_at,
                        versions={
                            source: await _version(store, source, attach_at),
                            predecessor: await _version(store, predecessor, attach_at),
                        },
                        reference="late-renewal-lineage",
                    ),
                    source_decision_id=source,
                    predecessors=(
                        RenewalPredecessor(
                            predecessor,
                            RenewedFromRelationshipBasis(("late-lineage",)),
                        ),
                    ),
                )
            )
            assert len(result.relationship_fact_ids) == 1
            after = await store.load_decision_for_command(source, known_at=attach_at)
            assert after is not None
            assert after.decision.need_id == need_id
            assert len(after.decision.history) == len(before.decision.history)
            lineage = await DecisionMemoryService(
                reader=store, now=lambda: attach_at
            ).lineage(source, known_at=attach_at)
            assert len(lineage) == 1
            assert lineage[0].state is DecisionRelationshipState.SUPPORTED
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_relationship_ports_expose_no_database_types() -> None:
    for name in (
        "get_relationship_receipt",
        "load_relationship_state",
        "commit_relationship",
        "load_relationship_history",
        "load_current_decision_state",
    ):
        signature = str(inspect.signature(getattr(PostgresDecisionStore, name)))
        assert "sqlalchemy" not in signature.lower()
        assert "asyncpg" not in signature.lower()


def test_four_state_relationship_history_round_trips(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        store = PostgresDecisionStore(engine)
        try:
            source = await _create_decision(store, recorded_at=BASE, label="source")
            target = await _create_decision(
                store, recorded_at=BASE + timedelta(minutes=1), label="target"
            )
            before = await store.load_relationship_history()
            assert before == ()
            with pytest.raises(DecisionRelationshipNotKnownAtCutoff):
                interpret_relationship(
                    before,
                    source_decision_id=source,
                    relationship_type=DecisionRelationshipType.SUPERSEDES,
                    target_decision_id=target,
                    effective_at=BASE + timedelta(minutes=2),
                    known_at=BASE + timedelta(minutes=2),
                )

            base_at = BASE + timedelta(hours=1)
            base_fact = uuid4()
            await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=base_at,
                fact_ids=(base_fact,),
                relationship_effective_at=base_at,
            )

            withdraw_at = base_at + timedelta(minutes=10)
            withdraw_fact = uuid4()
            await DecisionRelationshipCorrectionService(
                store=store,
                now=lambda: withdraw_at,
                new_uuid=lambda: withdraw_fact,
            ).correct(
                CorrectDecisionRelationshipCommand(
                    envelope=_envelope(
                        operation_id=OperationId(uuid4()),
                        effective_at=withdraw_at,
                        versions={
                            source: await _version(store, source, withdraw_at),
                            target: await _version(store, target, withdraw_at),
                        },
                        reference="withdraw-base",
                    ),
                    target_relationship_fact_id=DecisionRelationshipFactId(base_fact),
                    effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
                    correction_effective_at=withdraw_at,
                    correction_basis=DecisionRelationshipCorrectionBasis(
                        ("withdraw-base",)
                    ),
                )
            )
            withdrawn = await DecisionMemoryService(
                reader=store, now=lambda: withdraw_at
            ).lineage(target, known_at=withdraw_at)
            assert withdrawn[0].state is DecisionRelationshipState.WITHDRAWN

            second_recorded = withdraw_at + timedelta(minutes=10)
            second_effective = base_at + timedelta(minutes=1)
            second_fact = uuid4()
            await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=second_recorded,
                fact_ids=(second_fact,),
                relationship_effective_at=second_effective,
                reference="second-claim",
            )
            supported = await DecisionMemoryService(
                reader=store, now=lambda: second_recorded
            ).lineage(target, known_at=second_recorded)
            assert supported[0].state is DecisionRelationshipState.SUPPORTED

            third_recorded = second_recorded + timedelta(minutes=10)
            third_effective = base_at + timedelta(minutes=2)
            third_fact = uuid4()
            await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=third_recorded,
                fact_ids=(third_fact,),
                relationship_effective_at=third_effective,
                reference="conflicting-claim",
            )
            contested = await DecisionMemoryService(
                reader=store, now=lambda: third_recorded
            ).lineage(target, known_at=third_recorded)
            assert contested[0].state is DecisionRelationshipState.CONTESTED

            before_late_claim = await DecisionMemoryService(
                reader=store, now=lambda: second_recorded
            ).lineage(
                target,
                effective_at=second_recorded,
                known_at=second_recorded,
            )
            assert before_late_claim[0].state is DecisionRelationshipState.SUPPORTED
            assert before_late_claim[0].known_at == second_recorded
            assert before_late_claim[0].support_fact_ids == {
                DecisionRelationshipFactId(withdraw_fact),
                DecisionRelationshipFactId(second_fact),
            }
            assert DecisionRelationshipFactId(third_fact) not in (
                before_late_claim[0].support_fact_ids
            )
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_ordinary_mutation_advances_from_durable_relationship_version(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        store = PostgresDecisionStore(engine)
        source = await _create_decision(store, recorded_at=BASE, label="source")
        target = await _create_decision(
            store, recorded_at=BASE + timedelta(minutes=1), label="target"
        )
        relationship_at = BASE + timedelta(hours=1)
        await _supersede(
            store,
            source=source,
            targets=(target,),
            recorded_at=relationship_at,
            reference="version-witness",
        )
        assert await _version(store, source, relationship_at) == DecisionVersion(2)

        mutation_at = relationship_at + timedelta(minutes=5)
        mutation_fact = uuid4()
        result = await DecisionOrdinaryWorkService(
            store=store,
            now=lambda: mutation_at,
            new_uuid=lambda: mutation_fact,
        ).revise_subject(
            ReviseDecisionSubjectCommand(
                _envelope(
                    operation_id=OperationId(uuid4()),
                    effective_at=mutation_at,
                    versions={source: DecisionVersion(2)},
                    reference="post-relationship-subject",
                ),
                source,
                DecisionSubject("Decision source after relationship version"),
                DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
        assert result.version == DecisionVersion(3)
        state = await store.load_decision_for_command(source, known_at=mutation_at)
        assert state is not None
        assert state.decision.version == DecisionVersion(3)
        assert [fact.metadata.sequence.value for fact in state.decision.history] == [
            1,
            2,
        ]
        assert [
            fact.metadata.decision_version.value for fact in state.decision.history
        ] == [1, 3]
        await engine.dispose()

        restarted_engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        restarted = PostgresDecisionStore(restarted_engine)
        try:
            restarted_state = await restarted.load_decision_for_command(
                source, known_at=mutation_at
            )
            assert restarted_state is not None
            assert restarted_state.decision.version == DecisionVersion(3)
            assert [
                fact.metadata.sequence.value
                for fact in restarted_state.decision.history
            ] == [1, 2]
            assert [
                fact.metadata.decision_version.value
                for fact in restarted_state.decision.history
            ] == [1, 3]
            relationship_history = await restarted.load_relationship_history()
            assert any(
                getattr(fact, "source_decision_id", None) == source
                for fact in relationship_history
            )
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())


def test_malformed_persisted_correction_lineage_fails_closed(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url, schema=postgres_target.schema
        )
        store = PostgresDecisionStore(engine)
        try:
            source = await _create_decision(store, recorded_at=BASE, label="source")
            target = await _create_decision(
                store, recorded_at=BASE + timedelta(minutes=1), label="target"
            )
            unrelated = await _create_decision(
                store, recorded_at=BASE + timedelta(minutes=2), label="unrelated"
            )
            base_at = BASE + timedelta(hours=1)
            base_fact = uuid4()
            await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=base_at,
                fact_ids=(base_fact,),
            )

            correction_at = base_at + timedelta(minutes=10)
            correction_fact = uuid4()
            await DecisionRelationshipCorrectionService(
                store=store,
                now=lambda: correction_at,
                new_uuid=lambda: correction_fact,
            ).correct(
                CorrectDecisionRelationshipCommand(
                    envelope=_envelope(
                        operation_id=OperationId(uuid4()),
                        effective_at=correction_at,
                        versions={
                            source: await _version(store, source, correction_at),
                            target: await _version(store, target, correction_at),
                        },
                        reference="valid-correction",
                    ),
                    target_relationship_fact_id=DecisionRelationshipFactId(base_fact),
                    effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
                    correction_effective_at=correction_at,
                    correction_basis=DecisionRelationshipCorrectionBasis(
                        ("valid-correction",)
                    ),
                )
            )

            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "ALTER TABLE investment_decision_relationships "
                        "DISABLE TRIGGER "
                        "trg_investment_decision_relationships_immutable"
                    )
                )
                await connection.execute(
                    investment_decision_relationships.update()
                    .where(
                        investment_decision_relationships.c.relationship_fact_id
                        == correction_fact
                    )
                    .values(source_decision_id=unrelated.value)
                )
                await connection.execute(
                    text(
                        "ALTER TABLE investment_decision_relationships "
                        "ENABLE TRIGGER "
                        "trg_investment_decision_relationships_immutable"
                    )
                )

            with pytest.raises(DecisionCommandReadUnavailable):
                await store.load_relationship_history()
        finally:
            await engine.dispose()

    asyncio.run(scenario())
