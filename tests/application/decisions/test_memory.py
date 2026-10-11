from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
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
    DecisionVersionSupport,
    PersistenceUnavailable,
    RelationshipHistoryIncomplete,
    RelationshipHistoryInvalidOrIncomplete,
)
from polaris.application.decisions.owner_meaning import (
    DecisionMeaningProvenance,
    DecisionOwnerMeaningReader,
)
from polaris.application.evidence.owner_meaning import (
    GoverningDecisionMeaning,
    OwnerMeaningNoBasis,
    OwnerMeaningNoBasisReason,
    OwnerMeaningResolver,
    OwnerMeaningWitness,
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
    DecisionWorkControlBasis,
    DecisionWorkPosture,
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
    withdraw_decision_work,
)
from polaris.domain.decisions.facts import DecisionLifecycleFact
from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    DecisionContextVersionRef,
)
from polaris.domain.evidence.judgments import (
    EvidenceUse,
    InvestmentViewRef,
    JudgmentWideEvidenceScope,
)

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
    assert "DecisionOwnerMeaningReader" in decisions_api.__all__


def _meaning_key(decision: InvestmentDecision) -> BasisScopeKey:
    return BasisScopeKey(
        decision.decision_id,
        InvestmentViewRef(uuid4()),
        JudgmentWideEvidenceScope(),
        EvidenceUse.JUDGMENT_BASIS,
    )


def _meaning_subject(decision: InvestmentDecision) -> GoverningDecisionMeaning:
    return GoverningDecisionMeaning(
        DecisionContextVersionRef(decision.decision_id, decision.version)
    )


def _version_support(
    decision: InvestmentDecision, fact: DecisionRelationshipFact
) -> DecisionVersionSupport:
    return DecisionVersionSupport(
        decision.decision_id,
        fact.metadata.operation_id,
        frozenset((fact.metadata.relationship_fact_id,)),
        decision.version,
        DecisionVersion(decision.version.value + 1),
        fact.metadata.recorded_at,
    )


def _split_recording_operation(
    source: InvestmentDecision, target: InvestmentDecision
) -> tuple[DecisionRelationshipFact, DecisionRelationshipFact]:
    first = _supersession(source, target, recorded_at=NOW - timedelta(hours=2))
    second = _supersession(source, target, recorded_at=NOW - timedelta(hours=1))
    return first, replace(
        second,
        metadata=replace(second.metadata, operation_id=first.metadata.operation_id),
    )


def _future_relationship_owner(
    *, effective_at: datetime
) -> tuple[
    InvestmentDecision,
    DecisionRelationshipFact,
    FakeDecisionMemoryReader,
    BasisScopeKey,
    GoverningDecisionMeaning,
    OwnerMeaningResolver,
]:
    source, target = _decision(subject="Successor"), _decision(subject="Prior")
    edge = _supersession(
        source,
        target,
        recorded_at=NOW - timedelta(hours=1),
        effective_at=effective_at,
    )
    reader = FakeDecisionMemoryReader((source, target), relationship_history=(edge,))
    version = DecisionVersion(
        target.version.value
        + (edge.relationship_effective_at <= edge.metadata.recorded_at)
    )
    support = replace(_version_support(target, edge), after=version)
    reader.current_states[target.decision_id] = DecisionMemoryCurrentState(
        target.history, version, (edge,), (support,)
    )
    key = _meaning_key(target)
    subject = GoverningDecisionMeaning(
        DecisionContextVersionRef(target.decision_id, version)
    )
    return (
        target,
        edge,
        reader,
        key,
        subject,
        OwnerMeaningResolver(DecisionOwnerMeaningReader(reader)),
    )


def _witness_at(
    resolver: OwnerMeaningResolver,
    key: BasisScopeKey,
    subject: GoverningDecisionMeaning,
    at: datetime,
) -> OwnerMeaningWitness:
    result = asyncio.run(resolver.read_current(key, subject, at=at))
    assert isinstance(result, OwnerMeaningWitness)
    return result


def _owner_mutation(
    reference: str, *, effective_at: datetime, recorded_at: datetime
) -> DecisionMutationContext:
    return DecisionMutationContext(
        DecisionLifecycleFactId(uuid4()),
        OperationId(uuid4()),
        _actor(),
        _trigger(reference),
        effective_at,
        recorded_at,
        _technical(reference),
    )


