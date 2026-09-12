from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from polaris.application.decisions import (
    ConcurrencyConflict,
    ContinuityAmbiguous,
    ContinuityConflict,
    ContinuityDetermination,
    DecisionApplicationError,
    DecisionCommandEnvelope,
    DecisionInitiationService,
    DecisionNeedGroundingConflict,
    IdempotencyConflict,
    InitiateDecisionCommand,
    InitiationCommit,
    InitiationCommitOutcome,
    InitiationCommitted,
    InitiationContinuityConflict,
    InitiationIdempotencyConflict,
    InitiationNeedAlreadyGrounded,
    InitiationReceipt,
    InitiationReplayed,
    InitiationResult,
    InitiationResultKind,
    InitiationUnavailable,
    InvalidDecisionCommand,
    LifecycleConflict,
    PersistenceUnavailable,
    RelationshipConflict,
)
from polaris.domain.decisions import (
    ActorId,
    DecisionInitiated,
    DecisionInitiationDetermination,
    DecisionNeedId,
    DecisionScope,
    DecisionSubject,
    InvestmentDecision,
    InvestmentDecisionId,
    KnownActorAttribution,
    OperationId,
    PortfolioId,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    UnknownActorAttribution,
)

NOW = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)


class UUIDSequence:
    def __init__(self, *values: UUID) -> None:
        self._values = iter(values)

    def __call__(self) -> UUID:
        return next(self._values)


# duplicate-code: this initiation fake preserves candidate-basis and Need-grounding
# failure injection locally; sharing it with mutation-store fakes would couple distinct
# transaction contracts.
# arid: disable
class FakeDecisionStore:
    def __init__(
        self,
        *,
        candidates: tuple[InvestmentDecisionId, ...] = (),
        read_barrier: threading.Barrier | None = None,
        add_after_read: InvestmentDecisionId | None = None,
        unavailable: bool = False,
    ) -> None:
        self._lock = threading.Lock()
        self._candidate_ids = set(candidates)
        self._receipts: dict[OperationId, InitiationReceipt] = {}
        self._decisions: dict[InvestmentDecisionId, InvestmentDecision] = {}
        self._needs: dict[DecisionNeedId, InvestmentDecisionId] = {}
        self._read_barrier = read_barrier
        self._add_after_read = add_after_read
        self._unavailable = unavailable

    async def find_unresolved_continuity_candidates(
        self, *, known_at: datetime
    ) -> tuple[InvestmentDecisionId, ...]:
        assert known_at.tzinfo is not None
        with self._lock:
            snapshot = tuple(self._candidate_ids)
        if self._read_barrier is not None:
            self._read_barrier.wait(timeout=5)
        if self._add_after_read is not None:
            with self._lock:
                self._candidate_ids.add(self._add_after_read)
                self._add_after_read = None
        return snapshot

    async def get_initiation_receipt(
        self, operation_id: OperationId
    ) -> InitiationReceipt | None:
        with self._lock:
            return self._receipts.get(operation_id)

    async def commit_initiation(
        self, commit: InitiationCommit
    ) -> InitiationCommitOutcome:
        with self._lock:
            if self._unavailable:
                return InitiationUnavailable("fake store unavailable")

            prior = self._receipts.get(commit.operation_id)
            if prior is not None:
                if prior.request == commit.request:
                    return InitiationReplayed(prior)
                return InitiationIdempotencyConflict(commit.operation_id)

            current = frozenset(self._candidate_ids)
            if current != commit.candidate_basis.candidate_decision_ids:
                return InitiationContinuityConflict(current)

            if commit.result.kind is InitiationResultKind.CREATED:
                assert commit.decision is not None
                assert commit.result.need_id is not None
                existing = self._needs.get(commit.result.need_id)
                if existing is not None:
                    return InitiationNeedAlreadyGrounded(existing)
                self._needs[commit.result.need_id] = commit.result.decision_id
                self._decisions[commit.result.decision_id] = commit.decision
                self._candidate_ids.add(commit.result.decision_id)
            else:
                assert commit.decision is None
                if commit.result.decision_id not in current:
                    return InitiationContinuityConflict(current)

            receipt = InitiationReceipt(
                operation_id=commit.operation_id,
                request=commit.request,
                result=commit.result,
            )
            self._receipts[commit.operation_id] = receipt
            return InitiationCommitted(receipt)

    def decision(self, decision_id: InvestmentDecisionId) -> InvestmentDecision:
        with self._lock:
            return self._decisions[decision_id]

    @property
    def decisions(self) -> tuple[InvestmentDecision, ...]:
        with self._lock:
            return tuple(self._decisions.values())

    @property
    def receipts(self) -> tuple[InitiationReceipt, ...]:
        with self._lock:
            return tuple(self._receipts.values())


