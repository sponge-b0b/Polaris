from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from polaris.application import decisions as decisions_api
from polaris.application.decisions import (
    DecisionLineageDirection,
    DecisionMemoryCurrentState,
    DecisionMemoryQueryReader,
    DecisionMemoryService,
    DecisionMemoryView,
    DecisionNotFound,
    PersistenceUnavailable,
    RelationshipHistoryInvalidOrIncomplete,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionApplicability,
    DecisionContinuity,
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleCorrectionBasis,
    DecisionLifecycleCorrectionEffect,
    DecisionLifecycleDisposition,
    DecisionLifecycleFactId,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNeedId,
    DecisionRelationshipBasisRole,
    DecisionRelationshipCorrectionBasis,
    DecisionRelationshipCorrectionEffect,
    DecisionRelationshipFact,
    DecisionRelationshipFactId,
    DecisionRelationshipHistoryFact,
    DecisionRelationshipMutationContext,
    DecisionRelationshipState,
    DecisionRelationshipType,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    InvestmentDecision,
    InvestmentDecisionId,
    OperationId,
    SupersedesRelationshipBasis,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    UnsupportedDecisionNeedBasis,
    correct_decision_lifecycle,
    initiate_decision,
    relationship_correction,
    relationship_fact,
    revise_subject,
)
from polaris.domain.decisions.facts import DecisionLifecycleFact

NOW = datetime(2026, 9, 12, 6, 0, tzinfo=UTC)
START = NOW - timedelta(days=2)


# duplicate-code: this reader and temporal fact builders form the query suite's local
# immutable-history fixture language; sharing them with command-store fixtures would
# couple read-model proof to write-path mechanics.
# arid: disable
class FakeDecisionMemoryReader:
    def __init__(
        self,
        decisions: tuple[InvestmentDecision, ...],
        *,
        relationship_history: tuple[DecisionRelationshipHistoryFact, ...] = (),
        continuity_candidates: tuple[InvestmentDecisionId, ...] = (),
    ) -> None:
        self.lifecycle_history: dict[
            InvestmentDecisionId, tuple[DecisionLifecycleFact, ...]
        ] = {decision.decision_id: decision.history for decision in decisions}
        self.relationship_history = relationship_history
        self.current_states = {
            decision.decision_id: DecisionMemoryCurrentState(
                lifecycle_facts=decision.history,
                version=decision.version,
                relationship_history=relationship_history,
            )
            for decision in decisions
        }
        self.continuity_candidates = continuity_candidates

    async def find_unresolved_continuity_candidates(
        self, *, known_at: datetime
    ) -> tuple[InvestmentDecisionId, ...]:
        assert known_at.tzinfo is not None
        return self.continuity_candidates

    async def load_current_decision_state(
        self,
        decision_id: InvestmentDecisionId,
        *,
        known_at: datetime,
    ) -> DecisionMemoryCurrentState | None:
        state = self.current_states.get(decision_id)
        if state is None or state.lifecycle_facts[0].metadata.recorded_at > known_at:
            return None
        return state

    async def load_decision_history(
        self, decision_id: InvestmentDecisionId
    ) -> tuple[DecisionLifecycleFact, ...] | None:
        return self.lifecycle_history.get(decision_id)

    async def load_relationship_history(
        self,
    ) -> tuple[DecisionRelationshipHistoryFact, ...]:
        return self.relationship_history


class FailingDecisionMemoryReader(FakeDecisionMemoryReader):
    async def load_current_decision_state(
        self,
        decision_id: InvestmentDecisionId,
        *,
        known_at: datetime,
    ) -> DecisionMemoryCurrentState | None:
        raise RuntimeError("database unavailable")


