from __future__ import annotations

import asyncio
import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from polaris.application import decisions as decisions_api
from polaris.application.decisions import (
    ConcurrencyConflict,
    ContinuityAmbiguous,
    ContinuityConflict,
    ContinuityDetermination,
    DecisionCommandEnvelope,
    DecisionRelationshipCommit,
    DecisionRelationshipCommitOutcome,
    DecisionRelationshipCommitted,
    DecisionRelationshipConcurrencyConflict,
    DecisionRelationshipIdempotencyConflict,
    DecisionRelationshipReceipt,
    DecisionRelationshipReplayed,
    DecisionRelationshipResult,
    DecisionRelationshipRevalidationConflict,
    DecisionRelationshipService,
    DecisionRelationshipState,
    DecisionRelationshipUnavailable,
    EstablishSupersessionCommand,
    ExpectedDecisionVersion,
    IdempotencyConflict,
    PersistenceUnavailable,
    RelationshipConflict,
    RelationshipCycle,
    RelationshipCycleSafetyIndeterminate,
    RelationshipHistoryInvalidOrIncomplete,
    RenewalPredecessor,
    RenewDecisionCommand,
    SupersessionTarget,
)
from polaris.application.decisions.relationships import (
    CorrectDecisionRelationshipCommand,
    DecisionRelationshipContinuityConflict,
    DecisionRelationshipCorrectionService,
)
from polaris.domain.decisions import (
    ActorId,
    DecisionApplicability,
    DecisionInitiated,
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleCorrectionBasis,
    DecisionLifecycleCorrectionEffect,
    DecisionLifecycleDisposition,
    DecisionLifecycleFactId,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNeedId,
    DecisionRelationshipCorrectionBasis,
    DecisionRelationshipCorrectionEffect,
    DecisionRelationshipFact,
    DecisionRelationshipFactId,
    DecisionRelationshipHistoryFact,
    DecisionRelationshipType,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    HumanInvestmentDecisionEffect,
    InvestmentDecision,
    InvestmentDecisionId,
    KnownActorAttribution,
    OperationId,
    RenewedFromRelationshipBasis,
    SupersedesRelationshipBasis,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
    correct_decision_lifecycle,
    derive_relationship_applicability,
    initiate_decision,
    interpret_relationship,
    substantively_resolve_decision,
)
from polaris.domain.decisions import (
    DecisionRelationshipState as DomainRelationshipState,
)

NOW = datetime(2026, 9, 12, 5, 0, tzinfo=UTC)


class FakeReader:
    def __init__(self, store: FakeRelationshipStore) -> None:
        self._store = store

    async def find_unresolved_continuity_candidates(
        self, *, known_at: datetime
    ) -> tuple[InvestmentDecisionId, ...]:
        assert known_at.tzinfo is not None
        with self._store.lock:
            return tuple(self._store.continuity_candidates)


