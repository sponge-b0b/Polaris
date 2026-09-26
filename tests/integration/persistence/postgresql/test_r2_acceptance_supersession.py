from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from polaris.application.decisions import (
    ApplyHumanDeferralCommand,
    ApplySubstantiveResolutionCommand,
    ContinuityDetermination,
    DecisionCommandEnvelope,
    DecisionCommandState,
    DecisionInitiationService,
    DecisionLineageDirection,
    DecisionMemoryService,
    DecisionMutationCommit,
    DecisionMutationCommitOutcome,
    DecisionMutationReceipt,
    DecisionNonOperative,
    DecisionOperativeStatusContested,
    DecisionOrdinaryWorkService,
    ExpectedDecisionVersion,
    InitiateDecisionCommand,
)
from polaris.application.decisions.relationships import (
    DecisionRelationshipService,
    EstablishSupersessionCommand,
    SupersessionTarget,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionApplicability,
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleDisposition,
    DecisionLifecycleFactId,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNeedId,
    DecisionRelationshipCorrectionBasis,
    DecisionRelationshipCorrectionEffect,
    DecisionRelationshipFact,
    DecisionRelationshipFactId,
    DecisionRelationshipMutationContext,
    DecisionRelationshipState,
    DecisionRelationshipType,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    HumanInvestmentDecisionEffect,
    InvestmentDecision,
    InvestmentDecisionId,
    OperationId,
    SupersedesRelationshipBasis,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
    derive_relationship_applicability,
    initiate_decision,
    relationship_correction,
    relationship_fact,
)
from polaris.infrastructure.persistence.postgresql import PostgresDecisionStore

from .conftest import PostgresTestTarget, postgres_engine_store

START = datetime(2026, 9, 24, 18, 0, tzinfo=UTC)
ACTOR = KnownActorAttribution(ActorId(UUID("00000000-0000-4000-8000-000000000c01")))


# duplicate-code: this acceptance proof owns deterministic identity, provenance, and
# initiation fixtures independently of lower-level domain/persistence tests; sharing
# those helpers would couple product acceptance to another proof layer.
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
            _envelope(
                operation=operation,
                reference="acceptance-resolve-target",
                effective_at=recorded_at,
                versions={decision_id: version},
            ),
            decision_id,
            TrustedHumanInvestmentDecisionBasis(
                "acceptance-resolve-target",
                HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
            ),
        )
    )


# duplicate-code: Supersession command construction is kept local so this acceptance
# proof owns its endpoint/version/cardinality setup instead of importing lower-level
# persistence-test helpers.
# arid: disable
async def _supersede(
    store: PostgresDecisionStore,
    *,
    source: InvestmentDecisionId,
    targets: tuple[InvestmentDecisionId, ...],
    recorded_at: datetime,
    operation: int,
    fact_ids: tuple[int, ...],
    reference: str,
) -> tuple[EstablishSupersessionCommand, tuple[DecisionRelationshipFactId, ...]]:
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
                recorded_at,
            )
            for index, target in enumerate(targets)
        ),
    )
    ids = _ids(*fact_ids)
    result = await DecisionRelationshipService(
        reader=store,
        store=store,
        now=lambda: recorded_at,
        new_uuid=lambda: next(ids),
    ).establish_supersession(command)
    return command, result.relationship_fact_ids


# arid: enable