def test_decision_owner_attests_future_relationship_change_without_new_version() -> (
    None
):
    effective = NOW + timedelta(days=1)
    _, edge, _, key, subject, resolver = _future_relationship_owner(
        effective_at=effective
    )
    prior = _witness_at(resolver, key, subject, NOW)
    fresh = _witness_at(resolver, key, subject, effective)

    assert prior.subject == fresh.subject
    assert prior.meaning.applicability is DecisionApplicability.OPERATIVE
    assert fresh.meaning.applicability is DecisionApplicability.NON_OPERATIVE
    assert prior.semantic_identity != fresh.semantic_identity
    assert prior.provenance is DecisionMeaningProvenance.R2_DECISION_MEMORY
    assert prior.cause.complete and fresh.cause.complete
    assert prior.cause.fact_ancestry and prior.cause.relationship_guards
    assert prior.key == fresh.key == key
    assert prior.effective_at == prior.known_at == prior.read_at == NOW
    assert fresh.effective_at == fresh.known_at == fresh.read_at == effective
    assert prior.cause.relationship_guards[0].selected == ()
    assert fresh.cause.relationship_guards[0].selected == fresh.meaning.lineage
    assert any(record.fact == edge for record in fresh.cause.fact_ancestry)
    assert asyncio.run(resolver.verify(prior, validation_at=effective)) == prior
    fabricated = replace(
        prior,
        meaning=replace(
            prior.meaning, applicability=DecisionApplicability.NON_OPERATIVE
        ),
    )
    rejected = asyncio.run(resolver.verify(fabricated, validation_at=effective))
    assert isinstance(rejected, OwnerMeaningNoBasis)
    assert rejected.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY


@pytest.mark.parametrize(
    ("effective_at", "claimed_version"),
    (
        (NOW + timedelta(days=1), 2),
        (NOW - timedelta(days=1), 1),
    ),
)
def test_decision_owner_rejects_receipt_with_wrong_relationship_version_effect(
    effective_at: datetime, claimed_version: int
) -> None:
    target, _, reader, key, _, resolver = _future_relationship_owner(
        effective_at=effective_at
    )
    snapshot = reader.current_states[target.decision_id]
    version = DecisionVersion(claimed_version)
    reader.current_states[target.decision_id] = replace(
        snapshot,
        version=version,
        version_support=(replace(snapshot.version_support[0], after=version),),
    )
    subject = GoverningDecisionMeaning(
        DecisionContextVersionRef(target.decision_id, version)
    )
    result = asyncio.run(resolver.read_current(key, subject, at=NOW))
    assert isinstance(result, OwnerMeaningNoBasis)
    assert result.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY


def test_decision_owner_requires_version_change_with_existing_v1_correction() -> None:
    source, target = _decision(subject="Successor"), _decision(subject="Prior")
    recorded_at = NOW - timedelta(hours=1)
    edge = _supersession(source, target, recorded_at=recorded_at)
    corrected = correct_decision_lifecycle(
        target,
        target_fact_id=target.history[0].metadata.fact_id,
        effect=DecisionLifecycleCorrectionEffect.QUALIFY,
        correction_basis=DecisionLifecycleCorrectionBasis("future qualification"),
        replacement_disposition=(
            DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED
        ),
        replacement_basis=UnsupportedDecisionNeedBasis("bad initiation"),
        mutation=replace(
            _owner_mutation(
                "future-qualification",
                effective_at=NOW + timedelta(days=1),
                recorded_at=recorded_at,
            ),
            operation_id=edge.metadata.operation_id,
        ),
        applicability=DecisionApplicability.OPERATIVE,
    )
    assert corrected.version == target.version
    support = replace(_version_support(target, edge), after=target.version)
    reader = FakeDecisionMemoryReader((source, corrected), relationship_history=(edge,))
    reader.current_states[target.decision_id] = DecisionMemoryCurrentState(
        corrected.history, corrected.version, (edge,), (support,)
    )
    result = asyncio.run(
        OwnerMeaningResolver(DecisionOwnerMeaningReader(reader)).read_current(
            _meaning_key(corrected), _meaning_subject(corrected), at=NOW
        )
    )
    assert isinstance(result, OwnerMeaningNoBasis)
    assert result.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY


def test_decision_owner_accepts_initial_relationship_at_version_one() -> None:
    source = _decision(subject="Successor", recorded_at=START - timedelta(hours=1))
    target = _decision(subject="Prior", recorded_at=START)
    edge = _supersession(source, target, recorded_at=START, effective_at=START)
    edge = replace(
        edge,
        metadata=replace(
            edge.metadata, operation_id=target.history[0].metadata.operation_id
        ),
    )
    support = replace(_version_support(target, edge), after=target.version)
    reader = FakeDecisionMemoryReader((source, target), relationship_history=(edge,))
    reader.current_states[target.decision_id] = DecisionMemoryCurrentState(
        target.history, target.version, (edge,), (support,)
    )
    result = asyncio.run(
        OwnerMeaningResolver(DecisionOwnerMeaningReader(reader)).read_current(
            _meaning_key(target), _meaning_subject(target), at=NOW
        )
    )
    assert isinstance(result, OwnerMeaningWitness)
    assert result.cause.complete


def test_decision_owner_ignores_time_and_valid_future_only_history() -> None:
    target, edge, reader, key, subject, resolver = _future_relationship_owner(
        effective_at=NOW + timedelta(days=2)
    )
    prior = _witness_at(resolver, key, subject, NOW)
    fresh = _witness_at(resolver, key, subject, NOW + timedelta(days=1))

    assert prior.semantic_identity == fresh.semantic_identity
    assert prior.cause == fresh.cause

    unrelated_source, unrelated_target = _decision(), _decision()
    unrelated = _supersession(
        unrelated_source,
        unrelated_target,
        recorded_at=NOW + timedelta(hours=1),
        effective_at=NOW + timedelta(days=3),
    )
    reader.current_states[target.decision_id] = DecisionMemoryCurrentState(
        target.history,
        target.version,
        (edge, unrelated),
        (replace(_version_support(target, edge), after=target.version),),
    )
    after_unrelated = _witness_at(resolver, key, subject, NOW + timedelta(days=1))
    assert prior.semantic_identity == after_unrelated.semantic_identity
    assert prior.cause != after_unrelated.cause


def test_decision_owner_attests_future_lifecycle_correction_without_new_version() -> (
    None
):
    decision = _decision()
    effective = NOW + timedelta(days=1)
    corrected = correct_decision_lifecycle(
        decision,
        target_fact_id=decision.history[0].metadata.fact_id,
        effect=DecisionLifecycleCorrectionEffect.QUALIFY,
        correction_basis=DecisionLifecycleCorrectionBasis("unsupported-need"),
        replacement_disposition=(
            DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED
        ),
        replacement_basis=UnsupportedDecisionNeedBasis("bad-initiation"),
        mutation=_owner_mutation(
            "future-correction",
            effective_at=effective,
            recorded_at=NOW - timedelta(minutes=1),
        ),
        applicability=DecisionApplicability.OPERATIVE,
    )
    reader = FakeDecisionMemoryReader((corrected,))
    key, subject = _meaning_key(corrected), _meaning_subject(corrected)
    resolver = OwnerMeaningResolver(DecisionOwnerMeaningReader(reader))

    prior = _witness_at(resolver, key, subject, NOW)
    fresh = _witness_at(resolver, key, subject, effective)
    assert prior.subject == fresh.subject
    assert prior.meaning.disposition is DecisionLifecycleDisposition.UNRESOLVED
    assert (
        fresh.meaning.disposition
        is DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED
    )
    assert prior.semantic_identity != fresh.semantic_identity
    assert prior.cause.correction_ancestry == fresh.cause.correction_ancestry


@pytest.mark.parametrize("with_relationship", (False, True))
def test_decision_owner_rejects_future_correction_false_version_advance(
    with_relationship: bool,
) -> None:
    # duplicate-code: this forged correction probes both the lifecycle-only and
    # mixed-command version boundaries that lawful owner fixtures also construct.
    # arid: disable
    source, target = _decision(subject="Successor"), _decision(subject="Prior")
    recorded_at = NOW - timedelta(hours=1)
    edge = _supersession(
        source,
        target,
        recorded_at=recorded_at,
        effective_at=NOW + timedelta(days=2),
    )
    mutation = _owner_mutation(
        "future-correction-version",
        effective_at=NOW + timedelta(days=1),
        recorded_at=recorded_at,
    )
    if with_relationship:
        mutation = replace(mutation, operation_id=edge.metadata.operation_id)
    corrected = correct_decision_lifecycle(
        target,
        target_fact_id=target.history[0].metadata.fact_id,
        effect=DecisionLifecycleCorrectionEffect.QUALIFY,
        correction_basis=DecisionLifecycleCorrectionBasis("future correction"),
        replacement_disposition=(
            DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED
        ),
        replacement_basis=UnsupportedDecisionNeedBasis("bad initiation"),
        mutation=mutation,
        applicability=DecisionApplicability.OPERATIVE,
    )
    assert corrected.version == target.version
    claimed_version = DecisionVersion(target.version.value + 1)
    correction = replace(
        corrected.history[-1],
        metadata=replace(
            corrected.history[-1].metadata, decision_version=claimed_version
        ),
    )
    relationships = (edge,) if with_relationship else ()
    support = (_version_support(target, edge),) if with_relationship else ()
    reader = FakeDecisionMemoryReader(
        (source, target), relationship_history=relationships
    )
    reader.current_states[target.decision_id] = DecisionMemoryCurrentState(
        (*target.history, correction), claimed_version, relationships, support
    )
    subject = GoverningDecisionMeaning(
        DecisionContextVersionRef(target.decision_id, claimed_version)
    )
    result = asyncio.run(
        OwnerMeaningResolver(DecisionOwnerMeaningReader(reader)).read_current(
            _meaning_key(target), subject, at=NOW
        )
    )
    assert isinstance(result, OwnerMeaningNoBasis)
    assert result.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY
    # arid: enable