class FakeRelationshipStore:
    def __init__(
        self,
        decisions: tuple[InvestmentDecision, ...],
        *,
        history: tuple[DecisionRelationshipHistoryFact, ...] = (),
        continuity_candidates: frozenset[InvestmentDecisionId] = frozenset(),
        unavailable: bool = False,
        barrier: threading.Barrier | None = None,
    ) -> None:
        self.lock = threading.Lock()
        self.history = history
        self.decisions = {item.decision_id: item for item in decisions}
        self.continuity_candidates = continuity_candidates
        self.receipts: dict[OperationId, DecisionRelationshipReceipt] = {}
        self.unavailable = unavailable
        self.barrier = barrier
        self.candidate_change_on_commit: frozenset[InvestmentDecisionId] | None = None
        self.decision_change_on_commit: InvestmentDecision | None = None

    async def get_relationship_receipt(
        self, operation_id: OperationId
    ) -> DecisionRelationshipReceipt | None:
        with self.lock:
            return self.receipts.get(operation_id)

    async def load_relationship_state(
        self, *, known_at: datetime
    ) -> DecisionRelationshipState:
        assert known_at.tzinfo is not None
        with self.lock:
            return DecisionRelationshipState(self.history, dict(self.decisions))

    async def commit_relationship(
        self, commit: DecisionRelationshipCommit
    ) -> DecisionRelationshipCommitOutcome:
        if self.barrier is not None:
            return await asyncio.to_thread(self._commit_after_barrier, commit)
        return self._commit(commit)

    def _commit_after_barrier(
        self, commit: DecisionRelationshipCommit
    ) -> DecisionRelationshipCommitOutcome:
        assert self.barrier is not None
        self.barrier.wait()
        return self._commit(commit)

    def _commit(
        self, commit: DecisionRelationshipCommit
    ) -> DecisionRelationshipCommitOutcome:
        with self.lock:
            if self.unavailable:
                return DecisionRelationshipUnavailable(
                    "fake relationship store unavailable"
                )
            prior = self.receipts.get(commit.operation_id)
            if prior is not None:
                if prior.request == commit.request:
                    return DecisionRelationshipReplayed(prior)
                return DecisionRelationshipIdempotencyConflict(commit.operation_id)
            conflict = self._commit_conflict(commit)
            if conflict is not None:
                return conflict
            self.history = commit.history
            for decision in commit.updated_decisions:
                self.decisions[decision.decision_id] = decision
            receipt = DecisionRelationshipReceipt(
                commit.operation_id,
                commit.request,
                commit.result,
            )
            self.receipts[commit.operation_id] = receipt
            return DecisionRelationshipCommitted(receipt)

    def _commit_conflict(
        self, commit: DecisionRelationshipCommit
    ) -> (
        DecisionRelationshipConcurrencyConflict
        | DecisionRelationshipContinuityConflict
        | DecisionRelationshipRevalidationConflict
        | None
    ):
        if self.candidate_change_on_commit is not None:
            self.continuity_candidates = self.candidate_change_on_commit
            self.candidate_change_on_commit = None
        if (
            commit.candidate_basis is not None
            and commit.candidate_basis.candidate_decision_ids
            != self.continuity_candidates
        ):
            return DecisionRelationshipContinuityConflict(self.continuity_candidates)
        if self.decision_change_on_commit is not None:
            changed = self.decision_change_on_commit
            self.decisions[changed.decision_id] = changed
            self.decision_change_on_commit = None
        for decision_id, version in dict(commit.expected_versions).items():
            current = self.decisions.get(decision_id)
            if current is None or current.version != version:
                return DecisionRelationshipConcurrencyConflict(
                    f"stale Decision version for {decision_id.value}"
                )
        if any(
            self.decisions.get(expected.decision_id) != expected
            for expected in commit.expected_decisions
        ):
            return DecisionRelationshipRevalidationConflict(
                "endpoint Decision history changed before commit"
            )
        if self.history != commit.expected_relationship_history:
            return DecisionRelationshipRevalidationConflict(
                "complete relationship history changed before commit"
            )
        return None


# duplicate-code: relationship fixtures construct endpoint histories and provenance
# locally so atomic multi-Decision topology remains visible; sharing with lifecycle
# fixtures would couple separate transaction models.
# arid: disable
def _actor() -> KnownActorAttribution:
    return KnownActorAttribution(ActorId(uuid4()))


def _technical(reference: str = "relationship-trace") -> TechnicalProvenance:
    return TechnicalProvenance(
        (TechnicalReference(TechnicalReferenceKind.TRACE, reference),)
    )


def _decision(*, resolved: bool = False) -> InvestmentDecision:
    actor = _actor()
    operation_id = OperationId(uuid4())
    created = NOW - timedelta(hours=6)
    trigger = TriggerProvenance(TriggerKind.HUMAN_REQUEST, "initial-request")
    need = DecisionNeed(
        DecisionNeedId(uuid4()),
        "Whether to change portfolio exposure",
        created,
        created,
        operation_id,
        actor,
        trigger,
        _technical("initial-trace"),
    )
    decision = initiate_decision(
        decision_id=InvestmentDecisionId(uuid4()),
        need=need,
        subject=DecisionSubject("Portfolio exposure"),
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
    if not resolved:
        return decision
    resolved_at = NOW - timedelta(hours=2)
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
            TriggerProvenance(TriggerKind.HUMAN_REQUEST, "resolution"),
            resolved_at,
            resolved_at,
            _technical("resolution-trace"),
        ),
    )


