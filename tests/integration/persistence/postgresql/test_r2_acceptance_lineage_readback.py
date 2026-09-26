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
    DecisionHistoryView,
    DecisionInitiationService,
    DecisionLineageDirection,
    DecisionLineageView,
    DecisionMemoryService,
    DecisionNotFound,
    DecisionOrdinaryWorkService,
    ExpectedDecisionVersion,
    InitiateDecisionCommand,
    RelationshipHistoryInvalidOrIncomplete,
)
from polaris.application.decisions.relationships import (
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

from .conftest import (
    PostgresTestTarget,
    corrupt_relationship_lineage_source,
    postgres_engine_store,
)

START = datetime(2026, 9, 25, 7, 0, tzinfo=UTC)
ACTOR = KnownActorAttribution(ActorId(UUID("00000000-0000-4000-8000-000000001401")))


# duplicate-code: this ticket-level acceptance proof owns deterministic identity,
# provenance, and command construction independently of lower-level persistence tests.
# arid: disable
def _uuid(value: int) -> UUID:
    return UUID(f"00000000-0000-4000-8000-{value:012x}")


def _ids(*values: int) -> Iterator[UUID]:
    yield from (_uuid(value) for value in values)


def _technical(reference: str, *, present: bool = True) -> TechnicalProvenance:
    if not present:
        return TechnicalProvenance()
    return TechnicalProvenance(
        (
            TechnicalReference(TechnicalReferenceKind.TRACE, f"trace-{reference}"),
            TechnicalReference(TechnicalReferenceKind.REQUEST, f"request-{reference}"),
        )
    )


def _envelope(
    *,
    operation: int,
    reference: str,
    effective_at: datetime,
    versions: dict[InvestmentDecisionId, DecisionVersion] | None = None,
    technical: bool = True,
) -> DecisionCommandEnvelope:
    return DecisionCommandEnvelope(
        operation_id=OperationId(_uuid(operation)),
        actor_attribution=ACTOR,
        trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, reference),
        effective_at=effective_at,
        technical_provenance=_technical(reference, present=technical),
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
                reference=f"lineage-{label}",
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
    version = await _version(store, decision_id, recorded_at)
    await DecisionOrdinaryWorkService(
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: _uuid(fact),
    ).apply_substantive_resolution(
        ApplySubstantiveResolutionCommand(
            envelope=_envelope(
                operation=operation,
                reference="lineage-resolve-predecessor",
                effective_at=recorded_at,
                versions={decision_id: version},
            ),
            decision_id=decision_id,
            basis=TrustedHumanInvestmentDecisionBasis(
                "lineage-human-resolution",
                HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
            ),
        )
    )


async def _renew(
    store: PostgresDecisionStore,
    predecessor: InvestmentDecisionId,
    *,
    recorded_at: datetime,
    operation: int,
    generated_ids: tuple[int, int, int, int],
    reference: str,
) -> tuple[
    InvestmentDecisionId,
    DecisionRelationshipFactId,
    DecisionCommandEnvelope,
    RenewedFromRelationshipBasis,
]:
    candidates = await store.find_unresolved_continuity_candidates(known_at=recorded_at)
    envelope = _envelope(
        operation=operation,
        reference=reference,
        effective_at=recorded_at,
        versions={predecessor: await _version(store, predecessor, recorded_at)},
    )
    basis = RenewedFromRelationshipBasis((f"{reference}-basis",))
    generated = _ids(*generated_ids)
    result = await DecisionRelationshipService(
        reader=store,
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: next(generated),
    ).renew(
        RenewDecisionCommand(
            envelope=envelope,
            need_statement="Revisit the resolved portfolio decision",
            subject=DecisionSubject("Renewed portfolio decision"),
            scope=DecisionScope.unresolved(),
            predecessors=(RenewalPredecessor(predecessor, basis),),
            continuity=(
                ContinuityDetermination.create_new("independent renewed judgment")
                if candidates
                else None
            ),
        )
    )
    assert result.new_decision_id is not None
    assert len(result.relationship_fact_ids) == 1
    return result.new_decision_id, result.relationship_fact_ids[0], envelope, basis


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
    technical: bool = True,
) -> tuple[
    DecisionRelationshipFactId,
    DecisionCommandEnvelope,
    SupersedesRelationshipBasis,
]:
    envelope = _envelope(
        operation=operation,
        reference=reference,
        effective_at=recorded_at,
        versions={
            source: await _version(store, source, recorded_at),
            target: await _version(store, target, recorded_at),
        },
        technical=technical,
    )
    basis = SupersedesRelationshipBasis((f"{reference}-basis",))
    result = await DecisionRelationshipService(
        reader=store,
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: _uuid(fact),
    ).establish_supersession(
        EstablishSupersessionCommand(
            envelope=envelope,
            source_decision_id=source,
            targets=(SupersessionTarget(target, basis, effective_at),),
        )
    )
    return result.relationship_fact_ids[0], envelope, basis


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
) -> tuple[
    DecisionRelationshipFactId,
    DecisionCommandEnvelope,
    DecisionRelationshipCorrectionBasis,
]:
    envelope = _envelope(
        operation=operation,
        reference=reference,
        effective_at=correction_effective_at,
        versions={
            source: await _version(store, source, recorded_at),
            target: await _version(store, target, recorded_at),
        },
    )
    correction_basis = DecisionRelationshipCorrectionBasis(
        (f"{reference}-correction-basis",)
    )
    result = await DecisionRelationshipCorrectionService(
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: _uuid(fact),
    ).correct(
        CorrectDecisionRelationshipCommand(
            envelope=envelope,
            target_relationship_fact_id=target_fact_id,
            effect=effect,
            correction_effective_at=correction_effective_at,
            correction_basis=correction_basis,
            replacement_relationship_effective_at=replacement_effective_at,
            replacement_relationship_basis=(
                SupersedesRelationshipBasis((f"{reference}-replacement-basis",))
                if replacement_effective_at is not None
                else None
            ),
        )
    )
    return result.relationship_fact_ids[0], envelope, correction_basis