# arid: enable


def _command(
    *,
    operation_id: OperationId | None = None,
    actor_attribution: KnownActorAttribution | None = None,
    continuity: ContinuityDetermination | None = None,
    need_statement: str = "Decide whether to increase the SPY allocation",
    scope: DecisionScope | None = None,
    technical_reference: str = "trace-1",
) -> InitiateDecisionCommand:
    return InitiateDecisionCommand(
        envelope=DecisionCommandEnvelope(
            operation_id=operation_id or OperationId(uuid4()),
            actor_attribution=actor_attribution
            or KnownActorAttribution(ActorId(uuid4())),
            trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "request-1"),
            effective_at=NOW,
            technical_provenance=TechnicalProvenance(
                (
                    TechnicalReference(
                        TechnicalReferenceKind.TRACE,
                        technical_reference,
                    ),
                )
            ),
        ),
        need_statement=need_statement,
        subject=DecisionSubject("SPY allocation"),
        scope=scope if scope is not None else DecisionScope.unresolved(),
        continuity=continuity,
    )


def _service(
    store: FakeDecisionStore,
    *ids: UUID,
) -> DecisionInitiationService:
    return DecisionInitiationService(
        reader=store,
        store=store,
        now=lambda: NOW,
        new_uuid=UUIDSequence(*ids),
    )


def test_envelope_allows_unknown_but_initiation_requires_known_actor() -> None:
    envelope = DecisionCommandEnvelope(
        operation_id=OperationId(uuid4()),
        actor_attribution=UnknownActorAttribution(),
        trigger=TriggerProvenance(TriggerKind.EXTERNAL_OBSERVATION, "history-1"),
        effective_at=NOW,
        technical_provenance=TechnicalProvenance(),
    )

    assert isinstance(envelope.actor_attribution, UnknownActorAttribution)
    with pytest.raises(InvalidDecisionCommand):
        InitiateDecisionCommand(
            envelope=envelope,
            need_statement="Decide whether to increase the SPY allocation",
            subject=DecisionSubject("SPY allocation"),
            scope=DecisionScope.unresolved(),
        )


# duplicate-code: these continuity scenarios keep each materially different candidate
# basis and command outcome visible; a shared invocation scaffold would hide the
# ambiguity/revalidation distinction under proof.
# arid: disable
def test_no_candidate_initiation_commits_no_candidates_basis() -> None:
    store = FakeDecisionStore()
    service = _service(store, uuid4(), uuid4(), uuid4())
    command = _command()

    result = asyncio.run(service.initiate(command))

    assert result.kind is InitiationResultKind.CREATED
    assert result.need_id is not None
    assert not result.replayed
    decision = store.decision(result.decision_id)
    initiated = decision.history[0]
    assert isinstance(initiated, DecisionInitiated)
    assert (
        initiated.continuity.determination
        is DecisionInitiationDetermination.NO_CANDIDATES
    )
    assert initiated.continuity.candidate_decision_ids == frozenset()
    assert initiated.continuity.known_at == NOW
    assert initiated.metadata.actor_attribution == command.envelope.actor_attribution
    assert initiated.metadata.trigger == command.envelope.trigger
    assert (
        initiated.metadata.technical_provenance == command.envelope.technical_provenance
    )


