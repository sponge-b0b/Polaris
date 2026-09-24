from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

from polaris.application.decisions import (
    ContinuityDetermination,
    DecisionCommandEnvelope,
    DecisionInitiationService,
    DecisionMemoryService,
    ExpectedDecisionVersion,
    InitiateDecisionCommand,
)
from polaris.application.decisions.relationships import (
    DecisionRelationshipResult,
    DecisionRelationshipService,
    EstablishSupersessionCommand,
    SupersessionTarget,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionApplicability,
    DecisionRelationshipState,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    InvestmentDecisionId,
    OperationId,
    SupersedesRelationshipBasis,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
)
from polaris.domain.decisions.facts import DecisionLifecycleFact
from polaris.infrastructure.persistence.postgresql import PostgresDecisionStore

from .conftest import PostgresTestTarget, postgres_engine_store

START = datetime(2026, 9, 24, 22, 0, tzinfo=UTC)
ACTOR = KnownActorAttribution(ActorId(UUID("00000000-0000-4000-8000-000000000e01")))


# duplicate-code: this acceptance proof owns deterministic identity, provenance, and
# initiation fixtures independently of lower-level relationship/version tests; sharing
# them would couple ticket-level proof to another semantic layer.
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
    versions: dict[InvestmentDecisionId, DecisionVersion] | None = None,
) -> DecisionCommandEnvelope:
    return DecisionCommandEnvelope(
        operation_id=OperationId(_uuid(operation)),
        actor_attribution=ACTOR,
        trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, reference),
        effective_at=effective_at,
        technical_provenance=_technical(reference),
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
    ids: tuple[int, int, int, int],
) -> InvestmentDecisionId:
    candidates = await store.find_unresolved_continuity_candidates(known_at=recorded_at)
    generated = _ids(*ids[:3])
    result = await DecisionInitiationService(
        reader=store,
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: next(generated),
    ).initiate(
        InitiateDecisionCommand(
            envelope=_envelope(
                operation=ids[3],
                reference=f"acceptance-{label}",
                effective_at=recorded_at,
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


async def _version(
    store: PostgresDecisionStore,
    decision_id: InvestmentDecisionId,
    at: datetime,
) -> DecisionVersion:
    state = await store.load_decision_for_command(decision_id, known_at=at)
    assert state is not None
    return state.decision.version


async def _supersede(
    store: PostgresDecisionStore,
    *,
    source: InvestmentDecisionId,
    targets: tuple[InvestmentDecisionId, ...],
    recorded_at: datetime,
    effective_at: datetime,
    operation: int,
    fact_ids: tuple[int, ...],
    reference: str,
) -> DecisionRelationshipResult:
    versions = {
        identity: await _version(store, identity, recorded_at)
        for identity in (source, *targets)
    }
    command = EstablishSupersessionCommand(
        envelope=_envelope(
            operation=operation,
            reference=reference,
            effective_at=recorded_at,
            versions=versions,
        ),
        source_decision_id=source,
        targets=tuple(
            SupersessionTarget(
                target,
                SupersedesRelationshipBasis((f"{reference}-{index}",)),
                effective_at,
            )
            for index, target in enumerate(targets)
        ),
    )
    generated = _ids(*fact_ids)
    return await DecisionRelationshipService(
        reader=store,
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: next(generated),
    ).establish_supersession(command)


# arid: enable


async def _current_versions(
    store: PostgresDecisionStore,
    ids: tuple[InvestmentDecisionId, ...],
    at: datetime,
) -> dict[InvestmentDecisionId, DecisionVersion]:
    memory = DecisionMemoryService(reader=store, now=lambda: at)
    return {identity: (await memory.current(identity)).version for identity in ids}


async def _lifecycle_histories(
    store: PostgresDecisionStore,
    ids: tuple[InvestmentDecisionId, ...],
    at: datetime,
) -> dict[InvestmentDecisionId, tuple[DecisionLifecycleFact, ...]]:
    memory = DecisionMemoryService(reader=store, now=lambda: at)
    return {
        identity: (await memory.history(identity, known_at=at)).lifecycle_facts
        for identity in ids
    }


def test_r2_acceptance_relationship_meaning_versions_endpoints_once_without_lifecycle(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_engine_store(postgres_target) as (_, store):
            source = await _create_decision(
                store,
                recorded_at=START,
                label="version-source",
                ids=(0xE02, 0xE03, 0xE04, 0xE05),
            )
            target_a = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=1),
                label="version-target-a",
                ids=(0xE06, 0xE07, 0xE08, 0xE09),
            )
            target_b = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=2),
                label="version-target-b",
                ids=(0xE0A, 0xE0B, 0xE0C, 0xE0D),
            )
            ids = (source, target_a, target_b)
            relationship_at = START + timedelta(minutes=30)

            before_versions = await _current_versions(store, ids, relationship_at)
            before_histories = await _lifecycle_histories(store, ids, relationship_at)

            first = await _supersede(
                store,
                source=source,
                targets=(target_a, target_b),
                recorded_at=relationship_at,
                effective_at=relationship_at,
                operation=0xE0E,
                fact_ids=(0xE0F, 0xE10),
                reference="version-multi-target",
            )
            assert first.versioned_decision_ids == frozenset(ids)

            after_first = await _current_versions(store, ids, relationship_at)
            for identity in ids:
                assert after_first[identity] == DecisionVersion(
                    before_versions[identity].value + 1
                )
            assert await _lifecycle_histories(store, ids, relationship_at) == (
                before_histories
            )

            memory = DecisionMemoryService(reader=store, now=lambda: relationship_at)
            target_a_before_support = await memory.current(target_a)
            target_a_lineage_before_support = await memory.lineage(
                target_a,
                effective_at=relationship_at,
                known_at=relationship_at,
            )
            assert target_a_before_support.applicability is (
                DecisionApplicability.NON_OPERATIVE
            )
            assert len(target_a_lineage_before_support) == 1
            assert (
                target_a_lineage_before_support[0].state
                is DecisionRelationshipState.SUPPORTED
            )
            assert len(target_a_lineage_before_support[0].support_fact_ids) == 1

            support_at = relationship_at + timedelta(minutes=5)
            second = await _supersede(
                store,
                source=source,
                targets=(target_a,),
                recorded_at=support_at,
                effective_at=relationship_at,
                operation=0xE11,
                fact_ids=(0xE12,),
                reference="version-support-only",
            )
            assert second.versioned_decision_ids == frozenset({source, target_a})

            after_support = await _current_versions(store, ids, support_at)
            assert after_support[source] == DecisionVersion(
                after_first[source].value + 1
            )
            assert after_support[target_a] == DecisionVersion(
                after_first[target_a].value + 1
            )
            assert after_support[target_b] == after_first[target_b]
            assert (
                await _lifecycle_histories(store, ids, support_at) == before_histories
            )

            memory = DecisionMemoryService(reader=store, now=lambda: support_at)
            target_a_after_support = await memory.current(target_a)
            target_a_lineage_after_support = await memory.lineage(
                target_a,
                effective_at=support_at,
                known_at=support_at,
            )
            assert target_a_after_support.applicability is (
                target_a_before_support.applicability
            )
            assert (
                target_a_lineage_after_support[0].state
                is target_a_lineage_before_support[0].state
            )
            assert len(target_a_lineage_after_support[0].support_fact_ids) == 2

            before_restart = {
                identity: await memory.current(identity) for identity in ids
            }
            histories_before_restart = await _lifecycle_histories(
                store, ids, support_at
            )

        async with postgres_engine_store(postgres_target) as (_, restarted):
            restarted_memory = DecisionMemoryService(
                reader=restarted,
                now=lambda: support_at,
            )
            for identity in ids:
                assert (
                    await restarted_memory.current(identity)
                    == (before_restart[identity])
                )
            assert await _lifecycle_histories(restarted, ids, support_at) == (
                histories_before_restart
            )

    asyncio.run(scenario())


