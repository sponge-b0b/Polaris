from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from polaris.application.decisions import (
    ApplySubstantiveResolutionCommand,
    ContinuityDetermination,
    DecisionCommandEnvelope,
    DecisionInitiationService,
    DecisionMemoryService,
    DecisionOrdinaryWorkService,
    ExpectedDecisionVersion,
    InitiateDecisionCommand,
    RelationshipCycle,
    RelationshipCycleSafetyIndeterminate,
)
from polaris.application.decisions.relationships import (
    AttachOmittedRenewalLineageCommand,
    CorrectDecisionRelationshipCommand,
    CorrectDecisionRelationshipSetCommand,
    DecisionRelationshipCorrectionService,
    DecisionRelationshipResult,
    DecisionRelationshipService,
    EstablishSupersessionCommand,
    RelationshipCorrectionMember,
    RenewalPredecessor,
    SupersessionTarget,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionRelationshipCorrectionBasis,
    DecisionRelationshipCorrectionEffect,
    DecisionRelationshipFactId,
    DecisionRelationshipState,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    HumanInvestmentDecisionEffect,
    InvestmentDecisionId,
    OperationId,
    RenewedFromRelationshipBasis,
    SupersedesRelationshipBasis,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
)
from polaris.infrastructure.persistence.postgresql import PostgresDecisionStore

from .conftest import PostgresTestTarget, postgres_engine_store

START = datetime(2026, 9, 25, 0, 0, tzinfo=UTC)
ACTOR = KnownActorAttribution(ActorId(UUID("00000000-0000-4000-8000-000000000f01")))


# duplicate-code: this acceptance proof owns deterministic identity, provenance, and
# initiation fixtures independently of lower-level graph/persistence tests; sharing
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


async def _version(
    store: PostgresDecisionStore,
    decision_id: InvestmentDecisionId,
    at: datetime,
) -> DecisionVersion:
    state = await store.load_decision_for_command(decision_id, known_at=at)
    assert state is not None
    return state.decision.version


async def _resolve(
    store: PostgresDecisionStore,
    decision_id: InvestmentDecisionId,
    *,
    recorded_at: datetime,
    fact: int,
    operation: int,
) -> None:
    await DecisionOrdinaryWorkService(
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: _uuid(fact),
    ).apply_substantive_resolution(
        ApplySubstantiveResolutionCommand(
            _envelope(
                operation=operation,
                reference="acceptance-cycle-resolve",
                effective_at=recorded_at,
                versions={
                    decision_id: await _version(store, decision_id, recorded_at),
                },
            ),
            decision_id,
            TrustedHumanInvestmentDecisionBasis(
                "acceptance-cycle-resolve",
                HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
            ),
        )
    )


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
) -> DecisionRelationshipResult:
    replacement_basis = (
        SupersedesRelationshipBasis((f"{reference}-replacement",))
        if replacement_effective_at is not None
        else None
    )
    return await DecisionRelationshipCorrectionService(
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: _uuid(fact),
    ).correct(
        CorrectDecisionRelationshipCommand(
            envelope=_envelope(
                operation=operation,
                reference=reference,
                effective_at=correction_effective_at,
                versions={
                    source: await _version(store, source, recorded_at),
                    target: await _version(store, target, recorded_at),
                },
            ),
            target_relationship_fact_id=target_fact_id,
            effect=effect,
            correction_effective_at=correction_effective_at,
            correction_basis=DecisionRelationshipCorrectionBasis(
                (f"{reference}-correction",)
            ),
            replacement_relationship_effective_at=replacement_effective_at,
            replacement_relationship_basis=replacement_basis,
        )
    )


# arid: enable


async def _versions(
    store: PostgresDecisionStore,
    identities: tuple[InvestmentDecisionId, ...],
    at: datetime,
) -> dict[InvestmentDecisionId, DecisionVersion]:
    return {identity: await _version(store, identity, at) for identity in identities}