class InterleavingDecisionMemoryReader(FakeDecisionMemoryReader):
    def __init__(
        self,
        decisions: tuple[InvestmentDecision, ...],
        *,
        committed_relationship: DecisionRelationshipFact,
    ) -> None:
        super().__init__(decisions)
        self._committed_relationship = committed_relationship
        self._advanced = False

    async def load_current_decision_state(
        self,
        decision_id: InvestmentDecisionId,
        *,
        known_at: datetime,
    ) -> DecisionMemoryCurrentState | None:
        snapshot = await super().load_current_decision_state(
            decision_id,
            known_at=known_at,
        )
        if snapshot is None or self._advanced:
            return snapshot
        self._advanced = True
        self.relationship_history = (self._committed_relationship,)
        for identity in (
            self._committed_relationship.source_decision_id,
            self._committed_relationship.target_decision_id,
        ):
            prior = self.current_states[identity]
            self.current_states[identity] = DecisionMemoryCurrentState(
                lifecycle_facts=prior.lifecycle_facts,
                version=DecisionVersion(prior.version.value + 1),
                relationship_history=self.relationship_history,
            )
        await asyncio.sleep(0)
        return snapshot


def _actor() -> KnownActorAttribution:
    return KnownActorAttribution(ActorId(uuid4()))


def _trigger(reference: str) -> TriggerProvenance:
    return TriggerProvenance(TriggerKind.HUMAN_REQUEST, reference)


def _technical(reference: str) -> TechnicalProvenance:
    return TechnicalProvenance(
        (TechnicalReference(TechnicalReferenceKind.TRACE, reference),)
    )


def _decision(
    *,
    subject: str = "Portfolio exposure",
    recorded_at: datetime = START,
) -> InvestmentDecision:
    actor = _actor()
    operation_id = OperationId(uuid4())
    trigger = _trigger("initiation")
    technical = _technical("initiation")
    need = DecisionNeed(
        DecisionNeedId(uuid4()),
        "Choose portfolio exposure",
        recorded_at,
        recorded_at,
        operation_id,
        actor,
        trigger,
        technical,
    )
    return initiate_decision(
        decision_id=InvestmentDecisionId(uuid4()),
        need=need,
        subject=DecisionSubject(subject),
        scope=DecisionScope.unresolved(),
        continuity=DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination.NO_CANDIDATES,
            candidate_decision_ids=(),
            known_at=recorded_at,
        ),
        mutation=DecisionMutationContext(
            DecisionLifecycleFactId(uuid4()),
            operation_id,
            actor,
            trigger,
            recorded_at,
            recorded_at,
            technical,
        ),
    )


def _relationship_mutation(
    *,
    recorded_at: datetime,
    reference: str,
) -> DecisionRelationshipMutationContext:
    return DecisionRelationshipMutationContext(
        DecisionRelationshipFactId(uuid4()),
        OperationId(uuid4()),
        _actor(),
        _trigger(reference),
        recorded_at,
        _technical(reference),
    )


def _supersession(
    source: InvestmentDecision,
    target: InvestmentDecision,
    *,
    recorded_at: datetime = NOW - timedelta(hours=2),
    effective_at: datetime = NOW - timedelta(hours=3),
) -> DecisionRelationshipFact:
    return relationship_fact(
        source_decision_id=source.decision_id,
        target_decision_id=target.decision_id,
        relationship_type=DecisionRelationshipType.SUPERSEDES,
        relationship_effective_at=effective_at,
        relationship_basis=SupersedesRelationshipBasis(("supersession",)),
        mutation=_relationship_mutation(
            recorded_at=recorded_at,
            reference="supersession",
        ),
    )


# arid: enable


def _service(reader: FakeDecisionMemoryReader) -> DecisionMemoryService:
    typed_reader: DecisionMemoryQueryReader = reader
    return DecisionMemoryService(reader=typed_reader, now=lambda: NOW)