# arid: enable


def _lineage_by_type(
    values: tuple[DecisionLineageView, ...],
) -> dict[DecisionRelationshipType, DecisionLineageView]:
    return {value.relationship_type: value for value in values}


def _history_by_id(
    view: DecisionHistoryView,
) -> dict[
    DecisionRelationshipFactId,
    DecisionRelationshipFact | DecisionRelationshipCorrected,
]:
    return {
        fact.metadata.relationship_fact_id: fact for fact in view.relationship_facts
    }


def test_r2_acceptance_lineage_and_raw_history_reconstruct_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        predecessor_at = START
        resolve_at = START + timedelta(minutes=5)
        renewal_at = START + timedelta(minutes=10)
        superseder_at = START + timedelta(minutes=11)
        supersede_effective_at = START + timedelta(minutes=15)
        supersede_recorded_at = START + timedelta(minutes=20)
        withdraw_effective_at = START + timedelta(minutes=22)
        withdraw_recorded_at = START + timedelta(minutes=25)
        query_at = START + timedelta(minutes=30)

        async with postgres_engine_store(postgres_target) as (_, store):
            predecessor = await _create_decision(
                store,
                recorded_at=predecessor_at,
                label="restart-predecessor",
                ids=(0x1402, 0x1403, 0x1404, 0x1405),
            )
            await _resolve(
                store,
                predecessor,
                recorded_at=resolve_at,
                fact=0x1406,
                operation=0x1407,
            )
            renewed, renewal_fact_id, renewal_envelope, renewal_basis = await _renew(
                store,
                predecessor,
                recorded_at=renewal_at,
                operation=0x1408,
                generated_ids=(0x1409, 0x140A, 0x140B, 0x140C),
                reference="restart-renewal",
            )
            superseder = await _create_decision(
                store,
                recorded_at=superseder_at,
                label="restart-superseder",
                ids=(0x140D, 0x140E, 0x140F, 0x1410),
            )
            (
                supersession_fact_id,
                supersession_envelope,
                supersession_basis,
            ) = await _supersede(
                store,
                source=superseder,
                target=renewed,
                recorded_at=supersede_recorded_at,
                effective_at=supersede_effective_at,
                operation=0x1411,
                fact=0x1412,
                reference="restart-supersession",
                technical=False,
            )
            (
                withdrawal_fact_id,
                withdrawal_envelope,
                withdrawal_basis,
            ) = await _correct(
                store,
                source=superseder,
                target=renewed,
                target_fact_id=supersession_fact_id,
                recorded_at=withdraw_recorded_at,
                correction_effective_at=withdraw_effective_at,
                operation=0x1413,
                fact=0x1414,
                reference="restart-withdraw",
                effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
            )

        async with postgres_engine_store(postgres_target) as (_, restarted):
            memory = DecisionMemoryService(reader=restarted, now=lambda: query_at)
            lineage = await memory.lineage(
                renewed,
                effective_at=query_at,
                known_at=query_at,
            )
            history = await memory.history(renewed, known_at=query_at)

            assert all(type(item) is DecisionLineageView for item in lineage)
            assert type(history) is DecisionHistoryView
            assert len(lineage) == 2
            by_type = _lineage_by_type(lineage)

            renewal = by_type[DecisionRelationshipType.RENEWED_FROM]
            assert renewal.source_decision_id == renewed
            assert renewal.target_decision_id == predecessor
            assert renewal.direction is DecisionLineageDirection.OUTGOING
            assert renewal.effective_at == query_at
            assert renewal.known_at == query_at
            assert renewal.state is DecisionRelationshipState.SUPPORTED
            assert renewal.support_fact_ids == frozenset({renewal_fact_id})
            # duplicate-code: #344 independently proves the combined lineage read
            # model after restart; sharing this assertion with renewal acceptance
            # would couple separate ticket-level acceptance obligations.
            # arid: disable
            assert {
                (
                    contribution.relationship_fact_id,
                    contribution.role,
                    contribution.basis,
                )
                for contribution in renewal.basis_contributions
            } == {
                (
                    renewal_fact_id,
                    DecisionRelationshipBasisRole.RELATIONSHIP,
                    renewal_basis,
                )
            }
            # arid: enable
            assert len(renewal.surviving_positive_claims) == 1

            supersession = by_type[DecisionRelationshipType.SUPERSEDES]
            assert supersession.source_decision_id == superseder
            assert supersession.target_decision_id == renewed
            assert supersession.direction is DecisionLineageDirection.INCOMING
            assert supersession.effective_at == query_at
            assert supersession.known_at == query_at
            assert supersession.state is DecisionRelationshipState.WITHDRAWN
            assert supersession.surviving_positive_claims == frozenset()
            assert withdrawal_fact_id in supersession.support_fact_ids
            assert any(
                contribution.relationship_fact_id == withdrawal_fact_id
                and contribution.role is DecisionRelationshipBasisRole.CORRECTION
                and contribution.basis == withdrawal_basis
                for contribution in supersession.basis_contributions
            )

            raw = _history_by_id(history)
            assert set(raw) == {
                renewal_fact_id,
                supersession_fact_id,
                withdrawal_fact_id,
            }
            renewal_fact = raw[renewal_fact_id]
            supersession_fact = raw[supersession_fact_id]
            withdrawal_fact = raw[withdrawal_fact_id]
            assert isinstance(renewal_fact, DecisionRelationshipFact)
            assert isinstance(supersession_fact, DecisionRelationshipFact)
            assert isinstance(withdrawal_fact, DecisionRelationshipCorrected)

            assert (
                renewal_fact.relationship_type is DecisionRelationshipType.RENEWED_FROM
            )
            assert renewal_fact.source_decision_id == renewed
            assert renewal_fact.target_decision_id == predecessor
            assert renewal_fact.relationship_basis == renewal_basis
            assert renewal_fact.metadata.operation_id == renewal_envelope.operation_id
            assert renewal_fact.metadata.actor_attribution == ACTOR
            assert renewal_fact.metadata.trigger == renewal_envelope.trigger
            assert (
                renewal_fact.metadata.technical_provenance
                == renewal_envelope.technical_provenance
            )
            assert renewal_fact.relationship_effective_at == renewal_at
            assert renewal_fact.metadata.recorded_at == renewal_at

            assert (
                supersession_fact.relationship_type
                is DecisionRelationshipType.SUPERSEDES
            )
            assert supersession_fact.source_decision_id == superseder
            assert supersession_fact.target_decision_id == renewed
            assert supersession_fact.relationship_basis == supersession_basis
            assert (
                supersession_fact.metadata.operation_id
                == supersession_envelope.operation_id
            )
            assert supersession_fact.metadata.actor_attribution == ACTOR
            assert supersession_fact.metadata.trigger == supersession_envelope.trigger
            assert (
                supersession_fact.metadata.technical_provenance == TechnicalProvenance()
            )
            assert supersession_fact.relationship_effective_at == supersede_effective_at
            assert supersession_fact.metadata.recorded_at == supersede_recorded_at
            assert supersede_effective_at != supersede_recorded_at

            assert withdrawal_fact.target_relationship_fact_id == supersession_fact_id
            assert (
                withdrawal_fact.effect
                is DecisionRelationshipCorrectionEffect.DISCONFIRM
            )
            assert withdrawal_fact.correction_basis == withdrawal_basis
            assert (
                withdrawal_fact.metadata.operation_id
                == withdrawal_envelope.operation_id
            )
            assert withdrawal_fact.metadata.actor_attribution == ACTOR
            assert withdrawal_fact.metadata.trigger == withdrawal_envelope.trigger
            assert (
                withdrawal_fact.metadata.technical_provenance
                == withdrawal_envelope.technical_provenance
            )
            assert withdrawal_fact.correction_effective_at == withdraw_effective_at
            assert withdrawal_fact.metadata.recorded_at == withdraw_recorded_at
            assert withdraw_effective_at != withdraw_recorded_at

            business_and_technical_ids = {
                renewed.value,
                predecessor.value,
                superseder.value,
                renewal_fact_id.value,
                supersession_fact_id.value,
                withdrawal_fact_id.value,
                renewal_envelope.operation_id.value,
                supersession_envelope.operation_id.value,
                withdrawal_envelope.operation_id.value,
                ACTOR.actor_id.value,
            }
            assert len(business_and_technical_ids) == 10

    asyncio.run(scenario())