def test_decision_owner_attests_current_correction_version_advance() -> None:
    # duplicate-code: the currently effective correction is the positive
    # counterpart of the future-only correction's false-version proof.
    # arid: disable
    decision = _decision()
    corrected = correct_decision_lifecycle(
        decision,
        target_fact_id=decision.history[0].metadata.fact_id,
        effect=DecisionLifecycleCorrectionEffect.QUALIFY,
        correction_basis=DecisionLifecycleCorrectionBasis("current correction"),
        replacement_disposition=(
            DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED
        ),
        replacement_basis=UnsupportedDecisionNeedBasis("bad initiation"),
        mutation=_owner_mutation(
            "current-correction-version",
            effective_at=NOW - timedelta(hours=2),
            recorded_at=NOW - timedelta(hours=1),
        ),
        applicability=DecisionApplicability.OPERATIVE,
    )
    assert corrected.version == DecisionVersion(2)
    witness = _witness_at(
        OwnerMeaningResolver(
            DecisionOwnerMeaningReader(FakeDecisionMemoryReader((corrected,)))
        ),
        _meaning_key(corrected),
        _meaning_subject(corrected),
        NOW,
    )
    assert (
        witness.meaning.disposition
        is DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED
    )
    # arid: enable


def test_decision_owner_attests_future_work_posture_without_new_version() -> None:
    decision = _decision()
    effective = NOW + timedelta(days=1)
    withdrawn = withdraw_decision_work(
        decision,
        basis=DecisionWorkControlBasis("withdraw-work"),
        applicability=DecisionApplicability.OPERATIVE,
        mutation=_owner_mutation(
            "future-withdrawal",
            effective_at=effective,
            recorded_at=NOW - timedelta(minutes=1),
        ),
    )
    key, subject = _meaning_key(withdrawn), _meaning_subject(withdrawn)
    resolver = OwnerMeaningResolver(
        DecisionOwnerMeaningReader(FakeDecisionMemoryReader((withdrawn,)))
    )
    prior = _witness_at(resolver, key, subject, NOW)
    fresh = _witness_at(resolver, key, subject, effective)

    assert prior.subject == fresh.subject
    assert prior.meaning.disposition is fresh.meaning.disposition
    assert prior.meaning.work_posture is DecisionWorkPosture.ACTIVE
    assert fresh.meaning.work_posture is DecisionWorkPosture.WITHDRAWN
    assert prior.semantic_identity != fresh.semantic_identity


def test_decision_owner_rejects_invalid_future_only_relationship_history() -> None:
    decision = _decision()
    other = _decision()
    edge = _supersession(
        other,
        decision,
        effective_at=NOW + timedelta(days=2),
    )
    orphan = relationship_correction(
        target_relationship_fact_id=DecisionRelationshipFactId(uuid4()),
        effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
        correction_effective_at=NOW + timedelta(days=3),
        correction_basis=DecisionRelationshipCorrectionBasis(("orphan",)),
        mutation=_relationship_mutation(
            recorded_at=NOW - timedelta(minutes=1), reference="orphan"
        ),
    )
    reader = FakeDecisionMemoryReader(
        (decision, other), relationship_history=(edge, orphan)
    )
    reader.current_states[decision.decision_id] = DecisionMemoryCurrentState(
        decision.history, decision.version, (edge, orphan)
    )
    result = asyncio.run(
        OwnerMeaningResolver(DecisionOwnerMeaningReader(reader)).read_current(
            _meaning_key(decision), _meaning_subject(decision), at=NOW
        )
    )
    assert isinstance(result, OwnerMeaningNoBasis)
    assert result.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY


def test_decision_owner_does_not_infer_absence_or_accept_unexplained_meaning() -> None:
    decision = _decision()
    key, subject = _meaning_key(decision), _meaning_subject(decision)
    missing = OwnerMeaningResolver(
        DecisionOwnerMeaningReader(FakeDecisionMemoryReader(()))
    )
    absent = asyncio.run(missing.read_current(key, subject, at=NOW))
    assert isinstance(absent, OwnerMeaningNoBasis)
    assert absent.reason is OwnerMeaningNoBasisReason.MISSING

    reader = FakeDecisionMemoryReader((decision,))
    resolver = OwnerMeaningResolver(DecisionOwnerMeaningReader(reader))
    prior = asyncio.run(resolver.read_current(key, subject, at=NOW))
    assert isinstance(prior, OwnerMeaningWitness)

    class IncompleteReader(FakeDecisionMemoryReader):
        async def load_current_decision_state(
            self, decision_id: InvestmentDecisionId, *, known_at: datetime
        ) -> DecisionMemoryCurrentState | None:
            return DecisionMemoryCurrentState((), decision.version, ())

    changed = asyncio.run(
        OwnerMeaningResolver(
            DecisionOwnerMeaningReader(IncompleteReader((decision,)))
        ).verify(prior, validation_at=NOW + timedelta(hours=1))
    )
    assert isinstance(changed, OwnerMeaningNoBasis)
    assert changed.reason is OwnerMeaningNoBasisReason.INCOMPLETE

    unavailable = OwnerMeaningResolver(
        DecisionOwnerMeaningReader(FailingDecisionMemoryReader((decision,)))
    )
    result = asyncio.run(unavailable.read_current(key, subject, at=NOW))
    assert isinstance(result, OwnerMeaningNoBasis)
    assert result.reason is OwnerMeaningNoBasisReason.UNAVAILABLE

    revised = revise_subject(
        decision,
        subject=DecisionSubject("Unexpected same-version revision"),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        applicability=DecisionApplicability.OPERATIVE,
        mutation=_owner_mutation(
            "unversioned-revision", effective_at=NOW, recorded_at=NOW
        ),
    )
    reader.current_states[decision.decision_id] = DecisionMemoryCurrentState(
        revised.history, decision.version, ()
    )
    invalid = asyncio.run(resolver.read_current(key, subject, at=NOW))
    assert isinstance(invalid, OwnerMeaningNoBasis)
    assert invalid.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY


def test_decision_owner_keeps_temporal_and_version_failures_distinct() -> None:
    decision = _decision()
    key, subject = _meaning_key(decision), _meaning_subject(decision)
    reader = FakeDecisionMemoryReader((decision,))
    future_initiation = replace(
        decision.history[0],
        metadata=replace(
            decision.history[0].metadata,
            effective_at=NOW + timedelta(days=1),
        ),
    )
    reader.current_states[decision.decision_id] = DecisionMemoryCurrentState(
        (future_initiation,), decision.version, ()
    )
    resolver = OwnerMeaningResolver(DecisionOwnerMeaningReader(reader))
    future = asyncio.run(resolver.read_current(key, subject, at=NOW))
    assert isinstance(future, OwnerMeaningNoBasis)
    assert future.reason is OwnerMeaningNoBasisReason.NOT_YET_EFFECTIVE

    reader.current_states[decision.decision_id] = DecisionMemoryCurrentState(
        decision.history, DecisionVersion(decision.version.value + 1), ()
    )
    contradictory = asyncio.run(resolver.read_current(key, subject, at=NOW))
    assert isinstance(contradictory, OwnerMeaningNoBasis)
    assert contradictory.reason is OwnerMeaningNoBasisReason.CONTRADICTORY

    with pytest.raises(ValueError, match="exact key"):
        asyncio.run(resolver.read_current(_meaning_key(_decision()), subject, at=NOW))


