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
    CorrectDecisionRelationshipCommand,
    DecisionRelationshipCorrectionService,
    DecisionRelationshipService,
    EstablishSupersessionCommand,
    SupersessionTarget,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionRelationshipBasisRole,
    DecisionRelationshipCorrected,
    DecisionRelationshipCorrectionBasis,
    DecisionRelationshipCorrectionEffect,
    DecisionRelationshipFact,
    DecisionRelationshipFactId,
    DecisionRelationshipState,
    DecisionRelationshipType,
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
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    create_postgres_engine,
)

from .conftest import PostgresTestTarget, postgres_engine_store

START = datetime(2026, 9, 24, 20, 0, tzinfo=UTC)
ACTOR = KnownActorAttribution(ActorId(UUID("00000000-0000-4000-8000-000000000d01")))


# duplicate-code: this acceptance proof owns deterministic identity, provenance, and
# initiation fixtures independently of lower-level persistence/domain tests; sharing
# them would couple the ticket-level proof to another semantic layer.
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


# arid: enable


async def _version(
    store: PostgresDecisionStore,
    decision_id: InvestmentDecisionId,
    at: datetime,
) -> DecisionVersion:
    state = await store.load_decision_for_command(decision_id, known_at=at)
    assert state is not None
    return state.decision.version


# duplicate-code: base relationship establishment remains local so this acceptance
# module owns the exact business-path identity and version setup it certifies.
# arid: disable
async def _supersede(
    store: PostgresDecisionStore,
    *,
    source: InvestmentDecisionId,
    target: InvestmentDecisionId,
    recorded_at: datetime,
    effective_at: datetime,
    operation: int,
    fact: int,
    reference: str,
) -> DecisionRelationshipFactId:
    versions = {
        source: await _version(store, source, recorded_at),
        target: await _version(store, target, recorded_at),
    }
    result = await DecisionRelationshipService(
        reader=store,
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: _uuid(fact),
    ).establish_supersession(
        EstablishSupersessionCommand(
            envelope=_envelope(
                operation=operation,
                reference=reference,
                effective_at=recorded_at,
                versions=versions,
            ),
            source_decision_id=source,
            targets=(
                SupersessionTarget(
                    target,
                    SupersedesRelationshipBasis((f"{reference}-basis",)),
                    effective_at,
                ),
            ),
        )
    )
    return result.relationship_fact_ids[0]


# arid: enable


async def _correct(
    store: PostgresDecisionStore,
    *,
    source: InvestmentDecisionId,
    target: InvestmentDecisionId,
    target_fact_id: DecisionRelationshipFactId,
    recorded_at: datetime,
    correction_effective_at: datetime,
    operation: int,
    fact: int,
    reference: str,
    effect: DecisionRelationshipCorrectionEffect,
    replacement_effective_at: datetime | None = None,
) -> DecisionRelationshipFactId:
    versions = {
        source: await _version(store, source, recorded_at),
        target: await _version(store, target, recorded_at),
    }
    result = await DecisionRelationshipCorrectionService(
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: _uuid(fact),
    ).correct(
        CorrectDecisionRelationshipCommand(
            envelope=_envelope(
                operation=operation,
                reference=reference,
                effective_at=correction_effective_at,
                versions=versions,
            ),
            target_relationship_fact_id=target_fact_id,
            effect=effect,
            correction_effective_at=correction_effective_at,
            correction_basis=DecisionRelationshipCorrectionBasis(
                (f"{reference}-correction-basis",)
            ),
            replacement_relationship_effective_at=replacement_effective_at,
            replacement_relationship_basis=(
                SupersedesRelationshipBasis((f"{reference}-replacement-basis",))
                if replacement_effective_at is not None
                else None
            ),
        )
    )
    return result.relationship_fact_ids[0]


def _by_id(
    history: tuple[DecisionRelationshipFact | DecisionRelationshipCorrected, ...],
) -> dict[
    DecisionRelationshipFactId,
    DecisionRelationshipFact | DecisionRelationshipCorrected,
]:
    return {fact.metadata.relationship_fact_id: fact for fact in history}