async def _assert_supersession_rejected(
    store: PostgresDecisionStore,
    *,
    source: InvestmentDecisionId,
    target: InvestmentDecisionId,
    at: datetime,
    operation: int,
    fact: int,
    reference: str,
    expected: type[Exception],
    effective_at: datetime | None = None,
) -> None:
    identities = (source,) if source == target else (source, target)
    before_history = await store.load_relationship_history()
    before_versions = await _versions(store, identities, at)
    targets = (target,)
    with pytest.raises(expected):
        await _supersede(
            store,
            source=source,
            targets=targets,
            recorded_at=at,
            effective_at=at if effective_at is None else effective_at,
            operation=operation,
            fact_ids=(fact,),
            reference=reference,
        )
    assert await store.load_relationship_history() == before_history
    assert await _versions(store, identities, at) == before_versions
    assert await store.get_relationship_receipt(OperationId(_uuid(operation))) is None


def test_r2_acceptance_supported_and_mixed_cycles_fail_closed_without_partial_commit(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_engine_store(postgres_target) as (_, store):
            first = await _create_decision(
                store,
                recorded_at=START,
                label="cycle-first",
                ids=(0xF02, 0xF03, 0xF04, 0xF05),
            )
            second = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=1),
                label="cycle-second",
                ids=(0xF06, 0xF07, 0xF08, 0xF09),
            )
            third = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=2),
                label="cycle-third",
                ids=(0xF0A, 0xF0B, 0xF0C, 0xF0D),
            )
            at = START + timedelta(minutes=30)

            await _assert_supersession_rejected(
                store,
                source=first,
                target=first,
                at=at,
                operation=0xF0E,
                fact=0xF0F,
                reference="acceptance-self-cycle",
                expected=RelationshipCycle,
            )

            # duplicate-code: direct and indirect graph edges stay explicit at the
            # acceptance seam so the cycle topology remains independently diagnostic.
            # arid: disable
            await _supersede(
                store,
                source=first,
                targets=(second,),
                recorded_at=at + timedelta(minutes=1),
                effective_at=at + timedelta(minutes=1),
                operation=0xF10,
                fact_ids=(0xF11,),
                reference="acceptance-direct-forward",
            )

            direct_at = at + timedelta(minutes=2)
            await _assert_supersession_rejected(
                store,
                source=second,
                target=first,
                at=direct_at,
                operation=0xF12,
                fact=0xF13,
                reference="acceptance-direct-return",
                expected=RelationshipCycle,
            )

            await _supersede(
                store,
                source=second,
                targets=(third,),
                recorded_at=at + timedelta(minutes=3),
                effective_at=at + timedelta(minutes=3),
                operation=0xF14,
                fact_ids=(0xF15,),
                reference="acceptance-indirect-forward",
            )
            # arid: enable

            indirect_at = at + timedelta(minutes=4)
            await _assert_supersession_rejected(
                store,
                source=third,
                target=first,
                at=indirect_at,
                operation=0xF16,
                fact=0xF17,
                reference="acceptance-indirect-return",
                expected=RelationshipCycle,
            )

            predecessor_at = START + timedelta(hours=2)
            predecessor = await _create_decision(
                store,
                recorded_at=predecessor_at,
                label="mixed-predecessor",
                ids=(0xF18, 0xF19, 0xF1A, 0xF1B),
            )
            resolved_at = predecessor_at + timedelta(minutes=10)
            await _resolve(
                store,
                predecessor,
                recorded_at=resolved_at,
                fact=0xF1C,
                operation=0xF1D,
            )
            source_at = resolved_at + timedelta(minutes=10)
            renewed_source = await _create_decision(
                store,
                recorded_at=source_at,
                label="mixed-source",
                ids=(0xF1E, 0xF1F, 0xF20, 0xF21),
            )
            attach_at = source_at + timedelta(minutes=10)
            attach_fact = _uuid(0xF22)
            await DecisionRelationshipService(
                reader=store,
                store=store,
                now=lambda: attach_at,
                new_uuid=lambda: attach_fact,
            ).attach_omitted_renewal_lineage(
                AttachOmittedRenewalLineageCommand(
                    envelope=_envelope(
                        operation=0xF23,
                        reference="acceptance-mixed-renewal",
                        effective_at=source_at,
                        versions={
                            renewed_source: await _version(
                                store,
                                renewed_source,
                                attach_at,
                            ),
                            predecessor: await _version(
                                store,
                                predecessor,
                                attach_at,
                            ),
                        },
                    ),
                    source_decision_id=renewed_source,
                    predecessors=(
                        RenewalPredecessor(
                            predecessor,
                            RenewedFromRelationshipBasis(("acceptance-mixed-renewal",)),
                        ),
                    ),
                )
            )

            mixed_at = attach_at + timedelta(minutes=1)
            await _assert_supersession_rejected(
                store,
                source=predecessor,
                target=renewed_source,
                at=mixed_at,
                operation=0xF24,
                fact=0xF25,
                reference="acceptance-mixed-cycle-return",
                expected=RelationshipCycle,
            )

    asyncio.run(scenario())