# arid: enable


def _envelope(
    decisions: tuple[InvestmentDecision, ...],
    *,
    operation_id: OperationId | None = None,
    actor: KnownActorAttribution | None = None,
    effective_at: datetime = NOW,
    technical_reference: str = "relationship-trace",
) -> DecisionCommandEnvelope:
    return DecisionCommandEnvelope(
        operation_id or OperationId(uuid4()),
        actor or _actor(),
        TriggerProvenance(TriggerKind.HUMAN_REQUEST, "relationship-command"),
        effective_at,
        _technical(technical_reference),
        frozenset(
            ExpectedDecisionVersion(item.decision_id, item.version)
            for item in decisions
        ),
    )


def _service(store: FakeRelationshipStore) -> DecisionRelationshipService:
    return DecisionRelationshipService(
        reader=FakeReader(store),
        store=store,
        now=lambda: NOW,
        new_uuid=uuid4,
    )


def _supersede(
    store: FakeRelationshipStore,
    source: InvestmentDecision,
    *targets: InvestmentDecision,
    operation_id: OperationId | None = None,
    actor: KnownActorAttribution | None = None,
    technical_reference: str = "relationship-trace",
    effective_at: datetime = NOW,
) -> DecisionRelationshipResult:
    current = tuple(store.decisions[item.decision_id] for item in (source, *targets))
    command = EstablishSupersessionCommand(
        _envelope(
            current,
            operation_id=operation_id,
            actor=actor,
            technical_reference=technical_reference,
        ),
        source.decision_id,
        tuple(
            SupersessionTarget(
                item.decision_id,
                SupersedesRelationshipBasis((f"supersede-{index}",)),
                effective_at,
            )
            for index, item in enumerate(targets)
        ),
    )
    return asyncio.run(_service(store).establish_supersession(command))


def test_relationship_correction_is_privileged_not_package_exported() -> None:
    assert "CorrectDecisionRelationshipCommand" not in decisions_api.__all__
    assert "DecisionRelationshipCorrectionService" not in decisions_api.__all__


# duplicate-code: renewal cases retain each candidate basis and lineage construction at
# the assertion site; a shared scenario builder would hide the continuity distinction.
# arid: disable
def test_renewal_creates_new_need_decision_and_supported_lineage_atomically() -> None:
    predecessor = _decision(resolved=True)
    store = FakeRelationshipStore((predecessor,))
    command = RenewDecisionCommand(
        envelope=_envelope((predecessor,), effective_at=NOW),
        need_statement="Revisit portfolio exposure after new evidence",
        subject=DecisionSubject("Portfolio exposure"),
        scope=DecisionScope.unresolved(),
        predecessors=(
            RenewalPredecessor(
                predecessor.decision_id,
                RenewedFromRelationshipBasis(("renewed-judgment",)),
            ),
        ),
    )

    result = asyncio.run(_service(store).renew(command))

    assert result.new_decision_id is not None
    assert result.need_id is not None
    assert result.new_decision_id in store.decisions
    assert store.decisions[predecessor.decision_id].disposition is (
        DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
    )
    assert len(store.history) == 1
    fact = store.history[0]
    assert isinstance(fact, DecisionRelationshipFact)
    assert fact.relationship_type is DecisionRelationshipType.RENEWED_FROM
    assert fact.source_decision_id == result.new_decision_id
    assert fact.target_decision_id == predecessor.decision_id


def test_renewal_with_candidate_requires_explicit_create_new() -> None:
    predecessor = _decision(resolved=True)
    candidate = _decision()
    store = FakeRelationshipStore(
        (predecessor, candidate),
        continuity_candidates=frozenset({candidate.decision_id}),
    )
    command = RenewDecisionCommand(
        envelope=_envelope((predecessor,)),
        need_statement="Revisit portfolio exposure",
        subject=DecisionSubject("Portfolio exposure"),
        scope=DecisionScope.unresolved(),
        predecessors=(
            RenewalPredecessor(
                predecessor.decision_id,
                RenewedFromRelationshipBasis(("renewal",)),
            ),
        ),
    )

    with pytest.raises(ContinuityAmbiguous):
        asyncio.run(_service(store).renew(command))
    assert store.history == ()
    assert store.receipts == {}


