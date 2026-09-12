from __future__ import annotations

import asyncio
import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from polaris.application.decisions import (
    ApplyExternalResolutionCommand,
    ApplySubstantiveResolutionCommand,
    ConcurrencyConflict,
    DecisionCommandEnvelope,
    DecisionCommandState,
    DecisionMutationCommit,
    DecisionMutationCommitOutcome,
    DecisionMutationCommitted,
    DecisionMutationConcurrencyConflict,
    DecisionMutationIdempotencyConflict,
    DecisionMutationReceipt,
    DecisionMutationReplayed,
    DecisionMutationResultKind,
    DecisionMutationUnavailable,
    DecisionNonOperative,
    DecisionNotFound,
    DecisionOperativeStatusContested,
    DecisionOrdinaryWorkService,
    ExpectedDecisionVersion,
    IdempotencyConflict,
    InitiationCommit,
    InitiationCommitOutcome,
    InitiationReceipt,
    InvalidDecisionCommand,
    InvalidTrustedBasis,
    LifecycleConflict,
    PersistenceUnavailable,
)
from polaris.domain.decisions import (
    ActorId,
    DecisionApplicability,
    DecisionExternallyResolved,
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleDisposition,
    DecisionLifecycleFactId,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNeedId,
    DecisionScope,
    DecisionSubject,
    DecisionSubstantivelyResolved,
    DecisionVersion,
    ExternalResolutionBasis,
    HumanInvestmentDecisionEffect,
    InvestmentDecision,
    InvestmentDecisionId,
    KnownActorAttribution,
    OperationId,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
    UnknownActorAttribution,
    defer_decision,
    initiate_decision,
    substantively_resolve_decision,
)

NOW = datetime(2026, 9, 11, 20, 0, tzinfo=UTC)


# duplicate-code: this resolution fake and Decision builders model trusted-basis and
# late-resolution semantics locally; sharing with ordinary-work fixtures would couple
# independently meaningful command families.
# arid: disable
class FakeDecisionStore:
    def __init__(
        self,
        decision: InvestmentDecision,
        *,
        applicability: DecisionApplicability = DecisionApplicability.OPERATIVE,
        unavailable: bool = False,
        conflict_on_commit: bool = False,
    ) -> None:
        self._lock = threading.Lock()
        self._state = DecisionCommandState(decision, applicability)
        self._receipts: dict[OperationId, DecisionMutationReceipt] = {}
        self._unavailable = unavailable
        self._conflict_on_commit = conflict_on_commit

    async def get_initiation_receipt(
        self, operation_id: OperationId
    ) -> InitiationReceipt | None:
        raise AssertionError("initiation is outside this fake's test surface")

    async def commit_initiation(
        self, commit: InitiationCommit
    ) -> InitiationCommitOutcome:
        raise AssertionError("initiation is outside this fake's test surface")

    async def get_mutation_receipt(
        self, operation_id: OperationId
    ) -> DecisionMutationReceipt | None:
        with self._lock:
            return self._receipts.get(operation_id)

    async def load_decision_for_command(
        self,
        decision_id: InvestmentDecisionId,
        *,
        known_at: datetime,
    ) -> DecisionCommandState | None:
        assert known_at.tzinfo is not None
        with self._lock:
            if self._state.decision.decision_id != decision_id:
                return None
            return self._state

    async def commit_mutation(
        self, commit: DecisionMutationCommit
    ) -> DecisionMutationCommitOutcome:
        with self._lock:
            if self._unavailable:
                return DecisionMutationUnavailable("fake store unavailable")
            prior = self._receipts.get(commit.operation_id)
            if prior is not None:
                if prior.request == commit.request:
                    return DecisionMutationReplayed(prior)
                return DecisionMutationIdempotencyConflict(commit.operation_id)
            if (
                self._conflict_on_commit
                or self._state.decision.version != commit.expected_version
            ):
                return DecisionMutationConcurrencyConflict(
                    self._state.decision.decision_id
                )
            self._state = DecisionCommandState(
                commit.decision,
                self._state.applicability,
            )
            receipt = DecisionMutationReceipt(
                operation_id=commit.operation_id,
                request=commit.request,
                result=commit.result,
            )
            self._receipts[commit.operation_id] = receipt
            return DecisionMutationCommitted(receipt)

    @property
    def decision(self) -> InvestmentDecision:
        with self._lock:
            return self._state.decision

    @property
    def receipts(self) -> tuple[DecisionMutationReceipt, ...]:
        with self._lock:
            return tuple(self._receipts.values())


def _actor() -> KnownActorAttribution:
    return KnownActorAttribution(ActorId(uuid4()))


