from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from polaris.application.decisions import (
    ApplyHumanDeferralCommand,
    ConcurrencyConflict,
    ContinuityRequired,
    DecisionCommandEnvelope,
    DecisionCommandState,
    DecisionMutationCommit,
    DecisionMutationCommitOutcome,
    DecisionMutationCommitted,
    DecisionMutationConcurrencyConflict,
    DecisionMutationIdempotencyConflict,
    DecisionMutationReceipt,
    DecisionMutationReplayed,
    DecisionMutationResult,
    DecisionMutationResultKind,
    DecisionMutationUnavailable,
    DecisionNonOperative,
    DecisionNotFound,
    DecisionOperativeStatusContested,
    DecisionOrdinaryWorkService,
    EstablishOrReviseDecisionScopeCommand,
    ExpectedDecisionVersion,
    IdempotencyConflict,
    InitiationCommit,
    InitiationCommitOutcome,
    InitiationReceipt,
    InvalidDecisionCommand,
    InvalidTrustedBasis,
    LifecycleConflict,
    PersistenceUnavailable,
    ResumeDecisionWorkCommand,
    ReviseDecisionSubjectCommand,
    WithdrawDecisionWorkCommand,
)
from polaris.domain.decisions import (
    ActorId,
    DecisionApplicability,
    DecisionContinuity,
    DecisionDeferred,
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleDisposition,
    DecisionLifecycleFactId,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNeedId,
    DecisionScope,
    DecisionSubject,
    DecisionSubjectRevised,
    DecisionVersion,
    DecisionWorkControlBasis,
    DecisionWorkPosture,
    DecisionWorkResumed,
    DecisionWorkWithdrawn,
    HumanInvestmentDecisionEffect,
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
    TrustedHumanInvestmentDecisionBasis,
    UnknownActorAttribution,
    initiate_decision,
    substantively_resolve_decision,
)

NOW = datetime(2026, 9, 11, 13, 0, tzinfo=UTC)


# duplicate-code: this ordinary-work fake and its Decision builders preserve the exact
# admission/applicability model for this command family; sharing them with correction or
# resolution fixtures would couple distinct semantic test seams.
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
        (
            TechnicalReference(
                TechnicalReferenceKind.TRACE,
                reference,
            ),
        )
    )


def _mutation(
    *,
    actor: KnownActorAttribution | None = None,
    effective_at: datetime = NOW,
) -> DecisionMutationContext:
    return DecisionMutationContext(
        fact_id=DecisionLifecycleFactId(uuid4()),
        operation_id=OperationId(uuid4()),
        actor_attribution=actor or _actor(),
        trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "fixture"),
        effective_at=effective_at,
        recorded_at=NOW,
        technical_provenance=_technical("fixture-trace"),
    )


def _decision(
    *,
    scope: DecisionScope | None = None,
) -> InvestmentDecision:
    actor = _actor()
    operation_id = OperationId(uuid4())
    need = DecisionNeed(
        need_id=DecisionNeedId(uuid4()),
        statement="Decide whether to change the SPY allocation",
        effective_at=NOW,
        recorded_at=NOW,
        operation_id=operation_id,
        actor_attribution=actor,
        trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "initial-request"),
        technical_provenance=_technical("initial-trace"),
    )
    return initiate_decision(
        decision_id=InvestmentDecisionId(uuid4()),
        need=need,
        subject=DecisionSubject("SPY allocation"),
        scope=scope or DecisionScope.unresolved(),
        continuity=DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination.NO_CANDIDATES,
            candidate_decision_ids=(),
            known_at=NOW,
        ),
        mutation=DecisionMutationContext(
            fact_id=DecisionLifecycleFactId(uuid4()),
            operation_id=operation_id,
            actor_attribution=actor,
            trigger=need.trigger,
            effective_at=NOW,
            recorded_at=NOW,
            technical_provenance=need.technical_provenance,
        ),
    )


def _resolved_decision() -> InvestmentDecision:
    decision = _decision()
    return substantively_resolve_decision(
        decision,
        basis=TrustedHumanInvestmentDecisionBasis(
            "human-decision-resolve",
            HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
        ),
        applicability=DecisionApplicability.OPERATIVE,
        mutation=_mutation(),
    )