def test_explicit_continuation_creates_no_new_need_or_decision() -> None:
    existing = InvestmentDecisionId(uuid4())
    store = FakeDecisionStore(candidates=(existing,))
    service = _service(store)

    result = asyncio.run(
        service.initiate(
            _command(continuity=ContinuityDetermination.continue_existing(existing))
        )
    )

    assert result.kind is InitiationResultKind.CONTINUED
    assert result.decision_id == existing
    assert result.need_id is None
    assert store.decisions == ()
    assert len(store.receipts) == 1


def test_candidates_without_reliable_determination_fail_closed() -> None:
    existing = InvestmentDecisionId(uuid4())
    store = FakeDecisionStore(candidates=(existing,))
    service = _service(store)

    with pytest.raises(ContinuityAmbiguous) as exc_info:
        asyncio.run(service.initiate(_command()))

    assert exc_info.value.candidate_decision_ids == frozenset({existing})
    assert store.decisions == ()
    assert store.receipts == ()


def test_stale_continuation_determination_fails_closed() -> None:
    candidate = InvestmentDecisionId(uuid4())
    stale = InvestmentDecisionId(uuid4())
    store = FakeDecisionStore(candidates=(candidate,))
    service = _service(store)

    with pytest.raises(ContinuityAmbiguous) as exc_info:
        asyncio.run(
            service.initiate(
                _command(continuity=ContinuityDetermination.continue_existing(stale))
            )
        )

    assert exc_info.value.candidate_decision_ids == frozenset({candidate})
    assert store.decisions == ()
    assert store.receipts == ()


def test_create_new_without_required_rationale_fails_closed() -> None:
    existing = InvestmentDecisionId(uuid4())
    store = FakeDecisionStore(candidates=(existing,))
    service = _service(store)

    with pytest.raises(ContinuityAmbiguous) as exc_info:
        asyncio.run(
            service.initiate(_command(continuity=ContinuityDetermination.create_new()))
        )

    assert exc_info.value.candidate_decision_ids == frozenset({existing})
    assert store.decisions == ()
    assert store.receipts == ()


def test_explicit_create_preserves_candidate_basis_and_rationale() -> None:
    existing = InvestmentDecisionId(uuid4())
    store = FakeDecisionStore(candidates=(existing,))
    service = _service(store, uuid4(), uuid4(), uuid4())
    command = _command(
        continuity=ContinuityDetermination.create_new("Different portfolio choice")
    )

    result = asyncio.run(service.initiate(command))

    decision = store.decision(result.decision_id)
    initiated = decision.history[0]
    assert isinstance(initiated, DecisionInitiated)
    assert (
        initiated.continuity.determination
        is DecisionInitiationDetermination.EXPLICIT_CREATE_NEW
    )
    assert initiated.continuity.candidate_decision_ids == frozenset({existing})
    assert initiated.continuity.known_at == NOW
    assert initiated.continuity.rationale == "Different portfolio choice"
    assert initiated.metadata.actor_attribution == command.envelope.actor_attribution


def test_changed_candidate_basis_returns_continuity_conflict_without_commit() -> None:
    appeared = InvestmentDecisionId(uuid4())
    store = FakeDecisionStore(add_after_read=appeared)
    service = _service(store, uuid4(), uuid4(), uuid4())

    with pytest.raises(ContinuityConflict) as exc_info:
        asyncio.run(service.initiate(_command()))

    assert exc_info.value.candidate_decision_ids == frozenset({appeared})
    assert store.decisions == ()
    assert store.receipts == ()


def test_same_operation_replays_with_new_technical_attempt() -> None:
    operation_id = OperationId(uuid4())
    store = FakeDecisionStore()
    service = _service(store, uuid4(), uuid4(), uuid4())
    first = _command(operation_id=operation_id, technical_reference="trace-1")

    committed = asyncio.run(service.initiate(first))
    replay = asyncio.run(
        service.initiate(
            _command(
                operation_id=operation_id,
                actor_attribution=first.envelope.actor_attribution,
                technical_reference="trace-2",
            )
        )
    )

    assert replay.decision_id == committed.decision_id
    assert replay.need_id == committed.need_id
    assert replay.kind is committed.kind
    assert replay.replayed
    assert len(store.decisions) == 1
    assert len(store.receipts) == 1
    initiated = store.decision(committed.decision_id).history[0]
    assert isinstance(initiated, DecisionInitiated)
    assert (
        initiated.metadata.technical_provenance == first.envelope.technical_provenance
    )