# duplicate-code: the two current-view proofs retain different authoritative version
# sources; extracting their read/assert shape would obscure that distinction.
# arid: disable
def test_current_view_is_application_projection_with_exact_lineage() -> None:
    source = _decision(subject="Successor")
    target = _decision(subject="Prior decision")
    edge = _supersession(source, target)
    reader = FakeDecisionMemoryReader((source, target), relationship_history=(edge,))
    for decision in (source, target):
        reader.current_states[decision.decision_id] = DecisionMemoryCurrentState(
            lifecycle_facts=decision.history,
            version=DecisionVersion(decision.version.value + 1),
            relationship_history=reader.relationship_history,
        )

    view = asyncio.run(_service(reader).current(target.decision_id))

    assert type(view) is DecisionMemoryView
    assert not isinstance(view, InvestmentDecision)
    assert view.decision_id == target.decision_id
    assert view.need == target.need
    assert view.subject == target.subject
    assert view.scope == target.scope
    assert view.version == DecisionVersion(target.version.value + 1)
    assert view.applicability is DecisionApplicability.NON_OPERATIVE
    assert len(view.lineage) == 1
    lineage = view.lineage[0]
    assert lineage.direction is DecisionLineageDirection.INCOMING
    assert lineage.source_decision_id == source.decision_id
    assert lineage.target_decision_id == target.decision_id
    assert lineage.relationship_type is DecisionRelationshipType.SUPERSEDES
    assert lineage.state is DecisionRelationshipState.SUPPORTED
    assert lineage.support_fact_ids == frozenset({edge.metadata.relationship_fact_id})
    assert lineage.history == (edge,)


def test_current_view_uses_authoritative_version_beyond_lifecycle_history() -> None:
    decision = _decision()
    reader = FakeDecisionMemoryReader((decision,))
    reader.current_states[decision.decision_id] = DecisionMemoryCurrentState(
        lifecycle_facts=decision.history,
        version=DecisionVersion(decision.version.value + 1),
        relationship_history=reader.relationship_history,
    )

    view = asyncio.run(_service(reader).current(decision.decision_id))

    assert view.version == DecisionVersion(2)
    assert view.lifecycle_interpretation.effective_at == NOW
    assert view.lifecycle_interpretation.known_at == NOW
    assert (
        view.lifecycle_interpretation.disposition
        is DecisionLifecycleDisposition.UNRESOLVED
    )


# arid: enable


def test_current_view_stays_on_one_snapshot_during_relationship_commit() -> None:
    source = _decision(subject="Successor")
    target = _decision(subject="Prior")
    edge = _supersession(source, target)
    reader = InterleavingDecisionMemoryReader(
        (source, target),
        committed_relationship=edge,
    )
    service = _service(reader)

    before = asyncio.run(service.current(target.decision_id))
    after = asyncio.run(service.current(target.decision_id))

    assert before.version == target.version
    assert before.applicability is DecisionApplicability.OPERATIVE
    assert before.lineage == ()
    assert after.version == DecisionVersion(target.version.value + 1)
    assert after.applicability is DecisionApplicability.NON_OPERATIVE
    assert len(after.lineage) == 1
    assert after.lineage[0].support_fact_ids == frozenset(
        {edge.metadata.relationship_fact_id}
    )


# duplicate-code: temporal, raw-history, lineage, and cutoff cases spell out different
# fact universes; sharing construction would couple independent hindsight and support
# proofs.
# arid: disable
def test_temporal_queries_separate_effective_time_from_knowledge_cutoff() -> None:
    original = _decision(subject="Original subject")
    recorded_at = NOW - timedelta(hours=1)
    effective_at = NOW + timedelta(days=1)
    revised = revise_subject(
        original,
        subject=DecisionSubject("Future subject"),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        applicability=DecisionApplicability.OPERATIVE,
        mutation=DecisionMutationContext(
            DecisionLifecycleFactId(uuid4()),
            OperationId(uuid4()),
            _actor(),
            _trigger("future-subject"),
            effective_at,
            recorded_at,
            _technical("future-subject"),
        ),
    )
    reader = FakeDecisionMemoryReader((revised,))
    service = _service(reader)

    current = asyncio.run(service.current(revised.decision_id))
    before_recording = asyncio.run(
        service.as_known_at(
            revised.decision_id,
            recorded_at - timedelta(minutes=1),
        )
    )
    future_without_knowledge = asyncio.run(
        service.effective_at(
            revised.decision_id,
            effective_at,
            known_at=recorded_at - timedelta(minutes=1),
        )
    )
    future_with_knowledge = asyncio.run(
        service.effective_at(
            revised.decision_id,
            effective_at,
            known_at=NOW,
        )
    )

    assert current.subject == DecisionSubject("Original subject")
    assert before_recording.subject == DecisionSubject("Original subject")
    assert future_without_knowledge.subject == DecisionSubject("Original subject")
    assert future_with_knowledge.subject == DecisionSubject("Future subject")