def _envelope(
    decision: InvestmentDecision,
    *,
    operation_id: OperationId | None = None,
    actor: KnownActorAttribution | None = None,
    technical_reference: str = "trace-1",
    expected_version: DecisionVersion | None = None,
) -> DecisionCommandEnvelope:
    return DecisionCommandEnvelope(
        operation_id=operation_id or OperationId(uuid4()),
        actor_attribution=actor or _actor(),
        trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "request-1"),
        effective_at=NOW,
        technical_provenance=_technical(technical_reference),
        expected_versions=frozenset(
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


# arid: enable


def test_subject_revision_preserves_identity_and_provenance() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    service = _service(store)
    command = ReviseDecisionSubjectCommand(
        envelope=_envelope(decision),
        decision_id=decision.decision_id,
        subject=DecisionSubject("SPY allocation over the next quarter"),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
    )

    result = asyncio.run(service.revise_subject(command))

    assert result.kind is DecisionMutationResultKind.APPLIED
    assert result.decision_id == decision.decision_id
    assert result.version == DecisionVersion(2)
    fact = store.decision.history[-1]
    assert isinstance(fact, DecisionSubjectRevised)
    assert fact.subject == command.subject
    assert fact.metadata.operation_id == command.envelope.operation_id
    assert fact.metadata.actor_attribution == command.envelope.actor_attribution
    assert fact.metadata.trigger == command.envelope.trigger
    assert fact.metadata.technical_provenance == command.envelope.technical_provenance


# duplicate-code: Subject and Scope continuity cases keep their full public command
# shapes visible; a shared callable matrix would hide the identity-preserving boundary.
# arid: disable
def test_independent_subject_choice_routes_back_to_continuity() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    service = _service(store)

    with pytest.raises(ContinuityRequired) as exc_info:
        asyncio.run(
            service.revise_subject(
                ReviseDecisionSubjectCommand(
                    envelope=_envelope(decision),
                    decision_id=decision.decision_id,
                    subject=DecisionSubject("Treasury allocation"),
                    continuity=DecisionContinuity.INDEPENDENT_CHOICE,
                )
            )
        )

    assert exc_info.value.decision_id == decision.decision_id
    assert store.decision == decision
    assert store.receipts == ()


def test_subject_no_op_preserves_history_and_version() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    service = _service(store)

    result = asyncio.run(
        service.revise_subject(
            ReviseDecisionSubjectCommand(
                envelope=_envelope(decision),
                decision_id=decision.decision_id,
                subject=decision.subject,
                continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
    )

    assert result.kind is DecisionMutationResultKind.NO_OP
    assert result.version == decision.version
    assert store.decision.history == decision.history
    assert len(store.receipts) == 1


def test_scope_no_op_preserves_history_and_version() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)

    result = asyncio.run(
        _service(store).establish_or_revise_scope(
            EstablishOrReviseDecisionScopeCommand(
                envelope=_envelope(decision),
                decision_id=decision.decision_id,
                scope=decision.scope,
                continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
    )

    assert result.kind is DecisionMutationResultKind.NO_OP
    assert result.version == decision.version
    assert store.decision.history == decision.history
    assert len(store.receipts) == 1


def test_scope_partial_establishment_and_revision_preserve_identity() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    service = _service(store)
    first_portfolio = PortfolioId(uuid4())
    second_portfolio = PortfolioId(uuid4())

    partial = asyncio.run(
        service.establish_or_revise_scope(
            EstablishOrReviseDecisionScopeCommand(
                envelope=_envelope(store.decision),
                decision_id=decision.decision_id,
                scope=DecisionScope.unresolved(first_portfolio),
                continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
    )
    established = asyncio.run(
        service.establish_or_revise_scope(
            EstablishOrReviseDecisionScopeCommand(
                envelope=_envelope(store.decision),
                decision_id=decision.decision_id,
                scope=DecisionScope.established(first_portfolio),
                continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
    )
    revised = asyncio.run(
        service.establish_or_revise_scope(
            EstablishOrReviseDecisionScopeCommand(
                envelope=_envelope(store.decision),
                decision_id=decision.decision_id,
                scope=DecisionScope.established(first_portfolio, second_portfolio),
                continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
    )

    assert (partial.kind, established.kind, revised.kind) == (
        DecisionMutationResultKind.APPLIED,
        DecisionMutationResultKind.APPLIED,
        DecisionMutationResultKind.APPLIED,
    )
    assert store.decision.decision_id == decision.decision_id
    assert store.decision.scope == DecisionScope.established(
        second_portfolio,
        first_portfolio,
    )
    assert store.decision.version == DecisionVersion(4)


# arid: enable


# duplicate-code: these Scope/Deferral cases repeat command invocation so validation and
# trusted-basis semantics remain explicit and separate.
# arid: disable
def test_scope_rejects_empty_established_before_persistence() -> None:
    with pytest.raises(ValueError):
        DecisionScope.established()


def test_established_scope_cannot_become_unresolved_ordinary_work() -> None:
    portfolio = PortfolioId(uuid4())
    decision = _decision(scope=DecisionScope.established(portfolio))
    store = FakeDecisionStore(decision)

    with pytest.raises(LifecycleConflict):
        asyncio.run(
            _service(store).establish_or_revise_scope(
                EstablishOrReviseDecisionScopeCommand(
                    envelope=_envelope(decision),
                    decision_id=decision.decision_id,
                    scope=DecisionScope.unresolved(portfolio),
                    continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
                )
            )
        )

    assert store.decision == decision
    assert store.receipts == ()


def test_deferral_and_redeferral_require_distinct_trusted_bases() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    service = _service(store)
    first_basis = TrustedHumanInvestmentDecisionBasis(
        "human-decision-1",
        HumanInvestmentDecisionEffect.DEFERRING,
    )
    second_basis = TrustedHumanInvestmentDecisionBasis(
        "human-decision-2",
        HumanInvestmentDecisionEffect.DEFERRING,
    )

    first = asyncio.run(
        service.apply_human_deferral(
            ApplyHumanDeferralCommand(
                envelope=_envelope(store.decision),
                decision_id=decision.decision_id,
                basis=first_basis,
            )
        )
    )
    second = asyncio.run(
        service.apply_human_deferral(
            ApplyHumanDeferralCommand(
                envelope=_envelope(store.decision),
                decision_id=decision.decision_id,
                basis=second_basis,
            )
        )
    )

    assert first.kind is DecisionMutationResultKind.APPLIED
    assert second.kind is DecisionMutationResultKind.APPLIED
    assert store.decision.work_posture is DecisionWorkPosture.DEFERRED
    deferred = [
        fact for fact in store.decision.history if isinstance(fact, DecisionDeferred)
    ]
    assert [fact.basis for fact in deferred] == [first_basis, second_basis]

    with pytest.raises(InvalidDecisionCommand):
        asyncio.run(
            service.apply_human_deferral(
                ApplyHumanDeferralCommand(
                    envelope=_envelope(store.decision),
                    decision_id=decision.decision_id,
                    basis=first_basis,
                )
            )
        )

    assert (
        len(
            [
                fact
                for fact in store.decision.history
                if isinstance(fact, DecisionDeferred)
            ]
        )
        == 2
    )


# arid: enable


# duplicate-code: Deferral and work-control failures use similar fixture syntax but
# prove independently owned authority and continuity predicates.
# arid: disable
def test_deferral_rejects_non_deferring_or_untrusted_basis() -> None:
    decision = _decision()
    resolving = TrustedHumanInvestmentDecisionBasis(
        "human-decision-resolving",
        HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
    )

    with pytest.raises(InvalidTrustedBasis):
        ApplyHumanDeferralCommand(
            envelope=_envelope(decision),
            decision_id=decision.decision_id,
            basis=resolving,
        )

    with pytest.raises(InvalidTrustedBasis):
        ApplyHumanDeferralCommand(
            envelope=_envelope(decision),
            decision_id=decision.decision_id,
            basis=object(),  # type: ignore[arg-type]
        )


def test_withdraw_and_resume_preserve_unresolved_identity() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    service = _service(store)

    withdrawn = asyncio.run(
        service.withdraw_work(
            WithdrawDecisionWorkCommand(
                envelope=_envelope(store.decision),
                decision_id=decision.decision_id,
                basis=DecisionWorkControlBasis("operator-stop"),
            )
        )
    )
    resumed = asyncio.run(
        service.resume_work(
            ResumeDecisionWorkCommand(
                envelope=_envelope(store.decision),
                decision_id=decision.decision_id,
                basis=DecisionWorkControlBasis("awaited-condition-satisfied"),
                continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
    )

    assert withdrawn.kind is DecisionMutationResultKind.APPLIED
    assert resumed.kind is DecisionMutationResultKind.APPLIED
    assert store.decision.decision_id == decision.decision_id
    assert store.decision.disposition is DecisionLifecycleDisposition.UNRESOLVED
    assert store.decision.work_posture is DecisionWorkPosture.ACTIVE
    assert isinstance(store.decision.history[-2], DecisionWorkWithdrawn)
    assert isinstance(store.decision.history[-1], DecisionWorkResumed)


def test_review_condition_cannot_substitute_for_work_control_basis() -> None:
    decision = _decision()

    @dataclass(frozen=True, slots=True)
    class ReviewCondition:
        reference: str

    with pytest.raises(InvalidDecisionCommand):
        ResumeDecisionWorkCommand(
            envelope=_envelope(decision),
            decision_id=decision.decision_id,
            basis=ReviewCondition("quarterly-review"),  # type: ignore[arg-type]
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        )


def test_resume_independent_choice_routes_to_continuity() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    service = _service(store)
    asyncio.run(
        service.withdraw_work(
            WithdrawDecisionWorkCommand(
                envelope=_envelope(store.decision),
                decision_id=decision.decision_id,
                basis=DecisionWorkControlBasis("operator-stop"),
            )
        )
    )

    with pytest.raises(ContinuityRequired):
        asyncio.run(
            service.resume_work(
                ResumeDecisionWorkCommand(
                    envelope=_envelope(store.decision),
                    decision_id=decision.decision_id,
                    basis=DecisionWorkControlBasis("resume-attempt"),
                    continuity=DecisionContinuity.INDEPENDENT_CHOICE,
                )
            )
        )


# arid: enable


# duplicate-code: these explicit command collections preserve every ordinary public
# command signature in the admission matrix; a generic factory would hide coverage.
# arid: disable
def _ordinary_commands(
    decision: InvestmentDecision,
) -> tuple[
    ReviseDecisionSubjectCommand
    | EstablishOrReviseDecisionScopeCommand
    | ApplyHumanDeferralCommand
    | WithdrawDecisionWorkCommand
    | ResumeDecisionWorkCommand,
    ...,
]:
    def envelope() -> DecisionCommandEnvelope:
        return _envelope(decision)

    return (
        ReviseDecisionSubjectCommand(
            envelope=envelope(),
            decision_id=decision.decision_id,
            subject=DecisionSubject("Changed subject"),
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        ),
        EstablishOrReviseDecisionScopeCommand(
            envelope=envelope(),
            decision_id=decision.decision_id,
            scope=DecisionScope.unresolved(PortfolioId(uuid4())),
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        ),
        ApplyHumanDeferralCommand(
            envelope=envelope(),
            decision_id=decision.decision_id,
            basis=TrustedHumanInvestmentDecisionBasis(
                "human-decision-deferring",
                HumanInvestmentDecisionEffect.DEFERRING,
            ),
        ),
        WithdrawDecisionWorkCommand(
            envelope=envelope(),
            decision_id=decision.decision_id,
            basis=DecisionWorkControlBasis("stop"),
        ),
        ResumeDecisionWorkCommand(
            envelope=envelope(),
            decision_id=decision.decision_id,
            basis=DecisionWorkControlBasis("resume"),
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        ),
    )


def _ordinary_no_op_commands(
    decision: InvestmentDecision,
) -> tuple[
    ReviseDecisionSubjectCommand | EstablishOrReviseDecisionScopeCommand,
    ...,
]:
    return (
        ReviseDecisionSubjectCommand(
            envelope=_envelope(decision),
            decision_id=decision.decision_id,
            subject=decision.subject,
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        ),
        EstablishOrReviseDecisionScopeCommand(
            envelope=_envelope(decision),
            decision_id=decision.decision_id,
            scope=decision.scope,
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        ),
    )


def _run_command(
    service: DecisionOrdinaryWorkService,
    command: (
        ReviseDecisionSubjectCommand
        | EstablishOrReviseDecisionScopeCommand
        | ApplyHumanDeferralCommand
        | WithdrawDecisionWorkCommand
        | ResumeDecisionWorkCommand
    ),
) -> DecisionMutationResult:
    if isinstance(command, ReviseDecisionSubjectCommand):
        return asyncio.run(service.revise_subject(command))
    if isinstance(command, EstablishOrReviseDecisionScopeCommand):
        return asyncio.run(service.establish_or_revise_scope(command))
    if isinstance(command, ApplyHumanDeferralCommand):
        return asyncio.run(service.apply_human_deferral(command))
    if isinstance(command, WithdrawDecisionWorkCommand):
        return asyncio.run(service.withdraw_work(command))
    return asyncio.run(service.resume_work(command))


# arid: enable


# duplicate-code: the terminal admission/idempotency/concurrency matrix keeps each
# failure boundary and no-commit assertion local; factoring the repeated call shape
# would obscure which semantic outcome each test owns.
# arid: disable
@pytest.mark.parametrize("index", range(5))
def test_resolved_decision_rejects_every_ordinary_work_command(index: int) -> None:
    decision = _resolved_decision()
    store = FakeDecisionStore(decision)
    command = _ordinary_commands(decision)[index]

    with pytest.raises(LifecycleConflict):
        _run_command(_service(store), command)

    assert store.decision == decision
    assert store.receipts == ()


@pytest.mark.parametrize("index", range(2))
def test_resolved_decision_rejects_subject_and_scope_no_ops(index: int) -> None:
    decision = _resolved_decision()
    store = FakeDecisionStore(decision)
    command = _ordinary_no_op_commands(decision)[index]

    with pytest.raises(LifecycleConflict):
        _run_command(_service(store), command)

    assert store.decision == decision
    assert store.receipts == ()


@pytest.mark.parametrize(
    ("applicability", "error_type"),
    (
        (DecisionApplicability.NON_OPERATIVE, DecisionNonOperative),
        (DecisionApplicability.CONTESTED, DecisionOperativeStatusContested),
    ),
)
@pytest.mark.parametrize("index", range(5))
def test_non_operative_or_contested_decision_fails_closed_for_all_ordinary_work(
    applicability: DecisionApplicability,
    error_type: type[Exception],
    index: int,
) -> None:
    decision = _decision()
    store = FakeDecisionStore(decision, applicability=applicability)
    command = _ordinary_commands(decision)[index]

    with pytest.raises(error_type):
        _run_command(_service(store), command)

    assert store.decision == decision
    assert store.receipts == ()


@pytest.mark.parametrize(
    ("applicability", "error_type"),
    (
        (DecisionApplicability.NON_OPERATIVE, DecisionNonOperative),
        (DecisionApplicability.CONTESTED, DecisionOperativeStatusContested),
    ),
)
@pytest.mark.parametrize("index", range(2))
def test_non_operative_or_contested_rejects_subject_and_scope_no_ops(
    applicability: DecisionApplicability,
    error_type: type[Exception],
    index: int,
) -> None:
    decision = _decision()
    store = FakeDecisionStore(decision, applicability=applicability)
    command = _ordinary_no_op_commands(decision)[index]

    with pytest.raises(error_type):
        _run_command(_service(store), command)

    assert store.decision == decision
    assert store.receipts == ()


def test_existing_mutation_requires_known_actor_and_exact_expected_version() -> None:
    decision = _decision()
    unknown = DecisionCommandEnvelope(
        operation_id=OperationId(uuid4()),
        actor_attribution=UnknownActorAttribution(),
        trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "request"),
        effective_at=NOW,
        technical_provenance=TechnicalProvenance(),
        expected_versions=frozenset(
            {ExpectedDecisionVersion(decision.decision_id, decision.version)}
        ),
    )

    with pytest.raises(InvalidDecisionCommand):
        ReviseDecisionSubjectCommand(
            envelope=unknown,
            decision_id=decision.decision_id,
            subject=DecisionSubject("Changed"),
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        )

    missing_version = DecisionCommandEnvelope(
        operation_id=OperationId(uuid4()),
        actor_attribution=_actor(),
        trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "request"),
        effective_at=NOW,
        technical_provenance=TechnicalProvenance(),
    )
    with pytest.raises(InvalidDecisionCommand):
        ReviseDecisionSubjectCommand(
            envelope=missing_version,
            decision_id=decision.decision_id,
            subject=DecisionSubject("Changed"),
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        )


def test_stale_expected_version_returns_concurrency_conflict_without_commit() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    stale = DecisionVersion(decision.version.value + 1)

    with pytest.raises(ConcurrencyConflict):
        asyncio.run(
            _service(store).revise_subject(
                ReviseDecisionSubjectCommand(
                    envelope=_envelope(decision, expected_version=stale),
                    decision_id=decision.decision_id,
                    subject=DecisionSubject("Changed"),
                    continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
                )
            )
        )

    assert store.decision == decision
    assert store.receipts == ()


def test_commit_time_concurrency_conflict_is_all_or_nothing() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision, conflict_on_commit=True)

    with pytest.raises(ConcurrencyConflict):
        asyncio.run(
            _service(store).revise_subject(
                ReviseDecisionSubjectCommand(
                    envelope=_envelope(decision),
                    decision_id=decision.decision_id,
                    subject=DecisionSubject("Changed"),
                    continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
                )
            )
        )

    assert store.decision == decision
    assert store.receipts == ()


def test_same_operation_replays_when_only_technical_provenance_changes() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    service = _service(store)
    operation_id = OperationId(uuid4())
    actor = _actor()

    first = ReviseDecisionSubjectCommand(
        envelope=_envelope(
            decision,
            operation_id=operation_id,
            actor=actor,
            technical_reference="trace-1",
        ),
        decision_id=decision.decision_id,
        subject=DecisionSubject("Changed"),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
    )
    committed = asyncio.run(service.revise_subject(first))

    replay = ReviseDecisionSubjectCommand(
        envelope=_envelope(
            decision,
            operation_id=operation_id,
            actor=actor,
            technical_reference="trace-2",
        ),
        decision_id=decision.decision_id,
        subject=DecisionSubject("Changed"),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
    )
    replayed = asyncio.run(service.revise_subject(replay))

    assert committed.kind is DecisionMutationResultKind.APPLIED
    assert replayed.replayed
    assert replayed.version == committed.version
    assert len(store.receipts) == 1
    fact = store.decision.history[-1]
    assert fact.metadata.technical_provenance == first.envelope.technical_provenance


def test_same_operation_changed_semantic_request_conflicts() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    service = _service(store)
    operation_id = OperationId(uuid4())
    actor = _actor()

    asyncio.run(
        service.revise_subject(
            ReviseDecisionSubjectCommand(
                envelope=_envelope(
                    decision,
                    operation_id=operation_id,
                    actor=actor,
                ),
                decision_id=decision.decision_id,
                subject=DecisionSubject("Changed once"),
                continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            )
        )
    )

    with pytest.raises(IdempotencyConflict):
        asyncio.run(
            service.revise_subject(
                ReviseDecisionSubjectCommand(
                    envelope=_envelope(
                        decision,
                        operation_id=operation_id,
                        actor=actor,
                    ),
                    decision_id=decision.decision_id,
                    subject=DecisionSubject("Changed differently"),
                    continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
                )
            )
        )

    assert len(store.receipts) == 1


def test_persistence_unavailable_is_typed_and_commits_nothing() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision, unavailable=True)

    with pytest.raises(PersistenceUnavailable):
        asyncio.run(
            _service(store).withdraw_work(
                WithdrawDecisionWorkCommand(
                    envelope=_envelope(decision),
                    decision_id=decision.decision_id,
                    basis=DecisionWorkControlBasis("stop"),
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
        operation_id=OperationId(uuid4()),
        actor_attribution=_actor(),
        trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "request"),
        effective_at=NOW,
        technical_provenance=TechnicalProvenance(),
        expected_versions=frozenset(
            {ExpectedDecisionVersion(missing, DecisionVersion(1))}
        ),
    )

    with pytest.raises(DecisionNotFound):
        asyncio.run(
            _service(store).revise_subject(
                ReviseDecisionSubjectCommand(
                    envelope=envelope,
                    decision_id=missing,
                    subject=DecisionSubject("Missing"),
                    continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
                )
            )
        )


# arid: enable