def test_r2_acceptance_relationship_identity_and_recursive_correction_survive_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_engine_store(postgres_target) as (engine, store):
            source = await _create_decision(
                store,
                recorded_at=START,
                label="relationship-source",
                ids=(0xD02, 0xD03, 0xD04, 0xD05),
            )
            target = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=1),
                label="relationship-target",
                ids=(0xD06, 0xD07, 0xD08, 0xD09),
            )

            base_at = START + timedelta(minutes=10)
            base_one = await _supersede(
                store,
                source=source,
                target=target,
                recorded_at=base_at,
                effective_at=base_at,
                operation=0xD0A,
                fact=0xD0B,
                reference="relationship-base-one",
            )
            base_two_recorded = base_at + timedelta(minutes=1)
            base_two = await _supersede(
                store,
                source=source,
                target=target,
                recorded_at=base_two_recorded,
                effective_at=base_at,
                operation=0xD0C,
                fact=0xD0D,
                reference="relationship-base-two",
            )
            assert base_one != base_two
            assert (
                len(
                    {
                        base_one.value,
                        base_two.value,
                        source.value,
                        target.value,
                        _uuid(0xD0A),
                        _uuid(0xD0C),
                    }
                )
                == 6
            )

            memory = DecisionMemoryService(reader=store, now=lambda: base_two_recorded)
            initial_lineage = await memory.lineage(
                target,
                effective_at=base_two_recorded,
                known_at=base_two_recorded,
            )
            assert len(initial_lineage) == 1
            assert initial_lineage[0].state is DecisionRelationshipState.SUPPORTED
            assert initial_lineage[0].support_fact_ids == frozenset(
                {base_one, base_two}
            )
            initial_history = await memory.history(
                target,
                known_at=base_two_recorded,
            )
            initial_by_id = _by_id(initial_history.relationship_facts)
            base_one_before = initial_by_id[base_one]
            base_two_before = initial_by_id[base_two]
            assert isinstance(base_one_before, DecisionRelationshipFact)
            assert isinstance(base_two_before, DecisionRelationshipFact)
            assert base_one_before.source_decision_id == source
            assert base_one_before.target_decision_id == target
            assert base_two_before.source_decision_id == source
            assert base_two_before.target_decision_id == target
            assert (
                base_one_before.relationship_type is DecisionRelationshipType.SUPERSEDES
            )
            assert (
                base_two_before.relationship_type is DecisionRelationshipType.SUPERSEDES
            )

            qualify_recorded = START + timedelta(minutes=30)
            qualify_effective = START + timedelta(minutes=20)
            qualify = await _correct(
                store,
                source=source,
                target=target,
                target_fact_id=base_one,
                recorded_at=qualify_recorded,
                correction_effective_at=qualify_effective,
                operation=0xD0E,
                fact=0xD0F,
                reference="relationship-qualify",
                effect=DecisionRelationshipCorrectionEffect.QUALIFY,
                replacement_effective_at=base_at,
            )
            qualified_lineage = (
                await DecisionMemoryService(
                    reader=store,
                    now=lambda: qualify_recorded,
                ).lineage(
                    target,
                    effective_at=qualify_recorded,
                    known_at=qualify_recorded,
                )
            )[0]
            assert qualified_lineage.state is DecisionRelationshipState.SUPPORTED
            assert qualified_lineage.support_fact_ids == frozenset({qualify, base_two})
            qualify_roles = {
                (item.relationship_fact_id, item.role)
                for item in qualified_lineage.basis_contributions
            }
            assert (qualify, DecisionRelationshipBasisRole.CORRECTION) in qualify_roles
            assert (
                qualify,
                DecisionRelationshipBasisRole.RELATIONSHIP,
            ) in qualify_roles
            assert (
                base_two,
                DecisionRelationshipBasisRole.RELATIONSHIP,
            ) in qualify_roles

            restore_recorded = START + timedelta(minutes=40)
            restore_effective = START + timedelta(minutes=35)
            restore = await _correct(
                store,
                source=source,
                target=target,
                target_fact_id=qualify,
                recorded_at=restore_recorded,
                correction_effective_at=restore_effective,
                operation=0xD10,
                fact=0xD11,
                reference="relationship-restore",
                effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
            )
            before_restart = await DecisionMemoryService(
                reader=store,
                now=lambda: restore_recorded,
            ).history(target, known_at=restore_recorded)
            before_restart_by_id = _by_id(before_restart.relationship_facts)
            assert before_restart_by_id[base_one] == base_one_before
            assert before_restart_by_id[base_two] == base_two_before
            qualify_fact = before_restart_by_id[qualify]
            restore_fact = before_restart_by_id[restore]
            assert isinstance(qualify_fact, DecisionRelationshipCorrected)
            assert isinstance(restore_fact, DecisionRelationshipCorrected)
            assert qualify_fact.target_relationship_fact_id == base_one
            assert restore_fact.target_relationship_fact_id == qualify
            assert qualify_fact.effect is DecisionRelationshipCorrectionEffect.QUALIFY
            assert (
                restore_fact.effect is DecisionRelationshipCorrectionEffect.DISCONFIRM
            )
            assert qualify_fact.correction_effective_at == qualify_effective
            assert qualify_fact.replacement_relationship_effective_at == base_at
            assert qualify_fact.metadata.recorded_at == qualify_recorded
            assert restore_fact.correction_effective_at == restore_effective
            assert restore_fact.metadata.recorded_at == restore_recorded
            assert qualify_fact.metadata.actor_attribution == ACTOR
            assert restore_fact.metadata.actor_attribution == ACTOR
            assert qualify_fact.metadata.operation_id == OperationId(_uuid(0xD0E))
            assert restore_fact.metadata.operation_id == OperationId(_uuid(0xD10))
            assert qualify_fact.metadata.trigger == TriggerProvenance(
                TriggerKind.HUMAN_REQUEST,
                "relationship-qualify",
            )
            assert restore_fact.metadata.trigger == TriggerProvenance(
                TriggerKind.HUMAN_REQUEST,
                "relationship-restore",
            )
            assert qualify_fact.metadata.technical_provenance == _technical(
                "relationship-qualify"
            )
            assert restore_fact.metadata.technical_provenance == _technical(
                "relationship-restore"
            )

            # duplicate-code: this acceptance falsifier keeps its restart boundary
            # explicit; sharing it would couple independent restart semantics proofs.
            # arid: disable
            await engine.dispose()

        restarted_engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        restarted = PostgresDecisionStore(restarted_engine)
        try:
            memory = DecisionMemoryService(
                reader=restarted,
                now=lambda: restore_recorded,
            )
            # arid: enable
            lineage = (
                await memory.lineage(
                    target,
                    effective_at=restore_recorded,
                    known_at=restore_recorded,
                )
            )[0]
            assert lineage.state is DecisionRelationshipState.SUPPORTED
            assert lineage.support_fact_ids == frozenset({base_one, base_two, restore})
            assert {
                (item.relationship_fact_id, item.role)
                for item in lineage.basis_contributions
            } == {
                (base_one, DecisionRelationshipBasisRole.RELATIONSHIP),
                (base_two, DecisionRelationshipBasisRole.RELATIONSHIP),
                (restore, DecisionRelationshipBasisRole.CORRECTION),
            }

            history = await memory.history(target, known_at=restore_recorded)
            history_by_id = _by_id(history.relationship_facts)
            assert set(history_by_id) == {
                base_one,
                base_two,
                qualify,
                restore,
            }
            assert history_by_id[base_one] == base_one_before
            assert history_by_id[base_two] == base_two_before
            assert isinstance(history_by_id[qualify], DecisionRelationshipCorrected)
            assert isinstance(history_by_id[restore], DecisionRelationshipCorrected)
            assert history_by_id[qualify].target_relationship_fact_id == base_one
            assert history_by_id[restore].target_relationship_fact_id == qualify
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())