def test_renewal_with_candidate_preserves_explicit_create_new_basis() -> None:
    predecessor = _decision(resolved=True)
    candidate = _decision()
    store = FakeRelationshipStore(
        (predecessor, candidate),
        continuity_candidates=frozenset({candidate.decision_id}),
    )
    command = RenewDecisionCommand(
        envelope=_envelope((predecessor,)),
        need_statement="Revisit portfolio exposure as a distinct choice",
        subject=DecisionSubject("Portfolio exposure"),
        scope=DecisionScope.unresolved(),
        predecessors=(
            RenewalPredecessor(
                predecessor.decision_id,
                RenewedFromRelationshipBasis(("renewal",)),
            ),
        ),
        continuity=ContinuityDetermination.create_new(
            "new evidence changes the choice"
        ),
    )

    result = asyncio.run(_service(store).renew(command))

    assert result.new_decision_id is not None
    initiation = store.decisions[result.new_decision_id].history[0]
    assert isinstance(initiation, DecisionInitiated)
    assert initiation.continuity.determination is (
        DecisionInitiationDetermination.EXPLICIT_CREATE_NEW
    )
    assert initiation.continuity.candidate_decision_ids == frozenset(
        {candidate.decision_id}
    )
    assert initiation.continuity.rationale == "new evidence changes the choice"


def test_renewal_revalidates_continuity_candidates_at_commit() -> None:
    predecessor = _decision(resolved=True)
    new_candidate = _decision()
    store = FakeRelationshipStore((predecessor, new_candidate))
    store.candidate_change_on_commit = frozenset({new_candidate.decision_id})
    command = RenewDecisionCommand(
        envelope=_envelope((predecessor,)),
        need_statement="Revisit portfolio exposure",
        subject=DecisionSubject("Portfolio exposure"),
        scope=DecisionScope.unresolved(),
        predecessors=(
            RenewalPredecessor(
                predecessor.decision_id,
                RenewedFromRelationshipBasis(("renewal",)),
            ),
        ),
    )

    with pytest.raises(ContinuityConflict):
        asyncio.run(_service(store).renew(command))
    assert store.history == ()
    assert len(store.receipts) == 0


# arid: enable


def test_many_target_supersession_is_atomic_and_relationship_only() -> None:
    source = _decision()
    target_a = _decision(resolved=True)
    target_b = _decision()
    store = FakeRelationshipStore((source, target_a, target_b))
    before_histories = {
        item.decision_id: item.history for item in (source, target_a, target_b)
    }

    result = _supersede(store, source, target_a, target_b)

    assert len(store.history) == 2
    assert result.versioned_decision_ids == frozenset(
        {source.decision_id, target_a.decision_id, target_b.decision_id}
    )
    for item in (source, target_a, target_b):
        updated = store.decisions[item.decision_id]
        assert updated.history == before_histories[item.decision_id]
        assert updated.version == DecisionVersion(item.version.value + 1)
    assert store.decisions[target_a.decision_id].disposition is (
        DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
    )


def test_future_supersession_appends_without_premature_version_change() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))

    result = _supersede(
        store,
        source,
        target,
        effective_at=NOW + timedelta(days=1),
    )

    assert len(store.history) == 1
    assert result.versioned_decision_ids == frozenset()
    assert store.decisions[source.decision_id].version == source.version
    assert store.decisions[target.decision_id].version == target.version


# duplicate-code: applicability, cycle, and correction cases use similar edge setup but
# prove separate relationship predicates; extracting it would obscure the topology.
# arid: disable
def test_supersession_drives_nonoperative_applicability() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    _supersede(store, source, target)

    applicability = derive_relationship_applicability(
        target.decision_id,
        store.history,
        effective_at=NOW,
        known_at=NOW,
    )

    assert applicability is DecisionApplicability.NON_OPERATIVE
    assert store.decisions[target.decision_id].history == target.history