def _technical(reference: str = "trace-1") -> TechnicalProvenance:
    return TechnicalProvenance(
        (TechnicalReference(TechnicalReferenceKind.TRACE, reference),)
    )


def _decision() -> InvestmentDecision:
    actor = _actor()
    operation_id = OperationId(uuid4())
    created = NOW - timedelta(hours=4)
    trigger = TriggerProvenance(TriggerKind.HUMAN_REQUEST, "initial-request")
    need = DecisionNeed(
        DecisionNeedId(uuid4()),
        "Decide whether to change the SPY allocation",
        created,
        created,
        operation_id,
        actor,
        trigger,
        _technical("initial-trace"),
    )
    return initiate_decision(
        decision_id=InvestmentDecisionId(uuid4()),
        need=need,
        subject=DecisionSubject("SPY allocation"),
        scope=DecisionScope.unresolved(),
        continuity=DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination.NO_CANDIDATES,
            candidate_decision_ids=(),
            known_at=created,
        ),
        mutation=DecisionMutationContext(
            DecisionLifecycleFactId(uuid4()),
            operation_id,
            actor,
            trigger,
            created,
            created,
            need.technical_provenance,
        ),
    )


def _envelope(
    decision: InvestmentDecision,
    *,
    operation_id: OperationId | None = None,
    actor: KnownActorAttribution | None = None,
    effective_at: datetime = NOW,
    technical_reference: str = "trace-1",
    expected_version: DecisionVersion | None = None,
) -> DecisionCommandEnvelope:
    return DecisionCommandEnvelope(
        operation_id or OperationId(uuid4()),
        actor or _actor(),
        TriggerProvenance(TriggerKind.HUMAN_REQUEST, "request"),
        effective_at,
        _technical(technical_reference),
        frozenset(
            {
                ExpectedDecisionVersion(
                    decision.decision_id,
                    expected_version or decision.version,
                )
            }
        ),
    )


def _service(store: FakeDecisionStore) -> DecisionOrdinaryWorkService:
    return DecisionOrdinaryWorkService(
        store=store,
        now=lambda: NOW,
        new_uuid=uuid4,
    )


def _resolving_basis(
    reference: str = "human-deliberate-hold-no-action",
) -> TrustedHumanInvestmentDecisionBasis:
    return TrustedHumanInvestmentDecisionBasis(
        reference,
        HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
    )


# arid: enable


# duplicate-code: these positive/negative basis cases retain the exact trusted input at
# each assertion; a shared invocation helper would hide the effect distinction.
# arid: disable
def test_deliberate_hold_resolves_only_with_explicit_resolving_effect() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    command = ApplySubstantiveResolutionCommand(
        _envelope(decision), decision.decision_id, _resolving_basis()
    )

    result = asyncio.run(_service(store).apply_substantive_resolution(command))

    assert result.kind is DecisionMutationResultKind.APPLIED
    assert (
        store.decision.disposition
        is DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
    )
    fact = store.decision.history[-1]
    assert isinstance(fact, DecisionSubstantivelyResolved)
    assert fact.metadata.operation_id == command.envelope.operation_id
    assert fact.metadata.actor_attribution == command.envelope.actor_attribution
    assert fact.metadata.trigger == command.envelope.trigger
    assert fact.metadata.technical_provenance == command.envelope.technical_provenance


def test_recommendation_rejection_has_no_automatic_resolving_meaning() -> None:
    decision = _decision()
    non_resolving = TrustedHumanInvestmentDecisionBasis(
        "recommendation-rejected-further-judgment",
        HumanInvestmentDecisionEffect.DEFERRING,
    )

    with pytest.raises(InvalidTrustedBasis):
        ApplySubstantiveResolutionCommand(
            _envelope(decision), decision.decision_id, non_resolving
        )


def test_substantive_resolution_rejects_untrusted_basis() -> None:
    decision = _decision()
    with pytest.raises(InvalidTrustedBasis):
        ApplySubstantiveResolutionCommand(
            _envelope(decision),
            decision.decision_id,
            object(),  # type: ignore[arg-type]
        )


def test_external_resolution_closes_without_human_resolution_fact() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)

    result = asyncio.run(
        _service(store).apply_external_resolution(
            ApplyExternalResolutionCommand(
                _envelope(decision),
                decision.decision_id,
                ExternalResolutionBasis("counterparty-withdrew-opportunity"),
            )
        )
    )

    assert result.kind is DecisionMutationResultKind.APPLIED
    assert (
        store.decision.disposition is DecisionLifecycleDisposition.EXTERNALLY_RESOLVED
    )
    assert isinstance(store.decision.history[-1], DecisionExternallyResolved)
    assert not any(
        isinstance(fact, DecisionSubstantivelyResolved)
        for fact in store.decision.history
    )


