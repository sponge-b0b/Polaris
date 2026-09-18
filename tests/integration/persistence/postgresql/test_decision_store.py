from __future__ import annotations

import asyncio
import inspect
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from polaris.application.decisions import (
    ApplyExternalResolutionCommand,
    ApplyHumanDeferralCommand,
    ApplySubstantiveResolutionCommand,
    ConcurrencyConflict,
    ContinuityConflict,
    ContinuityDetermination,
    DecisionCommandEnvelope,
    DecisionCommandState,
    DecisionInitiationService,
    DecisionMemoryService,
    DecisionMutationResult,
    DecisionMutationResultKind,
    DecisionNotFound,
    DecisionOrdinaryWorkService,
    EstablishOrReviseDecisionScopeCommand,
    ExpectedDecisionVersion,
    IdempotencyConflict,
    InitiateDecisionCommand,
    InvalidDecisionCommand,
    PersistenceUnavailable,
    ResumeDecisionWorkCommand,
    ReviseDecisionSubjectCommand,
    WithdrawDecisionWorkCommand,
)
from polaris.application.decisions.contracts import (
    ContinuityCandidateBasis,
    InitiationCommit,
    InitiationNeedAlreadyGrounded,
    InitiationResult,
    InitiationResultKind,
    InitiationSemanticRequest,
)
from polaris.application.decisions.lifecycle_correction import (
    DecisionLifecycleCorrectionService,
    RecordDecisionLifecycleCorrectionCommand,
    RetractUnsupportedDecisionNeedCommand,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    ContestedDecisionLifecycleInterpretation,
    DecisionContinuity,
    DecisionDeferred,
    DecisionExternallyResolved,
    DecisionInitiated,
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleCorrected,
    DecisionLifecycleCorrectionBasis,
    DecisionLifecycleCorrectionEffect,
    DecisionLifecycleDisposition,
    DecisionLifecycleFactId,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNeedId,
    DecisionScope,
    DecisionScopeEstablished,
    DecisionScopeRevised,
    DecisionSubject,
    DecisionSubjectRevised,
    DecisionSubstantivelyResolved,
    DecisionVersion,
    DecisionWorkControlBasis,
    DecisionWorkPosture,
    DecisionWorkResumed,
    DecisionWorkWithdrawn,
    DeterminateDecisionLifecycleInterpretation,
    ExternalResolutionBasis,
    HumanInvestmentDecisionEffect,
    InvestmentDecisionId,
    NotYetEffectiveDecisionLifecycleInterpretation,
    OperationId,
    PortfolioId,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
    UnsupportedDecisionNeedBasis,
    initiate_decision,
)
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    create_postgres_engine,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    decision_needs,
    investment_decision_command_receipts,
    investment_decision_lifecycle_facts,
    investment_decisions,
)

from .conftest import PostgresTestTarget, postgres_engine_store, postgres_row_counts

RECORDED_AT = datetime(2026, 9, 17, 5, 0, tzinfo=UTC)
ACTOR_ID = UUID("00000000-0000-4000-8000-000000000001")
PORTFOLIO_A = UUID("00000000-0000-4000-8000-000000000002")
PORTFOLIO_B = UUID("00000000-0000-4000-8000-000000000003")
OPERATION_ID = UUID("00000000-0000-4000-8000-000000000004")
DECISION_ID = UUID("00000000-0000-4000-8000-000000000005")
NEED_ID = UUID("00000000-0000-4000-8000-000000000006")
FACT_ID = UUID("00000000-0000-4000-8000-000000000007")
MUTATION_OPERATION_ID = UUID("00000000-0000-4000-8000-000000000008")
MUTATION_FACT_ID = UUID("00000000-0000-4000-8000-000000000009")
MUTATION_RECORDED_AT = datetime(2026, 9, 17, 6, 0, tzinfo=UTC)
CONCURRENT_OPERATION_ID = UUID("00000000-0000-4000-8000-00000000000a")
CONCURRENT_FACT_ID = UUID("00000000-0000-4000-8000-00000000000b")


def _uuids(*values: UUID) -> Iterator[UUID]:
    yield from values


def _test_envelope(
    operation_id: UUID | OperationId,
    *,
    reference: str,
    effective_at: datetime = MUTATION_RECORDED_AT,
    decision_id: InvestmentDecisionId | None = InvestmentDecisionId(DECISION_ID),
    expected_version: DecisionVersion | None = DecisionVersion(1),
    technical_provenance: TechnicalProvenance | None = None,
) -> DecisionCommandEnvelope:
    operation = (
        operation_id
        if isinstance(operation_id, OperationId)
        else OperationId(operation_id)
    )
    expected_versions = (
        frozenset()
        if decision_id is None or expected_version is None
        else frozenset({ExpectedDecisionVersion(decision_id, expected_version)})
    )
    return DecisionCommandEnvelope(
        operation_id=operation,
        actor_attribution=KnownActorAttribution(ActorId(ACTOR_ID)),
        trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, reference),
        effective_at=effective_at,
        technical_provenance=(
            technical_provenance
            if technical_provenance is not None
            else TechnicalProvenance()
        ),
        expected_versions=expected_versions,
    )


def _subject_revision_command(
    *,
    operation_id: UUID | OperationId = MUTATION_OPERATION_ID,
    subject: str = "Whether to increase the position",
    decision_id: InvestmentDecisionId = InvestmentDecisionId(DECISION_ID),
    reference: str = "request-322",
    effective_at: datetime = MUTATION_RECORDED_AT,
    expected_version: DecisionVersion = DecisionVersion(1),
) -> ReviseDecisionSubjectCommand:
    return ReviseDecisionSubjectCommand(
        envelope=_test_envelope(
            operation_id,
            reference=reference,
            effective_at=effective_at,
            decision_id=decision_id,
            expected_version=expected_version,
        ),
        decision_id=decision_id,
        subject=DecisionSubject(subject),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
    )


def _command(scope: DecisionScope) -> InitiateDecisionCommand:
    return InitiateDecisionCommand(
        envelope=_test_envelope(
            OPERATION_ID,
            reference="request-321",
            effective_at=RECORDED_AT,
            decision_id=None,
            technical_provenance=TechnicalProvenance(
                {
                    TechnicalReference(
                        TechnicalReferenceKind.TRACE,
                        "trace-321",
                    ),
                    TechnicalReference(
                        TechnicalReferenceKind.REQUEST,
                        "request-321",
                    ),
                }
            ),
        ),
        need_statement="Review the durable decision boundary",
        subject=DecisionSubject("Whether to establish the position"),
        scope=scope,
    )


class _StaleCandidateReadStore(PostgresDecisionStore):
    async def find_unresolved_continuity_candidates(
        self, *, known_at: datetime
    ) -> tuple[InvestmentDecisionId, ...]:
        del known_at
        return ()


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


async def _initiate(
    target: PostgresTestTarget,
    scope: DecisionScope,
    *,
    store_type: type[PostgresDecisionStore] = PostgresDecisionStore,
) -> tuple[PostgresDecisionStore, InitiationResult]:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    store = store_type(engine)
    identities = _uuids(DECISION_ID, NEED_ID, FACT_ID)
    service = DecisionInitiationService(
        reader=store,
        store=store,
        now=lambda: RECORDED_AT,
        new_uuid=lambda: next(identities),
    )
    try:
        result = await service.initiate(_command(scope))
        return store, result
    except Exception:
        await engine.dispose()
        raise


@pytest.mark.parametrize(
    "scope",
    [
        DecisionScope.unresolved(),
        DecisionScope.unresolved(PortfolioId(PORTFOLIO_A)),
        DecisionScope.established(
            PortfolioId(PORTFOLIO_B),
            PortfolioId(PORTFOLIO_A),
        ),
    ],
)
def test_no_candidate_initiation_round_trips_after_restart(
    postgres_target: PostgresTestTarget,
    scope: DecisionScope,
) -> None:
    async def scenario() -> None:
        store, result = await _initiate(postgres_target, scope)
        assert result.decision_id == InvestmentDecisionId(DECISION_ID)
        assert result.need_id == DecisionNeedId(NEED_ID)
        assert result.kind is InitiationResultKind.CREATED
        await store._engine.dispose()

        async with postgres_engine_store(postgres_target) as (
            restarted_engine,
            restarted,
        ):
            receipt = await restarted.get_initiation_receipt(OperationId(OPERATION_ID))
            assert receipt is not None
            assert receipt.request.scope == scope
            memory = DecisionMemoryService(reader=restarted, now=lambda: RECORDED_AT)
            view = await memory.current(InvestmentDecisionId(DECISION_ID))
            assert view.need.need_id == DecisionNeedId(NEED_ID)
            assert view.subject == DecisionSubject("Whether to establish the position")
            assert view.scope == scope
            assert view.version.value == 1
            assert isinstance(
                view.lifecycle_interpretation,
                DeterminateDecisionLifecycleInterpretation,
            )
            initiated = view.lifecycle_interpretation.support_fact_ids
            assert initiated == frozenset({DecisionLifecycleFactId(FACT_ID)})
            history = await restarted.load_decision_history(
                InvestmentDecisionId(DECISION_ID)
            )
            assert history is not None
            initiation = history[0]
            assert isinstance(initiation, DecisionInitiated)
            continuity = initiation.continuity
            assert continuity.determination is (
                DecisionInitiationDetermination.NO_CANDIDATES
            )
            assert continuity.candidate_decision_ids == frozenset()
            assert continuity.known_at == RECORDED_AT
            assert history[0].metadata.actor_attribution == (
                KnownActorAttribution(ActorId(ACTOR_ID))
            )
            assert history[0].metadata.technical_provenance == (
                _command(scope).envelope.technical_provenance
            )
            async with restarted_engine.connect() as connection:
                projection = (
                    (await connection.execute(select(investment_decisions)))
                    .mappings()
                    .one()
                )
            assert projection["scope_completeness"] == scope.completeness.value
            assert set(projection["scope_portfolio_ids"]) == {
                identity.value for identity in scope.portfolio_ids
            }
            assert projection["lifecycle_interpretation_kind"] == "DETERMINATE"
            assert projection["lifecycle_disposition"] == "unresolved"
            assert projection["lifecycle_effective_at"] == RECORDED_AT
            assert projection["lifecycle_known_at"] == RECORDED_AT
            assert set(projection["lifecycle_support_fact_ids"]) == {FACT_ID}
            assert projection["work_posture"] == "active"
            assert projection["applicability"] == "operative"
            assert projection["decision_version"] == 1
            assert projection["rebuild_required"] is False

    asyncio.run(scenario())