def test_r2_acceptance_supersession_cardinality_applicability_and_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with postgres_engine_store(postgres_target) as (_, store):
            source_a = await _create_decision(
                store,
                recorded_at=START,
                label="source-a",
                ids=(0xC02, 0xC03, 0xC04, 0xC05),
            )
            target_unresolved = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=1),
                label="target-unresolved",
                ids=(0xC06, 0xC07, 0xC08, 0xC09),
            )
            target_resolved = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=2),
                label="target-resolved",
                ids=(0xC0A, 0xC0B, 0xC0C, 0xC0D),
            )
            source_b = await _create_decision(
                store,
                recorded_at=START + timedelta(minutes=3),
                label="source-b",
                ids=(0xC0E, 0xC0F, 0xC10, 0xC11),
            )
            assert len({source_a, source_b, target_unresolved, target_resolved}) == 4

            resolved_at = START + timedelta(minutes=20)
            await _resolve(
                store,
                target_resolved,
                recorded_at=resolved_at,
                fact=0xC12,
                operation=0xC13,
            )
            memory = DecisionMemoryService(reader=store, now=lambda: resolved_at)
            resolved_history_before = (
                await memory.history(target_resolved)
            ).lifecycle_facts

            first_at = START + timedelta(hours=1)
            first_command, first_fact_ids = await _supersede(
                store,
                source=source_a,
                targets=(target_unresolved, target_resolved),
                recorded_at=first_at,
                operation=0xC14,
                fact_ids=(0xC15, 0xC16),
                reference="acceptance-source-a-supersedes",
            )
            assert len(first_fact_ids) == 2
            assert len(set(first_fact_ids)) == 2

            second_at = first_at + timedelta(minutes=5)
            _, second_fact_ids = await _supersede(
                store,
                source=source_b,
                targets=(target_unresolved,),
                recorded_at=second_at,
                operation=0xC17,
                fact_ids=(0xC18,),
                reference="acceptance-source-b-supersedes",
            )
            assert len(second_fact_ids) == 1

            memory = DecisionMemoryService(reader=store, now=lambda: second_at)
            unresolved_current = await memory.current(target_unresolved)
            resolved_current = await memory.current(target_resolved)
            source_a_lineage = await memory.lineage(source_a, known_at=second_at)
            unresolved_lineage = await memory.lineage(
                target_unresolved,
                known_at=second_at,
            )
            resolved_history = await memory.history(target_resolved)

            assert unresolved_current.lifecycle_interpretation.disposition is (
                DecisionLifecycleDisposition.UNRESOLVED
            )
            assert unresolved_current.applicability is (
                DecisionApplicability.NON_OPERATIVE
            )
            assert resolved_current.lifecycle_interpretation.disposition is (
                DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
            )
            assert resolved_history.lifecycle_facts == resolved_history_before

            assert len(source_a_lineage) == 2
            assert {item.direction for item in source_a_lineage} == {
                DecisionLineageDirection.OUTGOING
            }
            assert {item.target_decision_id for item in source_a_lineage} == {
                target_unresolved,
                target_resolved,
            }
            assert {item.relationship_type for item in source_a_lineage} == {
                DecisionRelationshipType.SUPERSEDES
            }
            assert {item.state for item in source_a_lineage} == {
                DecisionRelationshipState.SUPPORTED
            }
            source_a_support_by_target = {
                item.target_decision_id: item.support_fact_ids
                for item in source_a_lineage
            }
            assert all(
                len(support_fact_ids) == 1
                for support_fact_ids in source_a_support_by_target.values()
            )
            assert frozenset().union(*source_a_support_by_target.values()) == frozenset(
                first_fact_ids
            )

            assert len(unresolved_lineage) == 2
            assert {item.direction for item in unresolved_lineage} == {
                DecisionLineageDirection.INCOMING
            }
            assert {item.source_decision_id for item in unresolved_lineage} == {
                source_a,
                source_b,
            }
            assert {item.state for item in unresolved_lineage} == {
                DecisionRelationshipState.SUPPORTED
            }
            unresolved_support_by_source = {
                item.source_decision_id: item.support_fact_ids
                for item in unresolved_lineage
            }
            assert (
                unresolved_support_by_source[source_a]
                == (source_a_support_by_target[target_unresolved])
            )
            assert unresolved_support_by_source[source_b] == frozenset(second_fact_ids)

            history_before_failed_work = await memory.history(target_unresolved)
            with pytest.raises(DecisionNonOperative):
                await DecisionOrdinaryWorkService(
                    store=store,
                    now=lambda: second_at,
                    new_uuid=lambda: _uuid(0xC19),
                ).apply_human_deferral(
                    ApplyHumanDeferralCommand(
                        _envelope(
                            operation=0xC1A,
                            reference="acceptance-nonoperative-work",
                            effective_at=second_at,
                            versions={
                                target_unresolved: unresolved_current.version,
                            },
                        ),
                        target_unresolved,
                        TrustedHumanInvestmentDecisionBasis(
                            "acceptance-nonoperative-work",
                            HumanInvestmentDecisionEffect.DEFERRING,
                        ),
                    )
                )
            assert await memory.history(target_unresolved) == history_before_failed_work

            source_history = await memory.history(source_a)
            source_base_facts = tuple(
                fact
                for fact in source_history.relationship_facts
                if isinstance(fact, DecisionRelationshipFact)
                and fact.metadata.relationship_fact_id in first_fact_ids
            )
            assert len(source_base_facts) == 2
            for fact in source_base_facts:
                assert fact.source_decision_id == source_a
                assert fact.relationship_type is DecisionRelationshipType.SUPERSEDES
                assert fact.metadata.actor_attribution == ACTOR
                assert fact.metadata.trigger == first_command.envelope.trigger
                assert (
                    fact.metadata.technical_provenance
                    == first_command.envelope.technical_provenance
                )

            pre_restart_unresolved = unresolved_current
            pre_restart_resolved = resolved_current
            pre_restart_source_lineage = source_a_lineage
            pre_restart_unresolved_lineage = unresolved_lineage
            pre_restart_resolved_history = resolved_history
            pre_restart_source_history = source_history

        async with postgres_engine_store(postgres_target) as (_, restarted):
            restarted_memory = DecisionMemoryService(
                reader=restarted,
                now=lambda: second_at,
            )
            assert (
                await restarted_memory.current(target_unresolved)
                == pre_restart_unresolved
            )
            assert await restarted_memory.current(target_resolved) == (
                pre_restart_resolved
            )
            assert (
                await restarted_memory.lineage(
                    source_a,
                    known_at=second_at,
                )
                == pre_restart_source_lineage
            )
            assert (
                await restarted_memory.lineage(
                    target_unresolved,
                    known_at=second_at,
                )
                == pre_restart_unresolved_lineage
            )
            assert (
                await restarted_memory.history(target_resolved)
                == pre_restart_resolved_history
            )
            assert await restarted_memory.history(source_a) == (
                pre_restart_source_history
            )

    asyncio.run(scenario())