# arid: enable


def test_external_resolution_rejects_human_basis_substitute() -> None:
    decision = _decision()
    with pytest.raises(InvalidDecisionCommand):
        ApplyExternalResolutionCommand(
            _envelope(decision),
            decision.decision_id,
            _resolving_basis(),  # type: ignore[arg-type]
        )


# duplicate-code: the operative/resolved/late matrices spell out each command kind so
# lifecycle versus relationship rejection remains independently visible.
# arid: disable
@pytest.mark.parametrize(
    ("applicability", "error_type"),
    (
        (DecisionApplicability.NON_OPERATIVE, DecisionNonOperative),
        (DecisionApplicability.CONTESTED, DecisionOperativeStatusContested),
    ),
)
@pytest.mark.parametrize("kind", ("substantive", "external"))
def test_nonoperative_and_contested_resolution_fail_closed(
    applicability: DecisionApplicability,
    error_type: type[Exception],
    kind: str,
) -> None:
    decision = _decision()
    store = FakeDecisionStore(decision, applicability=applicability)
    service = _service(store)
    if kind == "substantive":
        call = service.apply_substantive_resolution(
            ApplySubstantiveResolutionCommand(
                _envelope(decision), decision.decision_id, _resolving_basis()
            )
        )
    else:
        call = service.apply_external_resolution(
            ApplyExternalResolutionCommand(
                _envelope(decision),
                decision.decision_id,
                ExternalResolutionBasis("external-elimination"),
            )
        )

    with pytest.raises(error_type):
        asyncio.run(call)
    assert store.decision == decision
    assert store.receipts == ()


@pytest.mark.parametrize("kind", ("substantive", "external"))
def test_resolved_decision_rejects_ordinary_resolution(kind: str) -> None:
    decision = _decision()
    prior = NOW - timedelta(hours=2)
    decision = substantively_resolve_decision(
        decision,
        basis=_resolving_basis("prior-resolution"),
        applicability=DecisionApplicability.OPERATIVE,
        mutation=DecisionMutationContext(
            DecisionLifecycleFactId(uuid4()),
            OperationId(uuid4()),
            _actor(),
            TriggerProvenance(TriggerKind.HUMAN_REQUEST, "prior"),
            prior,
            prior,
            _technical("prior"),
        ),
    )
    store = FakeDecisionStore(decision)
    service = _service(store)
    if kind == "substantive":
        call = service.apply_substantive_resolution(
            ApplySubstantiveResolutionCommand(
                _envelope(decision),
                decision.decision_id,
                _resolving_basis("second-resolution"),
            )
        )
    else:
        call = service.apply_external_resolution(
            ApplyExternalResolutionCommand(
                _envelope(decision),
                decision.decision_id,
                ExternalResolutionBasis("late-external"),
            )
        )

    with pytest.raises(LifecycleConflict):
        asyncio.run(call)
    assert store.receipts == ()


@pytest.mark.parametrize("kind", ("substantive", "external"))
def test_late_historical_resolution_routes_out_of_forward_path(kind: str) -> None:
    decision = _decision()
    decision = defer_decision(
        decision,
        basis=TrustedHumanInvestmentDecisionBasis(
            "later-deferral",
            HumanInvestmentDecisionEffect.DEFERRING,
        ),
        applicability=DecisionApplicability.OPERATIVE,
        mutation=DecisionMutationContext(
            DecisionLifecycleFactId(uuid4()),
            OperationId(uuid4()),
            _actor(),
            TriggerProvenance(TriggerKind.HUMAN_REQUEST, "later-deferral"),
            NOW - timedelta(hours=1),
            NOW - timedelta(minutes=30),
            _technical("later-deferral"),
        ),
    )
    store = FakeDecisionStore(decision)
    envelope = _envelope(decision, effective_at=NOW - timedelta(hours=2))
    service = _service(store)
    if kind == "substantive":
        call = service.apply_substantive_resolution(
            ApplySubstantiveResolutionCommand(
                envelope,
                decision.decision_id,
                _resolving_basis("historical-human-resolution"),
            )
        )
    else:
        call = service.apply_external_resolution(
            ApplyExternalResolutionCommand(
                envelope,
                decision.decision_id,
                ExternalResolutionBasis("historical-external-resolution"),
            )
        )

    with pytest.raises(LifecycleConflict):
        asyncio.run(call)
    assert store.decision == decision
    assert store.receipts == ()