def test_cycle_is_relationship_conflict_and_commits_nothing() -> None:
    first = _decision()
    second = _decision()
    store = FakeRelationshipStore((first, second))
    _supersede(store, first, second)
    history_before = store.history
    first_now = store.decisions[first.decision_id]
    second_now = store.decisions[second.decision_id]

    with pytest.raises(RelationshipConflict):
        _supersede(store, second_now, first_now)
    assert store.history == history_before


def test_relationship_correction_preserves_original_and_can_contest_support() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    _supersede(store, source, target)
    original = store.history[0]
    source_now = store.decisions[source.decision_id]
    target_now = store.decisions[target.decision_id]
    command = CorrectDecisionRelationshipCommand(
        envelope=_envelope((source_now, target_now)),
        target_relationship_fact_id=original.metadata.relationship_fact_id,
        effect=DecisionRelationshipCorrectionEffect.QUALIFY,
        correction_effective_at=NOW,
        correction_basis=DecisionRelationshipCorrectionBasis(("new-evidence",)),
        replacement_relationship_effective_at=NOW - timedelta(minutes=10),
        replacement_relationship_basis=SupersedesRelationshipBasis(
            ("earlier-supersession",)
        ),
    )

    service = DecisionRelationshipCorrectionService(
        store=store,
        now=lambda: NOW,
        new_uuid=uuid4,
    )
    asyncio.run(service.correct(command))
    current_source = store.decisions[source.decision_id]
    current_target = store.decisions[target.decision_id]
    competing = CorrectDecisionRelationshipCommand(
        envelope=_envelope((current_source, current_target)),
        target_relationship_fact_id=original.metadata.relationship_fact_id,
        effect=DecisionRelationshipCorrectionEffect.QUALIFY,
        correction_effective_at=NOW,
        correction_basis=DecisionRelationshipCorrectionBasis(("competing-evidence",)),
        replacement_relationship_effective_at=NOW - timedelta(minutes=20),
        replacement_relationship_basis=SupersedesRelationshipBasis(
            ("competing-supersession",)
        ),
    )
    asyncio.run(service.correct(competing))

    assert store.history[0] == original
    interpretation = interpret_relationship(
        store.history,
        source_decision_id=source.decision_id,
        relationship_type=DecisionRelationshipType.SUPERSEDES,
        target_decision_id=target.decision_id,
        effective_at=NOW,
        known_at=NOW,
    )
    assert interpretation.state is DomainRelationshipState.CONTESTED
    assert len(interpretation.support_fact_ids) == 2


# arid: enable


# duplicate-code: relationship replay/conflict proofs preserve complete multi-endpoint
# requests so idempotency identity remains inspectable.
# arid: disable
def test_same_operation_same_semantic_request_replays_when_only_technical_changes() -> (
    None
):
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    operation_id = OperationId(uuid4())
    actor = _actor()

    first_envelope = _envelope(
        (source, target),
        operation_id=operation_id,
        actor=actor,
        technical_reference="trace-1",
    )
    retry_envelope = _envelope(
        (source, target),
        operation_id=operation_id,
        actor=actor,
        technical_reference="trace-2",
    )
    target_spec = SupersessionTarget(
        target.decision_id,
        SupersedesRelationshipBasis(("supersede-0",)),
        NOW,
    )
    first = asyncio.run(
        _service(store).establish_supersession(
            EstablishSupersessionCommand(
                first_envelope,
                source.decision_id,
                (target_spec,),
            )
        )
    )
    second = asyncio.run(
        _service(store).establish_supersession(
            EstablishSupersessionCommand(
                retry_envelope,
                source.decision_id,
                (target_spec,),
            )
        )
    )

    assert not first.replayed
    assert second.replayed
    assert len(store.history) == 1
    assert len(store.receipts) == 1