def test_history_preserves_raw_lifecycle_and_relationship_corrections() -> None:
    source = _decision(subject="Successor")
    target = _decision(subject="Prior")
    corrected_target = correct_decision_lifecycle(
        target,
        target_fact_id=target.history[0].metadata.fact_id,
        effect=DecisionLifecycleCorrectionEffect.QUALIFY,
        correction_basis=DecisionLifecycleCorrectionBasis("unsupported-need"),
        replacement_disposition=(
            DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED
        ),
        replacement_basis=UnsupportedDecisionNeedBasis("bad-initiation"),
        mutation=DecisionMutationContext(
            DecisionLifecycleFactId(uuid4()),
            OperationId(uuid4()),
            _actor(),
            _trigger("lifecycle-correction"),
            NOW - timedelta(minutes=20),
            NOW - timedelta(minutes=20),
            _technical("lifecycle-correction"),
        ),
        applicability=DecisionApplicability.OPERATIVE,
    )
    edge = _supersession(source, corrected_target)
    correction = relationship_correction(
        target_relationship_fact_id=edge.metadata.relationship_fact_id,
        effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
        correction_effective_at=NOW - timedelta(minutes=15),
        correction_basis=DecisionRelationshipCorrectionBasis(("withdraw-edge",)),
        mutation=_relationship_mutation(
            recorded_at=NOW - timedelta(minutes=10),
            reference="relationship-correction",
        ),
    )
    reader = FakeDecisionMemoryReader(
        (source, corrected_target),
        relationship_history=(edge, correction),
    )

    history = asyncio.run(_service(reader).history(corrected_target.decision_id))

    assert history.lifecycle_facts == corrected_target.history
    assert len(history.lifecycle_facts) == 2
    assert history.relationship_facts == (edge, correction)


def test_lineage_preserves_correction_support_and_direction() -> None:
    source = _decision(subject="Successor")
    target = _decision(subject="Prior")
    edge = _supersession(source, target)
    correction = relationship_correction(
        target_relationship_fact_id=edge.metadata.relationship_fact_id,
        effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
        correction_effective_at=NOW - timedelta(minutes=30),
        correction_basis=DecisionRelationshipCorrectionBasis(("withdraw",)),
        mutation=_relationship_mutation(
            recorded_at=NOW - timedelta(minutes=20),
            reference="withdraw",
        ),
    )
    reader = FakeDecisionMemoryReader(
        (source, target), relationship_history=(correction, edge)
    )

    lineage = asyncio.run(_service(reader).lineage(target.decision_id))

    assert len(lineage) == 1
    item = lineage[0]
    assert item.direction is DecisionLineageDirection.INCOMING
    assert item.state is DecisionRelationshipState.WITHDRAWN
    assert item.history == (correction, edge)
    assert correction.metadata.relationship_fact_id in item.support_fact_ids
    assert any(
        contribution.role is DecisionRelationshipBasisRole.CORRECTION
        for contribution in item.basis_contributions
    )