# arid: enable


def test_resolution_requires_known_actor() -> None:
    decision = _decision()
    envelope = DecisionCommandEnvelope(
        OperationId(uuid4()),
        UnknownActorAttribution(),
        TriggerProvenance(TriggerKind.HUMAN_REQUEST, "request"),
        NOW,
        TechnicalProvenance(),
        frozenset({ExpectedDecisionVersion(decision.decision_id, decision.version)}),
    )

    with pytest.raises(InvalidDecisionCommand):
        ApplySubstantiveResolutionCommand(
            envelope, decision.decision_id, _resolving_basis()
        )


def test_stale_expected_version_commits_nothing() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    command = ApplyExternalResolutionCommand(
        _envelope(
            decision,
            expected_version=DecisionVersion(decision.version.value + 1),
        ),
        decision.decision_id,
        ExternalResolutionBasis("external-elimination"),
    )

    with pytest.raises(ConcurrencyConflict):
        asyncio.run(_service(store).apply_external_resolution(command))
    assert store.decision == decision
    assert store.receipts == ()


# duplicate-code: replay, conflict, persistence, and missing-state cases preserve their
# full requests locally so distinct application outcomes cannot be collapsed by a
# shared assertion harness.
# arid: disable
def test_same_operation_same_resolution_replays_when_only_technical_changes() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    service = _service(store)
    operation_id = OperationId(uuid4())
    actor = _actor()
    first = ApplySubstantiveResolutionCommand(
        _envelope(
            decision,
            operation_id=operation_id,
            actor=actor,
            technical_reference="trace-1",
        ),
        decision.decision_id,
        _resolving_basis(),
    )
    committed = asyncio.run(service.apply_substantive_resolution(first))
    retry = ApplySubstantiveResolutionCommand(
        _envelope(
            decision,
            operation_id=operation_id,
            actor=actor,
            technical_reference="trace-2",
        ),
        decision.decision_id,
        _resolving_basis(),
    )

    replayed = asyncio.run(service.apply_substantive_resolution(retry))

    assert committed.kind is DecisionMutationResultKind.APPLIED
    assert replayed.replayed
    assert len(store.receipts) == 1
    assert (
        store.decision.history[-1].metadata.technical_provenance
        == first.envelope.technical_provenance
    )


def test_same_operation_different_resolution_conflicts() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    service = _service(store)
    operation_id = OperationId(uuid4())
    actor = _actor()
    asyncio.run(
        service.apply_external_resolution(
            ApplyExternalResolutionCommand(
                _envelope(decision, operation_id=operation_id, actor=actor),
                decision.decision_id,
                ExternalResolutionBasis("external-a"),
            )
        )
    )

    with pytest.raises(IdempotencyConflict):
        asyncio.run(
            service.apply_external_resolution(
                ApplyExternalResolutionCommand(
                    _envelope(decision, operation_id=operation_id, actor=actor),
                    decision.decision_id,
                    ExternalResolutionBasis("external-b"),
                )
            )
        )
    assert len(store.receipts) == 1


def test_commit_time_concurrency_conflict_is_atomic() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision, conflict_on_commit=True)

    with pytest.raises(ConcurrencyConflict):
        asyncio.run(
            _service(store).apply_substantive_resolution(
                ApplySubstantiveResolutionCommand(
                    _envelope(decision), decision.decision_id, _resolving_basis()
                )
            )
        )
    assert store.decision == decision
    assert store.receipts == ()


def test_persistence_unavailable_is_typed_and_commits_nothing() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision, unavailable=True)

    with pytest.raises(PersistenceUnavailable):
        asyncio.run(
            _service(store).apply_external_resolution(
                ApplyExternalResolutionCommand(
                    _envelope(decision),
                    decision.decision_id,
                    ExternalResolutionBasis("external-elimination"),
                )
            )
        )
    assert store.decision == decision
    assert store.receipts == ()


def test_missing_decision_is_typed() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    missing = InvestmentDecisionId(uuid4())
    envelope = DecisionCommandEnvelope(
        OperationId(uuid4()),
        _actor(),
        TriggerProvenance(TriggerKind.HUMAN_REQUEST, "request"),
        NOW,
        TechnicalProvenance(),
        frozenset({ExpectedDecisionVersion(missing, DecisionVersion(1))}),
    )

    with pytest.raises(DecisionNotFound):
        asyncio.run(
            _service(store).apply_external_resolution(
                ApplyExternalResolutionCommand(
                    envelope,
                    missing,
                    ExternalResolutionBasis("external-elimination"),
                )
            )
        )


# arid: enable