class _ContestedApplicabilityStore:
    def __init__(
        self,
        decision: InvestmentDecision,
        history: tuple[object, ...],
        boundary: datetime,
    ) -> None:
        self.decision = decision
        self.history = history
        self.boundary = boundary

    async def get_mutation_receipt(
        self,
        operation_id: OperationId,
    ) -> DecisionMutationReceipt | None:
        del operation_id
        return None

    async def load_decision_for_command(
        self,
        decision_id: InvestmentDecisionId,
        *,
        known_at: datetime,
    ) -> DecisionCommandState | None:
        if decision_id != self.decision.decision_id:
            return None
        return DecisionCommandState(
            self.decision,
            derive_relationship_applicability(
                decision_id,
                self.history,
                effective_at=known_at,
                known_at=known_at,
            ),
        )

    async def commit_mutation(
        self,
        commit: DecisionMutationCommit,
    ) -> DecisionMutationCommitOutcome:
        del commit
        raise AssertionError("contested ordinary work must fail before commit")


def _domain_decision() -> InvestmentDecision:
    recorded_at = START
    mutation = DecisionMutationContext(
        DecisionLifecycleFactId(_uuid(0xC20)),
        OperationId(_uuid(0xC21)),
        ACTOR,
        TriggerProvenance(TriggerKind.HUMAN_REQUEST, "contest-initiate"),
        recorded_at,
        recorded_at,
        _technical("contest-initiate"),
    )
    need = DecisionNeed(
        DecisionNeedId(_uuid(0xC22)),
        "Need contested applicability",
        recorded_at,
        recorded_at,
        mutation.operation_id,
        ACTOR,
        mutation.trigger,
        mutation.technical_provenance,
    )
    # duplicate-code: the contested-applicability falsifier owns its minimal domain
    # Decision construction; importing the domain-suite builder would couple
    # proof layers.
    # arid: disable
    result = initiate_decision(
        decision_id=InvestmentDecisionId(_uuid(0xC23)),
        need=need,
        subject=DecisionSubject("Contested applicability"),
        scope=DecisionScope.unresolved(),
        continuity=DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination.NO_CANDIDATES,
            candidate_decision_ids=(),
            known_at=recorded_at,
        ),
        mutation=mutation,
    )
    # arid: enable
    return result