def test_same_operation_changed_semantic_request_is_idempotency_conflict() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    operation_id = OperationId(uuid4())
    actor = _actor()
    _supersede(store, source, target, operation_id=operation_id, actor=actor)
    current_source = store.decisions[source.decision_id]
    current_target = store.decisions[target.decision_id]
    changed = EstablishSupersessionCommand(
        _envelope(
            (current_source, current_target),
            operation_id=operation_id,
            actor=actor,
        ),
        source.decision_id,
        (
            SupersessionTarget(
                target.decision_id,
                SupersedesRelationshipBasis(("different-basis",)),
                NOW,
            ),
        ),
    )

    with pytest.raises(IdempotencyConflict):
        asyncio.run(_service(store).establish_supersession(changed))


# arid: enable


def test_stale_expected_version_is_distinct_concurrency_conflict() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    stale_source = InvestmentDecision._from_validated(
        source._history,
        source._subject,
        source._scope,
        DecisionVersion(source.version.value + 1),
        source.lifecycle_interpretation,
        source._applicability,
        source._work_posture,
    )
    command = EstablishSupersessionCommand(
        _envelope((stale_source, target)),
        source.decision_id,
        (
            SupersessionTarget(
                target.decision_id,
                SupersedesRelationshipBasis(("supersession",)),
                NOW,
            ),
        ),
    )

    with pytest.raises(ConcurrencyConflict):
        asyncio.run(_service(store).establish_supersession(command))
    assert store.history == ()


# duplicate-code: revalidation and cycle falsifiers retain their exact history graph at
# each test site; sharing setup would hide the edge that changes the semantic outcome.
# arid: disable
def test_same_version_endpoint_history_change_fails_relationship_revalidation() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    corrected = correct_decision_lifecycle(
        target,
        target_fact_id=target.history[0].metadata.fact_id,
        effect=DecisionLifecycleCorrectionEffect.QUALIFY,
        correction_basis=DecisionLifecycleCorrectionBasis(
            "future endpoint history correction"
        ),
        replacement_disposition=DecisionLifecycleDisposition.UNRESOLVED,
        replacement_basis=None,
        mutation=DecisionMutationContext(
            DecisionLifecycleFactId(uuid4()),
            OperationId(uuid4()),
            _actor(),
            TriggerProvenance(
                TriggerKind.EXTERNAL_OBSERVATION,
                "future endpoint correction",
            ),
            NOW + timedelta(hours=1),
            NOW,
            _technical("future-endpoint-correction"),
        ),
        applicability=DecisionApplicability.OPERATIVE,
    )
    assert corrected.version == target.version
    assert corrected.history != target.history
    store.decision_change_on_commit = corrected

    with pytest.raises(RelationshipConflict):
        _supersede(store, source, target)

    assert store.history == ()
    assert store.receipts == {}


def test_relationship_correction_stale_version_is_concurrency_conflict() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    _supersede(store, source, target)
    original = store.history[0]
    current_source = store.decisions[source.decision_id]
    current_target = store.decisions[target.decision_id]
    stale_envelope = DecisionCommandEnvelope(
        OperationId(uuid4()),
        _actor(),
        TriggerProvenance(TriggerKind.HUMAN_REQUEST, "stale-correction"),
        NOW,
        _technical("stale-correction"),
        frozenset(
            {
                ExpectedDecisionVersion(source.decision_id, source.version),
                ExpectedDecisionVersion(target.decision_id, target.version),
            }
        ),
    )
    command = CorrectDecisionRelationshipCommand(
        envelope=stale_envelope,
        target_relationship_fact_id=original.metadata.relationship_fact_id,
        effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
        correction_effective_at=NOW,
        correction_basis=DecisionRelationshipCorrectionBasis(("withdraw",)),
    )

    with pytest.raises(ConcurrencyConflict):
        asyncio.run(
            DecisionRelationshipCorrectionService(
                store=store,
                now=lambda: NOW,
                new_uuid=uuid4,
            ).correct(command)
        )

    assert store.history == (original,)
    assert store.decisions[source.decision_id] == current_source
    assert store.decisions[target.decision_id] == current_target


def test_missing_correction_ancestry_is_typed_invalid_history() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    command = CorrectDecisionRelationshipCommand(
        envelope=_envelope((source, target)),
        target_relationship_fact_id=DecisionRelationshipFactId(uuid4()),
        effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
        correction_effective_at=NOW,
        correction_basis=DecisionRelationshipCorrectionBasis(("withdraw",)),
    )

    with pytest.raises(RelationshipHistoryInvalidOrIncomplete):
        asyncio.run(
            DecisionRelationshipCorrectionService(
                store=store,
                now=lambda: NOW,
                new_uuid=uuid4,
            ).correct(command)
        )
    assert store.history == ()


