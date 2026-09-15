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
    DecisionCommandReadUnavailable,
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
    InvalidDecisionCommand,
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
    CorrectDecisionRelationshipSetCommand,
    DecisionRelationshipContinuityConflict,
    DecisionRelationshipCorrectionService,
    RelationshipCorrectionMember,
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
        if self._store.candidate_read_unavailable:
            raise DecisionCommandReadUnavailable("fake candidate read unavailable")
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
        read_failure: str | None = None,
        candidate_read_unavailable: bool = False,
    ) -> None:
        self.lock = threading.Lock()
        self.history = history
        self.decisions = {item.decision_id: item for item in decisions}
        self.continuity_candidates = continuity_candidates
        self.receipts: dict[OperationId, DecisionRelationshipReceipt] = {}
        self.commits: list[DecisionRelationshipCommit] = []
        self.unavailable = unavailable
        self.barrier = barrier
        self.read_failure = read_failure
        self.candidate_read_unavailable = candidate_read_unavailable
        self.candidate_change_on_commit: frozenset[InvestmentDecisionId] | None = None
        self.decision_change_on_commit: InvestmentDecision | None = None

    async def get_relationship_receipt(
        self, operation_id: OperationId
    ) -> DecisionRelationshipReceipt | None:
        if self.read_failure == "receipt":
            raise DecisionCommandReadUnavailable("fake receipt read unavailable")
        with self.lock:
            return self.receipts.get(operation_id)

    async def load_relationship_state(
        self, *, known_at: datetime
    ) -> DecisionRelationshipState:
        if self.read_failure == "state":
            raise DecisionCommandReadUnavailable("fake state read unavailable")
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
            self.commits.append(commit)
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


def _correction_service(
    store: FakeRelationshipStore,
) -> DecisionRelationshipCorrectionService:
    return DecisionRelationshipCorrectionService(store=store, now=lambda: NOW)


def _correction_member(
    local_id: str,
    target: DecisionRelationshipFactId | str,
    *,
    effect: DecisionRelationshipCorrectionEffect = (
        DecisionRelationshipCorrectionEffect.DISCONFIRM
    ),
    basis: str = "withdraw",
    correction_effective_at: datetime = NOW,
    replacement_effective_at: datetime | None = None,
    replacement_basis: SupersedesRelationshipBasis | None = None,
) -> RelationshipCorrectionMember:
    return RelationshipCorrectionMember(
        local_id,
        target,
        effect,
        correction_effective_at,
        DecisionRelationshipCorrectionBasis((basis,)),
        replacement_effective_at,
        replacement_basis,
    )