def test_r2_acceptance_incompatible_corrections_remain_contested_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        # duplicate-code: the contested-support falsifier owns its product setup;
        # sharing this scaffold would couple independent acceptance scenarios.
        # arid: disable
        async with postgres_engine_store(postgres_target) as (engine, store):
            source = await _create_decision(
                store,
                recorded_at=START,
                label="contest-source",
                ids=(0xD20, 0xD21, 0xD22, 0xD23),
            )
            # arid: enable
            target = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=1),
                label="contest-target",
                ids=(0xD24, 0xD25, 0xD26, 0xD27),
            )
            base_at = START + timedelta(minutes=10)
            # duplicate-code: this scenario must establish its own base relationship;
            # sharing the invocation would couple distinct acceptance falsifiers.
            # arid: disable
            base = await _supersede(
                store,
                source=source,
                target=target,
                recorded_at=base_at,
                effective_at=base_at,
                operation=0xD28,
                fact=0xD29,
                reference="contest-base",
            )
            # arid: enable

            first_recorded = START + timedelta(minutes=20)
            first = await _correct(
                store,
                source=source,
                target=target,
                target_fact_id=base,
                recorded_at=first_recorded,
                correction_effective_at=first_recorded,
                operation=0xD2A,
                fact=0xD2B,
                reference="contest-first",
                effect=DecisionRelationshipCorrectionEffect.QUALIFY,
                replacement_effective_at=base_at,
            )
            second_recorded = START + timedelta(minutes=21)
            # duplicate-code: sibling corrections intentionally repeat command shape;
            # a helper/loop would hide the independently supported competing branch.
            # arid: disable
            second = await _correct(
                store,
                source=source,
                target=target,
                target_fact_id=base,
                recorded_at=second_recorded,
                correction_effective_at=first_recorded,
                operation=0xD2C,
                fact=0xD2D,
                reference="contest-second",
                effect=DecisionRelationshipCorrectionEffect.QUALIFY,
                replacement_effective_at=base_at + timedelta(minutes=1),
            )
            # arid: enable
            # duplicate-code: the pre-restart query stays explicit so the acceptance
            # proof independently compares the same semantic cut across restart.
            # arid: disable
            contested = (
                await DecisionMemoryService(
                    reader=store,
                    now=lambda: second_recorded,
                ).lineage(
                    target,
                    effective_at=second_recorded,
                    known_at=second_recorded,
                )
            )[0]
            # arid: enable
            assert contested.state is DecisionRelationshipState.CONTESTED
            assert contested.support_fact_ids == frozenset({first, second})
            assert {
                claim.relationship_effective_at
                for claim in contested.surviving_positive_claims
            } == {
                base_at,
                base_at + timedelta(minutes=1),
            }
            assert {
                item.relationship_fact_id for item in contested.basis_contributions
            } == {first, second}
            assert {item.role for item in contested.basis_contributions} == {
                DecisionRelationshipBasisRole.CORRECTION,
                DecisionRelationshipBasisRole.RELATIONSHIP,
            }

            # duplicate-code: this contested-support proof owns its restart boundary;
            # sharing it would couple independently diagnostic acceptance scenarios.
            # arid: disable
            await engine.dispose()

        restarted_engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        restarted = PostgresDecisionStore(restarted_engine)
        try:
            memory = DecisionMemoryService(
                reader=restarted,
                now=lambda: second_recorded,
            )
            # arid: enable
            lineage = (
                await memory.lineage(
                    target,
                    effective_at=second_recorded,
                    known_at=second_recorded,
                )
            )[0]
            assert lineage.state is DecisionRelationshipState.CONTESTED
            assert lineage.support_fact_ids == frozenset({first, second})
            assert {
                claim.relationship_effective_at
                for claim in lineage.surviving_positive_claims
            } == {
                base_at,
                base_at + timedelta(minutes=1),
            }

            history = await memory.history(target, known_at=second_recorded)
            history_by_id = _by_id(history.relationship_facts)
            assert set(history_by_id) == {base, first, second}
            assert isinstance(history_by_id[base], DecisionRelationshipFact)
            assert isinstance(history_by_id[first], DecisionRelationshipCorrected)
            assert isinstance(history_by_id[second], DecisionRelationshipCorrected)
            assert history_by_id[first].target_relationship_fact_id == base
            assert history_by_id[second].target_relationship_fact_id == base
            assert history_by_id[first].metadata.recorded_at < (
                history_by_id[second].metadata.recorded_at
            )
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())