def test_r2_acceptance_future_relationship_and_queries_do_not_synthesize_version(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        source_at = START
        async with postgres_engine_store(postgres_target) as (_, store):
            source = await _create_decision(
                store,
                recorded_at=source_at,
                label="future-version-source",
                ids=(0xE20, 0xE21, 0xE22, 0xE23),
            )
            target = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=1),
                label="future-version-target",
                ids=(0xE24, 0xE25, 0xE26, 0xE27),
            )
            ids = (source, target)
            recorded_at = START + timedelta(minutes=20)
            future_at = recorded_at + timedelta(days=1)

            before_versions = await _current_versions(store, ids, recorded_at)
            before_histories = await _lifecycle_histories(store, ids, recorded_at)

            result = await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=recorded_at,
                effective_at=future_at,
                operation=0xE28,
                fact_ids=(0xE29,),
                reference="future-version-noop",
            )
            assert result.versioned_decision_ids == frozenset()

            at_recording = await _current_versions(store, ids, recorded_at)
            assert at_recording == before_versions
            assert (
                await _lifecycle_histories(store, ids, recorded_at) == before_histories
            )

            memory = DecisionMemoryService(reader=store, now=lambda: recorded_at)
            target_at_recording = await memory.current(target)
            lineage_at_recording = await memory.lineage(
                target,
                effective_at=recorded_at,
                known_at=recorded_at,
            )
            assert target_at_recording.applicability is DecisionApplicability.OPERATIVE
            assert len(lineage_at_recording) == 1
            assert (
                lineage_at_recording[0].state is DecisionRelationshipState.NOT_EFFECTIVE
            )
            assert lineage_at_recording[0].support_fact_ids == frozenset()
            assert len((await memory.history(target)).relationship_facts) == 1

        aged_at = future_at + timedelta(minutes=1)
        async with postgres_engine_store(postgres_target) as (_, restarted):
            aged_memory = DecisionMemoryService(
                reader=restarted,
                now=lambda: aged_at,
            )
            aged_source = await aged_memory.current(source)
            aged_target = await aged_memory.current(target)
            assert aged_source.version == before_versions[source]
            assert aged_target.version == before_versions[target]
            assert aged_target.applicability is DecisionApplicability.NON_OPERATIVE

            aged_lineage = await aged_memory.lineage(
                target,
                effective_at=aged_at,
                known_at=aged_at,
            )
            assert len(aged_lineage) == 1
            assert aged_lineage[0].state is DecisionRelationshipState.SUPPORTED
            assert len(aged_lineage[0].support_fact_ids) == 1

            assert await _lifecycle_histories(restarted, ids, aged_at) == (
                before_histories
            )
            assert (await aged_memory.current(source)).version == (
                before_versions[source]
            )
            assert (await aged_memory.current(target)).version == (
                before_versions[target]
            )

    asyncio.run(scenario())