def _correction_set(
    decisions: tuple[InvestmentDecision, ...],
    corrections: tuple[RelationshipCorrectionMember, ...],
    *,
    operation_id: OperationId | None = None,
    actor: KnownActorAttribution | None = None,
) -> CorrectDecisionRelationshipSetCommand:
    return CorrectDecisionRelationshipSetCommand(
        _envelope(
            decisions,
            operation_id=operation_id,
            actor=actor,
        ),
        corrections,
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


def test_atomic_correction_set_resolves_same_command_ancestry_without_ordering() -> (
    None
):
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    _supersede(store, source, target)
    original = store.history[0]
    current = (store.decisions[source.decision_id], store.decisions[target.decision_id])
    command = CorrectDecisionRelationshipSetCommand(
        envelope=_envelope(current),
        corrections=(
            RelationshipCorrectionMember(
                "restore",
                "withdraw",
                DecisionRelationshipCorrectionEffect.QUALIFY,
                NOW,
                DecisionRelationshipCorrectionBasis(("restore",)),
                NOW - timedelta(minutes=1),
                SupersedesRelationshipBasis(("restore",)),
            ),
            RelationshipCorrectionMember(
                "withdraw",
                original.metadata.relationship_fact_id,
                DecisionRelationshipCorrectionEffect.DISCONFIRM,
                NOW,
                DecisionRelationshipCorrectionBasis(("withdraw",)),
            ),
        ),
    )

    result = asyncio.run(_correction_service(store).correct(command))

    assert len(result.relationship_fact_ids) == 2
    assert tuple(fact.metadata.relationship_fact_id for fact in store.history[-2:]) == (
        result.relationship_fact_ids
    )


def test_atomic_correction_set_commits_members_and_versions_endpoints_once() -> None:
    source = _decision()
    target_a = _decision()
    target_b = _decision()
    store = FakeRelationshipStore((source, target_a, target_b))
    _supersede(store, source, target_a)
    _supersede(
        store,
        store.decisions[source.decision_id],
        store.decisions[target_b.decision_id],
    )
    before = {
        identity: store.decisions[identity]
        for identity in (source.decision_id, target_a.decision_id, target_b.decision_id)
    }
    facts = tuple(store.history)
    current = tuple(store.decisions.values())
    commits_before = len(store.commits)

    result = asyncio.run(
        _correction_service(store).correct(
            _correction_set(
                current,
                (
                    _correction_member("left", facts[0].metadata.relationship_fact_id),
                    _correction_member("right", facts[1].metadata.relationship_fact_id),
                ),
            )
        )
    )

    assert len(store.history) == 4
    assert len(store.commits) == commits_before + 1
    assert result.relationship_fact_ids == tuple(
        fact.metadata.relationship_fact_id for fact in store.history[-2:]
    )
    assert result.versioned_decision_ids == frozenset(before)
    for identity, prior in before.items():
        assert store.decisions[identity].version == DecisionVersion(
            prior.version.value + 1
        )
        assert store.decisions[identity].history == prior.history


def test_atomic_correction_set_invalid_member_rolls_back_atomically() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    _supersede(store, source, target)
    current = (store.decisions[source.decision_id], store.decisions[target.decision_id])
    history_before = store.history
    decisions_before = dict(store.decisions)
    receipts_before = dict(store.receipts)

    with pytest.raises(RelationshipHistoryInvalidOrIncomplete):
        asyncio.run(
            DecisionRelationshipCorrectionService(store=store).correct(
                _correction_set(
                    current,
                    (
                        _correction_member(
                            "valid", history_before[0].metadata.relationship_fact_id
                        ),
                        _correction_member(
                            "invalid", DecisionRelationshipFactId(uuid4())
                        ),
                    ),
                )
            )
        )

    assert store.history == history_before
    assert store.decisions == decisions_before
    assert store.receipts == receipts_before


def test_atomic_correction_set_replays_reordered_members_with_renamed_handles() -> None:
    source = _decision()
    target_a = _decision()
    target_b = _decision()
    store = FakeRelationshipStore((source, target_a, target_b))
    _supersede(store, source, target_a)
    _supersede(
        store,
        store.decisions[source.decision_id],
        store.decisions[target_b.decision_id],
    )
    facts = tuple(store.history)
    current = tuple(store.decisions.values())
    operation_id = OperationId(uuid4())
    actor = _actor()
    first = _correction_set(
        current,
        (
            _correction_member("first", facts[0].metadata.relationship_fact_id),
            _correction_member("second", facts[1].metadata.relationship_fact_id),
        ),
        operation_id=operation_id,
        actor=actor,
    )
    retry = _correction_set(
        current,
        (
            _correction_member("renamed-b", facts[1].metadata.relationship_fact_id),
            _correction_member("renamed-a", facts[0].metadata.relationship_fact_id),
        ),
        operation_id=operation_id,
        actor=actor,
    )

    correction_service = _correction_service(store)
    first_result = asyncio.run(correction_service.correct(first))
    retry_result = asyncio.run(correction_service.correct(retry))

    assert not first_result.replayed
    assert retry_result.replayed
    assert retry_result.relationship_fact_ids == first_result.relationship_fact_ids
    assert len(store.history) == 4
    assert len(store.receipts) == 3


def test_atomic_correction_set_changed_content_with_same_operation_conflicts() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    _supersede(store, source, target)
    fact_id = store.history[0].metadata.relationship_fact_id
    current = (store.decisions[source.decision_id], store.decisions[target.decision_id])
    operation_id = OperationId(uuid4())
    actor = _actor()
    first = _correction_set(
        current,
        (_correction_member("member", fact_id),),
        operation_id=operation_id,
        actor=actor,
    )
    correction_service = _correction_service(store)
    asyncio.run(correction_service.correct(first))
    changed = _correction_set(
        current,
        (
            _correction_member(
                "member", fact_id, effect=DecisionRelationshipCorrectionEffect.QUALIFY
            ),
        ),
        operation_id=operation_id,
        actor=actor,
    )

    with pytest.raises(IdempotencyConflict):
        asyncio.run(correction_service.correct(changed))


def test_atomic_correction_set_changed_ancestry_with_same_operation_conflicts() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    _supersede(store, source, target)
    original = store.history[0].metadata.relationship_fact_id
    current = (store.decisions[source.decision_id], store.decisions[target.decision_id])
    operation_id = OperationId(uuid4())
    actor = _actor()
    first = _correction_set(
        current,
        (
            _correction_member("parent", original, basis="parent"),
            _correction_member("child", "parent", basis="child"),
        ),
        operation_id=operation_id,
        actor=actor,
    )
    correction_service = _correction_service(store)
    asyncio.run(correction_service.correct(first))
    changed = _correction_set(
        current,
        (
            _correction_member("parent", original, basis="parent"),
            _correction_member("child", original, basis="child"),
        ),
        operation_id=operation_id,
        actor=actor,
    )

    with pytest.raises(IdempotencyConflict):
        asyncio.run(correction_service.correct(changed))


def test_atomic_correction_set_child_target_is_order_independent() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    _supersede(store, source, target)
    original = store.history[0].metadata.relationship_fact_id
    current = (store.decisions[source.decision_id], store.decisions[target.decision_id])
    command = _correction_set(
        current,
        (
            _correction_member(
                "child",
                "parent",
                effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
                basis="child",
            ),
            _correction_member(
                "parent",
                original,
                effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
                basis="parent",
            ),
        ),
    )

    result = asyncio.run(_correction_service(store).correct(command))

    assert len(result.relationship_fact_ids) == 2
    new_facts = store.history[-2:]
    assert {fact.metadata.relationship_fact_id for fact in new_facts} == set(
        result.relationship_fact_ids
    )
    parent_fact = next(
        fact for fact in new_facts if fact.target_relationship_fact_id == original
    )
    child_fact = next(fact for fact in new_facts if fact is not parent_fact)
    assert (
        child_fact.target_relationship_fact_id
        == parent_fact.metadata.relationship_fact_id
    )


def test_atomic_correction_set_sibling_corrections_are_independent_and_contested() -> (
    None
):
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    _supersede(store, source, target)
    original = store.history[0].metadata.relationship_fact_id
    current = (store.decisions[source.decision_id], store.decisions[target.decision_id])

    result = asyncio.run(
        _correction_service(store).correct(
            _correction_set(
                current,
                (
                    _correction_member(
                        "sibling-a",
                        original,
                        effect=DecisionRelationshipCorrectionEffect.QUALIFY,
                        basis="a",
                        replacement_effective_at=NOW - timedelta(minutes=1),
                        replacement_basis=SupersedesRelationshipBasis(("a",)),
                    ),
                    _correction_member(
                        "sibling-b",
                        original,
                        effect=DecisionRelationshipCorrectionEffect.QUALIFY,
                        basis="b",
                        correction_effective_at=NOW - timedelta(minutes=1),
                        replacement_effective_at=NOW - timedelta(minutes=2),
                        replacement_basis=SupersedesRelationshipBasis(("b",)),
                    ),
                ),
            )
        )
    )

    assert len(result.relationship_fact_ids) == 2
    interpretation = interpret_relationship(
        store.history,
        source_decision_id=source.decision_id,
        relationship_type=DecisionRelationshipType.SUPERSEDES,
        target_decision_id=target.decision_id,
        effective_at=NOW,
        known_at=NOW,
    )
    assert interpretation.state is DomainRelationshipState.CONTESTED
    assert interpretation.support_fact_ids == frozenset(result.relationship_fact_ids)


def test_atomic_correction_set_accepts_equivalent_siblings_as_distinct_facts() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    _supersede(store, source, target)
    original = store.history[0].metadata.relationship_fact_id

    result = asyncio.run(
        _correction_service(store).correct(
            _correction_set(
                tuple(store.decisions.values()),
                (
                    _correction_member("first", original, basis="same"),
                    _correction_member("second", original, basis="same"),
                ),
            )
        )
    )

    assert len(result.relationship_fact_ids) == 2
    assert len(set(result.relationship_fact_ids)) == 2
    assert (
        tuple(fact.metadata.relationship_fact_id for fact in store.history[-2:])
        == result.relationship_fact_ids
    )


def test_atomic_correction_set_replays_equivalent_siblings_order_independent() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    _supersede(store, source, target)
    original = store.history[0].metadata.relationship_fact_id
    current = tuple(store.decisions.values())
    operation_id = OperationId(uuid4())
    actor = _actor()
    first = _correction_set(
        current,
        (
            _correction_member("first", original, basis="same"),
            _correction_member("second", original, basis="same"),
        ),
        operation_id=operation_id,
        actor=actor,
    )
    retry = _correction_set(
        current,
        (
            _correction_member("renamed-second", original, basis="same"),
            _correction_member("renamed-first", original, basis="same"),
        ),
        operation_id=operation_id,
        actor=actor,
    )

    service = _correction_service(store)
    first_result = asyncio.run(service.correct(first))
    retry_result = asyncio.run(service.correct(retry))

    assert not first_result.replayed
    assert retry_result.replayed
    assert retry_result.relationship_fact_ids == first_result.relationship_fact_ids
    assert len(store.history) == 3
    assert len(store.commits) == 2


def test_atomic_correction_set_cardinality_change_conflicts_for_same_operation() -> (
    None
):
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    _supersede(store, source, target)
    original = store.history[0].metadata.relationship_fact_id
    current = tuple(store.decisions.values())
    operation_id = OperationId(uuid4())
    actor = _actor()
    service = _correction_service(store)
    asyncio.run(
        service.correct(
            _correction_set(
                current,
                (
                    _correction_member("first", original, basis="same"),
                    _correction_member("second", original, basis="same"),
                ),
                operation_id=operation_id,
                actor=actor,
            )
        )
    )

    with pytest.raises(IdempotencyConflict):
        asyncio.run(
            service.correct(
                _correction_set(
                    current,
                    (_correction_member("only", original, basis="same"),),
                    operation_id=operation_id,
                    actor=actor,
                )
            )
        )

    assert len(store.history) == 3


def test_atomic_correction_set_equivalent_parents_preserve_ancestry_identity() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    _supersede(store, source, target)
    original = store.history[0].metadata.relationship_fact_id
    current = tuple(store.decisions.values())
    operation_id = OperationId(uuid4())
    actor = _actor()

    first = _correction_set(
        current,
        (
            _correction_member("parent-a", original, basis="parent"),
            _correction_member("parent-b", original, basis="parent"),
            _correction_member("child", "parent-a", basis="child"),
        ),
        operation_id=operation_id,
        actor=actor,
    )
    retry = _correction_set(
        current,
        (
            _correction_member("renamed-child", "renamed-parent-b", basis="child"),
            _correction_member("renamed-parent-a", original, basis="parent"),
            _correction_member("renamed-parent-b", original, basis="parent"),
        ),
        operation_id=operation_id,
        actor=actor,
    )

    service = _correction_service(store)
    first_result = asyncio.run(service.correct(first))
    retry_result = asyncio.run(service.correct(retry))

    assert retry_result.replayed
    assert retry_result.relationship_fact_ids == first_result.relationship_fact_ids
    new_facts = store.history[-3:]
    child_fact = next(
        fact
        for fact in new_facts
        if fact.target_relationship_fact_id
        in {
            new_facts[0].metadata.relationship_fact_id,
            new_facts[1].metadata.relationship_fact_id,
        }
    )
    assert (
        child_fact.metadata.relationship_fact_id in first_result.relationship_fact_ids
    )


@pytest.mark.parametrize(
    ("corrections", "message"),
    (
        (
            (_correction_member("missing", "unknown"),),
            "missing",
        ),
        (
            (_correction_member("self", "self"),),
            "acyclic",
        ),
        (
            (
                _correction_member("left", "right"),
                _correction_member("right", "left"),
            ),
            "acyclic",
        ),
    ),
)
def test_atomic_correction_set_rejects_invalid_local_ancestry_before_commit(
    corrections: tuple[RelationshipCorrectionMember, ...], message: str
) -> None:
    decision = _decision()
    store = FakeRelationshipStore((decision,))

    with pytest.raises(InvalidDecisionCommand, match=message):
        asyncio.run(
            _correction_service(store).correct(
                _correction_set((decision,), corrections)
            )
        )

    assert store.history == ()
    assert store.receipts == {}


def test_atomic_correction_set_requires_exact_existing_endpoint_versions() -> None:
    source = _decision()
    target = _decision()
    extra = _decision()
    store = FakeRelationshipStore((source, target, extra))
    _supersede(store, source, target)
    current = (
        store.decisions[source.decision_id],
        store.decisions[target.decision_id],
    )
    fact_id = store.history[0].metadata.relationship_fact_id

    missing = CorrectDecisionRelationshipSetCommand(
        _envelope((store.decisions[source.decision_id],)),
        (_correction_member("member", fact_id),),
    )
    with pytest.raises(ConcurrencyConflict):
        asyncio.run(_correction_service(store).correct(missing))

    extraneous_envelope = _envelope((*current, store.decisions[extra.decision_id]))
    extraneous = CorrectDecisionRelationshipSetCommand(
        extraneous_envelope,
        (_correction_member("member", fact_id),),
    )
    with pytest.raises(InvalidDecisionCommand, match="exactly"):
        asyncio.run(_correction_service(store).correct(extraneous))
    assert len(store.history) == 1
    assert len(store.receipts) == 1


def test_set_preserves_lifecycle_sequence_and_singular_receipt_shape() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    _supersede(store, source, target)
    current = (store.decisions[source.decision_id], store.decisions[target.decision_id])
    lifecycle_sequences = {
        identity: decision.history[-1].metadata.sequence
        for identity, decision in store.decisions.items()
    }
    original = store.history[0].metadata.relationship_fact_id
    singular_operation = OperationId(uuid4())
    singular = CorrectDecisionRelationshipCommand(
        _envelope(current, operation_id=singular_operation),
        original,
        DecisionRelationshipCorrectionEffect.DISCONFIRM,
        NOW,
        DecisionRelationshipCorrectionBasis(("singular",)),
    )
    singular_result = asyncio.run(_correction_service(store).correct(singular))
    singular_receipt = store.receipts[singular_operation]
    assert singular_receipt.request.payload.target_relationship_fact_id == original
    assert singular_receipt.result == singular_result

    set_source = store.decisions[source.decision_id]
    set_target = store.decisions[target.decision_id]
    set_fact = store.history[0].metadata.relationship_fact_id
    asyncio.run(
        _correction_service(store).correct(
            _correction_set(
                (set_source, set_target),
                (_correction_member("set-member", set_fact),),
            )
        )
    )
    for identity, sequence in lifecycle_sequences.items():
        assert store.decisions[identity].history[-1].metadata.sequence == sequence


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


@pytest.mark.parametrize("read_failure", ("receipt", "state"))
def test_relationship_state_reads_translate_unavailability_without_commit(
    read_failure: str,
) -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target), read_failure=read_failure)

    with pytest.raises(PersistenceUnavailable) as exc_info:
        _supersede(store, source, target)

    assert isinstance(exc_info.value.__cause__, DecisionCommandReadUnavailable)
    assert store.history == ()
    assert store.receipts == {}