def test_history_cutoff_hides_later_recorded_facts_without_deleting_them() -> None:
    original = _decision()
    correction_time = NOW - timedelta(minutes=10)
    corrected = correct_decision_lifecycle(
        original,
        target_fact_id=original.history[0].metadata.fact_id,
        effect=DecisionLifecycleCorrectionEffect.QUALIFY,
        correction_basis=DecisionLifecycleCorrectionBasis("unsupported-need"),
        replacement_disposition=(
            DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED
        ),
        replacement_basis=UnsupportedDecisionNeedBasis("bad-initiation"),
        mutation=DecisionMutationContext(
            DecisionLifecycleFactId(uuid4()),
            OperationId(uuid4()),
            _actor(),
            _trigger("later-correction"),
            correction_time,
            correction_time,
            _technical("later-correction"),
        ),
        applicability=DecisionApplicability.OPERATIVE,
    )
    reader = FakeDecisionMemoryReader((corrected,))
    service = _service(reader)

    before = asyncio.run(
        service.history(
            corrected.decision_id,
            known_at=correction_time - timedelta(minutes=1),
        )
    )
    after = asyncio.run(service.history(corrected.decision_id))

    assert before.lifecycle_facts == (corrected.history[0],)
    assert after.lifecycle_facts == corrected.history


# arid: enable


def test_unresolved_continuity_candidates_use_existing_async_reader_contract() -> None:
    first = _decision()
    second = _decision()
    reader = FakeDecisionMemoryReader(
        (first, second),
        continuity_candidates=(second.decision_id, first.decision_id),
    )

    candidates = asyncio.run(_service(reader).unresolved_continuity_candidates())

    assert candidates == tuple(
        sorted(
            (first.decision_id, second.decision_id),
            key=lambda identity: identity.value.int,
        )
    )


def test_missing_relationship_ancestry_fails_closed_with_application_error() -> None:
    decision = _decision()
    correction = relationship_correction(
        target_relationship_fact_id=DecisionRelationshipFactId(uuid4()),
        effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
        correction_effective_at=NOW - timedelta(minutes=30),
        correction_basis=DecisionRelationshipCorrectionBasis(("missing",)),
        mutation=_relationship_mutation(
            recorded_at=NOW - timedelta(minutes=20),
            reference="missing-ancestry",
        ),
    )
    reader = FakeDecisionMemoryReader((decision,), relationship_history=(correction,))

    with pytest.raises(RelationshipHistoryInvalidOrIncomplete):
        asyncio.run(_service(reader).lineage(decision.decision_id))


def test_reader_failure_is_translated_at_application_boundary() -> None:
    decision = _decision()
    service = _service(FailingDecisionMemoryReader((decision,)))

    with pytest.raises(PersistenceUnavailable) as raised:
        asyncio.run(service.current(decision.decision_id))

    assert isinstance(raised.value.__cause__, RuntimeError)


def test_unknown_decision_uses_shared_application_not_found_outcome() -> None:
    reader = FakeDecisionMemoryReader(())
    identity = InvestmentDecisionId(uuid4())

    with pytest.raises(DecisionNotFound):
        asyncio.run(_service(reader).current(identity))


def test_query_contract_is_executor_neutral_across_event_loops_and_threads() -> None:
    decision = _decision()
    service = _service(FakeDecisionMemoryReader((decision,)))

    def read_current(_: int) -> DecisionMemoryView:
        return asyncio.run(service.current(decision.decision_id))

    with ThreadPoolExecutor(max_workers=2) as executor:
        views = tuple(executor.map(read_current, range(2)))

    assert views[0] == views[1]
    assert views[0].decision_id == decision.decision_id


def test_public_query_surface_adds_no_prior_decision_context_contract() -> None:
    assert set(DecisionRelationshipType) == {
        DecisionRelationshipType.RENEWED_FROM,
        DecisionRelationshipType.SUPERSEDES,
    }
    assert "DecisionMemoryService" in decisions_api.__all__
    assert "DecisionMemoryQueryReader" in decisions_api.__all__