def test_decision_owner_requires_history_for_exact_root_and_version() -> None:
    decision, other = _decision(), _decision()
    key, subject = _meaning_key(decision), _meaning_subject(decision)
    reader = FakeDecisionMemoryReader((decision, other))
    resolver = OwnerMeaningResolver(DecisionOwnerMeaningReader(reader))

    reader.current_states[decision.decision_id] = DecisionMemoryCurrentState(
        other.history, decision.version, ()
    )
    wrong_root = asyncio.run(resolver.read_current(key, subject, at=NOW))
    assert isinstance(wrong_root, OwnerMeaningNoBasis)
    assert wrong_root.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY

    unsupported = DecisionVersion(decision.version.value + 1)
    reader.current_states[decision.decision_id] = DecisionMemoryCurrentState(
        decision.history, unsupported, ()
    )
    higher_subject = GoverningDecisionMeaning(
        DecisionContextVersionRef(decision.decision_id, unsupported)
    )
    no_version_cause = asyncio.run(resolver.read_current(key, higher_subject, at=NOW))
    assert isinstance(no_version_cause, OwnerMeaningNoBasis)
    assert no_version_cause.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY


def test_decision_owner_rejects_self_bootstrapping_relationship_version() -> None:
    target, _, reader, key, subject, resolver = _future_relationship_owner(
        effective_at=NOW - timedelta(days=1)
    )
    supported = reader.current_states[target.decision_id]
    claimed = supported.version_support[0]
    reader.current_states[target.decision_id] = replace(
        supported,
        version_support=(replace(claimed, before=supported.version),),
    )
    result = asyncio.run(resolver.read_current(key, subject, at=NOW))
    assert isinstance(result, OwnerMeaningNoBasis)
    assert result.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY

    reader.current_states[target.decision_id] = replace(supported, version_support=())
    missing = asyncio.run(resolver.read_current(key, subject, at=NOW))
    assert isinstance(missing, OwnerMeaningNoBasis)
    assert missing.reason is OwnerMeaningNoBasisReason.INCOMPLETE


def test_decision_owner_rejects_split_recording_boundary_in_one_operation() -> None:
    source, target = _decision(subject="Successor"), _decision(subject="Prior")
    first, second = _split_recording_operation(source, target)
    support = DecisionVersionSupport(
        target.decision_id,
        first.metadata.operation_id,
        frozenset(
            (
                first.metadata.relationship_fact_id,
                second.metadata.relationship_fact_id,
            )
        ),
        target.version,
        DecisionVersion(target.version.value + 1),
        second.metadata.recorded_at,
    )
    # duplicate-code: the split-recording falsifier constructs a deliberately
    # invalid operation; sharing its reader setup with the contested-history
    # proof would couple distinct owner failure boundaries.
    # arid: disable
    reader = FakeDecisionMemoryReader(
        (source, target), relationship_history=(first, second)
    )
    reader.current_states[target.decision_id] = DecisionMemoryCurrentState(
        target.history,
        # arid: enable
        support.after,
        (first, second),
        (support,),
    )
    key = _meaning_key(target)
    subject = GoverningDecisionMeaning(
        DecisionContextVersionRef(target.decision_id, support.after)
    )
    resolver = OwnerMeaningResolver(DecisionOwnerMeaningReader(reader))

    invalid = asyncio.run(resolver.read_current(key, subject, at=NOW))
    assert isinstance(invalid, OwnerMeaningNoBasis)
    assert invalid.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY

    partial = asyncio.run(
        resolver.read_current(key, subject, at=NOW - timedelta(minutes=90))
    )
    assert isinstance(partial, OwnerMeaningNoBasis)
    assert partial.reason is OwnerMeaningNoBasisReason.INCOMPLETE


def test_decision_owner_checks_nonincident_operation_recording_history() -> None:
    decision, source, target = _decision(), _decision(), _decision()
    first, second = _split_recording_operation(source, target)
    reader = FakeDecisionMemoryReader(
        (decision, source, target), relationship_history=(first, second)
    )
    reader.current_states[decision.decision_id] = DecisionMemoryCurrentState(
        decision.history, decision.version, (first, second)
    )
    # duplicate-code: this out-of-key invalid-history proof reads its own owner
    # result; sharing assertions with the orphan-history proof would couple
    # independent failure cases.
    # arid: disable
    result = asyncio.run(
        OwnerMeaningResolver(DecisionOwnerMeaningReader(reader)).read_current(
            _meaning_key(decision), _meaning_subject(decision), at=NOW
        )
    )
    assert isinstance(result, OwnerMeaningNoBasis)
    assert result.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY
    # arid: enable