def test_partial_scope_initiation_persists_confirmed_portfolio() -> None:
    portfolio_id = PortfolioId(uuid4())
    scope = DecisionScope.unresolved(portfolio_id)
    store = FakeDecisionStore()
    service = _service(store, uuid4(), uuid4(), uuid4())

    result = asyncio.run(service.initiate(_command(scope=scope)))

    assert result.need_id is not None
    decision = store.decision(result.decision_id)
    assert decision.need_id == result.need_id
    assert decision.scope == scope


def test_same_operation_different_semantic_request_conflicts() -> None:
    operation_id = OperationId(uuid4())
    store = FakeDecisionStore()
    service = _service(store, uuid4(), uuid4(), uuid4())
    first = _command(operation_id=operation_id)
    asyncio.run(service.initiate(first))

    with pytest.raises(IdempotencyConflict):
        asyncio.run(
            service.initiate(
                _command(
                    operation_id=operation_id,
                    actor_attribution=first.envelope.actor_attribution,
                    need_statement="Decide whether to reduce the SPY allocation",
                )
            )
        )

    assert len(store.decisions) == 1
    assert len(store.receipts) == 1


# arid: enable


def test_semantic_application_failures_remain_distinguishable() -> None:
    failure_types = (
        ConcurrencyConflict,
        IdempotencyConflict,
        ContinuityConflict,
        LifecycleConflict,
        RelationshipConflict,
        PersistenceUnavailable,
    )

    assert len(set(failure_types)) == len(failure_types)
    assert all(
        issubclass(failure_type, DecisionApplicationError)
        for failure_type in failure_types
    )


def test_need_identity_collision_cannot_ground_two_decisions() -> None:
    shared_need = uuid4()
    store = FakeDecisionStore()
    first = _service(store, uuid4(), shared_need, uuid4())
    first_result = asyncio.run(first.initiate(_command()))
    second = _service(store, uuid4(), shared_need, uuid4())

    with pytest.raises(DecisionNeedGroundingConflict) as exc_info:
        asyncio.run(
            second.initiate(
                _command(
                    continuity=ContinuityDetermination.create_new(
                        "Independent coherent choice"
                    )
                )
            )
        )

    assert exc_info.value.existing_decision_id == first_result.decision_id
    assert len(store.decisions) == 1


def test_persistence_unavailable_is_a_typed_application_outcome() -> None:
    store = FakeDecisionStore(unavailable=True)
    service = _service(store, uuid4(), uuid4(), uuid4())

    with pytest.raises(PersistenceUnavailable):
        asyncio.run(service.initiate(_command()))

    assert store.decisions == ()


def test_different_operation_race_cannot_silently_create_duplicates() -> None:
    barrier = threading.Barrier(2)
    store = FakeDecisionStore(read_barrier=barrier)
    services = (
        _service(store, uuid4(), uuid4(), uuid4()),
        _service(store, uuid4(), uuid4(), uuid4()),
    )
    commands = (_command(), _command())

    def run(index: int) -> InitiationResult | Exception:
        try:
            return asyncio.run(services[index].initiate(commands[index]))
        except Exception as exc:  # test captures the competing semantic result
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = tuple(executor.map(run, range(2)))

    created = [
        value
        for value in outcomes
        if not isinstance(value, Exception)
        and value.kind is InitiationResultKind.CREATED
    ]
    conflicts = [value for value in outcomes if isinstance(value, ContinuityConflict)]
    assert len(created) == 1
    assert len(conflicts) == 1
    assert len(store.decisions) == 1
    assert len(store.receipts) == 1
