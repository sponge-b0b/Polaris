from __future__ import annotations

import asyncio
import inspect
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from polaris.application.decisions import (
    ContinuityConflict,
    ContinuityDetermination,
    DecisionCommandEnvelope,
    DecisionInitiationService,
    DecisionMemoryService,
    IdempotencyConflict,
    InitiateDecisionCommand,
    PersistenceUnavailable,
)
from polaris.application.decisions.contracts import (
    ContinuityCandidateBasis,
    InitiationCommit,
    InitiationNeedAlreadyGrounded,
    InitiationResult,
    InitiationResultKind,
    InitiationSemanticRequest,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleFactId,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNeedId,
    DecisionScope,
    DecisionSubject,
    InvestmentDecisionId,
    OperationId,
    PortfolioId,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
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

from .conftest import PostgresTestTarget

RECORDED_AT = datetime(2026, 9, 17, 5, 0, tzinfo=UTC)
ACTOR_ID = UUID("00000000-0000-4000-8000-000000000001")
PORTFOLIO_A = UUID("00000000-0000-4000-8000-000000000002")
PORTFOLIO_B = UUID("00000000-0000-4000-8000-000000000003")
OPERATION_ID = UUID("00000000-0000-4000-8000-000000000004")
DECISION_ID = UUID("00000000-0000-4000-8000-000000000005")
NEED_ID = UUID("00000000-0000-4000-8000-000000000006")
FACT_ID = UUID("00000000-0000-4000-8000-000000000007")


def _uuids(*values: UUID) -> Iterator[UUID]:
    yield from values


def _command(scope: DecisionScope) -> InitiateDecisionCommand:
    return InitiateDecisionCommand(
        envelope=DecisionCommandEnvelope(
            operation_id=OperationId(OPERATION_ID),
            actor_attribution=KnownActorAttribution(ActorId(ACTOR_ID)),
            trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "request-321"),
            effective_at=RECORDED_AT,
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

        restarted_engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        restarted = PostgresDecisionStore(restarted_engine)
        try:
            receipt = await restarted.get_initiation_receipt(OperationId(OPERATION_ID))
            assert receipt is not None
            assert receipt.request.scope == scope
            memory = DecisionMemoryService(reader=restarted, now=lambda: RECORDED_AT)
            view = await memory.current(InvestmentDecisionId(DECISION_ID))
            assert view.need.need_id == DecisionNeedId(NEED_ID)
            assert view.subject == DecisionSubject("Whether to establish the position")
            assert view.scope == scope
            assert view.version.value == 1
            initiated = view.lifecycle_interpretation.support_fact_ids
            assert initiated == frozenset({DecisionLifecycleFactId(FACT_ID)})
            history = await restarted.load_decision_history(
                InvestmentDecisionId(DECISION_ID)
            )
            assert history is not None
            continuity = history[0].continuity
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
        finally:
            await restarted_engine.dispose()

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


def test_restart_reconstructs_semantics_from_history_not_projection(
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

        restarted_engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        restarted = PostgresDecisionStore(restarted_engine)
        try:
            view = await DecisionMemoryService(
                reader=restarted,
                now=lambda: RECORDED_AT,
            ).current(InvestmentDecisionId(DECISION_ID))
            assert view.subject == DecisionSubject("Whether to establish the position")
            assert view.scope == DecisionScope.unresolved(PortfolioId(PORTFOLIO_A))
        finally:
            await restarted_engine.dispose()

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
            envelope=DecisionCommandEnvelope(
                operation_id=OperationId(UUID("00000000-0000-4000-8000-00000000000b")),
                actor_attribution=second_command.envelope.actor_attribution,
                trigger=second_command.envelope.trigger,
                effective_at=second_command.envelope.effective_at,
                technical_provenance=(second_command.envelope.technical_provenance),
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
            async with engine.connect() as connection:
                decision_count = await connection.scalar(
                    select(func.count()).select_from(investment_decisions)
                )
                receipt_count = await connection.scalar(
                    select(func.count()).select_from(
                        investment_decision_command_receipts
                    )
                )
            assert decision_count == 1
            assert receipt_count == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_need_can_ground_only_one_decision(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
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


class _FailAfterProjectionStore(PostgresDecisionStore):
    def _write_completed(self, step: str) -> None:
        if step == "projection":
            raise RuntimeError("injected transaction failure")


def test_injected_failure_rolls_back_every_semantic_write(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        with pytest.raises(PersistenceUnavailable):
            await _initiate(
                postgres_target,
                DecisionScope.unresolved(),
                store_type=_FailAfterProjectionStore,
            )
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        try:
            async with engine.connect() as connection:
                for table in (
                    decision_needs,
                    investment_decisions,
                    investment_decision_lifecycle_facts,
                    investment_decision_command_receipts,
                ):
                    count = await connection.scalar(
                        select(func.count()).select_from(table)
                    )
                    assert count == 0
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_need_and_lifecycle_facts_are_database_immutable(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        store, _ = await _initiate(postgres_target, DecisionScope.unresolved())
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
        "commit_initiation",
        "find_unresolved_continuity_candidates",
        "get_initiation_receipt",
        "load_current_decision_state",
        "load_decision_history",
        "load_relationship_history",
    ):
        signature = str(inspect.signature(getattr(PostgresDecisionStore, name)))
        assert "sqlalchemy" not in signature.lower()
        assert "asyncpg" not in signature.lower()