def test_r2_acceptance_lineage_four_state_and_temporal_partition_survives_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_engine_store(postgres_target) as (_, store):
            supported_source = await _create_decision(
                store,
                recorded_at=START,
                label="state-supported-source",
                ids=(0x1420, 0x1421, 0x1422, 0x1423),
            )
            supported_target = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=1),
                label="state-supported-target",
                ids=(0x1424, 0x1425, 0x1426, 0x1427),
            )
            supported_at = START + timedelta(minutes=10)
            supported_fact, _, _ = await _supersede(
                store,
                source=supported_source,
                target=supported_target,
                recorded_at=supported_at,
                effective_at=supported_at,
                operation=0x1428,
                fact=0x1429,
                reference="state-supported",
            )

            withdrawn_source = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=20),
                label="state-withdrawn-source",
                ids=(0x142A, 0x142B, 0x142C, 0x142D),
            )
            withdrawn_target = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=21),
                label="state-withdrawn-target",
                ids=(0x142E, 0x142F, 0x1430, 0x1431),
            )
            withdrawn_base_at = START + timedelta(minutes=30)
            withdrawn_base, _, _ = await _supersede(
                store,
                source=withdrawn_source,
                target=withdrawn_target,
                recorded_at=withdrawn_base_at,
                effective_at=withdrawn_base_at,
                operation=0x1432,
                fact=0x1433,
                reference="state-withdrawn-base",
            )
            withdrawn_at = START + timedelta(minutes=31)
            withdrawn_fact, _, _ = await _correct(
                store,
                source=withdrawn_source,
                target=withdrawn_target,
                target_fact_id=withdrawn_base,
                recorded_at=withdrawn_at,
                correction_effective_at=withdrawn_at,
                operation=0x1434,
                fact=0x1435,
                reference="state-withdrawn",
                effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
            )

            future_source = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=40),
                label="state-future-source",
                ids=(0x1436, 0x1437, 0x1438, 0x1439),
            )
            future_target = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=41),
                label="state-future-target",
                ids=(0x143A, 0x143B, 0x143C, 0x143D),
            )
            future_recorded = START + timedelta(minutes=50)
            future_effective = START + timedelta(days=1)
            future_fact, _, _ = await _supersede(
                store,
                source=future_source,
                target=future_target,
                recorded_at=future_recorded,
                effective_at=future_effective,
                operation=0x143E,
                fact=0x143F,
                reference="state-future",
            )

            contested_source = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=60),
                label="state-contested-source",
                ids=(0x1440, 0x1441, 0x1442, 0x1443),
            )
            contested_target = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=61),
                label="state-contested-target",
                ids=(0x1444, 0x1445, 0x1446, 0x1447),
            )
            contested_base_at = START + timedelta(minutes=70)
            contested_base, _, _ = await _supersede(
                store,
                source=contested_source,
                target=contested_target,
                recorded_at=contested_base_at,
                effective_at=contested_base_at,
                operation=0x1448,
                fact=0x1449,
                reference="state-contested-base",
            )
            first_at = START + timedelta(minutes=71)
            # duplicate-code: competing qualification branches are separate
            # semantic possibilities in this four-state falsifier; a shared loop/helper
            # would hide which branch establishes each contested claim.
            # arid: disable
            first_fact, _, _ = await _correct(
                store,
                source=contested_source,
                target=contested_target,
                target_fact_id=contested_base,
                recorded_at=first_at,
                correction_effective_at=first_at,
                operation=0x144A,
                fact=0x144B,
                reference="state-contested-first",
                effect=DecisionRelationshipCorrectionEffect.QUALIFY,
                replacement_effective_at=contested_base_at,
            )
            # arid: enable
            second_at = START + timedelta(minutes=72)
            second_fact, _, _ = await _correct(
                store,
                source=contested_source,
                target=contested_target,
                target_fact_id=contested_base,
                recorded_at=second_at,
                correction_effective_at=first_at,
                operation=0x144C,
                fact=0x144D,
                reference="state-contested-second",
                effect=DecisionRelationshipCorrectionEffect.QUALIFY,
                replacement_effective_at=contested_base_at + timedelta(seconds=1),
            )

        async with postgres_engine_store(postgres_target) as (_, restarted):
            memory = DecisionMemoryService(reader=restarted, now=lambda: second_at)

            with pytest.raises(DecisionNotFound):
                await memory.lineage(
                    supported_target,
                    known_at=START,
                )

            supported = (
                await memory.lineage(
                    supported_target,
                    effective_at=second_at,
                    known_at=second_at,
                )
            )[0]
            withdrawn = (
                await memory.lineage(
                    withdrawn_target,
                    effective_at=second_at,
                    known_at=second_at,
                )
            )[0]
            not_effective = (
                await memory.lineage(
                    future_target,
                    effective_at=second_at,
                    known_at=second_at,
                )
            )[0]
            contested = (
                await memory.lineage(
                    contested_target,
                    effective_at=second_at,
                    known_at=second_at,
                )
            )[0]

            assert supported.state is DecisionRelationshipState.SUPPORTED
            assert supported.support_fact_ids == frozenset({supported_fact})
            assert len(supported.surviving_positive_claims) == 1

            assert withdrawn.state is DecisionRelationshipState.WITHDRAWN
            assert withdrawn_fact in withdrawn.support_fact_ids
            assert withdrawn.surviving_positive_claims == frozenset()

            assert not_effective.state is DecisionRelationshipState.NOT_EFFECTIVE
            assert not_effective.effective_at == second_at
            assert not_effective.known_at == second_at
            assert not_effective.surviving_positive_claims == frozenset()
            assert future_fact not in {
                support_id
                for claim in not_effective.surviving_positive_claims
                for support_id in claim.support_fact_ids
            }

            assert contested.state is DecisionRelationshipState.CONTESTED
            assert contested.support_fact_ids == frozenset({first_fact, second_fact})
            assert len(contested.surviving_positive_claims) == 2
            assert {
                claim.relationship_effective_at
                for claim in contested.surviving_positive_claims
            } == {
                contested_base_at,
                contested_base_at + timedelta(seconds=1),
            }

            future_after = (
                await memory.lineage(
                    future_target,
                    effective_at=future_effective,
                    known_at=second_at,
                )
            )[0]
            assert future_after.state is DecisionRelationshipState.SUPPORTED
            assert future_after.support_fact_ids == frozenset({future_fact})
            assert future_after.effective_at == future_effective
            assert future_after.known_at == second_at

    asyncio.run(scenario())


