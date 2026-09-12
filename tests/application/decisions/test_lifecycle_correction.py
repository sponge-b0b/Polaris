from __future__ import annotations

import asyncio
import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from polaris.application import decisions as decisions_api
from polaris.application.decisions import (
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
    DecisionNotFound,
    ExpectedDecisionVersion,
    IdempotencyConflict,
    InitiationCommit,
    InitiationCommitOutcome,
    InitiationReceipt,
    InvalidDecisionCommand,
    LifecycleConflict,
    PersistenceUnavailable,
)
from polaris.application.decisions.lifecycle_correction import (
    DecisionLifecycleCorrectionService,
    RecordDecisionLifecycleCorrectionCommand,
    RetractUnsupportedDecisionNeedCommand,
)
from polaris.domain.decisions import (
    ActorId,
    ContestedDecisionLifecycleInterpretation,
    DecisionApplicability,
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
    DecisionSubject,
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
    UnsupportedDecisionNeedBasis,
    defer_decision,
    initiate_decision,
    substantively_resolve_decision,
)

NOW = datetime(2026, 9, 12, 3, 30, tzinfo=UTC)
QUALIFY = DecisionLifecycleCorrectionEffect.QUALIFY
DISCONFIRM = DecisionLifecycleCorrectionEffect.DISCONFIRM
UNRESOLVED = DecisionLifecycleDisposition.UNRESOLVED
EXTERNAL = DecisionLifecycleDisposition.EXTERNALLY_RESOLVED
UNSUPPORTED = DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED


class FakeDecisionStore:
    def __init__(
        self,
        decision: InvestmentDecision,
        *,
        applicability: DecisionApplicability = DecisionApplicability.OPERATIVE,
        unavailable: bool = False,
        conflict_on_commit: bool = False,
        commit_barrier: threading.Barrier | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._state = DecisionCommandState(decision, applicability)
        self._receipts: dict[OperationId, DecisionMutationReceipt] = {}
        self._unavailable = unavailable
        self._conflict_on_commit = conflict_on_commit
        self._commit_barrier = commit_barrier

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
        if self._commit_barrier is not None:
            return await asyncio.to_thread(self._commit_after_barrier, commit)
        return self._commit(commit)

    def _commit_after_barrier(
        self, commit: DecisionMutationCommit
    ) -> DecisionMutationCommitOutcome:
        assert self._commit_barrier is not None
        self._commit_barrier.wait()
        return self._commit(commit)

    def _commit(self, commit: DecisionMutationCommit) -> DecisionMutationCommitOutcome:
        with self._lock:
            if self._unavailable:
                return DecisionMutationUnavailable("fake store unavailable")
            prior = self._receipts.get(commit.operation_id)
            if prior is not None:
                if prior.request == commit.request:
                    return DecisionMutationReplayed(prior)
                return DecisionMutationIdempotencyConflict(commit.operation_id)
            current = self._state.decision
            if (
                self._conflict_on_commit
                or current.version != commit.expected_version
                or current.history[-1].metadata.fact_id
                != commit.expected_history_tail_fact_id
            ):
                return DecisionMutationConcurrencyConflict(current.decision_id)
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


def _technical(reference: str = "correction-trace") -> TechnicalProvenance:
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


def _resolved_decision() -> InvestmentDecision:
    decision = _decision()
    effective = NOW - timedelta(hours=2)
    return substantively_resolve_decision(
        decision,
        basis=TrustedHumanInvestmentDecisionBasis(
            "human-resolution",
            HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
        ),
        applicability=DecisionApplicability.OPERATIVE,
        mutation=DecisionMutationContext(
            DecisionLifecycleFactId(uuid4()),
            OperationId(uuid4()),
            _actor(),
            TriggerProvenance(TriggerKind.HUMAN_REQUEST, "human-resolution"),
            effective,
            effective,
            _technical("human-resolution-trace"),
        ),
    )


def _envelope(
    decision: InvestmentDecision,
    *,
    operation_id: OperationId | None = None,
    actor: KnownActorAttribution | UnknownActorAttribution | None = None,
    effective_at: datetime | None = None,
    technical_reference: str = "correction-trace",
    expected_version: DecisionVersion | None = None,
) -> DecisionCommandEnvelope:
    return DecisionCommandEnvelope(
        operation_id or OperationId(uuid4()),
        actor or _actor(),
        TriggerProvenance(TriggerKind.EXTERNAL_OBSERVATION, "correction-evidence"),
        effective_at or NOW,
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


def _service(
    store: FakeDecisionStore,
    *,
    now: datetime = NOW,
) -> DecisionLifecycleCorrectionService:
    return DecisionLifecycleCorrectionService(
        store=store,
        now=lambda: now,
        new_uuid=uuid4,
    )


def _correction_basis(
    reference: str = "supported-correction",
) -> DecisionLifecycleCorrectionBasis:
    return DecisionLifecycleCorrectionBasis(reference)


def _unsupported_basis(
    reference: str = "original-need-was-unsupported",
) -> UnsupportedDecisionNeedBasis:
    return UnsupportedDecisionNeedBasis(reference)


def _record_command(
    decision: InvestmentDecision,
    *,
    target_fact_id: DecisionLifecycleFactId,
    operation_id: OperationId | None = None,
    actor: KnownActorAttribution | None = None,
    effective_at: datetime | None = None,
    effect: DecisionLifecycleCorrectionEffect = QUALIFY,
    replacement_disposition: DecisionLifecycleDisposition | None = UNRESOLVED,
    replacement_basis: ExternalResolutionBasis | None = None,
    correction_reference: str = "supported-correction",
    technical_reference: str = "correction-trace",
) -> RecordDecisionLifecycleCorrectionCommand:
    return RecordDecisionLifecycleCorrectionCommand(
        envelope=_envelope(
            decision,
            operation_id=operation_id,
            actor=actor,
            effective_at=effective_at,
            technical_reference=technical_reference,
        ),
        decision_id=decision.decision_id,
        target_fact_id=target_fact_id,
        effect=effect,
        correction_basis=_correction_basis(correction_reference),
        replacement_disposition=(
            None if effect is DISCONFIRM else replacement_disposition
        ),
        replacement_basis=None if effect is DISCONFIRM else replacement_basis,
    )


def test_correction_commands_are_privileged_module_surface_not_package_api() -> None:
    assert "RecordDecisionLifecycleCorrectionCommand" not in decisions_api.__all__
    assert "RetractUnsupportedDecisionNeedCommand" not in decisions_api.__all__
    assert "DecisionLifecycleCorrectionService" not in decisions_api.__all__


def test_live_correction_requires_known_actor_attribution() -> None:
    decision = _decision()
    with pytest.raises(InvalidDecisionCommand, match="known Actor Attribution"):
        RecordDecisionLifecycleCorrectionCommand(
            envelope=_envelope(decision, actor=UnknownActorAttribution()),
            decision_id=decision.decision_id,
            target_fact_id=decision.history[0].metadata.fact_id,
            effect=QUALIFY,
            correction_basis=_correction_basis(),
            replacement_disposition=UNRESOLVED,
        )


def test_unsupported_need_retraction_preserves_all_prior_acts_and_can_contest() -> None:
    decision = _resolved_decision()
    original_history = decision.history
    store = FakeDecisionStore(
        decision,
        applicability=DecisionApplicability.CONTESTED,
    )
    command = RetractUnsupportedDecisionNeedCommand(
        envelope=_envelope(
            decision,
            effective_at=NOW - timedelta(hours=3),
        ),
        decision_id=decision.decision_id,
        correction_basis=_correction_basis("need-correction"),
        unsupported_need_basis=_unsupported_basis(),
    )

    result = asyncio.run(_service(store).retract_unsupported_decision_need(command))

    assert result.kind is DecisionMutationResultKind.APPLIED
    assert store.decision.history[:-1] == original_history
    correction = store.decision.history[-1]
    assert isinstance(correction, DecisionLifecycleCorrected)
    assert correction.target_fact_id == original_history[0].metadata.fact_id
    assert correction.replacement_disposition is UNSUPPORTED
    assert correction.replacement_basis == command.unsupported_need_basis
    assert isinstance(
        store.decision.lifecycle_interpretation,
        ContestedDecisionLifecycleInterpretation,
    )


def test_late_external_resolution_qualifies_existing_resolution_without_rewrite() -> (
    None
):
    decision = _resolved_decision()
    original_history = decision.history
    resolution = original_history[-1]
    store = FakeDecisionStore(decision)
    external_basis = ExternalResolutionBasis("circumstances-ended-need-earlier")
    command = _record_command(
        decision,
        target_fact_id=resolution.metadata.fact_id,
        effective_at=NOW - timedelta(hours=3),
        replacement_disposition=EXTERNAL,
        replacement_basis=external_basis,
    )

    result = asyncio.run(_service(store).record_lifecycle_correction(command))

    assert result.kind is DecisionMutationResultKind.APPLIED
    assert store.decision.history[:-1] == original_history
    correction = store.decision.history[-1]
    assert isinstance(correction, DecisionLifecycleCorrected)
    assert correction.target_fact_id == resolution.metadata.fact_id
    assert correction.replacement_disposition is EXTERNAL
    assert correction.replacement_basis == external_basis
    assert store.decision.disposition is EXTERNAL


def test_competing_correction_support_remains_contested_without_latest_winner() -> None:
    decision = _resolved_decision()
    root = decision.history[-1]
    store = FakeDecisionStore(decision)
    first = _record_command(
        decision,
        target_fact_id=root.metadata.fact_id,
        effective_at=root.metadata.effective_at,
        replacement_disposition=EXTERNAL,
        replacement_basis=ExternalResolutionBasis("external-support"),
        correction_reference="first-correction",
    )
    asyncio.run(_service(store).record_lifecycle_correction(first))
    first_correction = store.decision.history[-1]
    after_first = store.decision
    second = RecordDecisionLifecycleCorrectionCommand(
        envelope=_envelope(
            after_first,
            effective_at=root.metadata.effective_at,
        ),
        decision_id=after_first.decision_id,
        target_fact_id=root.metadata.fact_id,
        effect=QUALIFY,
        correction_basis=_correction_basis("second-correction"),
        replacement_disposition=DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED,
        replacement_basis=TrustedHumanInvestmentDecisionBasis(
            "independent-human-support",
            HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
        ),
    )

    asyncio.run(_service(store).record_lifecycle_correction(second))

    second_correction = store.decision.history[-1]
    interpretation = store.decision.lifecycle_interpretation
    assert isinstance(interpretation, ContestedDecisionLifecycleInterpretation)
    assert interpretation.support_fact_ids == frozenset(
        {
            first_correction.metadata.fact_id,
            second_correction.metadata.fact_id,
        }
    )


def test_disconfirm_preserves_target_and_restores_prior_supported_interpretation() -> (
    None
):
    decision = _resolved_decision()
    initial, resolution = decision.history
    store = FakeDecisionStore(decision)
    command = _record_command(
        decision,
        target_fact_id=resolution.metadata.fact_id,
        effect=DISCONFIRM,
        replacement_disposition=None,
    )

    asyncio.run(_service(store).record_lifecycle_correction(command))

    assert store.decision.history[0] == initial
    assert store.decision.history[1] == resolution
    assert len(store.decision.history) == 3
    assert store.decision.disposition is UNRESOLVED


def test_ineligible_non_disposition_target_fails_without_commit() -> None:
    decision = _decision()
    deferred = defer_decision(
        decision,
        basis=TrustedHumanInvestmentDecisionBasis(
            "trusted-deferral",
            HumanInvestmentDecisionEffect.DEFERRING,
        ),
        applicability=DecisionApplicability.OPERATIVE,
        mutation=DecisionMutationContext(
            DecisionLifecycleFactId(uuid4()),
            OperationId(uuid4()),
            _actor(),
            TriggerProvenance(TriggerKind.HUMAN_REQUEST, "defer"),
            NOW - timedelta(hours=1),
            NOW - timedelta(hours=1),
            _technical("deferral-trace"),
        ),
    )
    store = FakeDecisionStore(deferred)
    command = _record_command(
        deferred,
        target_fact_id=deferred.history[-1].metadata.fact_id,
    )

    with pytest.raises(LifecycleConflict, match="eligible fact"):
        asyncio.run(_service(store).record_lifecycle_correction(command))

    assert store.decision == deferred
    assert store.receipts == ()


def test_same_operation_same_request_replays_without_second_append() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    operation_id = OperationId(uuid4())
    actor = _actor()
    command = _record_command(
        decision,
        target_fact_id=decision.history[0].metadata.fact_id,
        operation_id=operation_id,
        actor=actor,
        effective_at=NOW + timedelta(hours=1),
    )

    first = asyncio.run(_service(store).record_lifecycle_correction(command))
    history_after_first = store.decision.history
    retry = _record_command(
        decision,
        target_fact_id=decision.history[0].metadata.fact_id,
        operation_id=operation_id,
        actor=actor,
        effective_at=NOW + timedelta(hours=1),
        technical_reference="retry-trace-only",
    )
    replay = asyncio.run(_service(store).record_lifecycle_correction(retry))

    assert first.kind is DecisionMutationResultKind.APPLIED
    assert not first.replayed
    assert replay.replayed
    assert store.decision.history == history_after_first
    assert len(store.receipts) == 1
    assert (
        store.decision.history[-1].metadata.technical_provenance
        == command.envelope.technical_provenance
    )


def test_same_operation_changed_semantic_request_conflicts() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    operation_id = OperationId(uuid4())
    first = _record_command(
        decision,
        target_fact_id=decision.history[0].metadata.fact_id,
        operation_id=operation_id,
        effective_at=NOW + timedelta(hours=1),
    )
    asyncio.run(_service(store).record_lifecycle_correction(first))
    changed = _record_command(
        decision,
        target_fact_id=decision.history[0].metadata.fact_id,
        operation_id=operation_id,
        effective_at=NOW + timedelta(hours=2),
    )

    with pytest.raises(IdempotencyConflict):
        asyncio.run(_service(store).record_lifecycle_correction(changed))

    assert len(store.decision.history) == 2
    assert len(store.receipts) == 1


def test_stale_expected_version_fails_before_domain_or_commit() -> None:
    decision = _resolved_decision()
    store = FakeDecisionStore(decision)
    command = RecordDecisionLifecycleCorrectionCommand(
        envelope=_envelope(
            decision,
            expected_version=DecisionVersion(decision.version.value - 1),
        ),
        decision_id=decision.decision_id,
        target_fact_id=decision.history[-1].metadata.fact_id,
        effect=DISCONFIRM,
        correction_basis=_correction_basis(),
    )

    with pytest.raises(ConcurrencyConflict):
        asyncio.run(_service(store).record_lifecycle_correction(command))

    assert store.decision == decision
    assert store.receipts == ()


def test_commit_time_conflict_and_unavailability_have_no_partial_success() -> None:
    decision = _resolved_decision()
    command = _record_command(
        decision,
        target_fact_id=decision.history[-1].metadata.fact_id,
        effect=DISCONFIRM,
        replacement_disposition=None,
    )
    conflict_store = FakeDecisionStore(decision, conflict_on_commit=True)
    with pytest.raises(ConcurrencyConflict):
        asyncio.run(_service(conflict_store).record_lifecycle_correction(command))
    assert conflict_store.decision == decision
    assert conflict_store.receipts == ()

    unavailable_store = FakeDecisionStore(decision, unavailable=True)
    with pytest.raises(PersistenceUnavailable):
        asyncio.run(_service(unavailable_store).record_lifecycle_correction(command))
    assert unavailable_store.decision == decision
    assert unavailable_store.receipts == ()


def test_future_only_distinct_correction_appends_without_version_advance() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    command = _record_command(
        decision,
        target_fact_id=decision.history[0].metadata.fact_id,
        effective_at=NOW + timedelta(hours=1),
        replacement_disposition=UNRESOLVED,
    )

    result = asyncio.run(_service(store).record_lifecycle_correction(command))

    assert result.kind is DecisionMutationResultKind.APPLIED
    assert result.version == decision.version
    assert store.decision.version == decision.version
    assert len(store.decision.history) == len(decision.history) + 1
    assert (
        store.decision.history[-1].metadata.sequence.value
        == decision.history[-1].metadata.sequence.value + 1
    )


def test_parallel_same_version_future_corrections_use_history_tail_guard() -> None:
    decision = _decision()
    store = FakeDecisionStore(
        decision,
        commit_barrier=threading.Barrier(2),
    )
    first = _record_command(
        decision,
        target_fact_id=decision.history[0].metadata.fact_id,
        effective_at=NOW + timedelta(hours=1),
        correction_reference="parallel-one",
    )
    second = _record_command(
        decision,
        target_fact_id=decision.history[0].metadata.fact_id,
        effective_at=NOW + timedelta(hours=2),
        correction_reference="parallel-two",
    )

    async def run_both() -> list[object]:
        results = await asyncio.gather(
            _service(store).record_lifecycle_correction(first),
            _service(store).record_lifecycle_correction(second),
            return_exceptions=True,
        )
        return list(results)

    outcomes = asyncio.run(run_both())

    assert sum(isinstance(value, ConcurrencyConflict) for value in outcomes) == 1
    successes = [value for value in outcomes if not isinstance(value, BaseException)]
    assert len(successes) == 1
    assert store.decision.version == decision.version
    assert len(store.decision.history) == len(decision.history) + 1
    assert len(store.receipts) == 1


def test_missing_decision_is_typed_not_found_without_commit() -> None:
    decision = _decision()
    store = FakeDecisionStore(decision)
    missing_id = InvestmentDecisionId(uuid4())
    envelope = DecisionCommandEnvelope(
        OperationId(uuid4()),
        _actor(),
        TriggerProvenance(TriggerKind.EXTERNAL_OBSERVATION, "missing-decision"),
        NOW,
        _technical("missing-decision-trace"),
        frozenset({ExpectedDecisionVersion(missing_id, decision.version)}),
    )
    command = RecordDecisionLifecycleCorrectionCommand(
        envelope=envelope,
        decision_id=missing_id,
        target_fact_id=decision.history[0].metadata.fact_id,
        effect=QUALIFY,
        correction_basis=_correction_basis(),
        replacement_disposition=UNRESOLVED,
    )

    with pytest.raises(DecisionNotFound):
        asyncio.run(_service(store).record_lifecycle_correction(command))

    assert store.decision == decision
    assert store.receipts == ()


def test_recording_time_cannot_precede_committed_history() -> None:
    decision = _resolved_decision()
    store = FakeDecisionStore(decision)
    resolution = decision.history[-1]
    command = _record_command(
        decision,
        target_fact_id=resolution.metadata.fact_id,
        effect=DISCONFIRM,
        replacement_disposition=None,
    )

    with pytest.raises(LifecycleConflict):
        asyncio.run(
            _service(
                store,
                now=resolution.metadata.recorded_at - timedelta(minutes=1),
            ).record_lifecycle_correction(command)
        )

    assert store.decision == decision
    assert store.receipts == ()