def _relationship_mutation(
    *,
    fact: int,
    operation: int,
    reference: str,
    recorded_at: datetime,
) -> DecisionRelationshipMutationContext:
    return DecisionRelationshipMutationContext(
        DecisionRelationshipFactId(_uuid(fact)),
        OperationId(_uuid(operation)),
        ACTOR,
        TriggerProvenance(TriggerKind.EXTERNAL_OBSERVATION, reference),
        recorded_at,
        _technical(reference),
    )


def test_r2_acceptance_contested_supersession_applicability_fails_closed() -> None:
    target = _domain_decision()
    source = InvestmentDecisionId(_uuid(0xC24))
    base_at = START + timedelta(minutes=10)
    base = relationship_fact(
        source_decision_id=source,
        target_decision_id=target.decision_id,
        relationship_type=DecisionRelationshipType.SUPERSEDES,
        relationship_effective_at=base_at,
        relationship_basis=SupersedesRelationshipBasis(("contest-base",)),
        mutation=_relationship_mutation(
            fact=0xC25,
            operation=0xC26,
            reference="contest-base",
            recorded_at=base_at,
        ),
    )
    correction_at = base_at + timedelta(minutes=10)
    first = relationship_correction(
        target_relationship_fact_id=base.metadata.relationship_fact_id,
        effect=DecisionRelationshipCorrectionEffect.QUALIFY,
        correction_effective_at=correction_at,
        correction_basis=DecisionRelationshipCorrectionBasis(("contest-first",)),
        replacement_relationship_effective_at=base_at,
        replacement_relationship_basis=SupersedesRelationshipBasis(
            ("contest-first-support",)
        ),
        mutation=_relationship_mutation(
            fact=0xC27,
            operation=0xC28,
            reference="contest-first",
            recorded_at=correction_at,
        ),
    )
    second = relationship_correction(
        target_relationship_fact_id=base.metadata.relationship_fact_id,
        effect=DecisionRelationshipCorrectionEffect.QUALIFY,
        correction_effective_at=correction_at,
        correction_basis=DecisionRelationshipCorrectionBasis(("contest-second",)),
        replacement_relationship_effective_at=base_at - timedelta(minutes=1),
        replacement_relationship_basis=SupersedesRelationshipBasis(
            ("contest-second-support",)
        ),
        mutation=_relationship_mutation(
            fact=0xC29,
            operation=0xC2A,
            reference="contest-second",
            recorded_at=correction_at,
        ),
    )
    history = (base, first, second)
    applicability = derive_relationship_applicability(
        target.decision_id,
        history,
        effective_at=correction_at,
        known_at=correction_at,
    )
    assert applicability is DecisionApplicability.CONTESTED

    store = _ContestedApplicabilityStore(target, history, correction_at)
    with pytest.raises(DecisionOperativeStatusContested):
        asyncio.run(
            DecisionOrdinaryWorkService(
                store=store,
                now=lambda: correction_at,
                new_uuid=lambda: _uuid(0xC2B),
            ).apply_human_deferral(
                ApplyHumanDeferralCommand(
                    _envelope(
                        operation=0xC2C,
                        reference="contest-ordinary-work",
                        effective_at=correction_at,
                        versions={target.decision_id: target.version},
                    ),
                    target.decision_id,
                    TrustedHumanInvestmentDecisionBasis(
                        "contest-ordinary-work",
                        HumanInvestmentDecisionEffect.DEFERRING,
                    ),
                )
            )
        )