def test_renewal_candidate_read_translates_unavailability_without_commit() -> None:
    predecessor = _decision(resolved=True)
    store = FakeRelationshipStore(
        (predecessor,),
        candidate_read_unavailable=True,
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

    with pytest.raises(PersistenceUnavailable) as exc_info:
        asyncio.run(_service(store).renew(command))

    assert isinstance(exc_info.value.__cause__, DecisionCommandReadUnavailable)
    assert store.history == ()
    assert store.receipts == {}


def test_renewal_relationship_constructor_failure_is_translated() -> None:
    predecessor = _decision(resolved=True)
    store = FakeRelationshipStore((predecessor,))
    predecessor_spec = RenewalPredecessor(
        predecessor.decision_id,
        RenewedFromRelationshipBasis(("renewal",)),
    )
    object.__setattr__(
        predecessor_spec,
        "basis",
        SupersedesRelationshipBasis(("wrong-purpose-basis",)),
    )
    command = RenewDecisionCommand(
        envelope=_envelope((predecessor,)),
        need_statement="Revisit portfolio exposure",
        subject=DecisionSubject("Portfolio exposure"),
        scope=DecisionScope.unresolved(),
        predecessors=(predecessor_spec,),
    )

    with pytest.raises(RelationshipConflict):
        asyncio.run(_service(store).renew(command))

    assert store.history == ()
    assert store.receipts == {}


def test_supersession_relationship_constructor_cycle_is_translated() -> None:
    source = _decision()
    store = FakeRelationshipStore((source,))
    command = EstablishSupersessionCommand(
        _envelope((source,)),
        source.decision_id,
        (
            SupersessionTarget(
                source.decision_id,
                SupersedesRelationshipBasis(("self-supersession",)),
                NOW,
            ),
        ),
    )

    with pytest.raises(RelationshipCycle):
        asyncio.run(_service(store).establish_supersession(command))

    assert store.history == ()
    assert store.receipts == {}


def test_relationship_correction_constructor_history_failure_is_translated() -> None:
    source = _decision()
    target = _decision()
    store = FakeRelationshipStore((source, target))
    command = CorrectDecisionRelationshipCommand(
        envelope=_envelope((source, target)),
        target_relationship_fact_id=DecisionRelationshipFactId(uuid4()),
        effect=DecisionRelationshipCorrectionEffect.QUALIFY,
        correction_effective_at=NOW,
        correction_basis=DecisionRelationshipCorrectionBasis(("qualification",)),
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
    assert store.receipts == {}