def _mixed_operation_owner(
    *,
    lifecycle_recorded_at: datetime,
    relationship_recorded_at: datetime,
    relationship_effective_at: datetime | None = None,
) -> tuple[OwnerMeaningResolver, BasisScopeKey, GoverningDecisionMeaning]:
    # duplicate-code: this same-operation lifecycle fixture and the future-only
    # relationship fixture above exercise distinct receipt/version contracts.
    # arid: disable
    source, target = _decision(subject="Successor"), _decision(subject="Prior")
    edge = _supersession(
        source,
        target,
        recorded_at=relationship_recorded_at,
        effective_at=(
            relationship_effective_at
            if relationship_effective_at is not None
            else NOW - timedelta(hours=3)
        ),
    )
    # arid: enable
    revised = revise_subject(
        target,
        subject=DecisionSubject("Revised prior"),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        applicability=DecisionApplicability.OPERATIVE,
        mutation=replace(
            _owner_mutation(
                "mixed-operation-revision",
                effective_at=lifecycle_recorded_at,
                recorded_at=lifecycle_recorded_at,
            ),
            operation_id=edge.metadata.operation_id,
        ),
    )
    support = DecisionVersionSupport(
        target.decision_id,
        edge.metadata.operation_id,
        frozenset((edge.metadata.relationship_fact_id,)),
        target.version,
        revised.version,
        relationship_recorded_at,
    )
    reader = FakeDecisionMemoryReader((source, revised), relationship_history=(edge,))
    reader.current_states[target.decision_id] = DecisionMemoryCurrentState(
        revised.history, revised.version, (edge,), (support,)
    )
    return (
        OwnerMeaningResolver(DecisionOwnerMeaningReader(reader)),
        _meaning_key(revised),
        _meaning_subject(revised),
    )


def test_decision_owner_attests_atomic_lifecycle_and_relationship_revision() -> None:
    resolver, key, subject = _mixed_operation_owner(
        lifecycle_recorded_at=NOW - timedelta(hours=1),
        relationship_recorded_at=NOW - timedelta(hours=1),
    )
    result = asyncio.run(resolver.read_current(key, subject, at=NOW))
    assert isinstance(result, OwnerMeaningWitness)
    assert result.cause.complete
    assert result.meaning.subject == DecisionSubject("Revised prior")


def test_decision_owner_attests_atomic_revision_with_future_relationship() -> None:
    resolver, key, subject = _mixed_operation_owner(
        lifecycle_recorded_at=NOW - timedelta(hours=1),
        relationship_recorded_at=NOW - timedelta(hours=1),
        relationship_effective_at=NOW + timedelta(days=1),
    )
    result = asyncio.run(resolver.read_current(key, subject, at=NOW))
    assert isinstance(result, OwnerMeaningWitness)
    assert result.meaning.subject == DecisionSubject("Revised prior")
    assert result.cause.complete


def test_decision_owner_rejects_split_mixed_operation_recording() -> None:
    resolver, key, subject = _mixed_operation_owner(
        lifecycle_recorded_at=NOW - timedelta(hours=2),
        relationship_recorded_at=NOW - timedelta(hours=1),
    )
    result = asyncio.run(resolver.read_current(key, subject, at=NOW))
    assert isinstance(result, OwnerMeaningNoBasis)
    assert result.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY


@pytest.mark.parametrize("relationship_version", (1, 2))
def test_decision_owner_orders_equal_recording_time_by_version_cause(
    relationship_version: int,
) -> None:
    # duplicate-code: this distinct-operation causal-order proof shares the
    # revision and receipt setup with the atomic same-operation proof above.
    # arid: disable
    for _ in range(24):
        source, target = _decision(subject="Successor"), _decision(subject="Prior")
        recorded_at = NOW - timedelta(hours=1)
        revised = revise_subject(
            target,
            subject=DecisionSubject("Revised prior"),
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            applicability=DecisionApplicability.OPERATIVE,
            mutation=_owner_mutation(
                "equal-time-revision",
                effective_at=recorded_at,
                recorded_at=recorded_at,
            ),
        )
        edge = _supersession(
            source,
            target,
            recorded_at=recorded_at,
            effective_at=NOW + timedelta(days=1),
        )
        support = DecisionVersionSupport(
            target.decision_id,
            edge.metadata.operation_id,
            frozenset((edge.metadata.relationship_fact_id,)),
            DecisionVersion(relationship_version),
            DecisionVersion(relationship_version),
            recorded_at,
        )
        reader = FakeDecisionMemoryReader(
            (source, revised), relationship_history=(edge,)
        )
        reader.current_states[target.decision_id] = DecisionMemoryCurrentState(
            revised.history, revised.version, (edge,), (support,)
        )
        resolver = OwnerMeaningResolver(DecisionOwnerMeaningReader(reader))
        result = asyncio.run(
            resolver.read_current(
                _meaning_key(revised), _meaning_subject(revised), at=NOW
            )
        )
        assert isinstance(result, OwnerMeaningWitness)
        assert result.cause.complete
    # arid: enable