def test_definite_cycle_is_typed_relationship_cycle() -> None:
    first = _decision()
    second = _decision()
    store = FakeRelationshipStore((first, second))
    _supersede(store, first, second)
    first_now = store.decisions[first.decision_id]
    second_now = store.decisions[second.decision_id]

    with pytest.raises(RelationshipCycle):
        _supersede(store, second_now, first_now)


def test_contested_possible_cycle_is_typed_safety_indeterminate() -> None:
    first = _decision()
    second = _decision()
    store = FakeRelationshipStore((first, second))
    _supersede(store, first, second)
    original = store.history[0]
    correction_service = DecisionRelationshipCorrectionService(
        store=store,
        now=lambda: NOW,
        new_uuid=uuid4,
    )

    first_now = store.decisions[first.decision_id]
    second_now = store.decisions[second.decision_id]
    first_correction = CorrectDecisionRelationshipCommand(
        envelope=_envelope((first_now, second_now)),
        target_relationship_fact_id=original.metadata.relationship_fact_id,
        effect=DecisionRelationshipCorrectionEffect.QUALIFY,
        correction_effective_at=NOW,
        correction_basis=DecisionRelationshipCorrectionBasis(("first-competing",)),
        replacement_relationship_effective_at=NOW - timedelta(minutes=10),
        replacement_relationship_basis=SupersedesRelationshipBasis(
            ("first-competing",)
        ),
    )
    asyncio.run(correction_service.correct(first_correction))

    first_now = store.decisions[first.decision_id]
    second_now = store.decisions[second.decision_id]
    second_correction = CorrectDecisionRelationshipCommand(
        envelope=_envelope((first_now, second_now)),
        target_relationship_fact_id=original.metadata.relationship_fact_id,
        effect=DecisionRelationshipCorrectionEffect.QUALIFY,
        correction_effective_at=NOW,
        correction_basis=DecisionRelationshipCorrectionBasis(("second-competing",)),
        replacement_relationship_effective_at=NOW - timedelta(minutes=20),
        replacement_relationship_basis=SupersedesRelationshipBasis(
            ("second-competing",)
        ),
    )
    asyncio.run(correction_service.correct(second_correction))

    interpretation = interpret_relationship(
        store.history,
        source_decision_id=first.decision_id,
        relationship_type=DecisionRelationshipType.SUPERSEDES,
        target_decision_id=second.decision_id,
        effective_at=NOW,
        known_at=NOW,
    )
    assert interpretation.state is DomainRelationshipState.CONTESTED

    first_now = store.decisions[first.decision_id]
    second_now = store.decisions[second.decision_id]
    with pytest.raises(RelationshipCycleSafetyIndeterminate):
        _supersede(store, second_now, first_now)


# arid: enable


def test_persistence_unavailable_is_distinct_and_atomic() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target), unavailable=True)

    with pytest.raises(PersistenceUnavailable):
        _supersede(store, source, target)
    assert store.history == ()
    assert store.receipts == {}


def test_disjoint_parallel_commands_fail_closed_on_history_change() -> None:
    source_a = _decision()
    target_a = _decision()
    source_b = _decision()
    target_b = _decision()
    store = FakeRelationshipStore(
        (source_a, target_a, source_b, target_b),
        barrier=threading.Barrier(2),
    )
    results: list[DecisionRelationshipResult] = []
    errors: list[BaseException] = []
    guard = threading.Lock()

    def run(source: InvestmentDecision, target: InvestmentDecision) -> None:
        try:
            result = _supersede(store, source, target)
            with guard:
                results.append(result)
        except BaseException as error:
            with guard:
                errors.append(error)

    threads = (
        threading.Thread(target=run, args=(source_a, target_a)),
        threading.Thread(target=run, args=(source_b, target_b)),
    )
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], RelationshipConflict)
    assert len(store.history) == 1