def test_r2_acceptance_future_and_contested_cycle_possibilities_fail_closed(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_engine_store(postgres_target) as (_, store):
            # duplicate-code: the future-cycle acceptance proof keeps its endpoint and
            # edge topology local rather than importing lower-level graph fixtures.
            # arid: disable
            first = await _create_decision(
                store,
                recorded_at=START,
                label="future-first",
                ids=(0xF30, 0xF31, 0xF32, 0xF33),
            )
            second = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=1),
                label="future-second",
                ids=(0xF34, 0xF35, 0xF36, 0xF37),
            )
            recorded_at = START + timedelta(hours=1)
            future_at = recorded_at + timedelta(days=1)
            await _supersede(
                store,
                source=first,
                targets=(second,),
                recorded_at=recorded_at,
                effective_at=future_at,
                operation=0xF38,
                fact_ids=(0xF39,),
                reference="acceptance-future-forward",
            )

            return_at = recorded_at + timedelta(minutes=1)
            await _assert_supersession_rejected(
                store,
                source=second,
                target=first,
                at=return_at,
                operation=0xF3A,
                fact=0xF3B,
                reference="acceptance-future-return",
                expected=RelationshipCycle,
            )
            # arid: enable

            # This case is historical-only: the current graph is safe, but the
            # proposed backdated edge would have cycled before a prior withdrawal.
            historical_source = await _create_decision(
                store,
                recorded_at=START + timedelta(hours=3),
                label="historical-source",
                ids=(0xF70, 0xF71, 0xF72, 0xF73),
            )
            historical_target = await _create_decision(
                store,
                recorded_at=START + timedelta(hours=3, minutes=1),
                label="historical-target",
                ids=(0xF74, 0xF75, 0xF76, 0xF77),
            )
            supported_at = START + timedelta(hours=3, minutes=10)
            historical_base = await _supersede(
                store,
                source=historical_source,
                targets=(historical_target,),
                recorded_at=supported_at,
                effective_at=supported_at,
                operation=0xF78,
                fact_ids=(0xF79,),
                reference="acceptance-historical-forward",
            )
            withdrawn_at = supported_at + timedelta(minutes=5)
            await _correct(
                store,
                source=historical_source,
                target=historical_target,
                target_fact_id=historical_base.relationship_fact_ids[0],
                recorded_at=withdrawn_at,
                correction_effective_at=withdrawn_at,
                operation=0xF7A,
                fact=0xF7B,
                reference="acceptance-historical-withdraw",
                effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
            )
            historical_attempt_at = withdrawn_at + timedelta(minutes=5)
            historical_memory = DecisionMemoryService(
                reader=store,
                now=lambda: historical_attempt_at,
            )
            historical_lineage = await historical_memory.lineage(
                historical_target,
                effective_at=historical_attempt_at,
                known_at=historical_attempt_at,
            )
            assert len(historical_lineage) == 1
            assert historical_lineage[0].state is DecisionRelationshipState.WITHDRAWN
            await _assert_supersession_rejected(
                store,
                source=historical_target,
                target=historical_source,
                at=historical_attempt_at,
                effective_at=supported_at + timedelta(minutes=1),
                operation=0xF7C,
                fact=0xF7D,
                reference="acceptance-historical-return",
                expected=RelationshipCycle,
            )

            contest_start = historical_attempt_at + timedelta(minutes=10)
            source = await _create_decision(
                store,
                recorded_at=contest_start,
                label="contest-source",
                ids=(0xF3C, 0xF3D, 0xF3E, 0xF3F),
            )
            target = await _create_decision(
                store,
                recorded_at=contest_start + timedelta(minutes=1),
                label="contest-target",
                ids=(0xF40, 0xF41, 0xF42, 0xF43),
            )
            # duplicate-code: competing qualification branches must remain explicit in
            # this acceptance proof so the two surviving positive possibilities are
            # visible without coupling to correction-test fixtures.
            # arid: disable
            base_at = contest_start + timedelta(minutes=10)
            base = await _supersede(
                store,
                source=source,
                targets=(target,),
                recorded_at=base_at,
                effective_at=base_at,
                operation=0xF44,
                fact_ids=(0xF45,),
                reference="acceptance-contest-base",
            )
            base_fact_id = base.relationship_fact_ids[0]

            first_qualify_at = base_at + timedelta(minutes=1)
            await _correct(
                store,
                source=source,
                target=target,
                target_fact_id=base_fact_id,
                recorded_at=first_qualify_at,
                correction_effective_at=first_qualify_at,
                operation=0xF46,
                fact=0xF47,
                reference="acceptance-contest-first",
                effect=DecisionRelationshipCorrectionEffect.QUALIFY,
                replacement_effective_at=base_at,
            )
            second_qualify_at = base_at + timedelta(minutes=2)
            await _correct(
                store,
                source=source,
                target=target,
                target_fact_id=base_fact_id,
                recorded_at=second_qualify_at,
                correction_effective_at=second_qualify_at,
                operation=0xF48,
                fact=0xF49,
                reference="acceptance-contest-second",
                effect=DecisionRelationshipCorrectionEffect.QUALIFY,
                replacement_effective_at=base_at + timedelta(seconds=1),
            )
            # arid: enable

            memory = DecisionMemoryService(reader=store, now=lambda: second_qualify_at)
            contested = await memory.lineage(
                target,
                effective_at=second_qualify_at,
                known_at=second_qualify_at,
            )
            assert len(contested) == 1
            assert contested[0].state is DecisionRelationshipState.CONTESTED
            assert len(contested[0].surviving_positive_claims) == 2

            contested_at = base_at + timedelta(minutes=3)
            await _assert_supersession_rejected(
                store,
                source=target,
                target=source,
                at=contested_at,
                operation=0xF4A,
                fact=0xF4B,
                reference="acceptance-contested-return",
                expected=RelationshipCycleSafetyIndeterminate,
            )

    asyncio.run(scenario())