def test_decision_owner_orders_equal_time_relationship_correction_ancestry() -> None:
    for _ in range(16):
        source, target = _decision(subject="Successor"), _decision(subject="Prior")
        recorded_at = NOW - timedelta(hours=1)
        edge = _supersession(
            source,
            target,
            recorded_at=recorded_at,
            effective_at=NOW + timedelta(days=1),
        )
        correction = relationship_correction(
            target_relationship_fact_id=edge.metadata.relationship_fact_id,
            effect=DecisionRelationshipCorrectionEffect.DISCONFIRM,
            correction_effective_at=NOW + timedelta(days=2),
            correction_basis=DecisionRelationshipCorrectionBasis(
                ("future disconfirmation",)
            ),
            mutation=_relationship_mutation(
                recorded_at=recorded_at, reference="future disconfirmation"
            ),
        )
        support = (
            replace(_version_support(target, edge), after=target.version),
            DecisionVersionSupport(
                target.decision_id,
                correction.metadata.operation_id,
                frozenset((correction.metadata.relationship_fact_id,)),
                target.version,
                target.version,
                recorded_at,
            ),
        )
        reader = FakeDecisionMemoryReader(
            (source, target), relationship_history=(edge, correction)
        )
        reader.current_states[target.decision_id] = DecisionMemoryCurrentState(
            target.history, target.version, (edge, correction), support
        )
        result = _witness_at(
            OwnerMeaningResolver(DecisionOwnerMeaningReader(reader)),
            _meaning_key(target),
            _meaning_subject(target),
            NOW,
        )
        assert result.cause.complete


def test_decision_owner_keeps_incomplete_relationship_read_distinct() -> None:
    decision = _decision()
    key, subject = _meaning_key(decision), _meaning_subject(decision)

    class IncompleteRelationshipReader(FakeDecisionMemoryReader):
        async def load_current_decision_state(
            self, decision_id: InvestmentDecisionId, *, known_at: datetime
        ) -> DecisionMemoryCurrentState | None:
            raise RelationshipHistoryIncomplete("missing relationship ancestry")

    class InvalidRelationshipReader(FakeDecisionMemoryReader):
        async def load_current_decision_state(
            self, decision_id: InvestmentDecisionId, *, known_at: datetime
        ) -> DecisionMemoryCurrentState | None:
            raise RelationshipHistoryInvalidOrIncomplete("invalid relationship fact")

    incomplete = asyncio.run(
        OwnerMeaningResolver(
            DecisionOwnerMeaningReader(IncompleteRelationshipReader((decision,)))
        ).read_current(key, subject, at=NOW)
    )
    invalid = asyncio.run(
        OwnerMeaningResolver(
            DecisionOwnerMeaningReader(InvalidRelationshipReader((decision,)))
        ).read_current(key, subject, at=NOW)
    )
    assert isinstance(incomplete, OwnerMeaningNoBasis)
    assert incomplete.reason is OwnerMeaningNoBasisReason.INCOMPLETE
    assert isinstance(invalid, OwnerMeaningNoBasis)
    assert invalid.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY


def test_decision_owner_reports_contested_incident_relationship() -> None:
    source, target = _decision(subject="Successor"), _decision(subject="Prior")
    first = _supersession(source, target, effective_at=NOW - timedelta(hours=2))
    second = _supersession(source, target, effective_at=NOW - timedelta(hours=1))
    reader = FakeDecisionMemoryReader(
        (source, target), relationship_history=(first, second)
    )
    reader.current_states[target.decision_id] = DecisionMemoryCurrentState(
        target.history,
        DecisionVersion(target.version.value + 1),
        (first, second),
        (
            _version_support(target, first),
            replace(
                _version_support(target, second),
                before=DecisionVersion(target.version.value + 1),
                after=DecisionVersion(target.version.value + 1),
            ),
        ),
    )
    subject = GoverningDecisionMeaning(
        DecisionContextVersionRef(
            target.decision_id, DecisionVersion(target.version.value + 1)
        )
    )
    result = asyncio.run(
        OwnerMeaningResolver(DecisionOwnerMeaningReader(reader)).read_current(
            _meaning_key(target), subject, at=NOW
        )
    )
    assert isinstance(result, OwnerMeaningNoBasis)
    assert result.reason is OwnerMeaningNoBasisReason.CONTESTED