def test_explicit_create_new_persists_complete_candidate_basis(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        second_decision_id = UUID("00000000-0000-4000-8000-00000000000c")
        second_need_id = UUID("00000000-0000-4000-8000-00000000000d")
        second_fact_id = UUID("00000000-0000-4000-8000-00000000000e")
        operation_id = UUID("00000000-0000-4000-8000-00000000000f")
        identities = _uuids(second_decision_id, second_need_id, second_fact_id)
        command = InitiateDecisionCommand(
            envelope=_test_envelope(
                operation_id,
                reference="request-323",
                decision_id=None,
            ),
            need_statement="Review an independent durable choice",
            subject=DecisionSubject("Whether to reduce the position"),
            scope=DecisionScope.unresolved(),
            continuity=ContinuityDetermination.create_new(
                "The candidate addresses a different coherent choice"
            ),
        )
        service = DecisionInitiationService(
            reader=store,
            store=store,
            now=lambda: MUTATION_RECORDED_AT,
            new_uuid=lambda: next(identities),
        )
        second = await service.initiate(command)
        assert second.decision_id == InvestmentDecisionId(second_decision_id)

        third_at = MUTATION_RECORDED_AT + timedelta(minutes=1)
        third_decision_id = UUID("00000000-0000-4000-8000-000000000020")
        third_need_id = UUID("00000000-0000-4000-8000-000000000021")
        third_fact_id = UUID("00000000-0000-4000-8000-000000000022")
        third_identities = _uuids(
            third_decision_id,
            third_need_id,
            third_fact_id,
        )
        third_command = replace(
            command,
            envelope=replace(
                command.envelope,
                operation_id=OperationId(UUID("00000000-0000-4000-8000-000000000023")),
                effective_at=third_at,
            ),
            need_statement="Review another independent durable choice",
            subject=DecisionSubject("Whether to maintain the position"),
            continuity=ContinuityDetermination.create_new(
                "Both candidates address different coherent choices"
            ),
        )
        result = await DecisionInitiationService(
            reader=store,
            store=store,
            now=lambda: third_at,
            new_uuid=lambda: next(third_identities),
        ).initiate(third_command)
        assert result.decision_id == InvestmentDecisionId(third_decision_id)
        await store._engine.dispose()

        async with postgres_engine_store(postgres_target) as (
            restarted_engine,
            restarted,
        ):
            history = await restarted.load_decision_history(result.decision_id)
            assert history is not None
            initiation = history[0]
            assert isinstance(initiation, DecisionInitiated)
            assert initiation.continuity.determination is (
                DecisionInitiationDetermination.EXPLICIT_CREATE_NEW
            )
            assert initiation.continuity.candidate_decision_ids == frozenset(
                {
                    InvestmentDecisionId(DECISION_ID),
                    InvestmentDecisionId(second_decision_id),
                }
            )
            assert initiation.continuity.known_at == third_at
            assert initiation.continuity.rationale == (
                "Both candidates address different coherent choices"
            )
            assert initiation.metadata.actor_attribution == (
                KnownActorAttribution(ActorId(ACTOR_ID))
            )
            async with restarted_engine.connect() as connection:
                persisted = (
                    (
                        await connection.execute(
                            select(investment_decision_lifecycle_facts).where(
                                investment_decision_lifecycle_facts.c.fact_id
                                == third_fact_id
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
            assert persisted["continuity_determination"] == "explicit_create_new"
            assert set(persisted["continuity_candidate_ids"]) == {
                DECISION_ID,
                second_decision_id,
            }
            assert persisted["continuity_known_at"] == third_at
            assert persisted["continuity_rationale"] == (
                "Both candidates address different coherent choices"
            )
            assert {
                "continuity_lock_id",
                "continuity_token",
                "advisory_lock_key",
                "generation_token",
            }.isdisjoint(persisted)

    asyncio.run(scenario())


def test_continuation_persists_only_a_restart_safe_receipt(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        operation_id = OperationId(UUID("00000000-0000-4000-8000-00000000000c"))
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        command = InitiateDecisionCommand(
            envelope=_test_envelope(
                operation_id,
                reference="request-323",
                decision_id=None,
            ),
            # arid: enable
            need_statement="Recognize the existing coherent choice",
            subject=DecisionSubject("Whether to establish the position"),
            scope=DecisionScope.unresolved(),
            continuity=ContinuityDetermination.continue_existing(
                InvestmentDecisionId(DECISION_ID)
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
            ),
        )
        service = DecisionInitiationService(
            reader=store,
            store=store,
            now=lambda: MUTATION_RECORDED_AT,
            # arid: enable
            new_uuid=lambda: (_ for _ in ()).throw(
                AssertionError("continuation must not allocate identity")
            ),
        )
        result = await service.initiate(command)
        assert result.kind is InitiationResultKind.CONTINUED
        assert result.decision_id == InvestmentDecisionId(DECISION_ID)
        assert result.need_id is None
        await store._engine.dispose()

        async with postgres_engine_store(postgres_target) as (
            restarted_engine,
            restarted,
        ):
            replayed = await DecisionInitiationService(
                reader=restarted,
                store=restarted,
                now=lambda: MUTATION_RECORDED_AT,
            ).initiate(command)
            assert replayed == replace(result, replayed=True)
            counts = await postgres_row_counts(
                restarted_engine,
                decision_needs,
                investment_decisions,
                investment_decision_lifecycle_facts,
                investment_decision_command_receipts,
            )
            assert counts == (1, 1, 1, 2)

    asyncio.run(scenario())


def test_initiation_with_expected_version_commits_nothing(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        store = PostgresDecisionStore(engine)
        command = _command(DecisionScope.unresolved())
        command = replace(
            command,
            envelope=replace(
                command.envelope,
                expected_versions=frozenset(
                    {
                        ExpectedDecisionVersion(
                            InvestmentDecisionId(DECISION_ID),
                            DecisionVersion(1),
                        )
                    }
                ),
            ),
        )
        try:
            with pytest.raises(InvalidDecisionCommand):
                await DecisionInitiationService(
                    reader=store,
                    store=store,
                    now=lambda: RECORDED_AT,
                ).initiate(command)
            counts = await postgres_row_counts(
                engine,
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
                decision_needs,
                investment_decisions,
                investment_decision_lifecycle_facts,
                investment_decision_command_receipts,
            )
            # arid: enable
            assert counts == (0, 0, 0, 0)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_initiation_receipt_replays_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, created = await _initiate(postgres_target, DecisionScope.unresolved())
        await store._engine.dispose()

        restarted, replayed = await _initiate(
            postgres_target, DecisionScope.unresolved()
        )
        try:
            assert replayed == InitiationResult(
                decision_id=created.decision_id,
                need_id=created.need_id,
                kind=created.kind,
                replayed=True,
            )
        finally:
            await restarted._engine.dispose()

    asyncio.run(scenario())


def test_subject_revision_commits_fact_projection_and_receipt_before_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        service = DecisionOrdinaryWorkService(
            store=store,
            now=lambda: MUTATION_RECORDED_AT,
            new_uuid=lambda: MUTATION_FACT_ID,
        )
        command = _subject_revision_command()
        result = await service.revise_subject(command)
        assert result.kind is DecisionMutationResultKind.APPLIED
        assert result.version == DecisionVersion(2)
        await store._engine.dispose()

        async with postgres_engine_store(postgres_target) as (
            restarted_engine,
            restarted,
        ):
            receipt = await restarted.get_mutation_receipt(
                OperationId(MUTATION_OPERATION_ID)
            )
            assert receipt is not None
            assert receipt.result == result
            current = await restarted.load_decision_for_command(
                InvestmentDecisionId(DECISION_ID),
                known_at=MUTATION_RECORDED_AT,
            )
            assert current is not None
            assert current.decision.subject == DecisionSubject(
                "Whether to increase the position"
            )
            assert current.decision.version == DecisionVersion(2)
            assert len(current.decision.history) == 2
            assert current.decision.history[-1].metadata.fact_id == (
                DecisionLifecycleFactId(MUTATION_FACT_ID)
            )

    asyncio.run(scenario())


def test_subject_revision_replays_and_rejects_changed_request_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        command = _subject_revision_command()
        applied = await DecisionOrdinaryWorkService(
            store=store,
            now=lambda: MUTATION_RECORDED_AT,
            new_uuid=lambda: MUTATION_FACT_ID,
        ).revise_subject(command)
        await store._engine.dispose()

        restarted_engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        restarted_service = DecisionOrdinaryWorkService(
            store=PostgresDecisionStore(restarted_engine),
            now=lambda: MUTATION_RECORDED_AT,
        )
        try:
            replayed = await restarted_service.revise_subject(command)
            assert replayed == replace(applied, replayed=True)
            changed = replace(
                command,
                subject=DecisionSubject("A different semantic request"),
            )
            with pytest.raises(IdempotencyConflict):
                await restarted_service.revise_subject(changed)
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())


def test_subject_and_scope_no_ops_persist_receipts_without_changing_decision(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        decision_id = InvestmentDecisionId(DECISION_ID)

        def envelope(operation_id: UUID) -> DecisionCommandEnvelope:
            return _test_envelope(
                operation_id,
                reference="no-op",
                effective_at=MUTATION_RECORDED_AT,
                decision_id=decision_id,
                expected_version=DecisionVersion(1),
            )

        subject_command = ReviseDecisionSubjectCommand(
            envelope(MUTATION_OPERATION_ID),
            decision_id,
            DecisionSubject("Whether to establish the position"),
            DecisionContinuity.SAME_COHERENT_CHOICE,
        )
        scope_operation_id = UUID("00000000-0000-4000-8000-00000000000c")
        scope_command = EstablishOrReviseDecisionScopeCommand(
            envelope(scope_operation_id),
            decision_id,
            DecisionScope.unresolved(),
            DecisionContinuity.SAME_COHERENT_CHOICE,
        )
        service = DecisionOrdinaryWorkService(
            store=store,
            now=lambda: MUTATION_RECORDED_AT,
        )
        subject_result = await service.revise_subject(subject_command)
        scope_result = await service.establish_or_revise_scope(scope_command)
        assert subject_result.kind is DecisionMutationResultKind.NO_OP
        assert scope_result.kind is DecisionMutationResultKind.NO_OP
        assert subject_result.version == scope_result.version == DecisionVersion(1)
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        await store._engine.dispose()

        restarted_engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        # arid: enable
        restarted_store = PostgresDecisionStore(restarted_engine)
        restarted_service = DecisionOrdinaryWorkService(
            store=restarted_store,
            now=lambda: MUTATION_RECORDED_AT,
        )
        try:
            replayed = await restarted_service.revise_subject(subject_command)
            assert replayed == replace(subject_result, replayed=True)
            with pytest.raises(IdempotencyConflict):
                await restarted_service.revise_subject(
                    replace(
                        subject_command,
                        subject=DecisionSubject("A changed semantic request"),
                    )
                )
            state = await restarted_store.load_decision_for_command(
                decision_id,
                known_at=MUTATION_RECORDED_AT,
            )
            assert state is not None
            assert state.decision.version == DecisionVersion(1)
            assert len(state.decision.history) == 1
            assert (
                await restarted_store.get_mutation_receipt(
                    OperationId(scope_operation_id)
                )
                is not None
            )
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())


def test_mutation_rejects_operation_id_already_used_by_initiation(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        service = DecisionOrdinaryWorkService(
            store=store,
            now=lambda: MUTATION_RECORDED_AT,
            new_uuid=lambda: MUTATION_FACT_ID,
        )
        # arid: enable
        command = _subject_revision_command(operation_id=OPERATION_ID)
        try:
            with pytest.raises(IdempotencyConflict):
                await service.revise_subject(command)
            state = await store.load_decision_for_command(
                InvestmentDecisionId(DECISION_ID),
                known_at=MUTATION_RECORDED_AT,
            )
            assert state is not None
            assert len(state.decision.history) == 1
        finally:
            await store._engine.dispose()

    asyncio.run(scenario())


def test_initiation_rejects_mutation_operation_id_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        mutation = _subject_revision_command()
        await DecisionOrdinaryWorkService(
            store=store,
            now=lambda: MUTATION_RECORDED_AT,
            new_uuid=lambda: MUTATION_FACT_ID,
        ).revise_subject(mutation)
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        await store._engine.dispose()

        restarted_engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        # arid: enable
        restarted = PostgresDecisionStore(restarted_engine)
        initiation_at = MUTATION_RECORDED_AT + timedelta(minutes=1)
        base_command = _command(DecisionScope.unresolved())
        command = replace(
            base_command,
            envelope=replace(
                base_command.envelope,
                operation_id=OperationId(MUTATION_OPERATION_ID),
                effective_at=initiation_at,
            ),
            continuity=ContinuityDetermination.create_new(
                "A distinct unresolved choice"
            ),
        )
        identities = _uuids(uuid4(), uuid4(), uuid4())
        try:
            with pytest.raises(IdempotencyConflict):
                await DecisionInitiationService(
                    reader=restarted,
                    store=restarted,
                    now=lambda: initiation_at,
                    new_uuid=lambda: next(identities),
                ).initiate(command)
            counts = await postgres_row_counts(
                restarted_engine,
                investment_decisions,
                investment_decision_command_receipts,
            )
            assert counts == (1, 2)
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())


class _FailAfterMutationLifecycleFactStore(PostgresDecisionStore):
    def _write_completed(self, step: str) -> None:
        if step == "lifecycle_fact":
            raise RuntimeError("injected transaction failure")


class _FailAfterMutationProjectionStore(PostgresDecisionStore):
    def _write_completed(self, step: str) -> None:
        if step == "projection":
            raise RuntimeError("injected transaction failure")


class _FailAfterMutationReceiptStore(PostgresDecisionStore):
    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__(engine)
        self.receipt_write_completed = False

    def _write_completed(self, step: str) -> None:
        if step == "receipt":
            self.receipt_write_completed = True
            raise RuntimeError("injected transaction failure")


@pytest.mark.parametrize(
    "store_type",
    [
        _FailAfterMutationLifecycleFactStore,
        _FailAfterMutationProjectionStore,
        _FailAfterMutationReceiptStore,
    ],
)
def test_mutation_failure_between_semantic_writes_rolls_back_every_change(
    postgres_target: PostgresTestTarget,
    store_type: type[PostgresDecisionStore],
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        await store._engine.dispose()
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        failing = store_type(engine)
        service = DecisionOrdinaryWorkService(
            store=failing,
            now=lambda: MUTATION_RECORDED_AT,
            new_uuid=lambda: MUTATION_FACT_ID,
        )
        command = _subject_revision_command()
        try:
            with pytest.raises(PersistenceUnavailable):
                await service.revise_subject(command)
            state = await failing.load_decision_for_command(
                InvestmentDecisionId(DECISION_ID),
                known_at=MUTATION_RECORDED_AT,
            )
            assert state is not None
            assert state.decision.subject == DecisionSubject(
                "Whether to establish the position"
            )
            assert state.decision.version == DecisionVersion(1)
            assert len(state.decision.history) == 1
            assert (
                await failing.get_mutation_receipt(OperationId(MUTATION_OPERATION_ID))
                is None
            )
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_no_op_receipt_failure_rolls_back_receipt_only_transaction(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        await store._engine.dispose()
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        # arid: enable
        failing = _FailAfterMutationReceiptStore(engine)
        decision_id = InvestmentDecisionId(DECISION_ID)
        command = _subject_revision_command(
            subject="Whether to establish the position",
            decision_id=decision_id,
            reference="no-op",
        )
        try:
            with pytest.raises(PersistenceUnavailable):
                await DecisionOrdinaryWorkService(
                    store=failing,
                    now=lambda: MUTATION_RECORDED_AT,
                ).revise_subject(command)
            assert failing.receipt_write_completed is True
            assert (
                await failing.get_mutation_receipt(OperationId(MUTATION_OPERATION_ID))
                is None
            )
            state = await failing.load_decision_for_command(
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
                decision_id,
                known_at=MUTATION_RECORDED_AT,
            )
            assert state is not None
            assert state.decision.version == DecisionVersion(1)
            assert len(state.decision.history) == 1
            # arid: enable
        finally:
            await engine.dispose()

    asyncio.run(scenario())


class _ConcurrentLoadStore(PostgresDecisionStore):
    def __init__(self, engine: AsyncEngine, barrier: asyncio.Barrier) -> None:
        super().__init__(engine)
        self._barrier = barrier

    async def load_decision_for_command(
        self,
        decision_id: InvestmentDecisionId,
        *,
        known_at: datetime,
    ) -> DecisionCommandState | None:
        state = await super().load_decision_for_command(
            decision_id,
            known_at=known_at,
        )
        await self._barrier.wait()
        return state


def test_concurrent_expected_version_mutations_commit_exactly_once(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        await store._engine.dispose()
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        # arid: enable
        concurrent_store = _ConcurrentLoadStore(engine, asyncio.Barrier(2))

        def command(operation_id: UUID, subject: str) -> ReviseDecisionSubjectCommand:
            return _subject_revision_command(
                operation_id=operation_id,
                subject=subject,
                reference=f"request-{operation_id}",
            )

        first = DecisionOrdinaryWorkService(
            store=concurrent_store,
            now=lambda: MUTATION_RECORDED_AT,
            new_uuid=lambda: MUTATION_FACT_ID,
        ).revise_subject(
            command(MUTATION_OPERATION_ID, "Whether to increase the position")
        )
        second = DecisionOrdinaryWorkService(
            store=concurrent_store,
            now=lambda: MUTATION_RECORDED_AT,
            new_uuid=lambda: CONCURRENT_FACT_ID,
        ).revise_subject(
            command(CONCURRENT_OPERATION_ID, "Whether to decrease the position")
        )
        try:
            outcomes = await asyncio.gather(first, second, return_exceptions=True)
            assert sum(not isinstance(item, Exception) for item in outcomes) == 1
            assert sum(isinstance(item, ConcurrencyConflict) for item in outcomes) == 1
            state = await PostgresDecisionStore(engine).load_decision_for_command(
                InvestmentDecisionId(DECISION_ID),
                known_at=MUTATION_RECORDED_AT,
            )
            assert state is not None
            assert state.decision.version == DecisionVersion(2)
            assert len(state.decision.history) == 2
            receipts = [
                await concurrent_store.get_mutation_receipt(OperationId(operation_id))
                for operation_id in (MUTATION_OPERATION_ID, CONCURRENT_OPERATION_ID)
            ]
            assert sum(receipt is not None for receipt in receipts) == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.parametrize("same_request", [True, False])
def test_concurrent_same_operation_replays_or_reports_idempotency_conflict(
    postgres_target: PostgresTestTarget,
    *,
    same_request: bool,
) -> None:
    async def scenario() -> None:
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        await store._engine.dispose()
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        concurrent_store = _ConcurrentLoadStore(engine, asyncio.Barrier(2))
        # arid: enable
        decision_id = InvestmentDecisionId(DECISION_ID)

        def command(subject: str) -> ReviseDecisionSubjectCommand:
            return _subject_revision_command(
                subject=subject,
                decision_id=decision_id,
                reference="same-operation-race",
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
            )

        first = DecisionOrdinaryWorkService(
            store=concurrent_store,
            now=lambda: MUTATION_RECORDED_AT,
            new_uuid=lambda: MUTATION_FACT_ID,
            # arid: enable
        ).revise_subject(command("Whether to increase the position"))
        second_subject = (
            "Whether to increase the position"
            if same_request
            else "Whether to decrease the position"
            # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
            # arid: disable
        )
        second = DecisionOrdinaryWorkService(
            store=concurrent_store,
            now=lambda: MUTATION_RECORDED_AT,
            new_uuid=lambda: CONCURRENT_FACT_ID,
            # arid: enable
        ).revise_subject(command(second_subject))
        try:
            outcomes = await asyncio.gather(first, second, return_exceptions=True)
            if same_request:
                assert all(not isinstance(item, Exception) for item in outcomes)
                results = [
                    item
                    for item in outcomes
                    if isinstance(item, DecisionMutationResult)
                ]
                assert sum(result.replayed for result in results) == 1
            else:
                assert sum(not isinstance(item, Exception) for item in outcomes) == 1
                assert (
                    sum(isinstance(item, IdempotencyConflict) for item in outcomes) == 1
                )
            state = await PostgresDecisionStore(engine).load_decision_for_command(
                decision_id,
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
                known_at=MUTATION_RECORDED_AT,
            )
            assert state is not None
            assert state.decision.version == DecisionVersion(2)
            assert len(state.decision.history) == 2
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_all_ordinary_lifecycle_mutations_round_trip_with_distinct_redeferral(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        # arid: enable
        mutation_times = iter(
            MUTATION_RECORDED_AT + timedelta(hours=offset) for offset in range(9)
        )
        fact_ids = iter(
            UUID(f"00000000-0000-4000-8000-{value:012x}") for value in range(9, 18)
        )
        operation_ids = iter(
            UUID(f"00000000-0000-4000-8000-{value:012x}") for value in range(18, 27)
        )
        service = DecisionOrdinaryWorkService(
            store=store,
            now=lambda: next(mutation_times),
            new_uuid=lambda: next(fact_ids),
        )
        decision_id = InvestmentDecisionId(DECISION_ID)

        def envelope(version: int, effective_at: datetime) -> DecisionCommandEnvelope:
            return _test_envelope(
                next(operation_ids),
                reference=f"ordinary-{version}",
                effective_at=effective_at,
                decision_id=decision_id,
                expected_version=DecisionVersion(version),
                technical_provenance=TechnicalProvenance(
                    {
                        TechnicalReference(
                            TechnicalReferenceKind.TRACE,
                            f"ordinary-trace-{version}",
                        )
                    }
                ),
            )

        instants = [
            MUTATION_RECORDED_AT + timedelta(hours=offset) for offset in range(9)
        ]
        await service.revise_subject(
            ReviseDecisionSubjectCommand(
                envelope(1, instants[0]),
                decision_id,
                DecisionSubject("Whether to increase the position"),
                DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
        await service.establish_or_revise_scope(
            EstablishOrReviseDecisionScopeCommand(
                envelope(2, instants[1]),
                decision_id,
                DecisionScope.established(PortfolioId(PORTFOLIO_A)),
                DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
        await service.establish_or_revise_scope(
            EstablishOrReviseDecisionScopeCommand(
                envelope(3, instants[2]),
                decision_id,
                DecisionScope.established(
                    PortfolioId(PORTFOLIO_A),
                    PortfolioId(PORTFOLIO_B),
                ),
                DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
        await service.apply_human_deferral(
            ApplyHumanDeferralCommand(
                envelope(4, instants[3]),
                decision_id,
                TrustedHumanInvestmentDecisionBasis(
                    "human-deferral-1",
                    HumanInvestmentDecisionEffect.DEFERRING,
                ),
            )
        )
        await service.apply_human_deferral(
            ApplyHumanDeferralCommand(
                envelope(5, instants[4]),
                decision_id,
                TrustedHumanInvestmentDecisionBasis(
                    "human-deferral-2",
                    HumanInvestmentDecisionEffect.DEFERRING,
                ),
            )
        )
        await service.resume_work(
            ResumeDecisionWorkCommand(
                envelope(6, instants[5]),
                decision_id,
                DecisionWorkControlBasis("resume-after-deferral"),
                DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
        await service.withdraw_work(
            WithdrawDecisionWorkCommand(
                envelope(7, instants[6]),
                decision_id,
                DecisionWorkControlBasis("withdraw-work"),
            )
        )
        await service.resume_work(
            ResumeDecisionWorkCommand(
                envelope(8, instants[7]),
                decision_id,
                DecisionWorkControlBasis("resume-withdrawn-work"),
                DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
        result = await service.apply_external_resolution(
            ApplyExternalResolutionCommand(
                envelope(9, instants[8]),
                decision_id,
                ExternalResolutionBasis("external-resolution"),
            )
        )
        assert result.version == DecisionVersion(10)
        await store._engine.dispose()

        async with postgres_engine_store(postgres_target) as (
            restarted_engine,
            restarted,
        ):
            state = await restarted.load_decision_for_command(
                decision_id,
                known_at=instants[-1],
            )
            assert state is not None
            history = state.decision.history
            assert [fact.metadata.sequence.value for fact in history] == list(
                range(1, 11)
            )
            assert [fact.metadata.decision_version.value for fact in history] == list(
                range(1, 11)
            )
            assert [type(fact) for fact in history[1:]] == [
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
                DecisionSubjectRevised,
                DecisionScopeEstablished,
                DecisionScopeRevised,
                DecisionDeferred,
                # arid: enable
                DecisionDeferred,
                DecisionWorkResumed,
                DecisionWorkWithdrawn,
                DecisionWorkResumed,
                DecisionExternallyResolved,
            ]
            deferrals = [fact for fact in history if isinstance(fact, DecisionDeferred)]
            assert [fact.basis.decision_reference for fact in deferrals] == [
                "human-deferral-1",
                "human-deferral-2",
            ]
            assert state.decision.subject == DecisionSubject(
                "Whether to increase the position"
            )
            assert state.decision.scope == DecisionScope.established(
                PortfolioId(PORTFOLIO_A),
                PortfolioId(PORTFOLIO_B),
            )
            assert state.decision.version == DecisionVersion(10)
            for version, fact in enumerate(history[1:], start=1):
                assert fact.metadata.actor_attribution == KnownActorAttribution(
                    ActorId(ACTOR_ID)
                )
                assert fact.metadata.trigger.reference == f"ordinary-{version}"
                assert fact.metadata.technical_provenance == TechnicalProvenance(
                    {
                        TechnicalReference(
                            TechnicalReferenceKind.TRACE,
                            f"ordinary-trace-{version}",
                        )
                    }
                )

    asyncio.run(scenario())


def test_ordinary_mutation_rejects_unwitnessed_projection_version_ahead_of_history(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        decision_id = InvestmentDecisionId(DECISION_ID)
        async with store._engine.begin() as connection:
            await connection.execute(
                investment_decisions.update()
                .where(investment_decisions.c.decision_id == DECISION_ID)
                .values(decision_version=2)
            )
        try:
            with pytest.raises(ConcurrencyConflict):
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
                await DecisionOrdinaryWorkService(
                    store=store,
                    now=lambda: MUTATION_RECORDED_AT,
                    new_uuid=lambda: MUTATION_FACT_ID,
                    # arid: enable
                ).revise_subject(
                    _subject_revision_command(
                        decision_id=decision_id,
                        reference="after-unwitnessed-projection-version",
                        expected_version=DecisionVersion(2),
                    )
                )
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        finally:
            await store._engine.dispose()

    asyncio.run(scenario())


def test_concurrent_future_corrections_use_history_tail_when_version_does_not_advance(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        # arid: enable
        decision_id = InvestmentDecisionId(DECISION_ID)
        resolution_fact_id = DecisionLifecycleFactId(MUTATION_FACT_ID)
        resolution = TrustedHumanInvestmentDecisionBasis(
            "human-resolution",
            HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
        )
        resolution_service = DecisionOrdinaryWorkService(
            store=store,
            now=lambda: MUTATION_RECORDED_AT,
            new_uuid=lambda: MUTATION_FACT_ID,
        )
        await resolution_service.apply_substantive_resolution(
            ApplySubstantiveResolutionCommand(
                _test_envelope(
                    MUTATION_OPERATION_ID,
                    reference="resolution",
                    effective_at=MUTATION_RECORDED_AT,
                    decision_id=decision_id,
                    expected_version=DecisionVersion(1),
                ),
                decision_id,
                resolution,
            )
        )
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        await store._engine.dispose()

        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        concurrent_store = _ConcurrentLoadStore(engine, asyncio.Barrier(2))
        # arid: enable
        correction_recorded_at = MUTATION_RECORDED_AT + timedelta(hours=1)
        correction_effective_at = correction_recorded_at + timedelta(hours=2)

        def command(
            operation: UUID, reference: str
        ) -> RecordDecisionLifecycleCorrectionCommand:
            return RecordDecisionLifecycleCorrectionCommand(
                envelope=_test_envelope(
                    operation,
                    reference=reference,
                    effective_at=correction_effective_at,
                    decision_id=decision_id,
                    expected_version=DecisionVersion(2),
                ),
                decision_id=decision_id,
                target_fact_id=resolution_fact_id,
                effect=DecisionLifecycleCorrectionEffect.QUALIFY,
                correction_basis=DecisionLifecycleCorrectionBasis(reference),
                replacement_disposition=(
                    DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
                ),
                replacement_basis=TrustedHumanInvestmentDecisionBasis(
                    f"{reference}-replacement",
                    HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
                ),
            )

        first = DecisionLifecycleCorrectionService(
            store=concurrent_store,
            now=lambda: correction_recorded_at,
            new_uuid=lambda: CONCURRENT_FACT_ID,
        ).record_lifecycle_correction(command(CONCURRENT_OPERATION_ID, "correction-a"))
        second_operation = UUID("00000000-0000-4000-8000-00000000000c")
        second_fact = UUID("00000000-0000-4000-8000-00000000000d")
        second = DecisionLifecycleCorrectionService(
            store=concurrent_store,
            now=lambda: correction_recorded_at,
            new_uuid=lambda: second_fact,
        ).record_lifecycle_correction(command(second_operation, "correction-b"))
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        try:
            outcomes = await asyncio.gather(first, second, return_exceptions=True)
            assert sum(not isinstance(item, Exception) for item in outcomes) == 1
            assert sum(isinstance(item, ConcurrencyConflict) for item in outcomes) == 1
            state = await PostgresDecisionStore(engine).load_decision_for_command(
                # arid: enable
                decision_id,
                known_at=correction_recorded_at,
            )
            assert state is not None
            assert [
                fact.metadata.sequence.value for fact in state.decision.history
            ] == [
                1,
                2,
                3,
            ]
            assert [
                fact.metadata.decision_version.value for fact in state.decision.history
            ] == [
                1,
                2,
                2,
            ]
            assert isinstance(state.decision.history[-2], DecisionSubstantivelyResolved)
            assert isinstance(state.decision.history[-1], DecisionLifecycleCorrected)
            receipts = [
                await concurrent_store.get_mutation_receipt(OperationId(operation))
                for operation in (CONCURRENT_OPERATION_ID, second_operation)
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
            ]
            assert sum(receipt is not None for receipt in receipts) == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_concurrent_same_operation_future_correction_replays_after_tail_wait(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        # arid: enable
        decision_id = InvestmentDecisionId(DECISION_ID)
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        await DecisionOrdinaryWorkService(
            store=store,
            now=lambda: MUTATION_RECORDED_AT,
            new_uuid=lambda: MUTATION_FACT_ID,
            # arid: enable
        ).apply_substantive_resolution(
            # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
            # arid: disable
            ApplySubstantiveResolutionCommand(
                _test_envelope(
                    MUTATION_OPERATION_ID,
                    reference="resolution",
                    # arid: enable
                    decision_id=decision_id,
                ),
                decision_id,
                TrustedHumanInvestmentDecisionBasis(
                    "human-resolution",
                    HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
                ),
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
            )
        )
        await store._engine.dispose()

        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        concurrent_store = _ConcurrentLoadStore(engine, asyncio.Barrier(2))
        # arid: enable
        correction_operation_id = UUID("00000000-0000-4000-8000-00000000000c")
        correction_recorded_at = MUTATION_RECORDED_AT + timedelta(hours=1)
        correction_effective_at = correction_recorded_at + timedelta(hours=2)
        command = RecordDecisionLifecycleCorrectionCommand(
            envelope=_test_envelope(
                correction_operation_id,
                reference="same-correction-race",
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
                effective_at=correction_effective_at,
                decision_id=decision_id,
                expected_version=DecisionVersion(2),
            ),
            decision_id=decision_id,
            # arid: enable
            target_fact_id=DecisionLifecycleFactId(MUTATION_FACT_ID),
            effect=DecisionLifecycleCorrectionEffect.QUALIFY,
            correction_basis=DecisionLifecycleCorrectionBasis("correction"),
            replacement_disposition=DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED,
            replacement_basis=TrustedHumanInvestmentDecisionBasis(
                "replacement",
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
                HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
            ),
        )
        first = DecisionLifecycleCorrectionService(
            store=concurrent_store,
            now=lambda: correction_recorded_at,
            new_uuid=lambda: CONCURRENT_FACT_ID,
            # arid: enable
        ).record_lifecycle_correction(command)
        second = DecisionLifecycleCorrectionService(
            store=concurrent_store,
            now=lambda: correction_recorded_at,
            new_uuid=lambda: UUID("00000000-0000-4000-8000-00000000000d"),
        ).record_lifecycle_correction(command)
        try:
            outcomes = await asyncio.gather(first, second, return_exceptions=True)
            assert all(not isinstance(item, Exception) for item in outcomes)
            results = [
                item for item in outcomes if isinstance(item, DecisionMutationResult)
            ]
            assert sum(result.replayed for result in results) == 1
            assert all(result.version == DecisionVersion(2) for result in results)
            # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
            # arid: disable
            state = await PostgresDecisionStore(engine).load_decision_for_command(
                decision_id,
                known_at=correction_recorded_at,
            )
            assert state is not None
            # arid: enable
            assert len(state.decision.history) == 3
            assert [
                fact.metadata.decision_version.value for fact in state.decision.history
            ] == [1, 2, 2]
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_unsupported_need_retraction_and_disconfirmation_round_trip(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        decision_id = InvestmentDecisionId(DECISION_ID)
        # arid: enable
        correction_service = DecisionLifecycleCorrectionService(
            store=store,
            now=lambda: MUTATION_RECORDED_AT,
            new_uuid=lambda: MUTATION_FACT_ID,
        )
        retracted = await correction_service.retract_unsupported_decision_need(
            RetractUnsupportedDecisionNeedCommand(
                envelope=_test_envelope(
                    MUTATION_OPERATION_ID,
                    reference="unsupported-need",
                    effective_at=MUTATION_RECORDED_AT,
                    decision_id=decision_id,
                    expected_version=DecisionVersion(1),
                ),
                decision_id=decision_id,
                correction_basis=DecisionLifecycleCorrectionBasis("need-correction"),
                unsupported_need_basis=UnsupportedDecisionNeedBasis(
                    "need-was-unsupported"
                ),
            )
        )
        assert retracted.version == DecisionVersion(2)
        restored_at = MUTATION_RECORDED_AT + timedelta(hours=1)
        restored_fact_id = UUID("00000000-0000-4000-8000-00000000000a")
        restored_operation_id = UUID("00000000-0000-4000-8000-00000000000b")
        restored = await DecisionLifecycleCorrectionService(
            store=store,
            now=lambda: restored_at,
            new_uuid=lambda: restored_fact_id,
        ).record_lifecycle_correction(
            RecordDecisionLifecycleCorrectionCommand(
                envelope=_test_envelope(
                    restored_operation_id,
                    reference="restore-need",
                    effective_at=restored_at,
                    # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                    # arid: disable
                    decision_id=decision_id,
                    expected_version=DecisionVersion(2),
                ),
                decision_id=decision_id,
                target_fact_id=DecisionLifecycleFactId(MUTATION_FACT_ID),
                # arid: enable
                effect=DecisionLifecycleCorrectionEffect.DISCONFIRM,
                correction_basis=DecisionLifecycleCorrectionBasis(
                    "restore-need-correction"
                ),
            )
        )
        assert restored.version == DecisionVersion(3)
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        await store._engine.dispose()

        async with postgres_engine_store(postgres_target) as (
            restarted_engine,
            restarted,
        ):
            state = await restarted.load_decision_for_command(
                decision_id,
                # arid: enable
                known_at=restored_at,
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
            )
            assert state is not None
            assert [
                fact.metadata.sequence.value for fact in state.decision.history
            ] == [
                1,
                2,
                3,
            ]
            # arid: enable
            first_correction = state.decision.history[-2]
            second_correction = state.decision.history[-1]
            assert isinstance(first_correction, DecisionLifecycleCorrected)
            assert first_correction.replacement_disposition is (
                DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED
            )
            assert first_correction.replacement_basis == UnsupportedDecisionNeedBasis(
                "need-was-unsupported"
            )
            assert isinstance(second_correction, DecisionLifecycleCorrected)
            assert second_correction.effect is (
                DecisionLifecycleCorrectionEffect.DISCONFIRM
            )
            assert second_correction.replacement_basis is None
            receipt = await restarted.get_mutation_receipt(
                OperationId(restored_operation_id)
            )
            assert receipt is not None
            assert receipt.result == restored

    # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
    # arid: disable
    asyncio.run(scenario())


def test_decision_memory_distinguishes_knowledge_and_effective_boundaries(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        store = PostgresDecisionStore(engine)
        # arid: enable
        identities = _uuids(DECISION_ID, NEED_ID, FACT_ID)
        future_effective_at = RECORDED_AT + timedelta(hours=2)
        command = _command(DecisionScope.unresolved())
        command = replace(
            command,
            envelope=replace(command.envelope, effective_at=future_effective_at),
        )
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        await DecisionInitiationService(
            reader=store,
            store=store,
            now=lambda: RECORDED_AT,
            new_uuid=lambda: next(identities),
            # arid: enable
        ).initiate(command)
        await engine.dispose()

        restarted_engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        memory = DecisionMemoryService(
            reader=PostgresDecisionStore(restarted_engine),
            now=lambda: future_effective_at + timedelta(hours=1),
        )
        decision_id = InvestmentDecisionId(DECISION_ID)
        before_recording = RECORDED_AT - timedelta(minutes=1)
        before_effective = RECORDED_AT + timedelta(hours=1)
        try:
            with pytest.raises(DecisionNotFound):
                await memory.as_known_at(decision_id, before_recording)

            not_yet_effective = await memory.as_known_at(
                decision_id,
                before_effective,
            )
            assert isinstance(
                not_yet_effective.lifecycle_interpretation,
                NotYetEffectiveDecisionLifecycleInterpretation,
            )
            assert not_yet_effective.lifecycle_interpretation.effective_at == (
                before_effective
            )
            assert not_yet_effective.lifecycle_interpretation.known_at == (
                before_effective
            )
            assert not_yet_effective.work_posture is None

            known_future = await memory.effective_at(
                decision_id,
                future_effective_at,
                known_at=before_effective,
            )
            assert isinstance(
                known_future.lifecycle_interpretation,
                DeterminateDecisionLifecycleInterpretation,
            )
            assert known_future.lifecycle_interpretation.disposition is (
                DecisionLifecycleDisposition.UNRESOLVED
            )
            assert known_future.lifecycle_interpretation.support_fact_ids == frozenset(
                {DecisionLifecycleFactId(FACT_ID)}
            )

            as_known = await memory.as_known_at(decision_id, future_effective_at)
            effective = await memory.effective_at(
                decision_id,
                future_effective_at,
                known_at=future_effective_at,
            )
            assert as_known == effective
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())


def test_decision_memory_reconstructs_late_sibling_corrections_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        decision_id = InvestmentDecisionId(DECISION_ID)
        resolution_fact_id = DecisionLifecycleFactId(MUTATION_FACT_ID)
        await DecisionOrdinaryWorkService(
            store=store,
            now=lambda: MUTATION_RECORDED_AT,
            new_uuid=lambda: MUTATION_FACT_ID,
        ).apply_substantive_resolution(
            ApplySubstantiveResolutionCommand(
                _test_envelope(
                    MUTATION_OPERATION_ID,
                    # arid: enable
                    reference="initial-resolution",
                    # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                    # arid: disable
                    effective_at=MUTATION_RECORDED_AT,
                    decision_id=decision_id,
                    expected_version=DecisionVersion(1),
                ),
                decision_id,
                # arid: enable
                TrustedHumanInvestmentDecisionBasis(
                    "initial-resolution",
                    HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
                ),
            )
        )

        tied_recording_at = RECORDED_AT + timedelta(hours=3)
        restoration_recorded_at = tied_recording_at + timedelta(hours=1)
        external_operation = UUID("00000000-0000-4000-8000-00000000000c")
        external_fact = UUID("00000000-0000-4000-8000-00000000000d")
        equivalent_operation = UUID("00000000-0000-4000-8000-00000000000e")
        equivalent_fact = UUID("00000000-0000-4000-8000-00000000000f")
        restoration_operation = UUID("00000000-0000-4000-8000-000000000010")
        restoration_fact = UUID("00000000-0000-4000-8000-000000000011")

        external = await DecisionLifecycleCorrectionService(
            store=store,
            now=lambda: tied_recording_at,
            new_uuid=lambda: external_fact,
        ).record_lifecycle_correction(
            RecordDecisionLifecycleCorrectionCommand(
                envelope=_test_envelope(
                    external_operation,
                    reference="late-external-qualification",
                    effective_at=RECORDED_AT + timedelta(minutes=30),
                    # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                    # arid: disable
                    decision_id=decision_id,
                    expected_version=DecisionVersion(2),
                ),
                decision_id=decision_id,
                target_fact_id=resolution_fact_id,
                effect=DecisionLifecycleCorrectionEffect.QUALIFY,
                # arid: enable
                correction_basis=DecisionLifecycleCorrectionBasis(
                    "late-external-qualification"
                ),
                replacement_disposition=(
                    DecisionLifecycleDisposition.EXTERNALLY_RESOLVED
                ),
                replacement_basis=ExternalResolutionBasis("late-external-resolution"),
            )
        )
        assert external.version == DecisionVersion(3)

        equivalent = await DecisionLifecycleCorrectionService(
            store=store,
            now=lambda: tied_recording_at,
            new_uuid=lambda: equivalent_fact,
        ).record_lifecycle_correction(
            RecordDecisionLifecycleCorrectionCommand(
                envelope=_test_envelope(
                    equivalent_operation,
                    reference="equivalent-substantive-qualification",
                    effective_at=MUTATION_RECORDED_AT,
                    decision_id=decision_id,
                    expected_version=external.version,
                    # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                    # arid: disable
                ),
                decision_id=decision_id,
                target_fact_id=resolution_fact_id,
                effect=DecisionLifecycleCorrectionEffect.QUALIFY,
                correction_basis=DecisionLifecycleCorrectionBasis(
                    # arid: enable
                    "equivalent-substantive-qualification"
                ),
                replacement_disposition=(
                    DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
                ),
                replacement_basis=TrustedHumanInvestmentDecisionBasis(
                    "equivalent-substantive-resolution",
                    HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
                ),
            )
        )
        assert equivalent.version == DecisionVersion(4)

        restored = await DecisionLifecycleCorrectionService(
            store=store,
            now=lambda: restoration_recorded_at,
            new_uuid=lambda: restoration_fact,
        ).record_lifecycle_correction(
            RecordDecisionLifecycleCorrectionCommand(
                envelope=_test_envelope(
                    restoration_operation,
                    reference="restore-external-branch",
                    effective_at=restoration_recorded_at,
                    decision_id=decision_id,
                    expected_version=equivalent.version,
                ),
                decision_id=decision_id,
                target_fact_id=DecisionLifecycleFactId(external_fact),
                effect=DecisionLifecycleCorrectionEffect.DISCONFIRM,
                correction_basis=DecisionLifecycleCorrectionBasis(
                    "restore-external-branch"
                ),
            )
        )
        assert restored.version == DecisionVersion(5)
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        await store._engine.dispose()

        restarted_engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        memory = DecisionMemoryService(
            reader=PostgresDecisionStore(restarted_engine),
            # arid: enable
            now=lambda: restoration_recorded_at,
        )
        try:
            before_corrections = await memory.as_known_at(
                decision_id,
                MUTATION_RECORDED_AT,
            )
            assert isinstance(
                before_corrections.lifecycle_interpretation,
                DeterminateDecisionLifecycleInterpretation,
            )
            assert before_corrections.lifecycle_interpretation.disposition is (
                DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
            )

            late_effective = await memory.effective_at(
                decision_id,
                RECORDED_AT + timedelta(minutes=45),
                known_at=tied_recording_at,
            )
            assert isinstance(
                late_effective.lifecycle_interpretation,
                DeterminateDecisionLifecycleInterpretation,
            )
            assert late_effective.lifecycle_interpretation.disposition is (
                DecisionLifecycleDisposition.EXTERNALLY_RESOLVED
            )
            assert late_effective.lifecycle_interpretation.support_fact_ids == (
                frozenset({DecisionLifecycleFactId(external_fact)})
            )

            contested = await memory.effective_at(
                decision_id,
                tied_recording_at,
                known_at=tied_recording_at,
            )
            assert isinstance(
                contested.lifecycle_interpretation,
                ContestedDecisionLifecycleInterpretation,
            )
            assert contested.lifecycle_interpretation.support_fact_ids == frozenset(
                {
                    DecisionLifecycleFactId(external_fact),
                    DecisionLifecycleFactId(equivalent_fact),
                }
            )

            current = await memory.current(decision_id)
            assert current.version == DecisionVersion(5)
            assert isinstance(
                current.lifecycle_interpretation,
                DeterminateDecisionLifecycleInterpretation,
            )
            assert current.lifecycle_interpretation.disposition is (
                DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
            )
            assert current.lifecycle_interpretation.support_fact_ids == frozenset(
                {
                    resolution_fact_id,
                    DecisionLifecycleFactId(equivalent_fact),
                    DecisionLifecycleFactId(restoration_fact),
                }
            )
            assert DecisionLifecycleFactId(external_fact) not in (
                current.lifecycle_interpretation.support_fact_ids
            )

            history = await memory.history(decision_id)
            assert [
                fact.metadata.sequence.value for fact in history.lifecycle_facts
            ] == [1, 2, 3, 4, 5]
            assert history.lifecycle_facts[1].metadata.recorded_at < (
                history.lifecycle_facts[2].metadata.recorded_at
            )
            assert history.lifecycle_facts[2].metadata.recorded_at == (
                history.lifecycle_facts[3].metadata.recorded_at
            )
            assert (
                history.lifecycle_facts[1]
                == (
                    await PostgresDecisionStore(restarted_engine).load_decision_history(
                        decision_id
                    )
                )[1]
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
            )
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())


def test_decision_memory_restores_deferred_posture_after_disconfirmation(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        decision_id = InvestmentDecisionId(DECISION_ID)
        # arid: enable
        deferred_at = RECORDED_AT + timedelta(minutes=30)
        deferral_operation = UUID("00000000-0000-4000-8000-000000000012")
        deferral_fact = UUID("00000000-0000-4000-8000-000000000013")
        resolution_operation = UUID("00000000-0000-4000-8000-000000000014")
        resolution_fact = UUID("00000000-0000-4000-8000-000000000015")
        correction_operation = UUID("00000000-0000-4000-8000-000000000016")
        correction_fact = UUID("00000000-0000-4000-8000-000000000017")

        deferred = await DecisionOrdinaryWorkService(
            store=store,
            now=lambda: deferred_at,
            new_uuid=lambda: deferral_fact,
        ).apply_human_deferral(
            ApplyHumanDeferralCommand(
                _test_envelope(
                    deferral_operation,
                    reference="defer-before-resolution",
                    effective_at=deferred_at,
                    # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                    # arid: disable
                    decision_id=decision_id,
                    expected_version=DecisionVersion(1),
                ),
                decision_id,
                TrustedHumanInvestmentDecisionBasis(
                    # arid: enable
                    "defer-before-resolution",
                    HumanInvestmentDecisionEffect.DEFERRING,
                ),
            )
        )
        resolved_at = deferred_at + timedelta(minutes=30)
        resolved = await DecisionOrdinaryWorkService(
            store=store,
            now=lambda: resolved_at,
            new_uuid=lambda: resolution_fact,
        ).apply_substantive_resolution(
            ApplySubstantiveResolutionCommand(
                _test_envelope(
                    resolution_operation,
                    reference="resolve-after-deferral",
                    effective_at=resolved_at,
                    decision_id=decision_id,
                    expected_version=deferred.version,
                ),
                decision_id,
                TrustedHumanInvestmentDecisionBasis(
                    "resolve-after-deferral",
                    HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
                ),
            )
        )
        corrected_at = resolved_at + timedelta(minutes=30)
        corrected = await DecisionLifecycleCorrectionService(
            store=store,
            now=lambda: corrected_at,
            new_uuid=lambda: correction_fact,
        ).record_lifecycle_correction(
            RecordDecisionLifecycleCorrectionCommand(
                envelope=_test_envelope(
                    correction_operation,
                    reference="disconfirm-resolution",
                    effective_at=corrected_at,
                    decision_id=decision_id,
                    expected_version=resolved.version,
                ),
                decision_id=decision_id,
                target_fact_id=DecisionLifecycleFactId(resolution_fact),
                effect=DecisionLifecycleCorrectionEffect.DISCONFIRM,
                correction_basis=DecisionLifecycleCorrectionBasis(
                    "disconfirm-resolution"
                ),
            )
        )
        assert corrected.version == DecisionVersion(4)
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        await store._engine.dispose()

        restarted_engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        # arid: enable
        try:
            current = await DecisionMemoryService(
                reader=PostgresDecisionStore(restarted_engine),
                now=lambda: corrected_at,
            ).current(decision_id)
            # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
            # arid: disable
            assert isinstance(
                current.lifecycle_interpretation,
                DeterminateDecisionLifecycleInterpretation,
            )
            assert current.lifecycle_interpretation.disposition is (
                # arid: enable
                DecisionLifecycleDisposition.UNRESOLVED
            )
            assert current.work_posture is DecisionWorkPosture.DEFERRED
            assert current.lifecycle_interpretation.support_fact_ids == frozenset(
                {
                    DecisionLifecycleFactId(FACT_ID),
                    DecisionLifecycleFactId(correction_fact),
                }
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
            )
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())


def test_initiation_receipt_rejects_changed_request_reuse(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        await store._engine.dispose()

        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        # arid: enable
        restarted = PostgresDecisionStore(engine)
        service = DecisionInitiationService(
            reader=restarted,
            store=restarted,
            now=lambda: RECORDED_AT,
        )
        original = _command(DecisionScope.unresolved())
        changed = InitiateDecisionCommand(
            envelope=original.envelope,
            need_statement=original.need_statement,
            subject=DecisionSubject("A changed semantic request"),
            scope=original.scope,
        )
        try:
            with pytest.raises(IdempotencyConflict):
                await service.initiate(changed)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_restart_detects_projection_drift_without_trusting_projection(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(
            postgres_target,
            DecisionScope.unresolved(PortfolioId(PORTFOLIO_A)),
        )
        async with store._engine.begin() as connection:
            await connection.execute(
                investment_decisions.update().values(
                    subject_statement="corrupted projection",
                    scope_completeness="established",
                    scope_portfolio_ids=[PORTFOLIO_B],
                )
            )
        await store._engine.dispose()

        async with postgres_engine_store(postgres_target) as (
            restarted_engine,
            restarted,
        ):
            with pytest.raises(PersistenceUnavailable):
                await DecisionMemoryService(
                    reader=restarted,
                    now=lambda: RECORDED_AT,
                ).current(InvestmentDecisionId(DECISION_ID))
            history = await restarted.load_decision_history(
                InvestmentDecisionId(DECISION_ID)
            )
            assert history is not None
            assert history[0].subject == DecisionSubject(
                "Whether to establish the position"
            )
            assert history[0].scope == DecisionScope.unresolved(
                PortfolioId(PORTFOLIO_A)
            )

    asyncio.run(scenario())


def test_restart_detects_version_only_projection_drift(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        async with store._engine.begin() as connection:
            await connection.execute(
                investment_decisions.update().values(decision_version=2)
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
            )
        await store._engine.dispose()

        async with postgres_engine_store(postgres_target) as (
            restarted_engine,
            restarted,
        ):
            with pytest.raises(PersistenceUnavailable):
                await DecisionMemoryService(
                    reader=restarted,
                    now=lambda: RECORDED_AT,
                ).current(InvestmentDecisionId(DECISION_ID))
            history = await restarted.load_decision_history(
                InvestmentDecisionId(DECISION_ID)
            )
            assert history is not None
            # arid: enable
            assert history[-1].metadata.decision_version == DecisionVersion(1)

    # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
    # arid: disable
    asyncio.run(scenario())


def test_commit_revalidates_stale_empty_candidate_basis(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        await store._engine.dispose()

        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        # arid: enable
        stale_store = _StaleCandidateReadStore(engine)
        identities = _uuids(
            UUID("00000000-0000-4000-8000-000000000008"),
            UUID("00000000-0000-4000-8000-000000000009"),
            UUID("00000000-0000-4000-8000-00000000000a"),
        )
        service = DecisionInitiationService(
            reader=stale_store,
            store=stale_store,
            now=lambda: RECORDED_AT,
            new_uuid=lambda: next(identities),
        )
        second_command = _command(DecisionScope.unresolved())
        second_command = InitiateDecisionCommand(
            envelope=replace(
                second_command.envelope,
                operation_id=OperationId(UUID("00000000-0000-4000-8000-00000000000b")),
            ),
            need_statement="Attempt a stale-basis initiation",
            subject=DecisionSubject("A concurrent choice"),
            scope=DecisionScope.unresolved(),
        )
        try:
            with pytest.raises(ContinuityConflict) as raised:
                await service.initiate(second_command)
            assert raised.value.candidate_decision_ids == frozenset(
                {InvestmentDecisionId(DECISION_ID)}
            )
            counts = await postgres_row_counts(
                engine,
                investment_decisions,
                investment_decision_command_receipts,
            )
            assert counts == (1, 1)
        finally:
            await engine.dispose()

    # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
    # arid: disable
    asyncio.run(scenario())


def test_concurrent_different_operations_create_at_most_one_decision_and_need(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        # arid: enable
        store = _ConcurrentCandidateReadStore(engine, asyncio.Barrier(2))
        shared_need_id = UUID("00000000-0000-4000-8000-000000000010")

        def service(*, decision_id: UUID, fact_id: UUID) -> DecisionInitiationService:
            identities = _uuids(decision_id, shared_need_id, fact_id)
            return DecisionInitiationService(
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
                reader=store,
                store=store,
                now=lambda: RECORDED_AT,
                new_uuid=lambda: next(identities),
            )
            # arid: enable

        def command(operation_id: UUID, label: str) -> InitiateDecisionCommand:
            return InitiateDecisionCommand(
                envelope=_test_envelope(
                    operation_id,
                    reference=f"request-{label}",
                    effective_at=RECORDED_AT,
                    decision_id=None,
                ),
                need_statement=f"Concurrent Need {label}",
                subject=DecisionSubject(f"Concurrent choice {label}"),
                scope=DecisionScope.unresolved(),
            )

        first = service(
            decision_id=UUID("00000000-0000-4000-8000-000000000011"),
            fact_id=UUID("00000000-0000-4000-8000-000000000012"),
        ).initiate(command(UUID("00000000-0000-4000-8000-000000000013"), "first"))
        second = service(
            decision_id=UUID("00000000-0000-4000-8000-000000000014"),
            fact_id=UUID("00000000-0000-4000-8000-000000000015"),
        ).initiate(command(UUID("00000000-0000-4000-8000-000000000016"), "second"))
        try:
            outcomes = await asyncio.gather(first, second, return_exceptions=True)
            assert sum(not isinstance(item, Exception) for item in outcomes) == 1
            assert sum(isinstance(item, ContinuityConflict) for item in outcomes) == 1
            # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
            # arid: disable
            counts = await postgres_row_counts(
                engine,
                decision_needs,
                investment_decisions,
                investment_decision_lifecycle_facts,
                investment_decision_command_receipts,
            )
            # arid: enable
            assert counts == (1, 1, 1, 1)
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_need_can_ground_only_one_decision(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        # arid: enable
        first_id = InvestmentDecisionId(DECISION_ID)
        second_operation = OperationId(UUID("00000000-0000-4000-8000-000000000008"))
        second_id = InvestmentDecisionId(UUID("00000000-0000-4000-8000-000000000009"))
        second_fact_id = DecisionLifecycleFactId(
            UUID("00000000-0000-4000-8000-00000000000a")
        )
        need = DecisionNeed(
            need_id=DecisionNeedId(NEED_ID),
            statement="Review the durable decision boundary",
            effective_at=RECORDED_AT,
            recorded_at=RECORDED_AT,
            operation_id=second_operation,
            actor_attribution=KnownActorAttribution(ActorId(ACTOR_ID)),
            trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "request-322"),
        )
        continuity = DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination.EXPLICIT_CREATE_NEW,
            candidate_decision_ids={first_id},
            known_at=RECORDED_AT,
            rationale="A separate coherent choice",
        )
        decision = initiate_decision(
            decision_id=second_id,
            need=need,
            subject=DecisionSubject("A separate matter"),
            scope=DecisionScope.unresolved(),
            continuity=continuity,
            mutation=DecisionMutationContext(
                fact_id=second_fact_id,
                operation_id=second_operation,
                actor_attribution=need.actor_attribution,
                trigger=need.trigger,
                effective_at=RECORDED_AT,
                recorded_at=RECORDED_AT,
            ),
        )
        assert isinstance(need.actor_attribution, KnownActorAttribution)
        request = InitiationSemanticRequest(
            actor_attribution=need.actor_attribution,
            trigger=need.trigger,
            effective_at=RECORDED_AT,
            expected_versions=frozenset(),
            need_statement=need.statement,
            subject=decision.subject,
            scope=decision.scope,
            continuity=ContinuityDetermination.create_new("A separate coherent choice"),
        )
        outcome = await store.commit_initiation(
            InitiationCommit(
                operation_id=second_operation,
                request=request,
                candidate_basis=ContinuityCandidateBasis(
                    frozenset({first_id}), RECORDED_AT
                ),
                result=InitiationResult(
                    second_id,
                    need.need_id,
                    InitiationResultKind.CREATED,
                ),
                decision=decision,
            )
        )
        assert outcome == InitiationNeedAlreadyGrounded(first_id)
        await store._engine.dispose()

    asyncio.run(scenario())


class _FailAfterInitiationNeedStore(PostgresDecisionStore):
    def _write_completed(self, step: str) -> None:
        if step == "need":
            raise RuntimeError("injected transaction failure")


class _FailAfterInitiationProjectionStore(PostgresDecisionStore):
    def _write_completed(self, step: str) -> None:
        if step == "projection":
            raise RuntimeError("injected transaction failure")


class _FailAfterInitiationFactStore(PostgresDecisionStore):
    def _write_completed(self, step: str) -> None:
        if step == "lifecycle_fact":
            raise RuntimeError("injected transaction failure")


class _FailAfterInitiationReceiptStore(PostgresDecisionStore):
    def _write_completed(self, step: str) -> None:
        if step == "receipt":
            raise RuntimeError("injected transaction failure")


@pytest.mark.parametrize(
    "store_type",
    [
        _FailAfterInitiationNeedStore,
        _FailAfterInitiationProjectionStore,
        _FailAfterInitiationFactStore,
        _FailAfterInitiationReceiptStore,
    ],
)
def test_injected_failure_rolls_back_every_semantic_write(
    postgres_target: PostgresTestTarget,
    store_type: type[PostgresDecisionStore],
) -> None:
    async def scenario() -> None:
        with pytest.raises(PersistenceUnavailable):
            await _initiate(
                postgres_target,
                DecisionScope.unresolved(),
                store_type=store_type,
            )
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        try:
            assert await postgres_row_counts(
                # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
                # arid: disable
                engine,
                decision_needs,
                investment_decisions,
                investment_decision_lifecycle_facts,
                investment_decision_command_receipts,
                # arid: enable
            ) == (0, 0, 0, 0)
        # duplicate-code: independent Decision persistence falsifiers must keep scenario-local proof shape; sharing this fragment would couple distinct restart, rollback, concurrency, or temporal assertions.
        # arid: disable
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_need_and_lifecycle_facts_are_database_immutable(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
        # arid: enable
        try:
            async with store._engine.begin() as connection:
                with pytest.raises(SQLAlchemyError):
                    await connection.execute(
                        decision_needs.update().values(statement="mutated")
                    )
        finally:
            await store._engine.dispose()

    asyncio.run(scenario())


def test_inward_port_methods_expose_no_database_types() -> None:
    for name in (
        "commit_mutation",
        "commit_initiation",
        "find_unresolved_continuity_candidates",
        "get_initiation_receipt",
        "get_mutation_receipt",
        "load_decision_for_command",
        "load_current_decision_state",
        "load_decision_history",
        "load_relationship_history",
    ):
        signature = str(inspect.signature(getattr(PostgresDecisionStore, name)))
        assert "sqlalchemy" not in signature.lower()
        assert "asyncpg" not in signature.lower()