def test_r2_acceptance_recursive_restore_and_atomic_swap_use_final_graph_history(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_engine_store(postgres_target) as (_, store):
            left = await _create_decision(
                store,
                recorded_at=START,
                label="swap-left",
                ids=(0xF50, 0xF51, 0xF52, 0xF53),
            )
            right = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=1),
                label="swap-right",
                ids=(0xF54, 0xF55, 0xF56, 0xF57),
            )
            base_at = START + timedelta(hours=1)
            left_to_right = await _supersede(
                store,
                source=left,
                targets=(right,),
                recorded_at=base_at,
                effective_at=base_at,
                operation=0xF58,
                fact_ids=(0xF59,),
                reference="acceptance-swap-left-right",
            )
            left_to_right_id = left_to_right.relationship_fact_ids[0]

            withdraw_at = base_at + timedelta(minutes=1)
            withdrawn = await _correct(
                store,
                source=left,
                target=right,
                target_fact_id=left_to_right_id,
                recorded_at=withdraw_at,
                correction_effective_at=withdraw_at,
                operation=0xF5A,
                fact=0xF5B,
                reference="acceptance-swap-withdraw-left-right",
                effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
            )
            withdrawal_id = withdrawn.relationship_fact_ids[0]

            reverse_at = base_at + timedelta(minutes=2)
            right_to_left = await _supersede(
                store,
                source=right,
                targets=(left,),
                recorded_at=reverse_at,
                effective_at=reverse_at,
                operation=0xF5C,
                fact_ids=(0xF5D,),
                reference="acceptance-swap-right-left",
            )
            right_to_left_id = right_to_left.relationship_fact_ids[0]

            rejected_restore_operation = OperationId(_uuid(0xF5E))
            restore_at = base_at + timedelta(minutes=3)
            before_history = await store.load_relationship_history()
            before_versions = await _versions(store, (left, right), restore_at)
            with pytest.raises(RelationshipCycle):
                await _correct(
                    store,
                    source=left,
                    target=right,
                    target_fact_id=withdrawal_id,
                    recorded_at=restore_at,
                    correction_effective_at=restore_at,
                    operation=0xF5E,
                    fact=0xF5F,
                    reference="acceptance-swap-unsafe-restore",
                    effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
                )
            assert await store.load_relationship_history() == before_history
            assert await _versions(store, (left, right), restore_at) == before_versions
            assert (
                await store.get_relationship_receipt(rejected_restore_operation) is None
            )

            swap_at = base_at + timedelta(minutes=4)
            swap_operation = OperationId(_uuid(0xF60))
            generated = _ids(0xF61, 0xF62)
            result = await DecisionRelationshipCorrectionService(
                store=store,
                now=lambda: swap_at,
                new_uuid=lambda: next(generated),
            ).correct_set(
                CorrectDecisionRelationshipSetCommand(
                    envelope=_envelope(
                        operation=0xF60,
                        reference="acceptance-atomic-safe-swap",
                        effective_at=swap_at,
                        versions={
                            left: await _version(store, left, swap_at),
                            right: await _version(store, right, swap_at),
                        },
                    ),
                    corrections=(
                        RelationshipCorrectionMember(
                            local_id="restore-left-right",
                            target=withdrawal_id,
                            effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
                            correction_effective_at=swap_at,
                            correction_basis=DecisionRelationshipCorrectionBasis(
                                ("restore-left-right",)
                            ),
                        ),
                        RelationshipCorrectionMember(
                            local_id="withdraw-right-left",
                            target=right_to_left_id,
                            effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
                            correction_effective_at=swap_at,
                            correction_basis=DecisionRelationshipCorrectionBasis(
                                ("withdraw-right-left",)
                            ),
                        ),
                    ),
                )
            )
            assert len(result.relationship_fact_ids) == 2
            assert await store.get_relationship_receipt(swap_operation) is not None

            memory = DecisionMemoryService(reader=store, now=lambda: swap_at)
            lineage = await memory.lineage(
                left,
                effective_at=swap_at,
                known_at=swap_at,
            )
            states = {
                (item.source_decision_id, item.target_decision_id): item.state
                for item in lineage
            }
            assert states[(left, right)] is DecisionRelationshipState.SUPPORTED
            assert states[(right, left)] is DecisionRelationshipState.WITHDRAWN
            assert len(await store.load_relationship_history()) == 5

    asyncio.run(scenario())