def test_r2_acceptance_invalid_durable_lineage_is_not_reported_as_outage(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        correction_at = START + timedelta(minutes=20)

        # duplicate-code: the AC3 durable-corruption falsifier owns its
        # PostgreSQL setup independently of relationship-correction acceptance;
        # sharing scenario setup would couple distinct acceptance obligations.
        # arid: disable
        async with postgres_engine_store(postgres_target) as (engine, store):
            source = await _create_decision(
                store,
                recorded_at=START,
                label="invalid-source",
                ids=(0x1450, 0x1451, 0x1452, 0x1453),
            )
            # arid: enable
            target = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=1),
                label="invalid-target",
                ids=(0x1454, 0x1455, 0x1456, 0x1457),
            )
            unrelated = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=2),
                label="invalid-unrelated",
                ids=(0x1458, 0x1459, 0x145A, 0x145B),
            )
            base_at = START + timedelta(minutes=10)
            # duplicate-code: this base edge exists only to seed the AC3
            # malformed-history falsifier; sharing its invocation with correction
            # acceptance would couple independent proof scenarios.
            # arid: disable
            base_fact, _, _ = await _supersede(
                store,
                source=source,
                target=target,
                recorded_at=base_at,
                effective_at=base_at,
                operation=0x145C,
                fact=0x145D,
                reference="invalid-base",
            )
            # arid: enable
            correction_fact, _, _ = await _correct(
                store,
                source=source,
                target=target,
                target_fact_id=base_fact,
                recorded_at=correction_at,
                correction_effective_at=correction_at,
                operation=0x145E,
                fact=0x145F,
                reference="invalid-correction",
                effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
            )

            await corrupt_relationship_lineage_source(
                engine,
                relationship_fact_id=correction_fact,
                source_decision_id=unrelated,
            )

        async with postgres_engine_store(postgres_target) as (_, restarted):
            memory = DecisionMemoryService(
                reader=restarted,
                now=lambda: correction_at + timedelta(minutes=1),
            )
            with pytest.raises(RelationshipHistoryInvalidOrIncomplete):
                await memory.lineage(
                    target,
                    effective_at=correction_at + timedelta(minutes=1),
                    known_at=correction_at + timedelta(minutes=1),
                )
            with pytest.raises(RelationshipHistoryInvalidOrIncomplete):
                await memory.current(target)

    asyncio.run(scenario())
